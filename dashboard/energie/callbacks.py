"""
dashboard/energie/callbacks.py  — VERSION FINALE
══════════════════════════════════════════════════════════════════
CORRECTIONS :
  ✅ fig5 — bug "multiple values for keyword argument 'labels'" corrigé
  ✅ Interprétations 100% DYNAMIQUES — calculées sur fdf (données filtrées)
       → changent quand on filtre par pays, mois ou plage horaire
  ✅ Chargement UNIQUEMENT depuis MongoDB Atlas (pas de fallback CSV)
  ✅ 14 Outputs : 7 figures + 7 blocs d'interprétation
══════════════════════════════════════════════════════════════════
"""
import os, sys, traceback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, html

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

LAYOUT_BASE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#2c3e50"),
    margin=dict(l=10, r=10, t=40, b=40),
    hoverlabel=dict(bgcolor="white", font_size=12),
)

C_AMBER  = "#f59e0b"
C_ORANGE = "#f97316"
C_GREEN  = "#10b981"
C_CYAN   = "#06b6d4"
C_RED    = "#ef4444"


# ── Helper : boîte interprétation ────────────────────────────────────────────
def _ibox(color, children):
    """Génère une boîte interprétation au même style que l'ancien _interp()."""
    return [
        html.Div("💡 Interprétation",
                 className="interpretation-label interpretation-label-energie"),
        html.Div(children, className="interpretation-text",
                 style={"lineHeight": "1.7", "fontSize": "0.93rem"}),
    ]


def _badge(pays, mois, plage):
    """Génère un contexte lisible pour l'en-tête des interprétations."""
    mois_noms = {
        1:"Janvier", 2:"Février",  3:"Mars",      4:"Avril",
        5:"Mai",     6:"Juin",     7:"Juillet",   8:"Août",
        9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"
    }
    plage_labels = {
        "all":    "journée entière",
        "matin":  "matin (6h–12h)",
        "aprem":  "après-midi (12h–18h)",
        "pointe": "pointe (10h–15h)",
    }
    parts = []
    if pays:
        parts.append(", ".join(pays) if isinstance(pays, list) else str(pays))
    if mois:
        noms = [mois_noms.get(int(m), str(m)) for m in (mois if isinstance(mois, list) else [mois])]
        parts.append(", ".join(noms))
    if plage and plage != "all":
        parts.append(plage_labels.get(plage, plage))
    return " · ".join(parts) if parts else "Tous pays — Tous mois — Journée entière"


# ── Normalisation ─────────────────────────────────────────────────────────────
def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace(' ', '_') for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    for c in ["DC_Power", "AC_Power", "Ambient_Temperature", "Module_Temperature",
              "Irradiation", "Daily_Yield", "Total_Yield", "Day", "Month", "Hour"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ── Chargement MongoDB UNIQUEMENT ─────────────────────────────────────────────
def _load():
    """Charge depuis MongoDB Atlas — aucun fallback CSV."""
    try:
        from utils.db import get_collection
        col, client = get_collection("energie_data")
        data = list(col.find({}, {"_id": 0}))
        client.close()
        if data:
            df = _clean(pd.DataFrame(data))
            print(f"[ENERGIE] MongoDB OK — {len(df)} lignes")
            return df
        else:
            print("[ENERGIE] MongoDB : collection vide")
            return pd.DataFrame()
    except Exception as e:
        print(f"[ENERGIE] MongoDB ERREUR: {e}\n{traceback.format_exc()}")
        return pd.DataFrame()


def _apply_filters(df, pays, mois, plage):
    fdf = df.copy()
    if pays and "Country" in fdf.columns:
        fdf = fdf[fdf["Country"].isin(pays)]
    if mois and "Month" in fdf.columns:
        fdf = fdf[fdf["Month"].isin([int(m) for m in mois])]
    if plage and plage != "all" and "Hour" in fdf.columns:
        if plage == "matin":    fdf = fdf[(fdf["Hour"] >= 6)  & (fdf["Hour"] < 12)]
        elif plage == "aprem":  fdf = fdf[(fdf["Hour"] >= 12) & (fdf["Hour"] < 18)]
        elif plage == "pointe": fdf = fdf[(fdf["Hour"] >= 10) & (fdf["Hour"] < 15)]
    return fdf


def _empty_fig(msg="Données indisponibles"):
    f = go.Figure()
    f.update_layout(**LAYOUT_BASE,
                    annotations=[dict(text=msg, showarrow=False,
                                      font=dict(size=11, color="#e74c3c"),
                                      xref="paper", yref="paper",
                                      x=0.5, y=0.5, align="center")])
    return f


def _empty_interp(msg="Données indisponibles."):
    return _ibox(C_ORANGE, [html.P(msg, style={"color": "#9ca3af", "fontStyle": "italic"})])


# ══════════════════════════════════════════════════════════════════════════════
def register_callbacks(app, df_init):

    # ── Init filtres ──────────────────────────────────────────────────────────
    @app.callback(
        [Output("eng-filter-pays", "options"),
         Output("eng-filter-mois", "options")],
        Input("eng-filter-pays", "id"),
    )
    def init_options(_):
        try:
            df = _load() if (df_init is None or df_init.empty) else _clean(df_init)
            pays_opts = (
                [{"label": str(p), "value": str(p)}
                 for p in sorted(df["Country"].dropna().unique())]
                if "Country" in df.columns else []
            )
            mois_noms = {
                1:"Janvier", 2:"Février",  3:"Mars",      4:"Avril",
                5:"Mai",     6:"Juin",     7:"Juillet",   8:"Août",
                9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"
            }
            mois_opts = (
                [{"label": mois_noms.get(int(m), str(m)), "value": int(m)}
                 for m in sorted(df["Month"].dropna().unique().astype(int))]
                if "Month" in df.columns else []
            )
            print(f"[ENERGIE] Options OK: {len(pays_opts)} pays, {len(mois_opts)} mois")
            return pays_opts, mois_opts
        except Exception as e:
            print(f"[ENERGIE] init_options ERREUR:\n{traceback.format_exc()}")
            return [], []

    # ── Reset ─────────────────────────────────────────────────────────────────
    @app.callback(
        [Output("eng-filter-pays",  "value"),
         Output("eng-filter-mois",  "value"),
         Output("eng-filter-plage", "value")],
        Input("eng-btn-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(_):
        return None, None, "all"

    # ── 7 Graphiques + 7 Interprétations DYNAMIQUES ───────────────────────────
    @app.callback(
        [Output("eng-graph-dc-ac",       "figure"),
         Output("eng-graph-irradiation", "figure"),
         Output("eng-graph-temp",        "figure"),
         Output("eng-graph-yield",       "figure"),
         Output("eng-graph-corr",        "figure"),
         Output("eng-graph-patron",      "figure"),
         Output("eng-graph-heatmap",     "figure"),
         # ── Interprétations dynamiques ────────────────────────────────────
         Output("eng-interp-dc-ac",       "children"),
         Output("eng-interp-irradiation", "children"),
         Output("eng-interp-temp",        "children"),
         Output("eng-interp-yield",       "children"),
         Output("eng-interp-corr",        "children"),
         Output("eng-interp-patron",      "children"),
         Output("eng-interp-heatmap",     "children"),
        ],
        [Input("eng-filter-pays",  "value"),
         Input("eng-filter-mois",  "value"),
         Input("eng-filter-plage", "value")],
    )
    def update_graphs(pays, mois, plage):

        # ── Chargement ────────────────────────────────────────────────────────
        try:
            df  = _load() if (df_init is None or df_init.empty) else _clean(df_init)
            fdf = _apply_filters(df, pays, mois, plage)
            ctx = _badge(pays, mois, plage)
            print(f"[ENERGIE] update_graphs — {ctx} | fdf={len(fdf)}")
        except Exception as e:
            print(f"[ENERGIE] Chargement ERREUR:\n{traceback.format_exc()}")
            empty_f = _empty_fig(f"Erreur MongoDB: {e}")
            empty_i = _empty_interp(f"Erreur de chargement MongoDB : {e}")
            return [empty_f]*7 + [empty_i]*7

        if fdf.empty:
            empty_f = _empty_fig("Aucune donnée pour cette sélection")
            empty_i = _empty_interp("Aucune donnée pour cette sélection.")
            return [empty_f]*7 + [empty_i]*7

        # ══════════════════════════════════════════════════════════════════════
        # Fig 1 + Interp 1 — DC vs AC par heure
        # ══════════════════════════════════════════════════════════════════════
        try:
            hourly = fdf.groupby("Hour").agg(
                dc=("DC_Power", "mean"),
                ac=("AC_Power", "mean"),
            ).reset_index()

            pic_idx = hourly["dc"].idxmax()
            pic_h   = int(hourly.loc[pic_idx, "Hour"])
            pic_dc  = float(hourly.loc[pic_idx, "dc"])
            pic_ac  = float(hourly.loc[hourly["ac"].idxmax(), "ac"])

            prod_sel = fdf[fdf["DC_Power"] > 0]
            ecart = (
                ((prod_sel["DC_Power"] - prod_sel["AC_Power"]) / prod_sel["DC_Power"] * 100).mean()
                if len(prod_sel) > 0 else 0.0
            )
            eff_sel = (
                prod_sel["AC_Power"].sum() / prod_sel["DC_Power"].sum() * 100
                if prod_sel["DC_Power"].sum() > 0 else 0.0
            )

            fig1 = go.Figure([
                go.Scatter(x=hourly["Hour"], y=hourly["dc"], name="DC Power",
                           fill="tozeroy", line=dict(color=C_AMBER, width=2.5),
                           fillcolor="rgba(245,158,11,0.12)",
                           hovertemplate="<b>%{x}h</b><br>DC: %{y:,.1f} kW<extra></extra>"),
                go.Scatter(x=hourly["Hour"], y=hourly["ac"], name="AC Power",
                           fill="tozeroy", line=dict(color=C_ORANGE, width=2.5),
                           fillcolor="rgba(249,115,22,0.10)",
                           hovertemplate="<b>%{x}h</b><br>AC: %{y:,.1f} kW<extra></extra>"),
            ])
            fig1.update_layout(
                **LAYOUT_BASE, height=380,
                xaxis=dict(title="Heure", tickmode="linear", dtick=2,
                           gridcolor="rgba(0,0,0,0.06)"),
                yaxis=dict(title="Puissance (kW)", gridcolor="rgba(0,0,0,0.06)"),
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            )

            norme_ok = "✅ dans la norme acceptable (5–15%)" if ecart <= 15 else "⚠️ au-dessus de la norme (> 15%)"
            interp1 = _ibox(C_AMBER, [
                html.P(html.Strong(f"Contexte : {ctx}"),
                       style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                html.P([
                    f"Pic de production à ",
                    html.Strong(f"{pic_h}h"),
                    f" : DC {pic_dc:.1f} kW — AC {pic_ac:.1f} kW. ",
                    f"L'écart moyen DC→AC est de ",
                    html.Strong(f"{ecart:.1f}%"),
                    f" ({norme_ok}). ",
                    f"Efficacité de conversion sur cette sélection : ",
                    html.Strong(f"{eff_sel:.1f}%"),
                    ".",
                ]),
                html.P(
                    "Un écart > 15% signalerait un onduleur défaillant ou des pertes "
                    "de câblage anormales nécessitant une intervention technique."
                ),
            ])
            print(f"[ENERGIE] fig1 OK ({len(hourly)} h)")
        except Exception as e:
            print(f"[ENERGIE] fig1 ERREUR: {traceback.format_exc()}")
            fig1    = _empty_fig(f"fig1 erreur: {e}")
            interp1 = _empty_interp(f"Erreur fig1 : {e}")

        # ══════════════════════════════════════════════════════════════════════
        # Fig 2 + Interp 2 — Irradiation mensuelle
        # ══════════════════════════════════════════════════════════════════════
        try:
            monthly = fdf.groupby("Month").agg(irr=("Irradiation", "mean")).reset_index()
            lbl = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Juin",
                   7:"Jul",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
            monthly["mois_nom"] = monthly["Month"].apply(lambda x: lbl.get(int(x), str(x)))

            m_max   = monthly.loc[monthly["irr"].idxmax()]
            m_min   = monthly.loc[monthly["irr"].idxmin()]
            irr_moy = float(monthly["irr"].mean())
            var_pct = (m_max["irr"] - m_min["irr"]) / irr_moy * 100 if irr_moy > 0 else 0

            fig2 = px.bar(
                monthly, x="mois_nom", y="irr", color="irr",
                color_continuous_scale=["#fef3c7", "#f59e0b", "#c2410c"],
                labels={"irr": "Irradiation", "mois_nom": "Mois"},
            )
            fig2.update_layout(
                **LAYOUT_BASE, height=380,
                showlegend=False, coloraxis_showscale=False,
                xaxis=dict(title="Mois"),
                yaxis=dict(title="Irradiation Moyenne", gridcolor="rgba(0,0,0,0.06)"),
            )
            fig2.update_traces(hovertemplate="<b>%{x}</b><br>Irr: %{y:.4f}<extra></extra>")

            interp2 = _ibox(C_ORANGE, [
                html.P(html.Strong(f"Contexte : {ctx}"),
                       style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                html.P([
                    html.Strong(f"{m_max['mois_nom']}"),
                    f" enregistre l'irradiation maximale ({m_max['irr']:.3f}), ",
                    html.Strong(f"{m_min['mois_nom']}"),
                    f" la minimale ({m_min['irr']:.3f}). ",
                    f"Variation saisonnière : ±{var_pct:.0f}% autour de la moyenne ({irr_moy:.3f}). ",
                ]),
                html.P(
                    "Cette saisonnalité est directement corrélée à la production photovoltaïque. "
                    "Elle est essentielle pour dimensionner les installations de stockage "
                    "et anticiper les périodes de sous-production."
                ),
            ])
            print(f"[ENERGIE] fig2 OK ({len(monthly)} mois)")
        except Exception as e:
            print(f"[ENERGIE] fig2 ERREUR: {traceback.format_exc()}")
            fig2    = _empty_fig(f"fig2 erreur: {e}")
            interp2 = _empty_interp(f"Erreur fig2 : {e}")

        # ══════════════════════════════════════════════════════════════════════
        # Fig 3 + Interp 3 — Distribution températures
        # ══════════════════════════════════════════════════════════════════════
        try:
            amb = (fdf["Ambient_Temperature"].dropna()
                   if "Ambient_Temperature" in fdf.columns else pd.Series(dtype=float))
            mod = (fdf["Module_Temperature"].dropna()
                   if "Module_Temperature"  in fdf.columns else pd.Series(dtype=float))

            if len(amb) == 0:
                fig3    = _empty_fig("Données de température indisponibles")
                interp3 = _empty_interp("Températures non disponibles pour cette sélection.")
            else:
                amb_moy = float(amb.mean())
                mod_moy = float(mod.mean()) if len(mod) > 0 else 0.0
                diff_t  = mod_moy - amb_moy if len(mod) > 0 else 0.0
                corr_t  = float(amb.corr(mod)) if len(mod) > 0 else 0.0
                amb_max = float(amb.max())

                fig3 = go.Figure()
                fig3.add_trace(go.Histogram(
                    x=amb, name="T° Ambiante",
                    marker_color=C_CYAN, opacity=0.78, nbinsx=35,
                    hovertemplate="T°: %{x:.1f}°C | Fréq: %{y}<extra></extra>"))
                if len(mod) > 0:
                    fig3.add_trace(go.Histogram(
                        x=mod, name="T° Module",
                        marker_color=C_RED, opacity=0.78, nbinsx=35,
                        hovertemplate="T°: %{x:.1f}°C | Fréq: %{y}<extra></extra>"))
                fig3.update_layout(
                    **LAYOUT_BASE, height=380, barmode="overlay",
                    xaxis=dict(title="Température (°C)", gridcolor="rgba(0,0,0,0.06)"),
                    yaxis=dict(title="Fréquence", gridcolor="rgba(0,0,0,0.06)"),
                    legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
                )

                alerte = (
                    f" ⚠️ Pic détecté à {amb_max:.1f}°C — surveiller l'impact sur le rendement."
                    if amb_max > 35 else ""
                )
                interp3 = _ibox(C_RED, [
                    html.P(html.Strong(f"Contexte : {ctx}"),
                           style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                    html.P([
                        "T° ambiante moyenne : ",
                        html.Strong(f"{amb_moy:.1f}°C"),
                        f" (plage {amb.min():.1f} – {amb_max:.1f}°C). ",
                        "T° module moyenne : ",
                        html.Strong(f"{mod_moy:.1f}°C"),
                        " — soit ",
                        html.Strong(f"+{diff_t:.1f}°C"),
                        " au-dessus de l'ambiant. ",
                        f"Corrélation T° ambiante ↔ module : R = {corr_t:.3f}.",
                        html.Span(alerte, style={"color": C_ORANGE}),
                    ]),
                    html.P(
                        "Au-delà de 45°C de T° module, l'efficacité des panneaux diminue "
                        "d'environ 0,4%/°C supplémentaire (effet thermique des semi-conducteurs)."
                    ),
                ])
                print("[ENERGIE] fig3 OK")
        except Exception as e:
            print(f"[ENERGIE] fig3 ERREUR: {traceback.format_exc()}")
            fig3    = _empty_fig(f"fig3 erreur: {e}")
            interp3 = _empty_interp(f"Erreur fig3 : {e}")

        # ══════════════════════════════════════════════════════════════════════
        # Fig 4 + Interp 4 — Rendement quotidien
        # ══════════════════════════════════════════════════════════════════════
        try:
            dy_col = "Daily_Yield"
            if dy_col not in fdf.columns:
                fig4    = _empty_fig("Daily_Yield non disponible")
                interp4 = _empty_interp("Colonne Daily_Yield absente des données.")
            else:
                keys = [c for c in ["Country", "Month", "Day"] if c in fdf.columns]
                yd = (fdf.groupby(keys)[dy_col].first()
                         .reset_index()
                         .groupby("Day")[dy_col].mean()
                         .reset_index())
                yd.columns = ["Day", "yield_daily"]

                moy_yd = float(yd["yield_daily"].mean())
                max_yd = float(yd["yield_daily"].max())
                min_yd = float(yd["yield_daily"].min())
                std_yd = float(yd["yield_daily"].std())

                fig4 = go.Figure(go.Scatter(
                    x=yd["Day"], y=yd["yield_daily"],
                    fill="tozeroy", mode="lines+markers",
                    line=dict(color=C_GREEN, width=2.5),
                    fillcolor="rgba(16,185,129,0.10)",
                    marker=dict(size=5, color=C_GREEN),
                    hovertemplate="<b>Jour %{x}</b><br>Rendement: %{y:,.1f} kWh<extra></extra>",
                ))
                fig4.update_layout(
                    **LAYOUT_BASE, height=380,
                    xaxis=dict(title="Jour du mois", gridcolor="rgba(0,0,0,0.06)"),
                    yaxis=dict(title="Rendement Quotidien (kWh)", gridcolor="rgba(0,0,0,0.06)"),
                )

                stabilite = "stable" if std_yd < moy_yd * 0.15 else "variable"
                interp4 = _ibox(C_GREEN, [
                    html.P(html.Strong(f"Contexte : {ctx}"),
                           style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                    html.P([
                        "Rendement moyen : ",
                        html.Strong(f"{moy_yd:.0f} kWh/jour"),
                        f" — max {max_yd:.0f} kWh, min {min_yd:.0f} kWh, écart-type {std_yd:.0f} kWh. ",
                        f"Production journalière ",
                        html.Strong(stabilite),
                        f" (σ/μ = {std_yd/moy_yd*100:.1f}%).",
                    ]),
                    html.P(
                        "Le Daily Yield intègre toutes les heures de production et constitue "
                        "le KPI principal pour évaluer la rentabilité de l'installation. "
                        "Les journées sous 200 kWh signalent un ensoleillement très réduit "
                        "ou un incident technique à investiguer."
                    ),
                ])
                print(f"[ENERGIE] fig4 OK ({len(yd)} jours, {min_yd:.0f}–{max_yd:.0f} kWh)")
        except Exception as e:
            print(f"[ENERGIE] fig4 ERREUR: {traceback.format_exc()}")
            fig4    = _empty_fig(f"fig4 erreur: {e}")
            interp4 = _empty_interp(f"Erreur fig4 : {e}")

        # ══════════════════════════════════════════════════════════════════════
        # Fig 5 + Interp 5 — Corrélation Irradiation / AC  (BUG CORRIGÉ)
        # ══════════════════════════════════════════════════════════════════════
        try:
            prod   = fdf[fdf["DC_Power"] > 0] if "DC_Power" in fdf.columns else fdf
            sample = prod.sample(min(2500, len(prod)), random_state=42)

            corr_val = float(sample["Irradiation"].corr(sample["AC_Power"]))
            has_temp = "Module_Temperature" in sample.columns

            # ── CORRECTION : pas de labels= dans px.scatter
            #    on gère les titres via update_layout
            if has_temp:
                fig5 = px.scatter(
                    sample,
                    x="Irradiation",
                    y="AC_Power",
                    color="Module_Temperature",
                    color_continuous_scale=[C_CYAN, C_AMBER, C_RED],
                )
                fig5.update_coloraxes(colorbar_title="T° Module (°C)")
            else:
                fig5 = px.scatter(sample, x="Irradiation", y="AC_Power")

            fig5.update_traces(marker=dict(size=4, opacity=0.60))
            fig5.update_layout(
                **LAYOUT_BASE, height=380,
                xaxis=dict(title="Irradiation (kW/m²)", gridcolor="rgba(0,0,0,0.06)"),
                yaxis=dict(title="Puissance AC (kW)",   gridcolor="rgba(0,0,0,0.06)"),
            )

            force = ("très forte" if abs(corr_val) >= 0.9
                     else "forte" if abs(corr_val) >= 0.7
                     else "modérée")
            interp5 = _ibox("#8b5cf6", [
                html.P(html.Strong(f"Contexte : {ctx}"),
                       style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                html.P([
                    "Corrélation Irradiation ↔ Puissance AC : ",
                    html.Strong(f"R = {corr_val:.3f}"),
                    f" — relation ",
                    html.Strong(force),
                    ". ",
                    "L'irradiation est le facteur déterminant de la production : "
                    "chaque augmentation d'irradiation se traduit quasi-linéairement "
                    "en hausse de puissance AC.",
                ]),
                html.P(
                    "Les points hors tendance (outliers) révèlent des anomalies : "
                    "ombrage partiel, défaut de capteur, ou perte temporaire de rendement — "
                    "à investiguer pour maintenir la performance optimale."
                ) if has_temp else html.P(),
            ])
            print(f"[ENERGIE] fig5 OK ({len(sample)} pts) | R={corr_val:.3f}")
        except Exception as e:
            print(f"[ENERGIE] fig5 ERREUR: {traceback.format_exc()}")
            fig5    = _empty_fig(f"fig5 erreur: {e}")
            interp5 = _empty_interp(f"Erreur fig5 : {e}")

        # ══════════════════════════════════════════════════════════════════════
        # Fig 6 + Interp 6 — Patron horaire
        # ══════════════════════════════════════════════════════════════════════
        try:
            ph = fdf.groupby("Hour").agg(
                ac=("AC_Power",    "mean"),
                irr=("Irradiation","mean"),
            ).reset_index()

            pic_h   = int(ph.loc[ph["ac"].idxmax(), "Hour"])
            pic_ac  = float(ph["ac"].max())
            prod_h  = ph[ph["ac"] > 10]
            h_debut = int(prod_h["Hour"].min()) if not prod_h.empty else 0
            h_fin   = int(prod_h["Hour"].max()) if not prod_h.empty else 23
            nb_h    = h_fin - h_debut

            fig6 = go.Figure()
            fig6.add_trace(go.Bar(
                x=ph["Hour"], y=ph["ac"], name="Production AC",
                marker_color=C_AMBER, opacity=0.80,
                hovertemplate="<b>%{x}h</b><br>AC: %{y:,.1f} kW<extra></extra>"))
            fig6.add_trace(go.Scatter(
                x=ph["Hour"], y=ph["irr"], name="Irradiation",
                line=dict(color=C_RED, width=2.5), yaxis="y2",
                hovertemplate="<b>%{x}h</b><br>Irr: %{y:.3f}<extra></extra>"))
            fig6.update_layout(
                **LAYOUT_BASE, height=380,
                xaxis=dict(title="Heure", tickmode="linear", dtick=2,
                           gridcolor="rgba(0,0,0,0.06)"),
                yaxis=dict(title="Puissance AC (kW)", gridcolor="rgba(0,0,0,0.06)"),
                yaxis2=dict(title="Irradiation", overlaying="y", side="right",
                            gridcolor="rgba(0,0,0,0)"),
                legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
            )

            interp6 = _ibox(C_AMBER, [
                html.P(html.Strong(f"Contexte : {ctx}"),
                       style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                html.P([
                    html.Strong(f"Pic de production à {pic_h}h"),
                    f" : {pic_ac:.1f} kW AC en moyenne. ",
                    f"Plage productive (AC > 10 kW) : ",
                    html.Strong(f"{h_debut}h – {h_fin}h"),
                    f" ({nb_h} heures de production effective/jour). ",
                ]),
                html.P(
                    "La production suit fidèlement la courbe d'irradiation. "
                    "Les activités énergivores et la recharge des batteries "
                    "doivent être planifiées sur la fenêtre 9h–15h "
                    "pour maximiser l'autoconsommation."
                ),
            ])
            print("[ENERGIE] fig6 OK")
        except Exception as e:
            print(f"[ENERGIE] fig6 ERREUR: {traceback.format_exc()}")
            fig6    = _empty_fig(f"fig6 erreur: {e}")
            interp6 = _empty_interp(f"Erreur fig6 : {e}")

        # ══════════════════════════════════════════════════════════════════════
        # Fig 7 + Interp 7 — Heatmap efficacité pays/mois
        # ══════════════════════════════════════════════════════════════════════
        try:
            eff = (
                fdf.groupby(["Country", "Month"])
                .apply(
                    lambda x: (x["AC_Power"].sum() / x["DC_Power"].sum() * 100)
                    if x["DC_Power"].sum() > 0 else 0,
                    include_groups=False,
                )
                .reset_index(name="efficiency")
            )
            pivot = eff.pivot(index="Country", columns="Month", values="efficiency")
            lbl = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Juin",
                   7:"Jul",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
            pivot.columns = [lbl.get(int(c), str(c)) for c in pivot.columns]

            eff_pays  = eff.groupby("Country")["efficiency"].mean().sort_values(ascending=False)
            best_p    = eff_pays.idxmax()
            best_v    = float(eff_pays.max())
            worst_p   = eff_pays.idxmin()
            worst_v   = float(eff_pays.min())
            eff_glob  = float(eff["efficiency"].mean())
            classmt   = " > ".join([f"{p} {v:.0f}%" for p, v in eff_pays.items()])

            fig7 = go.Figure(go.Heatmap(
                z=pivot.values,
                x=list(pivot.columns),
                y=list(pivot.index),
                colorscale=[[0, "#fef3c7"], [0.5, "#f59e0b"], [1, "#b45309"]],
                text=[[f"{v:.1f}%" if pd.notna(v) else "" for v in row]
                      for row in pivot.values],
                texttemplate="%{text}", textfont={"size": 11},
                hovertemplate="<b>%{y}</b> — %{x}<br>Efficacité: %{z:.2f}%<extra></extra>",
                colorbar=dict(title="Efficacité %"), zmin=85, zmax=95,
            ))
            fig7.update_layout(
                **LAYOUT_BASE, height=380,
                xaxis=dict(title="Mois"),
                yaxis=dict(title="Pays"),
            )
            print(f"[ENERGIE] fig7 OK ({len(eff)} combos pays/mois)")

            interp7 = _ibox(C_ORANGE, [
                html.P(html.Strong(f"Contexte : {ctx}"),
                       style={"color": "#6b7280", "fontSize": "0.85rem", "marginBottom": "6px"}),
                html.P([
                    f"Efficacité moyenne DC→AC sur cette sélection : ",
                    html.Strong(f"{eff_glob:.1f}%"),
                    f". Classement : {classmt}. ",
                    html.Strong(best_p),
                    f" affiche les meilleures performances ({best_v:.0f}%), ",
                    html.Strong(worst_p),
                    f" les plus faibles ({worst_v:.0f}%).",
                ]),
                html.P(
                    "Les variations saisonnières d'efficacité s'expliquent par l'effet thermique : "
                    "les mois chauds dégradent légèrement le rendement des cellules PV. "
                    "Les zones les plus sombres sont prioritaires pour la maintenance préventive."
                ),
            ])
        except Exception as e:
            print(f"[ENERGIE] fig7 ERREUR: {traceback.format_exc()}")
            fig7    = _empty_fig(f"fig7 erreur: {e}")
            interp7 = _empty_interp(f"Erreur fig7 : {e}")

        return (
            fig1, fig2, fig3, fig4, fig5, fig6, fig7,
            interp1, interp2, interp3, interp4, interp5, interp6, interp7,
        )