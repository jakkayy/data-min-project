"""
Pipeline Orchestrator: 02_ETL/run_pipeline.py
Description: Executes the full automated ETL Pipeline (Extract -> Clean -> Transform -> Integrate -> Validate -> Load).
"""

import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extract import extract_raw_data
from src.clean import clean_one2car_data, clean_us_sales_data, clean_spec_data
from src.transform import transform_data
from src.integrate import integrate_star_schema
from src.validate import validate_dw_data
from src.load import load_to_data_warehouse

def main():
    print("=========================================================")
    print("  🚀 AUTOMATED ETL PIPELINE: USED CAR DATA WAREHOUSE")
    print("=========================================================\n")
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Step 1: Extract
    df_one2car_raw, df_us_raw, df_spec_raw = extract_raw_data(base_dir)
    print()
    
    # Step 2: Clean
    df_one2car_clean = clean_one2car_data(df_one2car_raw)
    df_us_clean = clean_us_sales_data(df_us_raw)
    df_spec_clean = clean_spec_data(df_spec_raw)
    print()
    
    # Step 3: Transform
    df_trans, df_us_trans = transform_data(df_one2car_clean, df_us_clean)
    print()
    
    # Step 4: Integrate
    dw_tables = integrate_star_schema(df_trans, df_us_trans)
    print()
    
    # Step 5: Validate
    is_valid = validate_dw_data(dw_tables)
    if not is_valid:
        print("❌ PIPELINE TERMINATED DUE TO DATA QUALITY VALIDATION ERRORS!")
        sys.exit(1)
        
    # Step 6: Load
    db_path = load_to_data_warehouse(dw_tables, base_dir)
    
    print("\n=========================================================")
    print("  🎉 ETL PIPELINE EXECUTED SUCCESSFULLY!")
    print(f"  📁 Data Warehouse SQLite DB: {db_path}")
    print("=========================================================")

if __name__ == '__main__':
    main()
