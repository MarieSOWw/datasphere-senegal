"""
dashboard/sante/app.py
Dashboard Santé / Analyse Hospitalière — intégré dans DataSphere
Design original préservé, données MongoDB (fallback CSV)
"""
import os
import sys
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_data():
    """Charge les données hospitalières — MongoDB puis fallback CSV."""
    try:
        from utils.db import get_collection
        col, client = get_collection("sante_data")
        data = list(col.find({}, {"_id": 0}))
        client.close()
        if data:
            df = pd.DataFrame(data)
            df["DateAdmission"] = pd.to_datetime(df.get("DateAdmission"), errors="coerce")
            df["DateSortie"]    = pd.to_datetime(df.get("DateSortie"),    errors="coerce")
            df["Mois"]         = df["DateAdmission"].dt.to_period("M").astype(str)
            df["Annee"]        = df["DateAdmission"].dt.year
            df["MoisNom"]      = df["DateAdmission"].dt.strftime("%B %Y")
            df["CoutParJour"]  = df["Cout"] / df["DureeSejour"].replace(0, pd.NA)
            df["CategorieAge"] = pd.cut(
                df["Age"], bins=[0, 18, 35, 50, 65, 120],
                labels=["0-18 ans", "19-35 ans", "36-50 ans", "51-65 ans", "65+ ans"]
            )
            return df
    except Exception:
        pass

    # Fallback CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "data", "hospital_data.csv")
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    df["DateAdmission"] = pd.to_datetime(df["DateAdmission"], format="%d/%m/%Y")
    df["DateSortie"]    = pd.to_datetime(df["DateSortie"],    format="%d/%m/%Y")
    df["Mois"]         = df["DateAdmission"].dt.to_period("M").astype(str)
    df["Annee"]        = df["DateAdmission"].dt.year
    df["MoisNom"]      = df["DateAdmission"].dt.strftime("%B %Y")
    df["CoutParJour"]  = df["Cout"] / df["DureeSejour"].replace(0, pd.NA)
    df["CategorieAge"] = pd.cut(
        df["Age"], bins=[0, 18, 35, 50, 65, 120],
        labels=["0-18 ans", "19-35 ans", "36-50 ans", "51-65 ans", "65+ ans"]
    )
    return df


def init_sante(server):
    """Attache le Dash Santé au serveur Flask."""
    df = _load_data()

    # Répertoire assets avec le CSS original du dashboard hospitalier
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Copier le CSS original
    src_css = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "assets", "hospital_style.css"
    )
    dst_css = os.path.join(assets_dir, "hospital_style.css")
    if os.path.exists(src_css) and not os.path.exists(dst_css):
        import shutil
        shutil.copy(src_css, dst_css)

    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/sante/",
        external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        assets_folder=assets_dir,
    )
    app.title = "DataSphere — Analyse Hospitalière"

    # Import layout & callbacks du dashboard hospitalier original
    from dashboard.sante.layout    import create_layout
    from dashboard.sante.callbacks import register_callbacks

    app.layout = create_layout(app)
    register_callbacks(app, df)

    return app
