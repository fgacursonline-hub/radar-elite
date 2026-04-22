import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components 
from datetime import datetime, timedelta, timezone
import pandas as pd
import time

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Caçadores de Elite", layout="wide", page_icon="🎯", initial_sidebar_state="collapsed")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

alunos_cadastrados = {
    "aluno": "elite123",
    "joao": "senha123",
    "maria": "bolsadevalores",
    "admin": "suasenhaforte"
}

if not st.session_state['autenticado']:
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
# 2. CONEXÃO E CACHE DE DADOS
# ==========================================
if 'tv' not in st.session_state:
    try:
        st.session_state.tv = TvDatafeed()
    except Exception:
        pass

bdrs_elite = [
    'NVDC34', 'P2LT34', 'ROXO34', 'INBR32', 'M1TA34', 'TSLA34', 'LILY34', 'AMZO34', 
    'AURA33', 'GOGL34', 'MSFT34', 'MUTC34', 'MELI34', 'C2OI34', 'ORCL34', 'M2ST34', 
    'A1MD34', 'NFLX34', 'ITLC34', 'AVGO34', 'COCA34', 'JBSS32', 'AAPL34', 'XPBR31', 'STOC34'
]

ibrx_selecao = [
    'PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3', 'AXIA3', 
    'SUZB3', 'RENT3', 'RADL3', 'EQTL3', 'LREN3', 'PRIO3', 'HAPV3', 'GGBR4', 'VBBR3', 
    'SBSP3', 'CMIG4', 'CPLE3', 'ENEV3', 'TIMS3', 'TOTS3', 'EGIE3', 'CSAN3', 'ALOS3', 
    'DIRR3', 'VIVT3', 'KLBN11', 'UGPA3', 'PSSA3', 'CYRE3', 'ASAI3', 'RAIL3', 'ISAE3', 
    'CSNA3', 'MGLU3', 'EMBJ3', 'TAEE11', 'BBSE3', 'FLRY3', 'MULT3', 'TFCO4', 'LEVE3', 
    'CPFE3', 'GOAU4', 'MRVE3', 'YDUQ3', 'SMTO3', 'SLCE3', 'CVCB3', 'USIM5', 'BRAP4', 
    'BRAV3', 'EZTC3', 'PCAR3', 'AUAU3', 'DXCO3', 'CASH3', 'VAMO3', 'AZZA3', 'AURE3', 
    'BEEF3', 'ECOR3', 'FESA4', 'POMO4', 'CURY3', 'INTB3', 'JHSF3', 'LIGT3', 'LOGG3', 
    'MDIA3', 'MBRF3', 'NEOE3', 'QUAL3', 'RAPT4', 'ROMI3', 'SANB11', 'SIMH3', 'TEND3', 
    'VULC3', 'PLPL3', 'CEAB3', 'UNIP6', 'LWSA3', 'BPAC11', 'GMAT3', 'CXSE3', 'ABCB4', 
    'CSMG3', 'SAPR11', 'GRND3', 'BRAP3', 'LAVV3', 'RANI3', 'ITSA3', 'ALUP11', 'FIQE3', 
    'COGN3', 'IRBR3', 'SEER3', 'ANIM3', 'JSLG3', 'POSI3', 'MYPK3', 'SOJA3', 'BLAU3', 
    'PGMN3', 'TUPY3', 'VVEO3', 'MELK3', 'SHUL4', 'BRSR6'
]
todos_ativos = list(set(bdrs_elite + ibrx_selecao))

# --- Função de Cache Macro (IBOV, BTC, OURO, etc) ---
@st.cache_data(ttl=300) # Atualiza a cada 5 minutos
def buscar_dados_macro():
    tv_local = TvDatafeed()
    macros = {
        'IBOV': {'symbol': 'IBOV', 'exchange': 'BMFBOVESPA', 'nome': 'IBOVESPA (Brasil)', 'prefix': 'pts', 'formato': '{:,.0f}'},
        'EWZ': {'symbol': 'EWZ', 'exchange': 'AMEX', 'nome': 'EWZ (ETF Brasil EUA)', 'prefix': '$', 'formato': '{:.2f}'},
        'BTC': {'symbol': 'BTCUSD', 'exchange': 'BITSTAMP', 'nome': 'Bitcoin (BTC)', 'prefix': '$', 'formato': '{:,.0f}'},
        'GOLD': {'symbol': 'XAUUSD', 'exchange': 'OANDA', 'nome': 'Ouro (Spot)', 'prefix': '$', 'formato': '{:.2f}'},
        'BRENT': {'symbol': 'UKOIL', 'exchange': 'TVC', 'nome': 'Petróleo Brent', 'prefix': '$', 'formato': '{:.2f}'}
    }
    
    resultados = []
    for chave, config in macros.items():
        try:
            df = tv_local.get_hist(symbol=config['symbol'], exchange=config['exchange'], interval=Interval.in_daily, n_bars=2)
            if df is not None and len(df) >= 2:
                fecho_hj = df['close'].iloc[-1]
                fecho_ontem = df['close'].iloc[-2]
                variacao = ((fecho_hj - fecho_ontem) / fecho_ontem) * 100
                valor_formatado = f"{config['prefix']} " + config['formato'].format(fecho_hj)
                resultados.append({'nome': config['nome'], 'valor': valor_formatado, 'variacao': variacao})
            else:
                resultados.append({'nome': config['nome'], 'valor': 'N/A', 'variacao': 0})
        except:
            resultados.append({'nome': config['nome'], 'valor': 'N/A', 'variacao': 0})
    return resultados

# --- Função de Cache Ranking B3 ---
@st.cache_data(ttl=900) # Memória dura 15 minutos para não travar a tela
def buscar_ranking_ativos(ativos):
    tv_local = TvDatafeed()
    lista_rank = []
    rompendo_topo = []
    
    for ativo in ativos:
        try:
            df = tv_local.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=4000)
            if df is not None and len(df) >= 2:
                fecho_hj = df['close'].iloc[-1]
                fecho_ontem = df['close'].iloc[-2]
                max_hj = df['high'].iloc[-1]
                
                var_pct = ((fecho_hj - fecho_ontem) / fecho_ontem) * 100
                lista_rank.append({'Ativo': ativo, 'Preço': fecho_hj, 'Variação': var_pct})
                
                max_historica = df['high'].iloc[:-1].max()
                if max_hj > max_historica:
                    rompendo_topo.append({'Ativo': ativo, 'Preço': fecho_hj, 'Variação': var_pct})
        except Exception: pass
        time.sleep(0.01)
        
    return pd.DataFrame(lista_rank), pd.DataFrame(rompendo_topo)

def formata_moeda_pct(val, is_pct=False):
    if is_pct: return f"+{val:.2f}%" if val > 0 else f"{val:.2f}%"
    return f"R$ {val:.2f}"

def colorir_tabela(row):
    val_float = float(row['Variação (%)'].replace('%', '').replace('+', ''))
    cor = 'lightgreen' if val_float > 0 else 'lightcoral' if val_float < 0 else 'white'
    return [f'color: {cor}'] * len(row)

# ==========================================
# 3. TELA APÓS LOGIN (DASHBOARD)
# ==========================================
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

# --- TERMÔMETRO MACRO GLOBAL ---
st.subheader("🌐 Termômetro Macro Global")

fuso_br = timezone(timedelta(hours=-3))
agora = datetime.now(fuso_br)

def is_mercado_aberto(data_atual):
    if data_atual.weekday() >= 5: return False
    if not (10 <= data_atual.hour < 18): return False
    feriados_fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20), (12, 25)]
    if (data_atual.month, data_atual.day) in feriados_fixos: return False
    feriados_moveis_2026 = [(2, 16), (2, 17), (4, 3), (6, 4)]
    if data_atual.year == 2026 and (data_atual.month, data_atual.day) in feriados_moveis_2026: return False
    return True

texto_status = "🟢 B3 Aberta" if is_mercado_aberto(agora) else "🔴 B3 Fechada"
st.caption(f"{texto_status} | Globais 24h. Última atualização: {agora.strftime('%d/%m às %H:%M')}.")

with st.spinner("Conectando com as bolsas globais..."):
    dados_macro = buscar_dados_macro()

if dados_macro:
    cols_macro = st.columns(len(dados_macro))
    for i, col in enumerate(cols_macro):
        with col:
            st.metric(
                label=dados_macro[i]['nome'], 
                value=dados_macro[i]['valor'], 
                delta=f"{dados_macro[i]['variacao']:.2f}%" if dados_macro[i]['valor'] != 'N/A' else None
            )

st.divider()

# ==========================================
# 4. PAINEL DE DESTAQUES (ALTAS, QUEDAS E TOPOS)
# ==========================================
st.subheader("🔥 Radar de Destaques (IBrX + BDRs)")
st.markdown("Monitoramento das maiores forças e fraquezas do mercado de capitais brasileiro hoje.")

with st.spinner("Varrendo o mercado em busca de oportunidades extremas..."):
    df_ranking, df_topos = buscar_ranking_ativos(todos_ativos)

col_altas, col_quedas, col_topos = st.columns(3)

if not df_ranking.empty:
    df_altas = df_ranking.sort_values(by='Variação', ascending=False).head(5).copy()
    df_altas['Preço'] = df_altas['Preço'].apply(lambda x: formata_moeda_pct(x))
    df_altas['Variação (%)'] = df_altas['Variação'].apply(lambda x: formata_moeda_pct(x, True))
    df_altas = df_altas.drop(columns=['Variação'])

    df_quedas = df_ranking.sort_values(by='Variação', ascending=True).head(5).copy()
    df_quedas['Preço'] = df_quedas['Preço'].apply(lambda x: formata_moeda_pct(x))
    df_quedas['Variação (%)'] = df_quedas['Variação'].apply(lambda x: formata_moeda_pct(x, True))
    df_quedas = df_quedas.drop(columns=['Variação'])

    with col_altas:
        st.success("### 🚀 Maiores Altas")
        st.dataframe(df_altas.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)

    with col_quedas:
        st.error("### 🩸 Maiores Quedas")
        st.dataframe(df_quedas.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)

    with col_topos:
        st.warning("### 👑 Rompendo Topo Histórico")
        if not df_topos.empty:
            df_topos_fmt = df_topos.sort_values(by='Variação', ascending=False).copy()
            df_topos_fmt['Preço'] = df_topos_fmt['Preço'].apply(lambda x: formata_moeda_pct(x))
            df_topos_fmt['Variação (%)'] = df_topos_fmt['Variação'].apply(lambda x: formata_moeda_pct(x, True))
            df_topos_fmt = df_topos_fmt.drop(columns=['Variação'])
            st.dataframe(df_topos_fmt.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ativo está a romper o topo histórico hoje.")
else:
    st.info("Aguardando cotações para gerar o ranking.")

st.divider()

# ==========================================
# 5. O SEU ARSENAL E LINKS ÚTEIS
# ==========================================
st.subheader("🛠️ O Seu Arsenal de Ferramentas")
c1, c2, c3 = st.columns(3)
with c1:
    st.info("### 📉 Regressão à Média\nVarreduras de **IFR** e **Canais de Keltner** para caçar ativos esticados e exaustos.")
    st.success("### 📊 Fluxo Institucional\nEncontre defesas de tubarões na **VWAP** com cruzamento da **POC** de Volume.")
with c2:
    st.warning("### 🔥 Seguidores de Tendência\nMonitore o **Setup 9.1**, **Fura-Teto (Momentum)** e **Volatilidade**.")
    st.error("### 📐 Fibo & Smart Money\nOpere a proporção áurea com o **Rastreador Fibonacci** e falhas de **FVG**.")
with c3:
    st.markdown("""
    <div style='background-color: #2b2b2b; padding: 15px; border-radius: 10px; border-left: 5px solid #a3a3a3;'>
        <h3 style='margin-top: 0;'>🕯️ Price Action</h3>
        Encontre os gatilhos gráficos perfeitos em zonas de valor (Martelos, Haramis e afins).
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.subheader("🧭 Inteligência de Mercado & Calendários")
cl1, cl2, cl3, cl4 = st.columns(4)
with cl1: st.link_button("📅 Calendário Econômico", "https://br.investing.com/economic-calendar", use_container_width=True)
with cl2: st.link_button("📊 Temporada de Balanços", "https://br.investing.com/earnings-calendar", use_container_width=True)
with cl3: st.link_button("🔍 Filtro de Ações", "https://br.investing.com/stock-screener/momentum-masters", use_container_width=True)
with cl4: st.link_button("🦈 HedgeFollow (Fundos)", "https://hedgefollow.com/", use_container_width=True)

# ==========================================
# 6. RADAR DE NOTÍCIAS MULTI-FONTE (FILTRADO)
# ==========================================
st.divider()
st.subheader("📰 Radar de Notícias Caçadores de Elite")
import xml.etree.ElementTree as ET
import requests

def carregar_feed(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        itens = []
        
        # Filtro blindado contra lixo da internet e esportes
        palavras_proibidas = ['futebol', 'copa', 'assistir', 'corinthians', 'vasco', 'palmeiras', 'flamengo', 'brasileirão', 'fofoca', 'bbb', 'novela', 'filme']
        
        for item in root.findall('./channel/item'): 
            titulo = item.find('title').text
            link = item.find('link').text
            
            # Converte para minúsculas para a verificação não falhar
            titulo_lower = titulo.lower()
            
            # Se encontrar qualquer palavra proibida, ignora a notícia
            if any(palavra in titulo_lower for palavra in palavras_proibidas):
                continue
                
            itens.append({"titulo": titulo, "link": link})
            
            # Quando atingir 8 notícias limpas, pára de procurar
            if len(itens) >= 8:
                break
                
        return itens
    except: return None

# Trocamos o G1 pelo Money Times para focar 100% no mercado
tab_info, tab_inv, tab_mt = st.tabs(["💰 InfoMoney", "📈 Investing.com", "🗞️ Money Times"])

with tab_info:
    n_im = carregar_feed("https://www.infomoney.com.br/feed/")
    if n_im:
        for n in n_im: st.markdown(f"• **{n['titulo']}** [Ler mais]({n['link']})")
with tab_inv:
    n_inv = carregar_feed("https://br.investing.com/rss/news_25.rss")
    if n_inv:
        for n in n_inv: st.markdown(f"• **{n['titulo']}** [Ler mais]({n['link']})")
with tab_mt:
    n_mt = carregar_feed("https://www.moneytimes.com.br/feed/")
    if n_mt:
        for n in n_mt: st.markdown(f"• **{n['titulo']}** [Ler mais]({n['link']})")
