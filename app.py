import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone, timedelta

# Configuração do Fuso Horário de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Configuração da página
st.set_page_config(
    page_title="Sistema de Ponto",
    page_icon="📍",
    layout="wide"
)

# Nomes dos arquivos JSON locais para persistência
ARQUIVO_COLABORADORES = "colaboradores.json"
ARQUIVO_REGISTROS = "registros_ponto.json"

# Funções para carregar e salvar dados em JSON
def carregar_dados_json():
    if os.path.exists(ARQUIVO_COLABORADORES):
        with open(ARQUIVO_COLABORADORES, "r", encoding="utf-8") as f:
            colaboradores = json.load(f)
    else:
        colaboradores = ["Eu Mesmo (Administrador)"]

    if os.path.exists(ARQUIVO_REGISTROS):
        with open(ARQUIVO_REGISTROS, "r", encoding="utf-8") as f:
            registros = json.load(f)
        df_registros = pd.DataFrame(registros)
    else:
        df_registros = pd.DataFrame(columns=["Colaborador", "Tipo", "Data/Hora", "Latitude", "Longitude"])

    return colaboradores, df_registros

def salvar_colaboradores(colaboradores):
    with open(ARQUIVO_COLABORADORES, "w", encoding="utf-8") as f:
        json.dump(colaboradores, f, ensure_ascii=False, indent=4)

def salvar_registros(df_registros):
    df_registros.to_dict(orient="records")
    with open(ARQUIVO_REGISTROS, "w", encoding="utf-8") as f:
        json.dump(df_registros.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

# Carrega os dados salvos
lista_colab, df_reg = carregar_dados_json()

# Menu principal (O padrão agora inicia na aba de Bater Ponto)
st.sidebar.image("https://img.icons8.com/color/96/map-pin.png", width=80)
st.sidebar.title("Sistema de Ponto")
menu = st.sidebar.selectbox(
    "Navegação", 
    ["1. Bater Ponto (Celular)", "2. Cadastrar Funcionários", "3. Dashboard Gerencial (RH)"]
)

if menu == "1. Bater Ponto (Celular)":
    st.title("📱 Registro de Ponto com Geolocalização")
    st.markdown("O sistema captura sua posição atual via GPS de onde você estiver no **Horário do Brasil**.")

    if not lista_colab:
        st.warning("Nenhum colaborador cadastrado. Vá na aba 'Cadastrar Funcionários' primeiro.")
    else:
        colaborador_atual = st.selectbox("Selecione seu Nome:", lista_colab)
        tipo_batida = st.selectbox("Tipo de Registro", ["Entrada", "Saída Almoço", "Retorno Almoço", "Saída"])

        st.info("👇 Permita o acesso à localização no navegador para registrar o ponto.")

        # HTML/JS para capturar a geolocalização do navegador
        geo_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                #map { height: 280px; width: 100%; border-radius: 8px; margin-top: 10px; }
                .info-box { background: #f8f9fa; padding: 10px; border-radius: 6px; border: 1px solid #dee2e6; font-family: sans-serif; }
            </style>
        </head>
        <body>
            <div class="info-box">
                <p id="status" style="margin:0; font-weight: bold; color: #0066cc;">Obtendo sua localização via GPS...</p>
            </div>
            <div id="map"></div>

            <script>
                var map = L.map('map').setView([-15.788497, -47.879873], 4);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap'
                }).addTo(map);

                var marker;

                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(function(position) {
                        var userLat = position.coords.latitude;
                        var userLon = position.coords.longitude;

                        map.setView([userLat, userLon], 16);
                        
                        if (marker) { map.removeLayer(marker); }
                        marker = L.marker([userLat, userLon]).addTo(map)
                            .bindPopup("<b>Você está aqui</b>").openPopup();

                        document.getElementById("status").innerHTML = "✅ Localização obtida! Lat: " + userLat.toFixed(5) + " | Lon: " + userLon.toFixed(5);
                        document.getElementById("status").style.color = "green";

                    }, function(error) {
                        document.getElementById("status").innerHTML = "⚠️ Ative o GPS no seu celular para registrar a localização.";
                        document.getElementById("status").style.color = "orange";
                    }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 });
                } else {
                    document.getElementById("status").innerHTML = "Seu navegador não suporta geolocalização.";
                }
            </script>
        </body>
        </html>
        """
        
        st.components.v1.html(geo_html, height=350)

        st.divider()

        # Coordenadas automáticas ou manuais para teste
        lat_input = st.number_input("Latitude Capturada", value=-23.55052, format="%.5f")
        lon_input = st.number_input("Longitude Capturada", value=-46.63331, format="%.5f")

        if st.button("🟢 Confirmar e Bater Ponto", type="primary"):
            # Pega a data e hora atual baseada no fuso de Brasília (UTC-3)
            agora = datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M:%S")
            
            novo_registro = pd.DataFrame([{
                "Colaborador": colaborador_atual,
                "Tipo": tipo_batida,
                "Data/Hora": agora,
                "Latitude": lat_input,
                "Longitude": lon_input
            }])
            
            df_reg = pd.concat([df_reg, novo_registro], ignore_index=True)
            salvar_registros(df_reg)
            
            st.success(f"Ponto de **{tipo_batida}** registrado com sucesso para **{colaborador_atual}** às **{agora}**!")
            st.balloons()

elif menu == "2. Cadastrar Funcionários":
    st.title("👤 Cadastro de Colaboradores")
    st.markdown("Cadastre novos colaboradores. Os dados são salvos localmente em JSON.")

    novo_nome = st.text_input("Nome Completo do Funcionário:")
    if st.button("Adicionar Colaborador", type="primary"):
        if novo_nome and novo_nome not in lista_colab:
            lista_colab.append(novo_nome)
            salvar_colaboradores(lista_colab)
            st.success(f"Colaborador **{novo_nome}** cadastrado com sucesso!")
            st.rerun()
        elif novo_nome in lista_colab:
            st.warning("Este colaborador já está cadastrado.")
        else:
            st.error("Digite um nome válido.")

    st.divider()
    st.subheader("📋 Colaboradores Ativos no Sistema")
    st.write(lista_colab)

elif menu == "3. Dashboard Gerencial (RH)":
    st.title("📊 Painel de Controle - Registros e Mapas")
    st.markdown("Acompanhe o histórico de marcações salvas no arquivo JSON e os locais das batidas.")

    if df_reg.empty:
        st.info("Nenhum ponto registrado ainda. Vá na aba de bater ponto para fazer o primeiro registro!")
    else:
        st.subheader("📋 Histórico de Marcações")
        st.dataframe(df_reg, use_container_width=True)

        st.subheader("🗺️ Mapa dos Locais de Batida de Ponto")
        df_mapa = df_reg.rename(columns={"Latitude": "lat", "Longitude": "lon"})
        st.map(df_mapa)
