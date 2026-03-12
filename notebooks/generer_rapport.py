"""
Genere_rapport/generer_rapport.py
══════════════════════════════════════════════════════════════
Génère un rapport HTML à partir du notebook Jupyter.
VERSION MISE À JOUR : lit depuis MongoDB (plus de chemin Excel hardcodé)
══════════════════════════════════════════════════════════════
"""

import os
import nbformat
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor
from pymongo import MongoClient
from Genere_rapport.htm_rapport import add_toc


def notebook_to_html(
    notebook_path: str,
    output_filename: str = "Rapport.html",
    mongo_uri: str = "mongodb://localhost:27017/",
    db_name: str = "banking_senegal",
    collection: str = "banques_senegal"
) -> str:
    """
    Exécute le notebook Jupyter et le convertit en HTML avec sommaire.

    Parameters
    ----------
    notebook_path   : chemin vers le fichier .ipynb
    output_filename : nom du fichier HTML de sortie
    mongo_uri       : URI MongoDB
    db_name         : base de données MongoDB
    collection      : nom de la collection bancaire

    Returns
    -------
    str : contenu HTML du rapport
    """

    # ── 1. Lecture du notebook ────────────────────────────────────────────────
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = nbformat.read(f, as_version=4)

    # ── 2. Exécution du notebook ──────────────────────────────────────────────
    executor = ExecutePreprocessor(
        timeout=600,               # 10 min max
        kernel_name="python3"
    )
    executor.preprocess(notebook)

    # ── 3. Export HTML ────────────────────────────────────────────────────────
    html_exporter = HTMLExporter(
        template_name="classic",
        exclude_input=True         # Ne pas afficher le code dans le rapport
    )
    body, _ = html_exporter.from_notebook_node(
        notebook, resources={"embed_widgets": True}
    )

    # ── 4. Ajout du sommaire (TOC) ────────────────────────────────────────────
    body = add_toc(body)

    # ── 5. Synthèse dynamique depuis MongoDB ─────────────────────────────────
    try:
        client = MongoClient(mongo_uri)
        col = client[db_name][collection]

        pipeline_bilan = [
            {"$group": {
                "_id": None,
                "total_bilan": {"$sum": "$bilan"},
                "nb_banques": {"$addToSet": "$sigle"}
            }}
        ]
        result = list(col.aggregate(pipeline_bilan))
        annees = sorted(col.distinct("annee"))

        if result:
            total_bilan = result[0].get("total_bilan", 0)
            nb_banques  = len(result[0].get("nb_banques", []))
            total_mds   = round(total_bilan / 1_000_000, 2)
        else:
            total_bilan = 0
            nb_banques  = 0
            total_mds   = 0

        annee_min = min(annees) if annees else "N/A"
        annee_max = max(annees) if annees else "N/A"
        client.close()

        synthese = f"""
        <div style="
            margin: 30px auto; padding: 25px;
            background: linear-gradient(135deg, #0F2044 0%, #1A6FBA 100%);
            border-radius: 12px; color: white;
            max-width: 900px; box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        ">
            <h3 style="margin-top:0; font-size:1.4rem;">📊 Synthèse Bancaire Sénégalaise</h3>
            <div style="display:grid; grid-template-columns: repeat(3,1fr); gap:20px; margin-top:15px;">
                <div style="background:rgba(255,255,255,0.15); padding:15px; border-radius:8px; text-align:center;">
                    <div style="font-size:2rem; font-weight:700;">{nb_banques}</div>
                    <div style="font-size:0.85rem; opacity:0.85;">Banques analysées</div>
                </div>
                <div style="background:rgba(255,255,255,0.15); padding:15px; border-radius:8px; text-align:center;">
                    <div style="font-size:2rem; font-weight:700;">{total_mds:,.0f} Mds</div>
                    <div style="font-size:0.85rem; opacity:0.85;">Total bilan cumulé (FCFA)</div>
                </div>
                <div style="background:rgba(255,255,255,0.15); padding:15px; border-radius:8px; text-align:center;">
                    <div style="font-size:2rem; font-weight:700;">{annee_min}–{annee_max}</div>
                    <div style="font-size:0.85rem; opacity:0.85;">Période couverte</div>
                </div>
            </div>
            <p style="margin-top:18px; font-size:0.9rem; opacity:0.85;">
                Source : BASE_SENEGAL2.xlsx + Rapports BCEAO PDF — MongoDB <code>banking_senegal</code>
            </p>
        </div>
        """
    except Exception as e:
        synthese = f"""
        <div style="margin:20px; padding:15px; background:#fff3cd; border-radius:8px;">
            <strong>⚠️ Synthèse non disponible</strong> — Vérifier la connexion MongoDB : {e}
        </div>
        """

    body += synthese

    # ── 6. Sauvegarde ─────────────────────────────────────────────────────────
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(body)

    print(f"✅ Rapport HTML généré : {output_filename}")
    return body