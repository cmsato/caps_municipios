import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
from pathlib import Path
import json

st.title("Encaminhamento CAPS")

# Initialize session state for map and year
if 'map_state' not in st.session_state:
    st.session_state.map_state = {}
if 'last_year' not in st.session_state:
    st.session_state.last_year = None

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
            return None
        return pd.read_csv(file_path)
    except Exception as e:
        st.error(f"Error loading CAPS data: {str(e)}")
        return None

@st.cache_data
def load_population_data(year):
    try:
        file_path = Path(f"data/pop_{year}.csv")
        if not file_path.exists():
            return None
        df = pd.read_csv(file_path, header=None, 
                        names=['UF', 'state_code', 'city_code', 'city', 'population'])
        return df
    except Exception as e:
        st.error(f"Error loading population data: {str(e)}")
        return None

def get_closest_population_year(year):
    available_years = [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    return min(available_years, key=lambda x: abs(x - year))

def prepare_geojson(_gdf, caps_data, pop_data, selected_year):
    _gdf = _gdf.copy()
    _gdf['valor'] = 0.0
    
    _gdf['NM_MUN_NORM'] = _gdf['NM_MUN'].str.upper().str.strip()
    caps_data['Municipio_NORM'] = caps_data['Municipio'].str.upper().str.strip()
    pop_data['city_NORM'] = pop_data['city'].str.upper().str.strip()
    
    for idx, row in _gdf.iterrows():
        mun_data = caps_data[caps_data['Municipio_NORM'] == row['NM_MUN_NORM']]
        pop_mun_data = pop_data[pop_data['city_NORM'] == row['NM_MUN_NORM']]
        
        if not mun_data.empty and not pop_mun_data.empty:
            caps_value = float(mun_data[str(selected_year)].iloc[0])
            population = float(pop_mun_data['population'].iloc[0])
            if population > 0:
                _gdf.at[idx, 'valor'] = round((caps_value / population) * 100000)
    
    return json.loads(_gdf[['geometry', 'NM_MUN', 'valor']].to_json())

@st.cache_data
def load_qlb_data(state_code):
    try:
        file_path = Path(f"data/qlb_{state_code}.csv")
        if not file_path.exists():
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

data_dir = Path("data")
state_options = ["Selecione um estado"] + [f"{name} ({code})" for code, name in STATE_NAMES.items()]
selected_state_option = st.selectbox("Selecione o estado", state_options)

if selected_state_option != "Selecione um estado":
    selected_state_code = selected_state_option[-3:-1]
    
    if selected_state_code not in st.session_state.map_state:
        st.session_state.map_state[selected_state_code] = {
            'center': STATE_COORDINATES[selected_state_code],
            'zoom': 7
        }
    
    state_data = load_and_simplify_shapefile(selected_state_code)
    caps_data = load_caps_data(selected_state_code)
    qlb_data = load_qlb_data(selected_state_code)
    
    if state_data is not None and caps_data is not None:
        # Create columns for layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_year = st.slider("Selecione o ano", 2014, 2023, 2023)
        
        pop_year = get_closest_population_year(selected_year)
        pop_data = load_population_data(pop_year)
        
        if pop_data is not None:
            geojson_data = prepare_geojson(state_data, caps_data, pop_data, selected_year)
            
            values = [f['properties']['valor'] for f in geojson_data['features'] if f['properties']['valor'] > 0]
            if values:
                # Create colormap for style function
                colormap = cm.LinearColormap(
                    colors=[
                        '#fff5f5', '#ffe6e6', '#ffd6d6', '#ffc7c7', 
                        '#ffb8b8', '#ffa8a8', '#ff9999', '#ff8a8a', 
                        '#ff7b7b', '#ff6c6c', '#ff5d5d', '#ff4e4e',
                        '#ff3f3f', '#ff3030', '#ff2121', '#ff1212',
                        '#ff0303'
                    ],
                    vmin=0,
                    vmax=max(values)
                )
                
                # Create main layout columns
                map_col, colorbar_col = st.columns([5, 1])
                
                with map_col:
                    style_function = lambda x: {
                        'fillColor': colormap(x['properties']['valor']) if x['properties']['valor'] > 0 else '#ffffff',
                        'color': 'black',
                        'weight': 0.5,
                        'fillOpacity': 0.7,
                    }
                    
                    current_center = st.session_state.map_state[selected_state_code]['center']
                    current_zoom = st.session_state.map_state[selected_state_code]['zoom']
                    
                    m = folium.Map(
                        location=current_center,
                        zoom_start=current_zoom,
                        scrollWheelZoom=True,
                        tiles='cartodbpositron'
                    )
                    
                    folium.GeoJson(
                        geojson_data,
                        style_function=style_function,
                        tooltip=folium.features.GeoJsonTooltip(
                            fields=['NM_MUN', 'valor'],
                            aliases=['Município:', "Taxa por 100.000:"],
                            localize=True
                        )
                    ).add_to(m)
                    
                    if qlb_data is not None:
                        for _, row in qlb_data.iterrows():
                            folium.CircleMarker(
                                location=[row['Lat_d'], row['Long_d']],
                                radius=3,
                                color='black',
                                weight=1,
                                fill=True,
                                popup=row['NM_CQ'],
                            ).add_to(m)
                    
                    # Display the map
                    map_data = st_folium(
                        m,
                        width=700,
                        height=600,
                        key=f"{selected_state_code}_{selected_year}",
                        returned_objects=["last_active_drawing"]
                    )
                    
                    # Update state only if map was interacted with
                    if map_data["last_active_drawing"] is not None:
                        last_pos = map_data["last_active_drawing"]
                        if 'center' in last_pos:
                            st.session_state.map_state[selected_state_code] = {
                                'center': [last_pos['center']['lat'], last_pos['center']['lng']],
                                'zoom': last_pos['zoom']
                            }
                
                with colorbar_col:
                    st.markdown("""
    <div style="background-color: white; padding: 10px; border: 2px solid rgba(0,0,0,0.2); 
            border-radius: 4px; margin: 10px 0; height: 600px;">
        <div style="text-align: center; font-weight: bold; margin-bottom: 15px;">
            Taxa por 100.000 habitantes
        </div>
        <div style="text-align: center; margin-bottom: 5px;">
            <span style="font-size: 0.9em;">0</span>
        </div>
        <div style="height: 450px; margin: 10px 0; display: flex; flex-direction: column;">
            <div style="flex-grow: 1; width: 30px; margin: 0 auto; background: linear-gradient(to bottom, 
                #ffe6e6, #ffd6d6, #ffc7c7, #ffb8b8,
                #ffa8a8, #ff9999, #ff8a8a, #ff7b7b,
                #ff6c6c, #ff5d5d, #ff4e4e, #ff3f3f,
                #ff3030, #ff2121, #ff1212, #ff0303);">
            </div>
        </div>
        <div style="text-align: center; margin-top: 5px;">
            <span style="font-size: 0.9em;">{}</span>
        </div>
    </div>
""".format(int(max(values))), unsafe_allow_html=True)
st.markdown('''
<div style="text-align: center">
    Fonte de dados:<br>
    <a href="https://sisab.saude.gov.br/">Sistema de Informação em Saúde para a Atenção Básica (SISAB)</a><br>
    <a href="https://www.ibge.gov.br/">Instituto Brasileiro de Geografia e Estatística (IBGE)</a>
</div>
''', unsafe_allow_html=True)