"""
dashboard/assurance/app.py
Initialisation du Dashboard Assurance — design unifié Santé
"""
import os, sys
import dash
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_data():
    try:
        from utils.db import get_collection
        col, client = get_collection("assurance_data")
        data = list(col.find({}, {"_id": 0}))
        client.close()
        if data:
            df = pd.DataFrame(data)
            for c in ["montant_prime","montant_sinistres","bonus_malus","age","nb_sinistres"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            return df
    except Exception:
        pass
    csv = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "data", "assurance_data_1000.csv")
    if os.path.exists(csv):
        df = pd.read_csv(csv, sep=";", encoding="utf-8")
        for c in ["montant_prime","montant_sinistres","bonus_malus","age","nb_sinistres"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    return pd.DataFrame()


def init_assurance(server):
    df = _load_data()

    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Copier le CSS partagé depuis /assets
    import shutil
    src = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "assets", "hospital_style.css")
    dst = os.path.join(assets_dir, "hospital_style.css")
    if os.path.exists(src):
        shutil.copy(src, dst)

    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/assurance/",
        suppress_callback_exceptions=True,
        assets_folder=assets_dir,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )
    app.title = "DataSphere — Dashboard Assurance"

    from dashboard.assurance.layout    import create_layout
    from dashboard.assurance.callbacks import register_callbacks

    app.layout = create_layout(app, df)
    register_callbacks(app, df)

    return app
