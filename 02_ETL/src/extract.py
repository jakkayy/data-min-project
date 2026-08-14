"""
Module: 02_ETL/src/extract.py
Description: Ingests raw data from 3+ Data Sources including multi-file scraped web data series with raw scraper column mapping.
"""

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
  """Ingests raw data from multi-file web scraped series, US sales, and spec datasets."""
  raw_dir = os.path.join(base_dir, '01_Raw_Data')

  # Data Source 1: Multi-file One2car Web Scraped Series (3 Raw Scraped Files)
  one2car_folder = os.path.join(raw_dir, 'one2car')
  one2car_files = sorted(glob.glob(os.path.join(one2car_folder, 'one2car-11-*.csv')))
  
  if len(one2car_files) > 0:
    print(f'[Extract] Ingesting & Standardizing {len(one2car_files)} raw One2Car scraped period files...')
    df_list = [standardize_scraped_columns(pd.read_csv(f)) for f in one2car_files]
    df_one2car = pd.concat(df_list, ignore_index=True)
  else:
    one2car_path = os.path.join(one2car_folder, 'one2car_data.csv')
    print(f'[Extract] Ingesting One2Car raw data from {one2car_path}...')
    df_one2car = pd.read_csv(one2car_path)

  # Data Source 2: US Sales Raw Data
  us_sales_path = os.path.join(raw_dir, 'us-usecar', 'used_car_sales.csv')
  print(f'[Extract] Ingesting US Sales raw data from {us_sales_path}...')
  df_us_sales = pd.read_csv(us_sales_path)

  # Data Source 3: Spec Datasets (Multi-file series)
  spec_path1 = os.path.join(raw_dir, 'usecar-dataset', 'used_car_dataset.csv')
  spec_path2 = os.path.join(raw_dir, 'usecar-dataset', 'used_cars_dataset_2.csv')
  print('[Extract] Ingesting and consolidating Spec datasets (Multi-file series)...')
  df_spec1 = pd.read_csv(spec_path1)
  df_spec2 = pd.read_csv(spec_path2)
  df_spec = pd.concat([df_spec1, df_spec2], ignore_index=True)

  print(
      f'[Extract Completed] One2car (Multi-file Scraped): {len(df_one2car)} rows, '
      f'US Sales: {len(df_us_sales)} rows, Spec Combined: {len(df_spec)} rows'
  )

  return df_one2car, df_us_sales, df_spec


if __name__ == '__main__':
  pass
