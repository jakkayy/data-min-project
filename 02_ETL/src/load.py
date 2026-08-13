"""
Module: 02_ETL/src/load.py
Description: Loads integrated Star Schema DataFrames into SQLite Data Warehouse, PostgreSQL DB, and exports CSV backups.
"""

import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine


def load_to_data_warehouse(
    dw_tables: dict,
    base_dir: str = '.',
    pg_url: str = 'postgresql://postgres:postgrespassword@localhost:5433/used_car_dw',
) -> str:
  """Loads Fact and Dimension DataFrames into SQLite database, PostgreSQL, and exports CSV backups."""
  dw_dir = os.path.join(base_dir, '03_Data_Warehouse')
  os.makedirs(dw_dir, exist_ok=True)

  # 1. SQLite Loading & CSV Export
  db_path = os.path.join(dw_dir, 'used_car_dw.db')
  print(f'[Load] Connecting to SQLite DB at {db_path}...')

  conn = sqlite3.connect(db_path)
  try:
    for table_name, df_table in dw_tables.items():
      df_table.to_sql(table_name, conn, if_exists='replace', index=False)
      print(
          f'  [SQLite Loaded] Table {table_name:20s} -> {len(df_table)} rows'
      )

      # Export CSV backup
      csv_path = os.path.join(dw_dir, f'{table_name}.csv')
      df_table.to_csv(csv_path, index=False)
    conn.commit()
  finally:
    conn.close()

  # 2. PostgreSQL Loading (Try Port 5433 first, fallback to 5432)
  pg_urls_to_try = [
      pg_url,
      'postgresql://postgres:postgrespassword@localhost:5432/used_car_dw',
  ]

  pg_success = False
  for target_url in pg_urls_to_try:
    try:
      engine = create_engine(target_url)
      with engine.connect() as pg_conn:
        print(f'[Load] Connected to PostgreSQL Data Warehouse ({target_url})')
        for table_name, df_table in dw_tables.items():
          df_table.to_sql(
              table_name.lower(), engine, if_exists='replace', index=False
          )
          print(
              f'  [PostgreSQL Loaded] Table {table_name.lower():20s} ->'
              f' {len(df_table)} rows'
          )
      print(
          '[Load] Successfully loaded all Star Schema tables into PostgreSQL'
          ' Data Warehouse!'
      )
      pg_success = True
      break
    except Exception:
      continue

  if not pg_success:
    print(
        '[Load Notice] Could not connect to PostgreSQL Container'
        ' (postgresql://localhost:5433 or 5432).'
    )
    print(
        '  👉 To activate PostgreSQL, run: `docker compose up -d` then re-run'
        ' `python 02_ETL/run_pipeline.py`'
    )

  print(
      f'[Load Completed] Data Warehouse updated at {db_path} and CSV backups'
      ' exported to 03_Data_Warehouse/'
  )
  return db_path


if __name__ == '__main__':
  pass
