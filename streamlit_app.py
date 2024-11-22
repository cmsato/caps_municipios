import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm

# Title
st.title("Mapa de Calor por Município do Brasil - Interativo")

# Path to shapefile
shapefile_path = "data/municipios.shp"

# Load and preprocess data
@st.cache_data
def load_shapefile(path):
    municipios = gpd.read_file(path)
    
    # Ensure CRS is set to WGS84 (EPSG:4326)
    if municipios.crs is None:
        municipios.set_crs("EPSG:4326", inplace=True)
    elif municipios.crs != "EPSG:4326":
        municipios = municipios.to_crs("EPSG:4326")
    
    return municipios

try:
    municipios = load_shapefile(shapefile_path)
except Exception as e:
    st.error(f"Error loading shapefile: {e}")
    st.stop()

# Year slider
selected_year = st.slider("Selecione o ano", 2014, 2023, 2023)

# Generate random data for the selected year
@st.cache_data
def generate_data(data_length, seed):
    np.random.seed(seed)
    return np.random.uniform(0, 100, size=data_length)

municipios['valor'] = generate_data(len(municipios), selected_year)

# Create folium map
m = folium.Map(location=[-14.2350, -51.9253], zoom_start=4)

# Define color map
colormap = cm.linear.OrRd_09.scale(
    municipios['valor'].min(),
    municipios['valor'].max()
)

# Add GeoJson layer with styles and tooltips
folium.GeoJson(
    municipios,
    name="Municípios",
    style_function=lambda x: {
        'fillColor': colormap(x['properties']['valor']),
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.7,
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=['valor'],
        aliases=["Valor:"],
        localize=True,
    )
).add_to(m)

# Add colormap to map
colormap.add_to(m)

# Display map in Streamlit
st_folium(m, width=800, height=600)
