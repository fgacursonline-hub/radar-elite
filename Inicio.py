import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components 
from datetime import datetime, timedelta, timezone # <-- Importação adicionada para o relógio da B3

# Mantendo sua configuração original de página e proteção
st.set_page_config(page_title="Caçadores de Elite", layout="wide", page_icon="🎯", initial_sidebar_state="collapsed")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Seus alunos cadastrados originais
alunos_cadastrados = {
    "aluno": "elite123",
    "joao": "senha123",
    "maria": "bolsadevalores",
    "admin": "suasenhaforte"
}

if not st.session_state['autenticado']:
    # CSS para esconder o menu antes do login
    st.markdown("<style>[data-testid='stSidebar'] {display: none;} [data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center;'>🎯 Caçadores de Elite</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Área Restrita do Radar Quantitativo</p>", unsafe_allow_html=True)
        with st.form("form_login"):
            usuario = st.text_input("Usuário").lower().strip()
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                if usuario in alunos_cadastrados and alunos_cadastrados[usuario] == senha:
                    st.session_state['autenticado'] = True
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# ==========================================
# TELA APÓS LOGIN (DASHBOARD DE ELITE)
# ==========================================

# Inicializa o TradingView na sessão global APENAS se estiver logado
if 'tv' not in st.session_state:
    try:
        st.session_state.tv = TvDatafeed()
    except Exception:
        pass

# Cabeçalho com o seu botão de saída
c_tit, c_sair = st.columns([8, 1])
with c_tit:
    st.title("🎯 Terminal Caçadores de Elite")
    st.markdown("Bem-vindo ao seu Quartel-General de Operações Institucionais.")
with c_sair:
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

st.divider()

# --- TERMÔMETRO DO MERCADO ---
st.subheader("🌐 Termômetro do Mercado (IBOVESPA)")

# Relógio e Status do Mercado (Lógica B3)
fuso_br = timezone(timedelta(hours=-3))
agora = datetime.now(fuso_br)

# Verifica se é dia de semana (0 a 4) e entre 10h e 18h
if agora.weekday() < 5 and 10 <= agora.hour < 18:
    texto_status = "🟢 Mercado Aberto"
else:
    texto_status = "🔴 Mercado Fechado"

msg_atualizacao = f"{texto_status}. Última atualização: {agora.strftime('%d/%m às %H:%M')}."
st.caption(msg_atualizacao) # Exibe a mensagem em texto menor logo abaixo do título

try:
    tv = st.session_state.tv
    df_ibov = tv.get_hist(symbol='IBOV', exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=2)
    
    if df_ibov is not None and len(df_ibov) >= 2:
        fecho_hoje = df_ibov['close'].iloc[-1]
        fecho_ontem = df_ibov['close'].iloc[-2]
        variacao = ((fecho_hoje - fecho_ontem) / fecho_ontem) * 100
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(label="Pontuação Atual", value=f"{fecho_hoje:,.0f} pts", delta=f"{variacao:.2f}%")
        with col_m2:
            estado_mercado = "🐂 Bull Market (Comprador)" if variacao > 0 else "🐻 Bear Market (Vendedor)"
            st.info(f"**Sentimento:** {estado_mercado}")
        with col_m3:
            st.warning("💡 **Dica de Ouro:** Não lute contra a tendência principal do IBOV.")
    else:
        st.caption("Aguardando conexão com os dados da B3...")
except Exception as e:
    st.caption("Sem conexão com os dados do mercado no momento.")

st.divider()

# --- O SEU ARSENAL ---
st.subheader("🛠️ O Seu Arsenal de Ferramentas")
st.markdown("Selecione sua estratégia no menu lateral à esquerda para iniciar as varreduras.")

c1, c2, c3 = st.columns(3)

with c1:
    st.info("### 📉 IFR & Keltner\nDescubra ativos sobrevendidos, esticados e com anomalias de volatilidade usando a regressão à média.")

with c2:
    st.warning("### 🔥 Setup 9.1\nO rastreador de inércia e tendência do lendário Larry Williams. Compre a força e venda a fraqueza.")

with c3:
    st.success("### 🕳️ Smart Money (FVG)\nOpere exatamente como os bancos institucionais, encontrando vácuos de liquidez e armadilhas.")


# ==========================================
# 4. RADAR DE NOTÍCIAS MULTI-FONTE (100% BR)
# ==========================================
st.divider()
st.subheader("📰 Radar de Notícias Caçadores de Elite")
st.markdown("Fique por dentro de tudo o que acontece nas principais fontes de economia do Brasil.")

import xml.etree.ElementTree as ET
import requests

# Função mestre para buscar e processar as notícias
def carregar_feed(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        itens = []
        for item in root.findall('./channel/item')[:8]: # Pega as 8 últimas de cada
            titulo = item.find('title').text
            link = item.find('link').text
            itens.append({"titulo": titulo, "link": link})
        return itens
    except:
        return None

# Criação das Sub-Abas de Notícias
tab_info, tab_inv, tab_g1 = st.tabs(["💰 InfoMoney", "📈 Investing.com", "🌍 G1 Economia"])

with tab_info:
    noticias_im = carregar_feed("https://www.infomoney.com.br/feed/")
    if noticias_im:
        for n in noticias_im:
            st.markdown(f"• **{n['titulo']}** \n[Ler mais]({n['link']})")
            st.divider()
    else:
        st.error("Erro ao carregar InfoMoney.")

with tab_inv:
    # O Investing.com às vezes bloqueia bots, por isso o timeout e headers são vitais
    noticias_inv = carregar_feed("https://br.investing.com/rss/news_25.rss")
    if noticias_inv:
        for n in noticias_inv:
            st.markdown(f"• **{n['titulo']}** \n[Ler mais]({n['link']})")
            st.divider()
    else:
        st.warning("Investing.com temporariamente indisponível.")

with tab_g1:
    noticias_g1 = carregar_feed("https://g1.globo.com/rss/g1/economia/")
    if noticias_g1:
        for n in noticias_g1:
            st.markdown(f"• **{n['titulo']}** \n[Ler mais]({n['link']})")
            st.divider()
    else:
        st.error("Erro ao carregar G1 Economia.")
