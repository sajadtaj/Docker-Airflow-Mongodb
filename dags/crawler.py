from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from pymongo import MongoClient
import requests
import json
from pytz import timezone

# Get Tehran Time Zone
IRST = timezone('Asia/Tehran')

# Set Headers and Urls
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53'}
url = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/1"

# default_args = {
#     'owner': 'airflow',
#     'depends_on_past': False,
#     'start_date': datetime(2024, 1, 1),
#     'retries': 1,
#     'retry_delay': timedelta(minutes=5),
# }

# dag = DAG(
#     'my_dag',
#     default_args=default_args,
#     description='My DAG for web scraping and MongoDB',
#     schedule_interval='*/1 9-15 * 1-4,6',  # every 1 minute, Monday to Thursday and Saturday, between 9 am and 3 pm
# )

def scrape_and_store(**kwargs):
    # try:
    #Start Crawl
    response        = requests.get(url, headers=headers)
    # instrumentOptMarketWatch is list
    shareholders    = response.json()['instrumentOptMarketWatch']
    connection_string = 'mongodb://admin:pass@localhost:27017'
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
    # except Exception as e:
    #     print('~~~~'*10,'\n','the error acuire in crawl data from TSETMS',e)

# scrape_task = PythonOperator(
#     task_id='scrape_and_store',
#     python_callable=scrape_and_store,
#     provide_context=True,
#     dag=dag,
# )

with DAG("my_dag",
  start_date=datetime(2023, 1 ,1), 
  schedule_interval='@daily', 
  catchup=False):

  Crawl = PythonOperator(
      task_id=f"Options_Crawler",
      trigger_rule='all_success',
      python_callable=scrape_and_store
  )

Crawl