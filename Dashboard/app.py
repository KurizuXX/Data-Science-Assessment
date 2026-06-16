import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

# ------------------------------------------------------------------------------
# 1. Carga y preparación de datos
# ------------------------------------------------------------------------------
df = pd.read_csv('googleplaystore_procesados.csv')

# Asegurar tipos numéricos para evitar errores
df['Installs'] = pd.to_numeric(df['Installs'], errors='coerce')
df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
df['Reviews'] = pd.to_numeric(df['Reviews'], errors='coerce')
df['Sentiment_Polarity'] = pd.to_numeric(df['Sentiment_Polarity'], errors='coerce').fillna(0)

# Asegurar que los sentimientos nulos sean Neutrales
df['Sentiment'] = df['Sentiment'].fillna('Neutral')

# Lista de categorías para el filtro
categorias = [{'label': cat, 'value': cat} for cat in df['Category'].dropna().unique()]
categorias.insert(0, {'label': 'Todas las Categorías', 'value': 'TODAS'})

# ------------------------------------------------------------------------------
# 2. Inicialización de la App
# ------------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Google Play Store Analytics"

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2(" Dashboard de Desempeño - Google Play Store", className="text-center text-primary mt-4 mb-4"), width=12)
    ]),

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

    # KPIs
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Total de Apps Únicas", className="card-title text-secondary"),
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
            html.H5("Sentimiento Global", className="card-title text-secondary"),
            html.H3(id="kpi-sentiment", className="card-text text-dark")
        ]), className="shadow-sm mb-4"), width=3),
    ]),

    # Gráficos 1 y 2
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-installs'), className="shadow-sm mb-4"), md=6),
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-sentiment'), className="shadow-sm mb-4"), md=6),
    ]),

    # Gráfico 3
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='grafico-dispersion'), className="shadow-sm mb-4"), md=12),
    ])

], fluid=True, style={'backgroundColor': '#f8f9fa', 'minHeight': '100vh', 'padding': '20px'})

# ------------------------------------------------------------------------------
# 3. Callbacks (Lógica de filtrado e interactividad)
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
    if categoria_seleccionada == 'TODAS':
        dff = df.copy()
    else:
        dff = df[df['Category'] == categoria_seleccionada]
        
    # --- CREAR UN DATAFRAME DE APPS ÚNICAS (Para métricas que no deben multiplicarse) ---
    df_apps_unicas = dff.drop_duplicates(subset=['App']).copy()
    
    # --- Cálculo de KPIs ---
    total_apps = f"{len(df_apps_unicas):,}"
    rating_promedio = f"{df_apps_unicas['Rating'].mean():.2f}" if not df_apps_unicas['Rating'].isnull().all() else "N/A"
    total_installs = f"{df_apps_unicas['Installs'].sum():,.0f}"
    sentimiento = dff['Sentiment'].mode()[0] if not dff['Sentiment'].empty else "N/A"

    # --- Gráfico 1: Top 10 Apps (Usando datos únicos) ---
    df_top_installs = df_apps_unicas.sort_values(by='Installs', ascending=False).head(10)
    fig_installs = px.bar(
        df_top_installs, 
        x='Installs', y='App', orientation='h',
        title="Top 10 Apps Únicas con Más Instalaciones",
        color='Installs', color_continuous_scale=px.colors.sequential.Teal
    )
    fig_installs.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=20, r=20, t=40, b=20))

    # --- Gráfico 2: Sentimiento (Usando TODO el dataset porque cada fila es una reseña) ---
    df_sent = dff['Sentiment'].value_counts().reset_index()
    df_sent.columns = ['Sentiment', 'Count']
    fig_sent = px.pie(
        df_sent, names='Sentiment', values='Count', 
        title="Distribución Total de Reseñas de Usuarios",
        color='Sentiment',
        color_discrete_map={'Positive':'#2ecc71', 'Neutral':'#95a5a6', 'Negative':'#e74c3c'},
        hole=0.4
    )
    fig_sent.update_layout(margin=dict(l=20, r=20, t=40, b=20))

    # --- Gráfico 3: Dispersión Técnico ---
    # Calculamos la polaridad promedio por cada app para graficarla
    df_scatter = dff.groupby('App').agg({
        'Reviews': 'first',
        'Rating': 'first',
        'Sentiment_Polarity': 'mean' # Promediamos los sentimientos de todas sus reseñas
    }).reset_index()
    
    df_scatter = df_scatter[df_scatter['Reviews'] > 0].dropna(subset=['Reviews', 'Rating'])
    
    fig_dispersion = px.scatter(
        df_scatter, x='Reviews', y='Rating', color='Sentiment_Polarity',
        hover_name='App',
        title="Rating vs Volumen de Reseñas (Color = Promedio de Polaridad)",
        log_x=True, color_continuous_scale=px.colors.diverging.RdYlGn
    )
    fig_dispersion.update_layout(margin=dict(l=20, r=20, t=40, b=20))

    return total_apps, rating_promedio, total_installs, sentimiento, fig_installs, fig_sent, fig_dispersion

if __name__ == '__main__':
    app.run(debug=True, port=8050)