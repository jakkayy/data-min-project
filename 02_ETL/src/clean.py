"""
Module: 02_ETL/src/clean.py
Description: Cleans raw data from Kaidee, One2car, and US Sales datasets.
             Handles deduplication, price/mileage normalization, and feature extraction.
"""

import re
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRICE_MIN = 20_000
PRICE_MAX = 35_000_000
MILEAGE_MIN = 0
MILEAGE_MAX = 500_000
YEAR_MIN = 1900
YEAR_MAX = 2026
US_PRICE_MIN = 100
US_PRICE_MAX = 500_000

TRANSMISSION_MAP = {
    "เกียร์อัตโนมัติ": "Automatic",
    "เกียร์ธรรมดา": "Manual",
}

PICKUP_KEYWORDS = ["pickup", "cab", "space cab", "hi-lander", "double cab", "smart cab",
                   "revo", "d-max", "ranger", "navara", "กระบะ"]
SUV_KEYWORDS = ["suv", "mu-x", "fortuner", "everest", "cr-v", "x3", "glc",
                "cross", "hr-v", "cx-5", "pajero"]
HATCHBACK_KEYWORDS = ["hatchback", "good cat", "yaris", "swift", "5 ประตู", "ora"]
COUPE_KEYWORDS = ["coupe", "gran m sport", "220i"]
VAN_KEYWORDS = ["van", "caravelle", "wagon", "ตู้"]
SEDAN_KEYWORDS = ["sedan", "city", "camry", "altis", "civic", "mazda 3",
                  "c220", "520d", "ซีดาน"]

HYBRID_KEYWORDS = ["e:hev", "hev", "hybrid", "ไฮบริด"]
EV_KEYWORDS = ["ora", "good cat", "ev", "รถไฟฟ้า", "100%"]
DIESEL_KEYWORDS = ["d-max", "hilux", "revo", "ranger", "navara", "mu-x",
                   "fortuner", "everest", "520d", "c220 d", "tdi", "ดีเซล"]

BANGKOK_SUBDISTRICTS = ["ตลิ่งชัน", "บางแค", "ศรีนครินทร์", "กาญจนา",
                         "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "นครปฐม"]
PROVINCE_ALIASES = {"โคราช": "นครราชสีมา", "หาดใหญ่": "สงขลา"}
SEARCHABLE_PROVINCES = [
    "เชียงใหม่", "เชียงราย", "ชลบุรี", "นนทบุรี", "ปทุมธานี",
    "สมุทรปราการ", "นครปฐม", "ภูเก็ต", "ขอนแก่น", "โคราช",
    "นครราชสีมา", "สงขลา", "หาดใหญ่", "ตลิ่งชัน", "บางแค",
    "ศรีนครินทร์", "กาญจนา",
]


# ---------------------------------------------------------------------------
# Helper: Cleaning
# ---------------------------------------------------------------------------

def clean_price(val) -> float | None:
    """Strips non-numeric characters and returns price as float."""
    if pd.isna(val):
        return None
    digits = re.sub(r"[^\d]", "", str(val))
    return float(digits) if digits else None


def clean_mileage(val) -> int | None:
    """Handles range strings (e.g. '170 - 175K กม.') and returns mileage as int."""
    if pd.isna(val):
        return None
    s = str(val).replace("กม.", "").replace(",", "").strip()
    range_match = re.search(r"(\d+)\s*-\s*(\d+)K", s, re.IGNORECASE)
    if range_match:
        low = float(range_match.group(1)) * 1000
        high = float(range_match.group(2)) * 1000
        return int((low + high) / 2)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


# ---------------------------------------------------------------------------
# Helper: Feature Extraction
# ---------------------------------------------------------------------------

def _contains_any(text: str, keywords: list) -> bool:
    return any(k in text for k in keywords)


def extract_body_type(title: str, desc: str = "") -> str:
    """Classifies body type from car title and description text."""
    text = (str(title) + " " + str(desc)).lower()
    if _contains_any(text, PICKUP_KEYWORDS):    return "Pick-up"
    if _contains_any(text, SUV_KEYWORDS):       return "SUV"
    if _contains_any(text, HATCHBACK_KEYWORDS): return "Hatchback"
    if _contains_any(text, COUPE_KEYWORDS):     return "Coupe"
    if _contains_any(text, VAN_KEYWORDS):       return "Van"
    return "Sedan"


def extract_fuel_type(title: str, desc: str = "") -> str:
    """Classifies fuel type from car title and description text."""
    text = (str(title) + " " + str(desc)).lower()
    if _contains_any(text, HYBRID_KEYWORDS): return "Hybrid"
    if _contains_any(text, EV_KEYWORDS):     return "EV"
    if _contains_any(text, DIESEL_KEYWORDS): return "Diesel"
    return "Petrol"


def parse_car_title(title: str, desc: str = "") -> pd.Series:
    """Parses model_year, brand, model, body_type, and fuel_type from a car title."""
    if pd.isna(title):
        return pd.Series([2018, "Unknown", "General", "Sedan", "Petrol"])

    title_str = str(title).strip()
    year_match = re.search(r"^(20\d{2}|19\d{2})", title_str)
    year = int(year_match.group(1)) if year_match else 2018

    text_no_year = re.sub(r"^(20\d{2}|19\d{2})\s*", "", title_str)
    parts = text_no_year.split()
    brand = parts[0] if len(parts) > 0 else "Unknown"
    model = parts[1] if len(parts) > 1 else "General"

    return pd.Series([year, brand, model,
                      extract_body_type(title_str, desc),
                      extract_fuel_type(title_str, desc)])


def extract_kaidee_location(row: dict) -> str:
    """Resolves province from location field or falls back to scanning description text."""
    loc = row.get("location")
    if pd.notna(loc) and str(loc).strip():
        return str(loc).strip()

    desc = str(row.get("description", ""))
    for province in SEARCHABLE_PROVINCES:
        if province in desc:
            if province in BANGKOK_SUBDISTRICTS:
                return "กรุงเทพมหานคร"
            return PROVINCE_ALIASES.get(province, province)

    return "กรุงเทพมหานคร"


# ---------------------------------------------------------------------------
# Public: Clean Functions
# ---------------------------------------------------------------------------

def clean_kaidee_data(df_kaidee: pd.DataFrame) -> pd.DataFrame:
    """Cleans Kaidee Auto JSON: deduplication, price/mileage normalization, feature extraction."""
    print("[Clean] Cleaning Kaidee Auto JSON dataset...")
    initial_len = len(df_kaidee)

    df = df_kaidee.drop_duplicates(subset=["title", "price", "brand", "year", "mileage"]).copy()

    df["price_clean"] = df["price"].apply(clean_price)
    df["mileage_clean"] = df["mileage"].apply(clean_mileage)
    df = df.dropna(subset=["price_clean"])
    df = df[(df["price_clean"] >= PRICE_MIN) & (df["price_clean"] <= PRICE_MAX)].copy()

    global_mileage_median = df["mileage_clean"].median()
    df["mileage_clean"] = (
        df.groupby(["brand", "year"])["mileage_clean"]
        .transform(lambda g: g.fillna(g.median() if not g.dropna().empty else global_mileage_median))
        .fillna(global_mileage_median)
        .astype(int)
    )

    df["model_year"] = pd.to_numeric(df["year"], errors="coerce").fillna(2018).astype(int)
    df["body_type"] = df.apply(lambda r: extract_body_type(r.get("title"), r.get("description")), axis=1)
    df["fuel_type"] = df.apply(lambda r: extract_fuel_type(r.get("title"), r.get("description")), axis=1)
    df["transmission_clean"] = df["transmission"].map(TRANSMISSION_MAP).fillna("Automatic")
    df["location"] = df.apply(extract_kaidee_location, axis=1)

    print(f"[Clean Completed] Kaidee Auto: {len(df):,} valid rows (Dropped {initial_len - len(df):,})")
    return df


def clean_one2car_data(df_one2car: pd.DataFrame) -> pd.DataFrame:
    """Cleans One2car dataset: deduplication, price trap filtering, feature extraction."""
    print("[Clean] Cleaning One2car dataset...")
    initial_len = len(df_one2car)

    df = df_one2car.drop_duplicates(subset=["car_title", "price", "mileage", "location"]).copy()

    df["price_clean"] = df["price"].apply(clean_price)
    df["mileage_clean"] = df["mileage"].apply(clean_mileage)
    df = df.dropna(subset=["price_clean"])
    df = df[(df["price_clean"] >= PRICE_MIN) & (df["price_clean"] <= PRICE_MAX)].copy()

    parsed = df.apply(lambda r: parse_car_title(r.get("car_title"), r.get("description")), axis=1)
    df[["model_year", "brand", "model", "body_type", "fuel_type"]] = parsed

    df["transmission_clean"] = df["transmission"].map(TRANSMISSION_MAP).fillna("Automatic")
    df["location"] = df["location"].fillna("กรุงเทพมหานคร")

    print(f"[Clean Completed] One2car: {len(df):,} valid rows (Dropped {initial_len - len(df):,})")
    return df


def clean_us_sales_data(df_us: pd.DataFrame) -> pd.DataFrame:
    """Cleans US Sales dataset: range filtering, column renaming, deduplication."""
    print("[Clean] Cleaning US Sales dataset...")
    initial_len = len(df_us)

    df = df_us[
        (df_us["pricesold"] > US_PRICE_MIN) & (df_us["pricesold"] <= US_PRICE_MAX) &
        (df_us["Mileage"] > MILEAGE_MIN) & (df_us["Mileage"] <= MILEAGE_MAX) &
        (df_us["Year"] >= YEAR_MIN) & (df_us["Year"] <= YEAR_MAX)
    ].rename(columns={
        "pricesold": "selling_price",
        "yearsold":  "sale_year",
        "Mileage":   "mileage",
        "Make":      "brand",
        "Model":     "model",
        "Year":      "model_year",
        "BodyType":  "body_type",
    }).copy()

    df["body_type"] = df["body_type"].fillna("Other")
    df["brand"] = df["brand"].fillna("Unknown")
    df["model"] = df["model"].fillna("General")
    df = df.drop_duplicates(subset=["brand", "model", "model_year", "selling_price", "mileage"]).copy()

    print(f"[Clean Completed] US Sales: {len(df):,} valid rows (Dropped {initial_len - len(df):,})")
    return df


if __name__ == "__main__":
    pass
