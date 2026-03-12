"""
Layout AVEC ONGLETS - Version organisée par thématique
======================================================

Cette version organise les 10 graphiques en 4 onglets :
1. Vue d'ensemble (évolution + départements)
2. Pathologies & Traitements
3. Analyse Financière
4. Profil des Patients

À utiliser si tu veux une navigation plus claire !
"""

from dash import dcc, html

def create_header():
    """En-tête du dashboard."""
    return html.Div([
        html.Div([
            html.H1(
                "🏥 Analyse de la Prise en Charge Hospitalière",
                className="header-title"
            ),
            html.P(
                "Dashboard interactif pour améliorer la qualité des soins, "
                "optimiser la durée d'hospitalisation et maîtriser les coûts",
                className="header-subtitle"
            ),
            html.P(
                "📊 500 patients analysés • Période : Déc 2024 - Déc 2025 • "
                "Durée moyenne : 8 jours • Coût moyen : 4060 €",
                className="header-stats"
            ),
        ], className="header-content"),
    ], className="header")


def create_filters():
    """Section des filtres (identique)."""
    return html.Div([
        html.Div([
            html.H3("🔍 Filtres d'Analyse", className="filter-title"),
            
            html.Div([
                html.Label("Département", className="filter-label"),
                dcc.Dropdown(
                    id='filter-departement',
                    multi=True,
                    placeholder="Tous les départements",
                    className="filter-dropdown"
                ),
            ], className="filter-group"),
            
            html.Div([
                html.Label("Pathologie", className="filter-label"),
                dcc.Dropdown(
                    id='filter-maladie',
                    multi=True,
                    placeholder="Toutes les pathologies",
                    className="filter-dropdown"
                ),
            ], className="filter-group"),
            
            html.Div([
                html.Label("Type de Traitement", className="filter-label"),
                dcc.Dropdown(
                    id='filter-traitement',
                    multi=True,
                    placeholder="Tous les traitements",
                    className="filter-dropdown"
                ),
            ], className="filter-group"),
            
            html.Div([
                html.Label("Catégorie d'Âge", className="filter-label"),
                dcc.Dropdown(
                    id='filter-age',
                    multi=True,
                    placeholder="Toutes les catégories",
                    className="filter-dropdown"
                ),
            ], className="filter-group"),
            
            html.Div([
                html.Button(
                    "🔄 Réinitialiser",
                    id='btn-reset',
                    n_clicks=0,
                    className="reset-button"
                ),
            ], className="filter-group"),
            
        ], className="filters-container"),
    ], className="filters-section")


def create_interpretation_box(text):
    """Boîte d'interprétation."""
    return html.Div([
        html.Div("💡 Interprétation", className="interpretation-label"),
        html.P(text, className="interpretation-text"),
    ], className="interpretation-box")


def create_charts_with_tabs():
    """
    Section avec ONGLETS pour une meilleure organisation.
    """
    return html.Div([
        dcc.Tabs(id="tabs-graphs", value='tab-1', children=[
            
            # ============================================================
            # ONGLET 1 : VUE D'ENSEMBLE
            # ============================================================
            dcc.Tab(label='📊 Vue d\'Ensemble', value='tab-1', children=[
                html.Div([
                    # Graphique 1
                    html.Div([
                        html.H3("📅 Évolution Mensuelle des Admissions", className="chart-title"),
                        html.P("Analyse de la tendance des hospitalisations sur 12 mois", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-evolution-temps', className="chart"),
                        create_interpretation_box(
                            "Le pic d'admissions est observé en juillet 2025 avec 49 patients, "
                            "suivi de février et août. Une baisse notable apparaît en décembre 2024 et septembre 2025. "
                            "Ces variations saisonnières suggèrent une planification des ressources à adapter selon les périodes."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 2
                    html.Div([
                        html.H3("🏥 Répartition des Patients par Département", className="chart-title"),
                        html.P("Distribution du volume de patients entre les services hospitaliers", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-departement', className="chart"),
                        create_interpretation_box(
                            "L'Oncologie est le département le plus sollicité avec 90 patients (18%), "
                            "suivi de la Gériatrie (77 patients) et l'Orthopédie (76 patients). "
                            "Cette concentration nécessite une allocation prioritaire des ressources vers ces services."
                        ),
                    ], className="chart-container-full"),
                ], style={'padding': '20px'}),
            ]),
            
            # ============================================================
            # ONGLET 2 : PATHOLOGIES & TRAITEMENTS
            # ============================================================
            dcc.Tab(label='🦠 Pathologies & Traitements', value='tab-2', children=[
                html.Div([
                    # Graphique 3
                    html.Div([
                        html.H3("🦠 Distribution des Pathologies", className="chart-title"),
                        html.P("Fréquence des différentes pathologies prises en charge", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-pathologies', className="chart"),
                        create_interpretation_box(
                            "L'Eczéma est la pathologie la plus fréquente (89 cas), suivi des Fractures (81 cas) "
                            "et du Cancer (77 cas). Bien que l'Eczéma soit fréquent, l'Alzheimer génère "
                            "les coûts les plus élevés (voir onglet Analyse Financière)."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 4
                    html.Div([
                        html.H3("💊 Répartition des Types de Traitements", className="chart-title"),
                        html.P("Approches thérapeutiques utilisées pour la prise en charge", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-traitements', className="chart"),
                        create_interpretation_box(
                            "Les Soins Spéciaux et la Physiothérapie dominent avec 89 cas chacun (17.8%), "
                            "suivis des Antibiotiques et de la Radiothérapie (87 cas). "
                            "Cette diversité thérapeutique reflète la variété des pathologies traitées."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 6
                    html.Div([
                        html.H3("⏰ Variabilité de la Durée de Séjour par Pathologie", className="chart-title"),
                        html.P("Distribution et dispersion des durées d'hospitalisation (box plot)", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-duree-pathologie', className="chart"),
                        create_interpretation_box(
                            "L'Alzheimer présente la durée moyenne la plus longue (8.4 jours), cohérent avec son coût élevé. "
                            "Les box plots révèlent une variabilité importante pour certaines pathologies, "
                            "suggérant des profils patients hétérogènes ou des protocoles de soins différents."
                        ),
                    ], className="chart-container-full"),
                ], style={'padding': '20px'}),
            ]),
            
            # ============================================================
            # ONGLET 3 : ANALYSE FINANCIÈRE
            # ============================================================
            dcc.Tab(label='💰 Analyse Financière', value='tab-3', children=[
                html.Div([
                    # Graphique 5
                    html.Div([
                        html.H3("💵 Coût Moyen de Prise en Charge par Pathologie", className="chart-title"),
                        html.P("Comparaison des coûts moyens d'hospitalisation selon la maladie", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-cout-pathologie', className="chart"),
                        create_interpretation_box(
                            "L'Alzheimer est la pathologie la plus coûteuse (4321 €), suivie de l'Infarctus (4234 €) "
                            "et des Fractures (4207 €). L'Hypertension est la moins coûteuse (3768 €). "
                            "Un écart de 553 € existe entre la pathologie la plus et la moins coûteuse."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 9
                    html.Div([
                        html.H3("🎯 Corrélation Durée d'Hospitalisation et Coût", className="chart-title"),
                        html.P("Relation entre la durée de séjour et le coût par département", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-duree-cout', className="chart"),
                        create_interpretation_box(
                            "Une corrélation très forte existe entre durée et coût (r=0.906), confirmant que "
                            "chaque jour supplémentaire augmente significativement le coût. Les points isolés (outliers) "
                            "représentent des cas complexes nécessitant une analyse approfondie pour optimiser la prise en charge."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 10
                    html.Div([
                        html.H3("📈 Coût Journalier par Catégorie d'Âge", className="chart-title"),
                        html.P("Comparaison du coût quotidien d'hospitalisation selon l'âge", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-cout-age', className="chart"),
                        create_interpretation_box(
                            "Les patients âgés de 51-65 ans présentent le coût journalier le plus élevé (514 €/jour), "
                            "suivis des 36-50 ans (508 €/jour). Malgré leur nombre élevé, les 65+ ans ont un coût/jour "
                            "légèrement inférieur (505 €/jour), suggérant des soins moins intensifs."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 11 (Heatmap)
                    html.Div([
                        html.H3("🔥 Matrice des Coûts : Département × Pathologie", className="chart-title"),
                        html.P("Cartographie des coûts moyens selon le croisement service/maladie", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-heatmap', className="chart"),
                        create_interpretation_box(
                            "Les combinaisons les plus coûteuses sont : Infarctus en Pneumologie (5216 €), "
                            "Alzheimer en Orthopédie (4895 €), et Cancer en Dermatologie (4812 €). "
                            "Cette matrice révèle des zones de concentration budgétaire nécessitant une attention particulière."
                        ),
                    ], className="chart-container-full"),
                ], style={'padding': '20px'}),
            ]),
            
            # ============================================================
            # ONGLET 4 : PROFIL DES PATIENTS
            # ============================================================
            dcc.Tab(label='👥 Profil des Patients', value='tab-4', children=[
                html.Div([
                    # Graphique 7
                    html.Div([
                        html.H3("👥 Profil Démographique des Patients", className="chart-title"),
                        html.P("Distribution des patients par catégorie d'âge et sexe", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-age-sexe', className="chart"),
                        create_interpretation_box(
                            "Les patients de 65+ ans représentent la catégorie la plus importante (137 patients, 27.4%), "
                            "suivis des 51-65 ans (106 patients). La répartition hommes/femmes est équilibrée (50.4% vs 49.6%). "
                            "Le vieillissement de la patientèle nécessite des ressources gériatriques renforcées."
                        ),
                    ], className="chart-container-full", style={'marginBottom': '30px'}),
                    
                    # Graphique 8
                    html.Div([
                        html.H3("📊 Distribution Continue des Âges", className="chart-title"),
                        html.P("Répartition détaillée de l'âge des patients hospitalisés", 
                               className="chart-subtitle"),
                        dcc.Graph(id='graph-age-distribution', className="chart"),
                        create_interpretation_box(
                            "L'âge moyen des patients est de 47.2 ans, avec une amplitude de 1 à 90 ans. "
                            "Deux pics sont observables : un premier autour de 20-40 ans et un second autour de 60-80 ans, "
                            "reflétant deux populations distinctes avec des besoins de soins différents."
                        ),
                    ], className="chart-container-full"),
                ], style={'padding': '20px'}),
            ]),
            
        ], style={'marginTop': '20px'}),
    ])


def create_footer():
    """Pied de page."""
    return html.Div([
        html.P([
            "Dashboard d'Analyse Hospitalière • ",
            html.Span("Visualisations interactives", className="footer-highlight"),
            " • Janvier 2026"
        ], className="footer-text"),
    ], className="footer")


def create_layout(app):
    """Layout complet AVEC ONGLETS."""
    return html.Div([
        create_header(),
        
        html.Div([
            create_filters(),
            
            html.Div([
                create_charts_with_tabs(),  
            ], className="main-content"),
            
        ], className="dashboard-container"),
        
        create_footer(),
        
        dcc.Store(id='filtered-data-store'),
        
    ], className="app-container")