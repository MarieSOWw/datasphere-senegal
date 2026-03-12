"""
dashboard/assurance/callbacks.py
══════════════════════════════════════════════════════════════════
Callbacks du Dashboard Assurance
══════════════════════════════════════════════════════════════════
"""
import os, sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Input, Output, callback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

LAYOUT_BASE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#2c3e50"),
    margin=dict(l=10, r=10, t=40, b=40),
    hoverlabel=dict(bgcolor="white", font_size=12),
)

PALETTE = ["#3498db","#2ecc71","#f39c12","#e74c3c","#9b59b6",
           "#1abc9c","#34495e","#e67e22","#16a085","#8e44ad"]


def _load():
    """Charge les données assurance depuis MongoDB ou CSV de fallback."""
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
    # Fallback CSV
    csv = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))),
        "data", "assurance_data_1000.csv")
    if os.path.exists(csv):
        df = pd.read_csv(csv, sep=";", encoding="utf-8")
        for c in ["montant_prime","montant_sinistres","bonus_malus","age","nb_sinistres"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    return pd.DataFrame()


def _apply_filters(df, types, regions, sexes):
    fdf = df.copy()
    if types   and "type_assurance" in fdf.columns: fdf = fdf[fdf["type_assurance"].isin(types)]
    if regions and "region"         in fdf.columns: fdf = fdf[fdf["region"].isin(regions)]
    if sexes   and "sexe"           in fdf.columns: fdf = fdf[fdf["sexe"].isin(sexes)]
    return fdf


def register_callbacks(app, df_init):

    # ── Init options filtres ─────────────────────────────────────────────────
    @app.callback(
        [Output("ass-filter-type",   "options"),
         Output("ass-filter-region", "options"),
         Output("ass-filter-sexe",   "options")],
        Input("ass-filter-type", "id"),
    )
    def init_options(_):
        df = _load() if df_init.empty else df_init
        def opts(col):
            if col not in df.columns: return []
            return [{"label": v, "value": v} for v in sorted(df[col].dropna().unique())]
        return opts("type_assurance"), opts("region"), opts("sexe")

    # ── Reset ────────────────────────────────────────────────────────────────
    @app.callback(
        [Output("ass-filter-type",   "value"),
         Output("ass-filter-region", "value"),
         Output("ass-filter-sexe",   "value")],
        Input("ass-btn-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(_):
        return None, None, None

    # ── Graphiques ───────────────────────────────────────────────────────────
    @app.callback(
        [Output("ass-graph-type",       "figure"),
         Output("ass-graph-region",     "figure"),
         Output("ass-graph-age",        "figure"),
         Output("ass-graph-sinistres",  "figure"),
         Output("ass-graph-bonus-malus","figure"),
         Output("ass-graph-scatter",    "figure")],
        [Input("ass-filter-type",   "value"),
         Input("ass-filter-region", "value"),
         Input("ass-filter-sexe",   "value")],
    )
    def update_graphs(types, regions, sexes):
        df  = _load() if df_init.empty else df_init.copy()
        fdf = _apply_filters(df, types, regions, sexes)

        def empty(msg="Données indisponibles"):
            f = go.Figure()
            f.update_layout(**LAYOUT_BASE,
                            annotations=[dict(text=msg, showarrow=False,
                                             font=dict(size=13, color="#95a5a6"),
                                             xref="paper", yref="paper", x=0.5, y=0.5)])
            return f

        if fdf.empty:
            return [empty("Aucune donnée pour cette sélection")] * 6

        # ── 1. Répartition par type (donut) ─────────────────────────────────
        if "type_assurance" in fdf.columns:
            tc   = fdf["type_assurance"].value_counts()
            fig1 = px.pie(values=tc.values, names=tc.index,
                          color_discrete_sequence=px.colors.qualitative.Set2,
                          hole=0.42)
            fig1.update_traces(textposition="inside", textinfo="percent+label",
                               hovertemplate="<b>%{label}</b><br>%{value} assurés (%{percent})<extra></extra>")
            fig1.update_layout(**LAYOUT_BASE, showlegend=True, height=380,
                               legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
        else:
            fig1 = empty()

        # ── 2. Analyse région (barres groupées axes doubles) ─────────────────
        if "region" in fdf.columns:
            rd = (fdf.groupby("region")
                     .agg(prime=("montant_prime","sum"), sinistres=("nb_sinistres","sum"))
                     .reset_index()
                     .sort_values("prime", ascending=False))
            fig2 = go.Figure([
                go.Bar(name="Prime Totale (FCFA)", x=rd["region"], y=rd["prime"],
                       marker_color="#3498db",
                       hovertemplate="<b>%{x}</b><br>Prime: %{y:,.0f} FCFA<extra></extra>"),
                go.Bar(name="Nb Sinistres", x=rd["region"], y=rd["sinistres"],
                       marker_color="#f39c12", yaxis="y2",
                       hovertemplate="<b>%{x}</b><br>Sinistres: %{y}<extra></extra>"),
            ])
            fig2.update_layout(**LAYOUT_BASE, barmode="group", height=380,
                               xaxis=dict(title="Région"),
                               yaxis=dict(title="Prime (FCFA)", gridcolor="rgba(0,0,0,0.06)"),
                               yaxis2=dict(title="Nb Sinistres", overlaying="y", side="right"),
                               legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"))
        else:
            fig2 = empty()

        # ── 3. Distribution âge (histogramme) ────────────────────────────────
        if "age" in fdf.columns:
            fig3 = px.histogram(fdf, x="age", nbins=25,
                                color_discrete_sequence=["#9b59b6"],
                                labels={"age": "Âge", "count": "Nombre d'assurés"})
            fig3.update_traces(marker_line_color="white", marker_line_width=1,
                               hovertemplate="Âge: %{x}<br>Assurés: %{y}<extra></extra>")
            fig3.update_layout(**LAYOUT_BASE, height=380,
                               xaxis=dict(title="Âge", gridcolor="rgba(0,0,0,0.06)"),
                               yaxis=dict(title="Nombre d'assurés", gridcolor="rgba(0,0,0,0.06)"))
        else:
            fig3 = empty()

        # ── 4. Sinistres par type (subplots) ──────────────────────────────────
        if "type_assurance" in fdf.columns:
            st = (fdf.groupby("type_assurance")
                     .agg(nb_sin=("nb_sinistres","sum"),
                          mnt_moy=("montant_sinistres","mean"))
                     .reset_index()
                     .sort_values("nb_sin", ascending=False))
            fig4 = make_subplots(rows=1, cols=2,
                                 subplot_titles=("Nombre de Sinistres",
                                                 "Montant Moyen (FCFA)"))
            fig4.add_trace(go.Bar(x=st["type_assurance"], y=st["nb_sin"],
                                  marker_color="#f39c12", name="Nb Sinistres",
                                  hovertemplate="<b>%{x}</b><br>Sinistres: %{y}<extra></extra>"),
                           row=1, col=1)
            fig4.add_trace(go.Bar(x=st["type_assurance"], y=st["mnt_moy"],
                                  marker_color="#2ecc71", name="Montant Moy.",
                                  hovertemplate="<b>%{x}</b><br>Montant: %{y:,.0f} FCFA<extra></extra>"),
                           row=1, col=2)
            fig4.update_layout(**LAYOUT_BASE, height=380, showlegend=False)
        else:
            fig4 = empty()

        # ── 5. Bonus / Malus (box plot) ───────────────────────────────────────
        if "bonus_malus" in fdf.columns and "type_assurance" in fdf.columns:
            fig5 = px.box(fdf, x="type_assurance", y="bonus_malus",
                          color="type_assurance",
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            fig5.update_layout(**LAYOUT_BASE, height=380, showlegend=False,
                               xaxis_title="Type d'Assurance",
                               yaxis_title="Coefficient Bonus/Malus",
                               yaxis=dict(gridcolor="rgba(0,0,0,0.06)"))
            fig5.add_hline(y=1.0, line_dash="dash", line_color="#e74c3c",
                           annotation_text="Neutre (1.0)",
                           annotation_position="top right",
                           annotation_font_color="#e74c3c")
        else:
            fig5 = empty()

        # ── 6. Prime vs Sinistres (scatter) ──────────────────────────────────
        if "montant_prime" in fdf.columns and "montant_sinistres" in fdf.columns:
            sample = fdf.sample(min(400, len(fdf)), random_state=42)
            kw = {}
            if "type_assurance" in sample.columns: kw["color"] = "type_assurance"
            if "nb_sinistres"   in sample.columns: kw["size"]  = "nb_sinistres"
            hover = [c for c in ["age","region","bonus_malus"] if c in sample.columns]
            if hover: kw["hover_data"] = hover
            fig6 = px.scatter(sample, x="montant_prime", y="montant_sinistres",
                              color_discrete_sequence=px.colors.qualitative.Set2,
                              labels={"montant_prime":"Prime (FCFA)",
                                      "montant_sinistres":"Montant Sinistres (FCFA)"},
                              **kw)
            fig6.update_layout(**LAYOUT_BASE, height=380,
                               xaxis=dict(title="Prime (FCFA)", gridcolor="rgba(0,0,0,0.06)"),
                               yaxis=dict(title="Montant Sinistres (FCFA)", gridcolor="rgba(0,0,0,0.06)"),
                               legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
        else:
            fig6 = empty()

        return fig1, fig2, fig3, fig4, fig5, fig6
