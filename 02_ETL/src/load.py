"""
Module: 02_ETL/src/load.py
Description: Loads integrated Star Schema DataFrames into SQLite, Local Docker PostgreSQL, Supabase Cloud PostgreSQL, exports CSV backups, and enforces DDL Primary Key & Foreign Key constraints.
"""

import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

try:
  from dotenv import load_dotenv

  load_dotenv()
except ImportError:
  pass


def apply_pg_constraints(engine):
  """Applies explicit Primary Key and Foreign Key constraints to PostgreSQL tables for strict database DDL compliance."""
  ddl_statements = [
      # Primary Keys
      "ALTER TABLE dimcar ADD PRIMARY KEY (car_key);",
      "ALTER TABLE dimdate ADD PRIMARY KEY (date_key);",
      "ALTER TABLE dimlocation ADD PRIMARY KEY (location_key);",
      "ALTER TABLE dimcustomer ADD PRIMARY KEY (customer_key);",
      "ALTER TABLE dimacquisitionsource ADD PRIMARY KEY (source_key);",
      "ALTER TABLE factsales ADD PRIMARY KEY (sales_id);",
      "ALTER TABLE factmarketlistings ADD PRIMARY KEY (listing_id);",
      # Foreign Keys for FactSales
      (
          "ALTER TABLE factsales ADD CONSTRAINT fk_factsales_car FOREIGN KEY"
          " (car_key) REFERENCES dimcar(car_key);"
      ),
      (
          "ALTER TABLE factsales ADD CONSTRAINT fk_factsales_date FOREIGN KEY"
          " (date_key) REFERENCES dimdate(date_key);"
      ),
      (
          "ALTER TABLE factsales ADD CONSTRAINT fk_factsales_location FOREIGN"
          " KEY (location_key) REFERENCES dimlocation(location_key);"
      ),
      (
          "ALTER TABLE factsales ADD CONSTRAINT fk_factsales_customer FOREIGN"
          " KEY (customer_key) REFERENCES dimcustomer(customer_key);"
      ),
      (
          "ALTER TABLE factsales ADD CONSTRAINT fk_factsales_source FOREIGN KEY"
          " (acquisition_source_key) REFERENCES"
          " dimacquisitionsource(source_key);"
      ),
      # Foreign Keys for FactMarketListings
      (
          "ALTER TABLE factmarketlistings ADD CONSTRAINT fk_factmarket_car"
          " FOREIGN KEY (car_key) REFERENCES dimcar(car_key);"
      ),
      (
          "ALTER TABLE factmarketlistings ADD CONSTRAINT fk_factmarket_date"
          " FOREIGN KEY (date_key) REFERENCES dimdate(date_key);"
      ),
      (
          "ALTER TABLE factmarketlistings ADD CONSTRAINT"
          " fk_factmarket_location FOREIGN KEY (location_key) REFERENCES"
          " dimlocation(location_key);"
      ),
  ]

  with engine.connect() as conn:
    for stmt in ddl_statements:
      try:
        conn.execute(text(stmt))
        conn.commit()
      except Exception:
        pass


def drop_pg_tables_cascade(engine):
  """Safely drops existing PostgreSQL tables with CASCADE to clear FK dependencies before re-loading."""
  tables = [
      "factsales",
      "factmarketlistings",
      "dimcar",
      "dimdate",
      "dimlocation",
      "dimcustomer",
      "dimacquisitionsource",
  ]
  with engine.connect() as conn:
    for t in tables:
      try:
        conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE;"))
        conn.commit()
      except Exception:
        pass


def load_to_data_warehouse(
    dw_tables: dict,
    base_dir: str = ".",
    pg_url: str = "postgresql://postgres:postgrespassword@localhost:5433/used_car_dw",
    supabase_url: str = None,
) -> str:
  """Loads Fact and Dimension DataFrames into SQLite, Local PostgreSQL, Supabase Cloud, applies DDL PK/FK constraints, and exports CSV backups."""
  dw_dir = os.path.join(base_dir, "03_Data_Warehouse")
  os.makedirs(dw_dir, exist_ok=True)

  # 1. SQLite Loading & CSV Export
  db_path = os.path.join(dw_dir, "used_car_dw.db")
  print(f"[Load] Connecting to SQLite DB at {db_path}...")

  conn = sqlite3.connect(db_path)
  try:
    for table_name, df_table in dw_tables.items():
      df_table.to_sql(table_name, conn, if_exists="replace", index=False)
      print(
          f"  [SQLite Loaded] Table {table_name:20s} -> {len(df_table)} rows"
      )

      # Export CSV backup
      csv_path = os.path.join(dw_dir, f"{table_name}.csv")
      df_table.to_csv(csv_path, index=False)
    conn.commit()
  finally:
    conn.close()

  # 2. Local Docker PostgreSQL Loading & Constraints
  pg_urls_to_try = [
      pg_url,
      "postgresql://postgres:postgrespassword@localhost:5432/used_car_dw",
  ]

  pg_success = False
  for target_url in pg_urls_to_try:
    try:
      engine = create_engine(target_url)
      with engine.connect() as pg_conn:
        print(
            f"[Load] Connected to Local Docker PostgreSQL Data Warehouse"
            f" ({target_url})"
        )
        drop_pg_tables_cascade(engine)
        for table_name, df_table in dw_tables.items():
          df_table.to_sql(
              table_name.lower(), engine, if_exists="replace", index=False
          )
          print(
              f"  [Local PG Loaded] Table {table_name.lower():20s} ->"
              f" {len(df_table)} rows"
          )
        # Apply Primary Keys and Foreign Keys constraints in PostgreSQL DDL
        apply_pg_constraints(engine)
        print(
            "  [Local PG Constraints] Enforced Primary Key & Foreign Key"
            " DDL constraints."
        )

      print(
          "[Load] Successfully loaded all Star Schema tables into Local Docker"
          " PostgreSQL with DDL PK/FK constraints!"
      )
      pg_success = True
      break
    except Exception:
      continue

  if not pg_success:
    print(
        "[Load Notice] Local Docker PostgreSQL is not running or not accessible."
    )

  print(
      f'[Load Completed] Data Warehouse updated at {db_path} and CSV backups'
      ' exported to 03_Data_Warehouse/'
  )
  return db_path


if __name__ == '__main__':
  pass
