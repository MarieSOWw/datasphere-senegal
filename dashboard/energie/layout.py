"""
dashboard/energie/layout.py
══════════════════════════════════════════════════════════════════
Dashboard Énergie Solaire — Design identique au Dashboard Santé
Thème : Orange solaire (gradient chaud)
Structure : Header · KPI Strip · Sidebar Filtres · Onglets · Footer

MODIFICATION : les _interp() statiques ont été remplacés par des
  html.Div(id="eng-interp-*") → contenu calculé dynamiquement
  par le callback selon les filtres actifs (pays, mois, plage).
══════════════════════════════════════════════════════════════════
"""
from dash import dcc, html

_KPI_COLORS = {
    "amber":  "#f59e0b",
    "orange": "#f97316",
    "green":  "#2ecc71",
    "red":    "#e74c3c",
    "cyan":   "#06b6d4",
    "teal":   "#10b981",
    "purple": "#8b5cf6",
}


def _kpi_card(emoji, label, value, color):
    return html.Div([
        html.Div(emoji, className=f"kpi-icon kpi-icon-{color}"),
        html.Div([
            html.Div(value, className="kpi-value",
                     style={"color": _KPI_COLORS.get(color, "#2c3e50")}),
            html.Div(label, className="kpi-label"),
        ], className="kpi-info"),
    ], className="kpi-card")


def _interp_placeholder(div_id):
    """Conteneur vide dont le contenu est rempli par le callback."""
    return html.Div(
        id=div_id,
        className="interpretation-box interpretation-box-energie",
        style={"minHeight": "48px"},
    )


def create_header():
    return html.Div([
        html.Div([
            html.H1("☀️ Monitoring de Production Solaire",
                    className="header-title"),
            html.P("Dashboard interactif pour analyser la production d'énergie solaire, "
                   "suivre les performances et optimiser le rendement des installations",
                   className="header-subtitle"),
            html.P("📊 35 136 mesures  •  4 pays  •  12 mois  •  "
                   "Filtres : Pays · Mois · Plage horaire",
                   className="header-stats"),
        ], className="header-content"),
    ], className="header header-energie")


def create_kpi_strip(total_dc, total_ac, avg_irr, avg_temp_m, avg_temp_a, total_yield, efficiency):
    return html.Div([
        html.Div([
            _kpi_card("⚡", "Puissance DC",     f"{total_dc/1e6:.1f} MWh",  "amber"),
            _kpi_card("🔌", "Puissance AC",     f"{total_ac/1e6:.1f} MWh",  "orange"),
            _kpi_card("🌞", "Irradiation Moy.", f"{avg_irr:.3f}",            "teal"),
            _kpi_card("🌡️", "Temp. Module",    f"{avg_temp_m:.1f}°C",       "red"),
            _kpi_card("💨", "Temp. Ambiante",   f"{avg_temp_a:.1f}°C",      "cyan"),
            _kpi_card("🍃", "Rendement Total",  f"{total_yield/1e6:.2f} M", "green"),
            _kpi_card("📊", "Efficacité",       f"{efficiency:.1f}%",        "purple"),
        ], className="kpi-strip-inner"),
    ], className="kpi-strip")


def create_filters():
    return html.Div([
        html.Div([
            html.H3("🔍 Filtres d'Analyse",
                    className="filter-title filter-title-energie"),

            html.Div([
                html.Label("Pays", className="filter-label"),
                dcc.Dropdown(id="eng-filter-pays", multi=True,
                             placeholder="Tous les pays",
                             className="filter-dropdown"),
            ], className="filter-group"),

            html.Div([
                html.Label("Mois", className="filter-label"),
                dcc.Dropdown(id="eng-filter-mois", multi=True,
                             placeholder="Tous les mois",
                             className="filter-dropdown"),
            ], className="filter-group"),

            html.Div([
                html.Label("Plage Horaire", className="filter-label"),
                dcc.Dropdown(
                    id="eng-filter-plage",
                    options=[
                        {"label": "Toute la journée",          "value": "all"},
                        {"label": "Matin (6h–12h)",            "value": "matin"},
                        {"label": "Après-midi (12h–18h)",      "value": "aprem"},
                        {"label": "Heures de pointe (10h–15h)","value": "pointe"},
                    ],
                    value="all",
                    clearable=False,
                    className="filter-dropdown",
                ),
            ], className="filter-group"),

            html.Div([
                html.Button("🔄 Réinitialiser", id="eng-btn-reset",
                            n_clicks=0,
                            className="reset-button reset-button-energie"),
            ], className="filter-group"),

        ], className="filters-container"),
    ], className="filters-section")


def create_charts_with_tabs():
    return html.Div([
        dcc.Tabs(id="eng-tabs", value="tab-1", children=[

            # ── Onglet 1 : Production ────────────────────────────────────────
            dcc.Tab(label="⚡ Production DC / AC", value="tab-1", children=[
                html.Div([

                    html.Div([
                        html.H3("📈 Évolution DC vs AC par Heure",
                                className="chart-title"),
                        html.P("Production DC et AC moyenne par heure de la journée",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-dc-ac", className="chart"),
                        # ← Interprétation DYNAMIQUE (remplie par callback)
                        _interp_placeholder("eng-interp-dc-ac"),
                    ], className="chart-container-full", style={"marginBottom": "30px"}),

                    html.Div([
                        html.H3("🌞 Irradiation par Mois (Saisonnalité)",
                                className="chart-title"),
                        html.P("Irradiation moyenne mensuelle pour analyser la saisonnalité",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-irradiation", className="chart"),
                        # ← Interprétation DYNAMIQUE
                        _interp_placeholder("eng-interp-irradiation"),
                    ], className="chart-container-full"),

                ], style={"padding": "20px"}),
            ]),

            # ── Onglet 2 : Températures & Rendement ─────────────────────────
            dcc.Tab(label="🌡️ Températures & Rendement", value="tab-2", children=[
                html.Div([

                    html.Div([
                        html.H3("🌡️ Distribution des Températures",
                                className="chart-title"),
                        html.P("Comparaison température ambiante vs température module",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-temp", className="chart"),
                        # ← Interprétation DYNAMIQUE
                        _interp_placeholder("eng-interp-temp"),
                    ], className="chart-container-full", style={"marginBottom": "30px"}),

                    html.Div([
                        html.H3("📊 Rendement Quotidien",
                                className="chart-title"),
                        html.P("Rendement quotidien moyen dans le temps",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-yield", className="chart"),
                        # ← Interprétation DYNAMIQUE
                        _interp_placeholder("eng-interp-yield"),
                    ], className="chart-container-full"),

                ], style={"padding": "20px"}),
            ]),

            # ── Onglet 3 : Performance & Corrélations ───────────────────────
            dcc.Tab(label="🎯 Performance & Corrélations", value="tab-3", children=[
                html.Div([

                    html.Div([
                        html.H3("🔗 Corrélation Irradiation / Puissance AC",
                                className="chart-title"),
                        html.P("Relation entre irradiation solaire et puissance AC produite",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-corr", className="chart"),
                        # ← Interprétation DYNAMIQUE
                        _interp_placeholder("eng-interp-corr"),
                    ], className="chart-container-full", style={"marginBottom": "30px"}),

                    html.Div([
                        html.H3("🌍 Patron Horaire — Production & Irradiation",
                                className="chart-title"),
                        html.P("Production et irradiation par heure pour identifier les pics",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-patron", className="chart"),
                        # ← Interprétation DYNAMIQUE
                        _interp_placeholder("eng-interp-patron"),
                    ], className="chart-container-full"),

                ], style={"padding": "20px"}),
            ]),

            # ── Onglet 4 : Efficacité & Carte thermique ──────────────────────
            dcc.Tab(label="📊 Efficacité & Heatmap", value="tab-4", children=[
                html.Div([

                    html.Div([
                        html.H3("🔥 Carte Thermique — Efficacité par Pays & Mois",
                                className="chart-title"),
                        html.P("Efficacité de conversion DC→AC (%) selon le pays et le mois",
                               className="chart-subtitle"),
                        dcc.Graph(id="eng-graph-heatmap", className="chart"),
                        # ← Interprétation DYNAMIQUE
                        _interp_placeholder("eng-interp-heatmap"),
                    ], className="chart-container-full"),

                ], style={"padding": "20px"}),
            ]),

        ], style={"marginTop": "20px"}),
    ])


def create_footer():
    return html.Div([
        html.P([
            "Dashboard Énergie Solaire  •  ",
            html.Span("Visualisations interactives", className="footer-highlight"),
            "  •  35 136 mesures  •  4 pays  •  ",
            html.A("← Accueil", href="/",
                   style={"color": "#f59e0b", "textDecoration": "none", "fontWeight": "600"}),
        ], className="footer-text"),
    ], className="footer")


def create_layout(app, df):
    """Layout principal — design identique à Santé avec thème orange."""
    if not df.empty:
        total_dc    = df["DC_Power"].sum()             if "DC_Power"            in df.columns else 0
        total_ac    = df["AC_Power"].sum()             if "AC_Power"            in df.columns else 0
        avg_irr     = df["Irradiation"].mean()         if "Irradiation"         in df.columns else 0
        avg_temp_m  = df["Module_Temperature"].mean()  if "Module_Temperature"  in df.columns else 0
        avg_temp_a  = df["Ambient_Temperature"].mean() if "Ambient_Temperature" in df.columns else 0
        total_yield = df["Total_Yield"].max()          if "Total_Yield"         in df.columns else 0
        efficiency  = (total_ac / total_dc * 100)      if total_dc > 0          else 0
    else:
        total_dc = total_ac = avg_irr = avg_temp_m = avg_temp_a = total_yield = efficiency = 0

    return html.Div([
        create_header(),
        create_kpi_strip(total_dc, total_ac, avg_irr,
                         avg_temp_m, avg_temp_a, total_yield, efficiency),

        html.Div([
            create_filters(),
            html.Div([create_charts_with_tabs()], className="main-content"),
        ], className="dashboard-container"),

        create_footer(),
        dcc.Store(id="eng-filtered-data"),
    ], className="app-container")