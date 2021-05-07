'''
Source code developed by DI2AG.
Thayer School of Engineering at Dartmouth College
Authors:    Dr. Eugene Santos, Jr
            Mr. Chase Yakaboski,
            Mr. Gregory Hyde,
            Dr. Keum Joo Kim
'''
import json
import itertools
import tqdm
import numpy as np
import logging
import csv
import uuid
from collections import defaultdict

from trapi_model.base import BiolinkEntity
from trapi_model.constants import *
from chp.trapi_handlers import DefaultHandler, WildCardHandler, OneHopHandler
from chp.errors import *

# Setup logging
logger = logging.getLogger(__name__)

# Helper functions

def parse_query_graph(query_graph):
    """ Will extract the parameters that were used to build the query from the client.
    """
    try:
        parsed = defaultdict(str)
        for node_id, node in query_graph["nodes"].items():
            if node["category"] == BIOLINK_PHENOTYPIC_FEATURE:
                parsed["outcome_name"] = node_id
            elif node["category"] == BIOLINK_DRUG:
                parsed["therapeutic"] = node_id
            elif node["category"] == BIOLINK_GENE:
                if 'genes' in parsed:
                    parsed["genes"].append(node_id)
                else:
                    parsed["genes"] = [node_id]
            elif node["category"] == BIOLINK_DISEASE:
                parsed["disease"] = node_id
            else:
                raise ValueError('Unrecognized category: {}'.format(node["category"]))
        # Sort the genes
        if 'genes' in parsed:
            parsed["genes"] = sorted(parsed["genes"])
        # Find the outome op and value
        for edge_id, edge in query_graph["edges"].items():
            if edge['predicate'] == BIOLINK_DISEASE_TO_PHENOTYPIC_FEATURE_PREDICATE:
                if 'properties' in edge.keys():
                    parsed["outcome_op"] = edge["properties"]["qualifier"]
                    parsed["outcome_value"] = edge["properties"]["days"]
                # default
                else:
                    parsed["outcome_op"] = ">="
                    parsed["outcome_value"] = 970
        return parsed
    except:
        return None

class TrapiInterface:
    def __init__(self,
                 query=None,
                 hosts_filename=None,
                 num_processes_per_host=0,
                 bkb_handler=None,
                 joint_reasoner=None,
                 dynamic_reasoner=None,
                ):
        self.hosts_filename = hosts_filename
        self.num_processes_per_host = num_processes_per_host
        self.bkb_handler = bkb_handler
        self.joint_reasoner = joint_reasoner
        self.dynamic_reasoner = dynamic_reasoner

        # Get default handler for processing curies and predicates requests
        self.handler = self._get_handler(None)
        self.curies = self.handler.curies
        self.query = query

        if query is not None:
            self.query = query.get_copy()
            self.max_results = self.query.max_results
            # Check if batch query
            if query.is_batch_query():
                self.queries = query.expand_batch_query()
                #print(json.dumps([q.to_dict() for q in self.queries], indent=2))
                #input()
                logger.info('Detected batch queries,')
            else:
                logger.info('Detected single query.')
                self.queries = [query]

            self.message_dict = self._setup_messages(self.queries)


            '''
            # Analyze queries
            self.query_dict, self.query_map = self._setup_query(query)
            '''
            # Initialize necessary handlers
            self.handlers = {}
            for message_type in self.message_dict:
                self.handlers[message_type] = self._get_handler(message_type)

    def _setup_messages(self, queries):
        message_dict = defaultdict(list)
        for query in queries:
            message_type, message = self._determine_message_type(query.message)
            message_dict[message_type].append(message)
        return message_dict

    def _determine_message_type(self, message):
        """ checks for query message types. First checks node requirements to check for query type,
            then checks structures under the assumption of query type. Also updates error
            message for return to user

            :returns: a query type or None if there is a failure in matching query type
            :rtype: string or None
        """
        if message is None:
            raise UnidentifiedQueryType
        query_graph = message.query_graph
        # Check for onehop query
        if len(query_graph.edges) == 1 or len(query_graph.nodes) == 2:
            return 'onehop', message
        else:
            # Check for standard or wildcard multihop query.
            gene_nodes = []
            disease_nodes = []
            drug_nodes = []
            phenotype_nodes = []
            wildcard_node_count = 0
            wildcard_node = None
            print(self.curies.keys())

            if message is not None:
                qg = message.query_graph
                for node_id, node in qg.nodes.items():
                    if node.categories is not None:
                        if node.categories[0] == BiolinkEntity(BIOLINK_GENE):
                            gene_nodes.append(node_id)
                            if node.ids is None:
                                print(node.ids)
                                wildcard_node_count += 1
                                wildcard_node = node_id
                            else:
                                found_curie = None
                                for curie in node.ids:
                                    if curie in self.curies[BIOLINK_GENE]:
                                        found_curie = curie
                                        qg.nodes[node_id].set_ids(found_curie)
                                if found_curie is None:
                                    raise(UnidentifiedGeneCurie(node.ids))
                        elif node.categories[0] == BiolinkEntity(BIOLINK_DRUG):
                            drug_nodes.append(node_id)
                            if node.ids is None:
                                print(node.ids)
                                wildcard_node_count += 1
                                wildcard_node = node_id
                            else:
                                found_curie = None
                                for curie in node.ids:
                                    if curie in self.curies[BIOLINK_DRUG]:
                                        found_curie = curie
                                        qg.nodes[node_id].set_ids(found_curie)
                                if found_curie is None:
                                    raise(UnidentifiedDrugCurie(node.ids))
                        elif node.categories[0] == BiolinkEntity(BIOLINK_DISEASE):
                            disease_nodes.append(node_id)
                        elif node.categories[0] == BiolinkEntity(BIOLINK_PHENOTYPIC_FEATURE):
                            phenotype_nodes.append(node_id)
                            found_curie = None
                            for curie in node.ids:
                                if curie in self.curies[BIOLINK_PHENOTYPIC_FEATURE]:
                                    found_curie = curie
                                    qg.nodes[node_id].set_ids(found_curie)
                            if found_curie is None:
                                raise(UnidentifiedPhenotypeCurie(node.ids))

            if wildcard_node_count > 1:
                raise(TooManyContributionNodes)
            if len(disease_nodes) > 1:
                raise(TooManyDiseaseNodes)
            if len(phenotype_nodes) > 1:
                raise(TooManyPhenotypeNodes)
            print(gene_nodes)
            print(disease_nodes)
            print(drug_nodes)
            print(phenotype_nodes)
            print(wildcard_node_count)
            print(wildcard_node)

            if wildcard_node_count == 0 and len(phenotype_nodes) == 1 and len(disease_nodes) == 1:
                if self._check_default_query(qg, gene_nodes, drug_nodes, disease_nodes, phenotype_nodes):
                    return 'default', message
            elif len(disease_nodes) == 1 and wildcard_node_count == 1:
                if self._check_wildcard_query(qg, gene_nodes, drug_nodes, disease_nodes, phenotype_nodes):
                    return 'wildcard', message
            else:
                raise(UnidentifiedQueryType)
            
    def get_curies(self):
        """ Returns the available curies and their associated names.
        """
        # Annotate curies 
        curies = {}
        for biolink_name, _curies in self.handler.curies.items():
            curies[BiolinkEntity(biolink_name).get_curie()] = _curies
        return curies

    def get_predicates(self):
        """ Returns the available predicates and their associated names.
        """
        with open(self.handler.bkb_data_handler.predicates_path, 'r') as predicates_file:
            return json.load(predicates_file)

    def checkQuery(self):
        return True

    def _check_wildcard_query(self, query_graph, gene_nodes, drug_nodes, disease_nodes, phenotype_nodes):
        print(query_graph)
        for edge_id, edge in query_graph.edges.items():
            if edge.predicates[0] == BiolinkEntity(BIOLINK_GENE_TO_DISEASE_PREDICATE, is_slot=True):
                if edge.subject not in gene_nodes or edge.object not in disease_nodes:
                    raise(MalformedSubjectObjectOnGeneToDisease(edge_id))
            elif edge.predicates[0] == BiolinkEntity(BIOLINK_CHEMICAL_TO_DISEASE_OR_PHENOTYPIC_FEATURE_PREDICATE, is_slot=True):
                if edge.subject not in drug_nodes or edge.object not in disease_nodes:
                    raise(MalformedSubjectObjectOnDrugToDisease(edge_id))
            elif edge.predicates[0] == BiolinkEntity(BIOLINK_DISEASE_TO_PHENOTYPIC_FEATURE_PREDICATE, is_slot=True):
                if edge.subject not in disease_nodes and edge.object not in phenotype_nodes:
                    raise(MalformedSubjectObjectOnDiseaseToPhenotype(edge_id))
            elif edge.predicates[0] == BiolinkEntity(BIOLINK_CHEMICAL_TO_GENE_PREDICATE, is_slot=True):
                raise(IncompatibleWildcardEdge(edge_id))
            else:
                raise(UnexpectedEdgeType(edge_id))
        return True

    def _check_one_hop_query(self, query, gene_nodes, drug_nodes, disease_nodes, phenotype_nodes, wildcard_node):
        for edge_id, edge in query['edges'].items():
            if edge['predicate'] == BiolinkEntity(BIOLINK_GENE_TO_DISEASE_PREDICATE, is_slot=True):
                raise(IncompatibleDrugGeneOneHopEdge(edge_id))
            elif edge['predicate'] == BiolinkEntity(BIOLINK_CHEMICAL_TO_DISEASE_OR_PHENOTYPIC_FEATURE_PREDICATE, is_slot=True):
                raise(IncompatibleDrugGeneOneHopEdge(edge_id))
            elif edge['predicate'] == BiolinkEntity(BIOLINK_DISEASE_TO_PHENOTYPIC_FEATURE_PREDICATE, is_slot=True):
                raise(IncompatibleDrugGeneOneHopEdge(edge_id))
            elif edge['predicate'] == BiolinkEntity(BIOLINK_CHEMICAL_TO_GENE_PREDICATE, is_slot=True):
                subject = edge['subject']
                object = edge['object']
                if object == wildcard_node:
                     raise(MalformedSubjectObjectOnDrugGene(edge_id))
            else:
                raise(UnexpectedEdgeType(edge_id))
        return True

    def _check_default_query(self, query_graph, gene_nodes, drug_nodes, disease_nodes, phenotype_nodes):
        for edge_id, edge in query_graph.edges.items():
            if edge.predicates[0] == BiolinkEntity(BIOLINK_GENE_TO_DISEASE_PREDICATE, is_slot=True):
                if edge.subject not in gene_nodes or edge.object not in disease_nodes:
                    raise(MalformedSubjectObjectOnGeneToDisease(edge_id))
            elif edge.predicates[0] == BiolinkEntity(BIOLINK_CHEMICAL_TO_DISEASE_OR_PHENOTYPIC_FEATURE_PREDICATE, is_slot=True):
                if edge.subject not in drug_nodes or edge.object not in disease_nodes:
                    raise(MalformedSubjectObjectOnDrugToDisease(edge_id))
            elif edge.predicates[0] == BiolinkEntity(BIOLINK_DISEASE_TO_PHENOTYPIC_FEATURE_PREDICATE, is_slot=True):
                if edge.subject not in disease_nodes and edge.object not in phenotype_nodes:
                    raise(MalformedSubjectObjectOnDiseaseToPhenotype(edge_id))
            elif edge.predicates[0] == BiolinkEntity(BIOLINK_CHEMICAL_TO_GENE_PREDICATE, is_slot=True):
                raise(IncompatibleDefaultEdge(edge_id))
            else:
                print(edge.predicates[0].get_curie())
                raise(UnexpectedEdgeType(edge_id))
        return True

    def _get_handler(self, message_type):
        if message_type == 'default':
            return DefaultHandler(
                self.message_dict['default'],
                self.query,
                hosts_filename=self.hosts_filename,
                num_processes_per_host=self.num_processes_per_host,
                bkb_handler=self.bkb_handler,
                joint_reasoner=self.joint_reasoner,
                dynamic_reasoner=self.dynamic_reasoner,
            )
        elif message_type == 'wildcard':
            return WildCardHandler(
                self.message_dict['wildcard'],
                self.query,
                hosts_filename=self.hosts_filename,
                num_processes_per_host=self.num_processes_per_host,
                max_results=self.max_results,
                bkb_handler=self.bkb_handler,
                dynamic_reasoner=self.dynamic_reasoner,
            )
        elif message_type == 'onehop':
            return OneHopHandler(
                self.message_dict['onehop'],
                self.query,
                hosts_filename=self.hosts_filename,
                num_processes_per_host=self.num_processes_per_host,
                max_results=self.max_results,
                dynamic_reasoner=self.dynamic_reasoner,
            )
        elif message_type is None:
            return DefaultHandler(None, None)
        else:
            raise('Unrecognized message type or unsupported message: {}'.format(message_type))

    def _order_response(self, results):
        _unordered_response = []
        for query_type, reasoner_type_results in results.items():
            for reasoner_type, query_results in reasoner_type_results.items():
                for query_id, result in query_results:
                    # If single result just return the response
                    if self.query_map is None:
                        return result
                    # Else put the results back in the appropriate order
                    _unordered_response.append((self.query_map.index(query_id), result))
        response = [result for _id, result in sorted(_unordered_response)]
        return response

    def build_chp_queries(self):
        built_chp_queries = {}
        for message_type, handler in self.handlers.items():
            logger.info('Building queries for {} type message(s).'.format(message_type))
            built_chp_queries[message_type] = handler.build_queries()
        return built_chp_queries

    def run_chp_queries(self):
        ran_chp_queries = {}
        for message_type, handler in self.handlers.items():
            logger.info('Running queries for {} type message(s).'.format(message_type))
            ran_chp_queries[message_type] = handler.run_queries()
        return ran_chp_queries

    def construct_trapi_response(self):
        response_query = self.query.get_copy()
        for message_type, handler in self.handlers.items():
            logger.info('Constructing TRAPI response(s) for {} type message(s).'.format(message_type))
            handler_response_query = handler.construct_trapi_response()
            print('>>>>>>>>>>>>>>')
            print(json.dumps(handler_response_query.to_dict(), indent=2))
            # Merge the messages
            response_query.message.update(
                    handler_response_query.message.knowledge_graph,
                    handler_response_query.message.results,
                    )
        return response_query
