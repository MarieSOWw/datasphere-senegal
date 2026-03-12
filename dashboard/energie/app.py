"""
dashboard/energie/app.py
Initialisation du Dashboard Énergie Solaire — design unifié Santé
"""
import os, sys
import dash
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_data():
    try:
        from utils.db import get_collection
        col, client = get_collection("energie_data")
        data = list(col.find({}, {"_id": 0}))
        client.close()
        if data:
            df = pd.DataFrame(data)
            df["DateTime"] = pd.to_datetime(df.get("DateTime"), errors="coerce")
            for c in ["DC_Power","AC_Power","Ambient_Temperature",
                      "Module_Temperature","Irradiation","Daily_Yield","Total_Yield"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            return df
    except Exception:
        pass
    csv = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "data", "salar_data.csv")
    if os.path.exists(csv):
        df = pd.read_csv(csv, sep=";", encoding="utf-8")
        df["DateTime"] = pd.to_datetime(df.get("DateTime"), errors="coerce")
        for c in ["DC_Power","AC_Power","Ambient_Temperature",
                  "Module_Temperature","Irradiation","Daily_Yield","Total_Yield"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    return pd.DataFrame()


def init_energie(server):
    df = _load_data()

    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(assets_dir, exist_ok=True)

    import shutil
    src = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "assets", "hospital_style.css")
    dst = os.path.join(assets_dir, "hospital_style.css")
    if os.path.exists(src):
        shutil.copy(src, dst)

    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/energie/",
        suppress_callback_exceptions=True,
        assets_folder=assets_dir,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )
    app.title = "DataSphere — Dashboard Énergie Solaire"

    from dashboard.energie.layout    import create_layout
    from dashboard.energie.callbacks import register_callbacks

    app.layout = create_layout(app, df)
    register_callbacks(app, df)

    return app
