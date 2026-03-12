"""
dashboard/banking/layout.py
Layout Dashboard Bancaire — Thème clair premium, interprétations dynamiques
"""
from dash import dcc, html
import dash_bootstrap_components as dbc

# ── Coordonnées GPS banques ────────────────────────────────────────────────────
COORDS = {
    "BHS":        (14.6928, -17.4467), "BOA":      (14.6890, -17.4382),
    "BICIS":      (14.6937, -17.4441), "BNDE":     (14.7045, -17.4677),
    "BSIC":       (14.6875, -17.4421), "BIS":      (14.6910, -17.4390),
    "CBAO":       (14.6963, -17.4421), "CBI":      (14.6885, -17.4350),
    "ECOBANK":    (14.6901, -17.4441), "SGBS":     (14.6955, -17.4431),
    "UBA":        (14.6880, -17.4432), "BCIM":     (14.6915, -17.4445),
    "BDK":        (14.7040, -17.4654), "BAS":      (14.6870, -17.4399),
    "BRM":        (14.6965, -17.4505), "BGFI":     (14.6930, -17.4430),
    "LBA":        (14.6920, -17.4460), "LBO":      (14.6900, -17.4410),
    "NSIA Banque":(14.6945, -17.4415), "ORABANK":  (14.6958, -17.4455),
    "FBNBANK":    (14.6875, -17.4375), "CDS":      (14.6840, -17.4360),
    "CITIBANK":   (14.6972, -17.4469),
}

# ── Tokens couleurs (plotly – fond clair) ─────────────────────────────────────
C_BG       = "#f0f2f5"
C_PLOT_BG  = "#ffffff"
C_SURFACE  = "#ffffff"
C_CARD     = "#ffffff"
C_BORDER   = "#dee2e6"
C_ACCENT   = "#667eea"
C_INDIGO_L = "#764ba2"
C_EMERALD  = "#27ae60"
C_AMBER    = "#f39c12"
C_ROSE     = "#e74c3c"
C_SKY      = "#3498db"
C_VIOLET   = "#9b59b6"
C_TEXT     = "#2c3e50"
C_TEXT2    = "#7f8c8d"
C_TEXT3    = "#95a5a6"
C_CARD2    = "#f8f9fa"
C_BORDER2  = "#ced4da"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _chart_card(title, chart_id, height=300, subtitle=None, interp_id=None, interp_static=None):
    """
    Carte graphique style clair.
    - interp_id  : id d'un html.Div dynamique (rempli par callback)
    - interp_static : texte fixe (fallback si pas de callback)
    """
    children = [html.H3(title, className="bank-chart-title")]
    if subtitle:
        children.append(html.P(subtitle, className="bank-chart-subtitle"))
    children.append(
        dcc.Graph(
            id=chart_id,
            config={"displayModeBar": False, "responsive": True},
            style={"height": f"{height}px"},
        )
    )
    if interp_id:
        children.append(html.Div(id=interp_id, className="bank-interp"))
    elif interp_static:
        children.append(
            html.Div([
                html.Div("💡 Interprétation", className="bank-interp-label"),
                html.P(interp_static, className="bank-interp-text"),
            ], className="bank-interp")
        )
    return html.Div(children, className="bank-chart-card")


def _table_card(title, table_id, subtitle=None, interp_id=None, interp_static=None):
    children = [html.H3(title, className="bank-chart-title")]
    if subtitle:
        children.append(html.P(subtitle, className="bank-chart-subtitle"))
    children.append(html.Div(id=table_id, style={"overflowX": "auto", "minHeight": "200px"}))
    if interp_id:
        children.append(html.Div(id=interp_id, className="bank-interp"))
    elif interp_static:
        children.append(
            html.Div([
                html.Div("💡 Interprétation", className="bank-interp-label"),
                html.P(interp_static, className="bank-interp-text"),
            ], className="bank-interp")
        )
    return html.Div(children, className="bank-chart-card")


def _section_divider(title, icon="📌"):
    return html.Div(f"{icon}  {title}", className="bank-section-divider")


def _interp_block(text):
    return html.Div([
        html.Div("💡 Interprétation", className="bank-interp-label"),
        html.P(text, className="bank-interp-text"),
    ], className="bank-interp")


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
def _header():
    return html.Div([
        html.Div([
            html.H1("🏦 Positionnement des Banques au Sénégal",
                    className="bank-header-title"),
            html.P(
                "Dashboard interactif — KPIs financiers, positionnement sectoriel "
                "et comparaison des banques sénégalaises (2015–2022)",
                className="bank-header-subtitle",
            ),
            html.P(
                "📊 23 banques analysées  ·  Période : 2015 – 2022  ·  "
                "Source : BCEAO  ·  MongoDB Atlas",
                className="bank-header-stats",
            ),
            html.Div([
                html.A("🏠 Accueil",   href="/",          className="bank-nav-link"),
                html.A("🏦 Bancaire",  href="/bancaire/",  className="bank-nav-link active"),
                html.A("🛡️ Assurance", href="/assurance/", className="bank-nav-link"),
                html.A("⚡ Énergie",   href="/energie/",   className="bank-nav-link"),
                html.A("🏥 Santé",     href="/sante/",     className="bank-nav-link"),
            ], className="bank-navbar"),
        ], className="bank-header-content"),
    ], className="bank-header")


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTRES
# ─────────────────────────────────────────────────────────────────────────────
def _sidebar():
    return html.Div([
        html.Div([
            html.H3("🔍 Filtres d'Analyse", className="bank-filter-title"),

            html.Div([
                html.Label("Banque", className="bank-filter-label"),
                dcc.Dropdown(
                    id="f-banque",
                    placeholder="Toutes les banques…",
                    clearable=True,
                    className="filter-dropdown",
                ),
            ], className="bank-filter-group"),

            html.Div([
                html.Label("Année", className="bank-filter-label"),
                dcc.Dropdown(
                    id="f-annee",
                    options=[{"label": str(y), "value": y} for y in range(2015, 2023)],
                    value=2022,
                    clearable=False,
                    className="filter-dropdown",
                ),
            ], className="bank-filter-group"),

            html.Div([
                html.Label("Indicateur", className="bank-filter-label"),
                dcc.Dropdown(
                    id="f-indic",
                    options=[
                        {"label": "Bilan",         "value": "bilan"},
                        {"label": "PNB",           "value": "produit_net_bancaire"},
                        {"label": "Résultat Net",  "value": "resultat_net"},
                        {"label": "Fonds Propres", "value": "fonds_propres"},
                        {"label": "Emploi",        "value": "emploi"},
                        {"label": "Ressources",    "value": "ressources"},
                    ],
                    value="bilan",
                    clearable=False,
                    className="filter-dropdown",
                ),
            ], className="bank-filter-group"),

            html.Div([
                html.Label("Groupe Bancaire", className="bank-filter-label"),
                dcc.Dropdown(
                    id="f-groupe",
                    options=[
                        {"label": "Tous",           "value": "Tous"},
                        {"label": "Locaux",         "value": "Groupes Locaux"},
                        {"label": "Régionaux",      "value": "Groupes Règionaux"},
                        {"label": "Continentaux",   "value": "Groupes Continentaux"},
                        {"label": "Internationaux", "value": "Groupes Internationaux"},
                    ],
                    value="Tous",
                    clearable=False,
                    className="filter-dropdown",
                ),
            ], className="bank-filter-group"),

            # Résumé contextuel dynamique (rempli par callback)
            html.Div(id="sidebar-resume", style={"marginTop": "16px"}),

        ], className="bank-filters-container"),
    ], className="bank-filters-section")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 : VUE D'ENSEMBLE
# ─────────────────────────────────────────────────────────────────────────────
def _tab_overview():
    return html.Div([
        _section_divider("Indicateurs Clés du Secteur", "📊"),
        html.Div([
            html.Div(id="kpi-bilan"),
            html.Div(id="kpi-pnb"),
            html.Div(id="kpi-rn"),
            html.Div(id="kpi-fp"),
        ], className="bank-kpi-row"),

        # Interprétation dynamique des KPIs
        html.Div(id="interp-kpi-overview", className="bank-interp",
                 style={"marginBottom": "18px"}),

        _section_divider("Tendances & Classements", "📈"),
        _chart_card(
            "📅 Évolution de l'Indicateur Sélectionné",
            "g-evolution", height=360,
            subtitle="Tendance historique de l'indicateur choisi par année",
            interp_id="interp-evolution",
        ),
        _chart_card(
            "🏆 Classement des Banques",
            "g-classement", height=660,
            subtitle="Classement par ordre décroissant pour l'indicateur sélectionné",
            interp_id="interp-classement",
        ),

        _section_divider("Structure du Marché", "🥧"),
        _chart_card(
            "🥧 Parts de Marché — Bilan",
            "g-parts", height=460,
            subtitle="Répartition du bilan agrégé entre établissements",
            interp_id="interp-parts",
        ),
        _chart_card(
            "⚖️ Emploi vs Ressources",
            "g-emploi-ressources", height=380,
            subtitle="Comparaison emplois accordés et ressources collectées",
            interp_id="interp-emploi",
        ),

        _section_divider("Ratios Financiers & Radar Sectoriel", "📐"),
        _chart_card(
            "📐 Ratios Financiers Sectoriels",
            "g-ratios", height=380,
            subtitle="Solvabilité, ROA, ROE et liquidité — vue sectorielle",
            interp_id="interp-ratios-overview",
        ),
        _chart_card(
            "🕸️ Radar Financier",
            "g-radar", height=400,
            subtitle="Profil multidimensionnel de la banque sélectionnée vs secteur",
            interp_id="interp-radar",
        ),

        _section_divider("Localisation Géographique", "🗺️"),
        _chart_card(
            "🗺️ Carte Interactive — Banques à Dakar",
            "g-carte", height=420,
            subtitle="Positionnement géographique — taille des bulles proportionnelle au bilan",
            interp_id="interp-carte",
        ),
    ], style={"padding": "20px"})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 : FICHE BANQUE
# ─────────────────────────────────────────────────────────────────────────────
def _tab_fiche():
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.Div("📁 Rapport de Positionnement PDF",
                             className="bank-rapport-title"),
                    html.Div(
                        "Téléchargez un rapport complet pour la banque sélectionnée "
                        "(KPIs, ratios, évolution historique, analyse comparative).",
                        className="bank-rapport-sub",
                    ),
                ]),
            ], style={"flex": "1"}),
            html.Div([
                html.Div([
                    html.Label("Banque analysée", className="bank-filter-label"),
                    dcc.Dropdown(
                        id="f-banque-fiche",
                        placeholder="Choisir une banque…",
                        clearable=False,
                        style={"minWidth": "180px"},
                    ),
                ], className="bank-filter-group", style={"marginBottom": "0"}),
            ]),
            html.Div([
                html.Button("📄 Télécharger PDF", id="btn-rapport",
                            className="bank-btn-pdf", n_clicks=0),
                html.Button("📊 Export Excel",    id="btn-excel",
                            className="bank-btn-excel", n_clicks=0),
                dcc.Download(id="download-rapport"),
                dcc.Download(id="download-excel"),
                html.Div(id="msg-rapport",
                         style={"fontSize": "0.85rem", "marginTop": "8px", "color": "#27ae60"}),
            ]),
        ], className="bank-rapport-section",
           style={"display": "flex", "alignItems": "center",
                  "gap": "20px", "flexWrap": "wrap"}),

        # Synthèse positionnement dynamique
        html.Div(id="fiche-positionnement-resume",
                 style={"marginBottom": "16px"}),

        _section_divider("KPIs de la Banque Sélectionnée", "📊"),
        html.Div([
            html.Div(id="fiche-kpi-bilan"),
            html.Div(id="fiche-kpi-pnb"),
            html.Div(id="fiche-kpi-rn"),
            html.Div(id="fiche-kpi-fp"),
        ], className="bank-kpi-row"),

        # Interprétation dynamique KPIs fiche
        html.Div(id="interp-fiche-kpis", className="bank-interp",
                 style={"marginBottom": "18px"}),

        _section_divider("Évolution Historique", "📈"),
        html.Div([
            _chart_card(
                "📅 Historique Complet — Tous les Indicateurs",
                "fiche-evolution", height=340,
                subtitle="Évolution des principaux KPIs sur toute la période 2015–2022",
                interp_id="interp-fiche-evolution",
            ),
            _chart_card(
                "🕸️ Radar de Positionnement",
                "fiche-radar", height=340,
                subtitle="Profil multidimensionnel vs moyenne du secteur",
                interp_id="interp-fiche-radar",
            ),
        ], className="bank-row-2"),

        _section_divider("Structure Bilan & Ratios", "⚙️"),
        html.Div([
            _chart_card(
                "⚖️ Emploi vs Ressources — Historique",
                "fiche-emploi", height=300,
                subtitle="Évolution du ratio de transformation sur la période",
                interp_id="interp-fiche-emploi",
            ),
            _chart_card(
                "📐 Évolution des Ratios Financiers",
                "fiche-ratios-hist", height=300,
                subtitle="Trajectoire des ratios prudentiels sur 2015–2022",
                interp_id="interp-fiche-ratios",
            ),
        ], className="bank-row-2"),

        _section_divider("Tableau de Bord Complet", "📋"),
        _table_card(
            "📋 Données Historiques Détaillées",
            "fiche-table-container",
            subtitle="Ensemble des indicateurs annuels — valeurs en millions de FCFA",
            interp_id="interp-fiche-table",
        ),
    ], style={"padding": "20px"})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 : COMPARAISON
# ─────────────────────────────────────────────────────────────────────────────
def _tab_comparaison():
    return html.Div([
        html.Div([
            html.Div([
                html.Div("⚖️ Comparaison Interbancaire",
                         style={"fontSize": "1.05rem", "fontWeight": "700",
                                "color": "#2c3e50", "marginBottom": "4px"}),
                html.Div("Sélectionnez 2 à 5 banques pour les comparer sur tous les KPIs",
                         style={"fontSize": "0.87rem", "color": "#95a5a6"}),
            ], style={"flex": "1"}),
            html.Div([
                html.Label("Banques à comparer", className="bank-filter-label"),
                dcc.Dropdown(
                    id="f-banques-comp",
                    multi=True,
                    placeholder="Sélectionnez 2 à 5 banques…",
                    style={"minWidth": "380px"},
                ),
            ], className="bank-filter-group", style={"marginBottom": "0"}),
        ], className="bank-rapport-section"),

        # Interprétation dynamique de la comparaison
        html.Div(id="interp-comp-synthese", className="bank-interp",
                 style={"marginBottom": "18px"}),

        _section_divider("Comparaison KPIs — Année Sélectionnée", "📊"),
        html.Div([
            _chart_card("📊 Bilan Comparé",   "comp-bilan", height=280,
                        subtitle="Total du bilan pour l'année sélectionnée",
                        interp_id="interp-comp-bilan"),
            _chart_card("📊 PNB Comparé",      "comp-pnb",   height=280,
                        subtitle="Produit Net Bancaire — revenu opérationnel",
                        interp_id="interp-comp-pnb"),
        ], className="bank-row-2"),
        html.Div([
            _chart_card("📊 Résultat Net Comparé",   "comp-rn",   height=280,
                        subtitle="Bénéfice net après coût du risque et impôts",
                        interp_id="interp-comp-rn"),
            _chart_card("📊 Fonds Propres Comparés", "comp-fp",   height=280,
                        subtitle="Capital et réserves — base de solvabilité",
                        interp_id="interp-comp-fp"),
            _chart_card("📐 Solvabilité Comparée %", "comp-solv", height=280,
                        subtitle="Fonds Propres / Bilan — norme BCEAO ≥ 8%",
                        interp_id="interp-comp-solv"),
        ], className="bank-row-3"),

        _section_divider("Évolution Comparative sur la Période", "📈"),
        html.Div([
            _chart_card("📈 Évolution Bilan Comparée", "comp-evol-bilan", height=320,
                        subtitle="Croissance comparée du bilan dans le temps",
                        interp_id="interp-comp-evol-bilan"),
            _chart_card("📈 Évolution PNB Comparée",   "comp-evol-pnb",   height=320,
                        subtitle="Trajectoire comparée du revenu bancaire",
                        interp_id="interp-comp-evol-pnb"),
        ], className="bank-row-2"),

        _section_divider("Profils Financiers Comparés", "🕸️"),
        _chart_card(
            "🕸️ Radar Multi-Banques — Positionnement Comparatif",
            "comp-radar", height=400,
            subtitle="Positionnement comparatif normalisé sur 6 dimensions financières",
            interp_id="interp-comp-radar",
        ),
    ], style={"padding": "20px"})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 : RATIOS FINANCIERS
# ─────────────────────────────────────────────────────────────────────────────
def _tab_ratios():
    return html.Div([
        html.Div([
            html.Div("📐 Analyse des Ratios Financiers",
                     style={"fontSize": "1.05rem", "fontWeight": "700",
                            "color": "#2c3e50", "marginBottom": "4px"}),
            html.Div("Solvabilité · Rentabilité · Liquidité · ROA · ROE · Coefficient d'exploitation",
                     style={"fontSize": "0.9rem", "color": "#95a5a6"}),
        ], className="bank-rapport-section",
           style={"borderLeft": "5px solid #9b59b6"}),

        # Synthèse dynamique des ratios
        html.Div(id="interp-ratios-synthese", className="bank-interp",
                 style={"marginBottom": "18px"}),

        _section_divider("Ratios par Banque — Année Sélectionnée", "📊"),
        html.Div([
            _chart_card("🛡️ Solvabilité par Banque",
                        "g-ratio-solv", height=340,
                        subtitle="Fonds Propres / Bilan — Norme BCEAO ≥ 8%",
                        interp_id="interp-ratio-solv"),
            _chart_card("📊 ROA — Rendement des Actifs",
                        "g-ratio-roa", height=340,
                        subtitle="Résultat Net / Bilan — Secteur ~1-2%",
                        interp_id="interp-ratio-roa"),
        ], className="bank-row-2"),
        html.Div([
            _chart_card("💰 ROE — Rentabilité des Capitaux",
                        "g-ratio-roe", height=300,
                        subtitle="Résultat Net / Fonds Propres — Secteur ~10-15%",
                        interp_id="interp-ratio-roe"),
            _chart_card("⚙️ Coefficient d'Exploitation",
                        "g-ratio-coeff", height=300,
                        subtitle="Charges Générales / PNB — Optimal < 65%",
                        interp_id="interp-ratio-coeff"),
            _chart_card("💧 Ratio Liquidité (E/R)",
                        "g-ratio-liq", height=300,
                        subtitle="Emploi / Ressources — Prudentiel < 100%",
                        interp_id="interp-ratio-liq"),
        ], className="bank-row-3"),

        _section_divider("Carte de Chaleur des Ratios — Toutes les Banques", "🔥"),
        _chart_card(
            "🔥 Heatmap des Ratios Financiers",
            "g-ratio-heatmap", height=430,
            subtitle="Vue consolidée de tous les ratios pour l'année sélectionnée",
            interp_id="interp-heatmap",
        ),

        _section_divider("Distribution Sectorielle des Ratios", "📉"),
        html.Div([
            _chart_card("📉 Distribution Solvabilité",
                        "g-ratio-dist-solv", height=280,
                        subtitle="Densité du ratio de solvabilité dans le secteur",
                        interp_id="interp-dist-solv"),
            _chart_card("📉 Distribution ROA",
                        "g-ratio-dist-roa", height=280,
                        subtitle="Densité du rendement des actifs dans le secteur",
                        interp_id="interp-dist-roa"),
        ], className="bank-row-2"),
    ], style={"padding": "20px"})


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 : MODULE PRÉDICTIF
# ─────────────────────────────────────────────────────────────────────────────
def _tab_predictif():
    return html.Div([
        html.Div([
            html.Div([
                html.Div("🔮 Module Prédictif — Bonus",
                         style={"fontSize": "1.05rem", "fontWeight": "700",
                                "color": "#2c3e50", "marginBottom": "4px"}),
                html.Div("Estimation du positionnement futur — Régression linéaire & tendances horizon 2026",
                         style={"fontSize": "0.9rem", "color": "#95a5a6"}),
            ], style={"flex": "1"}),
            html.Div([
                html.Label("Banque à analyser", className="bank-filter-label"),
                dcc.Dropdown(
                    id="pred-banque",
                    placeholder="Choisir une banque…",
                    clearable=False,
                    style={"minWidth": "210px"},
                ),
            ], className="bank-filter-group", style={"marginBottom": "0"}),
        ], className="bank-rapport-section",
           style={"borderLeft": "5px solid #3498db"}),

        html.Div([
            "ℹ️  Note : Les projections sont basées sur des régressions linéaires des données "
            "historiques BCEAO (2015–2022). Elles sont indicatives et ne constituent pas "
            "des prévisions financières certifiées."
        ], className="bank-alert"),

        _section_divider("Projections KPIs — Horizon 2026", "📊"),
        html.Div([
            html.Div(id="pred-kpi-bilan"),
            html.Div(id="pred-kpi-pnb"),
            html.Div(id="pred-kpi-rn"),
            html.Div(id="pred-kpi-fp"),
        ], className="bank-kpi-row"),

        # Interprétation dynamique prédictif
        html.Div(id="interp-predictif", className="bank-interp",
                 style={"marginBottom": "18px"}),

        _section_divider("Trajectoires Projetées avec Intervalle de Confiance 95%", "📈"),
        html.Div([
            _chart_card("📈 Projection Bilan 2023–2026",
                        "g-pred-bilan", height=320,
                        subtitle="Trend historique + projection linéaire avec intervalle de confiance",
                        interp_id="interp-pred-bilan"),
            _chart_card("📈 Projection PNB 2023–2026",
                        "g-pred-pnb", height=320,
                        subtitle="Tendance du Produit Net Bancaire avec extrapolation",
                        interp_id="interp-pred-pnb"),
        ], className="bank-row-2"),
        html.Div([
            _chart_card("📈 Projection Fonds Propres",
                        "g-pred-fp", height=280,
                        subtitle="Évolution projetée de la solidité financière",
                        interp_static="Une projection en hausse indique une politique de rétention des bénéfices saine."),
            _chart_card("📐 Projection Ratio Solvabilité",
                        "g-pred-solv", height=280,
                        subtitle="Trajectoire prévue du ratio de capital réglementaire",
                        interp_static="Une tendance descendante vers 8% doit déclencher des actions préventives de recapitalisation."),
        ], className="bank-row-2"),

        _section_divider("Score de Positionnement Futur 2026", "⭐"),
        _chart_card(
            "⭐ Score de Positionnement Prévu — Toutes les Banques",
            "g-pred-score", height=390,
            subtitle="Indice composite normalisé sur 5 KPIs projetés",
            interp_id="interp-pred-score",
        ),
    ], style={"padding": "20px"})


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def create_banking_layout():
    return html.Div([
        dcc.Location(id="url-bancaire", refresh=False),

        _header(),

        html.Div([
            _sidebar(),
            html.Div([
                dcc.Tabs(
                    id="tabs-main",
                    value="overview",
                    children=[
                        dcc.Tab(label="📊 Vue d'ensemble",    value="overview",
                                className="bank-tab", selected_className="bank-tab--selected"),
                        dcc.Tab(label="🏦 Fiche Banque",       value="fiche",
                                className="bank-tab", selected_className="bank-tab--selected"),
                        dcc.Tab(label="⚖️ Comparaison",        value="comparaison",
                                className="bank-tab", selected_className="bank-tab--selected"),
                        dcc.Tab(label="📐 Ratios Financiers",  value="ratios",
                                className="bank-tab", selected_className="bank-tab--selected"),
                        dcc.Tab(label="🔮 Module Prédictif",   value="predictif",
                                className="bank-tab", selected_className="bank-tab--selected"),
                    ],
                    colors={"border": "transparent", "primary": "#667eea", "background": "transparent"},
                ),
                html.Div(id="tabs-content", className="bank-tab-content"),
            ], className="bank-main-content"),
        ], className="bank-container"),

        html.Div([
            html.P([
                "DataSphere Sénégal  ·  Source : ",
                html.Span("BCEAO", className="bank-footer-highlight"),
                "  ·  MongoDB Atlas  ·  M2 Big Data & IA — ISM",
            ], className="bank-footer-text"),
        ], className="bank-footer"),

    ], className="bank-app")