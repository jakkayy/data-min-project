"""
Module: 02_ETL/src/load.py
Description: Loads integrated Star Schema DataFrames into SQLite, Local Docker PostgreSQL, Supabase Cloud PostgreSQL, and exports CSV backups.
"""

import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

try:
  from dotenv import load_dotenv

  load_dotenv()
except ImportError:
  pass


def load_to_data_warehouse(
    dw_tables: dict,
    base_dir: str = '.',
    pg_url: str = 'postgresql://postgres:postgrespassword@localhost:5433/used_car_dw',
    supabase_url: str = None,
) -> str:
  """Loads Fact and Dimension DataFrames into SQLite, Local PostgreSQL, Supabase Cloud, and exports CSV backups."""
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

  # 2. Local Docker PostgreSQL Loading
  pg_urls_to_try = [
      pg_url,
      'postgresql://postgres:postgrespassword@localhost:5432/used_car_dw',
  ]

  pg_success = False
  for target_url in pg_urls_to_try:
    try:
      engine = create_engine(target_url)
      with engine.connect() as pg_conn:
        print(
            f'[Load] Connected to Local Docker PostgreSQL Data Warehouse'
            f' ({target_url})'
        )
        for table_name, df_table in dw_tables.items():
          df_table.to_sql(
              table_name.lower(), engine, if_exists='replace', index=False
          )
          print(
              f'  [Local PG Loaded] Table {table_name.lower():20s} ->'
              f' {len(df_table)} rows'
          )
      print(
          '[Load] Successfully loaded all Star Schema tables into Local Docker'
          ' PostgreSQL!'
      )
      pg_success = True
      break
    except Exception:
      continue

  if not pg_success:
    print(
        '[Load Notice] Could not connect to Local Docker PostgreSQL Container'
        ' (localhost:5433/5432).'
    )

  # 3. Supabase Cloud PostgreSQL Loading (if SUPABASE_URL is provided or set in env)
  target_supabase = supabase_url or os.environ.get('SUPABASE_DB_URL')
  if (
      target_supabase
      and 'YOUR_PASSWORD_HERE' not in target_supabase
      and '[YOUR-PASSWORD]' not in target_supabase
  ):
    try:
      print(
          f'[Load] Connecting to Supabase Cloud PostgreSQL Data Warehouse...'
      )
      sp_engine = create_engine(target_supabase)
      with sp_engine.connect() as sp_conn:
        for table_name, df_table in dw_tables.items():
          df_table.to_sql(
              table_name.lower(), sp_engine, if_exists='replace', index=False
          )
          print(
              f'  [Supabase Cloud Loaded] Table {table_name.lower():20s} ->'
              f' {len(df_table)} rows'
          )
      print(
          '\n🎉 [Supabase Cloud] Successfully loaded all Star Schema tables'
          ' into Supabase Cloud Data Warehouse!'
      )
    except Exception as e:
      print(f'❌ [Supabase Notice] Failed to load to Supabase Cloud ({e}).')

  print(
      f'[Load Completed] Data Warehouse updated at {db_path} and CSV backups'
      ' exported to 03_Data_Warehouse/'
  )
  return db_path


if __name__ == '__main__':
  pass
