import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm

st.title("Mapa de Calor por Município do Brasil - Interativo")

shapefile_path = "data/municipios.shp"

try:
    municipios = gpd.read_file(shapefile_path)
    if municipios.crs is None:
        municipios.set_crs("EPSG:4326", inplace=True)
    elif municipios.crs != "EPSG:4326":
        municipios = municipios.to_crs("EPSG:4326")
    
    # Simplify geometries
    municipios['geometry'] = municipios['geometry'].simplify(0.01, preserve_topology=True)
except Exception as e:
    st.error(f"Error loading shapefile: {e}")

selected_year = st.slider("Selecione o ano", 2014, 2023, 2023)

np.random.seed(selected_year)
municipios['valor'] = np.random.uniform(0, 100, size=len(municipios))

m = folium.Map(location=[-14.2350, -51.9253], zoom_start=4)

colormap = cm.linear.OrRd_09.scale(
    municipios['valor'].min(),
    municipios['valor'].max()
)

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

colormap.add_to(m)

# Save map for debugging
m.save("map_debug.html")

# Display map
st_folium(m, width=800, height=600)

