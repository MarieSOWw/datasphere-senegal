"""
dashboard/banking/app.py
Initialisation du Dashboard Bancaire — design Premium amélioré
"""
from dash import Dash
import dash_bootstrap_components as dbc

from .layout import create_banking_layout
from . import callbacks  # important : importe les callbacks


def init_banking(server):
    dash_app = Dash(
        __name__,
        server=server,
        url_base_pathname="/bancaire/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP,
            # Polices Google Fonts Premium
            "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&"
            "family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&"
            "family=Space+Grotesk:wght@300;400;500;600;700&display=swap",
            # Font Awesome
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        ],
        suppress_callback_exceptions=True,
        title="DataSphere — Dashboard Bancaire",
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            {"name": "description",
             "content": "Dashboard Bancaire BCEAO — DataSphere Sénégal"},
        ],
    )

    dash_app.layout = create_banking_layout()
    return dash_app
