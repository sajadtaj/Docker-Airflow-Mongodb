from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from pymongo import MongoClient
import requests
import json
from pytz import timezone
IRST = timezone('Asia/Tehran')

# Set Headers and Urls
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53'}
url     = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/1"

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

# Define DAG parameters
default_args = {
    'owner': 'Xirano',  # Replace with your email
}

# Set DAG ID and schedule
dag = DAG(
    dag_id       = 'Crawler',
    default_args = default_args,
    start_date   = days_ago(1),  # Adjust as needed
    # Schedule to run between 9 AM and 3 PM on Saturday to Wednesday
    schedule_interval='* * * * *',  # Base for cron expression
    dagrun_timeout=timedelta(seconds=50),  # Adjust if needed
)

task = PythonOperator(
    task_id='your_task_id',
    provide_context=True,  # Pass context to function if needed
    python_callable=scrape_and_store,
    dag=dag,
)