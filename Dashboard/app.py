import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np

# ------------------------------------------------------------------------------
# 1. Carga y preparación de datos (Usando el dataset ya procesado)
# ------------------------------------------------------------------------------
# Cargar directamente el archivo limpio y unificado de la evaluación
df = pd.read_csv('googleplaystore_procesados.csv')

# Verificaciones preventivas de tipos de datos al leer desde el CSV
df['Installs'] = pd.to_numeric(df['Installs'], errors='coerce')
df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
df['Reviews'] = pd.to_numeric(df['Reviews'], errors='coerce')

if 'Sentiment_Polarity' in df.columns:
    df['Sentiment_Polarity'] = pd.to_numeric(df['Sentiment_Polarity'], errors='coerce')
else:
    df['Sentiment_Polarity'] = 0

if 'Sentiment' in df.columns:
    df['Sentiment'] = df['Sentiment'].fillna('Neutral')
else:
    df['Sentiment'] = 'Neutral'

# Eliminar filas con datos críticos faltantes
df = df.dropna(subset=['Category', 'Rating', 'Installs'])

# Lista de categorías para el filtro
categorias = [{'label': cat, 'value': cat} for cat in df['Category'].dropna().unique()]
categorias.insert(0, {'label': 'Todas las Categorías', 'value': 'TODAS'})

# ------------------------------------------------------------------------------
# 2. Inicialización de la App con Tema de Bootstrap (Diseño 'Flatly' moderno)
# ------------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Google Play Store Analytics"

# ------------------------------------------------------------------------------
# 3. Diseño de la Interfaz (Layout)
# ------------------------------------------------------------------------------
app.layout = dbc.Container([
    # Encabezado
    dbc.Row([
        dbc.Col(html.H2("Dashboard de Desempeño - Google Play Store", className="text-center text-primary mt-4 mb-4"), width=12)
    ]),

    # Filtros
    dbc.Row([
        dbc.Col([
            html.Label("Selecciona una Categoría:", className="fw-bold"),
            dcc.Dropdown(
                id='filtro-categoria',
                options=categorias,
                value='TODAS',
                clearable=False,
                className="mb-4"
            )
        ], width=4)
    ]),

    # Fila de KPIs (Métricas Gerenciales)
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Total de Apps", className="card-title text-secondary"),
            html.H3(id="kpi-apps", className="card-text text-dark")
        ]), className="shadow-sm mb-4"), width=3),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Rating Promedio", className="card-title text-secondary"),
            html.H3(id="kpi-rating", className="card-text text-dark")
        ]), className="shadow-sm mb-4"), width=3),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Instalaciones Totales", className="card-title text-secondary"),
            html.H3(id="kpi-installs", className="card-text text-dark")
        ]), className="shadow-sm mb-4"), width=3),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Sentimiento Predominante", className="card-title text-secondary"),
            html.H3(id="kpi-sentiment", className="card-text text-dark")
        ]), className="shadow-sm mb-4"), width=3),
    ]),

    # Fila de Gráficos 1
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-installs'), className="shadow-sm mb-4"), md=6),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-sentiment'), className="shadow-sm mb-4"), md=6),
    ]),

    # Fila de Gráficos 2
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-dispersion'), className="shadow-sm mb-4"), md=12),
    ])

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

# ------------------------------------------------------------------------------
# 4. Interactividad (Callbacks)
# ------------------------------------------------------------------------------
@app.callback(
    [Output("kpi-apps", "children"),
     Output("kpi-rating", "children"),
     Output("kpi-installs", "children"),
     Output("kpi-sentiment", "children"),
     Output("grafico-installs", "figure"),
     Output("grafico-sentiment", "figure"),
     Output("grafico-dispersion", "figure")],
    [Input("filtro-categoria", "value")]
)
def actualizar_dashboard(categoria_seleccionada):
    # Filtrar datos
    if categoria_seleccionada == 'TODAS':
        dff = df.copy()
    else:
        dff = df[df['Category'] == categoria_seleccionada]
        
    # --- Cálculo de KPIs ---
    total_apps = f"{len(dff['App'].unique()):,}"
    rating_promedio = f"{dff['Rating'].mean():.2f}" if not dff['Rating'].isnull().all() else "N/A"
    total_installs = f"{dff['Installs'].sum():,.0f}" if 'Installs' in dff.columns else "N/A"
    
    if 'Sentiment' in dff.columns and not dff['Sentiment'].isnull().all():
        sentimiento = dff['Sentiment'].mode()[0]
    else:
        sentimiento = "N/A"

    # --- Gráfico 1: Top 10 Apps por Instalaciones ---
    df_top_installs = dff.groupby('App')['Installs'].max().reset_index().sort_values(by='Installs', ascending=False).head(10)
    fig_installs = px.bar(
        df_top_installs, 
        x='Installs', 
        y='App', 
        orientation='h',
        title="Top 10 Apps con Más Instalaciones",
        color='Installs',
        color_continuous_scale=px.colors.sequential.Teal
    )
    fig_installs.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=20, r=20, t=40, b=20))

    # --- Gráfico 2: Distribución de Sentimiento de Usuarios ---
    if 'Sentiment' in dff.columns and not dff['Sentiment'].empty:
        df_sent = dff['Sentiment'].value_counts().reset_index()
        df_sent.columns = ['Sentiment', 'Count']
        fig_sent = px.pie(
            df_sent, 
            names='Sentiment', 
            values='Count', 
            title="Distribución de Sentimiento de Usuarios",
            color='Sentiment',
            color_discrete_map={'Positive':'#2ecc71', 'Neutral':'#95a5a6', 'Negative':'#e74c3c'},
            hole=0.4
        )
    else:
        fig_sent = px.pie(title="Datos de sentimiento no disponibles")
    fig_sent.update_layout(margin=dict(l=20, r=20, t=40, b=20))

    # --- Gráfico 3: Rating vs Reviews vs Sentiment Polarity ---
    if 'Reviews' in dff.columns and 'Sentiment_Polarity' in dff.columns:
        dff_scatter = dff.dropna(subset=['Reviews', 'Rating', 'Sentiment_Polarity']).copy()
        dff_scatter = dff_scatter[dff_scatter['Reviews'] > 0]
        
        if len(dff_scatter) > 0:
            fig_dispersion = px.scatter(
                dff_scatter, 
                x='Reviews', 
                y='Rating', 
                color='Sentiment_Polarity',
                hover_name='App',
                title="Análisis Técnico: Rating vs Volumen de Reseñas (Color = Polaridad de Sentimiento)",
                log_x=True,
                color_continuous_scale=px.colors.diverging.RdYlGn
            )
        else:
            fig_dispersion = px.scatter(title="No hay datos válidos para el análisis de dispersión")
    else:
        fig_dispersion = px.scatter(title="Datos no disponibles para análisis de dispersión")
    fig_dispersion.update_layout(margin=dict(l=20, r=20, t=40, b=20))

    return total_apps, rating_promedio, total_installs, sentimiento, fig_installs, fig_sent, fig_dispersion

# ------------------------------------------------------------------------------
# 5. Ejecución del Dashboard localmente
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=8050)