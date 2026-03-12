"""
scripts/0_load_energie_to_mongo.py
═════════════════════════════════════════════════════════════════
ÉTAPE 0B — Charger salar_data.csv (énergie solaire) dans MongoDB
Collection : energie_data (base : banking_senegal partagée)

Ce script :
  1. Lit le fichier CSV salar_data (séparateur ';')
  2. Nettoie les types (DateTime, numériques, NaN → None)
  3. Insère par batch (35 000+ lignes) via insert_many

Colonnes source :
  Date;Time;DateTime;Country;DC_Power;AC_Power;
  Ambient_Temperature;Module_Temperature;Irradiation;
  Day;Month;Hour;Daily_Yield;Total_Yield

Exécution :
    python scripts/0_load_energie_to_mongo.py
═════════════════════════════════════════════════════════════════
"""

import sys
import os
import logging
import math
import numpy as np
import pandas as pd
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BASE_DIR, "data", "salar_data.csv")
COLLECTION_NAME = "energie_data"
BATCH_SIZE = 5000


def load_and_clean_csv(path: str) -> pd.DataFrame:
    log.info(f"Lecture du fichier : {path}")
    df = pd.read_csv(path, sep=';')

    # Conversion DateTime
    df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
    # Stocker en string ISO pour MongoDB
    df['DateTime'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Colonnes numériques
    numeric_cols = [
        'DC_Power', 'AC_Power', 'Ambient_Temperature',
        'Module_Temperature', 'Irradiation', 'Daily_Yield', 'Total_Yield'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    int_cols = ['Day', 'Month', 'Hour']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    # Nettoyage NaN → None
    df = df.where(pd.notnull(df), None)

    df['source'] = 'csv_salar_data'
    log.info(f"  {len(df)} lignes | colonnes : {list(df.columns)}")
    return df


def clean_record(rec: dict) -> dict:
    """Nettoie un enregistrement pour MongoDB (NaN, types pandas)."""
    cleaned = {}
    for k, v in rec.items():
        if v is None:
            cleaned[k] = None
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif hasattr(v, 'item'):  # numpy/pandas types
            try:
                item = v.item()
                cleaned[k] = None if (isinstance(item, float) and math.isnan(item)) else item
            except Exception:
                cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def insert_to_mongo(df: pd.DataFrame):
    col, client = get_collection(COLLECTION_NAME)

    # Supprimer les données existantes pour repartir proprement
    deleted = col.delete_many({})
    log.info(f"  Données précédentes supprimées : {deleted.deleted_count}")

    # Créer un index sur DateTime + Country pour les requêtes fréquentes
    col.create_index([("DateTime", 1), ("Country", 1)])
    col.create_index([("Month", 1), ("Hour", 1)])

    records = df.to_dict(orient="records")
    total_inserted = 0

    # Insertion par batch pour éviter les timeouts
    for i in range(0, len(records), BATCH_SIZE):
        batch = [clean_record(r) for r in records[i:i + BATCH_SIZE]]
        col.insert_many(batch, ordered=False)
        total_inserted += len(batch)
        log.info(f"  Batch {i // BATCH_SIZE + 1} inséré : {total_inserted}/{len(records)} lignes")

    client.close()


def verifier_mongo():
    col, client = get_collection(COLLECTION_NAME)
    total    = col.count_documents({})
    pays     = col.distinct("Country")
    mois     = sorted(col.distinct("Month"))

    # Statistiques de puissance
    pipeline = [
        {"$group": {
            "_id": None,
            "dc_power_moy": {"$avg": "$DC_Power"},
            "ac_power_moy": {"$avg": "$AC_Power"},
            "irrad_moy":    {"$avg": "$Irradiation"},
        }}
    ]
    stats = list(col.aggregate(pipeline))

    log.info("VÉRIFICATION MongoDB — collection energie_data :")
    log.info(f"  Total documents : {total}")
    log.info(f"  Pays / Sites    : {pays}")
    log.info(f"  Mois disponibles: {mois}")
    if stats:
        s = stats[0]
        log.info(f"  DC Power moyen  : {s.get('dc_power_moy', 0):.2f} kW")
        log.info(f"  AC Power moyen  : {s.get('ac_power_moy', 0):.2f} kW")
        log.info(f"  Irradiation moy : {s.get('irrad_moy', 0):.4f}")
    client.close()


def main():
    log.info("=" * 60)
    log.info("  ÉTAPE 0B — Chargement salar_data.csv → MongoDB")
    log.info("=" * 60)
    df = load_and_clean_csv(CSV_PATH)
    insert_to_mongo(df)
    verifier_mongo()
    log.info("\n✅ Collection 'energie_data' chargée dans MongoDB")


if __name__ == "__main__":
    main()