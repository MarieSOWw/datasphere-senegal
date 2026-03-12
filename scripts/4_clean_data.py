"""
scripts/4_clean_data.py
═════════════════════════════════════════════════════════════════
ÉTAPE 4 — Nettoyage et validation des données dans MongoDB

Ce script :
  1. Détecte et signale les valeurs manquantes
  2. Impute les valeurs manquantes (médiane par groupe bancaire)
  3. Détecte les outliers (méthode IQR × 3)
  4. Vérifie la cohérence des données métier
  5. Recalcule les ratios financiers après nettoyage
  6. Sauvegarde le tout dans MongoDB
  7. Génère un rapport de qualité

CORRECTIONS apportées sur le script original :
  ✅ COLONNES_NUMERIQUES séparées en deux listes :
       - COLONNES_COMMUNES    : présentes dans Excel ET PDFs → imputables
       - COLONNES_EXCEL_ONLY  : absentes des PDFs (RESSOURCES, EFFECTIF,
         AGENCE, COMPTE) → NULL structurel, on n'impute PAS ces colonnes
         car elles sont normalement absentes pour 2021-2022
  ✅ L'imputation ne touche que les COLONNES_COMMUNES pour éviter de
     remplir des colonnes structurellement vides
  ✅ Rapport des manquants : distinction NULL normal vs NULL problématique
  ✅ Rapport final : ajout du taux de complétude par source

Exécution :
    python scripts/4_clean_data.py
═════════════════════════════════════════════════════════════════
"""

import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from pymongo import UpdateOne

sys.path.append(str(Path(__file__).parent.parent))
from utils.db import get_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

# ── CORRECTION : deux listes séparées ─────────────────────────────────────────
# Colonnes présentes dans les DEUX sources (Excel 2015-2020 + PDFs 2021-2022)
# → on peut imputer les valeurs manquantes
COLONNES_COMMUNES = [
    "bilan", "emploi", "fonds_propres",
    "produit_net_bancaire", "resultat_net",
    "interets_produits", "interets_charges",
    "commissions_produits", "commissions_charges",
    "charges_generales_exploitation", "cout_du_risque",
    "resultat_brut_exploitation", "resultat_exploitation",
    "resultat_avant_impot", "impots_benefices",
]

# Colonnes présentes UNIQUEMENT dans l'Excel (2015-2020)
# → NULL normal pour 2021-2022 (absentes des PDFs BCEAO) — NE PAS IMPUTER
COLONNES_EXCEL_ONLY = [
    "ressources", "effectif", "agence", "compte",
]

# Pour rétrocompatibilité (rapport, coherence)
COLONNES_NUMERIQUES = COLONNES_COMMUNES + COLONNES_EXCEL_ONLY


def mongo_vers_dataframe() -> pd.DataFrame:
    """Charge toute la collection MongoDB dans un DataFrame pandas."""
    col, client = get_collection()
    docs = list(col.find({}, {"_id": 0}))
    client.close()

    df = pd.DataFrame(docs)
    log.info(f"  {len(df)} documents chargés depuis MongoDB")
    log.info(f"  Années  : {sorted(df['annee'].unique())}")
    log.info(f"  Banques : {len(df['sigle'].unique())}")
    return df


def rapport_valeurs_manquantes(df: pd.DataFrame):
    """
    Affiche le rapport des valeurs manquantes par colonne.
    CORRECTION : distingue les NULL normaux (Excel only) des vrais manquants.
    """
    log.info(f"\n{'─'*60}")
    log.info("  RAPPORT VALEURS MANQUANTES")
    log.info(f"{'─'*60}")
    log.info(f"  {'COLONNE':<47} {'MANQUANTS':>9} {'%':>6}  NOTE")

    for col in COLONNES_COMMUNES:
        if col not in df.columns:
            continue
        nb   = df[col].isnull().sum()
        pct  = nb / len(df) * 100
        flag = "✅" if nb == 0 else ("⚠️ " if pct > 30 else "⬜")
        if nb > 0:
            log.info(f"  {flag} {col:<45} {nb:>9} {pct:>5.1f}%  → à imputer")

    log.info(f"\n  Colonnes structurellement NULL pour 2021-2022 (absentes des PDFs) :")
    for col in COLONNES_EXCEL_ONLY:
        if col not in df.columns:
            continue
        nb  = df[col].isnull().sum()
        pct = nb / len(df) * 100
        log.info(f"  ℹ️  {col:<45} {nb:>9} {pct:>5.1f}%  → NULL normal")


def imputer_valeurs_manquantes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute les valeurs manquantes par la médiane du groupe bancaire.
    CORRECTION : imputation uniquement sur COLONNES_COMMUNES.
    Les colonnes EXCEL_ONLY (ressources, effectif, etc.) ne sont pas imputées.
    """
    log.info(f"\n{'─'*60}")
    log.info("  IMPUTATION DES VALEURS MANQUANTES")
    log.info(f"  Stratégie : médiane par groupe_bancaire → médiane globale")
    log.info(f"  Colonnes concernées : COLONNES_COMMUNES uniquement")
    log.info(f"{'─'*60}")

    for col in COLONNES_COMMUNES:          # ← CORRECTION : était COLONNES_NUMERIQUES
        if col not in df.columns:
            continue

        nb_avant = df[col].isnull().sum()
        if nb_avant == 0:
            continue

        # Médiane par groupe bancaire
        mediane_groupe = df.groupby("groupe_bancaire")[col].transform("median")
        df[col] = df[col].fillna(mediane_groupe)

        # Si toujours NaN → médiane globale
        mediane_globale = df[col].median()
        df[col] = df[col].fillna(mediane_globale)

        nb_apres = df[col].isnull().sum()
        log.info(f"  {col:<47} : {nb_avant:>3} → {nb_apres:>3} manquants")

    return df


def detecter_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte les outliers avec la méthode IQR × 3.
    Marque les outliers (flag has_outlier) mais ne les supprime pas.
    """
    log.info(f"\n{'─'*60}")
    log.info("  DÉTECTION DES OUTLIERS (méthode IQR × 3)")
    log.info(f"{'─'*60}")

    df["has_outlier"] = False
    total = 0

    for col in ["bilan", "emploi", "resultat_net", "fonds_propres"]:
        if col not in df.columns:
            continue

        Q1  = df[col].quantile(0.25)
        Q3  = df[col].quantile(0.75)
        IQR = Q3 - Q1

        borne_inf = Q1 - 3 * IQR
        borne_sup = Q3 + 3 * IQR

        outliers_mask = (df[col] < borne_inf) | (df[col] > borne_sup)
        nb            = outliers_mask.sum()

        if nb > 0:
            df.loc[outliers_mask, "has_outlier"] = True
            total += nb
            log.info(f"\n  {col} : {nb} outlier(s)")
            log.info(f"    Bornes : [{borne_inf:,.0f} ; {borne_sup:,.0f}]")
            for _, row in df[outliers_mask][["sigle", "annee", col]].iterrows():
                log.info(f"    → {row['sigle']} ({row['annee']}) : {row[col]:,.0f}")

    if total == 0:
        log.info("  ✅ Aucun outlier détecté")

    return df


def verifier_coherence(df: pd.DataFrame) -> int:
    """Vérifie des règles de cohérence métier sur les données bancaires."""
    log.info(f"\n{'─'*60}")
    log.info("  VÉRIFICATION COHÉRENCE MÉTIER")
    log.info(f"{'─'*60}")

    erreurs = []

    # Règle 1 : Bilan > Emploi
    if "bilan" in df.columns and "emploi" in df.columns:
        mask = df["bilan"].notna() & df["emploi"].notna() & (df["bilan"] < df["emploi"])
        for _, row in df[mask].iterrows():
            erreurs.append(f"  ❌ bilan < emploi → {row['sigle']} ({row['annee']})")

    # Règle 2 : Fonds propres positifs
    if "fonds_propres" in df.columns:
        mask = df["fonds_propres"].notna() & (df["fonds_propres"] < 0)
        for _, row in df[mask].iterrows():
            erreurs.append(f"  ⚠️  fonds_propres négatifs → {row['sigle']} ({row['annee']})")

    # Règle 3 : Bilan non nul
    if "bilan" in df.columns:
        mask = df["bilan"].isnull() | (df["bilan"] == 0)
        for _, row in df[mask].iterrows():
            erreurs.append(f"  ❌ bilan nul/manquant → {row['sigle']} ({row['annee']})")

    if erreurs:
        for e in erreurs:
            log.warning(e)
    else:
        log.info("  ✅ Toutes les règles de cohérence sont respectées")

    return len(erreurs)


def recalculer_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Recalcule les ratios financiers après nettoyage."""
    log.info(f"\n{'─'*60}")
    log.info("  RECALCUL DES RATIOS FINANCIERS")
    log.info(f"{'─'*60}")

    def safe_div(a, b):
        try:
            result = a / b * 100
            return result.round(2)
        except Exception:
            return None

    if all(c in df.columns for c in ["fonds_propres", "bilan"]):
        df["ratio_solvabilite"] = safe_div(df["fonds_propres"], df["bilan"])
        log.info("  ✅ ratio_solvabilite    = fonds_propres / bilan × 100")

    if all(c in df.columns for c in ["resultat_net", "bilan"]):
        df["ratio_rendement_actifs"] = safe_div(df["resultat_net"], df["bilan"])
        log.info("  ✅ ratio_rendement_actifs (ROA) = resultat_net / bilan × 100")

    if all(c in df.columns for c in ["resultat_net", "fonds_propres"]):
        df["ratio_rentabilite_capitaux"] = safe_div(df["resultat_net"], df["fonds_propres"])
        log.info("  ✅ ratio_rentabilite_capitaux (ROE) = resultat_net / fonds_propres × 100")

    if all(c in df.columns for c in ["emploi", "ressources"]):
        df["ratio_emplois_ressources"] = safe_div(df["emploi"], df["ressources"])
        log.info("  ✅ ratio_emplois_ressources = emploi / ressources × 100")

    if all(c in df.columns for c in ["charges_generales_exploitation", "produit_net_bancaire"]):
        df["coefficient_exploitation"] = safe_div(
            df["charges_generales_exploitation"], df["produit_net_bancaire"]
        )
        log.info("  ✅ coefficient_exploitation = charges_generales / PNB × 100")

    return df


def sauvegarder_dans_mongo(df: pd.DataFrame):
    """Sauvegarde le DataFrame nettoyé dans MongoDB."""
    col, client = get_collection()
    records = df.to_dict(orient="records")

    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and np.isnan(v):
                rec[k] = None

    ops = [
        UpdateOne(
            {"sigle": rec["sigle"], "annee": rec["annee"]},
            {"$set": rec},
            upsert=True
        )
        for rec in records
        if rec.get("sigle") and rec.get("annee")
    ]

    result = col.bulk_write(ops)
    log.info(f"  Documents mis à jour : {result.modified_count + result.upserted_count}")
    client.close()


def rapport_final(df: pd.DataFrame):
    """Génère un rapport de qualité des données."""
    log.info(f"\n{'='*60}")
    log.info("  RAPPORT FINAL DE QUALITÉ DES DONNÉES")
    log.info(f"{'='*60}")
    log.info(f"  Total enregistrements  : {len(df)}")
    log.info(f"  Banques couvertes      : {len(df['sigle'].unique())}")
    log.info(f"  Années couvertes       : {sorted(df['annee'].unique())}")

    # Taux de complétude global (colonnes communes uniquement)
    cols = [c for c in COLONNES_COMMUNES if c in df.columns]
    completude_globale = (1 - df[cols].isnull().mean().mean()) * 100
    log.info(f"  Taux de complétude     : {completude_globale:.1f}%  (colonnes communes)")

    # Taux de complétude par source
    log.info(f"\n  Taux de complétude par source :")
    for src in sorted(df["source"].unique()):
        g    = df[df["source"] == src]
        cols_src = [c for c in COLONNES_COMMUNES if c in g.columns]
        tx   = (1 - g[cols_src].isnull().mean().mean()) * 100
        log.info(f"    {src:<30} : {tx:.1f}%  ({len(g)} enregistrements)")

    if "has_outlier" in df.columns:
        log.info(f"\n  Outliers détectés      : {int(df['has_outlier'].sum())}")

    log.info(f"\n  Bilan moyen par année (en millions FCFA) :")
    if "bilan" in df.columns:
        for a in sorted(df["annee"].unique()):
            g = df[df["annee"] == a]
            log.info(f"    {a} : {g['bilan'].mean():>14,.0f}  (n={len(g)} banques)")

    log.info(f"\n  PNB total par année :")
    if "produit_net_bancaire" in df.columns:
        for a in sorted(df["annee"].unique()):
            g = df[df["annee"] == a]
            log.info(f"    {a} : {g['produit_net_bancaire'].sum():>14,.0f}")


def main():
    log.info("=" * 60)
    log.info("  ÉTAPE 4 — Nettoyage et validation des données")
    log.info("=" * 60)

    # 1. Charger depuis MongoDB
    df = mongo_vers_dataframe()
    if df.empty:
        log.error("❌ MongoDB vide — exécute les étapes 1, 2 et 3 d'abord.")
        return

    # 2. Rapport valeurs manquantes
    rapport_valeurs_manquantes(df)

    # 3. Imputation (colonnes communes uniquement)
    df = imputer_valeurs_manquantes(df)

    # 4. Détection outliers
    df = detecter_outliers(df)

    # 5. Vérification cohérence
    nb_erreurs = verifier_coherence(df)

    # 6. Recalcul des ratios
    df = recalculer_ratios(df)

    # 7. Sauvegarder
    sauvegarder_dans_mongo(df)

    # 8. Rapport final
    rapport_final(df)

    log.info(f"\n{'='*60}")
    log.info(f"  ✅ Étape 4 terminée — {nb_erreurs} incohérence(s) détectée(s)")
    log.info("  Lance maintenant : python dashboard/app.py")
    log.info(f"{'='*60}")


if __name__ == "__main__":
    main()
