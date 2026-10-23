import os
import json
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd
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

# Função para converter Latitude e Longitude em Endereço amigável
def obter_endereco(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'SistemaPontoApp/1.0'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get("display_name", f"Lat: {lat}, Lon: {lon}")
    except Exception:
        pass
    return f"Lat: {lat}, Lon: {lon}"

# Funções para carregar e salvar dados em JSON (forçando Benedito Bandola de Oliveira Silva)
def carregar_dados_json():
    colaboradores = ["Benedito Bandola de Oliveira Silva"]
    if os.path.exists(ARQUIVO_COLABORADORES):
        try:
            with open(ARQUIVO_COLABORADORES, "r", encoding="utf-8") as f:
                dados_salvos = json.load(f)
                if isinstance(dados_salvos, list):
                    colaboradores = [c for c in dados_salvos if "Eu Mesmo" not in c]
                    if "Benedito Bandola de Oliveira Silva" not in colaboradores:
                        colaboradores.insert(0, "Benedito Bandola de Oliveira Silva")
        except Exception:
            pass

    with open(ARQUIVO_COLABORADORES, "w", encoding="utf-8") as f:
        json.dump(colaboradores, f, ensure_ascii=False, indent=4)

    if os.path.exists(ARQUIVO_REGISTROS):
        with open(ARQUIVO_REGISTROS, "r", encoding="utf-8") as f:
            registros = json.load(f)
        df_registros = pd.DataFrame(registros)
    else:
        df_registros = pd.DataFrame(columns=["Colaborador", "Tipo", "Data/Hora", "Data", "Hora", "Latitude", "Longitude", "Endereco"])

    return colaboradores, df_registros

def salvar_colaboradores(colaboradores):
    with open(ARQUIVO_COLABORADORES, "w", encoding="utf-8") as f:
        json.dump(colaboradores, f, ensure_ascii=False, indent=4)

def salvar_registros(df_registros):
    with open(ARQUIVO_REGISTROS, "w", encoding="utf-8") as f:
        json.dump(df_registros.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

def consolidar_por_dia_duas_linhas(df):
    """Transforma registros individuais em 2 linhas por dia (Manhã / Tarde)"""
    if df.empty:
        return pd.DataFrame(columns=["Colaborador", "Data", "Turno", "Tipo1", "Hora1", "Tipo2", "Hora2"])
    
    if "Data" not in df.columns or "Hora" not in df.columns:
        df["DataObj"] = pd.to_datetime(df["Data/Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        df["Data"] = df["DataObj"].dt.strftime("%d/%m/%Y")
        df["Hora"] = df["DataObj"].dt.strftime("%H:%M:%S")

    linhas_consolidadas = []
    for (colab, data), group in df.groupby(["Colaborador", "Data"]):
        entrada_reg, saida_int_reg, ret_int_reg, saida_reg = None, None, None, None
        
        for _, row in group.iterrows():
            tipo = row["Tipo"]
            if tipo == "Entrada":
                if entrada_reg is None:
                    entrada_reg = row
                else:
                    ret_int_reg = row
            elif tipo == "Saída Intervalo":
                saida_int_reg = row
            elif tipo == "Retorno Intervalo":
                ret_int_reg = row
            elif tipo == "Saída":
                saida_reg = row

        # Linha 1: Entrada e Saída Intervalo
        linhas_consolidadas.append({
            "Colaborador": colab,
            "Data": data,
            "Turno": "Manhã / Início",
            "Tipo1": "Entrada",
            "Hora1": entrada_reg["Hora"] if entrada_reg is not None else "-",
            "Tipo2": "Saída Intervalo",
            "Hora2": saida_int_reg["Hora"] if saida_int_reg is not None else "-"
        })

        # Linha 2: Retorno Intervalo e Saída
        linhas_consolidadas.append({
            "Colaborador": colab,
            "Data": data,
            "Turno": "Tarde / Fim",
            "Tipo1": "Retorno Intervalo",
            "Hora1": ret_int_reg["Hora"] if ret_int_reg is not None else "-",
            "Tipo2": "Saída",
            "Hora2": saida_reg["Hora"] if saida_reg is not None else "-"
        })
        
    return pd.DataFrame(linhas_consolidadas)

def gerar_pdf_sem_localizacao(df_duas_linhas):
    pdf = FPDF(orientation='P', unit='mm', format='A4') # Retrato (Portrait) já que não tem o campo de localização longo
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 15)
    pdf.cell(0, 8, "Relatorio de Espelho de Ponto", ln=True, align="center")
    
    pdf.set_font("helvetica", "", 9)
    gerado_em = datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y às %H:%M:%S")
    pdf.cell(0, 6, f"Gerado em: {gerado_em} (Horario de Brasilia)", ln=True, align="center")
    pdf.ln(8)

    pdf.set_font("helvetica", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    
    col_widths = [65, 25, 28, 22, 28, 22]
    headers = ["Colaborador", "Data", "1ª Batida", "Hora", "2ª Batida", "Hora"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="center")
    pdf.ln()
    
    pdf.set_font("helvetica", "", 8.5)
    for _, row in df_duas_linhas.iterrows():
        pdf.cell(col_widths[0], 7, str(row["Colaborador"]), border=1)
        pdf.cell(col_widths[1], 7, str(row["Data"]), border=1, align="center")
        pdf.cell(col_widths[2], 7, str(row["Tipo1"]), border=1, align="center")
        pdf.cell(col_widths[3], 7, str(row["Hora1"]), border=1, align="center")
        pdf.cell(col_widths[4], 7, str(row["Tipo2"]), border=1, align="center")
        pdf.cell(col_widths[5], 7, str(row["Hora2"]), border=1, align="center")
        pdf.ln()
        
    return bytes(pdf.output())

# Carrega os dados salvos
lista_colab, df_reg = carregar_dados_json()

# Configuração da Barra Lateral (Sidebar) com Seleção de Usuário
st.sidebar.title("Sistema de Ponto")
st.sidebar.markdown("---")
st.sidebar.subheader("👤 Usuário Ativo")

colaborador_atual = st.sidebar.selectbox("Selecione quem está usando:", lista_colab, index=0)

st.sidebar.markdown("---")
menu = st.sidebar.selectbox(
    "Navegação", 
    [
        "1. Bater Ponto (Celular)", 
        "2. Inserir / Editar Ponto Manualmente", 
        "3. Cadastrar Funcionários", 
        "4. Dashboard Gerencial (RH)"
    ]
)

if menu == "1. Bater Ponto (Celular)":
    st.title("📱 Registro de Ponto")
    st.markdown(f"Colaborador selecionado: **{colaborador_atual}**. Selecione o tipo de registro abaixo. A geolocalização do seu GPS será capturada automaticamente.")

    if not lista_colab:
        st.warning("Nenhum colaborador cadastrado. Vá na aba 'Cadastrar Funcionários' primeiro.")
    else:
        tipo_batida = st.selectbox(
            "Tipo de Registro", 
            ["Entrada", "Saída Intervalo", "Retorno Intervalo", "Saída"]
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
                #map { height: 260px; width: 100%; border-radius: 8px; margin-top: 10px; }
                .info-box { background: #f8f9fa; padding: 10px; border-radius: 6px; border: 1px solid #dee2e6; font-family: sans-serif; }
            </style>
        </head>
        <body>
            <div class="info-box">
                <p id="status" style="margin:0; font-weight: bold; color: #0066cc;">Obtendo sua localização real via GPS...</p>
            </div>
            <div id="map"></div>

            <script>
                var map = L.map('map').setView([-21.78436, -46.58513], 15);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap'
                }).addTo(map);

                var marker;

                function setStreamlitValue(lat, lon) {
                    const doc = window.parent.document;
                    const inputs = doc.querySelectorAll('input[type="number"]');
                    inputs.forEach(input => {
                        if (input.getAttribute('aria-label') && input.getAttribute('aria-label').includes('Latitude')) {
                            setInputValue(input, lat);
                        }
                        if (input.getAttribute('aria-label') && input.getAttribute('aria-label').includes('Longitude')) {
                            setInputValue(input, lon);
                        }
                    });
                }

                function setInputValue(input, value) {
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, "value").set;
                    nativeInputValueSetter.call(input, value);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }

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

                        setStreamlitValue(userLat, userLon);

                    }, function(error) {
                        document.getElementById("status").innerHTML = "⚠️ Ative o GPS no seu celular para registrar a localização exata.";
                        document.getElementById("status").style.color = "orange";
                    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
                } else {
                    document.getElementById("status").innerHTML = "Seu navegador não suporta geolocalização.";
                }
            </script>
        </body>
        </html>
        """
        
        st.components.v1.html(geo_html, height=330)
        st.divider()

        if "lat_val" not in st.session_state:
            st.session_state.lat_val = -21.78436
        if "lon_val" not in st.session_state:
            st.session_state.lon_val = -46.58513

        col1, col2 = st.columns(2)
        with col1:
            lat_input = st.number_input("Latitude Capturada", value=st.session_state.lat_val, format="%.5f")
        with col2:
            lon_input = st.number_input("Longitude Capturada", value=st.session_state.lon_val, format="%.5f")

        if st.button("🟢 Confirmar e Bater Ponto", type="primary"):
            agora = datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M:%S")
            data_atual = datetime.now(FUSO_BRASILIA).strftime("%d/%m/%Y")
            hora_atual = datetime.now(FUSO_BRASILIA).strftime("%H:%M:%S")
            
            with st.spinner("Buscando endereço correspondente à sua localização GPS..."):
                endereco_encontrado = obter_endereco(lat_input, lon_input)
            
            novo_registro = pd.DataFrame([{
                "Colaborador": colaborador_atual,
                "Tipo": tipo_batida,
                "Data/Hora": agora,
                "Data": data_atual,
                "Hora": hora_atual,
                "Latitude": lat_input,
                "Longitude": lon_input,
                "Endereco": endereco_encontrado
            }])
            
            df_reg = pd.concat([df_reg, novo_registro], ignore_index=True)
            salvar_registros(df_reg)
            
            st.success(f"Ponto de **{tipo_batida}** registrado com sucesso para **{colaborador_atual}** às **{agora}**!")
            st.balloons()

elif menu == "2. Inserir / Editar Ponto Manualmente":
    st.title("✍️ Inserção e Edição Manual de Ponto")
    st.markdown("Use esta tela para inserir manualmente pontos passados (como ontem) ou corrigir horários de hoje.")

    with st.form("form_manual"):
        colaborador_manual = st.selectbox("Colaborador:", lista_colab)
        tipo_manual = st.selectbox("Tipo de Registro:", ["Entrada", "Saída Intervalo", "Retorno Intervalo", "Saída"])
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            data_manual_obj = st.date_input("Data do Ponto:", value=datetime.now(FUSO_BRASILIA).date())
        with col_m2:
            hora_manual_obj = st.time_input("Horário do Ponto:", value=datetime.now(FUSO_BRASILIA).time())
            
        btn_salvar_manual = st.form_submit_button("💾 Salvar Registro Manual", type="primary")
        
        if btn_salvar_manual:
            data_str = data_manual_obj.strftime("%d/%m/%Y")
            hora_str = hora_manual_obj.strftime("%H:%M:%S")
            data_hora_str = f"{data_str} {hora_str}"
            
            novo_registro_manual = pd.DataFrame([{
                "Colaborador": colaborador_manual,
                "Tipo": tipo_manual,
                "Data/Hora": data_hora_str,
                "Data": data_str,
                "Hora": hora_str,
                "Latitude": -21.78436,
                "Longitude": -46.58513,
                "Endereco": "Inserido manualmente"
            }])
            
            df_reg = pd.concat([df_reg, novo_registro_manual], ignore_index=True)
            salvar_registros(df_reg)
            st.success(f"✅ Ponto manual de **{tipo_manual}** para **{colaborador_manual}** em **{data_hora_str}** salvo com sucesso!")

elif menu == "3. Cadastrar Funcionários":
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

elif menu == "4. Dashboard Gerencial (RH)":
    st.title("📊 Painel de Controle - Registros e Relatórios")
    st.markdown("Acompanhe o histórico de marcações, filtre por colaborador/data e exporte o **Espelho de Ponto em PDF**.")

    if df_reg.empty:
        st.info("Nenhum ponto registrado ainda. Vá na aba de bater ponto ou inserir manualmente para adicionar registros!")
    else:
        df_duas_linhas = consolidar_por_dia_duas_linhas(df_reg)

        st.subheader("🔍 Filtros de Busca")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            colaboradores_filtro = ["Todos"] + sorted(list(df_duas_linhas["Colaborador"].unique()))
            filtro_colab = st.selectbox("Filtrar por Colaborador:", colaboradores_filtro)
            
        with col_f2:
            datas_disponiveis = sorted(list(df_duas_linhas["Data"].unique()))
            filtro_data = st.selectbox("Filtrar por Data Específica:", ["Todas"] + datas_disponiveis)

        df_filtrado = df_duas_linhas.copy()
        if filtro_colab != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Colaborador"] == filtro_colab]
        if filtro_data != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Data"] == filtro_data]

        st.divider()

        pdf_bytes = gerar_pdf_sem_localizacao(df_filtrado)
        st.download_button(
            label="📄 Baixar Espelho de Ponto em PDF (Sem Localização)",
            data=pdf_bytes,
            file_name=f"espelho_ponto_{datetime.now(FUSO_BRASILIA).strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf",
            type="primary"
        )

        st.divider()
        st.subheader("📋 Espelho de Ponto Consolidado")
        st.dataframe(df_filtrado, use_container_width=True)

        st.divider()
        st.subheader("🔐 Área Administrativa (Correção e Exclusão)")
        
        with st.expander("Clique aqui para acessar as ferramentas de Administrador (Senha necessária)"):
            senha_admin = st.text_input("Senha de Administrador:", type="password")
            
            if senha_admin == "1234":
                st.success("✅ Acesso de administrador autorizado!")
                
                st.markdown("### Tabela Bruta de Registros (Para exclusão individual)")
                st.dataframe(df_reg, use_container_width=True)
                
                if not df_reg.empty:
                    indice_para_apagar = st.number_input("Digite o Índice (ID da linha) do registro que deseja apagar:", min_value=0, max_value=len(df_reg)-1, step=1)
                    
                    if st.button("🗑️ Excluir Registro Selecionado", type="secondary"):
                        df_reg = df_reg.drop(indice_para_apagar).reset_index(drop=True)
                        salvar_registros(df_reg)
                        st.success(f"Registro do índice {indice_para_apagar} excluído com sucesso!")
                        st.rerun()
                
                st.markdown("---")
                if st.button("⚠️ Apagar TODOS os Registros do Sistema", type="primary"):
                    df_reg = pd.DataFrame(columns=["Colaborador", "Tipo", "Data/Hora", "Data", "Hora", "Latitude", "Longitude", "Endereco"])
                    salvar_registros(df_reg)
                    st.warning("Todos os registros foram apagados permanentemente.")
                    st.rerun()
                    
            elif senha_admin != "":
                st.error("❌ Senha incorreta. Digite '1234'.")
