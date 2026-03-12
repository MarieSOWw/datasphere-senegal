"""
scripts/fix_mongodb_fields.py
═══════════════════════════════════════════════════════════════════
SCRIPT DE CORRECTION — Renomme les champs corrompus dans MongoDB Atlas

Problème détecté : MongoDB Atlas stocke les champs avec des noms erronés :
  s1mp_   → sigle     (le '1' OCR au lieu de 'i')
  b1lan   → bilan     (le '1' OCR au lieu de 'i')
  année   → annee     (accent non supporté)
  résultat_net → resultat_net  (accents)
  etc.

Ce script corrige tous ces champs EN PLACE dans MongoDB Atlas
sans supprimer ni rechargement les données.

Exécution :
    python scripts/fix_mongodb_fields.py

OU recharger complètement (plus fiable) :
    python scripts/0_load_all_data.py
═══════════════════════════════════════════════════════════════════
"""

import sys
import os
import logging
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


def normalize_field_name(name: str) -> str:
    """Normalise un nom de champ MongoDB en nom standard."""
    replacements = {
        "1": "i",       # s1mp_ → simp, b1lan → bilan
        "0": "o",       # cas rare
        "\u2019": "_",  # apostrophe typographique
        "\u2018": "_",
        "'": "_",
    }
    result = str(name)
    for k, v in replacements.items():
        result = result.replace(k, v)
    # Supprimer les accents
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if unicodedata.category(c) != "Mn")
    result = result.lower().rstrip("_")
    return result


# Champs cibles standards
TARGET_FIELDS = {
    "sigle", "annee", "bilan", "emploi", "ressources", "fonds_propres",
    "produit_net_bancaire", "resultat_net", "resultat_exploitation",
    "resultat_brut_exploitation", "resultat_avant_impot",
    "interets_produits", "interets_charges", "impots_benefices",
    "charges_generales_exploitation", "cout_du_risque",
    "commissions_produits", "commissions_charges",
    "autres_produits_exploitation", "autres_charges_exploitation",
    "subventions_investissement", "dotations_amortissements",
    "gains_pertes_actifs_immobilises", "gains_pertes_negociation",
    "gains_pertes_placement", "revenus_titres_variable",
    "groupe_bancaire", "source", "effectif", "agence", "compte",
    "ratio_solvabilite", "ratio_rendement_actifs",
    "ratio_rentabilite_capitaux", "coefficient_exploitation",
    "ratio_emplois_ressources",
    "groupe_bancaire", "source", "has_outlier",
}

# Mapping spécial : normalized_name → target
SPECIAL_MAP = {
    "simp": "sigle",               # s1mp_ → sigle
    "frais_d_interet": "interets_charges",
    "frais_d_interet": "interets_charges",
}


def build_rename_map(sample_doc: dict) -> dict:
    """
    Construit le mapping {champ_corrompu: champ_correct}
    en analysant un document MongoDB.
    """
    rename_map = {}
    for field in sample_doc.keys():
        if field == "_id":
            continue

        norm = normalize_field_name(field)

        # Chercher la cible
        target = None
        if field in TARGET_FIELDS:
            continue  # déjà correct
        elif norm in TARGET_FIELDS:
            target = norm
        elif norm in SPECIAL_MAP:
            target = SPECIAL_MAP[norm]
        else:
            # Essayer de matcher partiel
            for t in TARGET_FIELDS:
                if normalize_field_name(t) == norm:
                    target = t
                    break

        if target and field != target:
            rename_map[field] = target

    return rename_map


def fix_collection():
    """Corrige les noms de champs dans la collection bancaire."""
    col, client = get_collection()

    log.info("═" * 55)
    log.info("  Analyse des champs MongoDB...")
    log.info("═" * 55)

    # Récupérer un document pour analyser les champs
    sample = col.find_one({}, {"_id": 0})
    if not sample:
        log.error("❌ Collection vide !")
        client.close()
        return

    log.info(f"  Champs trouvés ({len(sample)}) : {sorted(sample.keys())}")

    rename_map = build_rename_map(sample)

    if not rename_map:
        log.info("\n✅ Tous les champs sont déjà corrects !")
        # Vérification quand même
        _verify(col)
        client.close()
        return

    log.info(f"\n  Corrections nécessaires ({len(rename_map)}) :")
    for old, new in sorted(rename_map.items()):
        log.info(f"    '{old}' → '{new}'")

    # Construire l'opération $rename pour MongoDB
    # $rename renomme les champs EN PLACE sans toucher aux valeurs
    rename_op = {"$rename": rename_map}

    log.info(f"\n  Application des corrections sur tous les documents...")
    result = col.update_many({}, rename_op)
    log.info(f"  ✅ {result.modified_count} documents corrigés")

    # Vérification
    _verify(col)
    client.close()


def _verify(col):
    """Vérifie que les champs clés sont présents et contiennent des données."""
    log.info("\n═" * 55)
    log.info("  VÉRIFICATION POST-CORRECTION")
    log.info("═" * 55)

    total = col.count_documents({})
    log.info(f"  Total documents : {total}")

    key_fields = ["sigle", "annee", "bilan", "produit_net_bancaire", "resultat_net"]
    for field in key_fields:
        count_present = col.count_documents({field: {"$exists": True, "$ne": None}})
        status = "✅" if count_present > 0 else "❌"
        log.info(f"  {status} {field:<30} : {count_present}/{total} non-nuls")

    # Années disponibles
    annees = sorted(col.distinct("annee"))
    log.info(f"\n  Années : {annees}")

    # Banques par année
    for a in annees:
        n = col.count_documents({"annee": a})
        log.info(f"    {a} : {n} banques")


def main():
    log.info("═" * 55)
    log.info("  FIX MONGODB — Correction des noms de champs")
    log.info("═" * 55)

    fix_collection()

    log.info("\n✅ Correction terminée.")
    log.info("   Relance l'application : python app.py")


if __name__ == "__main__":
    main()