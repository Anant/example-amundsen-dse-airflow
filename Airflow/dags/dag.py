import json
import logging
import os
import sys
import uuid

from airflow import DAG  # noqa
from airflow import macros  # noqa
from airflow.operators.python_operator import PythonOperator  # noqa
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator


from elasticsearch import Elasticsearch
from sqlalchemy.ext.declarative import declarative_base

from datetime import datetime, timedelta
from textwrap import dedent

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


dag_args = {
    'concurrency': 10,
    # One dagrun at a time
    'max_active_runs': 1,
    # 4AM, 4PM PST
    'schedule_interval': '0 11 * * *',
    'catchup': False
}

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2018, 6, 18),
    'depends_on_past': False,
    'email': [''],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'priority_weight': 10,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=120)
}

def create_table_extract_job():


    tmp_folder = '/var/tmp/amundsen/table_metadata'
    node_files_folder = f'{tmp_folder}/nodes/'
    relationship_files_folder = f'{tmp_folder}/relationships/'

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
    job = DefaultJob(conf=job_config,
               task=task,
               publisher=Neo4jCsvPublisher()).launch()
    job.launch()

def create_es_publisher_sample_job():
    # loader saves data to this location and publisher reads it from here
    extracted_search_data_path = '/var/tmp/amundsen/search_data.json'

    task = DefaultTask(loader=FSElasticsearchJSONLoader(),
                       extractor=Neo4jSearchDataExtractor(),
                       transformer=NoopTransformer())

    # elastic search client instance
    elasticsearch_client = es
    # unique name of new index in Elasticsearch
    elasticsearch_new_index_key = 'tables' + str(uuid.uuid4())
    # related to mapping type from /databuilder/publisher/elasticsearch_publisher.py#L38
    elasticsearch_new_index_key_type = 'table'
    # alias for Elasticsearch used in amundsensearchlibrary/search_service/config.py as an index
    elasticsearch_index_alias = 'table_search_index'

    job_config = ConfigFactory.from_dict({
        f'extractor.search_data.extractor.neo4j.{Neo4jExtractor.GRAPH_URL_CONFIG_KEY}': neo4j_endpoint,
        f'extractor.search_data.extractor.neo4j.{Neo4jExtractor.MODEL_CLASS_CONFIG_KEY}':
            'databuilder.models.table_elasticsearch_document.TableESDocument',
        f'extractor.search_data.extractor.neo4j.{Neo4jExtractor.NEO4J_AUTH_USER}': neo4j_user,
        f'extractor.search_data.extractor.neo4j.{Neo4jExtractor.NEO4J_AUTH_PW}': neo4j_password,
        f'loader.filesystem.elasticsearch.{FSElasticsearchJSONLoader.FILE_PATH_CONFIG_KEY}': extracted_search_data_path,
        f'loader.filesystem.elasticsearch.{FSElasticsearchJSONLoader.FILE_MODE_CONFIG_KEY}': 'w',
        f'publisher.elasticsearch.{ElasticsearchPublisher.FILE_PATH_CONFIG_KEY}': extracted_search_data_path,
        f'publisher.elasticsearch.{ElasticsearchPublisher.FILE_MODE_CONFIG_KEY}': 'r',
        f'publisher.elasticsearch.{ElasticsearchPublisher.ELASTICSEARCH_CLIENT_CONFIG_KEY}':
            elasticsearch_client,
        f'publisher.elasticsearch.{ElasticsearchPublisher.ELASTICSEARCH_NEW_INDEX_CONFIG_KEY}':
            elasticsearch_new_index_key,
        f'publisher.elasticsearch.{ElasticsearchPublisher.ELASTICSEARCH_DOC_TYPE_CONFIG_KEY}':
            elasticsearch_new_index_key_type,
        f'publisher.elasticsearch.{ElasticsearchPublisher.ELASTICSEARCH_ALIAS_CONFIG_KEY}':
            elasticsearch_index_alias
    })

    job = DefaultJob(conf=job_config,
                     task=task,
                     publisher=ElasticsearchPublisher())
    job.launch()


with DAG(
    'Cassandra01',
    default_args=default_args,
    description='Cassandra Extractor',
    schedule_interval=timedelta(days=1),
    start_date=days_ago(2),
    tags=['example'],
) as dag:
    

    t1 = PythonOperator(
    task_id='extract',
    python_callable=create_table_extract_job,
    )

    t2 = PythonOperator(
    task_id='publish',
    python_callable=create_es_publisher_sample_job,
    )

    t1 >> t2