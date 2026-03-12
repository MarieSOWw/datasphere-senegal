"""
scripts/0_load_assurance_to_mongo.py
═════════════════════════════════════════════════════════════════
ÉTAPE 0A — Charger assurance_data_1000.csv dans MongoDB
Collection : assurance_data (base : banking_senegal partagée)

Ce script :
  1. Lit le fichier CSV assurance (séparateur ';')
  2. Nettoie les types (dates, NaN → None)
  3. Insère via upsert sur id_assure

Exécution :
    python scripts/0_load_assurance_to_mongo.py
═════════════════════════════════════════════════════════════════
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from pymongo import MongoClient, UpdateOne

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH  = os.path.join(BASE_DIR, "data", "assurance_data_1000.csv")
COLLECTION_NAME = "assurance_data"


def load_and_clean_csv(path: str) -> pd.DataFrame:
    log.info(f"Lecture du fichier : {path}")
    df = pd.read_csv(path, sep=';')

    # Conversion de la date
    df['date_derniere_sinistre'] = pd.to_datetime(
        df['date_derniere_sinistre'], errors='coerce'
    )
    # Convertir datetime en string ISO pour MongoDB
    df['date_derniere_sinistre'] = df['date_derniere_sinistre'].dt.strftime('%Y-%m-%d')

    # Nettoyage des NaN → None
    df = df.where(pd.notnull(df), None)

    # Assurer les bons types numériques
    for col in ['age', 'duree_contrat', 'nb_sinistres']:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    for col in ['montant_prime', 'montant_sinistres', 'bonus_malus']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['source'] = 'csv_assurance_data'

    log.info(f"  {len(df)} lignes | colonnes : {list(df.columns)}")
    return df


def upsert_to_mongo(df: pd.DataFrame):
    col, client = get_collection(COLLECTION_NAME)
    col.create_index([("id_assure", 1)], unique=True)

    records = df.to_dict(orient="records")

    # Nettoyage des NaN résiduels et types pandas non sérialisables
    for rec in records:
        for k, v in list(rec.items()):
            if isinstance(v, float) and np.isnan(v):
                rec[k] = None
            # Convertir les entiers pandas Int64 en int Python natif
            try:
                import pandas as pd_inner
                if pd_inner.isna(v):
                    rec[k] = None
                elif hasattr(v, 'item'):
                    rec[k] = v.item()
            except Exception:
                pass

    ops = [
        UpdateOne(
            {"id_assure": rec["id_assure"]},
            {"$set": rec},
            upsert=True
        )
        for rec in records
    ]
    result = col.bulk_write(ops)
    log.info(f"  Insérés  : {result.upserted_count}")
    log.info(f"  Modifiés : {result.modified_count}")
    client.close()


def verifier_mongo():
    col, client = get_collection(COLLECTION_NAME)
    total = col.count_documents({})
    types = col.distinct("type_assurance")
    regions = col.distinct("region")
    log.info("VÉRIFICATION MongoDB — collection assurance_data :")
    log.info(f"  Total documents    : {total}")
    log.info(f"  Types d'assurance  : {sorted(types)}")
    log.info(f"  Régions            : {sorted(regions)}")
    client.close()


def main():
    log.info("=" * 60)
    log.info("  ÉTAPE 0A — Chargement assurance_data_1000.csv → MongoDB")
    log.info("=" * 60)
    df = load_and_clean_csv(CSV_PATH)
    upsert_to_mongo(df)
    verifier_mongo()
    log.info("\n✅ Collection 'assurance_data' chargée dans MongoDB")


if __name__ == "__main__":
    main()