import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Meu Sistema de Ponto",
    page_icon="📍",
    layout="wide"
)

# Inicialização do Session State para persistir dados enquanto o app estiver aberto
if "colaboradores" not in st.session_state:
    st.session_state.colaboradores = ["Eu Mesmo (Administrador)"]

if "registros_ponto" not in st.session_state:
    st.session_state.registros_ponto = pd.DataFrame(columns=[
        "Colaborador", "Tipo", "Data/Hora", "Latitude", "Longitude"
    ])

# Barra lateral de navegação
st.sidebar.image("https://img.icons8.com/color/96/map-pin.png", width=80)
st.sidebar.title("Sistema de Ponto Pessoal")
menu = st.sidebar.selectbox("Menu Principal", ["1. Cadastrar Funcionários", "2. Bater Ponto (Celular)", "3. Dashboard Gerencial (RH)"])

if menu == "1. Cadastrar Funcionários":
    st.title("👤 Cadastro de Colaboradores")
    st.markdown("Cadastre o seu nome ou de quem vai utilizar o sistema de ponto.")

    novo_nome = st.text_input("Nome Completo do Funcionário:")
    if st.button("Adicionar Colaborador", type="primary"):
        if novo_nome and novo_nome not in st.session_state.colaboradores:
            st.session_state.colaboradores.append(novo_nome)
            st.success(f"Colaborador **{novo_nome}** cadastrado com sucesso!")
        elif novo_nome in st.session_state.colaboradores:
            st.warning("Este colaborador já está cadastrado.")
        else:
            st.error("Digite um nome válido.")

    st.divider()
    st.subheader("📋 Colaboradores Ativos no Sistema")
    st.write(st.session_state.colaboradores)

elif menu == "2. Bater Ponto (Celular)":
    st.title("📱 Registro de Ponto com Geolocalização")
    st.markdown("O sistema captura sua posição atual via GPS de onde você estiver.")

    if not st.session_state.colaboradores:
        st.warning("Nenhum colaborador cadastrado. Vá na aba 'Cadastrar Funcionários' primeiro.")
    else:
        colaborador_atual = st.selectbox("Selecione seu Nome:", st.session_state.colaboradores)
        tipo_batida = st.selectbox("Tipo de Registro", ["Entrada", "Saída Almoço", "Retorno Almoço", "Saída"])

        st.info("👇 Permita o acesso à localização no navegador para exibir seu mapa e liberar o registro.")

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

        # Coordenadas automáticas ou manuais para teste de fallback
        lat_input = st.number_input("Latitude Capturada", value=-23.55052, format="%.5f")
        lon_input = st.number_input("Longitude Capturada", value=-46.63331, format="%.5f")

        if st.button("🟢 Confirmar e Bater Ponto", type="primary"):
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            novo_registro = pd.DataFrame([{
                "Colaborador": colaborador_atual,
                "Tipo": tipo_batida,
                "Data/Hora": agora,
                "Latitude": lat_input,
                "Longitude": lon_input
            }])
            
            st.session_state.registros_ponto = pd.concat([st.session_state.registros_ponto, novo_registro], ignore_index=True)
            st.success(f"Ponto de **{tipo_batida}** registrado com sucesso para **{colaborador_atual}** às **{agora}**!")
            st.balloons()

elif menu == "3. Dashboard Gerencial (RH)":
    st.title("📊 Painel de Controle - Registros e Mapas")
    st.markdown("Acompanhe o seu histórico de marcações e os locais de onde o ponto foi batido.")

    df_reg = st.session_state.registros_ponto

    if df_reg.empty:
        st.info("Nenhum ponto registrado ainda. Cadastre-se na aba 1 e bata seu ponto na aba 2!")
    else:
        st.subheader("📋 Histórico de Marcações")
        st.dataframe(df_reg, use_container_width=True)

        st.subheader("🗺️ Mapa dos Locais de Batida de Ponto")
        df_mapa = df_reg.rename(columns={"Latitude": "lat", "Longitude": "lon"})
        st.map(df_mapa)
