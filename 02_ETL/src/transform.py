"""
Module: 02_ETL/src/transform.py
Description: Performs Feature Engineering and calculates Performance Measures (Profit, Discount, Depreciation Ratio, Price Tier).
"""

import re
import numpy as np
import pandas as pd


def get_price_tier(price: float) -> str:
  """Categorizes selling price into 4 Business Price Tiers."""
  if price < 300000:
    return '1. Eco (<300k)'
  elif price <= 500000:
    return '2. Mid-Low (300k-500k)'
  elif price <= 1000000:
    return '3. Mid-High (500k-1M)'
  else:
    return '4. Premium (>1M)'


def transform_data(
    df_one2car_clean: pd.DataFrame, df_us_clean: pd.DataFrame
) -> tuple:
  """Calculates derived features and Business Performance Measures for One2car and US datasets."""
  print('[Transform] Performing Feature Engineering & Measures Calculation...')

  # 1. Transform One2car Data (Market Listings & Simulated Dealership Transactions)
  df_trans = df_one2car_clean.copy()

  df_trans['car_age'] = 2026 - df_trans['model_year']
  df_trans['car_age'] = df_trans['car_age'].apply(lambda x: max(x, 1))

  # MSRP estimate for new car baseline
  df_trans['msrp_estimate'] = df_trans['price_clean'] * 1.45

  # Simulated Discount strategy metrics
  np.random.seed(42)
  df_trans['discount_pct'] = np.random.uniform(2.0, 12.0, len(df_trans))
  df_trans['list_price'] = df_trans['price_clean'] / (
      1 - (df_trans['discount_pct'] / 100.0)
  )
  df_trans['discount_amount'] = df_trans['list_price'] - df_trans['price_clean']

  # Profit metrics
  df_trans['cost_price'] = df_trans['price_clean'] * np.random.uniform(
      0.80, 0.88, len(df_trans)
  )
  df_trans['profit'] = df_trans['price_clean'] - df_trans['cost_price']
  df_trans['profit_margin'] = (
      df_trans['profit'] / df_trans['price_clean']
  ) * 100.0

  # Depreciation and Ratio metrics
  df_trans['depreciation_amount'] = (
      df_trans['msrp_estimate'] - df_trans['price_clean']
  )
  df_trans['discount_to_deprec_ratio'] = (
      df_trans['discount_amount']
      / df_trans['depreciation_amount'].replace(0, 1)
  ) * 100.0

  df_trans['net_revenue'] = df_trans['price_clean'] - df_trans['discount_amount']
  df_trans['days_on_lot'] = np.random.randint(7, 120, size=len(df_trans))
  df_trans['price_tier'] = df_trans['price_clean'].apply(get_price_tier)

  print(
      f'[Transform Completed] One2car transformed with {len(df_trans)}'
      ' rows with full Measures.'
  )
  return df_trans, df_us_clean


if __name__ == '__main__':
  pass
