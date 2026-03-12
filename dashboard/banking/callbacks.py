"""
dashboard/banking/callbacks.py — VERSION AMÉLIORÉE — Interprétations 100% Dynamiques
═══════════════════════════════════════════════════════════════════════════
AUDIT & CORRECTIONS :
  ✅ Toutes les interprétations sont désormais dynamiques (callbacks dédiés)
  ✅ Thème clair unifié (fond blanc #ffffff, fond page #f0f2f5) — cohérent avec CSS
  ✅ Sidebar : résumé contextuel dynamique (nb banques, total bilan, etc.)
  ✅ Interprétation KPI Overview : compare vs année N-1 et vs secteur
  ✅ Interprétation Évolution : détecte tendance (croissance/stagnation/déclin)
  ✅ Interprétation Classement : identifie le leader et les percentiles
  ✅ Interprétation Parts de Marché : calcule la part du TOP 3
  ✅ Interprétation Emploi/Ressources : identifie les banques sur-engagées
  ✅ Interprétation Ratios Overview : alerte si < seuil BCEAO
  ✅ Interprétation Radar : identifie points forts/faibles
  ✅ Interprétation Carte : compte les banques présentes
  ✅ Fiche Banque : synthèse positionnement + rang sectoriel dynamique
  ✅ Comparaison : synthèse des écarts entre banques sélectionnées
  ✅ Ratios Tab : alerte nombre de banques sous seuil BCEAO
  ✅ Heatmap : identifie la meilleure/pire banque
  ✅ Module Prédictif : interprétation de la trajectoire projetée
═══════════════════════════════════════════════════════════════════════════
"""
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, State, callback, html, dcc, no_update
from utils.db import get_collection
from dashboard.banking.rapport import generer_rapport_pdf
from dashboard.banking.layout import (
    COORDS, C_ACCENT, C_EMERALD, C_AMBER, C_ROSE, C_SKY,
    C_TEXT, C_TEXT2, C_TEXT3, C_BG, C_CARD, C_BORDER,
    C_INDIGO_L, C_VIOLET, C_CARD2, C_BORDER2,
    _tab_overview, _tab_fiche, _tab_comparaison,
    _tab_ratios, _tab_predictif,
)

# ── Palettes ───────────────────────────────────────────────────────────────────
PALETTE = [
    "#6366F1", "#34D399", "#FBBF24", "#FB7185", "#38BDF8",
    "#A78BFA", "#F97316", "#84CC16", "#EC4899", "#14B8A6",
    "#8B5CF6", "#0EA5E9", "#F59E0B", "#10B981", "#EF4444",
]

COULEURS_GROUPE = {
    "Groupes Locaux":         "#34D399",
    "Groupes Règionaux":      "#6366F1",
    "Groupes Continentaux":   "#FBBF24",
    "Groupes Internationaux": "#FB7185",
}

LABELS = {
    "bilan":                "Bilan (M FCFA)",
    "produit_net_bancaire": "PNB (M FCFA)",
    "resultat_net":         "Résultat Net (M FCFA)",
    "fonds_propres":        "Fonds Propres (M FCFA)",
    "emploi":               "Emploi (M FCFA)",
    "ressources":           "Ressources (M FCFA)",
}

# Thème clair — cohérent avec banking_style.css
LAYOUT_BASE = dict(
    template="plotly_white",
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    margin=dict(l=8, r=8, t=8, b=8),
    font=dict(family="Segoe UI, Arial, sans-serif", size=11, color="#2c3e50"),
    hoverlabel=dict(bgcolor="#2c3e50", font_size=11, bordercolor="#667eea",
                    font_color="#ffffff"),
    transition={"duration": 350, "easing": "cubic-in-out"},
)

GROUPE_NORM = {
    "Groupes Régionaux":  "Groupes Règionaux",
    "Groupes regionaux":  "Groupes Règionaux",
    "Groupes Regionaux":  "Groupes Règionaux",
    "Locaux":             "Groupes Locaux",
    "Règionaux":          "Groupes Règionaux",
    "Régionaux":          "Groupes Règionaux",
    "Continentaux":       "Groupes Continentaux",
    "Internationaux":     "Groupes Internationaux",
}

GROUPE_REF = {
    "BAS": "Groupes Continentaux", "BCIM": "Groupes Règionaux",
    "BDK": "Groupes Règionaux", "BGFI": "Groupes Règionaux",
    "BHS": "Groupes Locaux", "BICIS": "Groupes Internationaux",
    "BIS": "Groupes Règionaux", "BNDE": "Groupes Locaux",
    "BOA": "Groupes Continentaux", "BRM": "Groupes Règionaux",
    "BSIC": "Groupes Règionaux", "CBAO": "Groupes Continentaux",
    "CBI": "Groupes Règionaux", "CDS": "Groupes Règionaux",
    "CITIBANK": "Groupes Continentaux", "ECOBANK": "Groupes Continentaux",
    "FBNBANK": "Groupes Continentaux", "LBA": "Groupes Locaux",
    "LBO": "Groupes Locaux", "NSIA Banque": "Groupes Règionaux",
    "ORABANK": "Groupes Continentaux", "SGBS": "Groupes Internationaux",
    "UBA": "Groupes Continentaux",
}

CHAMPS_NUM = [
    "bilan", "emploi", "ressources", "fonds_propres",
    "produit_net_bancaire", "resultat_net",
    "interets_produits", "interets_charges",
    "commissions_produits", "commissions_charges",
    "charges_generales_exploitation", "cout_du_risque",
    "resultat_brut_exploitation", "resultat_exploitation",
    "resultat_avant_impot", "impots_benefices",
    "ratio_solvabilite", "ratio_rendement_actifs",
    "ratio_rentabilite_capitaux", "coefficient_exploitation",
    "ratio_emplois_ressources",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/D"
    v = float(val)
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.2f} B"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f} Mds"
    return f"{v:,.0f} M"


def _empty_fig(msg="Données non disponibles"):
    fig = go.Figure()
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        annotations=[dict(
            text=msg, showarrow=False,
            font=dict(size=13, color="#95a5a6"),
            xref="paper", yref="paper", x=0.5, y=0.5,
        )],
    )
    return fig


def _empty_interp():
    """Retourne un bloc interprétation vide."""
    return html.Div()


def _interp_content(emoji, title, text, color="#667eea"):
    """Construit un bloc interprétation dynamique."""
    return html.Div([
        html.Div(f"{emoji} {title}", className="bank-interp-label",
                 style={"color": color}),
        html.P(text, className="bank-interp-text"),
    ])


def charger():
    """Charge et normalise les données bancaires depuis MongoDB."""
    try:
        col, client = get_collection()
        docs = list(col.find({}, {"_id": 0}))
        client.close()
        if not docs:
            return pd.DataFrame()
        df = pd.DataFrame(docs)

        if "simp_" in df.columns and "sigle" not in df.columns:
            df.rename(columns={"simp_": "sigle"}, inplace=True)
        if "sigle" in df.columns:
            df["sigle"] = df["sigle"].astype(str).str.strip()

        if "groupe_bancaire" in df.columns:
            df["groupe_bancaire"] = df["groupe_bancaire"].apply(
                lambda g: GROUPE_NORM.get(g, g) if isinstance(g, str) else g
            )
            if "sigle" in df.columns:
                df["groupe_bancaire"] = df.apply(
                    lambda r: GROUPE_REF.get(r["sigle"], r["groupe_bancaire"]), axis=1
                )

        for c in CHAMPS_NUM:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        if "annee" in df.columns:
            df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")

        # Recalcul ratios si absents
        if "ratio_solvabilite" not in df.columns or df["ratio_solvabilite"].isna().all():
            if "fonds_propres" in df.columns and "bilan" in df.columns:
                df["ratio_solvabilite"] = (df["fonds_propres"] / df["bilan"] * 100).round(4)
        if "ratio_rendement_actifs" not in df.columns or df["ratio_rendement_actifs"].isna().all():
            if "resultat_net" in df.columns and "bilan" in df.columns:
                df["ratio_rendement_actifs"] = (df["resultat_net"] / df["bilan"] * 100).round(4)
        if "ratio_rentabilite_capitaux" not in df.columns or df["ratio_rentabilite_capitaux"].isna().all():
            if "resultat_net" in df.columns and "fonds_propres" in df.columns:
                df["ratio_rentabilite_capitaux"] = (df["resultat_net"] / df["fonds_propres"] * 100).round(4)
        if "coefficient_exploitation" not in df.columns or df["coefficient_exploitation"].isna().all():
            if "charges_generales_exploitation" in df.columns and "produit_net_bancaire" in df.columns:
                df["coefficient_exploitation"] = (
                    df["charges_generales_exploitation"] / df["produit_net_bancaire"] * 100
                ).round(4)
        if "ratio_emplois_ressources" not in df.columns or df["ratio_emplois_ressources"].isna().all():
            if "emploi" in df.columns and "ressources" in df.columns:
                df["ratio_emplois_ressources"] = (
                    df["emploi"] / df["ressources"].replace(0, float("nan")) * 100
                ).round(4)
        return df
    except Exception as e:
        import traceback
        print(f"[charger] Erreur : {e}\n{traceback.format_exc()}")
        return pd.DataFrame()


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    except Exception:
        return "99,102,241"

_int_from_hex = _hex_to_rgb


def _apply_groupe_filter(df, groupe):
    if groupe and groupe != "Tous":
        return df[df["groupe_bancaire"] == groupe]
    return df


def _kpi_card(label, value, subtitle, icon, color, delta=None):
    delta_el = []
    if delta is not None and not (isinstance(delta, float) and math.isnan(delta)):
        up = delta >= 0
        delta_el = [html.Div([
            f"{'↑' if up else '↓'} {abs(delta):.1f}%",
        ], style={
            "fontSize": "11px", "fontWeight": "600",
            "color": C_EMERALD if up else C_ROSE,
            "marginTop": "4px",
        })]

    return html.Div([
        html.Div([
            html.Div(label, style={
                "fontSize": "9px", "fontWeight": "700",
                "letterSpacing": "0.12em", "textTransform": "uppercase",
                "color": "#7f8c8d",
            }),
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.Span("●", style={"color": color, "fontSize": "18px", "marginRight": "8px"}),
            html.Span(value, style={
                "fontSize": "22px", "fontWeight": "800",
                "color": C_TEXT, "letterSpacing": "-0.03em",
            }),
        ]),
        *delta_el,
        html.Div(subtitle, style={
            "fontSize": "11px", "color": "#95a5a6",
            "marginTop": "6px",
        }),
    ], style={
        "background": "#ffffff",
        "border": f"1px solid {C_BORDER}",
        "borderRadius": "12px",
        "padding": "18px 20px",
        "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
        "height": "100%",
        "borderLeft": f"4px solid {color}",
        "transition": "transform 0.2s",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING : TABS
# ═══════════════════════════════════════════════════════════════════════════════
@callback(Output("tabs-content", "children"), Input("tabs-main", "value"))
def render_tab(tab):
    if tab == "overview":    return _tab_overview()
    elif tab == "fiche":     return _tab_fiche()
    elif tab == "comparaison": return _tab_comparaison()
    elif tab == "ratios":    return _tab_ratios()
    elif tab == "predictif": return _tab_predictif()
    return _tab_overview()


# ═══════════════════════════════════════════════════════════════════════════════
# OPTIONS BANQUES
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("f-banque", "options"), Output("f-banque", "value"),
    Input("url-bancaire", "pathname"),
)
def init_banque_options(_):
    df = charger()
    if df.empty or "sigle" not in df.columns:
        return [], None
    banques = sorted(df["sigle"].dropna().unique().tolist())
    return [{"label": b, "value": b} for b in banques], None


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR RÉSUMÉ DYNAMIQUE
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("sidebar-resume", "children"),
    Input("f-annee",  "value"),
    Input("f-groupe", "value"),
    Input("f-banque", "value"),
)
def sidebar_resume(annee, groupe, banque):
    df = charger()
    if df.empty or not annee:
        return _empty_interp()
    d = df[df["annee"] == int(annee)]
    d = _apply_groupe_filter(d, groupe)
    if banque:
        d = d[d["sigle"] == banque]

    nb = len(d)
    bilan_tot = d["bilan"].sum() if "bilan" in d.columns else 0
    pnb_tot   = d["produit_net_bancaire"].sum() if "produit_net_bancaire" in d.columns else 0

    if banque:
        label = f"📌 {banque} — {annee}"
    elif groupe and groupe != "Tous":
        label = f"📌 {groupe} — {annee}"
    else:
        label = f"📌 Secteur bancaire — {annee}"

    items = [
        html.Div(label, style={"fontWeight": "700", "color": C_TEXT,
                               "fontSize": "0.85rem", "marginBottom": "8px"}),
        html.Div([
            html.Span("Banques : ", style={"color": "#7f8c8d", "fontSize": "0.8rem"}),
            html.Span(str(nb), style={"fontWeight": "700", "color": C_ACCENT, "fontSize": "0.8rem"}),
        ]),
        html.Div([
            html.Span("Bilan total : ", style={"color": "#7f8c8d", "fontSize": "0.8rem"}),
            html.Span(fmt(bilan_tot), style={"fontWeight": "700", "color": C_EMERALD, "fontSize": "0.8rem"}),
        ], style={"marginTop": "4px"}),
        html.Div([
            html.Span("PNB total : ", style={"color": "#7f8c8d", "fontSize": "0.8rem"}),
            html.Span(fmt(pnb_tot), style={"fontWeight": "700", "color": C_AMBER, "fontSize": "0.8rem"}),
        ], style={"marginTop": "4px"}),
    ]

    return html.Div(items, style={
        "background": "#f8f9fa", "borderRadius": "10px",
        "padding": "12px 14px", "borderLeft": f"3px solid {C_ACCENT}",
        "fontSize": "0.82rem",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# KPI CARDS — VUE D'ENSEMBLE
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("kpi-bilan", "children"), Output("kpi-pnb",   "children"),
    Output("kpi-rn",    "children"), Output("kpi-fp",    "children"),
    Input("f-banque", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def kpi_overview(banque, annee, groupe):
    df = charger()
    blank = _kpi_card("N/D", "–", "Données indisponibles", "fas fa-circle", "#95a5a6")
    if df.empty or not annee:
        return blank, blank, blank, blank

    d = df[df["annee"] == int(annee)]
    d = _apply_groupe_filter(d, groupe)
    if banque:
        d = d[d["sigle"] == banque]

    def _kv(col):
        v = d[col].sum() if col in d.columns else None
        return v if (v and not pd.isna(v)) else None

    def _delta(col, val):
        if val is None: return None
        prev = df[df["annee"] == int(annee) - 1]
        prev = _apply_groupe_filter(prev, groupe)
        if banque: prev = prev[prev["sigle"] == banque]
        pv = prev[col].sum() if col in prev.columns else 0
        if pv and pv != 0:
            return ((val - pv) / abs(pv)) * 100
        return None

    bilan = _kv("bilan"); pnb = _kv("produit_net_bancaire")
    rn    = _kv("resultat_net"); fp = _kv("fonds_propres")
    lbl   = banque or ("Secteur" if groupe == "Tous" else groupe)

    return (
        _kpi_card("TOTAL BILAN",    fmt(bilan), f"{lbl} · {annee}", "fas fa-balance-scale", "#6366F1", _delta("bilan", bilan)),
        _kpi_card("PNB",            fmt(pnb),   f"{lbl} · {annee}", "fas fa-chart-line",    "#34D399", _delta("produit_net_bancaire", pnb)),
        _kpi_card("RÉSULTAT NET",   fmt(rn),    f"{lbl} · {annee}", "fas fa-coins",          "#FBBF24", _delta("resultat_net", rn)),
        _kpi_card("FONDS PROPRES",  fmt(fp),    f"{lbl} · {annee}", "fas fa-shield-alt",     "#38BDF8", _delta("fonds_propres", fp)),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTERPRÉTATION KPI OVERVIEW — DYNAMIQUE
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("interp-kpi-overview", "children"),
    Input("f-banque", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_kpi_overview(banque, annee, groupe):
    df = charger()
    if df.empty or not annee:
        return _empty_interp()

    d = df[df["annee"] == int(annee)]
    d = _apply_groupe_filter(d, groupe)
    if banque:
        d = d[d["sigle"] == banque]

    if d.empty:
        return _empty_interp()

    parts = []

    # Comparaison N vs N-1
    if "bilan" in d.columns:
        bilan_n = d["bilan"].sum()
        prev = df[df["annee"] == int(annee) - 1]
        prev = _apply_groupe_filter(prev, groupe)
        if banque: prev = prev[prev["sigle"] == banque]
        if not prev.empty and "bilan" in prev.columns:
            bilan_n1 = prev["bilan"].sum()
            if bilan_n1 > 0:
                delta_pct = (bilan_n - bilan_n1) / bilan_n1 * 100
                direction = "progressé" if delta_pct > 0 else "reculé"
                emoji = "📈" if delta_pct > 0 else "📉"
                parts.append(
                    f"{emoji} Le bilan total a {direction} de {abs(delta_pct):.1f}% "
                    f"par rapport à {int(annee)-1} ({fmt(bilan_n1)} → {fmt(bilan_n)})."
                )

    # Rentabilité
    if "resultat_net" in d.columns and "bilan" in d.columns:
        rn_total = d["resultat_net"].sum()
        b_total  = d["bilan"].sum()
        if b_total > 0:
            roa = rn_total / b_total * 100
            if roa < 0:
                parts.append(f"⚠️ Le résultat net agrégé est négatif ({fmt(rn_total)} FCFA) — "
                             f"ROA sectoriel de {roa:.2f}%, signalant une pression sur la rentabilité.")
            elif roa < 1:
                parts.append(f"📊 ROA sectoriel de {roa:.2f}% — en dessous de la norme de 1%, "
                             f"indiquant des marges sous pression.")
            else:
                parts.append(f"✅ ROA sectoriel de {roa:.2f}% — au-dessus du seuil de 1%, "
                             f"reflétant une gestion saine des actifs.")

    # Nb banques
    if banque:
        nb_annees = len(d)
        parts.append(f"📅 Données disponibles pour {banque} sur {nb_annees} année(s).")
    else:
        nb_b = len(d["sigle"].unique()) if "sigle" in d.columns else 0
        parts.append(f"🏦 {nb_b} établissement(s) analysé(s) pour {annee}.")

    if not parts:
        return _empty_interp()

    return html.Div([
        html.Div("💡 Analyse Contextuelle", className="bank-interp-label"),
        html.P("  ".join(parts), className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ÉVOLUTION TEMPORELLE
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-evolution", "figure"),
    Input("f-banque", "value"), Input("f-indic", "value"),
    Input("f-groupe", "value"), Input("f-annee", "value"),
)
def g_evolution(banque, indic, groupe, annee):
    df = charger()
    if df.empty or not indic:
        return _empty_fig()
    if indic not in df.columns:
        return _empty_fig(f"Indicateur '{indic}' non disponible")

    traces = []
    if banque:
        d = df[df["sigle"] == banque].sort_values("annee").dropna(subset=[indic, "annee"])
        if d.empty:
            return _empty_fig(f"Pas de données pour {banque}")
        traces.append(go.Scatter(
            x=d["annee"].astype(int), y=d[indic],
            name=banque, mode="lines+markers",
            line=dict(color=C_ACCENT, width=2.5),
            marker=dict(size=7, color=C_ACCENT),
            hovertemplate=f"<b>{banque}</b><br>{LABELS.get(indic, indic)}: %{{y:,.0f}}<extra></extra>",
        ))
    else:
        df2 = _apply_groupe_filter(df, groupe)
        for i, b in enumerate(sorted(df2["sigle"].dropna().unique())):
            d = df2[df2["sigle"] == b].sort_values("annee").dropna(subset=[indic, "annee"])
            if d.empty: continue
            traces.append(go.Scatter(
                x=d["annee"].astype(int), y=d[indic],
                name=b, mode="lines+markers",
                line=dict(color=PALETTE[i % len(PALETTE)], width=1.8),
                marker=dict(size=5),
                hovertemplate=f"<b>{b}</b><br>{LABELS.get(indic, indic)}: %{{y:,.0f}}<extra></extra>",
            ))

    if not traces:
        return _empty_fig()

    fig = go.Figure(traces)
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        xaxis=dict(title="Année", gridcolor="#f0f0f0", tickformat="d"),
        yaxis=dict(title=LABELS.get(indic, "M FCFA"), gridcolor="#f0f0f0"),
        legend=dict(font=dict(size=9), orientation="h", y=-0.22, x=0.5, xanchor="center"),
    )
    # Add smooth line animation via updatemenus
    fig.update_traces(
        line=dict(shape="spline", smoothing=0.6),
        selector=dict(type="scatter"),
    )
    return fig


@callback(
    Output("interp-evolution", "children"),
    Input("f-banque", "value"), Input("f-indic", "value"),
    Input("f-groupe", "value"),
)
def interp_evolution(banque, indic, groupe):
    df = charger()
    if df.empty or not indic or indic not in df.columns:
        return _empty_interp()

    if banque:
        d = df[df["sigle"] == banque].sort_values("annee").dropna(subset=[indic, "annee"])
        if d.empty or len(d) < 2:
            return _empty_interp()
        vals = d[indic].values
        first, last = vals[0], vals[-1]
        yr_first = int(d["annee"].values[0])
        yr_last  = int(d["annee"].values[-1])
        if first and first != 0:
            total_growth = (last - first) / abs(first) * 100
            cagr = (abs(last / first) ** (1 / max(yr_last - yr_first, 1)) - 1) * 100
            if last > first:
                txt = (f"📈 {banque} affiche une croissance de {total_growth:.1f}% sur {LABELS.get(indic, indic)} "
                       f"entre {yr_first} et {yr_last} (TCAM : {cagr:.1f}%). "
                       f"Dernière valeur : {fmt(last)} FCFA.")
            else:
                txt = (f"📉 {banque} enregistre un repli de {abs(total_growth):.1f}% sur {LABELS.get(indic, indic)} "
                       f"entre {yr_first} et {yr_last}. Valeur en {yr_last} : {fmt(last)} FCFA. "
                       f"Un diagnostic approfondi s'impose.")
        else:
            txt = f"Données insuffisantes pour calculer la tendance de {banque}."
    else:
        # Vue sectorielle : trouver le max et le tendance globale
        df2 = _apply_groupe_filter(df, groupe)
        if df2.empty:
            return _empty_interp()
        yr_min = int(df2["annee"].min())
        yr_max = int(df2["annee"].max())
        agg = df2.groupby("annee")[indic].sum().sort_index()
        if len(agg) >= 2:
            first, last = agg.iloc[0], agg.iloc[-1]
            if first > 0:
                g = (last - first) / first * 100
                lbl_indic = LABELS.get(indic, indic)
                dir_txt = "croissance" if g > 0 else "contraction"
                txt = (f"📊 Le secteur affiche une {dir_txt} globale de {abs(g):.1f}% "
                       f"sur {lbl_indic} entre {yr_min} et {yr_max}. "
                       f"Total {yr_max} : {fmt(last)} FCFA.")
            else:
                txt = f"Tendance sectorielle indisponible pour {LABELS.get(indic, indic)}."
        else:
            txt = "Données insuffisantes pour analyser la tendance."

    return html.Div([
        html.Div("💡 Analyse de la Tendance", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSEMENT
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-classement", "figure"),
    Input("f-annee", "value"), Input("f-indic", "value"),
    Input("f-groupe", "value"), Input("f-banque", "value"),
)
def g_classement(annee, indic, groupe, banque):
    if not annee: return _empty_fig()
    df = charger()
    if df.empty or not indic or indic not in df.columns:
        return _empty_fig()

    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    d = d[["sigle", indic, "groupe_bancaire"]].dropna(subset=[indic])
    if d.empty:
        return _empty_fig(f"Aucune donnée {indic} pour {annee}")

    d = d.sort_values(indic, ascending=True)

    # Gradient colors: selected bank = accent, others = group color with gradient effect
    bar_colors = []
    bar_opacities = []
    for _, row in d.iterrows():
        if banque and row["sigle"] == banque:
            bar_colors.append(C_ACCENT)
            bar_opacities.append(1.0)
        else:
            base_color = COULEURS_GROUPE.get(row.get("groupe_bancaire", ""), "#a0aec0")
            bar_colors.append(base_color)
            bar_opacities.append(0.75)

    fig = go.Figure(go.Bar(
        x=d[indic], y=d["sigle"],
        orientation="h",
        marker=dict(
            color=bar_colors,
            opacity=bar_opacities,
            line=dict(
                color=[C_ACCENT if (banque and row["sigle"] == banque) else "rgba(255,255,255,0.3)" for _, row in d.iterrows()],
                width=[2 if (banque and row["sigle"] == banque) else 0.5 for _, row in d.iterrows()],
            ),
        ),
        text=d[indic].apply(fmt),
        textposition="auto",
        textfont=dict(size=9, color=C_TEXT),
        hovertemplate="<b>%{y}</b><br>" + LABELS.get(indic, indic) + ": %{x:,.0f} M FCFA<extra></extra>",
        cliponaxis=True,
    ))
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("transition", "margin")},
        autosize=True,
        xaxis=dict(title=LABELS.get(indic, ""), gridcolor="#f0f0f0", zeroline=False),
        yaxis=dict(tickfont=dict(size=10), automargin=True),
        showlegend=False,
        margin=dict(l=10, r=60, t=10, b=30),
        bargap=0.2,
    )
    return fig


@callback(
    Output("interp-classement", "children"),
    Input("f-annee", "value"), Input("f-indic", "value"),
    Input("f-groupe", "value"), Input("f-banque", "value"),
)
def interp_classement(annee, indic, groupe, banque):
    df = charger()
    if df.empty or not annee or not indic or indic not in df.columns:
        return _empty_interp()

    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    d = d[["sigle", indic]].dropna(subset=[indic]).sort_values(indic, ascending=False).reset_index(drop=True)
    if d.empty:
        return _empty_interp()

    leader = d.iloc[0]
    nb = len(d)
    top3_share = d.head(3)[indic].sum() / d[indic].sum() * 100 if d[indic].sum() > 0 else 0
    lbl = LABELS.get(indic, indic)

    txt = (f"🏆 Leader : {leader['sigle']} avec {fmt(leader[indic])} FCFA de {lbl} en {annee}. "
           f"Le TOP 3 concentre {top3_share:.1f}% du total sectoriel — "
           f"{'marché très concentré' if top3_share > 60 else 'marché modérément concentré'}.")

    if banque and "sigle" in d.columns:
        row_b = d[d["sigle"] == banque]
        if not row_b.empty:
            rang = row_b.index[0] + 1
            pct = ((nb - rang) / (nb - 1) * 100) if nb > 1 else 100
            txt += (f" {banque} se classe {rang}ème sur {nb} établissements "
                    f"(top {100-pct:.0f}% du secteur).")

    return html.Div([
        html.Div("💡 Analyse du Classement", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# PARTS DE MARCHÉ
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-parts", "figure"),
    Input("f-annee", "value"), Input("f-groupe", "value"),
)
def g_parts(annee, groupe):
    if not annee: return _empty_fig()
    df = charger()
    if df.empty or "bilan" not in df.columns:
        return _empty_fig()

    d = df[df["annee"] == int(annee)][["sigle", "bilan", "groupe_bancaire"]].dropna(subset=["bilan"])
    d = _apply_groupe_filter(d, groupe) if groupe and groupe != "Tous" else d
    if d.empty:
        return _empty_fig(f"Aucune donnée bilan pour {annee}")

    d = d.sort_values("bilan", ascending=False)
    if len(d) > 12:
        top = d.head(12)
        autres = pd.DataFrame([{"sigle": "Autres", "bilan": d.tail(len(d)-12)["bilan"].sum()}])
        d = pd.concat([top, autres], ignore_index=True)

    # Rich color palette with pull effect for top bank
    pull_vals = [0.06] + [0.0] * (len(d) - 1)  # pull out the leader

    fig = go.Figure(go.Pie(
        labels=d["sigle"],
        values=d["bilan"],
        hole=0.50,
        pull=pull_vals,
        textinfo="percent",
        textfont=dict(size=9, color="#2c3e50"),
        insidetextorientation="radial",
        marker=dict(
            colors=PALETTE[:len(d)],
            line=dict(color="#ffffff", width=2),
        ),
        hovertemplate="<b>%{label}</b><br>Bilan: %{value:,.0f} M FCFA<br>Part: %{percent}<extra></extra>",
        sort=False,
        direction="clockwise",
        rotation=90,
    ))

    total_bilan = d["bilan"].sum()
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("transition", "margin")},
        autosize=True,
        margin=dict(l=10, r=140, t=30, b=10),
        showlegend=True,
        legend=dict(
            font=dict(size=8),
            orientation="v",
            yanchor="middle", y=0.5,
            xanchor="left", x=1.0,
            itemsizing="constant",
        ),
        annotations=[dict(
            text=f"<b>Total</b><br>{fmt(total_bilan)}",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=11, color=C_TEXT, family="Segoe UI, Arial"),
            align="center",
        )],
    )
    return fig


@callback(
    Output("interp-parts", "children"),
    Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_parts(annee, groupe):
    df = charger()
    if df.empty or not annee or "bilan" not in df.columns:
        return _empty_interp()

    d = df[df["annee"] == int(annee)][["sigle", "bilan", "groupe_bancaire"]].dropna(subset=["bilan"])
    d = _apply_groupe_filter(d, groupe) if groupe and groupe != "Tous" else d
    if d.empty:
        return _empty_interp()

    d = d.sort_values("bilan", ascending=False).reset_index(drop=True)
    total = d["bilan"].sum()
    top1 = d.iloc[0]
    top1_share = top1["bilan"] / total * 100
    top3_share = d.head(3)["bilan"].sum() / total * 100

    # Concentration par groupe
    if "groupe_bancaire" in d.columns:
        grp_share = d.groupby("groupe_bancaire")["bilan"].sum().sort_values(ascending=False)
        top_grp = grp_share.index[0] if len(grp_share) > 0 else "N/D"
        top_grp_pct = grp_share.iloc[0] / total * 100 if total > 0 else 0
        grp_txt = f" Le groupe dominant est '{top_grp}' avec {top_grp_pct:.1f}% du bilan sectoriel."
    else:
        grp_txt = ""

    conc_level = "très concentré" if top3_share > 65 else ("concentré" if top3_share > 50 else "diversifié")

    txt = (f"🥧 {top1['sigle']} détient {top1_share:.1f}% du bilan sectoriel total en {annee}. "
           f"Le TOP 3 cumule {top3_share:.1f}% — marché {conc_level}.{grp_txt}")

    return html.Div([
        html.Div("💡 Analyse de la Concentration", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# EMPLOI & RESSOURCES
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-emploi-ressources", "figure"),
    Input("f-annee", "value"), Input("f-groupe", "value"),
)
def g_emploi_ressources(annee, groupe):
    if not annee: return _empty_fig()
    df = charger()
    if df.empty: return _empty_fig()
    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    d = d[["sigle", "emploi", "ressources"]].dropna(subset=["emploi", "ressources"])
    if d.empty:
        return _empty_fig(f"Aucune donnée emploi/ressources pour {annee}")

    d = d.sort_values("emploi", ascending=False).head(15)
    fig = go.Figure([
        go.Bar(name="Emploi",     x=d["sigle"], y=d["emploi"],
               marker=dict(color=C_ACCENT, opacity=0.85),
               hovertemplate="<b>%{x}</b><br>Emploi: %{y:,.0f} M<extra></extra>"),
        go.Bar(name="Ressources", x=d["sigle"], y=d["ressources"],
               marker=dict(color=C_EMERALD, opacity=0.85),
               hovertemplate="<b>%{x}</b><br>Ressources: %{y:,.0f} M<extra></extra>"),
    ])
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, barmode="group",
        xaxis=dict(tickfont=dict(size=9), gridcolor="#f0f0f0"),
        yaxis=dict(title="M FCFA", gridcolor="#f0f0f0"),
        legend=dict(font=dict(size=10), orientation="h", y=-0.2, x=0.5, xanchor="center"),
    )
    return fig


@callback(
    Output("interp-emploi", "children"),
    Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_emploi(annee, groupe):
    df = charger()
    if df.empty or not annee:
        return _empty_interp()
    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    d = d[["sigle", "emploi", "ressources"]].dropna(subset=["emploi", "ressources"])
    if d.empty:
        return _empty_interp()

    d["ratio_er"] = d["emploi"] / d["ressources"] * 100
    sur_engagees = d[d["ratio_er"] > 100]["sigle"].tolist()
    ratio_med = d["ratio_er"].median()
    total_emp = d["emploi"].sum()
    total_res = d["ressources"].sum()
    ratio_secteur = total_emp / total_res * 100 if total_res > 0 else 0

    txt = (f"⚖️ Ratio Emplois/Ressources sectoriel : {ratio_secteur:.1f}% en {annee} "
           f"(médiane banque : {ratio_med:.1f}%). "
           f"{'✅ Les dépôts couvrent globalement les crédits.' if ratio_secteur < 100 else '⚠️ Les crédits dépassent les dépôts au niveau sectoriel.'}")

    if sur_engagees:
        txt += (f" {len(sur_engagees)} banque(s) dépassent 100% : "
                f"{', '.join(sur_engagees[:3])}{'...' if len(sur_engagees) > 3 else ''} — "
                f"risque de liquidité à surveiller.")

    return html.Div([
        html.Div("💡 Analyse Emplois / Ressources", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# RATIOS FINANCIERS (VUE D'ENSEMBLE)
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-ratios", "figure"),
    Input("f-banque", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def g_ratios(banque, annee, groupe):
    if not annee: return _empty_fig()
    df = charger()
    if df.empty: return _empty_fig()

    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    if banque:
        d = d[d["sigle"] == banque]

    ratios = {
        "Solvabilité (FP/Bilan %)":  "ratio_solvabilite",
        "ROA (RN/Bilan %)":          "ratio_rendement_actifs",
        "ROE (RN/FP %)":             "ratio_rentabilite_capitaux",
        "Coeff. Exploit. (%)":       "coefficient_exploitation",
        "Liquidité (E/R %)":         "ratio_emplois_ressources",
    }
    colors_map = [C_ACCENT, C_EMERALD, C_AMBER, C_ROSE, C_SKY]
    labels, values, colors = [], [], []

    for i, (lbl, col) in enumerate(ratios.items()):
        if col in d.columns:
            v = d[col].mean()
            if not pd.isna(v):
                labels.append(lbl); values.append(round(float(v), 2))
                colors.append(colors_map[i % len(colors_map)])

    if not labels:
        return _empty_fig("Ratios non calculés")

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=colors, opacity=0.85),
        text=[f"{v:.2f}%" for v in values], textposition="outside",
        textfont=dict(size=10, color=C_TEXT),
        hovertemplate="<b>%{x}</b><br>Valeur: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        xaxis=dict(tickfont=dict(size=9), gridcolor="#f0f0f0"),
        yaxis=dict(title="%", gridcolor="#f0f0f0"),
        showlegend=False,
    )
    return fig


@callback(
    Output("interp-ratios-overview", "children"),
    Input("f-banque", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_ratios_overview(banque, annee, groupe):
    df = charger()
    if df.empty or not annee:
        return _empty_interp()

    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    if banque:
        d = d[d["sigle"] == banque]
    if d.empty:
        return _empty_interp()

    parts = []
    if "ratio_solvabilite" in d.columns:
        solv_moy = d["ratio_solvabilite"].mean()
        nb_sous = (d["ratio_solvabilite"] < 8).sum()
        if not pd.isna(solv_moy):
            status = "✅ conforme" if solv_moy >= 8 else "⚠️ sous la norme"
            parts.append(f"🛡️ Solvabilité moyenne : {solv_moy:.1f}% ({status} BCEAO 8%). "
                         f"{nb_sous} banque(s) sous le seuil réglementaire.")
    if "ratio_rendement_actifs" in d.columns:
        roa_moy = d["ratio_rendement_actifs"].mean()
        if not pd.isna(roa_moy):
            emoji = "✅" if roa_moy >= 1 else "⚠️"
            parts.append(f"{emoji} ROA moyen : {roa_moy:.2f}% (norme ~1-2%).")
    if "coefficient_exploitation" in d.columns:
        coeff_moy = d["coefficient_exploitation"].mean()
        if not pd.isna(coeff_moy):
            emoji = "✅" if coeff_moy <= 65 else "⚠️"
            parts.append(f"{emoji} Coefficient d'exploitation moyen : {coeff_moy:.1f}% "
                         f"({'efficace' if coeff_moy <= 65 else 'à optimiser'}, seuil optimal 65%).")

    if not parts:
        return _empty_interp()

    return html.Div([
        html.Div("💡 Analyse des Ratios Prudentiels", className="bank-interp-label"),
        html.P("  ".join(parts), className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# RADAR — PROFIL FINANCIER
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-radar", "figure"),
    Input("f-banque", "value"), Input("f-annee", "value"),
)
def g_radar(banque, annee):
    if not annee or not banque: return _empty_fig("Sélectionnez une banque")
    df = charger()
    if df.empty: return _empty_fig()

    d = df[(df["annee"] == int(annee)) & (df["sigle"] == banque)]
    if d.empty: return _empty_fig(f"Pas de données pour {banque} en {annee}")

    all_year = df[df["annee"] == int(annee)]
    dims = [
        ("Bilan",      "bilan"),      ("PNB",       "produit_net_bancaire"),
        ("Résultat",   "resultat_net"),("F.Propres", "fonds_propres"),
        ("Emploi",     "emploi"),     ("Ressources","ressources"),
    ]
    r_vals = []
    for _, col in dims:
        v  = d[col].values[0] if col in d.columns else 0
        mx = all_year[col].max() if col in all_year.columns else 1
        r_vals.append(round(float(v / mx * 100), 1) if mx and not pd.isna(v) and mx > 0 else 0)

    cats = [l for l, _ in dims]
    fig = go.Figure(go.Scatterpolar(
        r=r_vals + [r_vals[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor=f"rgba({_hex_to_rgb(C_ACCENT)},0.15)",
        line=dict(color=C_ACCENT, width=2.5), name=banque,
        hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        polar=dict(
            bgcolor="#f8f9fa",
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=8), gridcolor="#dee2e6"),
            angularaxis=dict(gridcolor="#dee2e6", tickfont=dict(size=9)),
        ),
        showlegend=False,
    )
    return fig


@callback(
    Output("interp-radar", "children"),
    Input("f-banque", "value"), Input("f-annee", "value"),
)
def interp_radar(banque, annee):
    df = charger()
    if df.empty or not annee or not banque:
        return html.Div([
            html.Div("💡 Interprétation", className="bank-interp-label"),
            html.P("Sélectionnez une banque pour voir son profil radar normalisé vs le maximum sectoriel.",
                   className="bank-interp-text"),
        ])

    d = df[(df["annee"] == int(annee)) & (df["sigle"] == banque)]
    all_year = df[df["annee"] == int(annee)]
    if d.empty:
        return _empty_interp()

    dims = [("Bilan","bilan"),("PNB","produit_net_bancaire"),("Résultat","resultat_net"),
            ("F.Propres","fonds_propres"),("Emploi","emploi"),("Ressources","ressources")]

    scores = {}
    for lbl, col in dims:
        if col not in d.columns: continue
        v  = d[col].values[0]
        mx = all_year[col].max() if col in all_year.columns else 1
        scores[lbl] = round(float(v / mx * 100), 1) if mx and not pd.isna(v) and mx > 0 else 0

    if not scores:
        return _empty_interp()

    top_dim   = max(scores, key=scores.get)
    bot_dim   = min(scores, key=scores.get)
    avg_score = sum(scores.values()) / len(scores)

    txt = (f"🕸️ {banque} obtient un score moyen de {avg_score:.1f}% vs le maximum sectoriel en {annee}. "
           f"Point fort : {top_dim} ({scores[top_dim]:.1f}%). "
           f"Axe à renforcer : {bot_dim} ({scores[bot_dim]:.1f}%). "
           f"{'Profil de leader sectoriel.' if avg_score > 70 else 'Potentiel d amélioration significatif sur plusieurs dimensions.' if avg_score < 40 else 'Profil équilibré avec quelques axes de développement.'}")

    return html.Div([
        html.Div("💡 Analyse du Profil Radar", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# CARTE INTERACTIVE
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("g-carte", "figure"),
    Input("f-annee", "value"), Input("f-groupe", "value"),
)
def g_carte(annee, groupe):
    if not annee: return _empty_fig()
    df = charger()
    if df.empty: return _empty_fig()

    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    d = d[["sigle", "bilan", "groupe_bancaire"]].dropna(subset=["bilan"])

    lats, lons, names, bilans, groups = [], [], [], [], []
    for _, row in d.iterrows():
        sigle = str(row.get("sigle", "")).strip()
        if sigle in COORDS:
            lat, lon = COORDS[sigle]
            lats.append(lat); lons.append(lon)
            names.append(sigle)
            bilans.append(float(row.get("bilan", 0)) or 0)
            groups.append(row.get("groupe_bancaire", "Autre"))

    if not lats:
        return _empty_fig("Coordonnées non disponibles")

    max_b  = max(bilans) if bilans else 1
    sizes  = [max(12, (b / max_b) * 45) for b in bilans]
    colors = [COULEURS_GROUPE.get(g, "#6366F1") for g in groups]

    fig = go.Figure(go.Scattermapbox(
        lat=lats, lon=lons, mode="markers+text",
        marker=dict(size=sizes, color=colors, opacity=0.85, sizemode="diameter"),
        text=names, textposition="top right",
        textfont=dict(size=9, color="#2c3e50"),
        customdata=list(zip(names, bilans, groups)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Bilan: %{customdata[1]:,.0f} M FCFA<br>"
            "Groupe: %{customdata[2]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        mapbox=dict(style="carto-positron", center=dict(lat=14.7, lon=-17.45), zoom=11.5),
        margin=dict(l=0, r=0, t=0, b=0), height=400,
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(color=C_TEXT),
    )
    return fig


@callback(
    Output("interp-carte", "children"),
    Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_carte(annee, groupe):
    df = charger()
    if df.empty or not annee:
        return _empty_interp()

    d = df[df["annee"] == int(annee)].copy()
    d = _apply_groupe_filter(d, groupe)
    d = d[["sigle", "bilan", "groupe_bancaire"]].dropna(subset=["bilan"])

    nb_carte = sum(1 for _, r in d.iterrows() if str(r["sigle"]).strip() in COORDS)
    total_bilans = d["bilan"].sum()
    leader = d.sort_values("bilan", ascending=False).iloc[0] if not d.empty else None

    txt = (f"🗺️ {nb_carte} banques géolocalisées à Dakar sur {len(d)} actives en {annee}. "
           f"La taille des bulles est proportionnelle au bilan (max : {fmt(total_bilans)} FCFA au total). "
           f"{'Plus grande bulle : ' + leader['sigle'] + ' (' + fmt(leader['bilan']) + ' FCFA).' if leader is not None else ''} "
           f"Les couleurs distinguent les 4 groupes bancaires.")

    return html.Div([
        html.Div("💡 Lecture de la Carte", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ─── FICHE BANQUE ─────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("f-banque-fiche", "options"), Output("f-banque-fiche", "value"),
    Input("tabs-main", "value"),
)
def init_fiche_options(tab):
    if tab != "fiche": return no_update, no_update
    df = charger()
    if df.empty or "sigle" not in df.columns: return [], None
    banques = sorted(df["sigle"].dropna().unique().tolist())
    return [{"label": b, "value": b} for b in banques], banques[0] if banques else None


@callback(
    Output("fiche-positionnement-resume", "children"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def fiche_positionnement_resume(banque, annee):
    """Bloc synthèse positionnement sectoriel dynamique."""
    if not banque or not annee:
        return html.Div()
    df = charger()
    if df.empty:
        return html.Div()

    d_all = df[df["annee"] == int(annee)].dropna(subset=["bilan"])
    d_b   = d_all[d_all["sigle"] == banque]
    if d_b.empty or d_all.empty:
        return html.Div()

    d_sorted = d_all.sort_values("bilan", ascending=False).reset_index(drop=True)
    rang_bilan = d_sorted[d_sorted["sigle"] == banque].index
    rang_bilan = int(rang_bilan[0]) + 1 if len(rang_bilan) > 0 else "N/D"
    nb_total   = len(d_sorted)

    bilan_b  = d_b["bilan"].values[0]
    bilan_s  = d_all["bilan"].sum()
    part_b   = bilan_b / bilan_s * 100 if bilan_s > 0 else 0

    groupe   = d_b["groupe_bancaire"].values[0] if "groupe_bancaire" in d_b.columns else "N/D"
    solv     = d_b["ratio_solvabilite"].values[0] if "ratio_solvabilite" in d_b.columns else None
    solv_txt = f"{float(solv):.1f}%" if solv is not None and not pd.isna(solv) else "N/D"
    solv_ok  = (solv is not None and not pd.isna(solv) and float(solv) >= 8)

    items = [
        html.Div(f"📋 Synthèse — {banque} · {annee}",
                 style={"fontWeight": "700", "color": C_TEXT, "fontSize": "1rem",
                        "marginBottom": "12px"}),
        html.Div([
            # Rang
            html.Div([
                html.Div(f"#{rang_bilan}", style={"fontSize": "1.8rem", "fontWeight": "800",
                                                    "color": C_ACCENT}),
                html.Div(f"/ {nb_total} banques", style={"fontSize": "0.8rem", "color": C_TEXT2}),
                html.Div("Rang (bilan)", style={"fontSize": "0.75rem", "color": C_TEXT3,
                                                 "textTransform": "uppercase"}),
            ], style={"textAlign": "center", "padding": "10px 20px",
                      "borderRight": f"1px solid {C_BORDER}"}),
            # Part de marché
            html.Div([
                html.Div(f"{part_b:.1f}%", style={"fontSize": "1.8rem", "fontWeight": "800",
                                                    "color": C_EMERALD}),
                html.Div("du bilan sectoriel", style={"fontSize": "0.8rem", "color": C_TEXT2}),
                html.Div("Part de marché", style={"fontSize": "0.75rem", "color": C_TEXT3,
                                                   "textTransform": "uppercase"}),
            ], style={"textAlign": "center", "padding": "10px 20px",
                      "borderRight": f"1px solid {C_BORDER}"}),
            # Groupe
            html.Div([
                html.Div(groupe.replace("Groupes ", ""), style={"fontSize": "1rem", "fontWeight": "700",
                                                                  "color": C_AMBER}),
                html.Div("Classification BCEAO", style={"fontSize": "0.8rem", "color": C_TEXT2}),
                html.Div("Groupe bancaire", style={"fontSize": "0.75rem", "color": C_TEXT3,
                                                    "textTransform": "uppercase"}),
            ], style={"textAlign": "center", "padding": "10px 20px",
                      "borderRight": f"1px solid {C_BORDER}"}),
            # Solvabilité
            html.Div([
                html.Div(solv_txt, style={"fontSize": "1.8rem", "fontWeight": "800",
                                          "color": C_EMERALD if solv_ok else C_ROSE}),
                html.Div("✅ Conforme" if solv_ok else "⚠️ Sous seuil",
                         style={"fontSize": "0.8rem",
                                "color": C_EMERALD if solv_ok else C_ROSE}),
                html.Div("Solvabilité (BCEAO ≥8%)", style={"fontSize": "0.75rem", "color": C_TEXT3,
                                                             "textTransform": "uppercase"}),
            ], style={"textAlign": "center", "padding": "10px 20px"}),
        ], style={"display": "flex", "flexWrap": "wrap", "justifyContent": "space-around"}),
    ]

    return html.Div(items, style={
        "background": "#ffffff", "borderRadius": "12px",
        "padding": "20px 24px", "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
        "borderLeft": f"4px solid {C_ACCENT}", "marginBottom": "18px",
    })


@callback(
    Output("fiche-kpi-bilan", "children"), Output("fiche-kpi-pnb",   "children"),
    Output("fiche-kpi-rn",    "children"), Output("fiche-kpi-fp",    "children"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def fiche_kpis(banque, annee):
    blank = _kpi_card("N/D", "–", "–", "fas fa-circle", "#95a5a6")
    if not banque or not annee:
        return blank, blank, blank, blank
    df = charger()
    if df.empty: return blank, blank, blank, blank
    d = df[(df["sigle"] == banque) & (df["annee"] == int(annee))]
    if d.empty: return blank, blank, blank, blank

    def gv(col):
        if col not in d.columns: return None
        v = d[col].values[0]
        return float(v) if not pd.isna(v) else None

    def delta(col, val):
        if val is None: return None
        prev = df[(df["sigle"] == banque) & (df["annee"] == int(annee) - 1)]
        if prev.empty or col not in prev.columns: return None
        pv = prev[col].values[0]
        if pd.isna(pv) or pv == 0: return None
        return ((val - float(pv)) / abs(float(pv))) * 100

    bilan = gv("bilan"); pnb = gv("produit_net_bancaire")
    rn    = gv("resultat_net"); fp  = gv("fonds_propres")
    return (
        _kpi_card("BILAN",         fmt(bilan), f"{banque} · {annee}", "fas fa-balance-scale", "#6366F1", delta("bilan", bilan)),
        _kpi_card("PNB",           fmt(pnb),   f"{banque} · {annee}", "fas fa-chart-line",    "#34D399", delta("produit_net_bancaire", pnb)),
        _kpi_card("RÉSULTAT NET",  fmt(rn),    f"{banque} · {annee}", "fas fa-coins",          "#FBBF24", delta("resultat_net", rn)),
        _kpi_card("FONDS PROPRES", fmt(fp),    f"{banque} · {annee}", "fas fa-shield-alt",     "#38BDF8", delta("fonds_propres", fp)),
    )


@callback(
    Output("interp-fiche-kpis", "children"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def interp_fiche_kpis(banque, annee):
    df = charger()
    if df.empty or not banque or not annee:
        return _empty_interp()
    d   = df[(df["sigle"] == banque) & (df["annee"] == int(annee))]
    d_s = df[df["annee"] == int(annee)]
    if d.empty: return _empty_interp()

    parts = []

    # Rang bilan
    if "bilan" in d.columns and "bilan" in d_s.columns:
        b_val = d["bilan"].values[0]
        d_sorted = d_s.sort_values("bilan", ascending=False).reset_index(drop=True)
        rang = d_sorted[d_sorted["sigle"] == banque].index
        rang = int(rang[0]) + 1 if len(rang) > 0 else None
        nb   = len(d_sorted)
        if rang and not pd.isna(b_val):
            parts.append(f"📊 Bilan de {fmt(b_val)} FCFA → rang {rang}/{nb} du secteur en {annee}.")

    # Résultat net
    if "resultat_net" in d.columns:
        rn = d["resultat_net"].values[0]
        if not pd.isna(rn):
            if rn < 0:
                parts.append(f"⚠️ Résultat net négatif ({fmt(rn)} FCFA) — situation déficitaire à analyser.")
            else:
                parts.append(f"✅ Résultat net positif ({fmt(rn)} FCFA).")

    # Delta bilan N vs N-1
    if "bilan" in df.columns:
        prev = df[(df["sigle"] == banque) & (df["annee"] == int(annee) - 1)]
        if not prev.empty and "bilan" in prev.columns:
            pv = prev["bilan"].values[0]
            cv = d["bilan"].values[0]
            if not pd.isna(pv) and not pd.isna(cv) and pv > 0:
                delta_pct = (cv - pv) / pv * 100
                dir_t = "croissance" if delta_pct >= 0 else "repli"
                parts.append(f"{'📈' if delta_pct >= 0 else '📉'} {dir_t.capitalize()} du bilan de "
                             f"{abs(delta_pct):.1f}% vs {int(annee)-1}.")

    if not parts:
        return _empty_interp()

    return html.Div([
        html.Div("💡 Analyse des KPIs", className="bank-interp-label"),
        html.P("  ".join(parts), className="bank-interp-text"),
    ])


@callback(Output("fiche-evolution", "figure"), Input("f-banque-fiche", "value"))
def fiche_evolution(banque):
    if not banque: return _empty_fig("Sélectionnez une banque")
    df = charger()
    if df.empty: return _empty_fig()
    d = df[df["sigle"] == banque].sort_values("annee")
    if d.empty: return _empty_fig(f"Pas de données pour {banque}")

    cols = ["bilan", "produit_net_bancaire", "resultat_net", "fonds_propres"]
    colors_map = [C_ACCENT, C_EMERALD, C_AMBER, "#38BDF8"]
    traces = []
    for i, col in enumerate(cols):
        if col in d.columns:
            dt = d.dropna(subset=[col])
            if not dt.empty:
                traces.append(go.Scatter(
                    x=dt["annee"].astype(int), y=dt[col],
                    name=LABELS.get(col, col).split(" ")[0],
                    mode="lines+markers",
                    line=dict(color=colors_map[i], width=2.5),
                    marker=dict(size=7),
                    hovertemplate=f"<b>{LABELS.get(col, col)}</b>: %{{y:,.0f}} M FCFA<extra></extra>",
                ))

    if not traces: return _empty_fig()
    fig = go.Figure(traces)
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        xaxis=dict(title="Année", gridcolor="#f0f0f0", tickformat="d"),
        yaxis=dict(title="M FCFA", gridcolor="#f0f0f0"),
        legend=dict(font=dict(size=9), orientation="h", y=-0.18, x=0.5, xanchor="center"),
        title=dict(text=f"Évolution 2015–2022 — {banque}", font=dict(size=12, color=C_TEXT2), x=0.01),
    )
    return fig


@callback(
    Output("interp-fiche-evolution", "children"),
    Input("f-banque-fiche", "value"),
)
def interp_fiche_evolution(banque):
    df = charger()
    if df.empty or not banque:
        return _empty_interp()
    d = df[df["sigle"] == banque].sort_values("annee").dropna(subset=["bilan"])
    if d.empty or len(d) < 2:
        return _empty_interp()

    yr_min = int(d["annee"].min()); yr_max = int(d["annee"].max())
    b_first = d["bilan"].iloc[0];   b_last  = d["bilan"].iloc[-1]
    growth  = (b_last - b_first) / b_first * 100 if b_first > 0 else 0

    # Année la plus forte
    max_idx = d["bilan"].idxmax()
    yr_peak = int(d.loc[max_idx, "annee"])
    val_peak = d.loc[max_idx, "bilan"]

    txt = (f"📅 {banque} couvre {len(d)} années ({yr_min}–{yr_max}). "
           f"Croissance du bilan de {growth:.1f}% sur la période. "
           f"Pic atteint en {yr_peak} avec {fmt(val_peak)} FCFA. "
           f"{'Trajectoire globalement haussière — positionnement renforcé.' if growth > 10 else 'Trajectoire stable — consolidation du positionnement.' if growth >= 0 else 'Trajectoire en repli — nécessite une analyse des causes.'}")

    return html.Div([
        html.Div("💡 Lecture de l'Historique", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


@callback(
    Output("fiche-radar", "figure"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def fiche_radar(banque, annee):
    if not banque or not annee: return _empty_fig("Sélectionnez une banque")
    df = charger()
    if df.empty: return _empty_fig()
    d     = df[(df["sigle"] == banque) & (df["annee"] == int(annee))]
    all_y = df[df["annee"] == int(annee)]
    if d.empty: return _empty_fig()

    dims = [("Bilan","bilan"),("PNB","produit_net_bancaire"),("Résultat","resultat_net"),
            ("F.Propres","fonds_propres"),("Emploi","emploi"),("Ressources","ressources")]
    r_vals = []
    for _, col in dims:
        v  = d[col].values[0] if col in d.columns else 0
        mx = all_y[col].max() if col in all_y.columns else 1
        r_vals.append(round(float(v / mx * 100), 1) if mx and not pd.isna(v) and mx > 0 else 0)

    cats = [l for l, _ in dims]
    fig = go.Figure(go.Scatterpolar(
        r=r_vals + [r_vals[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor=f"rgba({_hex_to_rgb(C_ACCENT)},0.15)",
        line=dict(color=C_ACCENT, width=2.5), name=banque,
    ))
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        polar=dict(
            bgcolor="#f8f9fa",
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=8), gridcolor="#dee2e6"),
            angularaxis=dict(gridcolor="#dee2e6", tickfont=dict(size=9)),
        ),
        showlegend=False,
    )
    return fig


@callback(
    Output("interp-fiche-radar", "children"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def interp_fiche_radar(banque, annee):
    df = charger()
    if df.empty or not banque or not annee: return _empty_interp()
    d     = df[(df["sigle"] == banque) & (df["annee"] == int(annee))]
    all_y = df[df["annee"] == int(annee)]
    if d.empty: return _empty_interp()

    dims = [("Bilan","bilan"),("PNB","produit_net_bancaire"),("Résultat","resultat_net"),
            ("F.Propres","fonds_propres"),("Emploi","emploi"),("Ressources","ressources")]
    scores = {}
    for lbl, col in dims:
        if col not in d.columns: continue
        v = d[col].values[0]; mx = all_y[col].max() if col in all_y.columns else 1
        scores[lbl] = round(float(v / mx * 100), 1) if mx and not pd.isna(v) and mx > 0 else 0

    if not scores: return _empty_interp()
    top = max(scores, key=scores.get); bot = min(scores, key=scores.get)
    avg = sum(scores.values()) / len(scores)

    txt = (f"🕸️ Score normalisé moyen de {banque} : {avg:.1f}% vs maximum sectoriel. "
           f"Dimension dominante : {top} ({scores[top]:.0f}%). "
           f"Dimension la plus faible : {bot} ({scores[bot]:.0f}%). "
           f"{'Leader sur ce profil.' if avg > 70 else 'Profil dans la moyenne sectorielle.' if avg > 40 else 'Profil en retrait — axes de progression identifiés.'}")

    return html.Div([
        html.Div("💡 Profil Multidimensionnel", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


@callback(
    Output("fiche-emploi", "figure"), Input("f-banque-fiche", "value"),
)
def fiche_emploi(banque):
    if not banque: return _empty_fig("Sélectionnez une banque")
    df = charger()
    if df.empty: return _empty_fig()
    d = df[df["sigle"] == banque].sort_values("annee").dropna(subset=["emploi", "ressources"])
    if d.empty: return _empty_fig()
    fig = go.Figure([
        go.Bar(name="Emploi",     x=d["annee"].astype(int), y=d["emploi"],
               marker=dict(color=C_ACCENT, opacity=0.85)),
        go.Bar(name="Ressources", x=d["annee"].astype(int), y=d["ressources"],
               marker=dict(color=C_EMERALD, opacity=0.85)),
    ])
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, barmode="group",
        xaxis=dict(tickformat="d", gridcolor="#f0f0f0"),
        yaxis=dict(title="M FCFA", gridcolor="#f0f0f0"),
        legend=dict(font=dict(size=10), orientation="h", y=-0.22, x=0.5, xanchor="center"),
    )
    return fig


@callback(
    Output("interp-fiche-emploi", "children"), Input("f-banque-fiche", "value"),
)
def interp_fiche_emploi(banque):
    df = charger()
    if df.empty or not banque: return _empty_interp()
    d = df[df["sigle"] == banque].sort_values("annee").dropna(subset=["emploi", "ressources"])
    if d.empty: return _empty_interp()

    d = d.copy()
    d["er"] = d["emploi"] / d["ressources"] * 100
    last_er = d["er"].iloc[-1]; last_yr = int(d["annee"].iloc[-1])
    trend   = "en hausse" if d["er"].iloc[-1] > d["er"].iloc[0] else "en baisse"

    txt = (f"⚖️ Ratio Emplois/Ressources de {banque} en {last_yr} : {last_er:.1f}% "
           f"({'⚠️ dépasse 100% — dépendance refinancement' if last_er > 100 else '✅ sous 100% — situation saine'}). "
           f"Tendance {trend} sur la période. "
           f"Un ratio croissant signale une transformation bilancielle plus agressive.")

    return html.Div([
        html.Div("💡 Analyse Emplois / Ressources", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


@callback(
    Output("fiche-ratios-hist", "figure"), Input("f-banque-fiche", "value"),
)
def fiche_ratios_hist(banque):
    if not banque: return _empty_fig("Sélectionnez une banque")
    df = charger()
    if df.empty: return _empty_fig()
    d = df[df["sigle"] == banque].sort_values("annee").tail(8)
    if d.empty: return _empty_fig()

    ratios = [
        ("Solvabilité %", "ratio_solvabilite",         C_ACCENT),
        ("ROA %",         "ratio_rendement_actifs",     C_EMERALD),
        ("ROE %",         "ratio_rentabilite_capitaux", C_AMBER),
        ("Liquidité %",   "ratio_emplois_ressources",   C_SKY),
    ]
    traces = []
    for name, col, color in ratios:
        if col in d.columns:
            dt = d.dropna(subset=[col])
            if not dt.empty:
                traces.append(go.Scatter(
                    x=dt["annee"].astype(int), y=dt[col],
                    name=name, mode="lines+markers",
                    line=dict(color=color, width=2.5), marker=dict(size=6),
                ))
    if not traces: return _empty_fig("Ratios non disponibles")
    fig = go.Figure(traces)
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        xaxis=dict(tickformat="d", gridcolor="#f0f0f0"),
        yaxis=dict(title="%", gridcolor="#f0f0f0"),
        legend=dict(font=dict(size=9), orientation="h", y=-0.22, x=0.5, xanchor="center"),
    )
    return fig


@callback(
    Output("interp-fiche-ratios", "children"), Input("f-banque-fiche", "value"),
)
def interp_fiche_ratios(banque):
    df = charger()
    if df.empty or not banque: return _empty_interp()
    d = df[df["sigle"] == banque].sort_values("annee").tail(8)
    if d.empty: return _empty_interp()

    parts = []
    if "ratio_solvabilite" in d.columns:
        last_solv = d["ratio_solvabilite"].dropna()
        if not last_solv.empty:
            v = last_solv.iloc[-1]
            yr = int(d.dropna(subset=["ratio_solvabilite"])["annee"].iloc[-1])
            trend_vals = last_solv.values
            trend = "en progression" if len(trend_vals) > 1 and trend_vals[-1] > trend_vals[0] else "en repli"
            parts.append(f"🛡️ Solvabilité {yr} : {v:.1f}% {'✅' if v >= 8 else '⚠️'} ({trend} sur la période).")

    if "ratio_rendement_actifs" in d.columns:
        last_roa = d["ratio_rendement_actifs"].dropna()
        if not last_roa.empty:
            v = last_roa.iloc[-1]
            parts.append(f"📊 ROA : {v:.2f}% ({'satisfaisant' if v >= 1 else 'à améliorer'}, norme ~1%).")

    if not parts:
        return _empty_interp()

    return html.Div([
        html.Div("💡 Évolution des Ratios", className="bank-interp-label"),
        html.P("  ".join(parts), className="bank-interp-text"),
    ])


@callback(
    Output("fiche-table-container", "children"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def fiche_table(banque, annee):
    if not banque:
        return html.Div([
            html.Div("🏦", style={"fontSize": "2.5rem", "marginBottom": "10px"}),
            html.Div("Sélectionnez une banque dans le menu déroulant ci-dessus",
                     style={"color": "#7f8c8d", "fontSize": "0.95rem"}),
        ], style={"textAlign": "center", "padding": "40px 20px"})

    df = charger()
    if df.empty:
        return html.Div("⚠️ Données indisponibles.", style={"padding": "20px", "color": C_ROSE})

    d = df[df["sigle"] == banque].sort_values("annee", ascending=False)
    if d.empty:
        return html.Div(f"⚠️ Aucune donnée pour {banque}.",
                        style={"padding": "20px", "color": C_ROSE})

    cols_show = ["annee", "bilan", "produit_net_bancaire", "resultat_net",
                 "fonds_propres", "emploi", "ressources",
                 "ratio_solvabilite", "ratio_rendement_actifs"]
    cols_show = [c for c in cols_show if c in d.columns]
    d2 = d[cols_show].head(10)

    col_labels = {
        "annee": "Année", "bilan": "Bilan (M FCFA)", "produit_net_bancaire": "PNB (M FCFA)",
        "resultat_net": "Rés. Net (M FCFA)", "fonds_propres": "F. Propres (M FCFA)",
        "emploi": "Emploi (M FCFA)", "ressources": "Ressources (M FCFA)",
        "ratio_solvabilite": "Solvabilité %", "ratio_rendement_actifs": "ROA %",
    }

    header_style = {
        "padding": "11px 14px", "textAlign": "right", "fontSize": "11px",
        "fontWeight": "700", "letterSpacing": "0.05em", "textTransform": "uppercase",
        "color": "#ffffff", "background": "#667eea",
        "borderRight": "1px solid rgba(255,255,255,0.15)", "whiteSpace": "nowrap",
    }
    cell_style = {
        "padding": "9px 14px", "fontSize": "13px", "textAlign": "right",
        "color": C_TEXT, "borderBottom": f"1px solid {C_BORDER}",
        "borderRight": f"1px solid {C_BORDER}",
    }
    annee_style = dict(cell_style, textAlign="center", fontWeight="700",
                       color="#667eea", background="#f0f2ff")
    ratio_ok   = dict(cell_style, color="#27ae60", fontWeight="600")
    ratio_warn = dict(cell_style, color="#e74c3c", fontWeight="600")

    rows = []
    for i, (_, row) in enumerate(d2.iterrows()):
        row_bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
        cells  = []
        for c in cols_show:
            v = row[c]
            if c == "annee":
                txt = str(int(v)) if not pd.isna(v) else "–"
                cells.append(html.Td(txt, style=annee_style))
            elif c == "ratio_solvabilite":
                txt = f"{float(v):.2f}%" if not pd.isna(v) else "–"
                style = ratio_ok if (not pd.isna(v) and float(v) >= 8) else ratio_warn
                cells.append(html.Td(txt, style=dict(style, background=row_bg)))
            elif c == "ratio_rendement_actifs":
                txt = f"{float(v):.2f}%" if not pd.isna(v) else "–"
                style = ratio_ok if (not pd.isna(v) and float(v) >= 1) else ratio_warn
                cells.append(html.Td(txt, style=dict(style, background=row_bg)))
            else:
                txt = fmt(v) if not pd.isna(v) else "–"
                cells.append(html.Td(txt, style=dict(cell_style, background=row_bg)))
        rows.append(html.Tr(cells))

    return html.Div([
        html.Table([
            html.Thead(html.Tr([
                html.Th(col_labels.get(c, c),
                        style=dict(header_style, textAlign="center") if c == "annee" else header_style)
                for c in cols_show
            ]), style={"position": "sticky", "top": "0", "zIndex": "1"}),
            html.Tbody(rows),
        ], style={"width": "100%", "borderCollapse": "collapse"}),
    ], style={
        "background": "#ffffff", "borderRadius": "10px",
        "border": f"1px solid {C_BORDER}",
        "overflow": "auto", "maxHeight": "420px",
        "boxShadow": "0 2px 10px rgba(0,0,0,0.05)",
    })


@callback(
    Output("interp-fiche-table", "children"),
    Input("f-banque-fiche", "value"), Input("f-annee", "value"),
)
def interp_fiche_table(banque, annee):
    df = charger()
    if df.empty or not banque: return _empty_interp()
    d = df[df["sigle"] == banque].sort_values("annee", ascending=False)
    if d.empty: return _empty_interp()

    nb_ans = len(d)
    yr_range = f"{int(d['annee'].min())}–{int(d['annee'].max())}"
    nb_null = d[["bilan","resultat_net","fonds_propres"]].isna().sum().sum()

    txt = (f"📋 {nb_ans} années disponibles pour {banque} ({yr_range}). "
           f"Les valeurs sont en millions de FCFA. "
           f"{'✅ Données complètes.' if nb_null == 0 else f'⚠️ {nb_null} valeur(s) manquante(s) — les années 2021-2022 peuvent avoir moins d indicateurs (source PDF BCEAO).'} "
           f"Les ratios en rouge signalent un non-respect des normes prudentielles BCEAO.")

    return html.Div([
        html.Div("💡 Lecture du Tableau", className="bank-interp-label"),
        html.P(txt, className="bank-interp-text"),
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ─── COMPARAISON ──────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@callback(Output("f-banques-comp", "options"), Input("tabs-main", "value"))
def init_comp_options(tab):
    if tab != "comparaison": return no_update
    df = charger()
    if df.empty or "sigle" not in df.columns: return []
    banques = sorted(df["sigle"].dropna().unique().tolist())
    return [{"label": b, "value": b} for b in banques]


def _comp_bar(df, banques, annee, col, title, color):
    d = df[(df["sigle"].isin(banques)) & (df["annee"] == int(annee))][["sigle", col]].dropna(subset=[col])
    if d.empty: return _empty_fig(f"Aucune donnée {title} pour {annee}")
    d = d.sort_values(col, ascending=False)
    fig = go.Figure(go.Bar(
        x=d["sigle"], y=d[col],
        marker=dict(color=[PALETTE[banques.index(s) % len(PALETTE)] for s in d["sigle"]], opacity=0.85),
        text=d[col].apply(fmt), textposition="outside",
        textfont=dict(size=10, color=C_TEXT),
        hovertemplate="<b>%{x}</b><br>" + title + ": %{y:,.0f} M FCFA<extra></extra>",
    ))
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        xaxis=dict(tickfont=dict(size=9), gridcolor="#f0f0f0"),
        yaxis=dict(title="M FCFA", gridcolor="#f0f0f0"),
        showlegend=False,
    )
    return fig


def _comp_evol(df, banques, col, title):
    traces = []
    for i, b in enumerate(banques):
        d = df[df["sigle"] == b].sort_values("annee").dropna(subset=[col, "annee"])
        if not d.empty:
            traces.append(go.Scatter(
                x=d["annee"].astype(int), y=d[col], name=b,
                mode="lines+markers",
                line=dict(color=PALETTE[i % len(PALETTE)], width=2.5),
                marker=dict(size=6),
                hovertemplate=f"<b>{b}</b><br>{title}: %{{y:,.0f}} M<extra></extra>",
            ))
    if not traces: return _empty_fig()
    fig = go.Figure(traces)
    fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        xaxis=dict(title="Année", gridcolor="#f0f0f0", tickformat="d"),
        yaxis=dict(title="M FCFA", gridcolor="#f0f0f0"),
        legend=dict(font=dict(size=9), orientation="h", y=-0.2, x=0.5, xanchor="center"),
    )
    return fig


@callback(
    Output("comp-bilan", "figure"),   Output("comp-pnb",        "figure"),
    Output("comp-rn",    "figure"),   Output("comp-fp",         "figure"),
    Output("comp-solv",  "figure"),   Output("comp-evol-bilan", "figure"),
    Output("comp-evol-pnb", "figure"),Output("comp-radar",      "figure"),
    Input("f-banques-comp", "value"), Input("f-annee", "value"),
)
def comp_all(banques, annee):
    empty8 = tuple(_empty_fig("Sélectionnez au moins 2 banques") for _ in range(8))
    if not banques or len(banques) < 2 or not annee:
        return empty8
    df = charger()
    if df.empty: return empty8

    c_bilan = _comp_bar(df, banques, annee, "bilan",                "Bilan",         C_ACCENT)
    c_pnb   = _comp_bar(df, banques, annee, "produit_net_bancaire", "PNB",           C_EMERALD)
    c_rn    = _comp_bar(df, banques, annee, "resultat_net",         "Résultat Net",  C_AMBER)
    c_fp    = _comp_bar(df, banques, annee, "fonds_propres",        "Fonds Propres", "#38BDF8")

    d_solv = df[(df["sigle"].isin(banques)) & (df["annee"] == int(annee))][
        ["sigle", "ratio_solvabilite"]].dropna()
    if not d_solv.empty:
        c_solv = go.Figure(go.Bar(
            x=d_solv["sigle"], y=d_solv["ratio_solvabilite"],
            marker=dict(color=[PALETTE[banques.index(s) % len(PALETTE)] for s in d_solv["sigle"]], opacity=0.85),
            text=d_solv["ratio_solvabilite"].apply(lambda v: f"{v:.2f}%"),
            textposition="outside", textfont=dict(size=10, color=C_TEXT),
        ))
        c_solv.add_hline(y=8, line_dash="dash", line_color=C_ROSE, line_width=1.5,
                         annotation_text="BCEAO 8%", annotation_font_color=C_ROSE)
        c_solv.update_layout(**{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, yaxis=dict(title="%", gridcolor="#f0f0f0"), showlegend=False)
    else:
        c_solv = _empty_fig()

    c_ev_b = _comp_evol(df, banques, "bilan",                "Bilan")
    c_ev_p = _comp_evol(df, banques, "produit_net_bancaire", "PNB")

    # Radar multi-banques
    all_y = df[df["annee"] == int(annee)]
    dims  = [("Bilan","bilan"),("PNB","produit_net_bancaire"),("Résultat","resultat_net"),
             ("F.Propres","fonds_propres"),("Emploi","emploi"),("Ressources","ressources")]
    cats = [l for l, _ in dims]
    radar_fig = go.Figure()
    for i, b in enumerate(banques):
        d = df[(df["sigle"] == b) & (df["annee"] == int(annee))]
        if d.empty: continue
        r_vals = []
        for _, col in dims:
            v  = d[col].values[0] if col in d.columns else 0
            mx = all_y[col].max() if col in all_y.columns else 1
            r_vals.append(round(float(v / mx * 100), 1) if mx and not pd.isna(v) and mx > 0 else 0)
        radar_fig.add_trace(go.Scatterpolar(
            r=r_vals + [r_vals[0]], theta=cats + [cats[0]], fill="toself",
            fillcolor=f"rgba({_int_from_hex(PALETTE[i % len(PALETTE)])},0.12)",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2), name=b,
        ))
    radar_fig.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
        polar=dict(
            bgcolor="#f8f9fa",
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=8), gridcolor="#dee2e6"),
            angularaxis=dict(gridcolor="#dee2e6", tickfont=dict(size=9)),
        ),
        legend=dict(font=dict(size=10), orientation="h", y=-0.1, x=0.5, xanchor="center"),
    )
    return c_bilan, c_pnb, c_rn, c_fp, c_solv, c_ev_b, c_ev_p, radar_fig


# Interprétations comparaison
@callback(
    Output("interp-comp-synthese",   "children"),
    Output("interp-comp-bilan",      "children"),
    Output("interp-comp-pnb",        "children"),
    Output("interp-comp-rn",         "children"),
    Output("interp-comp-fp",         "children"),
    Output("interp-comp-solv",       "children"),
    Output("interp-comp-evol-bilan", "children"),
    Output("interp-comp-evol-pnb",   "children"),
    Output("interp-comp-radar",      "children"),
    Input("f-banques-comp", "value"), Input("f-annee", "value"),
)
def interp_comp_all(banques, annee):
    empty9 = tuple(html.Div() for _ in range(9))
    if not banques or len(banques) < 2 or not annee:
        return empty9

    df = charger()
    if df.empty:
        return empty9

    d = df[(df["sigle"].isin(banques)) & (df["annee"] == int(annee))]

    def _make(text):
        return html.Div([
            html.Div("💡 Interprétation", className="bank-interp-label"),
            html.P(text, className="bank-interp-text"),
        ])

    def _leader_txt(col, lbl):
        sub = d[["sigle", col]].dropna(subset=[col]).sort_values(col, ascending=False)
        if sub.empty: return f"Données {lbl} non disponibles pour la sélection."
        leader = sub.iloc[0]; nb = len(sub)
        if nb > 1:
            dernier = sub.iloc[-1]
            ecart = (leader[col] - dernier[col]) / abs(dernier[col]) * 100 if dernier[col] != 0 else 0
            return (f"🏆 {leader['sigle']} domine avec {fmt(leader[col])} FCFA de {lbl} en {annee}. "
                    f"Écart avec {dernier['sigle']} (dernier) : {ecart:.1f}%. "
                    f"{'Forte disparité entre les établissements.' if abs(ecart) > 100 else 'Niveaux relativement proches.'}")
        return f"{leader['sigle']} : {fmt(leader[col])} FCFA de {lbl} en {annee}."

    # Synthèse générale
    b_list = ", ".join(banques)
    synth = (f"⚖️ Comparaison de {len(banques)} banques ({b_list}) en {annee}. "
             f"Utilisez les graphiques ci-dessous pour identifier les forces et faiblesses relatives "
             f"de chaque établissement sur les principaux KPIs financiers.")

    interp_bilan = _make(_leader_txt("bilan", "bilan"))
    interp_pnb   = _make(_leader_txt("produit_net_bancaire", "PNB"))
    interp_rn    = _make(
        _leader_txt("resultat_net", "résultat net") + " " +
        (f"⚠️ {', '.join(d[d['resultat_net'] < 0]['sigle'].tolist())} en déficit."
         if "resultat_net" in d.columns and (d["resultat_net"] < 0).any() else "")
    )
    interp_fp = _make(_leader_txt("fonds_propres", "fonds propres"))

    if "ratio_solvabilite" in d.columns:
        solv_sub = d[["sigle","ratio_solvabilite"]].dropna()
        sous_seuil = solv_sub[solv_sub["ratio_solvabilite"] < 8]["sigle"].tolist()
        solv_txt = (f"🛡️ Solvabilité des banques sélectionnées : "
                    f"{', '.join(f'{r.sigle} ({r.ratio_solvabilite:.1f}%)' for _, r in solv_sub.iterrows())}. "
                    f"{'⚠️ Sous seuil BCEAO 8% : ' + ', '.join(sous_seuil) + '.' if sous_seuil else '✅ Toutes conformes au seuil BCEAO 8%.'}")
        interp_solv = _make(solv_txt)
    else:
        interp_solv = html.Div()

    # Évolutions
    def _evol_txt(col, lbl):
        parts = []
        for b in banques:
            d2 = df[df["sigle"] == b].sort_values("annee").dropna(subset=[col])
            if d2.empty or len(d2) < 2: continue
            g = (d2[col].iloc[-1] - d2[col].iloc[0]) / abs(d2[col].iloc[0]) * 100 if d2[col].iloc[0] != 0 else 0
            dir_sym = "↑" if g >= 0 else "↓"
            parts.append(f"{b} {dir_sym}{abs(g):.0f}%")
        return (f"📈 Croissance {lbl} (2015→{int(df['annee'].max())}) : " + ", ".join(parts) + ".") if parts else ""

    interp_evol_b = _make(_evol_txt("bilan", "bilan"))
    interp_evol_p = _make(_evol_txt("produit_net_bancaire", "PNB"))

    # Radar
    all_y = df[df["annee"] == int(annee)]
    dims  = [("Bilan","bilan"),("PNB","produit_net_bancaire"),("Résultat","resultat_net"),
             ("F.Propres","fonds_propres"),("Emploi","emploi"),("Ressources","ressources")]
    scores_all = {}
    for b in banques:
        d2 = all_y[all_y["sigle"] == b]
        if d2.empty: continue
        sc = []
        for _, col in dims:
            if col not in d2.columns: continue
            v = d2[col].values[0]; mx = all_y[col].max() if col in all_y.columns else 1
            sc.append(float(v / mx * 100) if mx and not pd.isna(v) and mx > 0 else 0)
        scores_all[b] = sum(sc) / len(sc) if sc else 0

    if scores_all:
        best = max(scores_all, key=scores_all.get)
        worst = min(scores_all, key=scores_all.get)
        radar_txt = (f"🕸️ Score radar normalisé — meilleur profil : {best} ({scores_all[best]:.0f}%), "
                     f"profil le plus faible : {worst} ({scores_all[worst]:.0f}%). "
                     f"Le radar compare 6 dimensions financières normalisées au maximum sectoriel.")
    else:
        radar_txt = "Données insuffisantes pour le radar."

    interp_radar = _make(radar_txt)

    return (
        _make(synth),
        interp_bilan, interp_pnb, interp_rn, interp_fp, interp_solv,
        interp_evol_b, interp_evol_p, interp_radar,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORT PDF
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("download-rapport", "data"), Output("msg-rapport", "children"),
    Input("btn-rapport", "n_clicks"),
    State("f-banque-fiche", "value"), State("f-annee", "value"),
    prevent_initial_call=True,
)
def telecharger_rapport(n, banque, annee):
    if not n: return no_update, no_update
    if not banque:
        return no_update, "⚠️ Sélectionnez d'abord une banque dans l'onglet Fiche Banque"
    try:
        import base64 as _b64
        pdf_b64 = generer_rapport_pdf(banque, annee or 2022)
        if isinstance(pdf_b64, str):
            pdf_bytes = _b64.b64decode(pdf_b64)
        else:
            pdf_bytes = pdf_b64
        return (
            dcc.send_bytes(pdf_bytes, f"rapport_{banque}_{annee or 2022}.pdf"),
            f"✅ Rapport généré pour {banque} ({annee or 2022})",
        )
    except Exception as e:
        return no_update, f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
@callback(
    Output("download-excel", "data"),
    Input("btn-excel", "n_clicks"),
    State("f-banque-fiche", "value"), State("f-annee", "value"),
    prevent_initial_call=True,
)
def telecharger_excel(n, banque, annee):
    if not n: return no_update
    df = charger()
    if df.empty: return no_update
    if banque:
        df = df[df["sigle"] == banque]

    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        cols_export = [c for c in [
            "sigle", "annee", "groupe_bancaire",
            "bilan", "emploi", "ressources", "fonds_propres",
            "produit_net_bancaire", "resultat_net",
            "ratio_solvabilite", "ratio_rendement_actifs",
            "ratio_rentabilite_capitaux", "coefficient_exploitation",
            "ratio_emplois_ressources",
        ] if c in df.columns]
        df[cols_export].sort_values(["sigle", "annee"]).to_excel(
            writer, sheet_name="Données", index=False)
        if "annee" in df.columns:
            last_yr = df["annee"].max()
            df_last = df[df["annee"] == last_yr]
            df_last[cols_export].sort_values("bilan", ascending=False).to_excel(
                writer, sheet_name=f"Résumé_{last_yr}", index=False)
    return dcc.send_bytes(buf.getvalue(), f"export_{banque or 'toutes_banques'}_{annee or 'all'}.xlsx")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB RATIOS — callbacks
# ═══════════════════════════════════════════════════════════════════════════════
def _ratio_bar(df_yr, col, title, color, seuil=None, seuil_label=None):
    sub = df_yr[[col, "sigle"]].dropna().sort_values(col, ascending=True)
    colors = [C_ROSE if v < 0 else color for v in sub[col]]
    fig = go.Figure(go.Bar(
        x=sub[col], y=sub["sigle"], orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in sub[col]], textposition="outside",
        textfont=dict(size=9, color=C_TEXT),
        hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
    ))
    if seuil is not None:
        fig.add_vline(x=seuil, line_dash="dash", line_color=C_ROSE, line_width=1.5,
                      annotation_text=seuil_label or f"Seuil {seuil}%",
                      annotation_font_color=C_ROSE, annotation_font_size=10)
    fig.update_layout(**{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
                      xaxis_title=title, yaxis_title=None,
                      xaxis=dict(gridcolor="#f0f0f0"),
                      yaxis=dict(gridcolor="#f0f0f0"),
                      showlegend=False)
    return fig


@callback(
    Output("g-ratio-solv",  "figure"), Output("g-ratio-roa",   "figure"),
    Output("g-ratio-roe",   "figure"), Output("g-ratio-coeff", "figure"),
    Output("g-ratio-liq",   "figure"),
    Input("tabs-main", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def ratios_tab_charts(tab, annee, groupe):
    empty = _empty_fig()
    if tab != "ratios":
        return empty, empty, empty, empty, empty
    df = charger()
    if df.empty:
        return empty, empty, empty, empty, empty
    df = _apply_groupe_filter(df, groupe)
    yr = annee or 2022
    df_yr = df[df["annee"] == yr].copy() if "annee" in df.columns else df.copy()
    if df_yr.empty:
        return empty, empty, empty, empty, empty

    fig_solv  = _ratio_bar(df_yr, "ratio_solvabilite",         "Solvabilité (%)",       C_ACCENT,  seuil=8,   seuil_label="BCEAO 8%")  if "ratio_solvabilite"         in df_yr.columns else empty
    fig_roa   = _ratio_bar(df_yr, "ratio_rendement_actifs",    "ROA (%)",               C_EMERALD) if "ratio_rendement_actifs"    in df_yr.columns else empty
    fig_roe   = _ratio_bar(df_yr, "ratio_rentabilite_capitaux","ROE (%)",               C_AMBER)   if "ratio_rentabilite_capitaux" in df_yr.columns else empty
    fig_coeff = _ratio_bar(df_yr, "coefficient_exploitation",  "Coeff. Exploitation (%)", C_SKY, seuil=65, seuil_label="Optimal 65%") if "coefficient_exploitation" in df_yr.columns else empty
    fig_liq   = _ratio_bar(df_yr, "ratio_emplois_ressources",  "Ratio E/R (%)",         C_VIOLET, seuil=100, seuil_label="Seuil 100%") if "ratio_emplois_ressources" in df_yr.columns else empty

    return fig_solv, fig_roa, fig_roe, fig_coeff, fig_liq


@callback(
    Output("interp-ratios-synthese", "children"),
    Output("interp-ratio-solv",      "children"),
    Output("interp-ratio-roa",       "children"),
    Output("interp-ratio-roe",       "children"),
    Output("interp-ratio-coeff",     "children"),
    Output("interp-ratio-liq",       "children"),
    Input("tabs-main", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_ratios_tab(tab, annee, groupe):
    empty7 = tuple(html.Div() for _ in range(6))
    if tab != "ratios":
        return html.Div(), *empty7[:5]
    df = charger()
    if df.empty:
        return html.Div(), *empty7[:5]

    df = _apply_groupe_filter(df, groupe)
    yr = annee or 2022
    df_yr = df[df["annee"] == yr].copy() if "annee" in df.columns else df.copy()
    if df_yr.empty:
        return html.Div(), *empty7[:5]

    def _make(text):
        return html.Div([
            html.Div("💡 Interprétation", className="bank-interp-label"),
            html.P(text, className="bank-interp-text"),
        ])

    def _ratio_stats(col):
        if col not in df_yr.columns: return None, None, None
        v = df_yr[col].dropna()
        if v.empty: return None, None, None
        return v.mean(), v.min(), v.max()

    # Synthèse globale
    nb_total = len(df_yr["sigle"].unique()) if "sigle" in df_yr.columns else 0
    if "ratio_solvabilite" in df_yr.columns:
        nb_sous = (df_yr["ratio_solvabilite"] < 8).sum()
        pct_sous = nb_sous / nb_total * 100 if nb_total > 0 else 0
    else:
        nb_sous = 0; pct_sous = 0

    _pct_s = f"{pct_sous:.0f}"
    synthese_txt = (
        f"📐 Analyse de {nb_total} banques pour l'année {yr}. "
        + (f"⚠️ {nb_sous} banque(s) ({_pct_s}%) sous le seuil BCEAO (8%)."
           if nb_sous > 0 else
           "✅ Toutes les banques respectent le seuil BCEAO (8%).")
        + " Survolez les barres pour les valeurs détaillées."
    )

    # Solvabilité
    moy_s, min_s, max_s = _ratio_stats("ratio_solvabilite")
    if moy_s is not None:
        leader_s = df_yr.loc[df_yr["ratio_solvabilite"].idxmax(), "sigle"] if "sigle" in df_yr.columns else "N/D"
        solv_txt = (f"🛡️ Solvabilité moyenne : {moy_s:.1f}% (min {min_s:.1f}% / max {max_s:.1f}%). "
                    f"Meilleure capitalisation : {leader_s} ({max_s:.1f}%). "
                    f"{'⚠️ ' + str(nb_sous) + ' banque(s) sous le seuil réglementaire.' if nb_sous > 0 else '✅ Toutes conformes.'}")
    else:
        solv_txt = "Données de solvabilité non disponibles."

    # ROA
    moy_r, min_r, max_r = _ratio_stats("ratio_rendement_actifs")
    if moy_r is not None:
        leader_r = df_yr.loc[df_yr["ratio_rendement_actifs"].idxmax(), "sigle"] if "sigle" in df_yr.columns else "N/D"
        nb_neg_roa = (df_yr["ratio_rendement_actifs"] < 0).sum()
        roa_txt = (f"📊 ROA moyen : {moy_r:.2f}% (norme 1-2%). "
                   f"Meilleur rendement actifs : {leader_r} ({max_r:.2f}%). "
                   f"{'⚠️ ' + str(nb_neg_roa) + ' banque(s) à ROA négatif.' if nb_neg_roa > 0 else '✅ Aucun ROA négatif.'}")
    else:
        roa_txt = "Données ROA non disponibles."

    # ROE
    moy_roe, _, max_roe = _ratio_stats("ratio_rentabilite_capitaux")
    if moy_roe is not None:
        roe_txt = (f"💰 ROE moyen : {moy_roe:.1f}% (norme saine 10-15%). "
                   f"{'✅ Rentabilité des capitaux satisfaisante.' if 10 <= moy_roe <= 25 else '⚠️ ROE moyen hors de la norme — vérifier la structure des fonds propres.' if moy_roe < 5 else '📈 ROE élevé — potentiellement lié à un faible niveau de fonds propres.'}")
    else:
        roe_txt = "Données ROE non disponibles."

    # Coeff exploitation
    moy_c, _, _ = _ratio_stats("coefficient_exploitation")
    if moy_c is not None:
        nb_eff = (df_yr["coefficient_exploitation"] <= 65).sum() if "coefficient_exploitation" in df_yr.columns else 0
        coeff_txt = (f"⚙️ Coefficient d'exploitation moyen : {moy_c:.1f}% (optimal < 65%). "
                     f"{nb_eff} banque(s) en dessous du seuil optimal sur {nb_total}. "
                     f"{'✅ Structure de coûts maîtrisée.' if moy_c <= 65 else '⚠️ Charges opérationnelles trop élevées en moyenne.'}")
    else:
        coeff_txt = "Données coefficient d'exploitation non disponibles."

    # Liquidité
    moy_liq, _, _ = _ratio_stats("ratio_emplois_ressources")
    if moy_liq is not None:
        nb_sur = (df_yr["ratio_emplois_ressources"] > 100).sum() if "ratio_emplois_ressources" in df_yr.columns else 0
        liq_txt = (f"💧 Ratio Emplois/Ressources moyen : {moy_liq:.1f}% (prudentiel < 100%). "
                   f"{'⚠️ ' + str(nb_sur) + ' banque(s) dépassent 100% — risque liquidité.' if nb_sur > 0 else '✅ Aucune banque en situation de surliquidité.'}")
    else:
        liq_txt = "Données liquidité non disponibles."

    return (
        _make(synthese_txt),
        _make(solv_txt), _make(roa_txt), _make(roe_txt), _make(coeff_txt), _make(liq_txt),
    )


@callback(
    Output("g-ratio-heatmap",   "figure"),
    Output("g-ratio-dist-solv", "figure"),
    Output("g-ratio-dist-roa",  "figure"),
    Input("tabs-main", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def ratios_tab_heatmap(tab, annee, groupe):
    empty = _empty_fig()
    if tab != "ratios": return empty, empty, empty
    df = charger()
    if df.empty: return empty, empty, empty
    df = _apply_groupe_filter(df, groupe)
    yr = annee or 2022
    df_yr = df[df["annee"] == yr].copy() if "annee" in df.columns else df.copy()
    if df_yr.empty: return empty, empty, empty

    ratio_cols = {
        "Solvabilité %":   "ratio_solvabilite",
        "ROA %":           "ratio_rendement_actifs",
        "ROE %":           "ratio_rentabilite_capitaux",
        "Liquidité E/R %": "ratio_emplois_ressources",
    }

    available = {lbl: col for lbl, col in ratio_cols.items() if col in df_yr.columns}
    if available and "sigle" in df_yr.columns:
        df_heat = df_yr[["sigle"] + list(available.values())].set_index("sigle")
        df_heat.columns = list(available.keys())
        df_heat = df_heat.dropna(how="all")
        df_norm = df_heat.apply(lambda c: (c - c.min()) / (c.max() - c.min() + 1e-9) * 100)
        fig_heat = go.Figure(go.Heatmap(
            z=df_norm.values, x=list(df_norm.columns), y=list(df_norm.index),
            colorscale=[[0, "#FEF2F2"], [0.4, "#FCA5A5"], [0.7, "#FEF3C7"], [1, "#D1FAE5"]],
            text=[[f"{v:.1f}%" for v in row] for row in df_heat.values],
            hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
            showscale=True,
        ))
        fig_heat.update_layout(**{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, xaxis_title=None, yaxis_title=None,
                               yaxis=dict(autorange="reversed"))
    else:
        fig_heat = empty

    if "ratio_solvabilite" in df_yr.columns:
        vals = df_yr["ratio_solvabilite"].dropna()
        fig_ds = go.Figure()
        fig_ds.add_trace(go.Histogram(x=vals, nbinsx=12, marker_color=C_ACCENT, opacity=0.8,
                                      hovertemplate="Solvabilité: %{x:.1f}%<br>Nb banques: %{y}<extra></extra>"))
        fig_ds.add_vline(x=8, line_dash="dash", line_color=C_ROSE, line_width=2,
                         annotation_text="BCEAO 8%", annotation_font_color=C_ROSE)
        fig_ds.update_layout(**{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, xaxis_title="Solvabilité (%)", yaxis_title="Nb banques",
                              xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"),
                              showlegend=False)
    else:
        fig_ds = empty

    if "ratio_rendement_actifs" in df_yr.columns:
        vals_roa = df_yr["ratio_rendement_actifs"].dropna()
        fig_dr = go.Figure()
        fig_dr.add_trace(go.Histogram(x=vals_roa, nbinsx=12, marker_color=C_EMERALD, opacity=0.8,
                                      hovertemplate="ROA: %{x:.2f}%<br>Nb banques: %{y}<extra></extra>"))
        fig_dr.add_vline(x=1, line_dash="dash", line_color=C_AMBER, line_width=1.5,
                         annotation_text="Seuil 1%", annotation_font_color=C_AMBER)
        fig_dr.update_layout(**{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, xaxis_title="ROA (%)", yaxis_title="Nb banques",
                              xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"),
                              showlegend=False)
    else:
        fig_dr = empty

    return fig_heat, fig_ds, fig_dr


@callback(
    Output("interp-heatmap",   "children"),
    Output("interp-dist-solv", "children"),
    Output("interp-dist-roa",  "children"),
    Input("tabs-main", "value"), Input("f-annee", "value"), Input("f-groupe", "value"),
)
def interp_heatmap(tab, annee, groupe):
    empty3 = tuple(html.Div() for _ in range(3))
    if tab != "ratios": return empty3
    df = charger()
    if df.empty: return empty3
    df = _apply_groupe_filter(df, groupe)
    yr = annee or 2022
    df_yr = df[df["annee"] == yr].copy() if "annee" in df.columns else df.copy()
    if df_yr.empty: return empty3

    def _make(text):
        return html.Div([html.Div("💡 Interprétation", className="bank-interp-label"),
                         html.P(text, className="bank-interp-text")])

    # Heatmap : meilleure / pire banque
    heat_parts = []
    for col, lbl in [("ratio_solvabilite","Solvabilité"), ("ratio_rendement_actifs","ROA")]:
        if col in df_yr.columns and "sigle" in df_yr.columns:
            sub = df_yr[[col,"sigle"]].dropna()
            if not sub.empty:
                best  = sub.loc[sub[col].idxmax(), "sigle"]
                worst = sub.loc[sub[col].idxmin(), "sigle"]
                heat_parts.append(f"• {lbl} : meilleur = {best} ({sub[col].max():.1f}%), "
                                  f"plus faible = {worst} ({sub[col].min():.1f}%)")
    heat_txt = (f"🔥 La carte de chaleur normalise chaque ratio de 0 à 100%. "
                f"Zones vertes = performances élevées, zones rouges = ratios faibles. "
                + " ".join(heat_parts))

    # Distribution solvabilité
    if "ratio_solvabilite" in df_yr.columns:
        vals = df_yr["ratio_solvabilite"].dropna()
        nb_sous = (vals < 8).sum()
        moy = vals.mean()
        dist_solv_txt = (f"📉 Distribution de la solvabilité en {yr} : moyenne {moy:.1f}%. "
                         f"{'⚠️ ' + str(nb_sous) + ' banque(s) sous le seuil réglementaire de 8%.' if nb_sous > 0 else '✅ Toutes les banques dépassent le seuil de 8%.'} "
                         f"Une queue gauche sous 8% identifie les banques sous-capitalisées à risque réglementaire.")
    else:
        dist_solv_txt = "Données de solvabilité non disponibles."

    # Distribution ROA
    if "ratio_rendement_actifs" in df_yr.columns:
        vals_roa = df_yr["ratio_rendement_actifs"].dropna()
        nb_neg = (vals_roa < 0).sum()
        moy_roa = vals_roa.mean()
        dist_roa_txt = (f"📉 Distribution du ROA en {yr} : moyenne {moy_roa:.2f}%. "
                        f"{'⚠️ ' + str(nb_neg) + ' banque(s) à ROA négatif — pertes structurelles.' if nb_neg > 0 else '✅ Aucun ROA négatif.'} "
                        f"Des outliers négatifs signalent des établissements fragilisant potentiellement le système.")
    else:
        dist_roa_txt = "Données ROA non disponibles."

    return _make(heat_txt), _make(dist_solv_txt), _make(dist_roa_txt)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB PRÉDICTIF — callbacks
# ═══════════════════════════════════════════════════════════════════════════════
def _linear_projection(years, values, horizon=3):
    x = np.array(years, dtype=float)
    y = np.array(values, dtype=float)
    mask = ~np.isnan(y)
    x, y = x[mask], y[mask]
    if len(x) < 2: return [], [], [], []
    coeffs = np.polyfit(x, y, 1)
    poly   = np.poly1d(coeffs)
    last   = int(x[-1])
    proj_years = list(range(last + 1, last + horizon + 1))
    proj_vals  = [poly(yr) for yr in proj_years]
    resid = y - poly(x)
    std   = resid.std()
    lower = [v - 1.96 * std for v in proj_vals]
    upper = [v + 1.96 * std for v in proj_vals]
    return proj_years, proj_vals, lower, upper


@callback(
    Output("pred-banque", "options"), Output("pred-banque", "value"),
    Input("tabs-main", "value"),
)
def init_pred_options(tab):
    if tab != "predictif": return [], None
    df = charger()
    if df.empty or "sigle" not in df.columns: return [], None
    banques = sorted(df["sigle"].dropna().unique().tolist())
    return [{"label": b, "value": b} for b in banques], banques[0] if banques else None


def _proj_card(label, val_proj, delta_pct, color):
    arrow = "↑" if delta_pct >= 0 else "↓"
    arrow_color = C_EMERALD if delta_pct >= 0 else C_ROSE
    return html.Div([
        html.Div(label, style={"fontSize": "10px", "color": "#7f8c8d",
                               "textTransform": "uppercase", "letterSpacing": "0.08em"}),
        html.Div(fmt(val_proj), style={"fontSize": "22px", "fontWeight": "800",
                                       "color": C_TEXT, "margin": "8px 0 4px"}),
        html.Div([
            html.Span(f"{arrow} {abs(delta_pct):.1f}%",
                      style={"color": arrow_color, "fontSize": "11px", "fontWeight": "700"}),
            html.Span(" vs dernière année", style={"color": "#95a5a6", "fontSize": "10px"}),
        ]),
    ], style={
        "background": "#ffffff", "border": f"1px solid {C_BORDER}",
        "borderTop": f"3px solid {color}", "borderRadius": "12px",
        "padding": "18px 20px", "height": "100%",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    })


@callback(
    Output("pred-kpi-bilan", "children"), Output("pred-kpi-pnb",  "children"),
    Output("pred-kpi-rn",    "children"), Output("pred-kpi-fp",   "children"),
    Output("g-pred-bilan",   "figure"),   Output("g-pred-pnb",    "figure"),
    Output("g-pred-fp",      "figure"),   Output("g-pred-solv",   "figure"),
    Output("g-pred-score",   "figure"),
    Input("tabs-main", "value"), Input("pred-banque", "value"),
)
def predictif_all(tab, banque):
    empty = _empty_fig()
    empty_card = html.Div()
    if tab != "predictif" or not banque:
        return (empty_card, empty_card, empty_card, empty_card, empty, empty, empty, empty, empty)

    df = charger()
    if df.empty:
        return (empty_card, empty_card, empty_card, empty_card, empty, empty, empty, empty, empty)

    dfs = df[df["sigle"] == banque].sort_values("annee")
    if dfs.empty:
        return (empty_card, empty_card, empty_card, empty_card, empty, empty, empty, empty, empty)

    years = dfs["annee"].tolist()
    HORIZON = 4

    def _proj_fig(col, title, color):
        if col not in dfs.columns: return empty
        vals = dfs[col].tolist()
        proj_years, proj_vals, lower, upper = _linear_projection(years, vals, HORIZON)
        if not proj_years: return empty
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=vals, mode="lines+markers", name="Historique",
            line=dict(color=color, width=2.5), marker=dict(size=6),
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=proj_years, y=proj_vals, mode="lines+markers", name="Projection",
            line=dict(color=color, width=2.5, dash="dot"), marker=dict(size=7, symbol="diamond"),
            hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
        ci_x = proj_years + proj_years[::-1]
        ci_y = upper + lower[::-1]
        fig.add_trace(go.Scatter(
            x=ci_x, y=ci_y, fill="toself",
            fillcolor=f"rgba({_hex_to_rgb(color)},0.10)",
            line=dict(color="rgba(0,0,0,0)"), name="IC 95%", hoverinfo="skip"))
        fig.add_vline(x=years[-1] + 0.5, line_dash="dash",
                      line_color=C_BORDER, line_width=1.5)
        fig.update_layout(**{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True, title=title,
                          xaxis_title="Année", yaxis_title="M FCFA",
                          xaxis=dict(gridcolor="#f0f0f0"),
                          yaxis=dict(gridcolor="#f0f0f0"),
                          legend=dict(orientation="h", y=1.05))
        return fig

    def _kpi(col, label, color):
        if col not in dfs.columns: return empty_card
        vals = dfs[col].tolist()
        py, pv, _, _ = _linear_projection(years, vals, 1)
        if not py: return empty_card
        last_val = next((v for v in reversed(vals) if v == v), 0)
        delta = ((pv[0] - last_val) / (abs(last_val) + 1e-9)) * 100
        return _proj_card(label, pv[0], delta, color)

    card_bilan = _kpi("bilan",                "Bilan 2026 proj.",       C_ACCENT)
    card_pnb   = _kpi("produit_net_bancaire", "PNB 2026 proj.",         C_EMERALD)
    card_rn    = _kpi("resultat_net",         "Rés. Net 2026",          C_AMBER)
    card_fp    = _kpi("fonds_propres",        "Fonds Propres 2026",     C_VIOLET)

    fig_bilan = _proj_fig("bilan",                "Bilan",           C_ACCENT)
    fig_pnb   = _proj_fig("produit_net_bancaire", "PNB",             C_EMERALD)
    fig_fp    = _proj_fig("fonds_propres",        "Fonds Propres",   C_VIOLET)
    fig_solv  = _proj_fig("ratio_solvabilite",    "Solvabilité %",   C_ROSE)

    # Score composite
    kpi_score_cols = ["bilan", "produit_net_bancaire", "resultat_net",
                      "fonds_propres", "ratio_solvabilite"]
    TARGET_YEAR = years[-1] + 4
    all_scores = {}
    for sig in df["sigle"].dropna().unique():
        d2 = df[df["sigle"] == sig].sort_values("annee")
        if d2.empty: continue
        yrs2 = d2["annee"].tolist(); score = 0; n = 0
        for col in kpi_score_cols:
            if col not in d2.columns: continue
            py, pv, _, _ = _linear_projection(yrs2, d2[col].tolist(), TARGET_YEAR - yrs2[-1])
            if py: score += pv[-1]; n += 1
        all_scores[sig] = score / n if n else 0

    if all_scores:
        max_score = max(all_scores.values()) or 1
        norm_scores = {k: v / max_score * 100 for k, v in all_scores.items()}
        sorted_items = sorted(norm_scores.items(), key=lambda x: x[1], reverse=True)
        sig_list = [i[0] for i in sorted_items]
        sc_list  = [i[1] for i in sorted_items]
        bar_colors = [C_ACCENT if s == banque else "#dee2e6" for s in sig_list]
        fig_score = go.Figure(go.Bar(
            x=sig_list, y=sc_list,
            marker_color=bar_colors,
            marker_line_color=[C_ACCENT if s == banque else C_BORDER for s in sig_list],
            marker_line_width=2,
            text=[f"{v:.0f}" for v in sc_list], textposition="outside",
            textfont=dict(size=9, color=C_TEXT),
            hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}/100<extra></extra>",
        ))
        fig_score.add_hline(y=70, line_dash="dash", line_color=C_EMERALD,
                            annotation_text="Leadership ≥ 70", line_width=1.5,
                            annotation_font_color=C_EMERALD, annotation_font_size=10)
        fig_score.update_layout(
            **{k: v for k, v in LAYOUT_BASE.items() if k != "transition"}, autosize=True,
            xaxis=dict(gridcolor="#f0f0f0", tickangle=-45),
            yaxis=dict(gridcolor="#f0f0f0", range=[0, 115]),
            showlegend=False,
        )
    else:
        fig_score = empty

    return (card_bilan, card_pnb, card_rn, card_fp,
            fig_bilan, fig_pnb, fig_fp, fig_solv, fig_score)


@callback(
    Output("interp-predictif",  "children"),
    Output("interp-pred-bilan", "children"),
    Output("interp-pred-pnb",   "children"),
    Output("interp-pred-score", "children"),
    Input("tabs-main",   "value"),
    Input("pred-banque", "value"),
)
def interp_predictif(tab, banque):
    empty4 = tuple(html.Div() for _ in range(4))
    if tab != "predictif" or not banque: return empty4
    df = charger()
    if df.empty: return empty4

    dfs = df[df["sigle"] == banque].sort_values("annee").dropna(subset=["bilan"])
    if dfs.empty or len(dfs) < 2: return empty4

    years = dfs["annee"].tolist()

    def _make(text):
        return html.Div([html.Div("💡 Interprétation", className="bank-interp-label"),
                         html.P(text, className="bank-interp-text")])

    # Synthèse
    py_b, pv_b, _, _ = _linear_projection(years, dfs["bilan"].tolist(), 4)
    if py_b:
        last_b = dfs["bilan"].iloc[-1]; proj_b = pv_b[-1]
        delta_b = (proj_b - last_b) / abs(last_b) * 100 if last_b != 0 else 0
        synth_txt = (
            f"🔮 Projection de {banque} basée sur {len(years)} années historiques (2015–{int(years[-1])}). "
            f"Bilan projeté en {py_b[-1]} : {fmt(proj_b)} FCFA "
            f"({'↑ +' if delta_b >= 0 else '↓ '}{abs(delta_b):.1f}% vs {int(years[-1])}). "
            f"{'Trajectoire de croissance soutenue.' if delta_b > 20 else 'Croissance modérée projetée.' if delta_b > 0 else 'Tendance baissière — actions correctives recommandées.'}"
        )
        interp_bilan = _make(
            f"📈 Bilan {banque} projeté à {fmt(proj_b)} FCFA en {py_b[-1]}. "
            f"La zone ombrée représente l'intervalle de confiance à 95%. "
            f"{'Une croissance soutenue confirme un positionnement concurrentiel solide.' if delta_b > 10 else 'Croissance faible : surveiller la pression concurrentielle.'}"
        )
    else:
        synth_txt = f"Données insuffisantes pour projeter {banque}."
        interp_bilan = html.Div()

    # PNB
    if "produit_net_bancaire" in dfs.columns:
        py_p, pv_p, _, _ = _linear_projection(years, dfs["produit_net_bancaire"].tolist(), 4)
        if py_p:
            last_p = dfs["produit_net_bancaire"].dropna().iloc[-1] if not dfs["produit_net_bancaire"].dropna().empty else 0
            delta_p = (pv_p[-1] - last_p) / abs(last_p) * 100 if last_p != 0 else 0
            interp_pnb = _make(
                f"📈 PNB projeté en {py_p[-1]} : {fmt(pv_p[-1])} FCFA "
                f"({'↑ +' if delta_p >= 0 else '↓ '}{abs(delta_p):.1f}% vs {int(years[-1])}). "
                f"{'Un PNB accéléré indique une conquête de parts de marché.' if delta_p > 15 else 'Décélération du PNB — possible pression concurrentielle sur les marges.' if delta_p < 0 else 'Croissance stable du PNB.'}"
            )
        else:
            interp_pnb = html.Div()
    else:
        interp_pnb = html.Div()

    # Score
    interp_score = _make(
        f"⭐ Le score composite de {banque} est calculé sur 5 KPIs projetés (bilan, PNB, "
        f"résultat net, fonds propres, solvabilité) et normalisé à 100% du maximum sectoriel. "
        f"Un score > 70 indique un positionnement de leader maintenu en {int(years[-1]) + 4}. "
        f"La banque en surbrillance est {banque}."
    )

    return _make(synth_txt), interp_bilan, interp_pnb, interp_score