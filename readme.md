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
   ```bash
   cd Airflow
   docker-compose up airflow-init
   docker-compose up
   ```

## 3. Populate DSE with data
   ```bash
   docker exec -it airfloworiginal_dse1_1 cqlsh
   ```

## 4. Run the scripts to Extract and Publish    
 Transfer the scripts into the /amundsen/databuilder/example/scripts
 ```bash
   python cassandra_data_loader.py
   python cassaandra_no4j_es_loader.py 
 ```
