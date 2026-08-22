"""
Module: 02_ETL/src/transform.py
Description: Performs Feature Engineering, consolidates Kaidee JSON + One2car listings, and calculates Business Measures.
"""

import numpy as np
import pandas as pd


def assign_price_tier(price: float) -> str:
  """Categorizes selling price into business price tiers."""
  if price < 300000:
    return '1. Eco (<300k)'
  elif price < 500000:
    return '2. Mid-Low (300k-500k)'
  elif price < 1000000:
    return '3. Mid-High (500k-1M)'
  else:
    return '4. Premium (>1M)'


def transform_data(
    df_kaidee_clean: pd.DataFrame,
    df_one2car_clean: pd.DataFrame,
    df_us_clean: pd.DataFrame,
) -> tuple:
  """Consolidates Thai listings (Kaidee JSON + One2car) and calculates all Financial & Derived Measures."""
  print(
      '[Transform] Consolidating Thai Market Listings (Kaidee JSON + One2car'
      ' Multi-file) & Calculating Measures...'
  )

  # Consolidate Thai Listings
  cols = [
      'price_clean',
      'mileage_clean',
      'model_year',
      'brand',
      'model',
      'body_type',
      'fuel_type',
      'transmission_clean',
      'location',
  ]
  df_t1 = df_one2car_clean[cols].copy()
  df_t2 = df_kaidee_clean[cols].copy()
  df_trans = pd.concat([df_t1, df_t2], ignore_index=True)

  np.random.seed(42)

  # 1. Car Age & Annual Mileage
  df_trans['car_age'] = (2026 - df_trans['model_year']).clip(lower=1)
  df_trans['annual_mileage'] = (df_trans['mileage_clean'] / df_trans['car_age']).round(0).astype(int)

  # 2. List Price & Discounts
  df_trans['list_price'] = (
      df_trans['price_clean'] * np.random.uniform(1.05, 1.15, size=len(df_trans))
  ).round(-3)
  df_trans['discount_amount'] = (
      df_trans['list_price'] - df_trans['price_clean']
  ).round(2)
  df_trans['discount_pct'] = (
      (df_trans['discount_amount'] / df_trans['list_price']) * 100
  ).round(2)

  # 3. Cost Price & Profit
  df_trans['cost_price'] = (
      df_trans['price_clean'] * np.random.uniform(0.80, 0.88, size=len(df_trans))
  ).round(-3)
  df_trans['profit'] = (df_trans['price_clean'] - df_trans['cost_price']).round(
      2
  )
  df_trans['profit_margin'] = (
      (df_trans['profit'] / df_trans['price_clean']) * 100
  ).round(2)

  # 4. Depreciation Amount & Ratio (8% per year)
  deprec_rate = 0.08
  df_trans['depreciation_amount'] = (
      df_trans['list_price'] * (1 - (1 - deprec_rate) ** df_trans['car_age'])
  ).round(2)
  df_trans['discount_to_deprec_ratio'] = np.where(
      df_trans['depreciation_amount'] > 0,
      (df_trans['discount_amount'] / df_trans['depreciation_amount']) * 100,
      0,
  ).round(2)
  df_trans['is_discount_exceeds_deprec'] = df_trans['discount_amount'] > df_trans['depreciation_amount']

  # 5. Inventory & Price Tier
  df_trans['days_on_lot'] = np.random.randint(10, 120, size=len(df_trans))
  df_trans['net_revenue'] = df_trans['price_clean']
  df_trans['price_tier'] = df_trans['price_clean'].apply(assign_price_tier)

  # Process US Sales
  df_us_trans = df_us_clean.copy()
  df_us_trans['car_age'] = (2026 - df_us_trans['model_year']).clip(lower=1)
  df_us_trans['days_on_lot'] = np.random.randint(15, 90, size=len(df_us_trans))

  print(
      f'[Transform Completed] Consolidated Thai Market transformed with'
      f' {len(df_trans):,} rows with full Measures.'
  )
  return df_trans, df_us_trans


if __name__ == '__main__':
  pass
