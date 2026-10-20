import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timezone, timedelta
from fpdf import FPDF

# Configuração do Fuso Horário de Brasília (UTC-3)
FUSO_BRASILIA = timezone(timedelta(hours=-3))

# Configuração da página
st.set_page_config(
    page_title="Sistema de Ponto 4 Batidas",
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
    with open(ARQUIVO_REGISTROS, "w", encoding="utf-8") as f:
        json.dump(df_registros.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

# Função para gerar o PDF em MODO PAISAGEM (Horizontal) organizado por data
def gerar_pdf_paisagem(df):
    # orientation='L' (Landscape / Paisagem), unidade='mm', formato='A4'
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Cabeçalho do Relatório
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Relatorio de Espelho de Ponto - Jornada de 4 Registros", ln=True, align="center")
    
    pdf.set_font("helvetica", "", 10)
    gerado_em = datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y às %H:%M:%S")
    pdf.cell(0, 8, f"Gerado em: {gerado_em} (Horario de Brasilia)", ln=True, align="center")
    pdf.ln(10)
    
    # Ordenar por data/hora se houver registros
    if not df.empty and "Data/Hora" in df.columns:
        df["DataObj"] = pd.to_datetime(df["Data/Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        df = df.sort_values(by="DataObj", ascending=True)

    # Tabela no PDF (A4 Paisagem tem largura útil de cerca de 277mm)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    
    col_widths = [60, 50, 65, 50, 52] # Total = 277 mm
    headers = ["Colaborador", "Tipo de Batida", "Data e Hora", "Latitude", "Longitude"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="center")
    pdf.ln()
    
    pdf.set_font("helvetica", "", 9)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 7, str(row["Colaborador"]), border=1)
        pdf.cell(col_widths[1], 7, str(row["Tipo"]), border=1, align="center")
        pdf.cell(col_widths[2], 7, str(row["Data/Hora"]), border=1, align="center")
        pdf.cell(col_widths[3], 7, str(row["Latitude"]), border=1, align="center")
        pdf.cell(col_widths[4], 7, str(row["Longitude"]), border=1, align="center")
        pdf.ln()
        
    return bytes(pdf.output())

# Carrega os dados salvos
lista_colab, df_reg = carregar_dados_json()

# Menu principal (Inicia direto na aba de bater ponto)
st.sidebar.image("https://img.icons8.com/color/96/map-pin.png", width=80)
st.sidebar.title("Sistema de Ponto")
menu = st.sidebar.selectbox(
    "Navegação", 
    ["1. Bater Ponto (Celular)", "2. Cadastrar Funcionários", "3. Dashboard Gerencial (RH)"]
)

if menu == "1. Bater Ponto (Celular)":
    st.title("📱 Registro de Ponto (4 Batidas Diárias)")
    st.markdown("Horários de referência: **Entrada (07:42)** | **Saída Refeição (12:00)** | **Volta Refeição (13:00)** | **Saída (17:30)**. *Você pode bater em qualquer horário livre.*")

    if not lista_colab:
        st.warning("Nenhum colaborador cadastrado. Vá na aba 'Cadastrar Funcionários' primeiro.")
    else:
        colaborador_atual = st.selectbox("Selecione seu Nome:", lista_colab)
        
        # As 4 opções exatas solicitadas
        tipo_batida = st.selectbox(
            "Tipo de Registro", 
            ["Entrada (Ref: 07:42)", "Saída Refeição (Ref: 12:00)", "Volta Refeição (Ref: 13:00)", "Saída (Ref: 17:30)"]
        )

        st.info("👇 Permita o acesso à localização no navegador para registrar o ponto com GPS.")

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

        lat_input = st.number_input("Latitude Capturada", value=-23.55052, format="%.5f")
        lon_input = st.number_input("Longitude Capturada", value=-46.63331, format="%.5f")

        if st.button("🟢 Confirmar e Bater Ponto", type="primary"):
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
    st.title("📊 Painel de Controle - Registros e Relatórios")
    st.markdown("Acompanhe o histórico de marcações, visualize no mapa e exporte em **PDF Paisagem** organizado por data.")

    df_reg = st.session_state.registros_ponto if "registros_ponto" in locals() else df_reg

    if df_reg.empty:
        st.info("Nenhum ponto registrado ainda. Vá na aba de bater ponto para fazer o primeiro registro!")
    else:
        # Botão de Exportação para PDF em Modo Paisagem
        pdf_bytes = gerar_pdf_paisagem(df_reg)
        st.download_button(
            label="📄 Baixar Relatório em PDF (Modo Paisagem / Organizado por Data)",
            data=pdf_bytes,
            file_name=f"relatorio_ponto_paisagem_{datetime.now(FUSO_BRASILIA).strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
            type="primary"
        )

        st.divider()
        st.subheader("📋 Histórico de Marcações")
        st.dataframe(df_reg, use_container_width=True)

        st.subheader("🗺️ Mapa dos Locais de Batida de Ponto")
        df_mapa = df_reg.rename(columns={"Latitude": "lat", "Longitude": "lon"})
        st.map(df_mapa)
