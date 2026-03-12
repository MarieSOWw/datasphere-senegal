"""
scripts/fix_mongodb.py
═══════════════════════════════════════════════════════════════════
SCRIPT DE CORRECTION MONGODB — À lancer UNE seule fois avant app.py

Corrections appliquées :
  1. Renomme "simp_" → "sigle" (champ mal nommé lors de l'import Excel)
  2. Corrige groupe_bancaire "Groupes Régionaux" → "Groupes Règionaux"
  3. Recalcule tous les ratios financiers manquants

Usage :
    python scripts/fix_mongodb.py
    python scripts/fix_mongodb.py --dry-run  (simulation)
═══════════════════════════════════════════════════════════════════
"""
import sys, math, logging, argparse
from pathlib import Path
from pymongo import UpdateOne

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.db import get_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

GROUPE_PAR_SIGLE = {
    "BAS": "Groupes Continentaux",    "BCIM": "Groupes Règionaux",
    "BDK": "Groupes Règionaux",       "BGFI": "Groupes Règionaux",
    "BHS": "Groupes Locaux",          "BICIS": "Groupes Internationaux",
    "BIS": "Groupes Règionaux",       "BNDE": "Groupes Locaux",
    "BOA": "Groupes Continentaux",    "BRM": "Groupes Règionaux",
    "BSIC": "Groupes Règionaux",      "CBAO": "Groupes Continentaux",
    "CBI": "Groupes Règionaux",       "CDS": "Groupes Règionaux",
    "CISA": "Groupes Internationaux", "CITIBANK": "Groupes Continentaux",
    "ECOBANK": "Groupes Continentaux","FBNBANK": "Groupes Continentaux",
    "LBA": "Groupes Locaux",          "LBO": "Groupes Locaux",
    "NSIA Banque": "Groupes Règionaux","ORABANK": "Groupes Continentaux",
    "SGBS": "Groupes Internationaux", "UBA": "Groupes Continentaux",
}


def _sf(val):
    if val is None: return None
    try:
        f = float(str(val).replace(" ", "").replace(",", ".").strip())
        return None if math.isnan(f) or math.isinf(f) else f
    except: return None


def _ratios(doc):
    def sd(a, b):
        a, b = _sf(a), _sf(b)
        return round(a / b * 100, 4) if (a and b and b != 0) else None
    return {
        "ratio_solvabilite":          sd(doc.get("fonds_propres"),               doc.get("bilan")),
        "ratio_rendement_actifs":     sd(doc.get("resultat_net"),                doc.get("bilan")),
        "ratio_rentabilite_capitaux": sd(doc.get("resultat_net"),                doc.get("fonds_propres")),
        "ratio_emplois_ressources":   sd(doc.get("emploi"),                      doc.get("ressources")),
        "coefficient_exploitation":   sd(doc.get("charges_generales_exploitation"), doc.get("produit_net_bancaire")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    DR = args.dry_run
    if DR: log.info("MODE DRY-RUN — aucune modification\n")

    col, client = get_collection()
    try:
        total   = col.count_documents({})
        simp_nb = col.count_documents({"simp_": {"$exists": True}})
        log.info(f"Total docs : {total}  |  docs avec 'simp_' : {simp_nb}")

        # 1. simp_ → sigle
        if simp_nb:
            log.info(f"\n[1/3] Renommage 'simp_' → 'sigle' sur {simp_nb} documents...")
            if not DR:
                col.update_many(
                    {"simp_": {"$exists": True}},
                    [{"$set": {"sigle": {"$trim": {"input": "$simp_"}}}}, {"$unset": "simp_"}]
                )
                log.info("  ✅ Renommage effectué")
        else:
            log.info("\n[1/3] ✅ Pas de champ 'simp_'")

        # 2. Corriger groupe_bancaire
        log.info("\n[2/3] Correction groupe_bancaire...")
        docs = list(col.find({"sigle": {"$exists": True}}, {"_id": 1, "sigle": 1, "groupe_bancaire": 1}))
        ops2 = []
        for d in docs:
            sigle = str(d.get("sigle", "")).strip()
            cible = GROUPE_PAR_SIGLE.get(sigle)
            if cible and d.get("groupe_bancaire") != cible:
                ops2.append(UpdateOne({"_id": d["_id"]}, {"$set": {"groupe_bancaire": cible}}))
        if ops2:
            log.info(f"  {len(ops2)} corrections à appliquer")
            if not DR:
                col.bulk_write(ops2)
                log.info(f"  ✅ {len(ops2)} groupe_bancaire corrigés")
        else:
            log.info("  ✅ groupe_bancaire déjà corrects")

        # 3. Recalcul ratios
        log.info("\n[3/3] Recalcul ratios financiers...")
        docs_all = list(col.find({"sigle": {"$exists": True}}, {"_id": 0}))
        ops3 = []
        for d in docs_all:
            if d.get("sigle") and d.get("annee") is not None:
                ops3.append(UpdateOne(
                    {"sigle": d["sigle"], "annee": d["annee"]},
                    {"$set": _ratios(d)}
                ))
        if ops3 and not DR:
            col.bulk_write(ops3)
        log.info(f"  ✅ {len(ops3)} ratios {'recalculés' if not DR else 'auraient été recalculés'}")

        if not DR:
            log.info("\n✅ MongoDB corrigé — relance maintenant : python app.py")

    finally:
        client.close()


if __name__ == "__main__":
    main()