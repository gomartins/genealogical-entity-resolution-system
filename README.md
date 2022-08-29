## Multi-source entity resolution using unstructured genealogical data


### Setting up environment
- Install Spacy version 3.2 and transformer models ([see spacy.io](https://spacy.io/usage))
- Install Neo4j ([see neo4j.com](https://neo4j.com/developer/docker-run-neo4j/))
- Unzip files within data directory
- Update `BASE_DIRECTORY` in constants.py to point to the data directory

### Directory structure:
- **/data**: Datasets and configuration files used
- **/tests**: Test classes
- **/tests/results_test.py**: Test class containing the final results for Entity Resolution & others

### Datasets description:
- **annotated_wikipedia_articles.zip**:
  - 395 Wikipedia articles from U.S. presidents and close relationships annotated for Named Entity Recognition (person) and Coreference Resolution tasks. Can be imported into Doccano or similar tools.   
- **wikipedia_articles_html.zip**:
  - Original Wikipedia articles in a HTML format. 
- **neo4j.zip**:
  - Neo4j data directory containing loaded dataset.
- **wikidata_dataset.zip**:
  - Simplified Neo4j dump.
- **social_security_dataset_transformed.zip**:
  - Transformed United States Social Security dataset aggregating more than 350 million name reports since 1880.

    
