"""
dashboard/assurance/layout.py
══════════════════════════════════════════════════════════════════
Dashboard Assurance — Design identique au Dashboard Santé
Structure : Header · KPI Strip · Sidebar Filtres · Onglets · Footer
══════════════════════════════════════════════════════════════════
"""
from dash import dcc, html

_KPI_COLORS = {
    "blue":   "#3498db",
    "purple": "#9b59b6",
    "orange": "#f39c12",
    "green":  "#2ecc71",
    "red":    "#e74c3c",
}


def _kpi_card(emoji, label, value, color):
    return html.Div([
        html.Div(emoji, className=f"kpi-icon kpi-icon-{color}"),
        html.Div([
            html.Div(value, className="kpi-value",
                     style={"color": _KPI_COLORS[color]}),
            html.Div(label, className="kpi-label"),
        ], className="kpi-info"),
    ], className="kpi-card")


def create_interpretation_box(text):
    return html.Div([
        html.Div("💡 Interprétation", className="interpretation-label"),
        html.P(text, className="interpretation-text"),
    ], className="interpretation-box")


def create_header():
    return html.Div([
        html.Div([
            html.H1("🏢 Analyse du Portefeuille d'Assurance",
                    className="header-title"),
            html.P("Dashboard interactif pour analyser la sinistralité, évaluer "
                   "les risques et optimiser la tarification du portefeuille",
                   className="header-subtitle"),
            html.P("📊 1 000 assurés analysés  •  4 types d'assurance  •  4 régions  "
                   "•  Filtres : Type · Région · Sexe",
                   className="header-stats"),
        ], className="header-content"),
    ], className="header")


def create_kpi_strip(total_assures, prime_moy, sin_total, montant_sin, age_moy):
    return html.Div([
        html.Div([
            _kpi_card("👥", "Total Assurés",     f"{int(total_assures):,}",       "blue"),
            _kpi_card("💰", "Prime Moyenne",     f"{prime_moy:,.0f} FCFA",        "purple"),
            _kpi_card("⚠️", "Total Sinistres",   f"{int(sin_total):,}",           "orange"),
            _kpi_card("💸", "Montant Sinistres", f"{montant_sin/1e6:.2f} M FCFA", "green"),
            _kpi_card("🎂", "Âge Moyen",         f"{age_moy:.0f} ans",            "red"),
        ], className="kpi-strip-inner"),
    ], className="kpi-strip")


def create_filters():
    return html.Div([
        html.Div([
            html.H3("🔍 Filtres d'Analyse", className="filter-title"),

            html.Div([
                html.Label("Type d'Assurance", className="filter-label"),
                dcc.Dropdown(id="ass-filter-type", multi=True,
                             placeholder="Tous les types",
                             className="filter-dropdown"),
            ], className="filter-group"),

            html.Div([
                html.Label("Région", className="filter-label"),
                dcc.Dropdown(id="ass-filter-region", multi=True,
                             placeholder="Toutes les régions",
                             className="filter-dropdown"),
            ], className="filter-group"),

            html.Div([
                html.Label("Sexe", className="filter-label"),
                dcc.Dropdown(id="ass-filter-sexe", multi=True,
                             placeholder="Tous",
                             className="filter-dropdown"),
            ], className="filter-group"),

            html.Div([
                html.Button("🔄 Réinitialiser", id="ass-btn-reset",
                            n_clicks=0, className="reset-button"),
            ], className="filter-group"),

        ], className="filters-container"),
    ], className="filters-section")


def create_charts_with_tabs():
    return html.Div([
        dcc.Tabs(id="ass-tabs", value="tab-1", children=[

            # ── Onglet 1 : Vue d'ensemble ─────────────────────────────────────
            dcc.Tab(label="📊 Vue d'Ensemble", value="tab-1", children=[
                html.Div([
                    html.Div([
                        html.H3("📊 Répartition par Type d'Assurance",
                                className="chart-title"),
                        html.P("Visualiser la répartition des types d'assurance "
                               "pour identifier le type dominant et les préférences clients",
                               className="chart-subtitle"),
                        dcc.Graph(id="ass-graph-type", className="chart"),
                        create_interpretation_box(
                            "L'assurance Auto domine le portefeuille avec 26,1% (261 assurés), "
                            "suivie de Santé (25,4% – 254 assurés), Vie (24,3% – 243 assurés) "
                            "et Habitation (24,2% – 242 assurés). "
                            "Cette répartition quasi-équilibrée traduit une diversification saine. "
                            "Renforcer les segments Vie et Habitation permettrait de réduire "
                            "la concentration du risque sur l'Auto."
                        ),
                    ], className="chart-container-full", style={"marginBottom": "30px"}),

                    html.Div([
                        html.H3("🗺️ Analyse par Région — Primes & Sinistres",
                                className="chart-title"),
                        html.P("Comparer les primes totales et le nombre de sinistres "
                               "par région pour identifier les zones à fort potentiel et à risque",
                               className="chart-subtitle"),
                        dcc.Graph(id="ass-graph-region", className="chart"),
                        create_interpretation_box(
                            "Thiès concentre le plus grand portefeuille (276 assurés, 286 839 FCFA de primes) "
                            "et enregistre également le plus de sinistres (135). "
                            "Saint-Louis suit avec 255 assurés et 130 sinistres. "
                            "Dakar, malgré son poids économique, affiche le portefeuille le plus réduit "
                            "(232 assurés, 106 sinistres). "
                            "Un ratio sinistres/assurés élevé sur une région justifie "
                            "une révision tarifaire ciblée et un renforcement des critères de souscription."
                        ),
                    ], className="chart-container-full"),
                ], style={"padding": "20px"}),
            ]),

            # ── Onglet 2 : Démographie & Sinistres ───────────────────────────
            dcc.Tab(label="🦠 Démographie & Sinistres", value="tab-2", children=[
                html.Div([
                    html.Div([
                        html.H3("👤 Distribution par Âge des Assurés",
                                className="chart-title"),
                        html.P("Répartition démographique pour adapter les offres "
                               "selon les profils d'âge",
                               className="chart-subtitle"),
                        dcc.Graph(id="ass-graph-age", className="chart"),
                        create_interpretation_box(
                            "L'âge moyen des assurés est de 50 ans (médiane : 50 ans), "
                            "avec une plage allant de 18 à 79 ans. "
                            "Cette distribution quasi-uniforme reflète un portefeuille "
                            "multigénérationnel sans segment d'âge dominant. "
                            "Les tranches 40–60 ans constituent le cœur du portefeuille — "
                            "profils à revenus stables, particulièrement sensibles "
                            "aux produits Vie et Prévoyance à valoriser en priorité."
                        ),
                    ], className="chart-container-full", style={"marginBottom": "30px"}),

                    html.Div([
                        html.H3("⚠️ Analyse des Sinistres par Type",
                                className="chart-title"),
                        html.P("Nombre et montant moyen des sinistres par type "
                               "pour évaluer le risque par catégorie d'assurance",
                               className="chart-subtitle"),
                        dcc.Graph(id="ass-graph-sinistres", className="chart"),
                        create_interpretation_box(
                            "La Santé enregistre le plus grand nombre de sinistres (138) "
                            "et le montant moyen le plus élevé (5 124 FCFA), "
                            "cumulant volume ET coût élevé — signal d'une révision tarifaire urgente. "
                            "La Vie suit avec 124 sinistres (4 861 FCFA en moyenne), "
                            "l'Auto avec 114 sinistres (5 001 FCFA) "
                            "et l'Habitation avec 108 sinistres (4 824 FCFA). "
                            "Tout type concentrant à la fois un volume élevé "
                            "et un coût unitaire important exige une correction de prime immédiate."
                        ),
                    ], className="chart-container-full"),
                ], style={"padding": "20px"}),
            ]),

            # ── Onglet 3 : Tarification & Risques ────────────────────────────
            dcc.Tab(label="💰 Tarification & Risques", value="tab-3", children=[
                html.Div([
                    html.Div([
                        html.H3("📈 Coefficient Bonus / Malus par Type",
                                className="chart-title"),
                        html.P("Distribution des coefficients bonus/malus par type "
                               "pour identifier les profils à risque",
                               className="chart-subtitle"),
                        dcc.Graph(id="ass-graph-bonus-malus", className="chart"),
                        create_interpretation_box(
                            "Le coefficient moyen du portefeuille est de 1,00 : "
                            "50,9% des assurés (509) bénéficient d'un bonus (coefficient < 1,0), "
                            "47,8% (478) ont un malus (> 1,0) et 1,3% sont neutres (= 1,0). "
                            "Les segments affichant la plus forte concentration de malus "
                            "présentent une sinistralité structurelle élevée, "
                            "justifiant une tarification différenciée "
                            "et une sélection renforcée à la souscription."
                        ),
                    ], className="chart-container-full", style={"marginBottom": "30px"}),

                    html.Div([
                        html.H3("💰 Relation Prime vs Montant des Sinistres",
                                className="chart-title"),
                        html.P("Corrélation entre prime versée et montant des sinistres "
                               "pour optimiser la tarification",
                               className="chart-subtitle"),
                        dcc.Graph(id="ass-graph-scatter", className="chart"),
                        create_interpretation_box(
                            "La corrélation entre prime et sinistres est quasi nulle (-0,01), "
                            "confirmant que les primes actuelles ne reflètent pas le risque réel. "
                            "Le montant moyen des sinistres (4 956 FCFA) est près de 5 fois "
                            "supérieur à la prime moyenne (1 039 FCFA), "
                            "avec un ratio moyen sinistres/primes de 8,11. "
                            "Les points très éloignés de la diagonale — assurés très sinistres "
                            "avec prime faible — sont les profils prioritaires "
                            "pour une révision tarifaire immédiate."
                        ),
                    ], className="chart-container-full"),
                ], style={"padding": "20px"}),
            ]),

        ], style={"marginTop": "20px"}),
    ])


def create_footer():
    return html.Div([
        html.P([
            "Dashboard Assurance  •  ",
            html.Span("Visualisations interactives", className="footer-highlight"),
            "  •  1 000 assurés  •  ",
            html.A("← Accueil", href="/",
                   style={"color": "#3498db", "textDecoration": "none", "fontWeight": "600"}),
        ], className="footer-text"),
    ], className="footer")


def create_layout(app, df):
    """Layout principal — identique à la structure du Dashboard Santé."""
    if not df.empty:
        total_assures = len(df)
        prime_moy     = df["montant_prime"].mean()    if "montant_prime"     in df.columns else 0
        sin_total     = df["nb_sinistres"].sum()      if "nb_sinistres"      in df.columns else 0
        montant_sin   = df["montant_sinistres"].sum() if "montant_sinistres" in df.columns else 0
        age_moy       = df["age"].mean()              if "age"               in df.columns else 0
    else:
        total_assures = prime_moy = sin_total = montant_sin = age_moy = 0

    return html.Div([
        create_header(),
        create_kpi_strip(total_assures, prime_moy, sin_total, montant_sin, age_moy),

        html.Div([
            create_filters(),
            html.Div([create_charts_with_tabs()], className="main-content"),
        ], className="dashboard-container"),

        create_footer(),
        dcc.Store(id="ass-filtered-data"),
    ], className="app-container")