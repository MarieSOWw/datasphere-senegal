"""
scripts/3_normalize_and_merge.py
═════════════════════════════════════════════════════════════════
ÉTAPE 3 — Normaliser les données PDF et les fusionner dans MongoDB

Ce script :
  1. Lit les JSONs extraits (extracted_2021.json, extracted_2022.json)
  2. Normalise les sigles (alias → sigle officiel)
  3. Aligne les groupes bancaires avec BASE_SENEGAL2.xlsx
  4. Calcule les ratios financiers
  5. Fusionne dans MongoDB (upsert sur sigle + annee)

CORRECTIONS apportées sur le script original :
  ✅ GROUPE_BANCAIRE entièrement revu et corrigé pour correspondre
     exactement à BASE_SENEGAL2.xlsx (le prof a fourni ces groupes)
     Erreurs dans l'original :
       BCIM  : "Locaux"        → "Règionaux"
       BDK   : "Locaux"        → "Règionaux"
       BIS   : "Locaux"        → "Règionaux"
       BOA   : "Règionaux"     → "Continentaux"
       BRM   : "Locaux"        → "Règionaux"
       CBAO  : "Internationaux"→ "Continentaux"
       CBI   : "Locaux"        → "Règionaux"
       CDS   : "Locaux"        → "Règionaux"
       ECOBANK:"Règionaux"     → "Continentaux"
       BGFI  : absent          → "Règionaux"
       LBA   : "Règionaux"     → "Locaux"
       LBO   : "Règionaux"     → "Locaux"
       NSIA  : "Continentaux"  → "Règionaux"
       ORABANK:"Règionaux"     → "Continentaux"

  ✅ SIGLE_ALIASES corrigés :
       "BANQUE ATLANTIQUE" → "BCIM"  (était "BAT" → banque inexistante)
       "BANQUE DU SAHEL"   → supprimé (mappait "BDK" à tort)
       "SG"                → supprimé (trop générique, risque de faux match)

  ✅ Filtre annee : > 2020 AND <= 2022 (l'original n'avait pas la borne haute)
     → évite d'insérer 2023 si un JSON traîne dans data/extracted/

  ✅ charger_json_extraits() filtrée sur [2021, 2022] uniquement

Exécution :
    python scripts/3_normalize_and_merge.py
═════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import logging
from pathlib import Path
from pymongo import UpdateOne

sys.path.append(str(Path(__file__).parent.parent))
from utils.db import get_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

BASE_DIR      = Path(__file__).parent.parent
EXTRACTED_DIR = BASE_DIR / "data" / "extracted"

# ── CORRECTION : SIGLE_ALIASES revu ───────────────────────────────────────────
# L'original avait des entrées fausses ("BAT", "BANQUE DU SAHEL"→BDK, etc.)
SIGLE_ALIASES = {
    "NSIA BANQUE":      "NSIA Banque",
    "NSIA":             "NSIA Banque",
    "BANQUE ATLANTIQUE":"BCIM",         # ← CORRECTION (était "BAT" dans l'original)
    "ATB SENEGAL":      "BCIM",
    "CITIBANK NA":      "CITIBANK",
    "BAS SENEGAL":      "BAS",
    "SOCIETE GENERALE": "SGBS",
    "SOCIÉTÉ GÉNÉRALE": "SGBS",
    "BRM SENEGAL":      "BRM",
    # "BANQUE DU SAHEL" → BDK supprimé (faux alias dans l'original)
    # "SG" → SGBS supprimé (trop générique, risque de collision)
    # "VERSUS" → supprimé (n'existe pas au Sénégal)
}

# ── CORRECTION : GROUPE_BANCAIRE conforme à BASE_SENEGAL2.xlsx ────────────────
# L'original avait ~12 groupes incorrects (voir corrections dans l'entête)
GROUPE_BANCAIRE = {
    "BAS":        "Groupes Continentaux",
    "BCIM":       "Groupes Règionaux",       # ← CORRIGÉ (était "Locaux")
    "BDK":        "Groupes Règionaux",       # ← CORRIGÉ (était "Locaux")
    "BGFI":       "Groupes Règionaux",       # ← AJOUTÉ (manquait)
    "BHS":        "Groupes Locaux",
    "BICIS":      "Groupes Internationaux",
    "BIS":        "Groupes Règionaux",       # ← CORRIGÉ (était "Locaux")
    "BNDE":       "Groupes Locaux",
    "BOA":        "Groupes Continentaux",    # ← CORRIGÉ (était "Règionaux")
    "BRM":        "Groupes Règionaux",       # ← CORRIGÉ (était "Locaux")
    "BSIC":       "Groupes Règionaux",
    "CBAO":       "Groupes Continentaux",    # ← CORRIGÉ (était "Internationaux")
    "CBI":        "Groupes Règionaux",       # ← CORRIGÉ (était "Locaux")
    "CDS":        "Groupes Règionaux",       # ← CORRIGÉ (était "Locaux")
    "CISA":       "Groupes Internationaux",
    "CITIBANK":   "Groupes Continentaux",    # ← CORRIGÉ (était "Internationaux")
    "ECOBANK":    "Groupes Continentaux",    # ← CORRIGÉ (était "Règionaux")
    "FBNBANK":    "Groupes Continentaux",
    "LBA":        "Groupes Locaux",          # ← CORRIGÉ (était "Règionaux")
    "LBO":        "Groupes Locaux",          # ← CORRIGÉ (était "Règionaux")
    "NSIA Banque":"Groupes Règionaux",       # ← CORRIGÉ (était "Continentaux")
    "ORABANK":    "Groupes Continentaux",    # ← CORRIGÉ (était "Règionaux")
    "SGBS":       "Groupes Internationaux",
    "UBA":        "Groupes Continentaux",
}


def normaliser_sigle(sigle: str) -> str:
    """Ramène les alias au sigle officiel."""
    sigle_up = sigle.upper().strip()
    for alias, officiel in SIGLE_ALIASES.items():
        if alias in sigle_up:
            return officiel
    return sigle.strip()


def calculer_ratios(record: dict) -> dict:
    """
    Calcule les 5 ratios financiers clés.
    Utilisés dans le dashboard pour l'analyse du positionnement.
    """
    def safe_div(a, b):
        try:
            return round(a / b * 100, 2) if b and b != 0 else None
        except Exception:
            return None

    bilan         = record.get("bilan")
    fonds_propres = record.get("fonds_propres")
    resultat_net  = record.get("resultat_net")
    ressources    = record.get("ressources")
    emploi        = record.get("emploi")
    pnb           = record.get("produit_net_bancaire")
    charges       = record.get("charges_generales_exploitation")

    record["ratio_solvabilite"]          = safe_div(fonds_propres, bilan)
    record["ratio_rendement_actifs"]     = safe_div(resultat_net, bilan)
    record["ratio_rentabilite_capitaux"] = safe_div(resultat_net, fonds_propres)
    record["ratio_emplois_ressources"]   = safe_div(emploi, ressources)
    record["coefficient_exploitation"]   = safe_div(charges, pnb)
    return record


def normaliser_record(record: dict) -> dict:
    """Normalise un enregistrement extrait du PDF."""
    record["sigle"]          = normaliser_sigle(record.get("sigle", ""))
    record["groupe_bancaire"]= GROUPE_BANCAIRE.get(record["sigle"], "Inconnu")
    record["annee"]          = int(record.get("annee", 0))
    record                   = calculer_ratios(record)
    return record


def charger_json_extraits() -> list:
    """
    CORRECTION : charge uniquement 2021 et 2022.
    L'original chargeait TOUS les JSONs du dossier (risque de charger 2023).
    """
    tous_records = []

    for annee in [2021, 2022]:                              # ← CORRECTION : liste fixe
        json_path = EXTRACTED_DIR / f"extracted_{annee}.json"

        if not json_path.exists():
            log.warning(f"  ⚠️  Fichier absent : {json_path.name}")
            log.warning(f"     → Exécute d'abord : python scripts/2_scrape_bceao_pdfs.py")
            continue

        log.info(f"  Lecture : {json_path.name}")
        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        log.info(f"    → {len(records)} enregistrements")
        tous_records.extend(records)

    return tous_records


def upsert_vers_mongo(records: list):
    """Insère ou met à jour les enregistrements dans MongoDB."""
    if not records:
        log.warning("Aucun enregistrement à insérer.")
        return

    col, client = get_collection()
    col.create_index([("sigle", 1), ("annee", 1)], unique=True)

    ops = [
        UpdateOne(
            {"sigle": rec["sigle"], "annee": rec["annee"]},
            {"$set": rec},
            upsert=True
        )
        for rec in records
        if rec.get("sigle") and rec.get("annee")
    ]

    if ops:
        result = col.bulk_write(ops)
        log.info(f"  Insérés  : {result.upserted_count}")
        log.info(f"  Modifiés : {result.modified_count}")
    else:
        log.warning("  Aucune opération valide.")

    client.close()


def afficher_bilan_mongo():
    """Affiche le bilan complet de la base après fusion."""
    col, client = get_collection()
    total   = col.count_documents({})
    banques = sorted(col.distinct("sigle"))
    annees  = sorted(col.distinct("annee"))
    sources = col.distinct("source")

    log.info(f"\n{'='*60}")
    log.info("  BILAN DE LA BASE DE DONNÉES MONGODB")
    log.info(f"{'='*60}")
    log.info(f"  Total documents  : {total}")
    log.info(f"  Années couvertes : {annees}")
    log.info(f"  Nb banques       : {len(banques)}")
    log.info(f"  Sources          : {sources}")
    log.info("\n  Détail par année :")
    for annee in annees:
        n  = col.count_documents({"annee": annee})
        ok = "✅" if n >= 23 else "⚠️ "
        log.info(f"    {ok} {annee} : {n} banques")

    client.close()


def main():
    log.info("=" * 60)
    log.info("  ÉTAPE 3 — Normalisation et fusion dans MongoDB")
    log.info("  Périmètre : JSONs 2021 et 2022 uniquement")
    log.info("=" * 60)

    # 1. Charger les JSONs 2021-2022
    records_bruts = charger_json_extraits()
    log.info(f"\nTotal enregistrements bruts : {len(records_bruts)}")

    if not records_bruts:
        log.error("❌ Aucun enregistrement — vérifie que l'étape 2 a été exécutée.")
        return

    # 2. Normaliser chaque enregistrement
    records_propres = []
    for rec in records_bruts:
        try:
            rec_norm = normaliser_record(rec)
            # ── CORRECTION : filtre annee > 2020 ET <= 2022 ───────────────────
            # L'original n'avait que "> 2020" sans borne haute
            if rec_norm["sigle"] and 2020 < rec_norm["annee"] <= 2022:
                records_propres.append(rec_norm)
        except Exception as e:
            log.warning(f"  Erreur normalisation : {e} | sigle={rec.get('sigle')}")

    log.info(f"Enregistrements normalisés  : {len(records_propres)}")
    for a in [2021, 2022]:
        n = sum(1 for r in records_propres if r["annee"] == a)
        log.info(f"  {a} : {n} banques")

    # 3. Fusionner dans MongoDB
    upsert_vers_mongo(records_propres)

    # 4. Bilan final
    afficher_bilan_mongo()

    log.info("\n✅ Étape 3 terminée — Lance : python scripts/4_clean_data.py")


if __name__ == "__main__":
    main()
