"""
app.py — DataSphere · Point d'entrée principal
═══════════════════════════════════════════════════════════════════
Flask orchestre 4 dashboards Dash :
  /              → Page d'accueil (landing page)
  /bancaire/     → Dashboard Bancaire  (Dash — projet central BCEAO)
  /assurance/    → Dashboard Assurance (Dash)
  /energie/      → Dashboard Énergie Solaire (Dash)
  /sante/        → Dashboard Santé — Analyse Hospitalière (Dash)

Lancement : python app.py  →  http://127.0.0.1:8050
═══════════════════════════════════════════════════════════════════
"""

import os
import sys
import threading
import webbrowser

from flask import Flask, render_template, redirect, url_for

# ── Ajouter le dossier racine au path ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── 1. Serveur Flask ──────────────────────────────────────────────────────────
server = Flask(__name__, template_folder="templates")
server.secret_key = "datasphere-secret-2024"


# ── 2. Routes Flask ───────────────────────────────────────────────────────────
@server.route("/")
def home():
    return render_template("base.html")


@server.route("/accueil")
def accueil_redirect():
    return redirect("/")


# ── 3. Initialisation des sous-dashboards ────────────────────────────────────
# IMPORTANT : importer APRÈS la création de `server`
from dashboard.banking.app   import init_banking
from dashboard.assurance.app import init_assurance
from dashboard.energie.app   import init_energie
from dashboard.sante.app     import init_sante

init_banking(server)    # /bancaire/
init_assurance(server)  # /assurance/
init_energie(server)    # /energie/
init_sante(server)      # /sante/


# ── 4. Lancement ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    server.run(debug=False, port=port, host="0.0.0.0")