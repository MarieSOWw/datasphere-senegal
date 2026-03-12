"""
scripts/1_load_excel_to_mongo.py
═════════════════════════════════════════════════════════════════
ÉTAPE 1 — Charger BASE_SENEGAL2.xlsx dans MongoDB

Ce script :
  1. Lit le fichier Excel (feuille "Sheet 1") — données 2015-2020
  2. Renomme toutes les colonnes en snake_case
  3. Convertit les types (NaN → None, annee → int)
  4. Insère dans MongoDB via upsert sur (sigle + annee)

Exécution :
    python scripts/1_load_excel_to_mongo.py
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

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(BASE_DIR, "data", "BASE_SENEGAL2.xlsx")

# ── Mapping colonnes Excel → snake_case MongoDB ────────────────────────────────
COLUMN_RENAME = {
    "Sigle":            "sigle",
    "Goupe_Bancaire":   "groupe_bancaire",
    "ANNEE":            "annee",
    "EMPLOI":           "emploi",
    "BILAN":            "bilan",
    "RESSOURCES":       "ressources",
    "FONDS.PROPRE":     "fonds_propres",
    "EFFECTIF":         "effectif",
    "AGENCE":           "agence",
    "COMPTE":           "compte",
    "INTERETS.ET.PRODUITS.ASSIMILES":
        "interets_produits",
    "NTERETS.ET.CHARGES.ASSIMILEES":
        "interets_charges",
    "REVENUS.DES.TITRES.A.REVENU.VARIABLE":
        "revenus_titres_variable",
    "COMMISSIONS.(PRODUITS)":
        "commissions_produits",
    "COMMISSIONS.(CHARGES)":
        "commissions_charges",
    "GAINS.OU.PERTES.NETS.SUR.OPERATIONS.DES.PORTEFEUILLES.DE.NEGOCIATION":
        "gains_pertes_negociation",
    "GAINS.OU.PERTES.NETS.SUR.OPERATIONS.DES.PORTEFEUILLES.DE.PLACEMENT.ET.ASSIMILES":
        "gains_pertes_placement",
    "AUTRES.PRODUITS.D'EXPLOITATION.BANCAIRE":
        "autres_produits_exploitation",
    "AUTRES.CHARGES.D'EXPLOITATION.BANCAIRE":
        "autres_charges_exploitation",
    "PRODUIT.NET.BANCAIRE":
        "produit_net_bancaire",
    "SUBVENTIONS.D'INVESTISSEMENT":
        "subventions_investissement",
    "CHARGES.GENERALES.D'EXPLOITATION":
        "charges_generales_exploitation",
    "DOTATIONS.AUX.AMORTISSEMENTS.ET.AUX.DEPRECIATIONS.DES.IMMOBILISATIONS.INCORPORELLES.ET.CORPORELLES":
        "dotations_amortissements",
    "RESULTAT.BRUT.D'EXPLOITATION":
        "resultat_brut_exploitation",
    "COÛT.DU.RISQUE":
        "cout_du_risque",
    "RESULTAT.D'EXPLOITATION":
        "resultat_exploitation",
    "GAINS.OU.PERTES.NETS.SUR.ACTIFS.IMMOBILISES":
        "gains_pertes_actifs_immobilises",
    "RESULTAT.AVANT.IMPÔT":
        "resultat_avant_impot",
    "IMPÔTS.SUR.LES.BENEFICES":
        "impots_benefices",
    "RESULTAT.NET":
        "resultat_net",
}


def load_and_clean_excel(path: str) -> pd.DataFrame:
    log.info(f"Lecture du fichier : {path}")
    df = pd.read_excel(path, sheet_name="Sheet 1")   # feuille vérifiée
    df.rename(columns=COLUMN_RENAME, inplace=True)
    df = df.where(pd.notnull(df), None)
    df["annee"]  = df["annee"].astype(int)
    df["source"] = "excel_base_senegal2"
    log.info(f"  {len(df)} lignes | {len(df.columns)} colonnes")
    log.info(f"  Banques : {sorted(df['sigle'].unique())}")
    log.info(f"  Années  : {sorted(df['annee'].unique())}")
    return df


def upsert_to_mongo(df: pd.DataFrame):
    col, client = get_collection()
    col.create_index([("sigle", 1), ("annee", 1)], unique=True)

    records = df.to_dict(orient="records")

    # ── CORRECTION : nettoyage des NaN résiduels avant insertion ──────────────
    # pandas peut laisser des float("nan") que MongoDB rejette
    for rec in records:
        for k, v in list(rec.items()):
            if isinstance(v, float) and np.isnan(v):
                rec[k] = None
    # ──────────────────────────────────────────────────────────────────────────

    ops = [
        UpdateOne(
            {"sigle": rec["sigle"], "annee": rec["annee"]},
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
    col, client = get_collection()
    total   = col.count_documents({})
    banques = col.distinct("sigle")
    annees  = col.distinct("annee")
    log.info("VÉRIFICATION MONGODB :")
    log.info(f"  Total documents : {total}")
    log.info(f"  Banques ({len(banques)}) : {sorted(banques)}")
    log.info(f"  Années  : {sorted(annees)}")
    log.info("  Détail par année :")
    for a in sorted(annees):
        n = col.count_documents({"annee": a})
        log.info(f"    {a} : {n} banques")
    client.close()


def main():
    log.info("=" * 60)
    log.info("  ÉTAPE 1 — Chargement BASE_SENEGAL2.xlsx → MongoDB")
    log.info("  Source : données 2015-2020 fournies par le professeur")
    log.info("=" * 60)
    df = load_and_clean_excel(EXCEL_PATH)
    upsert_to_mongo(df)
    verifier_mongo()
    log.info("\n Étape 1 terminée — Lance : python scripts/2_scrape_bceao_pdfs.py")


if __name__ == "__main__":
    main()