"""
scripts/2_scrape_bceao_pdfs.py  — VERSION FINALE CORRIGÉE
═══════════════════════════════════════════════════════════════════════════════
ÉTAPE 2 — Web Scraping + Extraction PDF BCEAO

CORRECTIONS v3 :
  ✅ LABEL_TO_FIELD garde les accents (comme l'original) → 21 champs extraits
  ✅ normaliser_label() ne supprime PAS les accents (cohérence avec LABEL_TO_FIELD)
  ✅ construire_records() filtre sur [2021, 2022] uniquement (pas 2020 — déjà dans Excel)
  ✅ sauvegarder_json() idem — only 2021/2022
  ✅ main_extract_only() ajoutée → appelable depuis 0_load_all_data.py
  ✅ Web scraping BCEAO (requests + BeautifulSoup) avec fallback URLs directes
  ✅ OCR fallback pytesseract pour pages scannées (si pdfplumber retourne < 50 chars)

ARCHITECTURE (3 couches) :
  Couche 1 — Web Scraping  : téléchargement automatique PDF depuis bceao.int
  Couche 2 — pdfplumber    : extraction texte natif par coordonnées X/Y
  Couche 3 — OCR fallback  : pytesseract sur pages scannées/illisibles

EXÉCUTION :
  python scripts/2_scrape_bceao_pdfs.py                  # pipeline complet
  python scripts/2_scrape_bceao_pdfs.py --force-download  # re-télécharge le PDF
  python scripts/2_scrape_bceao_pdfs.py --pdf mon.pdf    # PDF local
  python scripts/2_scrape_bceao_pdfs.py --from-json      # depuis JSONs existants
  python scripts/2_scrape_bceao_pdfs.py --ocr-force      # force OCR toutes pages

DÉPENDANCES :
  pip install pdfplumber requests beautifulsoup4 pytesseract pdf2image Pillow
  + Tesseract OCR Engine : https://github.com/UB-Mannheim/tesseract/wiki
  + Poppler (Windows)    : https://github.com/oschwartz10612/poppler-windows
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import re
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import pdfplumber
import numpy as np

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))
from utils.db import get_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

PDF_DIR       = BASE_DIR / "data" / "pdfs"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
PDF_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

# ── Dépendances OCR (optionnelles) ───────────────────────────────────────────
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
    log.info("OCR disponible (pytesseract + pdf2image)")
except ImportError:
    OCR_AVAILABLE = False
    log.warning(
        "OCR non disponible — pip install pytesseract pdf2image Pillow\n"
        "   + Tesseract : https://github.com/UB-Mannheim/tesseract/wiki"
    )

# Décommenter si Tesseract n'est pas dans le PATH Windows :
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

BCEAO_PAGE_URL = (
    "https://www.bceao.int/fr/publications/"
    "bilans-et-comptes-de-resultat-des-banques-"
    "etablissements-financiers-et-compagnies"
)

BCEAO_PDF_DIRECT_URLS = [
    "https://www.bceao.int/sites/default/files/2024-05/"
    "Bilans%20et%20comptes%20de%20r%C3%A9sultat%20des%20banques%2C%20"
    "%C3%A9tablissements%20financiers%20et%20compagnies%20financi%C3%A8res%20"
    "de%20l%27UMOA%202022.pdf",
    "https://www.bceao.int/sites/default/files/2023-09/"
    "Bilans_et_comptes_de_resultat_des_banques_"
    "etablissements_financiers_et_compagnies_financieres_de_l_UMOA_2022.pdf",
]

PDF_LOCAL_NAME = "bceao_bilans_2022.pdf"

SIGLE_MAP = {
    "SGSN": "SGBS", "BICIS": "BICIS", "CBAO": "CBAO", "C.D.S.": "CDS",
    "B.H.S.": "BHS", "CITIBANK": "CITIBANK", "LBA": "LBA", "B.I.S.": "BIS",
    "ECOBANK": "ECOBANK", "ORABANK": "ORABANK", "BOA-S": "BOA", "BSIC": "BSIC",
    "BIMAO": "BCIM", "B.A-S.": "BAS", "B.A.-S.": "BAS", "B.R.M.": "BRM",
    "U.B.A.": "UBA", "FBNBANK": "FBNBANK", "CI": "CBI", "CBI-SENEGAL": "CBI",
    "B.N.D.E": "BNDE", "NSIA BANQUE": "NSIA Banque", "BDK": "BDK",
    "BGFI BANK": "BGFI", "LBO": "LBO",
}

GROUPES = {
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

# ✅ CRITIQUE : garder les accents — doit être cohérent avec normaliser_label()
# normaliser_label() normalise UNIQUEMENT les apostrophes, pas les accents
LABEL_TO_FIELD = {
    "intérêts et produits assimilés":              "interets_produits",
    "intérêts et charges assimilées":              "interets_charges",
    "revenus des titres à revenu variable":        "revenus_titres_variable",
    "commissions (produits)":                      "commissions_produits",
    "commissions (charges)":                       "commissions_charges",
    "gains ou pertes nets sur opérations des portefeuilles de négociation":
                                                   "gains_pertes_negociation",
    "gains ou pertes nets sur opérations des portefeuilles de placement et assimilés":
                                                   "gains_pertes_placement",
    "autres produits d'exploitation bancaire":     "autres_produits_exploitation",
    "autres charges d'exploitation bancaire":      "autres_charges_exploitation",
    "produit net bancaire":                        "produit_net_bancaire",
    "subventions d'investissement":                "subventions_investissement",
    "charges générales d'exploitation":            "charges_generales_exploitation",
    "dotation aux amortissements et aux dépréciations des immobilisations incorporelles et corporelles":
                                                   "dotations_amortissements",
    "dotation aux amortissements":                 "dotations_amortissements",
    "resultat brut d'exploitation":                "resultat_brut_exploitation",
    "coût du risque":                              "cout_du_risque",
    "resultat d'exploitation":                     "resultat_exploitation",
    "gains ou pertes nets sur actifs immobilisés": "gains_pertes_actifs_immobilises",
    "resultat avant impôt":                        "resultat_avant_impot",
    "impôts sur les bénéfices":                    "impots_benefices",
    "resultat net":                                "resultat_net",
    "total de l'actif":                            "bilan",
    "capitaux propres et ressources assimilées":   "fonds_propres",
    "créances sur la clientèle":                   "emploi",
    "dettes à l'égard de la clientèle":            "ressources",
}

# Patterns OCR pour pages scannées
OCR_PATTERNS = {
    "bilan":                 r"total\s+de\s+l.actif\s+([\d\s\-.,]+)",
    "fonds_propres":         r"capitaux\s+propres\s+et\s+ressources\s+assimil.es\s+([\d\s\-.,]+)",
    "emploi":                r"cr.ances\s+sur\s+la\s+client.le\s+([\d\s\-.,]+)",
    "ressources":            r"dettes\s+.+?gard\s+de\s+la\s+client.le\s+([\d\s\-.,]+)",
    "produit_net_bancaire":  r"produit\s+net\s+bancaire\s+([\d\s\-.,]+)",
    "resultat_net":          r"r.sultat\s+net\s+([\d\s\-.,]+)",
    "cout_du_risque":        r"co.t\s+du\s+risque\s+([\d\s\-.,]+)",
    "charges_generales_exploitation": r"charges\s+g.n.rales\s+d.exploitation\s+([\d\s\-.,]+)",
}


# ══════════════════════════════════════════════════════════════════════════════
#  COUCHE 1 — WEB SCRAPING
# ══════════════════════════════════════════════════════════════════════════════

def scraper_lien_pdf_depuis_page(url: str, session: requests.Session):
    """Visite la page BCEAO et extrait le lien vers le PDF 2022 via BeautifulSoup."""
    log.info(f"  Scraping de la page BCEAO : {url}")
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            href_lower = href.lower()
            if (
                href_lower.endswith(".pdf")
                and ("bilan" in href_lower or "compte" in href_lower)
                and "2022" in href_lower
            ):
                pdf_url = href if href.startswith("http") else "https://www.bceao.int" + href
                log.info(f"  Lien PDF trouvé : {pdf_url}")
                return pdf_url
        log.warning("  Aucun lien PDF 2022 trouvé sur la page")
        return None
    except Exception as e:
        log.warning(f"  Erreur scraping page : {e}")
        return None


def telecharger_pdf_bceao(force: bool = False) -> str:
    """
    Télécharge le PDF BCEAO automatiquement.
    Stratégie : scraping page → URLs directes → PDF local existant.
    """
    pdf_path = PDF_DIR / PDF_LOCAL_NAME

    if pdf_path.exists() and not force:
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        log.info(f"  PDF déjà présent ({size_mb:.1f} Mo) : {pdf_path.name}")
        log.info("  Utiliser --force-download pour re-télécharger")
        return str(pdf_path)

    log.info("=" * 60)
    log.info("  COUCHE 1 — WEB SCRAPING BCEAO")
    log.info("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    })

    # Niveau 1 : scraping de la page
    pdf_url = scraper_lien_pdf_depuis_page(BCEAO_PAGE_URL, session)

    # Niveau 2 : URLs directes de secours
    if not pdf_url:
        log.info("  Essai URLs directes de secours...")
        for url in BCEAO_PDF_DIRECT_URLS:
            try:
                test = session.head(url, timeout=15, allow_redirects=True)
                if test.status_code == 200:
                    pdf_url = url
                    log.info(f"  URL directe valide : {url}")
                    break
                log.warning(f"  HTTP {test.status_code} : {url}")
            except Exception as e:
                log.warning(f"  Inaccessible : {e}")

    # Niveau 3 : PDF local existant
    if not pdf_url:
        existing = list(PDF_DIR.glob("*.pdf"))
        if existing:
            log.warning(f"  Réseau inaccessible → PDF local : {existing[0].name}")
            return str(existing[0])
        raise RuntimeError(
            f"Impossible de télécharger le PDF BCEAO.\n"
            f"Téléchargez manuellement depuis :\n{BCEAO_PAGE_URL}\n"
            f"et placez-le dans : {PDF_DIR}"
        )

    # Téléchargement en streaming
    log.info(f"  Téléchargement : {pdf_url}")
    resp = session.get(pdf_url, timeout=120, stream=True)
    resp.raise_for_status()

    total_bytes = int(resp.headers.get("content-length", 0))
    downloaded  = 0
    with open(pdf_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_bytes:
                    pct = downloaded / total_bytes * 100
                    print(f"\r  Progression : {pct:5.1f}% ({downloaded/1e6:.1f}/{total_bytes/1e6:.1f} Mo)", end="")
    print()
    log.info(f"  ✅ PDF téléchargé : {pdf_path.name} ({downloaded/1e6:.1f} Mo)")
    return str(pdf_path)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def normaliser_label(text: str) -> str:
    """
    ✅ Normalise UNIQUEMENT les apostrophes typographiques → '
    NE supprime PAS les accents — doit rester cohérent avec LABEL_TO_FIELD.
    """
    t = text.lower().strip()
    for apos in ["\u2019", "\u2018", "\u02bc", "\u02b9", "\u00b4", "\u02bb"]:
        t = t.replace(apos, "'")
    return re.sub(r"\s+", " ", t)


def tokens_to_float(tokens: list):
    if not tokens:
        return None
    s = "".join(tokens).replace(" ", "").replace("\u202f", "").replace("\xa0", "")
    try:
        return float(s)
    except Exception:
        return None


def normaliser_sigle(raw: str) -> str:
    raw = raw.strip()
    if raw in SIGLE_MAP:
        return SIGLE_MAP[raw]
    for k, v in SIGLE_MAP.items():
        if k.upper() == raw.upper():
            return v
    return raw


def trouver_page_senegal(pdf) -> int:
    """Cherche la 1ère page dont la PREMIÈRE ligne est exactement 'SENEGAL'."""
    for i, page in enumerate(pdf.pages):
        text  = page.extract_text() or ""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if lines and lines[0].upper() == "SENEGAL":
            return i
    log.warning("Section Sénégal introuvable → fallback page 261")
    return 260


# ══════════════════════════════════════════════════════════════════════════════
#  COUCHE 2 — EXTRACTION pdfplumber (PDF natif)
# ══════════════════════════════════════════════════════════════════════════════

def est_page_native(page) -> bool:
    """True si la page contient du texte natif (> 50 chars) → pdfplumber suffit."""
    return len((page.extract_text() or "").strip()) > 50


def extraire_par_coordonnees(page) -> dict:
    """
    Extraction par coordonnées X/Y (pdfplumber).
    Détecte les colonnes 2020/2021/2022 par position des en-têtes d'années.
    """
    words = page.extract_words(keep_blank_chars=False, x_tolerance=3, y_tolerance=3)
    if not words:
        return {}

    year_cols = {}
    for w in words:
        if w["text"] in ("2020", "2021", "2022"):
            year_cols[int(w["text"])] = (w["x0"] + w["x1"]) / 2

    if len(year_cols) < 2:
        return {}

    if 2020 not in year_cols and 2021 in year_cols and 2022 in year_cols:
        year_cols[2020] = year_cols[2021] - (year_cols[2022] - year_cols[2021])

    sy = sorted(year_cols)
    boundaries = {}
    for i, yr in enumerate(sy):
        cx    = year_cols[yr]
        left  = (year_cols[sy[i - 1]] + cx) / 2 if i > 0 else cx - 80
        right = (cx + year_cols[sy[i + 1]]) / 2 if i < len(sy) - 1 else cx + 80
        boundaries[yr] = (left, right)

    LABEL_MAX_X = boundaries[sy[0]][0]

    rows_dict = {}
    for w in words:
        y = round(w["top"] / 5) * 5
        rows_dict.setdefault(y, []).append(w)

    label_parts, num_parts = {}, {}
    for y_key in sorted(rows_dict):
        rw  = sorted(rows_dict[y_key], key=lambda w: w["x0"])
        lws = []
        cns = {2020: [], 2021: [], 2022: []}
        for w in rw:
            cx = (w["x0"] + w["x1"]) / 2
            if cx < LABEL_MAX_X:
                lws.append(w["text"])
            else:
                placed = False
                for yr in [2020, 2021, 2022]:
                    lb, rb = boundaries.get(yr, (0, 0))
                    if lb <= cx <= rb:
                        cns[yr].append(w["text"])
                        placed = True
                        break
                if not placed:
                    closest = min(year_cols, key=lambda y: abs(year_cols[y] - cx))
                    cns[closest].append(w["text"])
        label_parts[y_key] = lws
        num_parts[y_key]   = cns

    result = {}
    ys = sorted(label_parts.keys())
    i  = 0
    while i < len(ys):
        y        = ys[i]
        lp       = label_parts[y]
        np_      = num_parts[y]
        has_nums = any(v for v in np_.values())

        if lp:
            lt = " ".join(lp)
            if not has_nums:
                if (i + 1 < len(ys)
                        and label_parts[ys[i + 1]]
                        and not any(v for v in num_parts[ys[i + 1]].values())):
                    lt += " " + " ".join(label_parts[ys[i + 1]])
                    i += 1
                elif (i + 1 < len(ys)
                      and not label_parts[ys[i + 1]]
                      and any(v for v in num_parts[ys[i + 1]].values())):
                    np_ = num_parts[ys[i + 1]]
                    i += 1

            ln = normaliser_label(lt)
            if ln in LABEL_TO_FIELD:
                result[LABEL_TO_FIELD[ln]] = {
                    yr: tokens_to_float(np_.get(yr, []))
                    for yr in [2020, 2021, 2022]
                }
        i += 1

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  COUCHE 3 — FALLBACK OCR (pages scannées)
# ══════════════════════════════════════════════════════════════════════════════

def page_vers_image(pdf_path: str, page_num: int, dpi: int = 300):
    """Convertit une page PDF en image 300 DPI pour l'OCR (pdf2image + Poppler)."""
    if not OCR_AVAILABLE:
        return None
    try:
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_num + 1,
            last_page=page_num + 1,
            fmt="RGB",
        )
        return images[0] if images else None
    except Exception as e:
        log.warning(f"    OCR — Erreur conversion image : {e}")
        return None


def parser_nombre_ocr(texte_brut: str) -> list:
    """Extrait 3 nombres depuis une chaîne OCR brute → [val_2020, val_2021, val_2022]."""
    texte_nettoye = re.sub(r"[^\d\s\-.,]", " ", texte_brut)
    nombres = re.findall(r"-?\s*[\d][\d\s]*(?:[.,]\d+)?", texte_nettoye)
    valeurs = []
    for n in nombres[:3]:
        try:
            valeurs.append(float(n.replace(" ", "").replace(",", ".")))
        except ValueError:
            valeurs.append(None)
    while len(valeurs) < 3:
        valeurs.append(None)
    return valeurs[:3]


def extraire_par_ocr(pdf_path: str, page_num: int) -> dict:
    """
    Couche 3 — OCR pytesseract pour pages scannées.
    Processus : conversion image 300 DPI → niveaux de gris → Tesseract fra+eng → regex.
    """
    if not OCR_AVAILABLE:
        return {}

    log.info(f"    OCR — Conversion page {page_num + 1} (300 DPI)...")
    img = page_vers_image(pdf_path, page_num, dpi=300)
    if img is None:
        return {}

    # Pré-traitement : niveaux de gris (améliore Tesseract)
    img_gris = img.convert("L")

    log.info(f"    OCR — Reconnaissance Tesseract (fra+eng)...")
    try:
        texte_ocr = pytesseract.image_to_string(
            img_gris,
            lang="fra+eng",
            config="--psm 6 --oem 3",
        )
    except Exception as e:
        log.warning(f"    OCR — Tesseract erreur : {e}")
        return {}

    if not texte_ocr or len(texte_ocr.strip()) < 20:
        log.warning(f"    OCR — Texte trop court (page vierge ?)")
        return {}

    log.info(f"    OCR — {len(texte_ocr)} caractères extraits")

    texte_lower = normaliser_label(texte_ocr)
    result = {}
    for champ, pattern in OCR_PATTERNS.items():
        match = re.search(pattern, texte_lower, re.IGNORECASE)
        if match:
            valeurs = parser_nombre_ocr(match.group(1))
            result[champ] = {2020: valeurs[0], 2021: valeurs[1], 2022: valeurs[2]}
            log.info(f"    OCR → {champ} : {valeurs}")

    if not result:
        log.warning(f"    OCR — Aucun champ reconnu (page {page_num + 1})")
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATEUR — Extraction intelligente
# ══════════════════════════════════════════════════════════════════════════════

def extraire_page_intelligente(page, pdf_path: str, page_num: int,
                                force_ocr: bool = False) -> tuple:
    """
    Couche 2 (pdfplumber) en priorité → Couche 3 (OCR) si page scannée/vide.
    Retourne (dict_résultats, méthode_utilisée).
    """
    if not force_ocr and est_page_native(page):
        result = extraire_par_coordonnees(page)
        if result:
            return result, "pdfplumber"

    if OCR_AVAILABLE:
        log.info(f"    Fallback OCR — page {page_num + 1}")
        result = extraire_par_ocr(pdf_path, page_num)
        if result:
            return result, "ocr"

    return {}, "aucun"


def extraire_toutes_banques(pdf_path: str, force_ocr: bool = False) -> dict:
    log.info(f"Ouverture PDF : {pdf_path}")
    all_data       = {}
    stats_methodes = {"pdfplumber": 0, "ocr": 0, "aucun": 0}

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        log.info(f"  {total} pages au total")

        start = trouver_page_senegal(pdf)
        log.info(f"  Section Sénégal détectée à la page {start + 1}")

        bank_pages = {}
        SKIP = {
            "banques et établissements financiers",
            "banques et etablissements financiers",
            "banques", "etablissements financiers", "établissements financiers",
        }

        for i in range(start, min(start + 150, total)):
            text  = pdf.pages[i].extract_text() or ""
            lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
            if not lines or lines[0].upper() != "SENEGAL":
                break
            sp = lines[1].strip() if len(lines) > 1 else ""
            pt = lines[2].strip().lower() if len(lines) > 2 else ""
            if sp.lower() in SKIP or any(x in sp.lower() for x in ["banques et", "établissements", "financiers"]):
                continue
            if sp not in bank_pages:
                bank_pages[sp] = {}
            if "bilan" in pt:
                bank_pages[sp]["bilan"] = i
            elif "résultat" in pt or "resultat" in pt:
                bank_pages[sp]["cr"] = i

        log.info(f"  {len(bank_pages)} banques/établissements détectés")

        for sp, pages in bank_pages.items():
            so = normaliser_sigle(sp)
            if so not in GROUPES:
                continue
            log.info(f"  Extraction : {sp} → {so}")
            db = {}

            for pk in ("bilan", "cr"):
                if pk not in pages:
                    continue
                page_num = pages[pk]
                extracted, methode = extraire_page_intelligente(
                    pdf.pages[page_num], pdf_path, page_num, force_ocr=force_ocr
                )
                stats_methodes[methode] = stats_methodes.get(methode, 0) + 1

                for f, v in extracted.items():
                    if f not in db:
                        db[f] = v
                    else:
                        for yr in [2020, 2021, 2022]:
                            if db[f].get(yr) is None and v.get(yr) is not None:
                                db[f][yr] = v[yr]

            if db:
                if so in all_data:
                    for f, v in db.items():
                        if f not in all_data[so]:
                            all_data[so][f] = v
                        else:
                            for yr in [2020, 2021, 2022]:
                                if all_data[so][f].get(yr) is None and v.get(yr) is not None:
                                    all_data[so][f][yr] = v[yr]
                else:
                    all_data[so] = db
                log.info(f"    → {len(all_data[so])} champs")
            else:
                log.warning(f"    → AUCUN champ pour {so}")

    log.info(f"  Extraction terminée : {len(all_data)} banques")
    log.info(
        f"  Méthodes → pdfplumber: {stats_methodes['pdfplumber']} pages | "
        f"OCR: {stats_methodes['ocr']} pages | "
        f"Échec: {stats_methodes['aucun']} pages"
    )
    return all_data


# ══════════════════════════════════════════════════════════════════════════════
#  PERSISTANCE — JSON + MongoDB
# ══════════════════════════════════════════════════════════════════════════════

def construire_records(all_data: dict) -> list:
    """
    ✅ FILTRE sur [2021, 2022] uniquement.
    2020 est déjà dans MongoDB via BASE_SENEGAL2.xlsx (données du prof).
    On l'extrait quand même du PDF pour validation croisée mais on ne l'insère pas.
    """
    records = []
    for sigle, data in all_data.items():
        for annee in [2021, 2022]:          # ← 2020 exclu volontairement
            rec = {
                "sigle":           sigle,
                "annee":           annee,
                "groupe_bancaire": GROUPES.get(sigle, "Inconnu"),
                "source":          "pdf_bceao_2022",
                "extracted_at":    datetime.utcnow().isoformat(),
            }
            for field, vals in data.items():
                val = vals.get(annee)
                if isinstance(val, float) and np.isnan(val):
                    val = None
                rec[field] = val
            records.append(rec)
    return records


def sauvegarder_json(records: list):
    """✅ Sauvegarde uniquement extracted_2021.json et extracted_2022.json."""
    by_year = {2021: [], 2022: []}          # ← 2020 exclu
    for r in records:
        if r["annee"] in by_year:
            by_year[r["annee"]].append(r)
    for annee, recs in by_year.items():
        out = EXTRACTED_DIR / f"extracted_{annee}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=2, default=str)
        log.info(f"  Sauvegardé : {out.name} ({len(recs)} records)")


def upsert_records_mongo(records: list):
    from pymongo import UpdateOne
    col, client = get_collection()
    col.create_index([("sigle", 1), ("annee", 1)], unique=True)
    ops = [
        UpdateOne(
            {"sigle": r["sigle"], "annee": r["annee"]},
            {"$set": r},
            upsert=True,
        )
        for r in records if r.get("sigle") and r.get("annee")
    ]
    if ops:
        res = col.bulk_write(ops)
        log.info(f"  MongoDB — Insérés: {res.upserted_count} | Modifiés: {res.modified_count}")
    client.close()


def run_extraction(pdf_path: str, force_ocr: bool = False) -> list:
    log.info("=" * 60)
    log.info("  ÉTAPE 2 — Extraction PDF BCEAO (pdfplumber + OCR fallback)")
    log.info("  Périmètre insertion MongoDB : 2021 et 2022 uniquement")
    log.info("=" * 60)
    all_data = extraire_toutes_banques(pdf_path, force_ocr=force_ocr)
    records  = construire_records(all_data)   # filtre 2021-2022
    sauvegarder_json(records)
    upsert_records_mongo(records)
    log.info(f"✅ {len(records)} records insérés (2 ans × {len(all_data)} banques)")
    return records


def afficher_resume(records: list):
    import pandas as pd
    df = pd.DataFrame(records)
    if df.empty:
        return
    print("\n" + "=" * 65)
    print("  RÉSUMÉ — EXTRACTION PDF BCEAO")
    print("=" * 65)
    print(f"  Banques : {df['sigle'].nunique()} | "
          f"Années insérées : {sorted(df['annee'].unique())} | "
          f"Records : {len(df)}")
    KEY = ["bilan", "emploi", "ressources", "fonds_propres",
           "produit_net_bancaire", "resultat_net"]
    print("\n  Taux de complétion :")
    for f in KEY:
        if f in df.columns:
            pct = df[f].notna().sum() / len(df) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"  {f:<38} [{bar}] {pct:5.1f}%")
    missing = [s for s in GROUPES if s not in df["sigle"].values]
    if missing:
        print(f"\n  ⚠️  Banques manquantes : {missing}")
    else:
        print("\n  ✅ Toutes les banques du périmètre extraites")
    print()
    ocr_status = "✅ disponible (fallback actif)" if OCR_AVAILABLE else "⚠️  non disponible"
    print(f"  OCR pytesseract : {ocr_status}")


# ══════════════════════════════════════════════════════════════════════════════
#  POINTS D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main_extract_only():
    """
    ✅ Point d'entrée pour 0_load_all_data.py
    Appelé via : from scripts.s2_scrape import main_extract_only
    (renommer ce fichier en s2_scrape.py dans scripts/)
    """
    pdf_path = telecharger_pdf_bceao(force=False)
    records  = run_extraction(pdf_path, force_ocr=False)
    afficher_resume(records)
    return records


def main():
    """Point d'entrée CLI avec arguments."""
    parser = argparse.ArgumentParser(
        description="DataSphere — Web Scraping BCEAO + Extraction PDF"
    )
    parser.add_argument("--pdf",            type=str, default=None,
                        help="PDF local (désactive le téléchargement web)")
    parser.add_argument("--force-download", action="store_true",
                        help="Re-télécharge même si le PDF existe déjà")
    parser.add_argument("--from-json",      action="store_true",
                        help="Recharge depuis les JSONs existants → upsert MongoDB")
    parser.add_argument("--ocr-force",      action="store_true",
                        help="Force OCR sur toutes les pages")
    parser.add_argument("--extract-only",   action="store_true",
                        help="Extraction seulement (sans upsert MongoDB)")
    args = parser.parse_args()

    if args.from_json:
        records = []
        for a in (2021, 2022):              # ← seulement 2021-2022
            jp = EXTRACTED_DIR / f"extracted_{a}.json"
            if jp.exists():
                with open(jp, "r", encoding="utf-8") as f:
                    records.extend(json.load(f))
        log.info(f"Rechargé {len(records)} records depuis JSON")
        if not args.extract_only:
            upsert_records_mongo(records)
    else:
        if args.pdf:
            pdf_path = args.pdf
            log.info(f"PDF fourni manuellement : {pdf_path}")
        else:
            pdf_path = telecharger_pdf_bceao(force=args.force_download)

        records = run_extraction(pdf_path, force_ocr=args.ocr_force)

    afficher_resume(records)
    log.info("✅ Étape 2 OK — Lance : python scripts/3_normalize_and_merge.py")


if __name__ == "__main__":
    main()