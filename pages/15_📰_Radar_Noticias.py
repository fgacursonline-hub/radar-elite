import streamlit as st
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import sys
import os

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

# Lista mestra de ativos
ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar de Notícias", layout="wide", page_icon="📰")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

st.title("📰 Cão Farejador: Radar de Notícias")
st.markdown("Varredura em tempo real nos principais portais financeiros do mundo para capturar o sentimento do mercado antes do pregão abrir.")

# ==========================================
# 3. MOTOR DE BUSCA (GOOGLE NEWS RSS)
# ==========================================
def buscar_noticias_google(termo_busca, periodo_dias):
    """
    Usa a API aberta de RSS do Google News para puxar as manchetes.
    """
    # Adiciona o filtro de tempo do Google (ex: when:1d)
    query_formatada = f"{termo_busca} when:{periodo_dias}d"
    query_codificada = urllib.parse.quote(query_formatada)
    
    # URL do Google News Brasil
    url = f"https://news.google.com/rss/search?q={query_codificada}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    
    # Camuflagem (User-Agent) para não ser bloqueado pelo Google
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    
    resultados = []
    
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            # Navega pela árvore do XML para achar as notícias (itens)
            for item in root.findall('.//item'):
                titulo_completo = item.find('title').text
                link = item.find('link').text
                data_pub = item.find('pubDate').text
                fonte = item.find('source').text if item.find('source') is not None else "Desconhecida"
                
                # O Google às vezes coloca "Nome do Site - Título". Vamos limpar isso.
                if " - " in titulo_completo:
                    titulo = titulo_completo.rsplit(" - ", 1)[0]
                else:
                    titulo = titulo_completo
                
                # Converte a data gringa para o padrão BR
                try:
                    dt_obj = datetime.strptime(data_pub, "%a, %d %b %Y %H:%M:%S %Z")
                    data_formatada = dt_obj.strftime("%d/%m/%Y %H:%M")
                except:
                    data_formatada = data_pub
                
                resultados.append({
                    'Data': data_formatada,
                    'Fonte': fonte,
                    'Manchete': titulo,
                    'Link': link
                })
                
    except Exception as e:
        st.error(f"⚠️ Erro ao interceptar os satélites de notícias: {e}")
        
    return resultados

# ==========================================
# 4. PAINEL DE CONTROLE (INTERFACE)
# ==========================================
with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tipo_busca = st.radio("Método de Busca:", ["Usar Lista do Radar", "Digitar Nome Livre"], horizontal=True)
        if tipo_busca == "Usar Lista do Radar":
            ativo_selecionado = st.selectbox("Selecione o Ativo:", ativos_para_rastrear)
            termo_final = f"{ativo_selecionado} ações OR mercado"
        else:
            termo_livre = st.text_input("Digite o ativo, empresa ou assunto:", placeholder="Ex: NVIDIA balanço")
            termo_final = termo_livre
            
    with col2:
        st.write("") # Espaçamento
        periodo = st.selectbox("Janela de Tempo:", ["Hoje (Últimas 24h)", "Últimos 3 dias", "Últimos 7 dias", "Último mês"])
        mapa_dias = {"Hoje (Últimas 24h)": 1, "Últimos 3 dias": 3, "Últimos 7 dias": 7, "Último mês": 30}
        dias = mapa_dias[periodo]
        
    with col3:
        st.write("")
        st.write("")
        btn_farejar = st.button("📡 Iniciar Varredura de Notícias", type="primary", use_container_width=True)

# ==========================================
# 5. EXECUÇÃO DA BUSCA
# ==========================================
if btn_farejar:
    if tipo_busca == "Digitar Nome Livre" and not termo_final.strip():
        st.warning("Comandante, digite um alvo válido para a varredura.")
    else:
        with st.spinner(f"Interceptando comunicações sobre {termo_final.replace(' ações OR mercado', '')}..."):
            # Executa o motor
            noticias = buscar_noticias_google(termo_final, dias)
            time.sleep(0.5) # Charme de carregamento
            
            if noticias:
                st.success(f"✅ Varredura Concluída! Encontramos {len(noticias)} boletins importantes no radar.")
                
                # Criação da tabela com links clicáveis
                df_noticias = pd.DataFrame(noticias)
                
                # Configuração do st.data_editor/dataframe para suportar links nativos do Streamlit
                st.data_editor(
                    df_noticias,
                    column_config={
                        "Link": st.column_config.LinkColumn(
                            "🔗 Ler na Íntegra",
                            display_text="Acessar Matéria"
                        ),
                        "Manchete": st.column_config.TextColumn(
                            "Manchete Principal",
                            width="large"
                        ),
                        "Fonte": st.column_config.TextColumn(
                            "Portal",
                            width="medium"
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=True # Tabela apenas para leitura
                )
                
                # ------------------------------------
                # MÓDULO DE IA (PRONTO PARA O FUTURO)
                # ------------------------------------
                st.divider()
                with st.expander("🤖 Resumo Analítico por Inteligência Artificial (Módulo Desativado)"):
                    st.info("Para ativar o Cérebro Analítico, precisamos plugar a chave da API do Gemini ou da OpenAI no sistema. Quando ativado, o robô lerá essas manchetes e escreverá um relatório tático automático dizendo se o mercado está **Otimista** ou **Pessimista**.")
            else:
                st.warning(f"Silêncio no rádio. Nenhuma notícia relevante encontrada para este alvo no período de {dias} dia(s).")
