import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
from shapely.geometry import Polygon, MultiPolygon
import pandas as pd

# Title
st.title("Mapa de Calor por Município do Brasil - Interativo")

# State center coordinates
STATE_COORDINATES = {
    'AC': [-8.77, -70.55], 'AL': [-9.71, -35.73], 'AP': [0.90, -52.00],
    'AM': [-3.47, -65.10], 'BA': [-12.96, -41.70], 'CE': [-5.20, -39.53],
    'DF': [-15.83, -47.86], 'ES': [-19.19, -40.34], 'GO': [-15.98, -49.86],
    'MA': [-5.42, -45.44], 'MT': [-12.64, -55.42], 'MS': [-20.51, -54.54],
    'MG': [-18.10, -44.38], 'PA': [-3.79, -52.48], 'PB': [-7.28, -36.72],
    'PR': [-24.89, -51.55], 'PE': [-8.38, -37.86], 'PI': [-6.60, -42.28],
    'RJ': [-22.25, -42.66], 'RN': [-5.81, -36.59], 'RS': [-30.17, -53.50],
    'RO': [-10.83, -63.34], 'RR': [2.81, -61.75], 'SC': [-27.45, -50.95],
    'SP': [-22.19, -48.79], 'SE': [-10.57, -37.45], 'TO': [-10.25, -48.25]
}

# State names dictionary
STATE_NAMES = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
    'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal',
    'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão',
    'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais',
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco',
    'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
    'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima',
    'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe',
    'TO': 'Tocantins'
}

@st.cache_data
def generate_dummy_municipalities(state_code):
    """Generate dummy municipality polygons for a given state."""
    center_lat, center_lon = STATE_COORDINATES[state_code]
    
    # Generate random number of municipalities (between 20 and 50)
    n_municipalities = np.random.randint(20, 50)
    
    municipalities = []
    # Generate unique municipality names
    municipality_names = [f"Município {i+1} - {state_code}" for i in range(n_municipalities)]
    
    for i in range(n_municipalities):
        # Generate a random point near the state center
        center_point_lat = center_lat + np.random.uniform(-1, 1)
        center_point_lon = center_lon + np.random.uniform(-1, 1)
        
        # Create a polygon (hexagon) around this point
        size = 0.1  # Size of the polygon
        angles = np.linspace(0, 360, 7)[:-1]  # 6 points for hexagon
        polygon_points = []
        
        for angle in angles:
            dx = size * np.cos(np.radians(angle))
            dy = size * np.sin(np.radians(angle))
            polygon_points.append((center_point_lon + dx, center_point_lat + dy))
        
        # Close the polygon
        polygon_points.append(polygon_points[0])
        
        municipalities.append({
            'NM_MUN': municipality_names[i],
            'UF': state_code,
            'geometry': Polygon(polygon_points)
        })
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(municipalities, crs="EPSG:4326")
    return gdf

# Create state selection dropdown
state_options = ["Selecione um estado"] + [f"{name} ({code})" for code, name in STATE_NAMES.items()]
selected_state_option = st.selectbox("Selecione o estado", state_options)

# Only proceed if a state is selected
if selected_state_option != "Selecione um estado":
    selected_state_code = selected_state_option[-3:-1]  # Extract state code from option
    
    # Generate dummy data for selected state
    state_data = generate_dummy_municipalities(selected_state_code)
    
    # Year slider
    selected_year = st.slider("Selecione o ano", 2014, 2023, 2023)
    
    # Generate random values for the selected year
    @st.cache_data
    def generate_data(data_length, seed):
        np.random.seed(seed)
        return np.random.uniform(0, 100, size=data_length)
    
    state_data['valor'] = generate_data(len(state_data), selected_year)
    
    # Create folium map centered on the selected state
    state_center = STATE_COORDINATES[selected_state_code]
    m = folium.Map(location=state_center, zoom_start=7)
    
    # Define color map
    colormap = cm.linear.OrRd_09.scale(
        state_data['valor'].min(),
        state_data['valor'].max()
    )
    
    # Add GeoJson layer with styles and tooltips
    folium.GeoJson(
        state_data,
        name="Municípios",
        style_function=lambda x: {
            'fillColor': colormap(x['properties']['valor']),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=['NM_MUN', 'valor'],
            aliases=['Município:', "Valor:"],
            localize=True,
        )
    ).add_to(m)
    
    # Add colormap to map
    colormap.add_to(m)
    
    # Display map in Streamlit
    st_folium(m, width=800, height=600)
