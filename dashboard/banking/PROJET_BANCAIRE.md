# DataSphere Sénégal — Dashboard Bancaire BCEAO
### Projet M2 Big Data · Analyse Multisectorielle du Secteur Bancaire Sénégalais

---

## Table des matières

1. [Présentation du projet](#1-présentation-du-projet)
2. [Structure du projet](#2-structure-du-projet)
3. [Sources de données et extraction PDF](#3-sources-de-données-et-extraction-pdf)
4. [Installation et configuration](#4-installation-et-configuration)
5. [Étapes pour lancer l'application](#5-étapes-pour-lancer-lapplication)
6. [Pipeline de données détaillé](#6-pipeline-de-données-détaillé)
7. [Fonctionnalités du dashboard](#7-fonctionnalités-du-dashboard)
8. [KPI et indicateurs financiers](#8-kpi-et-indicateurs-financiers)
9. [Architecture technique](#9-architecture-technique)
10. [Limites connues et justifications](#10-limites-connues-et-justifications)

---

## 1. Présentation du projet

**DataSphere Sénégal** est une application web d'analyse et de visualisation des données financières du secteur bancaire sénégalais, développée dans le cadre du **Master 2 Big Data**.

Elle exploite les données publiques de la **BCEAO (Banque Centrale des États de l'Afrique de l'Ouest)** pour produire des tableaux de bord interactifs permettant d'analyser le positionnement de **23 banques** sur la période **2015–2022**, avec des projections jusqu'en **2026**.

| Caractéristique | Détail |
|---|---|
| Banques couvertes | 23 banques agréées au Sénégal |
| Période historique | 2015 – 2022 |
| Horizon prédictif | jusqu'à 2026 |
| Base de données | MongoDB Atlas (cloud) |
| Sources primaires | Excel BCEAO (2015–2020) + PDFs BCEAO (2021–2022) |

---

## 2. Structure du projet

```
datasphere/
│
├── app.py                          # Point d'entrée Flask principal
├── .env                            # Variables d'environnement (MONGO_URI, DB_NAME)
├── requirements.txt                # Dépendances Python
│
├── utils/
│   └── db.py                       # Connexion MongoDB Atlas centralisée
│
├── data/
│   ├── BASE_SENEGAL2.xlsx          # Données Excel BCEAO 2015–2020
│   ├── pdfs/                       # PDFs BCEAO téléchargés automatiquement
│   └── extracted/
│       ├── extracted_2021.json     # Données extraites des PDFs 2021
│       └── extracted_2022.json     # Données extraites des PDFs 2022
│
├── scripts/                        # Pipeline de données (à exécuter dans l'ordre)
│   ├── 0_load_all_data.py          # ★ Script maître — lance tout le pipeline
│   ├── 1_load_excel_to_mongo.py    # Étape 1 : Excel → MongoDB
│   ├── 2_scrape_bceao_pdfs.py      # Étape 2 : Web scraping + extraction PDFs BCEAO
│   ├── 3_normalize_and_merge.py    # Étape 3 : Normalisation & fusion dans MongoDB
│   ├── 4_clean_data.py             # Étape 4 : Nettoyage, imputation, ratios
│   ├── fix_mongodb.py              # Utilitaire : corrections ponctuelles MongoDB
│   └── fix_mongodb_fields.py       # Utilitaire : harmonisation des champs
│
└── dashboard/
    ├── banking/                    # ★ Dashboard Bancaire (ce projet)
    │   ├── __init__.py
    │   ├── app.py                  # Initialisation Dash sur /bancaire/
    │   ├── layout.py               # Structure HTML/Dash (5 onglets, filtres)
    │   ├── callbacks.py            # Logique interactive (45 callbacks)
    │   ├── rapport.py              # Génération PDF (ReportLab) + Export Excel
    │   └── banking_style.css       # Feuille de styles dédiée
    │
    ├── assurance/                  # Dashboard Assurance (/assurance/)
    ├── energie/                    # Dashboard Énergie (/energie/)
    └── sante/                      # Dashboard Santé (/sante/)
```

---

## 3. Sources de données et extraction PDF

### 3.1 Source principale — Fichier Excel BCEAO (2015–2020)

Le fichier `data/BASE_SENEGAL2.xlsx` (feuille `Sheet 1`) fourni par la BCEAO contient les données financières agrégées des 23 banques sénégalaises pour les années **2015 à 2020**.

Il est chargé par le script `1_load_excel_to_mongo.py` avec un mapping de colonnes vers le format `snake_case` MongoDB :

| Colonne Excel | Champ MongoDB |
|---|---|
| `BILAN` | `bilan` |
| `EMPLOI` | `emploi` |
| `RESSOURCES` | `ressources` |
| `FONDS.PROPRE` | `fonds_propres` |
| `Goupe_Bancaire` | `groupe_bancaire` |
| … (21 colonnes au total) | … |

### 3.2 Source secondaire — PDFs BCEAO (2021–2022)

Les rapports annuels BCEAO pour 2021 et 2022 sont extraits via un **pipeline en 3 couches** implémenté dans `2_scrape_bceao_pdfs.py` :

```
┌────────────────────────────────────────────────────────────┐
│  COUCHE 1 — Web Scraping (requests + BeautifulSoup)        │
│  URL : https://www.bceao.int/fr/publications/bilans-...    │
│  → Détection automatique du lien PDF le plus récent        │
│  → Fallback sur URLs directes BCEAO hardcodées            │
├────────────────────────────────────────────────────────────┤
│  COUCHE 2 — Extraction texte natif (pdfplumber)            │
│  → Parsing par coordonnées X/Y dans le PDF                 │
│  → 21 champs financiers extraits par banque et par année   │
├────────────────────────────────────────────────────────────┤
│  COUCHE 3 — OCR Fallback (pytesseract + pdf2image)         │
│  → Activé si pdfplumber retourne < 50 caractères par page  │
│  → Conversion page → image → reconnaissance de texte       │
└────────────────────────────────────────────────────────────┘
```

**Modes d'exécution du scraper :**
```bash
python scripts/2_scrape_bceao_pdfs.py                   # Pipeline complet
python scripts/2_scrape_bceao_pdfs.py --force-download  # Re-télécharge le PDF
python scripts/2_scrape_bceao_pdfs.py --pdf mon.pdf     # Utilise un PDF local
python scripts/2_scrape_bceao_pdfs.py --from-json       # Repart des JSONs existants
python scripts/2_scrape_bceao_pdfs.py --ocr-force       # Force OCR sur toutes les pages
```

**Résultat :** fichiers `data/extracted/extracted_2021.json` et `extracted_2022.json` contenant les données structurées prêtes pour MongoDB.

### 3.3 Fusion et nettoyage des données

Les deux sources (Excel + PDFs) sont fusionnées dans MongoDB par `3_normalize_and_merge.py` via un `upsert` sur la clé `(sigle, annee)`, puis nettoyées par `4_clean_data.py` :

- **Imputation** : valeurs manquantes remplacées par la médiane du groupe bancaire
- **Outliers** : détection par la méthode IQR × 3
- **Ratios** : calculés automatiquement après nettoyage si absents
- **Note** : `RESSOURCES`, `EFFECTIF`, `AGENCE`, `COMPTE` sont absents des PDFs 2021–2022 (limitation structurelle de la source BCEAO) — ces colonnes ne sont pas imputées

---

## 4. Installation et configuration

### 4.1 Prérequis système

- Python **3.9+**
- Tesseract OCR *(optionnel, pour le fallback OCR)*
  - Windows : [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux : `sudo apt install tesseract-ocr`
- Poppler *(optionnel, requis par pdf2image)*
  - Windows : [https://github.com/oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows)
  - Linux : `sudo apt install poppler-utils`

### 4.2 Installation des dépendances Python

```bash
pip install -r requirements.txt
```

Dépendances principales :

```
flask
dash
dash-bootstrap-components
plotly
pandas
numpy
pymongo[srv]
python-dotenv
pdfplumber
requests
beautifulsoup4
reportlab
openpyxl
scikit-learn
# OCR (optionnel)
pytesseract
pdf2image
Pillow
```

### 4.3 Configuration MongoDB Atlas

1. Créer un compte sur [https://cloud.mongodb.com](https://cloud.mongodb.com)
2. Créer un cluster gratuit (M0)
3. Créer un utilisateur base de données avec droits lecture/écriture
4. **Autoriser les connexions entrantes** : *Security → Network Access → Add IP Address → `0.0.0.0/0`*
5. Récupérer la chaîne de connexion : *Connect → Drivers → Python*

Créer le fichier `.env` à la racine du projet :

```env
MONGO_URI=mongodb+srv://<utilisateur>:<motdepasse>@<cluster>.mongodb.net/?retryWrites=true&w=majority
DB_NAME=banking_senegal
```

---

## 5. Étapes pour lancer l'application

### Étape 1 — Cloner et installer

```bash
git clone <url-du-repo>
cd datasphere
pip install -r requirements.txt
```

### Étape 2 — Configurer la base de données

Créer le fichier `.env` comme décrit en section 4.3.

Vérifier la connexion MongoDB :
```bash
python -c "from utils.db import ping; print('✅ Connecté' if ping() else '❌ Échec connexion')"
```

### Étape 3 — Charger les données dans MongoDB

Placer le fichier `BASE_SENEGAL2.xlsx` dans le dossier `data/`, puis exécuter le script maître :

```bash
python scripts/0_load_all_data.py
```

Ce script orchestre automatiquement les 4 étapes du pipeline :
```
1. Excel (2015–2020)     → MongoDB
2. PDFs BCEAO (2021–22)  → extraction JSON
3. Normalisation & fusion → MongoDB
4. Nettoyage & ratios    → MongoDB
```

> **Note :** si les PDFs ne peuvent pas être téléchargés automatiquement (réseau restreint), placer manuellement `bceao_bilans_2022.pdf` dans `data/pdfs/` et relancer avec `--from-json` ou `--pdf data/pdfs/bceao_bilans_2022.pdf`.

### Étape 4 — Lancer l'application Flask

```bash
python app.py
```

L'application est accessible sur : **[http://localhost:8050](http://localhost:8050)**

| Dashboard | URL |
|---|---|
| Bancaire | http://localhost:8050/bancaire/ |
| Assurance | http://localhost:8050/assurance/ |
| Énergie | http://localhost:8050/energie/ |
| Santé | http://localhost:8050/sante/ |

---

## 6. Pipeline de données détaillé

```
BASE_SENEGAL2.xlsx          PDFs BCEAO 2021-2022
(23 banques, 2015-2020)     (bceao.int)
        │                         │
        ▼                         ▼
1_load_excel_to_mongo.py    2_scrape_bceao_pdfs.py
  • Renommage snake_case      • Web scraping requests
  • Upsert (sigle, annee)     • Extraction pdfplumber
                              • OCR fallback pytesseract
        │                         │
        │                    extracted_2021.json
        │                    extracted_2022.json
        │                         │
        └──────────┬──────────────┘
                   ▼
        3_normalize_and_merge.py
          • Correction sigles (SIGLE_ALIASES)
          • Alignement groupes bancaires
          • Calcul ratios financiers
          • Upsert MongoDB
                   │
                   ▼
          4_clean_data.py
            • Détection valeurs manquantes
            • Imputation (médiane par groupe)
            • Détection outliers (IQR × 3)
            • Recalcul ratios
            • Rapport qualité
                   │
                   ▼
        MongoDB Atlas
        DB : banking_senegal
        Collection : banques_senegal
        (23 banques × 8 années × 21 champs)
                   │
                   ▼
        Dashboard Dash/Flask
        (callbacks.py — 45 callbacks)
```

---

## 7. Fonctionnalités du dashboard

### Onglet 1 — Vue d'ensemble
- 6 KPI cards en temps réel (Bilan, Emploi, Fonds propres, PNB, ROA, Ratio solvabilité)
- Évolution temporelle 2015–2022 (ligne + barres)
- Classement des banques par indicateur (barres horizontales)
- Parts de marché (donut chart)
- Graphique Emploi vs Ressources

### Onglet 2 — Fiche Banque
- Profil complet d'une banque sélectionnée
- Tableau de données historiques complet
- Radar de positionnement multidimensionnel (vs moyenne secteur)

### Onglet 3 — Comparaison Interbancaire
- Comparaison de 2 à 5 banques simultanément
- Graphiques superposés par indicateur
- Tableau de classement cross-banques

### Onglet 4 — Ratios Financiers
- Heatmap des ratios par banque et par année
- Distribution des ratios (boxplots)
- Alertes automatiques BCEAO (solvabilité ≥ 8%)
- Interprétations dynamiques sur chaque graphique

### Onglet 5 — Module Prédictif *(Bonus)*
- Régression linéaire sur données 2015–2022
- Projections à horizon configurable (jusqu'à 2026)
- Intervalles de confiance à 95%
- Score composite normalisé pour 23 banques

### Fonctionnalités transversales
- **Filtres** : Banque, Année, Indicateur, Groupe bancaire
- **Carte interactive** : Scattermapbox — localisation des 23 banques à Dakar
- **Export PDF** : Rapport de positionnement complet par banque (ReportLab)
- **Export Excel** : Données historiques multi-feuilles (openpyxl)

---

## 8. KPI et indicateurs financiers

| Champ MongoDB | Indicateur | Source |
|---|---|---|
| `bilan` | Total bilan | Excel + PDF |
| `emploi` | Emplois (crédits, placements) | Excel + PDF |
| `ressources` | Ressources (dépôts, emprunts) | Excel uniquement |
| `fonds_propres` | Fonds propres | Excel + PDF |
| `produit_net_bancaire` | PNB | Excel + PDF |
| `resultat_net` | Résultat net | Excel + PDF |
| `ratio_solvabilite` | Fonds propres / Bilan × 100 | Calculé |
| `ratio_rendement_actifs` | ROA = Résultat net / Bilan × 100 | Calculé |
| `ratio_rentabilite_capitaux` | ROE = Résultat net / Fonds propres × 100 | Calculé |
| `coefficient_exploitation` | Charges exploitation / PNB × 100 | Calculé |
| `ratio_emplois_ressources` | Emploi / Ressources × 100 *(proxy liquidité)* | Calculé |

**Norme BCEAO de référence :** ratio de solvabilité ≥ 8% (seuil prudentiel UMOA)

---

## 9. Architecture technique

| Composant | Technologie |
|---|---|
| Backend web | Flask |
| Dashboards | Plotly Dash |
| UI Components | Dash Bootstrap Components |
| Graphiques | Plotly (go.Bar, go.Scatter, Scattermapbox, go.Pie, go.Radar) |
| Base de données | MongoDB Atlas (cloud) |
| ORM | PyMongo |
| Génération PDF | ReportLab (SimpleDocTemplate) |
| Export Excel | openpyxl (ExcelWriter multi-feuilles) |
| Web Scraping | requests + BeautifulSoup4 |
| Extraction PDF | pdfplumber |
| OCR | pytesseract + pdf2image |
| Machine Learning | NumPy (np.polyfit — régression linéaire) |
| Styles | CSS custom (banking_style.css) + Google Fonts |

---

## 10. Limites connues et justifications

| Limite | Explication |
|---|---|
| **Bilan non décomposé** (actif/passif/capital) | Les publications BCEAO ne fournissent que le total bilan consolidé. La décomposition actif/passif/capital n'est pas disponible dans les rapports publics. |
| **Ressources absentes en 2021–2022** | La colonne `RESSOURCES` est présente dans les fichiers Excel BCEAO (2015–2020) mais absente des PDFs publics pour 2021–2022. Il s'agit d'une limitation structurelle de la source primaire. |
| **Carte : toutes les banques à Dakar** | L'ensemble des banques sénégalaises agréées ont leur siège social dans la région de Dakar. La carte représente donc fidèlement la réalité géographique. |
| **Ratio liquidité = proxy E/R** | Le ratio de liquidité officiel BCEAO (LCR) n'est pas publié dans les rapports publics disponibles. Le ratio Emplois/Ressources est l'approximation standard utilisée dans la littérature bancaire UEMOA. |

---

## Auteurs

Projet réalisé dans le cadre du **Master 2 Big Data** — DataSphere Sénégal  
Données sources : **BCEAO** (Banque Centrale des États de l'Afrique de l'Ouest) — [bceao.int](https://www.bceao.int)