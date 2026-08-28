"""
Module: 02_ETL/src/transform.py
Description: Feature engineering for Thai market listings (Kaidee + One2car)
             and US Sales — calculates financial and derived measures.
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_YEAR = 2026
DEPRECIATION_RATE = 0.08
LIST_PRICE_MARKUP = (1.05, 1.15)   # uniform range above selling price
COST_PRICE_RATIO = (0.80, 0.88)    # uniform range below selling price
DAYS_ON_LOT_THAI = (10, 120)
DAYS_ON_LOT_US = (15, 90)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def assign_price_tier(price: float) -> str:
    """Categorises selling price into business price tiers."""
    if price < 300_000:  return "1. Eco (<300k)"
    if price < 500_000:  return "2. Mid-Low (300k-500k)"
    if price < 1_000_000: return "3. Mid-High (500k-1M)"
    return "4. Premium (>1M)"


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def transform_data(
    df_kaidee_clean: pd.DataFrame,
    df_one2car_clean: pd.DataFrame,
    df_us_clean: pd.DataFrame,
) -> tuple:
    """
    Consolidates Thai listings (Kaidee + One2car) and calculates all
    financial & derived measures. Returns (df_thai_trans, df_us_trans).
    """
    print("[Transform] Consolidating Thai Market Listings & Calculating Measures...")

    # --- Thai Listings ---
    shared_cols = ["price_clean", "mileage_clean", "model_year", "brand", "model",
                   "body_type", "fuel_type", "transmission_clean", "location"]

    df_thai = pd.concat(
        [df_one2car_clean[shared_cols], df_kaidee_clean[shared_cols]],
        ignore_index=True,
    )

    rng = np.random.default_rng(seed=42)
    n = len(df_thai)

    df_thai["car_age"] = (CURRENT_YEAR - df_thai["model_year"]).clip(lower=1)
    df_thai["annual_mileage"] = (df_thai["mileage_clean"] / df_thai["car_age"]).round(0).astype(int)

    df_thai["list_price"] = (df_thai["price_clean"] * rng.uniform(*LIST_PRICE_MARKUP, size=n)).round(-3)
    df_thai["discount_amount"] = (df_thai["list_price"] - df_thai["price_clean"]).round(2)
    df_thai["discount_pct"] = (df_thai["discount_amount"] / df_thai["list_price"] * 100).round(2)

    df_thai["cost_price"] = (df_thai["price_clean"] * rng.uniform(*COST_PRICE_RATIO, size=n)).round(-3)
    df_thai["profit"] = (df_thai["price_clean"] - df_thai["cost_price"]).round(2)
    df_thai["profit_margin"] = (df_thai["profit"] / df_thai["price_clean"] * 100).round(2)

    df_thai["depreciation_amount"] = (
        df_thai["list_price"] * (1 - (1 - DEPRECIATION_RATE) ** df_thai["car_age"])
    ).round(2)
    df_thai["discount_to_deprec_ratio"] = np.where(
        df_thai["depreciation_amount"] > 0,
        (df_thai["discount_amount"] / df_thai["depreciation_amount"] * 100).round(2),
        0,
    )
    df_thai["is_discount_exceeds_deprec"] = df_thai["discount_amount"] > df_thai["depreciation_amount"]

    df_thai["days_on_lot"] = rng.integers(*DAYS_ON_LOT_THAI, size=n)
    df_thai["net_revenue"] = df_thai["price_clean"]
    df_thai["price_tier"] = df_thai["price_clean"].apply(assign_price_tier)

    # --- US Sales ---
    df_us = df_us_clean.copy()
    df_us["car_age"] = (CURRENT_YEAR - df_us["model_year"]).clip(lower=1)
    df_us["days_on_lot"] = rng.integers(*DAYS_ON_LOT_US, size=len(df_us))

    print(f"[Transform Completed] Thai Market: {len(df_thai):,} rows | US Sales: {len(df_us):,} rows")
    return df_thai, df_us


if __name__ == "__main__":
    pass
