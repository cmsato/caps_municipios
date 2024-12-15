import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
from pathlib import Path
import json

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
def load_and_simplify_shapefile(state_code, tolerance=0.001):
    """Load shapefile for a specific state and simplify geometries."""
    try:
        file_path = Path(f"data/{state_code}.shp")
        
        if not file_path.exists():
            st.error(f"Shapefile for {STATE_NAMES[state_code]} ({state_code}) not found at {file_path}")
            return None
        
        # Load the shapefile
        gdf = gpd.read_file(file_path, encoding='utf-8')
        
        # Ensure CRS is set to WGS84
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        # Simplify geometries
        gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerance, preserve_topology=True)
        
        # Add state code if not present
        if 'UF' not in gdf.columns:
            gdf['UF'] = state_code
            
        return gdf
        
    except Exception as e:
        st.error(f"Error loading shapefile for {STATE_NAMES[state_code]} ({state_code}): {str(e)}")
        return None

@st.cache_data
def prepare_geojson(_gdf, values):
    """Prepare GeoJSON with only necessary properties."""
    if 'NM_MUN' not in _gdf.columns:
        _gdf['NM_MUN'] = [f"Municipality {i+1}" for i in range(len(_gdf))]
    
    simple_gdf = _gdf[['geometry', 'NM_MUN']].copy()
    simple_gdf['valor'] = values
    
    return json.loads(simple_gdf.to_json())

# Check if data directory exists
data_dir = Path("data")
if not data_dir.exists():
    st.error("Data directory not found. Please create a 'data' directory and add state shapefiles.")
    st.stop()

# Create state selection dropdown
state_options = ["Selecione um estado"] + [f"{name} ({code})" for code, name in STATE_NAMES.items()]
selected_state_option = st.selectbox("Selecione o estado", state_options)

# Only proceed if a state is selected
if selected_state_option != "Selecione um estado":
    selected_state_code = selected_state_option[-3:-1]
    
    # Load state data with simplified geometries
    state_data = load_and_simplify_shapefile(selected_state_code)
    
    if state_data is not None:
        # Year slider
        selected_year = st.slider("Selecione o ano", 2014, 2023, 2023)
        
        # Generate random values
        @st.cache_data
        def generate_data(data_length, seed):
            np.random.seed(seed)
            return np.random.uniform(0, 100, size=data_length)
        
        values = generate_data(len(state_data), selected_year)
        
        # Prepare optimized GeoJSON
        geojson_data = prepare_geojson(state_data, values)
        
        # Create folium map
        state_center = STATE_COORDINATES[selected_state_code]
        m = folium.Map(location=state_center, zoom_start=7)
        
        # Define color map
        colormap = cm.linear.OrRd_09.scale(
            min(values),
            max(values)
        )
        
        # Add GeoJson layer with reduced data
        folium.GeoJson(
            geojson_data,
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
        
        # Display map
        st_folium(m, width=800, height=600)