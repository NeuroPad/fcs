import os
from neo4j import GraphDatabase

uri = os.environ.get('NEO4J_URI')
user = os.environ.get('NEO4J_USER')
pwd = os.environ.get('NEO4J_PASSWORD')

print(f"Testing Neo4j connection to {uri} with user {user}")

try:
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session() as session:
        result = session.run('RETURN 1')
        print('Success:', result.single()[0])
except Exception as e:
    print('Failed to connect to Neo4j:')
    print(e) 