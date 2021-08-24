import json
import logging
import os
import sys
import uuid

from elasticsearch import Elasticsearch
from pyhocon import ConfigFactory
from sqlalchemy.ext.declarative import declarative_base

from databuilder.extractor.cassandra_extractor import CassandraExtractor
from databuilder.extractor.neo4j_search_data_extractor import Neo4jSearchDataExtractor
from databuilder.job.job import DefaultJob
from databuilder.loader.file_system_elasticsearch_json_loader import FSElasticsearchJSONLoader
from databuilder.loader.file_system_neo4j_csv_loader import FsNeo4jCSVLoader
from databuilder.publisher.elasticsearch_publisher import ElasticsearchPublisher
from databuilder.publisher.neo4j_csv_publisher import Neo4jCsvPublisher
from databuilder.publisher.neo4j_csv_publisher import JOB_PUBLISH_TAG
from databuilder.task.task import DefaultTask
from databuilder.transformer.base_transformer import NoopTransformer

tmp_folder = f'/var/tmp/amundsen/gospode3'
node_files_folder = f'{tmp_folder}/nodes'
relationship_files_folder = f'{tmp_folder}/relationships'

es_host = os.getenv('CREDENTIALS_ELASTICSEARCH_PROXY_HOST', 'localhost')
neo_host = os.getenv('CREDENTIALS_NEO4J_PROXY_HOST', 'localhost')

es_port = os.getenv('CREDENTIALS_ELASTICSEARCH_PROXY_PORT', 9200)
neo_port = os.getenv('CREDENTIALS_NEO4J_PROXY_PORT', 7687)
if len(sys.argv) > 1:
    es_host = sys.argv[1]
if len(sys.argv) > 2:
    neo_host = sys.argv[2]

es = Elasticsearch([
    {'host': es_host, 'port': es_port},
])

Base = declarative_base()

NEO4J_ENDPOINT = f'bolt://{neo_host}:{neo_port}'

neo4j_endpoint = NEO4J_ENDPOINT

neo4j_user = 'neo4j'
neo4j_password = 'test'

LOGGER = logging.getLogger(__name__)

job_config = ConfigFactory.from_dict({
    'extractor.cassandra.{}'.format(CassandraExtractor.CLUSTER_KEY): 'Test Cluster',
    'extractor.cassandra.{}'.format(CassandraExtractor.IPS_KEY): ['127.0.0.1'],
    'extractor.cassandra.{}'.format(CassandraExtractor.KWARGS_KEY): {'port': 9042},
    'extractor.cassandra.{}'.format(CassandraExtractor.FILTER_FUNCTION_KEY): None,
    'loader.filesystem_csv_neo4j.node_dir_path': node_files_folder,
    'loader.filesystem_csv_neo4j.relationship_dir_path': relationship_files_folder,
    'loader.filesystem_csv_neo4j.delete_created_directories': True,
    'publisher.neo4j.node_files_directory': node_files_folder,
    'publisher.neo4j.relation_files_directory': relationship_files_folder,
    'publisher.neo4j.neo4j_endpoint': neo4j_endpoint,
    'publisher.neo4j.neo4j_user': neo4j_user,
    'publisher.neo4j.neo4j_password': neo4j_password,
    'publisher.neo4j.neo4j_encrypted': False,
    'publisher.neo4j.job_publish_tag': 'cassandra',  # should use unique tag here like {ds}

})



task = DefaultTask(extractor=CassandraExtractor(),
                       loader=FsNeo4jCSVLoader(),
                       transformer=NoopTransformer())

DefaultJob(conf=job_config,
               task=task,
               publisher=Neo4jCsvPublisher()).launch()

               