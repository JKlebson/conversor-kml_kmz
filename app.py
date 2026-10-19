import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import xml.etree.ElementTree as ET
import zipfile
import re
import os
import tempfile

st.set_page_config(page_title="Conversor KML para DBF", page_icon="🌍")

st.title("Conversor de KML/KMZ para DBF 🌍")
st.write("Anexe o seu arquivo de mapeamento abaixo para extrair a tabela de coordenadas no formato DBF isolado.")

# Campo de arrastar e soltar do site
arquivo_upload = st.file_uploader("Selecione ou arraste o arquivo KML/KMZ", type=["kml", "kmz"])

if arquivo_upload is not None:
    st.success(f"Arquivo recebido! Processando...")
    
    try:
        # Extração do KML/KMZ em memória
        if arquivo_upload.name.lower().endswith('.kmz'):
            with zipfile.ZipFile(arquivo_upload, 'r') as kmz:
                kml_interno = [f for f in kmz.namelist() if f.lower().endswith('.kml')][0]
                with kmz.open(kml_interno, 'r') as file:
                    tree = ET.parse(file)
        else:
            tree = ET.parse(arquivo_upload)
        
        root = tree.getroot()
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        dados = []
        for placemark in root.findall('.//kml:Placemark', ns) or root.findall('.//{*}Placemark'):
            name_elem = placemark.find('.//kml:name', ns) or placemark.find('.//{*}name')
            nome = name_elem.text if name_elem is not None else ""
            
            point = placemark.find('.//kml:Point', ns) or placemark.find('.//{*}Point')
            if point is not None:
                coord_elem = point.find('.//kml:coordinates', ns) or point.find('.//{*}coordinates')
                if coord_elem is not None:
                    coords = coord_elem.text.strip().split(',')
                    if len(coords) >= 2:
                        lon, lat = coords[0], coords[1]
                        dados.append({'Name': nome, 'LONGITUDE': lon, 'LATITUDE': lat})
        
        df = pd.DataFrame(dados)
        
        def extrair_numero(texto):
            match = re.match(r'^(\d+)', str(texto).strip())
            return str(int(match.group(1))) if match else "0"
            
        df['NUM'] = df['Name'].apply(extrair_numero)
        df_final = df[['NUM', 'LATITUDE', 'LONGITUDE']].copy()
        
        gdf = gpd.GeoDataFrame(df_final, geometry=[Point(0,0)] * len(df_final), crs="EPSG:4326")
        
        # Cria um diretório temporário na nuvem para processar o Shapefile e isolar o DBF
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_shp = os.path.join(tmpdir, "temp_saida.shp")
            caminho_dbf = os.path.join(tmpdir, "temp_saida.dbf")
            
            gdf.to_file(caminho_shp)
            
            # Lê o DBF gerado para a memória para entregar no download
            with open(caminho_dbf, "rb") as f:
                dbf_bytes = f.read()
                
        # Define o nome do arquivo de saída
        nome_original = re.sub(r'(?i)\.km[lz]$', '', arquivo_upload.name)
        nome_saida = f"{nome_original}_formatado.dbf"
        
        st.write("---")
        st.write("**Conversão concluída!**")
        
        # Botão de Download do site
        st.download_button(
            label="⬇️ Baixar Arquivo DBF",
            data=dbf_bytes,
            file_name=nome_saida,
            mime="application/octet-stream"
        )
        
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")