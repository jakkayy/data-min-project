"""
Module: 02_ETL/src/extract.py
Description: Ingests raw data from 3 Data Sources: Kaidee Auto (JSON), One2car (Multi-file CSVs), and US Sales (CSV Log).
"""

import json
import os
import glob
import pandas as pd


def standardize_scraped_columns(df: pd.DataFrame) -> pd.DataFrame:
  """Standardizes raw Web Scraper column names (data, data2, data3...) to domain names."""
  rename_map = {
      'data': 'car_title',
      'data2': 'description',
      'data3': 'mileage',
      'data4': 'location',
      'data6': 'car_model',
      'data16': 'transmission',
  }
  return df.rename(columns=rename_map)


def extract_raw_data(base_dir: str = '.') -> tuple:
  """Ingests raw data from Kaidee Auto JSON, One2car Multi-file series, and US Sales dataset."""
  raw_dir = os.path.join(base_dir, '01_Raw_Data')

  # Data Source 1: Kaidee Auto JSON Data Source
  kaidee_json_path = os.path.join(raw_dir, 'kaidee', 'kaidee_cars_detail.json')
  print(f'[Extract] Ingesting Data Source 1: Kaidee Auto JSON from {kaidee_json_path}...')
  with open(kaidee_json_path, 'r', encoding='utf-8') as f:
    df_kaidee = pd.DataFrame(json.load(f))

  # Data Source 2: Multi-file One2car Web Scraped Series
  one2car_folder = os.path.join(raw_dir, 'one2car')
  one2car_files = sorted(glob.glob(os.path.join(one2car_folder, 'one2car-11-*.csv')))
  
  if len(one2car_files) > 0:
    print(f'[Extract] Ingesting & Standardizing Data Source 2: {len(one2car_files)} raw One2Car scraped period files...')
    df_list = [standardize_scraped_columns(pd.read_csv(f)) for f in one2car_files]
    df_one2car = pd.concat(df_list, ignore_index=True)
  else:
    one2car_path = os.path.join(one2car_folder, 'one2car_data.csv')
    print(f'[Extract] Ingesting One2Car raw data from {one2car_path}...')
    df_one2car = pd.read_csv(one2car_path)

  # Data Source 3: US Sales Raw Data
  us_sales_path = os.path.join(raw_dir, 'us-usecar', 'used_car_sales.csv')
  print(f'[Extract] Ingesting Data Source 3: US Sales raw data from {us_sales_path}...')
  df_us_sales = pd.read_csv(us_sales_path)

  print(
      f'[Extract Completed] Kaidee Auto JSON: {len(df_kaidee):,} rows | '
      f'One2car Multi-file: {len(df_one2car):,} rows | US Sales: {len(df_us_sales):,} rows'
  )

  return df_kaidee, df_one2car, df_us_sales


if __name__ == '__main__':
  pass
