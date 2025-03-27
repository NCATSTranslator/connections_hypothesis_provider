# Connections Hypothesis Provider Reasoner Code Documentation

# About

## Description
This repository houses the reasoning code and TRAPI interface for the Connections Hypothesis Provider (CHP) service built by Dartmouth College (PI – Dr. Eugene Santos) and Tufts University (Co-PI – Joseph Gormley) in collaboration with the National Center for Advancing Translational Sciences (NCATS). CHP aims to leverage clinical data along with structured biochemical knowledge to derive a computational representation of pathway structures and molecular components to support human and machine-driven interpretation, enable pathway-based biomarker discovery, and aid in the drug development process.
In its current version, CHP supports queries relating to genetic, therapeutic, and patient clinical features (e.g. tumor staging) contribution toward patient survival, as computed within the context of our test pilot: a robust breast cancer dataset from The Cancer Genome Atlas (TCGA). We are using this as a proving ground for our system’s basic operations as we work to incorporate structured pathway knowledge and pathway analysis methods into the tool. 


For more details about the service CHP provides please see here: https://github.com/di2ag/chp_api

# Terms and Definitions
The greater NCATS consortium uses a series of terms (that we have adopted) to convey meaning quickly. A link to those terms and their definitions are available here: https://docs.google.com/spreadsheets/d/1C8hKXacxtQC5UzXI4opQs1r4pBJ_5hqgXrZH_raYQ4w/edit#gid=1581951609
We extend this list local to our KP (Look, here is an NCATS term right here!) with the following terms: 

•	Connections Hypothesis Provider – CHP

•	The Cancer Genome Atlas – TCGA

• Genomic Data Commons - GDC

•	Bayesian Knowledge Base – BKB

# Smart API
CHP is registered with Smart API: [https://smart-api.info/ui/855adaa128ce5aa58a091d99e520d396](http://smart-api.info/registry?q=412af63e15b73e5a30778aac84ce313f)

# Open Endpoints
* [query](query.md) : `POST /query/`
* [predicates](predicates.md) : `GET /meta_knowledge_graph/`


# Other Notable Links
Other notable links:

Our API Repository: https://github.com/di2ag/chp_api

Our NCATS Wiki Page: https://github.com/NCATSTranslator/Translator-All/wiki/Connections-Hypothesis-Provider

# Contacts
Dr. Eugene Santos (PI): Eugene.Santos.Jr@dartmouth.edu

Joseph Gormley (Co-PI): jgormley@tuftsmedicalcenter.org
