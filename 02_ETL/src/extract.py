"""
Module: 02_ETL/src/extract.py
Description: Ingests raw data from 01_Raw_Data directory for all 3 data sources.
"""

import os
import pandas as pd


def extract_raw_data(base_dir: str = '.'):
  """Extracts raw datasets from 01_Raw_Data directory."""
  one2car_path = os.path.join(
      base_dir, '01_Raw_Data', 'one2car', 'one2car_data.csv'
  )
  us_sales_path = os.path.join(
      base_dir, '01_Raw_Data', 'us-usecar', 'used_car_sales.csv'
  )
  spec1_path = os.path.join(
      base_dir, '01_Raw_Data', 'usecar-dataset', 'used_car_dataset.csv'
  )
  spec2_path = os.path.join(
      base_dir, '01_Raw_Data', 'usecar-dataset', 'used_cars_dataset_2.csv'
  )

  print('[Extract] Ingesting One2Car raw data...')
  df_one2car = pd.read_csv(one2car_path)

  print('[Extract] Ingesting US Sales raw data...')
  df_us_sales = pd.read_csv(us_sales_path)

  print('[Extract] Ingesting and consolidating Spec datasets...')
  df_spec1 = pd.read_csv(spec1_path)
  df_spec2 = pd.read_csv(spec2_path)
  df_spec_combined = pd.concat([df_spec1, df_spec2], ignore_index=True)

  print(f'[Extract Completed] One2car: {len(df_one2car)} rows, US Sales: {len(df_us_sales)} rows, Spec Combined: {len(df_spec_combined)} rows')
  return df_one2car, df_us_sales, df_spec_combined


if __name__ == '__main__':
  df1, df2, df3 = extract_raw_data()
