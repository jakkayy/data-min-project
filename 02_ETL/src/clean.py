"""
Module: 02_ETL/src/clean.py
Description: Cleans prices, mileages, parses car titles via Regex, and standardizes categories.
"""

import re
import pandas as pd


def clean_price(val):
  """Cleans price string into numeric float."""
  if pd.isna(val):
    return None
  nums = re.sub(r'[^\d]', '', str(val))
  return float(nums) if nums != '' else None


def clean_mileage(val):
  """Cleans mileage string (handles range e.g.

  '170 - 175K กม.') into numeric int.
  """
  if pd.isna(val):
    return None
  s = str(val).replace('กม.', '').replace(',', '').strip()
  match_range = re.search(r'(\d+)\s*-\s*(\d+)K', s, re.IGNORECASE)
  if match_range:
    low = float(match_range.group(1)) * 1000
    high = float(match_range.group(2)) * 1000
    return int((low + high) / 2)
  nums = re.sub(r'[^\d]', '', s)
  return int(nums) if nums != '' else None


def parse_car_title(title):
  """Parses model_year, brand, and model from car_title string."""
  if pd.isna(title):
    return pd.Series([2018, 'Unknown', 'General'])
  title_str = str(title).strip()
  year_match = re.search(r'^(20\d{2}|19\d{2})', title_str)
  year = int(year_match.group(1)) if year_match else 2018

  text_clean = re.sub(r'^(20\d{2}|19\d{2})\s*', '', title_str)
  parts = text_clean.split()
  brand = parts[0] if len(parts) > 0 else 'Unknown'
  model = parts[1] if len(parts) > 1 else 'General'
  return pd.Series([year, brand, model])


def clean_one2car_data(df_one2car: pd.DataFrame) -> pd.DataFrame:
  """Cleans One2car raw dataset."""
  print('[Clean] Cleaning One2car dataset...')
  df_clean = df_one2car.dropna(subset=['price']).copy()

  df_clean['price_clean'] = df_clean['price'].apply(clean_price)
  df_clean['mileage_clean'] = df_clean['mileage'].apply(clean_mileage)
  df_clean[['model_year', 'brand', 'model']] = df_clean['car_title'].apply(
      parse_car_title
  )

  df_clean = df_clean.dropna(subset=['price_clean']).copy()

  df_clean['transmission_clean'] = (
      df_clean['transmission']
      .map({'เกียร์อัตโนมัติ': 'Automatic', 'เกียร์ธรรมดา': 'Manual'})
      .fillna('Automatic')
  )

  df_clean['location'] = df_clean['location'].fillna('กรุงเทพมหานคร')
  print(f'[Clean Completed] One2car cleaned: {len(df_clean)} valid rows')
  return df_clean


def clean_us_sales_data(df_us: pd.DataFrame) -> pd.DataFrame:
  """Cleans US Sales raw dataset."""
  print('[Clean] Cleaning US Sales dataset...')
  df_clean = df_us[(df_us['pricesold'] > 100) & (df_us['Mileage'] > 0)].copy()

  df_clean = df_clean.rename(
      columns={
          'pricesold': 'selling_price',
          'yearsold': 'sale_year',
          'Mileage': 'mileage',
          'Make': 'brand',
          'Model': 'model',
          'Year': 'model_year',
          'BodyType': 'body_type',
      }
  )

  df_clean['body_type'] = df_clean['body_type'].fillna('Other')
  print(f'[Clean Completed] US Sales cleaned: {len(df_clean)} valid rows')
  return df_clean


def clean_spec_data(df_spec: pd.DataFrame) -> pd.DataFrame:
  """Cleans Spec combined raw dataset."""
  print('[Clean] Cleaning Spec dataset...')
  df_clean = df_spec.copy()
  df_clean['AskPrice_clean'] = df_clean['AskPrice'].apply(clean_price)
  df_clean['kmDriven_clean'] = df_clean['kmDriven'].apply(clean_mileage)
  print(f'[Clean Completed] Spec cleaned: {len(df_clean)} valid rows')
  return df_clean


if __name__ == '__main__':
  pass
