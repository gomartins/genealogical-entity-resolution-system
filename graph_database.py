import logging
from neo4j import GraphDatabase

driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "admin"))
logger = logging.getLogger('logger')

NAME_RELATED_FIELDS = ["given_name", "known_as", "label", "birth_name", "nickname"]
NAME_INDEX = "nameIndex"


class Database(object):

    def __init__(self):
        logger.debug("Initializing database...")
        self.session = driver.session()
        person_unique_constraint = "CREATE CONSTRAINT unique_id IF NOT EXISTS ON (n:Person) ASSERT n.id IS UNIQUE"
        person_index = "CREATE INDEX id_idx IF NOT EXISTS FOR (n:Person) ON (n.id)"
        self.session.write_transaction(lambda tx: list(tx.run(person_unique_constraint)))
        self.session.write_transaction(lambda tx: list(tx.run(person_index)))
        try:
            name_related_fields = ','.join(f'"{w}"' for w in NAME_RELATED_FIELDS)
            full_text_stmt = 'CALL db.index.fulltext.createNodeIndex("{0}",["Person"],[{1}])'.format(NAME_INDEX,
                                                                                                     name_related_fields)
            self.session.write_transaction(lambda tx: list(tx.run(full_text_stmt)))
        except Exception as e:
            logger.debug("Full Text Index may already exist: %s", e)

    def get_by_id(self, wikidata_id):
        logger.debug("Getting record by id %s", wikidata_id)
        try:
            stmt = 'MATCH (p:Person) where p.id = $id return p'
            response = self.session.read_transaction(lambda tx: list(tx.run(stmt, id=wikidata_id)))
            if response:
                return response[0]
        except Exception as e:
            print(e)

    def get_relationships(self, wikidata_id):
        logger.debug("Getting relationships by id %s", wikidata_id)
        try:
            # This returns one-side relationships for anything that is not SPOUSE_OF or SIBLING_OF
            # Then it returns any-side relationship for SPOUSE_OF or SIBLING_OF
            # This is required because SPOUSE_OF and SIBLING_OF are not bi-directional in Neo4j
            stmt = "MATCH (Person {id: $id})-[r]->(p) WHERE type(r) <> ['SPOUSE_OF', 'SIBLING_OF'] " \
                   "RETURN type(r) as relationship, p.id as id " \
                   "UNION ALL " \
                   "MATCH (Person {id: $id})-[r]-(p)  WHERE type(r) IN ['SPOUSE_OF', 'SIBLING_OF'] " \
                   "RETURN type(r)  as relationship, p.id as id"
            return self.session.read_transaction(lambda tx: list(tx.run(stmt, id=wikidata_id)))
        except Exception as e:
            print(e)

    def get_all(self):
        logger.debug("Getting all the data")
        try:
            stmt = 'MATCH (p:Person) return p'
            return self.session.read_transaction(lambda tx: list(tx.run(stmt)))
        except Exception as e:
            print(e)

    def create_person(self, id, gender):
        logger.debug("Creating person ID: {0}, Gender: {1}".format(id, gender))
        try:
            stmt = f'CREATE (p: Person:{gender} {{ id: $id}})'
            self.session.write_transaction(lambda tx: list(tx.run(stmt, id=id)))
        except Exception as e:
            print(e)

    def create_relationship(self, from_id, to_id, rel_type):
        logger.debug("Creating relationship between {0} and {1} of type {2}".format(from_id, to_id, rel_type))
        rel_type = rel_type.upper()
        stmt = f'MATCH (a:Person),(b:Person) WHERE NOT (a)-[:{rel_type}]-(b) AND a.id = $from_id AND b.id = $to_id MERGE (a)-[r:{rel_type}]->(b)'
        self.session.write_transaction(lambda tx: list(tx.run(stmt, from_id=from_id, to_id=to_id)))

    def set_property(self, id, key, value):
        # logger.debug("Setting property on ID: {0}, Key: {1}, Value: {2}".format(id, key, value))
        stmt = f'MATCH (p:Person {{ id: $id }}) SET p.{key} = $value'
        self.session.write_transaction(lambda tx: list(tx.run(stmt, id=id, value=value)))

    def truncate(self):
        logger.warning("Truncating database...")
        self.session.write_transaction(lambda tx: list(tx.run('MATCH (n)-[r]-() DELETE r')))
        self.session.write_transaction(lambda tx: list(tx.run('MATCH (n) DELETE n')))

    def query_text(self, text):
        logger.debug("Querying text")
        try:
            stmt = 'CALL db.index.fulltext.queryNodes("{0}", "{1}") YIELD node, score RETURN node.id, node.label, score'.format(
                NAME_INDEX, text)
            return self.session.read_transaction(lambda tx: list(tx.run(stmt)))
        except Exception as e:
            print(e)

    def query_attr(self, attr, value):
        try:
            stmt = "MATCH(n:Person) where n.{0} = $value RETURN n".format(attr)
            return self.session.read_transaction(lambda tx: list(tx.run(stmt, value=value)))
        except Exception as e:
            print(e)
