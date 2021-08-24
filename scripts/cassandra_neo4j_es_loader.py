# Copyright Contributors to the Amundsen project.
# SPDX-License-Identifier: Apache-2.0

"""
This is a example script demonstrating how to load data into Neo4j and
Elasticsearch without using an Airflow DAG.

It contains several jobs:
- `run_csv_job`: runs a job that extracts table data from a CSV, loads (writes)
  this into a different local directory as a csv, then publishes this data to
  neo4j.
- `run_table_column_job`: does the same thing as `run_csv_job`, but with a csv
  containing column data.
- `create_last_updated_job`: creates a job that gets the current time, dumps it
  into a predefined model schema, and publishes this to neo4j.
- `create_es_publisher_sample_job`: creates a job that extracts data from neo4j
  and pubishes it into elasticsearch.

For other available extractors, please take a look at
https://github.com/amundsen-io/amundsendatabuilder#list-of-extractors
"""

import logging
import os
import sys
import uuid

from amundsen_common.models.index_map import DASHBOARD_ELASTICSEARCH_INDEX_MAPPING, USER_INDEX_MAP
from elasticsearch import Elasticsearch
from pyhocon import ConfigFactory
from sqlalchemy.ext.declarative import declarative_base

from databuilder.extractor.csv_extractor import (
    CsvColumnLineageExtractor, CsvExtractor, CsvTableBadgeExtractor, CsvTableColumnExtractor, CsvTableLineageExtractor,
)
from databuilder.extractor.cassandra_extractor import CassandraExtractor
from databuilder.extractor.es_last_updated_extractor import EsLastUpdatedExtractor
from databuilder.extractor.neo4j_search_data_extractor import Neo4jSearchDataExtractor
from databuilder.job.job import DefaultJob
from databuilder.loader.file_system_elasticsearch_json_loader import FSElasticsearchJSONLoader
from databuilder.loader.file_system_neo4j_csv_loader import FsNeo4jCSVLoader
from databuilder.publisher.elasticsearch_publisher import ElasticsearchPublisher
from databuilder.publisher.neo4j_csv_publisher import Neo4jCsvPublisher
from databuilder.task.task import DefaultTask
from databuilder.transformer.base_transformer import ChainedTransformer, NoopTransformer
from databuilder.transformer.dict_to_model import MODEL_CLASS, DictToModel
from databuilder.transformer.generic_transformer import (
    CALLBACK_FUNCTION, FIELD_NAME, GenericTransformer,
)

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


def run_csv_job(file_loc, job_name, model):
    tmp_folder = f'/var/tmp/amundsen/{job_name}'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'

    cassandra_extractor = CassandraExtractor()
    csv_loader = FsNeo4jCSVLoader()

    task = DefaultTask(extractor=cassandra_extractor,
                       loader=csv_loader,
                       transformer=NoopTransformer())

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
        'publisher.neo4j.job_publish_tag': 'cassandra1',  # should use unique tag here like {ds}
    })

    DefaultJob(conf=job_config,
               task=task,
               publisher=Neo4jCsvPublisher()).launch()


def run_table_badge_job(table_path, badge_path):
    tmp_folder = '/var/tmp/amundsen/table_badge'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'
    extractor = CsvTableBadgeExtractor()
    csv_loader = FsNeo4jCSVLoader()
    task = DefaultTask(extractor=extractor,
                       loader=csv_loader,
                       transformer=NoopTransformer())
    job_config = ConfigFactory.from_dict({
        'extractor.csvtablebadge.table_file_location': table_path,
        'extractor.csvtablebadge.badge_file_location': badge_path,
        'loader.filesystem_csv_neo4j.node_dir_path': node_files_folder,
        'loader.filesystem_csv_neo4j.relationship_dir_path': relationship_files_folder,
        'loader.filesystem_csv_neo4j.delete_created_directories': True,
        'publisher.neo4j.node_files_directory': node_files_folder,
        'publisher.neo4j.relation_files_directory': relationship_files_folder,
        'publisher.neo4j.neo4j_endpoint': neo4j_endpoint,
        'publisher.neo4j.neo4j_user': neo4j_user,
        'publisher.neo4j.neo4j_password': neo4j_password,
        'publisher.neo4j.neo4j_encrypted': False,
        'publisher.neo4j.job_publish_tag': 'unique_tag_b',  # should use unique tag here like {ds}
    })
    job = DefaultJob(conf=job_config,
                     task=task,
                     publisher=Neo4jCsvPublisher())
    job.launch()


def run_table_column_job(table_path, column_path):
    tmp_folder = '/var/tmp/amundsen/table_column1'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'
    extractor = CsvTableColumnExtractor()
    csv_loader = FsNeo4jCSVLoader()
    task = DefaultTask(extractor,
                       loader=csv_loader,
                       transformer=NoopTransformer())
    job_config = ConfigFactory.from_dict({
        'extractor.csvtablecolumn.table_file_location': table_path,
        'extractor.csvtablecolumn.column_file_location': column_path,
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
    job = DefaultJob(conf=job_config,
                     task=task,
                     publisher=Neo4jCsvPublisher())
    job.launch()


def run_table_lineage_job(table_lineage_path):
    tmp_folder = '/var/tmp/amundsen/table_column1'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'
    extractor = CsvTableLineageExtractor()
    csv_loader = FsNeo4jCSVLoader()
    task = DefaultTask(extractor,
                       loader=csv_loader,
                       transformer=NoopTransformer())
    job_config = ConfigFactory.from_dict({
        'extractor.csvtablelineage.table_lineage_file_location': table_lineage_path,
        'loader.filesystem_csv_neo4j.node_dir_path': node_files_folder,
        'loader.filesystem_csv_neo4j.relationship_dir_path': relationship_files_folder,
        'loader.filesystem_csv_neo4j.delete_created_directories': True,
        'publisher.neo4j.node_files_directory': node_files_folder,
        'publisher.neo4j.relation_files_directory': relationship_files_folder,
        'publisher.neo4j.neo4j_endpoint': neo4j_endpoint,
        'publisher.neo4j.neo4j_user': neo4j_user,
        'publisher.neo4j.neo4j_password': neo4j_password,
        'publisher.neo4j.neo4j_encrypted': False,
        'publisher.neo4j.job_publish_tag': 'lineage_unique_tag',  # should use unique tag here like {ds}
    })
    job = DefaultJob(conf=job_config,
                     task=task,
                     publisher=Neo4jCsvPublisher())
    job.launch()


def run_column_lineage_job(column_lineage_path):
    tmp_folder = '/var/tmp/amundsen/table_column1'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'
    extractor = CsvColumnLineageExtractor()
    csv_loader = FsNeo4jCSVLoader()
    task = DefaultTask(extractor,
                       loader=csv_loader,
                       transformer=NoopTransformer())
    job_config = ConfigFactory.from_dict({
        'extractor.csvcolumnlineage.column_lineage_file_location': column_lineage_path,
        'loader.filesystem_csv_neo4j.node_dir_path': node_files_folder,
        'loader.filesystem_csv_neo4j.relationship_dir_path': relationship_files_folder,
        'loader.filesystem_csv_neo4j.delete_created_directories': True,
        'publisher.neo4j.node_files_directory': node_files_folder,
        'publisher.neo4j.relation_files_directory': relationship_files_folder,
        'publisher.neo4j.neo4j_endpoint': neo4j_endpoint,
        'publisher.neo4j.neo4j_user': neo4j_user,
        'publisher.neo4j.neo4j_password': neo4j_password,
        'publisher.neo4j.neo4j_encrypted': False,
        'publisher.neo4j.job_publish_tag': 'lineage_unique_tag',  # should use unique tag here like {ds}
    })
    job = DefaultJob(conf=job_config,
                     task=task,
                     publisher=Neo4jCsvPublisher())
    job.launch()


def create_last_updated_job():
    # loader saves data to these folders and publisher reads it from here
    tmp_folder = '/var/tmp/amundsen/last_updated_data'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'

    task = DefaultTask(extractor=EsLastUpdatedExtractor(),
                       loader=FsNeo4jCSVLoader())

    job_config = ConfigFactory.from_dict({
        'extractor.es_last_updated.model_class':
            'databuilder.models.es_last_updated.ESLastUpdated',

        'loader.filesystem_csv_neo4j.node_dir_path': node_files_folder,
        'loader.filesystem_csv_neo4j.relationship_dir_path': relationship_files_folder,
        'publisher.neo4j.node_files_directory': node_files_folder,
        'publisher.neo4j.relation_files_directory': relationship_files_folder,
        'publisher.neo4j.neo4j_endpoint': neo4j_endpoint,
        'publisher.neo4j.neo4j_user': neo4j_user,
        'publisher.neo4j.neo4j_password': neo4j_password,
        'publisher.neo4j.neo4j_encrypted': False,
        'publisher.neo4j.job_publish_tag': 'unique_lastupdated_tag',  # should use unique tag here like {ds}
    })

    return DefaultJob(conf=job_config,
                      task=task,
                      publisher=Neo4jCsvPublisher())


def _str_to_list(str_val):
    return str_val.split(',')


def create_dashboard_tables_job():
    # loader saves data to these folders and publisher reads it from here
    tmp_folder = '/var/tmp/amundsen/dashboard_table'
    node_files_folder = f'{tmp_folder}/nodes'
    relationship_files_folder = f'{tmp_folder}/relationships'

    csv_extractor = CsvExtractor()
    csv_loader = FsNeo4jCSVLoader()

    generic_transformer = GenericTransformer()
    dict_to_model_transformer = DictToModel()
    transformer = ChainedTransformer(transformers=[generic_transformer, dict_to_model_transformer],
                                     is_init_transformers=True)

    task = DefaultTask(extractor=csv_extractor,
                       loader=csv_loader,
                       transformer=transformer)
    publisher = Neo4jCsvPublisher()

    job_config = ConfigFactory.from_dict({
        f'{csv_extractor.get_scope()}.file_location': 'example/sample_data/sample_dashboard_table.csv',
        f'{transformer.get_scope()}.{generic_transformer.get_scope()}.{FIELD_NAME}': 'table_ids',
        f'{transformer.get_scope()}.{generic_transformer.get_scope()}.{CALLBACK_FUNCTION}': _str_to_list,
        f'{transformer.get_scope()}.{dict_to_model_transformer.get_scope()}.{MODEL_CLASS}':
            'databuilder.models.dashboard.dashboard_table.DashboardTable',
        f'{csv_loader.get_scope()}.node_dir_path': node_files_folder,
        f'{csv_loader.get_scope()}.relationship_dir_path': relationship_files_folder,
        f'{csv_loader.get_scope()}.delete_created_directories': True,
        f'{publisher.get_scope()}.node_files_directory': node_files_folder,
        f'{publisher.get_scope()}.relation_files_directory': relationship_files_folder,
        f'{publisher.get_scope()}.neo4j_endpoint': neo4j_endpoint,
        f'{publisher.get_scope()}.neo4j_user': neo4j_user,
        f'{publisher.get_scope()}.neo4j_password': neo4j_password,
        f'{publisher.get_scope()}.neo4j_encrypted': False,
        f'{publisher.get_scope()}.job_publish_tag': 'unique_tag',  # should use unique tag here like {ds}
    })

    return DefaultJob(conf=job_config,
                      task=task,
                      publisher=publisher)


def create_es_publisher_sample_job(elasticsearch_index_alias='table_search_index',
                                   elasticsearch_doc_type_key='table',
                                   model_name='databuilder.models.table_elasticsearch_document.TableESDocument',
                                   entity_type='table',
                                   elasticsearch_mapping=None):
    """
    :param elasticsearch_index_alias:  alias for Elasticsearch used in
                                       amundsensearchlibrary/search_service/config.py as an index
    :param elasticsearch_doc_type_key: name the ElasticSearch index is prepended with. Defaults to `table` resulting in
                                       `table_{uuid}`
    :param model_name:                 the Databuilder model class used in transporting between Extractor and Loader
    :param entity_type:                Entity type handed to the `Neo4jSearchDataExtractor` class, used to determine
                                       Cypher query to extract data from Neo4j. Defaults to `table`.
    :param elasticsearch_mapping:      Elasticsearch field mapping "DDL" handed to the `ElasticsearchPublisher` class,
                                       if None is given (default) it uses the `Table` query baked into the Publisher
    """
    # loader saves data to this location and publisher reads it from here
    extracted_search_data_path = '/var/tmp/amundsen/search_data.json'

    task = DefaultTask(loader=FSElasticsearchJSONLoader(),
                       extractor=Neo4jSearchDataExtractor(),
                       transformer=NoopTransformer())

    # elastic search client instance
    elasticsearch_client = es
    # unique name of new index in Elasticsearch
    elasticsearch_new_index_key = f'{elasticsearch_doc_type_key}_{uuid.uuid4()}'

    job_config = ConfigFactory.from_dict({
        'extractor.search_data.entity_type': entity_type,
        'extractor.search_data.extractor.neo4j.graph_url': neo4j_endpoint,
        'extractor.search_data.extractor.neo4j.model_class': model_name,
        'extractor.search_data.extractor.neo4j.neo4j_auth_user': neo4j_user,
        'extractor.search_data.extractor.neo4j.neo4j_auth_pw': neo4j_password,
        'extractor.search_data.extractor.neo4j.neo4j_encrypted': False,
        'loader.filesystem.elasticsearch.file_path': extracted_search_data_path,
        'loader.filesystem.elasticsearch.mode': 'w',
        'publisher.elasticsearch.file_path': extracted_search_data_path,
        'publisher.elasticsearch.mode': 'r',
        'publisher.elasticsearch.client': elasticsearch_client,
        'publisher.elasticsearch.new_index': elasticsearch_new_index_key,
        'publisher.elasticsearch.doc_type': elasticsearch_doc_type_key,
        'publisher.elasticsearch.alias': elasticsearch_index_alias,
    })

    # only optionally add these keys, so need to dynamically `put` them
    if elasticsearch_mapping:
        job_config.put(f'publisher.elasticsearch.{ElasticsearchPublisher.ELASTICSEARCH_MAPPING_CONFIG_KEY}',
                       elasticsearch_mapping)

    job = DefaultJob(conf=job_config,
                     task=task,
                     publisher=ElasticsearchPublisher())
    return job


if __name__ == "__main__":
    # Uncomment next line to get INFO level logging
    # logging.basicConfig(level=logging.INFO)

    #run_table_column_job('/home/stefan/amundsen/databuilder/example/sample_data/Table_0.csv', '/var/tmp/amundsen/gospode1/nodes/Column_1.csv')
   
    create_dashboard_tables_job().launch()

    create_last_updated_job().launch()

    job_es_table = create_es_publisher_sample_job(
        elasticsearch_index_alias='table_search_index',
        elasticsearch_doc_type_key='table',
        entity_type='table',
        model_name='databuilder.models.table_elasticsearch_document.TableESDocument')
    job_es_table.launch()

    job_es_user = create_es_publisher_sample_job(
        elasticsearch_index_alias='user_search_index',
        elasticsearch_doc_type_key='user',
        model_name='databuilder.models.user_elasticsearch_document.UserESDocument',
        entity_type='user',
        elasticsearch_mapping=USER_INDEX_MAP)
    job_es_user.launch()

    job_es_dashboard = create_es_publisher_sample_job(
        elasticsearch_index_alias='dashboard_search_index',
        elasticsearch_doc_type_key='dashboard',
        model_name='databuilder.models.dashboard_elasticsearch_document.DashboardESDocument',
        entity_type='dashboard',
        elasticsearch_mapping=DASHBOARD_ELASTICSEARCH_INDEX_MAPPING)
    job_es_dashboard.launch()
