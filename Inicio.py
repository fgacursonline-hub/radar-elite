import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components 
from datetime import datetime, timedelta, timezone

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

# Relógio e Status do Mercado (Lógica B3 com Feriados)
fuso_br = timezone(timedelta(hours=-3))
agora = datetime.now(fuso_br)

def is_mercado_aberto(data_atual):
    if data_atual.weekday() >= 5: return False
    if not (10 <= data_atual.hour < 18): return False
    
    feriados_fixos = [
        (1, 1), (4, 21), (5, 1), (9, 7), 
        (10, 12), (11, 2), (11, 15), (11, 20), (12, 25)
    ]
    if (data_atual.month, data_atual.day) in feriados_fixos: return False
        
    feriados_moveis_2026 = [(2, 16), (2, 17), (4, 3), (6, 4)]
    if data_atual.year == 2026 and (data_atual.month, data_atual.day) in feriados_moveis_2026: return False
        
    return True

if is_mercado_aberto(agora): texto_status = "🟢 Mercado Aberto"
else: texto_status = "🔴 Mercado Fechado"

msg_atualizacao = f"{texto_status}. Última atualização: {agora.strftime('%d/%m às %H:%M')}."
st.caption(msg_atualizacao)

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
    st.info("### 📉 Regressão à Média\nVarreduras de **IFR** e **Canais de Keltner** para caçar ativos esticados e exaustos.")
    st.success("### 📊 Fluxo Institucional\nEncontre defesas de tubarões na **VWAP** com cruzamento da **POC** de Volume.")

with c2:
    st.warning("### 🔥 Seguidores de Tendência\nMonitore o **Setup 9.1**, **Rompimentos** e **Explosão de Volatilidade**.")
    st.error("### 📐 Fibo & Smart Money\nOpere a proporção áurea com o **Rastreador Fibonacci** e falhas de **FVG**.")

with c3:
    st.markdown("""
    <div style='background-color: #2b2b2b; padding: 15px; border-radius: 10px; border-left: 5px solid #a3a3a3;'>
        <h3 style='margin-top: 0;'>🕯️ Price Action</h3>
        Encontre os gatilhos gráficos perfeitos em zonas de valor (Martelos, Haramis e afins).
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# 4. INTELIGÊNCIA DE MERCADO E CALENDÁRIOS
# ==========================================
st.divider()
st.subheader("🧭 Inteligência de Mercado & Calendários")
st.markdown("Acesse rapidamente a agenda macroeconômica, balanços e os movimentos dos grandes tubarões.")

c_link1, c_link2, c_link3, c_link4 = st.columns(4)

with c_link1:
    st.link_button("📅 Calendário Econômico", "https://br.investing.com/economic-calendar", use_container_width=True)
    st.caption("Agenda de indicadores e eventos globais.")

with c_link2:
    st.link_button("📊 Temporada de Balanços", "https://br.investing.com/earnings-calendar", use_container_width=True)
    st.caption("Fique atento à divulgação de resultados.")

with c_link3:
    st.link_button("🔍 Filtro de Ações (Screener)", "https://br.investing.com/stock-screener/momentum-masters", use_container_width=True)
    st.caption("Rastreador de Momentum Masters.")

with c_link4:
    st.link_button("🐋 Investing Pro Ideas", "https://br.investing.com/pro/ideas", use_container_width=True)
    st.link_button("🦈 HedgeFollow (Fundos)", "https://hedgefollow.com/", use_container_width=True)


# ==========================================
# 5. RADAR DE NOTÍCIAS MULTI-FONTE (100% BR)
# ==========================================
st.divider()
st.subheader("📰 Radar de Notícias Caçadores de Elite")
st.markdown("Fique por dentro de tudo o que acontece nas principais fontes de economia do Brasil.")

import xml.etree.ElementTree as ET
import requests

def carregar_feed(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        itens = []
        for item in root.findall('./channel/item')[:8]: 
            titulo = item.find('title').text
            link = item.find('link').text
            itens.append({"titulo": titulo, "link": link})
        return itens
    except:
        return None

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
