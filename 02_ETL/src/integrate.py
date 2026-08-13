"""
Module: 02_ETL/src/integrate.py
Description: Assembles the Star Schema Data Warehouse tables (2 Fact Tables + 5 Dimensions) with Surrogate Keys.
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def integrate_star_schema(
    df_trans: pd.DataFrame, df_us_clean: pd.DataFrame
) -> dict:
  """Integrates cleaned and transformed datasets into a Star Schema (2 Fact Tables + 5 Dimension Tables)."""
  print('[Integrate] Assembling Star Schema Data Warehouse tables...')

  # 1. DimCar
  dim_car = (
      df_trans[['brand', 'model', 'model_year', 'transmission_clean', 'price_tier']]
      .drop_duplicates()
      .reset_index(drop=True)
  )
  dim_car = dim_car.rename(columns={'transmission_clean': 'transmission'})
  dim_car['body_type'] = 'Sedan/SUV'
  dim_car['fuel_type'] = 'Petrol/Diesel'
  dim_car['car_key'] = dim_car.index + 1

  # Map car_key back to df_trans
  df_trans = df_trans.merge(
      dim_car[['brand', 'model', 'model_year', 'transmission', 'car_key']],
      left_on=['brand', 'model', 'model_year', 'transmission_clean'],
      right_on=['brand', 'model', 'model_year', 'transmission'],
      how='left',
  )

  # 2. DimDate
  date_range = pd.date_range(start='2024-01-01', end='2026-12-31', freq='D')
  dim_date = pd.DataFrame({'full_date': date_range})
  dim_date['date_key'] = (
      dim_date['full_date'].dt.strftime('%Y%m%d').astype(int)
  )
  dim_date['year'] = dim_date['full_date'].dt.year
  dim_date['quarter'] = dim_date['full_date'].dt.quarter
  dim_date['month'] = dim_date['full_date'].dt.month
  dim_date['month_name'] = dim_date['full_date'].dt.strftime('%B')
  dim_date['day_name'] = dim_date['full_date'].dt.strftime('%A')
  dim_date['is_weekend'] = dim_date['full_date'].dt.dayofweek >= 5

  # 3. DimLocation
  provinces = df_trans['location'].dropna().unique()
  dim_location = pd.DataFrame({'province': provinces})
  dim_location['location_key'] = dim_location.index + 1
  dim_location['region'] = dim_location['province'].apply(
      lambda p: (
          'Bangkok Metropolitan'
          if p
          in ['กรุงเทพมหานคร', 'สมุทรปราการ', 'นนทบุรี', 'ปทุมธานี', 'นครปฐม']
          else 'Other Region'
      )
  )

  df_trans = df_trans.merge(
      dim_location[['province', 'location_key']],
      left_on='location',
      right_on='province',
      how='left',
  )
  df_trans['location_key'] = df_trans['location_key'].fillna(1).astype(int)

  # 4. DimCustomer
  payment_methods = ['Finance/Leasing', 'Cash', 'Bank Transfer']
  segments = ['Individual', 'Corporate', 'First-Time Buyer']
  dim_customer = pd.DataFrame({
      'customer_key': range(1, 101),
      'province': np.random.choice(provinces, 100),
      'payment_method': np.random.choice(payment_methods, 100),
      'customer_segment': np.random.choice(segments, 100),
  })

  # 5. DimAcquisitionSource
  dim_source = pd.DataFrame({
      'source_key': [1, 2, 3],
      'source_type': [
          'Auction House',
          'Direct Customer Trade-In',
          'Fleet Buyout',
      ],
      'supplier_name': ['Bangkok Auction', 'Direct Owner', 'Corporate Fleet'],
  })

  # 6. FactSales (Fact Table 1)
  df_trans['sales_id'] = range(1, len(df_trans) + 1)
  df_trans['customer_key'] = np.random.randint(1, 101, size=len(df_trans))
  df_trans['acquisition_source_key'] = np.random.randint(
      1, 4, size=len(df_trans)
  )

  # Generate date_key for sale
  random_dates = np.random.choice(dim_date['date_key'], size=len(df_trans))
  df_trans['date_key'] = random_dates

  fact_sales = pd.DataFrame({
      'sales_id': df_trans['sales_id'],
      'car_key': df_trans['car_key'].fillna(1).astype(int),
      'date_key': df_trans['date_key'],
      'customer_key': df_trans['customer_key'],
      'acquisition_source_key': df_trans['acquisition_source_key'],
      'location_key': df_trans['location_key'],
      'list_price': df_trans['list_price'],
      'selling_price': df_trans['price_clean'],
      'discount_amount': df_trans['discount_amount'],
      'discount_pct': df_trans['discount_pct'],
      'cost_price': df_trans['cost_price'],
      'profit': df_trans['profit'],
      'profit_margin': df_trans['profit_margin'],
      'depreciation_amount': df_trans['depreciation_amount'],
      'discount_to_deprec_ratio': df_trans['discount_to_deprec_ratio'],
      'net_revenue': df_trans['net_revenue'],
      'days_on_lot': df_trans['days_on_lot'],
      'car_age': df_trans['car_age'],
      'mileage': df_trans['mileage_clean'].fillna(50000).astype(int),
      'quantity': 1,
  })

  # 7. FactMarketListings (Fact Table 2 - One2car Benchmark Market Supply)
  fact_market = pd.DataFrame({
      'listing_id': range(1, len(df_trans) + 1),
      'car_key': df_trans['car_key'].fillna(1).astype(int),
      'date_key': df_trans['date_key'],
      'location_key': df_trans['location_key'],
      'ask_price': df_trans['price_clean'],
      'mileage': df_trans['mileage_clean'].fillna(50000).astype(int),
      'car_age': df_trans['car_age'],
  })

  tables = {
      'DimCar': dim_car,
      'DimDate': dim_date,
      'DimLocation': dim_location,
      'DimCustomer': dim_customer,
      'DimAcquisitionSource': dim_source,
      'FactSales': fact_sales,
      'FactMarketListings': fact_market,
  }

  print(
      '[Integrate Completed] Star Schema assembled: 2 Fact Tables (FactSales:'
      f' {len(fact_sales)}, FactMarketListings: {len(fact_market)}) + 5'
      ' Dimensions.'
  )
  return tables


if __name__ == '__main__':
  pass
