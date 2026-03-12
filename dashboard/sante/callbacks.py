"""
Callbacks de l'application Dash
================================

Gestion de l'interactivité : filtrage des données et mise à jour
des visualisations en temps réel.

Auteur: Data Analyst
Date: Janvier 2026
"""

from dash import Input, Output, callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from io import StringIO  # ← FIX: nécessaire pour pd.read_json sur Python 3.14+


def register_callbacks(app, df):
    """
    Enregistre tous les callbacks de l'application.
    
    Args:
        app: Instance Dash
        df: DataFrame des données hospitalières
    """
    
    # ========================================================================
    # CALLBACK 1: Initialisation des options des filtres
    # ========================================================================
    @app.callback(
        [Output('filter-departement', 'options'),
         Output('filter-maladie', 'options'),
         Output('filter-traitement', 'options'),
         Output('filter-age', 'options')],
        Input('filter-departement', 'id')
    )
    def init_filter_options(_):
        """Initialise les options des dropdowns."""
        dept_options = [{'label': d, 'value': d} for d in sorted(df['Departement'].unique())]
        maladie_options = [{'label': m, 'value': m} for m in sorted(df['Maladie'].unique())]
        traitement_options = [{'label': t, 'value': t} for t in sorted(df['Traitement'].unique())]
        age_options = [{'label': c, 'value': c} for c in ['0-18 ans', '19-35 ans', '36-50 ans', '51-65 ans', '65+ ans']]
        
        return dept_options, maladie_options, traitement_options, age_options
    
    
    # ========================================================================
    # CALLBACK 2: Réinitialisation des filtres
    # ========================================================================
    @app.callback(
        [Output('filter-departement', 'value'),
         Output('filter-maladie', 'value'),
         Output('filter-traitement', 'value'),
         Output('filter-age', 'value')],
        Input('btn-reset', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_filters(n_clicks):
        """Réinitialise tous les filtres."""
        return None, None, None, None
    
    
    # ========================================================================
    # CALLBACK 3: Filtrage des données
    # ========================================================================
    @app.callback(
        Output('filtered-data-store', 'data'),
        [Input('filter-departement', 'value'),
         Input('filter-maladie', 'value'),
         Input('filter-traitement', 'value'),
         Input('filter-age', 'value')]
    )
    def filter_data(dept_filter, maladie_filter, traitement_filter, age_filter):
        """
        Filtre les données selon les critères sélectionnés.
        """
        filtered_df = df.copy()
        
        if dept_filter:
            filtered_df = filtered_df[filtered_df['Departement'].isin(dept_filter)]
        
        if maladie_filter:
            filtered_df = filtered_df[filtered_df['Maladie'].isin(maladie_filter)]
        
        if traitement_filter:
            filtered_df = filtered_df[filtered_df['Traitement'].isin(traitement_filter)]
        
        if age_filter:
            filtered_df = filtered_df[filtered_df['CategorieAge'].isin(age_filter)]
        
        return filtered_df.to_json(date_format='iso', orient='split')
    
    
    # ========================================================================
    # CALLBACK 4: Graphique évolution temporelle
    # ========================================================================
    @app.callback(
        Output('graph-evolution-temps', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_evolution_graph(filtered_data_json):
        """
        Évolution mensuelle des admissions.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        monthly_data = filtered_df.groupby('Mois').agg({
            'PatientID': 'count',
            'Cout': 'sum',
            'DureeSejour': 'mean'
        }).reset_index()
        
        monthly_data.columns = ['Mois', 'NbPatients', 'CoutTotal', 'DureeMoyenne']
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_data['Mois'],
            y=monthly_data['NbPatients'],
            mode='lines+markers',
            name='Nombre de patients',
            line=dict(color='#3498db', width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{x}</b><br>Patients: %{y}<extra></extra>'
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            hovermode='x unified',
            xaxis=dict(
                title='Mois',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
            ),
            yaxis=dict(
                title='Nombre de patients',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            margin=dict(l=60, r=30, t=30, b=80),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 5: Graphique répartition départements
    # ========================================================================
    @app.callback(
        Output('graph-departement', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_departement_graph(filtered_data_json):
        """
        Répartition des patients par département (pie chart).
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        dept_counts = filtered_df['Departement'].value_counts()
        
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', 
                 '#1abc9c', '#34495e', '#16a085', '#27ae60', '#d35400']
        
        fig = go.Figure(data=[go.Pie(
            labels=dept_counts.index,
            values=dept_counts.values,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>Patients: %{value}<br>Pourcentage: %{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 6: Graphique distribution pathologies
    # ========================================================================
    @app.callback(
        Output('graph-pathologies', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_pathologies_graph(filtered_data_json):
        """
        Distribution des pathologies (bar chart horizontal).
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        pathologie_counts = filtered_df['Maladie'].value_counts().sort_values()
        
        fig = go.Figure(data=[go.Bar(
            x=pathologie_counts.values,
            y=pathologie_counts.index,
            orientation='h',
            marker=dict(
                color=pathologie_counts.values,
                colorscale='Blues',
                showscale=False
            ),
            hovertemplate='<b>%{y}</b><br>Patients: %{x}<extra></extra>'
        )])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            xaxis=dict(
                title='Nombre de patients',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(title=''),
            margin=dict(l=120, r=30, t=30, b=60),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 7: Graphique types de traitements
    # ========================================================================
    @app.callback(
        Output('graph-traitements', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_traitements_graph(filtered_data_json):
        """
        Répartition des types de traitements (pie chart).
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        traitement_counts = filtered_df['Traitement'].value_counts()
        
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
        
        fig = go.Figure(data=[go.Pie(
            labels=traitement_counts.index,
            values=traitement_counts.values,
            marker=dict(colors=colors),
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Patients: %{value}<extra></extra>'
        )])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=11, color='#2c3e50'),
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.02
            ),
            margin=dict(l=20, r=150, t=30, b=20),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 8: Graphique coût par pathologie
    # ========================================================================
    @app.callback(
        Output('graph-cout-pathologie', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_cout_pathologie_graph(filtered_data_json):
        """
        Coût moyen par pathologie.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        cout_moyen = filtered_df.groupby('Maladie')['Cout'].mean().sort_values()
        
        fig = go.Figure(data=[go.Bar(
            x=cout_moyen.values,
            y=cout_moyen.index,
            orientation='h',
            marker=dict(
                color=cout_moyen.values,
                colorscale='Oranges',
                showscale=False
            ),
            hovertemplate='<b>%{y}</b><br>Coût moyen: %{x:,.0f} €<extra></extra>'
        )])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            xaxis=dict(
                title='Coût moyen (€)',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(title=''),
            margin=dict(l=120, r=30, t=30, b=60),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 9: Graphique durée par pathologie (box plot)
    # ========================================================================
    @app.callback(
        Output('graph-duree-pathologie', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_duree_pathologie_graph(filtered_data_json):
        """
        Box plot des durées de séjour par pathologie.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        medians = filtered_df.groupby('Maladie')['DureeSejour'].median().sort_values()
        
        fig = go.Figure()
        
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', 
                 '#9b59b6', '#1abc9c', '#34495e', '#16a085']
        
        for i, maladie in enumerate(medians.index):
            data = filtered_df[filtered_df['Maladie'] == maladie]['DureeSejour']
            fig.add_trace(go.Box(
                y=data,
                name=maladie,
                marker_color=colors[i % len(colors)],
                boxmean='sd',
                hovertemplate='<b>%{x}</b><br>Durée: %{y} jours<extra></extra>'
            ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            showlegend=False,
            yaxis=dict(
                title='Durée de séjour (jours)',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            xaxis=dict(title=''),
            margin=dict(l=60, r=30, t=30, b=100),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 10: Graphique âge-sexe
    # ========================================================================
    @app.callback(
        Output('graph-age-sexe', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_age_sexe_graph(filtered_data_json):
        """
        Distribution par âge et sexe (barres groupées).
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        age_sexe = filtered_df.groupby(['CategorieAge', 'Sexe']).size().reset_index(name='Count')
        
        fig = go.Figure()
        
        for sexe, color in [('M', '#3498db'), ('F', '#e74c3c')]:
            data = age_sexe[age_sexe['Sexe'] == sexe]
            fig.add_trace(go.Bar(
                x=data['CategorieAge'],
                y=data['Count'],
                name='Homme' if sexe == 'M' else 'Femme',
                marker_color=color,
                hovertemplate='<b>%{x}</b><br>%{fullData.name}: %{y}<extra></extra>'
            ))
        
        fig.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            xaxis=dict(
                title='Catégorie d\'âge',
                showgrid=False
            ),
            yaxis=dict(
                title='Nombre de patients',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            margin=dict(l=60, r=30, t=60, b=60),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 11: Histogramme des âges
    # ========================================================================
    @app.callback(
        Output('graph-age-distribution', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_age_distribution_graph(filtered_data_json):
        """
        Histogramme de la distribution des âges.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        fig = go.Figure(data=[go.Histogram(
            x=filtered_df['Age'],
            nbinsx=20,
            marker=dict(
                color='#9b59b6',
                line=dict(color='white', width=1)
            ),
            hovertemplate='Âge: %{x}<br>Patients: %{y}<extra></extra>'
        )])
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            xaxis=dict(
                title='Âge (années)',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title='Nombre de patients',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            margin=dict(l=60, r=30, t=30, b=60),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 12: Scatter durée-coût
    # ========================================================================
    @app.callback(
        Output('graph-duree-cout', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_duree_cout_graph(filtered_data_json):
        """
        Scatter plot durée vs coût par département.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        fig = px.scatter(
            filtered_df,
            x='DureeSejour',
            y='Cout',
            color='Departement',
            size='Age',
            hover_data=['Maladie', 'Traitement', 'Sexe'],
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            xaxis=dict(
                title='Durée de séjour (jours)',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title='Coût (€)',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            legend=dict(
                title='Département',
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            ),
            margin=dict(l=60, r=180, t=30, b=60),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 13: Coût par jour selon l'âge
    # ========================================================================
    @app.callback(
        Output('graph-cout-age', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_cout_age_graph(filtered_data_json):
        """
        Box plot du coût par jour selon la catégorie d'âge.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        fig = go.Figure()
        
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']
        categories = ['0-18 ans', '19-35 ans', '36-50 ans', '51-65 ans', '65+ ans']
        
        for i, cat in enumerate(categories):
            data = filtered_df[filtered_df['CategorieAge'] == cat]['CoutParJour']
            if len(data) > 0:
                fig.add_trace(go.Box(
                    y=data,
                    name=cat,
                    marker_color=colors[i],
                    boxmean='sd',
                    hovertemplate='<b>%{x}</b><br>Coût/jour: %{y:,.0f} €<extra></extra>'
                ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color='#2c3e50'),
            showlegend=False,
            yaxis=dict(
                title='Coût par jour (€)',
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            xaxis=dict(title='Catégorie d\'âge'),
            margin=dict(l=60, r=30, t=30, b=80),
            height=350
        )
        
        return fig
    
    
    # ========================================================================
    # CALLBACK 14: Heatmap coût par département et pathologie
    # ========================================================================
    @app.callback(
        Output('graph-heatmap', 'figure'),
        Input('filtered-data-store', 'data')
    )
    def update_heatmap(filtered_data_json):
        """
        Heatmap du coût moyen croisé département × pathologie.
        """
        filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')  # ← FIX
        
        pivot_cout = filtered_df.pivot_table(
            values='Cout',
            index='Maladie',
            columns='Departement',
            aggfunc='mean'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_cout.values,
            x=pivot_cout.columns,
            y=pivot_cout.index,
            colorscale='RdYlGn_r',
            text=np.round(pivot_cout.values, 0),
            texttemplate='%{text:.0f}€',
            textfont={"size": 10},
            hovertemplate='<b>%{y}</b><br>%{x}<br>Coût moyen: %{z:,.0f} €<extra></extra>',
            colorbar=dict(title='Coût (€)')
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=11, color='#2c3e50'),
            xaxis=dict(title='Département', side='bottom'),
            yaxis=dict(title='Pathologie'),
            margin=dict(l=120, r=120, t=30, b=100),
            height=450
        )
        
        return fig