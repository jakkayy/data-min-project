"""
Module: 02_ETL/src/validate.py
Description: Asserts Data Quality Rules (PK uniqueness, FK integrity, non-negative measures) before loading into Data Warehouse.
"""

import sys
import pandas as pd


def validate_dw_data(dw_tables: dict) -> bool:
  """Executes 4 Data Quality Assertions on the integrated Star Schema tables."""
  print('[Validate] Running Data Quality Assertion Checks...')
  errors = []

  # Rule 1: Check PK Uniqueness in Dimensions
  for dim_name, pk_col in [
      ('DimCar', 'car_key'),
      ('DimDate', 'date_key'),
      ('DimLocation', 'location_key'),
      ('DimCustomer', 'customer_key'),
      ('DimAcquisitionSource', 'source_key'),
  ]:
    if dw_tables[dim_name][pk_col].duplicated().sum() > 0:
      errors.append(f'Rule 1 Fail: Found duplicate PKs in {dim_name}')
    else:
      print(f'  [PASS] Rule 1: {dim_name} Primary Keys are 100% Unique.')

  # Rule 2: Check Foreign Key Integrity in FactSales
  fact_sales = dw_tables['FactSales']
  for fk_col in [
      'car_key',
      'date_key',
      'location_key',
      'customer_key',
      'acquisition_source_key',
  ]:
    null_count = fact_sales[fk_col].isnull().sum()
    if null_count > 0:
      errors.append(
          f'Rule 2 Fail: Found {null_count} null Foreign Keys ({fk_col}) in'
          ' FactSales'
      )
    else:
      print(f'  [PASS] Rule 2: FactSales {fk_col} is 100% Non-Null.')

  # Rule 3: Positive Financial Measures
  if (fact_sales['selling_price'] <= 0).sum() > 0:
    errors.append('Rule 3 Fail: Found non-positive selling_price in FactSales')
  else:
    print('  [PASS] Rule 3: All selling prices are positive values.')

  # Rule 4: Non-negative Days on Lot
  if (fact_sales['days_on_lot'] < 0).sum() > 0:
    errors.append('Rule 4 Fail: Found negative days_on_lot in FactSales')
  else:
    print('  [PASS] Rule 4: All days_on_lot values are non-negative.')

  if len(errors) == 0:
    print(
        '[Validate Completed] ALL 4 DATA QUALITY ASSERTIONS PASSED! Data'
        ' ready for Data Warehouse loading.\n'
    )
    return True
  else:
    print(f'[Validate Failed] Found {len(errors)} validation errors:')
    for err in errors:
      print(f'  ❌ {err}')
    return False


if __name__ == '__main__':
  pass
