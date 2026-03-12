"""
scripts/0_load_all_data.py
═══════════════════════════════════════════════════════════════════
SCRIPT MAÎTRE — Charge toutes les données dans MongoDB Atlas

Étapes :
  1. Excel BASE_SENEGAL2.xlsx (banques 2015-2020) → MongoDB
  2. PDFs BCEAO (2021-2022) extraction
  3. Normalisation & fusion PDF → MongoDB
  4. Nettoyage, imputation, ratios financiers
  5. Données Assurance → MongoDB
  6. Données Énergie → MongoDB
  7. Données Santé → MongoDB

Exécution :
    python scripts/0_load_all_data.py
═══════════════════════════════════════════════════════════════════
"""

import os
import sys
import logging
import importlib.util

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║         DataSphere — Chargement MongoDB Atlas                   ║
║         Projet M2 Big Data · Analyse Multisectorielle          ║
╚══════════════════════════════════════════════════════════════════╝
"""


def load_module_from_file(module_name: str, file_name: str):
    """
    Charge un module Python à partir d'un fichier, même si le nom du fichier
    commence par un chiffre.
    """
    file_path = os.path.join(SCRIPTS_DIR, file_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger le module : {file_name}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_step(name, func):
    log.info(f"{'═' * 55}")
    log.info(f"  ▶  {name}")
    log.info(f"{'═' * 55}")
    try:
        func()
        log.info(f"  ✅ {name} — TERMINÉ\n")
        return True
    except Exception as e:
        log.error(f"  ❌ {name} — ERREUR : {e}\n")
        return False


def main():
    print(BANNER)
    results = {}

    # ── Étape 1 : Excel Bancaire ────────────────────────────────────────────
    try:
        s1_module = load_module_from_file("s1_module", "1_load_excel_to_mongo.py")
        results["Excel Bancaire"] = run_step(
            "ÉTAPE 1 — Chargement Excel Bancaire → MongoDB",
            s1_module.main
        )
    except Exception as e:
        log.error(f"  ❌ ÉTAPE 1 — ERREUR : {e}\n")
        results["Excel Bancaire"] = False

    # ── Étape 2 : Scraping PDFs BCEAO ───────────────────────────────────────
    log.info("═" * 55)
    log.info("  ▶  ÉTAPE 2 — Extraction PDFs BCEAO (2021-2022)")
    log.info("  ℹ️  Cette étape extrait les données des PDFs BCEAO")
    log.info("  ℹ️  Si les PDFs ne sont pas disponibles, elle sera ignorée")
    log.info("═" * 55)

    try:
        s2_module = load_module_from_file("s2_module", "2_scrape_bceao_pdfs.py")

        # Cas 1 : le script expose main_extract_only()
        if hasattr(s2_module, "main_extract_only"):
            s2_module.main_extract_only()
        # Cas 2 : le script expose main()
        elif hasattr(s2_module, "main"):
            s2_module.main()
        else:
            raise AttributeError(
                "Le script 2_scrape_bceao_pdfs.py ne contient ni main_extract_only() ni main()"
            )

        results["Scraping PDFs"] = True
        log.info("  ✅ Scraping PDFs — TERMINÉ\n")
    except Exception as e:
        log.warning(f"  ⚠️  Scraping PDFs ignoré : {e}\n")
        results["Scraping PDFs"] = False

    # ── Étape 3 : Normalisation & Fusion ────────────────────────────────────
    try:
        s3_module = load_module_from_file("s3_module", "3_normalize_and_merge.py")
        results["Normalisation"] = run_step(
            "ÉTAPE 3 — Normalisation & Fusion PDF → MongoDB",
            s3_module.main
        )
    except Exception as e:
        log.warning(f"  ⚠️  Normalisation ignorée : {e}\n")
        results["Normalisation"] = False

    # ── Étape 4 : Nettoyage ─────────────────────────────────────────────────
    try:
        s4_module = load_module_from_file("s4_module", "4_clean_data.py")
        results["Nettoyage"] = run_step(
            "ÉTAPE 4 — Nettoyage & Ratios Financiers",
            s4_module.main
        )
    except Exception as e:
        log.error(f"  ❌ ÉTAPE 4 — ERREUR : {e}\n")
        results["Nettoyage"] = False

    # ── Étape 5 : Assurance ─────────────────────────────────────────────────
    try:
        from scripts.load_assurance_to_mongo import main as s5
        results["Assurance"] = run_step(
            "ÉTAPE 5 — Chargement Données Assurance",
            s5
        )
    except Exception as e:
        log.error(f"  ❌ ÉTAPE 5 — ERREUR : {e}\n")
        results["Assurance"] = False

    # ── Étape 6 : Énergie ───────────────────────────────────────────────────
    try:
        from scripts.load_energie_to_mongo import main as s6
        results["Énergie"] = run_step(
            "ÉTAPE 6 — Chargement Données Énergie Solaire",
            s6
        )
    except Exception as e:
        log.error(f"  ❌ ÉTAPE 6 — ERREUR : {e}\n")
        results["Énergie"] = False

    # ── Étape 7 : Santé ─────────────────────────────────────────────────────
    try:
        from scripts.load_sante_to_mongo import main as s7
        results["Santé"] = run_step(
            "ÉTAPE 7 — Chargement Données Hospitalières",
            s7
        )
    except Exception as e:
        log.error(f"  ❌ ÉTAPE 7 — ERREUR : {e}\n")
        results["Santé"] = False

    # ── Rapport final ───────────────────────────────────────────────────────
    log.info("╔══════════════════════════════════════════╗")
    log.info("║          RAPPORT DE CHARGEMENT           ║")
    log.info("╠══════════════════════════════════════════╣")
    for name, ok in results.items():
        status = "✅ OK   " if ok else "⚠️  Skip"
        log.info(f"║  {status}  {name:<28}║")
    log.info("╚══════════════════════════════════════════╝")
    log.info("\nLancement : python app.py → http://localhost:8050")


if __name__ == "__main__":
    main()