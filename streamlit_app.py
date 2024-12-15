import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
from pathlib import Path
import json
import pandas as pd

st.title("Mapa de Calor por Município do Brasil - Interativo")

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
def load_caps_data(state_code):
    try:
        file_path = Path(f"data/caps_{state_code}.csv")
        if not file_path.exists():
            st.error(f"CAPS data file for {STATE_NAMES[state_code]} not found")
            return None
        df = pd.read_csv(file_path)
        return df[df['UF'] == state_code]
    except Exception as e:
        st.error(f"Error loading CAPS data: {str(e)}")
        return None

@st.cache_data
def load_qlb_data(state_code):
    try:
        file_path = Path(f"data/qlb_{state_code}.csv")
        if not file_path.exists():
            st.error(f"QLB data file for {STATE_NAMES[state_code]} not found")
            return None
        df = pd.read_csv(file_path, sep=';')
        return df[['NM_CQ', 'Lat_d', 'Long_d']].drop_duplicates()
    except Exception as e:
        st.error(f"Error loading QLB data: {str(e)}")
        return None

@st.cache_data
def load_and_simplify_shapefile(state_code, tolerance=0.001):
    try:
        file_path = Path(f"data/{state_code}.shp")
        
        if not file_path.exists():
            st.error(f"Shapefile for {STATE_NAMES[state_code]} ({state_code}) not found at {file_path}")
            return None
        
        gdf = gpd.read_file(file_path, encoding='utf-8')
        
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerance, preserve_topology=True)
        
        if 'UF' not in gdf.columns:
            gdf['UF'] = state_code
            
        return gdf
        
    except Exception as e:
        st.error(f"Error loading shapefile for {STATE_NAMES[state_code]} ({state_code}): {str(e)}")
        return None

def prepare_geojson(_gdf, caps_data):
    if 'NM_MUN' not in _gdf.columns:
        _gdf['NM_MUN'] = [f"Municipality {i+1}" for i in range(len(_gdf))]
    
    simple_gdf = _gdf[['geometry', 'NM_MUN']].copy()
    
    # Merge with CAPS data
    values = []
    for mun in simple_gdf['NM_MUN']:
        value = caps_data[caps_data['Municipio'] == mun][str(selected_year)].values
        values.append(value[0] if len(value) > 0 else 0)
    
    simple_gdf['valor'] = values
    return json.loads(simple_gdf.to_json())


if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 7
if 'map_center' not in st.session_state:
    st.session_state.map_center = None

data_dir = Path("data")
if not data_dir.exists():
    st.error("Data directory not found. Please create a 'data' directory and add required files.")
    st.stop()

state_options = ["Selecione um estado"] + [f"{name} ({code})" for code, name in STATE_NAMES.items()]
selected_state_option = st.selectbox("Selecione o estado", state_options)

if selected_state_option != "Selecione um estado":
    selected_state_code = selected_state_option[-3:-1]
    
    state_data = load_and_simplify_shapefile(selected_state_code)
    caps_data = load_caps_data(selected_state_code)
    qlb_data = load_qlb_data(selected_state_code)
    
    if state_data is not None and caps_data is not None:
        selected_year = st.slider("Selecione o ano", 2014, 2023, 2023)
        
        geojson_data = prepare_geojson(state_data, caps_data)
        
        state_center = STATE_COORDINATES[selected_state_code]
        m = folium.Map(
            location=st.session_state.map_center or state_center,
            zoom_start=st.session_state.map_zoom
        )
        
        values = [f['properties']['valor'] for f in geojson_data['features']]
        colormap = cm.linear.OrRd_09.scale(
            min(values),
            max(values)
        )
        
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
        
        if qlb_data is not None:
            for _, row in qlb_data.iterrows():
                folium.CircleMarker(
                    location=[row['Lat_d'], row['Long_d']],
                    radius=5,
                    color='black',
                    fill=True,
                    popup=row['NM_CQ'],
                ).add_to(m)
        
        colormap.add_to(m)
        
        map_data = st_folium(m, width=800, height=600)

        if map_data.get('last_active_drawing'):
            last_pos = map_data['last_active_drawing']
            if 'center' in last_pos:
                st.session_state.map_center = [last_pos['center']['lat'], last_pos['center']['lng']]
            if 'zoom' in last_pos:
                st.session_state.map_zoom = last_pos['zoom']