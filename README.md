# ETL Data Pipeline using Apache Airflow

## Dokumen Ringkasan Proyek: Membangun ETL Pipeline e-books Menggunakan Apache Airflow

Project ini berfokus pada pembuatan ETL pipeline sederhana menggunakan Apache Airflow. Pipeline ini mengekstrak data ebook dari website, melakukan transformasi untuk membersihkan data, dan memuatnya ke dalam database PostgreSQL.

## ETL Pipeline:
1. Extract: Data diambil melalui scraping dari situs https://ebook.twointomedia.com/.
2. Transform: Data dibersihkan dan diproses untuk analisis.
3. Load: Data dimuat ke database PostgreSQL.

## Apache Airflow: 
Digunakan untuk mengelola workflow melalui DAGs (Directed Acyclic Graphs), memastikan otomatisasi dan penjadwalan pipeline.

## Docker:
Mempermudah instalasi dan pengelolaan komponen seperti Airflow, PostgreSQL, dan PGAdmin.

## Programming Language: 
Python untuk logika pipeline dan SQL untuk query database.

## Implementasi

1. Instalasi lingkungan virtual Python.
2. Pengaturan Docker untuk menjalankan Airflow dan PostgreSQL.
3. Konfigurasi koneksi Airflow ke database PostgreSQL.
4. Pembuatan dan eksekusi DAG untuk menjalankan proses ETL.
5. Verifikasi hasil data di database PostgreSQL.
