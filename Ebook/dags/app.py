# Requirements

from datetime import datetime, timedelta
from airflow import DAG
import pandas as pd
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook 
from bs4 import BeautifulSoup
import requests

# 1) EXTRACT
        
def get_ebook_data(jumlah_buku, ti):
    base_url = 'https://ebook.twointomedia.com/page/'
    ebooks = []
    telah_dilihat = set()
    page_num = 1
    
    while len(ebooks) < jumlah_buku:
        html_text = requests.get(base_url + str(page_num)).text
        soup = BeautifulSoup(html_text, 'lxml')
        container = soup.find_all('div', class_='smallcard')
        for buku in container:
            judul = buku.find('h2', class_='entry-title-mini')
            penulis = buku.find('div', class_='entry-author')
            link = buku.find('a', href = True)
        
            if judul and penulis and link:
                judul_ebook = judul.text.strip()
                
                if judul_ebook in telah_dilihat:
                    telah_dilihat.add(judul_ebook)
                    ebooks.append({
                    'Judul': judul.text.strip(),
                    'Penulis': penulis.text.strip(),
                    'Link': link['href']
                })
        
        page_num += 1

    # 2) TRANSFORM 
           
    ebooks = ebooks[:jumlah_buku]
    
    df = pd.DataFrame(ebooks)
    df.drop_duplicates(subset="Judul", inplace=True)
    
    ti.xcom_push(key='ebook_data', value=df.to_dict('records'))

# 3) LOAD

def insert_ebook_data_into_postgres(ti):
    ebook_data = ti.xcom_pull(key='ebook_data', task_ids='fetch_ebook_data')
    if not ebook_data:
        raise ValueError("Data ebook tidak ditemukan")
    
    postgres_hook = PostgresHook(postgres_conn_id='ebooks_connection')
    insert_query = """
    INSERT INTO ebooks (judul, penulis, link)
    VALUES (%s, %s, %s)
    """
    for ebook in ebook_data:
        postgres_hook.run(insert_query, parameters=(ebook['Judul'], ebook['Penulis'], ebook['Link']))

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2020, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fetch_and_store_ebooks',
    default_args=default_args,
    description='A simple DAG to fetch ebook data from ebook.twointomedia.com and store it in Postgres',
    schedule_interval=timedelta(days=1),
)

fetch_ebook_data_task = PythonOperator(
    task_id='fetch_ebook_data',
    python_callable=get_ebook_data,
    op_args=[50],  # Number of ebooks to fetch
    dag=dag,
)

create_table_task = PostgresOperator(
    task_id='create_table',
    postgres_conn_id='ebooks_connection',
    sql="""
    CREATE TABLE IF NOT EXISTS public.ebooks (
        id SERIAL PRIMARY KEY,
        judul TEXT NOT NULL,
        penulis TEXT,
        link TEXT
    );
    """,
    dag=dag,
)

insert_ebook_data_task = PythonOperator(
    task_id='insert_ebook_data',
    python_callable=insert_ebook_data_into_postgres,
    dag=dag,
)

fetch_ebook_data_task >> create_table_task >> insert_ebook_data_task