from datetime import datetime, timedelta
from airflow import DAG
import pandas as pd
import json
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook 
from bs4 import BeautifulSoup
import requests

# 1) EXTRACT
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://ebook.twointomedia.com/",
}

def get_ebook_data(task_instance):
    base_url = 'https://ebook.twointomedia.com/page/'
    ebooks = []
    seen_links = set()
    page_num = 1
    max_page = 1500
    failed_attempts = 0
    max_failures = 5  # Hentikan jika gagal lebih dari 5 kali berturut-turut
    
    while page_num <= max_page and failed_attempts < max_failures:
        try:
            response = requests.get(base_url + str(page_num), headers=headers)
            response.raise_for_status()  # Memastikan request sukses
            html_text = response.text
        except requests.exceptions.RequestException as e:
            print(f"Gagal mengambil data dari halaman {page_num}: {e}")
            failed_attempts += 1
            continue  # Lewati halaman ini, coba halaman berikutnya
        
        soup = BeautifulSoup(html_text, 'lxml')
        container = soup.find_all('div', class_='smallcard')
        if not container:
            print(f"Tidak ada data di halaman {page_num}. Menghentikan proses.")
            break
        
        for buku in container:
            judul = buku.find('h2', class_='entry-title-mini')
            penulis = buku.find('div', class_='entry-author')
            link = buku.find('a', href=True)
        
            if judul and penulis and link:
                ebook_link = link['href']
                if ebook_link not in seen_links:
                    ebooks.append({
                        'Judul': judul.text.strip(),
                        'Penulis': penulis.text.strip(),
                        'Link': ebook_link
                    })
                    seen_links.add(ebook_link)
        
        page_num += 1
        failed_attempts = 0  # Reset jika sukses
        
    if page_num > max_page:
        print(f"Berhenti karena mencapai batas maksimal halaman ({max_page})")

# 2) TRANSFORM        
    df = pd.DataFrame(ebooks)
    df.drop_duplicates(subset="Link", inplace=True)
    
    task_instance.xcom_push(key='ebook_data', value=json.dumps(df.to_dict('records')))

# 3) LOAD
def insert_ebook_data_into_postgres(task_instance):
    ebook_data = json.loads(task_instance.xcom_pull(key='ebook_data', task_ids='fetch_ebook_data'))
    if not ebook_data:
        print("Peringatan: Data ebook kosong. Tidak ada data yang akan dimasukkan.")
        return
    
    postgres_hook = PostgresHook(postgres_conn_id='ebooks_connection')
    
    insert_query = """
    INSERT INTO ebooks (judul, penulis, link)
    VALUES (%s, %s, %s)
    """
    check_query = """
    SELECT link FROM ebooks WHERE link = %s;
    """
    
    for ebook in ebook_data:
        existing = postgres_hook.get_records(check_query, parameters=(ebook['Link'],))
        if not existing:
            postgres_hook.run(insert_query, parameters=(ebook['Judul'], ebook['Penulis'], ebook['Link']))

# 4) DAG Definition
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'ebook_scraping_pipeline',
    default_args=default_args,
    description='Pipeline untuk scraping data ebook dan menyimpan ke PostgreSQL',
    schedule_interval=timedelta(days=7), 
    catchup=False,
    max_active_runs=1,
    tags=['ebooks'],
)

fetch_ebook_data_task = PythonOperator(
    task_id='fetch_ebook_data',
    python_callable=get_ebook_data,
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
        link TEXT UNIQUE
    );
    """,
    dag=dag,
)

insert_ebook_data_task = PythonOperator(
    task_id='insert_into_postgres',
    python_callable=insert_ebook_data_into_postgres,
    dag=dag,
)

create_table_task >> fetch_ebook_data_task >> insert_ebook_data_task
