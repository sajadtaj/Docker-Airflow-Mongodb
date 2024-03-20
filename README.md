## Setup __Airflow__ and __MongoDB__ to Crawl TSETMC Data in 12 Steps

### Description
This project involves setting up a Docker Compose environment with Airflow and MongoDB to crawl TSETMC data efficiently.

### Prerequisites
- Docker installed on your machine
- Basic understanding of Docker Compose
- Access to TSETMC data source

# Setup Instructions

## Start By Airflow
1. **Fetching docker-compose.yaml :**
+   To deploy Airflow on Docker Compose, you should fetch docker-compose.yaml.


   ```bash
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.8.3/docker-compose.yaml'
   ```
+   This file contains several service definitions:
   
+   airflow-scheduler - The scheduler monitors all tasks + and DAGs, then triggers the task instances once +    their dependencies are complete.
   
+   *airflow-webserver* - The webserver is available at http://localhost:8080.
  
+   *airflow-worker* - The worker that executes the tasks +  given by the scheduler.
   
+   *airflow-triggerer* - The triggerer runs an event loop + for deferrable tasks.
   
+   *airflow-init* - The initialization service.
   
+   *postgres* - The database.
   
+   *redis* - The redis - broker that forwards messages from scheduler to worker.

2. **Some directories in the container are mounted, which means that their contents are synchronized between your computer and the container :**
```bash
mkdir -p ./dags ./logs ./plugins ./config
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

+   ./dags - you can put your DAG files here.

+   ./logs - contains logs from task execution and scheduler.

+   ./config - you can add custom log parser or add airflow_local_settings.py to configure cluster policy.

+   ./plugins - you can put your custom plugins here.

3. **Initialize the database :**
```bash
docker compose up airflow-init
```

## Continue By Mongo:

4. **Add mongo docker compose config to your `docker-compose.yml` :**
```docker-compose.yml
# in docker-compose.yml

services

  db:
    container_name: mongoDatabase
    image: mongo:4.2
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_DATABASE=auth
      - MONGO_INITDB_ROOT_PASSWORD=pass
    networks: 
      - mongo-compose-network
    ports:
      - '27017:27017'
    volumes: 
      - ./data:/data/db
  
  mongo-express:
    container_name: mongo-express
    image: mongo-express
    depends_on:
      - db
    networks: 
      - mongo-compose-network
    environment:
      - ME_CONFIG_MONGODB_SERVER=mongoDatabase
      - ME_CONFIG_MONGODB_ADMINUSERNAME=admin
      - ME_CONFIG_MONGODB_ADMINPASSWORD=pass
      - ME_CONFIG_BASICAUTH_USERNAME=admin
      - ME_CONFIG_BASICAUTH_PASSWORD=tribes
    ports:
      - '8081:8081'
    volumes: 
      - ./data:/data/db 

networks:
  mongo-compose-network:

```

5. **Add `mongo-compose-network` To Other Airflow Services :**
For all Services:
```
# in docker-compose.yml

services
  postgres:
      networks: 
        - mongo-compose-network
  redis:
      networks: 
        - mongo-compose-network
  airflow-webserver:
      networks: 
        - mongo-compose-network
  airflow-scheduler:
      networks: 
        - mongo-compose-network
  airflow-worker:
      networks: 
        - mongo-compose-network
  airflow-triggerer:
      networks: 
        - mongo-compose-network
  airflow-init:
      networks: 
        - mongo-compose-network
  airflow-cli:
      networks: 
        - mongo-compose-network
  flower:
      networks: 
        - mongo-compose-network
```

6. **For run some python function in DAGs you need install some packages :**
```bash
mkdir ./docker_airflow
```
7. **in `docker_airflow` direct create Dockerfile :**

```DockerFile
# in DockerFile

# Use the official Airflow image
FROM apache/airflow:2.8.3

# Copy requirements.txt to the container
COPY requirements.txt /requirements.txt

# Install additional Python packages
RUN pip install --no-cache-dir -r /requirements.txt

```
8. **Add `requirements.txt` in same folder :**
```requirements.txt
# in requirements.txt

pymongo==4.6.2
requests==2.31.0
```

9. **Add this address to `airflow-triggerer` service :**
>>    build: \
>>      context: ./dockerfile_airflow
```bash
# in docker-compose.yml

  airflow-triggerer:
    <<: *airflow-common
    command: triggerer
    container_name: Triggerer
    build:
      context: ./dockerfile_airflow
    healthcheck:
      test: ["CMD-SHELL", 'airflow jobs check --job-type TriggererJob --hostname "$${HOSTNAME}"']
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully
    networks: 
      - mongo-compose-network

```
10. **Set DAGs in `./dags`**
+   Create Python file -> Crawler.py
+ + First Call packages:
```python
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from pymongo import MongoClient  # For coonect to mongo db
import requests                  # for work by API And Crawl 
import json
from pytz import timezone        # for set timezone
IRST = timezone('Asia/Tehran')
```
+ + Set Headers and Urls :

```python
# Set Headers and Urls
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53'}
url     = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/1"
```
+ + define Crawler function :
```python
def scrape_and_store(**kwargs):
    try:
        #Start Crawl
        response        = requests.get(url, headers=headers)
        # instrumentOptMarketWatch is list
        shareholders    = response.json()['instrumentOptMarketWatch']
        connection_string = 'mongodb://admin:pass@mongoDatabase:27017'

        client = MongoClient(connection_string)

        # DB config
        db = client['options']
        collection = db['options_snap']
        data_to_store = shareholders # Replace with the actual data
        result =collection.insert_many(data_to_store)

        #Attach Time of insert
        collection.update_many(
            {"_id": {"$in": result.inserted_ids}},
            {"$set": {  "time": datetime.now(IRST).strftime("%Y-%m-%d"),
                        "date": datetime.now(IRST).strftime("%H:%M:%S")
                    }
            }
        )
    except Exception as e:
        print('~~~~'*10,'\n','the error acuire in crawl data from TSETMS',e)
```
**connection_string** :\
`mongodb: admin:pass@mongoDatabase:27017`

`admin` : *password* Set in docker compose  \
`pass`  : *username* Set in docker compose  \
`mongoDatabase` : *host* or container name Set in docker compose \
`27017` : *port* Set in docker compose

+ + Define DAG parameters :
```python

default_args = {
    'owner': 'Xirano',  # Replace with your email
}

# Set DAG ID and schedule
dag = DAG(
    dag_id       = 'Crawler',
    default_args = default_args,
    start_date   = days_ago(1),  # Adjust as needed
    schedule_interval='* * * * *',  # Base for cron expression
    dagrun_timeout=timedelta(seconds=50),  # Adjust if needed
)

task = PythonOperator(
    task_id='your_task_id',
    provide_context=True,  # Pass context to function if needed
    python_callable=scrape_and_store,
    dag=dag,
)

```

11. **Build and Start Docker Containers:**
   ```bash
   docker-compose up --build
   ```

12. **Access Airflow UI:**
   - Open a web browser and navigate to `http://localhost:8080` to access the Airflow UI.
   - Configure necessary connections and variables in Airflow for MongoDB.

13. **Run the Airflow DAG:**
   - Initiate the Airflow DAG to commence crawling TSETMC data.

### Additional Notes
- Customize the Airflow DAG as per your specific requirements for crawling TSETMC data effectively.
- Monitor Airflow tasks and MongoDB database for successful data crawling operations.

### References
- Docker Compose Documentation: [https://docs.docker.com/compose/](https://docs.docker.com/compose/)
- Airflow Documentation: [https://airflow.apache.org/docs/](https://airflow.apache.org/docs/)
- MongoDB Documentation: [https://docs.mongodb.com/](https://docs.mongodb.com/)
