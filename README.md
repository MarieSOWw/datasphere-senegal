# 🌐 DataSphere — Plateforme d'Analyse Multisectorielle

> **Projet M2 Big Data** — Visualisation interactive avec Flask + Dash + MongoDB Atlas

## 📋 Présentation

DataSphere est une plateforme Flask orchestrant **4 dashboards Dash** :

| Dashboard | URL | Description |
|---|---|---|
| 🏦 **Bancaire** | `/bancaire/` | Positionnement des banques au Sénégal (BCEAO) — **projet central** |
| 🛡️ **Assurance** | `/assurance/` | Analyse du portefeuille d'assurance (1 000 assurés) |
| ☀️ **Énergie** | `/energie/` | Production solaire DC/AC (35 000+ relevés) |
| 🏥 **Santé** | `/sante/` | Analyse hospitalière (500 patients) |

## 🏗️ Architecture du Projet

```
datasphere/
├── app.py                          # Point d'entrée Flask + orchestration
├── .env                            # Configuration MongoDB Atlas
├── requirements.txt
├── README.md
│
├── utils/
│   └── db.py                       # Connexion MongoDB centralisée
│
├── dashboard/
│   ├── banking/
│   │   ├── app.py                  # Init Dash bancaire
│   │   ├── layout.py               # Layout dark premium
│   │   ├── callbacks.py            # Tous les callbacks
│   │   └── rapport.py              # Génération PDF par banque
│   ├── assurance/
│   │   ├── app.py
│   │   └── layout.py               # Dashboard assurance
│   ├── energie/
│   │   ├── app.py
│   │   └── layout.py               # Dashboard énergie solaire
│   └── sante/
│       ├── app.py
│       ├── layout.py               # Layout hospitalier original
│       ├── callbacks.py            # Callbacks hospitaliers
│       └── assets/
│           └── hospital_style.css  # CSS original préservé
│
├── scripts/
│   ├── 0_load_all_data.py          # 🚀 Script maître (lance tout)
│   ├── 1_load_excel_to_mongo.py    # Excel 2015-2020 → MongoDB
│   ├── 2_scrape_bceao_pdfs.py      # Scraping + OCR PDFs BCEAO
│   ├── 3_normalize_and_merge.py    # Fusion & normalisation sigles
│   ├── 4_clean_data.py             # Nettoyage, imputation, ratios
│   ├── load_assurance_to_mongo.py  # CSV Assurance → MongoDB
│   ├── load_energie_to_mongo.py    # CSV Énergie → MongoDB
│   └── load_sante_to_mongo.py      # CSV Hôpital → MongoDB
│
├── data/
│   ├── BASE_SENEGAL2.xlsx          # Données prof 2015-2020
│   ├── assurance_data_1000.csv
│   ├── salar_data.csv
│   ├── hospital_data.csv
│   └── extracted/pdfs/             # PDFs téléchargés BCEAO
│
├── templates/
│   └── base.html                   # Landing page (dark animated)
└── assets/
    ├── style.css                   # CSS global dark premium
    └── hospital_style.css          # CSS dashboard santé (original)
```

---

## ⚡ Installation rapide sur VS Code

### Étape 1 — Cloner et ouvrir

```bash
# Ouvrir le dossier datasphere/ dans VS Code
code datasphere/
```

### Étape 2 — Créer un environnement virtuel

```bash
# Dans le terminal VS Code (Ctrl+`)
python -m venv venv

# Activer (Windows)
venv\Scripts\activate

# Activer (Mac/Linux)
source venv/bin/activate
```

### Étape 3 — Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 4 — Vérifier la configuration MongoDB

Le fichier `.env` est déjà configuré :
```env
MONGO_URI=<votre_mongo_uri>
DB_NAME=banking_senegal
```

Tester la connexion :
```bash
python -c "from utils.db import ping; print('MongoDB OK' if ping() else 'Connexion échouée')"
```

### Étape 5 — Charger les données dans MongoDB

```bash
# Option A : Tout charger en une seule commande (recommandé)

   # Données bancaires 2015-2020
python scripts/load_assurance_to_mongo.py # Données assurance
python scripts/load_energie_to_mongo.py   # Données énergie
python scripts/load_sante_to_mongo.py     # Données hospitalières

# Option B : Extraction BCEAO 2021-2022 complète (optionnel)
python scripts/2_scrape_bceao_pdfs.py --extract-only
python scripts/3_normalize_and_merge.py
python scripts/4_clean_data.py
```

### Étape 6 — Lancer l'application

```bash
python app.py
```

Ouvrir dans le navigateur : **http://localhost:8050**

---

## 🗂️ Collections MongoDB Atlas

| Collection | Données | Documents |
|---|---|---|
| `banques_senegal` | Données BCEAO 2015-2022 | ~180+ docs |
| `assurance_data` | Portefeuille assurance | 1 000 docs |
| `energie_data` | Production solaire | 35 136 docs |
| `sante_data` | Données hospitalières | 500 docs |

---

## 📊 Dashboard Bancaire — Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| **KPI Cards** | Bilan, PNB, Résultat Net, Fonds Propres |
| **Évolution temporelle** | Courbes multi-banques 2015-2022 |
| **Classement** | Top banques par indicateur |
| **Ratios financiers** | ROA, ROE, Solvabilité, Coeff. Exploitation |
| **Parts de marché** | Donut chart par groupe bancaire |
| **Emploi & Ressources** | Bar chart groupé |
| **Radar** | Profil financier normalisé |
| **Carte Sénégal** | Positionnement géographique Mapbox |
| **Rapport PDF** | Génération automatique par banque/année |

### Filtres disponibles
- **Banque** : toutes les banques BCEAO (23+)
- **Année** : 2015 à 2023 (selon disponibilité)
- **Indicateur** : Bilan, PNB, Résultat Net, Fonds Propres, Emploi, Ressources
- **Groupe** : Locaux, Régionaux, Continentaux, Internationaux

---

## 🔗 Sources de Données

| Source | Données | Période |
|---|---|---|
| **BASE_SENEGAL2.xlsx** | Données prof (Excel) | 2015-2020 |
| **BCEAO PDFs** | Bilans et comptes de résultat | 2021-2022 |
| **URL BCEAO** | https://www.bceao.int/fr/publications/bilans-et-comptes-de-resultat-des-banques-etablissements-financiers-et-compagnies | - |

---

## 🚀 Déploiement (Render / Railway / Heroku)

### Procfile
```
web: gunicorn app:server
```

### Variables d'environnement à configurer
```
MONGO_URI = <votre_mongo_uri>
DB_NAME   = banking_senegal
```

---

## 🛠️ Technologies

- **Flask** 2.3+ — Orchestration des dashboards
- **Dash** 2.14+ — Dashboards interactifs
- **Plotly** 5.18+ — Visualisations
- **MongoDB Atlas** — Base de données cloud
- **PyMongo** 4.6+ — Driver MongoDB
- **Pandas** 2.0+ — Manipulation données
- **pdfplumber** — Extraction PDFs BCEAO
- **ReportLab** — Génération rapports PDF
- **dash-bootstrap-components** — UI/UX

---

## 📁 Données BCEAO — Extraction PDFs

Le script `2_scrape_bceao_pdfs.py` extrait automatiquement les données depuis :
```
https://www.bceao.int/sites/default/files/2023-09/Bilans_et_comptes_de_resultat_des_banques_2022.pdf
```

**Pipeline complet** :
```bash
python scripts/2_scrape_bceao_pdfs.py   # Télécharge + extrait les PDFs
python scripts/3_normalize_and_merge.py  # Normalise et fusionne dans MongoDB
python scripts/4_clean_data.py           # Nettoie et calcule les ratios
```

---

## 💡 Bonnes Pratiques

- Toutes les données sont en **MongoDB Atlas** (pas de fichiers locaux requis)
- Le dashboard bancaire utilise un **upsert** (sigle + année) pour éviter les doublons
- Les ratios financiers (ROA, ROE, Solvabilité) sont calculés automatiquement
- Le rapport PDF est généré à la demande pour chaque banque sélectionnée

---

*© 2025 DataSphere · M2 Big Data · Développé avec Flask + Dash + MongoDB*
