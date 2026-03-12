"""
scripts/load_sante_to_mongo.py
═══════════════════════════════════════════════════════════════════
Chargement des données hospitalières dans MongoDB (collection: sante_data)

Exécution :
    python scripts/load_sante_to_mongo.py
═══════════════════════════════════════════════════════════════════
"""

import os
import sys
import logging
import pandas as pd
from pymongo import UpdateOne

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BASE_DIR, "data", "hospital_data.csv")


def load_and_clean(path):
    log.info(f"Lecture : {path}")
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df["DateAdmission"] = pd.to_datetime(df["DateAdmission"], format="%d/%m/%Y", errors="coerce")
    df["DateSortie"]    = pd.to_datetime(df["DateSortie"],    format="%d/%m/%Y", errors="coerce")
    # Convertir dates en string pour MongoDB
    df["DateAdmission"] = df["DateAdmission"].dt.strftime("%Y-%m-%d")
    df["DateSortie"]    = df["DateSortie"].dt.strftime("%Y-%m-%d")
    df = df.where(pd.notnull(df), None)
    log.info(f"  {len(df)} patients | {len(df.columns)} colonnes")
    return df


def upsert_to_mongo(df):
    col, client = get_collection("sante_data")
    col.create_index([("PatientID", 1)], unique=True)
    records = df.to_dict(orient="records")
    ops = [UpdateOne({"PatientID": r["PatientID"]}, {"$set": r}, upsert=True) for r in records]
    result = col.bulk_write(ops)
    log.info(f"  Insérés : {result.upserted_count} | Modifiés : {result.modified_count}")
    client.close()


def main():
    log.info("=" * 55)
    log.info("  Chargement hospital_data.csv → MongoDB (sante_data)")
    log.info("=" * 55)
    df = load_and_clean(CSV_PATH)
    upsert_to_mongo(df)
    log.info("✅ Données santé chargées avec succès")


if __name__ == "__main__":
    main()
