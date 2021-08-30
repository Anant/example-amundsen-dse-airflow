# Example Amundsen/DSE + Airflow
This project is ment to demonstrate integrating Amundsen with DSE and Airflow using Docker

## Software involved
- docker (docker-compose)
- Amundsen
- Datastax Enterprise Cassandra
- Airflow

## Requirements
- docker, docker-compose

## 1. Run Amundsen
Full Installation: https://github.com/amundsen-io/amundsen/blob/main/docs/installation.md
The following instructions are for setting up a version of Amundsen using Docker.

1. Make sure you have at least 3GB available to docker. Install `docker` and  `docker-compose`.
2. Clone [this repo](https://github.com/amundsen-io/amundsen) and its submodules by running:
   ```bash
   $ git clone --recursive https://github.com/amundsen-io/amundsen.git
   ```
3. Enter the cloned directory and run below:
    ```bash
    # For Neo4j Backend
    $ docker-compose -f docker-amundsen.yml up

    # For Atlas
    $ docker-compose -f docker-amundsen-atlas.yml up
    ```
    If it's your first time, you may want to proactively go through [troubleshooting](#troubleshooting) steps, especially the first one related to heap memory for ElasticSearch and Docker engine memory allocation (leading to Docker error 137).

## 2. Run Airflow
   Full Installation: https://airflow.apache.org/docs/apache-airflow/stable/start/docker
   ```bash
   cd Airflow
   docker-compose up airflow-init
   docker-compose up
   ```

## 3. Populate DSE/Postgres with data
   Cassandra
   ```bash
   docker exec -it airfloworiginal_dse1_1 cqlsh
   ```
   ```bash
   CREATE KEYSPACE demo WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
   USE demo;
   CREATE TABLE User_type(
   user_type INT,
   user_ID UUID,
   primary key(user_ID));
   ```
   Postgres
   ```bash
   docker exec -it airfloworiginal_postgres_1 psql -U airflow
   ```
   ```bash
   \dt
   CREATE TABLE accounts (
	user_id serial PRIMARY KEY,
	username VARCHAR ( 50 ) UNIQUE NOT NULL,
	password VARCHAR ( 50 ) NOT NULL,
	email VARCHAR ( 255 ) UNIQUE NOT NULL,
	created_on TIMESTAMP NOT NULL,
        last_login TIMESTAMP 
  );  
   ```         
   

## 4. Run the scripts to Extract and Publish    
 Transfer the scripts into the /amundsen/databuilder/example/scripts
 ```bash
   python cassandra_data_loader.py
   python cassaandra_no4j_es_loader.py 
 ```

## 5. Install requirements  
 In the airflow_worker CLI install the dependencies
 ```bash
   cd dags/req
   pip install -r requirements.txt
   pip install cassandra-driver
 ```
## 6. Configure the DAG
In the /dags/dag.py file you need to configure the connections for Cassandra/Neo4j and ES
1. you should see the network
 ```bash
   docker network ls
 ``` 
 example:
 Network ID   amundsen_amundsennet      bridge    local
2. With this command you should be able to see all containers running on this network   
 ```bash
   docker network inspect amundsen_amundsennet
 ```
3. Get the IPv4Address for this 3 containers Example:
 ```bash
                "Name": "airfloworiginal_dse1_1",
                "EndpointID": "3e3e13d95457c500dcf10660f0e9796b08dff4190f5893b3d1443dbff771a3f8",
                "MacAddress": "02:42:ac:15:00:09",
                "IPv4Address": "172.21.0.9/16",
                "IPv6Address": "" 

               "Name": "es_amundsen",
                "EndpointID": "dfa0fc9580d97309516add337fc4b5aa1df8e8439b7e075c28c0d3d6a990a8c4",
                "MacAddress": "02:42:ac:15:00:02",
                "IPv4Address": "172.21.0.2/16",
                "IPv6Address": ""

               "Name": "neo4j_amundsen",
                "EndpointID": "c044909c033c8f82172be6c265a70e0e077825fb1b01c960a9fd5d0373f9508f",
                "MacAddress": "02:42:ac:15:00:03",
                "IPv4Address": "172.21.0.3/16",
                "IPv6Address": ""         
 ```
## 7. Edit the DAG file 
Change the file on these 3 lines 
 1. On line 95:
 ```bash
   'extractor.cassandra.{}'.format(CassandraExtractor.IPS_KEY): ['172.21.0.9'],
 ```
 2. On line 56:
 ```bash
   NEO4J_ENDPOINT = f'bolt://172.21.0.3:{neo_port}'
 ```
 2. On line 51:
 ```bash
   {'host': '172.21.0.2', 'port': es_port},
 ```   