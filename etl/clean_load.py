# etl/clean_load.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import glob
import json
from datetime import datetime
import pandas as pd
import numpy as np
from shared.db import get_collection

# Folders
RAW_DIR = os.path.join("data", "raw")
CLEAN_DIR = os.path.join("data", "cleaned")
os.makedirs(CLEAN_DIR, exist_ok=True)

# Numeric fields to clean with z-score
NUMERIC_FIELDS = ["temperature", "salinity", "odo"]

# Common column name variations (alias map)
ALIAS_MAP = {
    "Temperature (c)": "temperature",
    "Temperature": "temperature",
    "Salinity (ppt)": "salinity",
    "Salinity": "salinity",
    "ODO mg/L": "odo",
    "ODO": "odo",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Date": "date",
    "Time": "time",
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename and unify columns across different CSVs."""
    df = df.rename(columns={c: ALIAS_MAP.get(c, c) for c in df.columns})

    # Combine date/time if separate
    if "timestamp" not in df.columns:
        if {"date", "time"} <= set(df.columns):
            df["timestamp"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str),
                                             errors="coerce")
        elif "Date" in df.columns and "Time" in df.columns:
            df["timestamp"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str),
                                             errors="coerce")
        else:
            for c in df.columns:
                if "time" in c.lower() or "date" in c.lower():
                    df["timestamp"] = pd.to_datetime(df[c], errors="coerce")
                    break

    # Ensure numeric columns are numeric
    for col in ["latitude", "longitude"] + NUMERIC_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def zscore_clean(df: pd.DataFrame, fields=NUMERIC_FIELDS, z_thresh=3.0):
    """Remove outliers using z-score."""
    mask = pd.Series(True, index=df.index)
    for f in fields:
        if f in df.columns:
            s = df[f].astype(float)
            mu, sd = s.mean(), s.std(ddof=0)
            if sd and not np.isnan(sd):
                z = (s - mu) / sd
                mask &= z.abs() <= z_thresh
    cleaned = df[mask]
    removed = len(df) - len(cleaned)
    return cleaned, len(df), removed

def insert_into_db(df: pd.DataFrame):
    """Insert cleaned data into MongoDB or mongomock."""
    coll = get_collection()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    if records:
        coll.insert_many(records)

def main():
    csv_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {RAW_DIR}")
        return

    total_before, total_removed, total_after = 0, 0, 0

    for file in csv_files:
        print(f"\nProcessing: {file}")
        df = pd.read_csv(file)
        df = normalize_columns(df)
        cleaned, before, removed = zscore_clean(df)
        total_before += before
        total_removed += removed
        total_after += len(cleaned)

        # Save cleaned version
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = os.path.join(CLEAN_DIR, f"cleaned_{os.path.basename(file).replace('.csv', '')}_{timestamp}.csv")
        cleaned.to_csv(out_path, index=False)
        print(f"  Rows original: {before}")
        print(f"  Rows removed:  {removed}")
        print(f"  Rows remaining: {len(cleaned)}")
        print(f"  Cleaned file saved: {out_path}")

        insert_into_db(cleaned)

    print("\n=== ETL Summary ===")
    print(f"Total rows originally: {total_before}")
    print(f"Rows removed as outliers: {total_removed}")
    print(f"Rows remaining after cleaning: {total_after}")

if __name__ == "__main__":
    main()
