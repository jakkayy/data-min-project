import re
import pandas as pd


def clean_price(val):
  """Cleans price string/number into numeric float."""
  if pd.isna(val):
    return None
  nums = re.sub(r'[^\d]', '', str(val))
  return float(nums) if nums != '' else None


def clean_mileage(val):
  """Cleans mileage string/number (handles ranges e.g. '170 - 175K กม.') into numeric int."""
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


def extract_body_type(title_str, desc_str=''):
  """Extracts BodyType (Pick-up, SUV, Sedan, Hatchback, Coupe, Van) from car title & description."""
  text = (str(title_str) + ' ' + str(desc_str)).lower()
  if any(k in text for k in ['pickup', 'cab', 'space cab', 'hi-lander', 'double cab', 'smart cab', 'revo', 'd-max', 'ranger', 'navara', 'กระบะ']):
    return 'Pick-up'
  elif any(k in text for k in ['suv', 'mu-x', 'fortuner', 'everest', 'cr-v', 'x3', 'glc', 'cross', 'hr-v', 'cx-5', 'pajero']):
    return 'SUV'
  elif any(k in text for k in ['hatchback', 'good cat', 'yaris', 'swift', '5 ประตู', 'ora']):
    return 'Hatchback'
  elif any(k in text for k in ['coupe', 'gran m sport', '220i']):
    return 'Coupe'
  elif any(k in text for k in ['van', 'caravelle', 'wagon', 'ตู้']):
    return 'Van'
  elif any(k in text for k in ['sedan', 'city', 'camry', 'altis', 'civic', 'mazda 3', 'c220', '520d', 'ซีดาน']):
    return 'Sedan'
  else:
    return 'Sedan'


def extract_fuel_type(title_str, desc_str=''):
  """Extracts FuelType (Diesel, Petrol, Hybrid, EV) from car title & description."""
  text = (str(title_str) + ' ' + str(desc_str)).lower()
  if any(k in text for k in ['e:hev', 'hev', 'hybrid', 'ไฮบริด']):
    return 'Hybrid'
  elif any(k in text for k in ['ora', 'good cat', 'ev', 'รถไฟฟ้า', '100%']):
    return 'EV'
  elif any(k in text for k in ['d-max', 'hilux', 'revo', 'ranger', 'navara', 'mu-x', 'fortuner', 'everest', '520d', 'c220 d', 'tdi', 'ดีเซล']):
    return 'Diesel'
  else:
    return 'Petrol'


def parse_car_title(title, desc=''):
  """Parses model_year, brand, model, body_type, and fuel_type from car title & description."""
  if pd.isna(title):
    return pd.Series([2018, 'Unknown', 'General', 'Sedan', 'Petrol'])

  title_str = str(title).strip()
  year_match = re.search(r'^(20\d{2}|19\d{2})', title_str)
  year = int(year_match.group(1)) if year_match else 2018

  text_clean = re.sub(r'^(20\d{2}|19\d{2})\s*', '', title_str)
  parts = text_clean.split()
  brand = parts[0] if len(parts) > 0 else 'Unknown'
  model = parts[1] if len(parts) > 1 else 'General'

  body_type = extract_body_type(title_str, desc)
  fuel_type = extract_fuel_type(title_str, desc)

  return pd.Series([year, brand, model, body_type, fuel_type])


def extract_kaidee_location(row):
  loc = row.get('location')
  if pd.notna(loc) and str(loc).strip() != '':
    return str(loc).strip()
  desc = str(row.get('description', ''))
  provinces = ['เชียงใหม่', 'เชียงราย', 'ชลบุรี', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ', 'นครปฐม', 'ภูเก็ต', 'ขอนแก่น', 'โคราช', 'นครราชสีมา', 'สงขลา', 'หาดใหญ่', 'ตลิ่งชัน', 'บางแค', 'ศรีนครินทร์', 'กาญจนา']
  for p in provinces:
    if p in desc:
      if p in ['ตลิ่งชัน', 'บางแค', 'ศรีนครินทร์', 'กาญจนา', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ', 'นครปฐม']:
        return 'กรุงเทพมหานคร'
      elif p in ['โคราช']:
        return 'นครราชสีมา'
      elif p in ['หาดใหญ่']:
        return 'สงขลา'
      return p
  return 'กรุงเทพมหานคร'


def clean_kaidee_data(df_kaidee: pd.DataFrame) -> pd.DataFrame:
  """Cleans Kaidee Auto JSON dataset with deduplication and smart imputation."""
  print('[Clean] Cleaning Kaidee Auto JSON dataset...')
  initial_len = len(df_kaidee)
  
  # 1. Deduplication
  df_clean = df_kaidee.drop_duplicates(subset=['title', 'price', 'brand', 'year', 'mileage']).copy()
  
  # 2. Price & Mileage Clean
  df_clean['price_clean'] = df_clean['price'].apply(clean_price)
  df_clean['mileage_clean'] = df_clean['mileage'].apply(clean_mileage)
  
  df_clean = df_clean.dropna(subset=['price_clean'])
  df_clean = df_clean[(df_clean['price_clean'] >= 20000) & (df_clean['price_clean'] <= 35000000)].copy()

  # 3. Smart Mileage Imputation
  global_mileage_median = df_clean['mileage_clean'].median()
  df_clean['mileage_clean'] = df_clean.groupby(['brand', 'year'])['mileage_clean'].transform(
      lambda g: g.fillna(g.median() if not g.dropna().empty else global_mileage_median)
  )
  df_clean['mileage_clean'] = df_clean['mileage_clean'].fillna(global_mileage_median).astype(int)

  # 4. Feature Extraction
  df_clean['model_year'] = (
      pd.to_numeric(df_clean['year'], errors='coerce').fillna(2018).astype(int)
  )
  df_clean['body_type'] = df_clean.apply(
      lambda r: extract_body_type(r.get('title'), r.get('description')), axis=1
  )
  df_clean['fuel_type'] = df_clean.apply(
      lambda r: extract_fuel_type(r.get('title'), r.get('description')), axis=1
  )
  df_clean['transmission_clean'] = (
      df_clean['transmission']
      .map({'เกียร์อัตโนมัติ': 'Automatic', 'เกียร์ธรรมดา': 'Manual'})
      .fillna('Automatic')
  )
  df_clean['location'] = df_clean.apply(extract_kaidee_location, axis=1)

  print(f'[Clean Completed] Kaidee Auto cleaned: {len(df_clean):,} valid rows (Dropped {initial_len - len(df_clean)} duplicate/invalid rows)')
  return df_clean


def clean_one2car_data(df_one2car: pd.DataFrame) -> pd.DataFrame:
  """Cleans One2car raw dataset with deduplication and price trap filtering."""
  print('[Clean] Cleaning One2car dataset & extracting BodyType/FuelType features...')
  initial_len = len(df_one2car)

  # 1. Deduplication
  df_clean = df_one2car.drop_duplicates(subset=['car_title', 'price', 'mileage', 'location']).copy()

  # 2. Price & Mileage Clean
  df_clean['price_clean'] = df_clean['price'].apply(clean_price)
  df_clean['mileage_clean'] = df_clean['mileage'].apply(clean_mileage)

  # Filter Missing Prices & Price Traps (< 20,000 THB)
  df_clean = df_clean.dropna(subset=['price_clean'])
  df_clean = df_clean[(df_clean['price_clean'] >= 20000) & (df_clean['price_clean'] <= 35000000)].copy()

  # 3. Title Parsing
  parsed = df_clean.apply(
      lambda row: parse_car_title(row.get('car_title'), row.get('description')),
      axis=1,
  )
  df_clean[['model_year', 'brand', 'model', 'body_type', 'fuel_type']] = parsed

  df_clean['transmission_clean'] = (
      df_clean['transmission']
      .map({'เกียร์อัตโนมัติ': 'Automatic', 'เกียร์ธรรมดา': 'Manual'})
      .fillna('Automatic')
  )

  df_clean['location'] = df_clean['location'].fillna('กรุงเทพมหานคร')
  print(f'[Clean Completed] One2car cleaned: {len(df_clean):,} valid rows (Dropped {initial_len - len(df_clean)} duplicate/invalid/trap rows)')
  return df_clean


def clean_us_sales_data(df_us: pd.DataFrame) -> pd.DataFrame:
  """Cleans US Sales raw dataset with typo filters for Year and Mileage."""
  print('[Clean] Cleaning US Sales dataset & filtering typos...')
  initial_len = len(df_us)

  # 1. Filter Invalid Prices (> 100 USD & <= 500k USD)
  df_clean = df_us[(df_us['pricesold'] > 100) & (df_us['pricesold'] <= 500000)].copy()

  # 2. Filter Mileage Typos (0 < Mileage <= 500k miles)
  df_clean = df_clean[(df_clean['Mileage'] > 0) & (df_clean['Mileage'] <= 500000)].copy()

  # 3. Filter Year Typos (1900 <= Year <= 2026)
  df_clean = df_clean[(df_clean['Year'] >= 1900) & (df_clean['Year'] <= 2026)].copy()

  # 4. Rename Columns
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

  # 5. Fill Missing Categoricals
  df_clean['body_type'] = df_clean['body_type'].fillna('Other')
  df_clean['brand'] = df_clean['brand'].fillna('Unknown')
  df_clean['model'] = df_clean['model'].fillna('General')

  # 6. Deduplication
  df_clean = df_clean.drop_duplicates(subset=['brand', 'model', 'model_year', 'selling_price', 'mileage']).copy()

  print(f'[Clean Completed] US Sales cleaned: {len(df_clean):,} valid rows (Dropped {initial_len - len(df_clean)} typo/duplicate rows)')
  return df_clean


if __name__ == '__main__':
  pass
