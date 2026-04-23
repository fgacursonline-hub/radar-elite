import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components 
from datetime import datetime, timedelta, timezone
import pandas as pd
import time

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Caçadores de Elite", layout="wide", page_icon="🎯", initial_sidebar_state="collapsed")

# --- CAMUFLAGEM E AJUSTES DE FONTE ---
st.markdown("""
    <style>
    /* Oculta o Manual do menu lateral */
    [data-testid="stSidebarNav"] a[href*="Manual"] {
        display: none !important;
    }
    /* Ajusta os números do Termômetro Macro */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
    }
    /* Ajuste para os cabeçalhos das caixas coloridas (Altas/Quedas) */
    div[data-testid="stNotification"] h3 {
        font-size: 1.1rem !important;
        white-space: nowrap !important;
        margin-bottom: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

alunos_cadastrados = {
    "aluno": "elite123",
    "joao": "senha123",
    "maria": "bolsadevalores",
    "admin": "suasenhaforte"
}

aviso_risco = "⚠️ **AVISO DE COMANDO:** Esta plataforma foi forjada exclusivamente para fins educacionais e de estudo quantitativo. Não emitimos recomendações de compra, venda ou manutenção de ativos. Toda operação no mercado financeiro gera risco real de perda de capital. Seja um Caçador com disciplina implacável e responsabilidade: o seu maior patrimônio é o seu gerenciamento de risco."

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
                    
        st.markdown("<br>", unsafe_allow_html=True)
        st.warning(aviso_risco)
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

@st.cache_data(ttl=300) 
def buscar_dados_macro():
    tv_local = TvDatafeed()
    macros = {
        'IBOV': {'symbol': 'IBOV', 'exchange': 'BMFBOVESPA', 'nome': 'IBOVESPA', 'prefix': 'pts', 'formato': '{:,.0f}', 'url': 'https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3AIBOV'},
        'WIN': {'symbol': 'WIN1!', 'exchange': 'BMFBOVESPA', 'nome': 'Mini Índice', 'prefix': 'pts', 'formato': '{:,.0f}', 'url': 'https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3AWIN1%21'},
        'WDO': {'symbol': 'WDO1!', 'exchange': 'BMFBOVESPA', 'nome': 'Mini Dólar', 'prefix': 'R$', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3AWDO1%21'},
        'DI1': {'symbol': 'DI11!', 'exchange': 'BMFBOVESPA', 'nome': 'Juros BR (DI1)', 'prefix': '%', 'formato': '{:.3f}', 'url': 'https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3ADI11%21'},
        'EWZ': {'symbol': 'EWZ', 'exchange': 'AMEX', 'nome': 'EWZ (ETF Brasil)', 'prefix': '$', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=AMEX%3AEWZ'},
        'MINERIO': {'symbol': 'FEF2!', 'exchange': 'SGX', 'nome': 'Minério de Ferro', 'prefix': '$', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=SGX%3AFEF2%21'},
        'BRENT': {'symbol': 'BRN1!', 'exchange': 'ICEEUR', 'nome': 'Petróleo Brent', 'prefix': '$', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=ICEEUR%3ABRN1%21'},
        'GOLD': {'symbol': 'XAUUSD', 'exchange': 'OANDA', 'nome': 'Ouro (Spot)', 'prefix': '$', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=OANDA%3AXAUUSD'},
        'BTC': {'symbol': 'BTCUSD', 'exchange': 'BITSTAMP', 'nome': 'Bitcoin (BTC)', 'prefix': '$', 'formato': '{:,.0f}', 'url': 'https://br.tradingview.com/chart/?symbol=BITSTAMP%3ABTCUSD'},
        'VIX': {'symbol': 'VIX', 'exchange': 'CBOE', 'nome': 'Índice VIX (Medo)', 'prefix': 'pts', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=CBOE%3AVIX'}
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
                resultados.append({'nome': config['nome'], 'valor': valor_formatado, 'variacao': variacao, 'url': config['url']})
            else:
                resultados.append({'nome': config['nome'], 'valor': 'N/A', 'variacao': 0, 'url': config['url']})
        except:
            resultados.append({'nome': config['nome'], 'valor': 'N/A', 'variacao': 0, 'url': config['url']})
    return resultados

# NOVA FUNÇÃO: Substitui o @st.cache_data para permitir a exibição da Barra Azul
def buscar_ranking_ativos_com_progresso(ativos):
    agora = datetime.now()
    
    # 1. Verifica se já temos os dados no "cérebro" do robô e se são recentes (menos de 590 segundos)
    if 'rank_cache_time' in st.session_state and 'rank_data' in st.session_state:
        if (agora - st.session_state['rank_cache_time']).total_seconds() < 590:
            return st.session_state['rank_data'][0], st.session_state['rank_data'][1]

    # 2. Se não tiver no cache, vamos caçar e mostrar a barra azul!
    tv_local = TvDatafeed()
    lista_rank = []
    rompendo_topo = []
    
    p_bar = st.progress(0)
    status_text = st.empty()
    total_ativos = len(ativos)
    
    for idx, ativo in enumerate(ativos):
        status_text.text(f"Atualizando os dados da pagina, isso pode demorar. Aguarde! ({idx+1}/{total_ativos})")
        p_bar.progress((idx + 1) / total_ativos)
        try:
            df = tv_local.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=4000)
            if df is not None and len(df) >= 2:
                c = df['close']
                hj = c.iloc[-1]
                v_dia = ((hj - c.iloc[-2]) / c.iloc[-2]) * 100 if len(c) >= 2 else 0
                v_sem = ((hj - c.iloc[-6]) / c.iloc[-6]) * 100 if len(c) >= 6 else v_dia
                v_mes = ((hj - c.iloc[-22]) / c.iloc[-22]) * 100 if len(c) >= 22 else v_sem
                v_ano = ((hj - c.iloc[-253]) / c.iloc[-253]) * 100 if len(c) >= 253 else v_mes
                
                lista_rank.append({'Ativo': ativo, 'Preço': hj, 'Dia': v_dia, 'Semana': v_sem, 'Mês': v_mes, 'Ano': v_ano})
                
                max_historica = df['high'].iloc[:-1].max()
                if df['high'].iloc[-1] > max_historica:
                    rompendo_topo.append({'Ativo': ativo, 'Preço': hj, 'Dia': v_dia, 'Semana': v_sem, 'Mês': v_mes, 'Ano': v_ano})
        except: pass
        time.sleep(0.01)
        
    p_bar.empty()
    status_text.empty()
    
    df_rank = pd.DataFrame(lista_rank)
    df_topos = pd.DataFrame(rompendo_topo)
    
    # 3. Salva os dados na memória para não carregar de novo pelos próximos 10 minutos
    st.session_state['rank_data'] = (df_rank, df_topos)
    st.session_state['rank_cache_time'] = agora
    
    return df_rank, df_topos

def formata_moeda_pct(val, is_pct=False):
    if is_pct: return f"+{val:.2f}%" if val > 0 else f"{val:.2f}%"
    return f"R$ {val:.2f}"

def colorir_tabela(row):
    val_float = float(row['Variação (%)'].replace('%', '').replace('+', ''))
    cor = 'lightgreen' if val_float > 0 else 'lightcoral' if val_float < 0 else 'white'
    return [f'color: {cor}'] * len(row)

# ==========================================
# 3. INTERFACE PRINCIPAL
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

# --- TERMÔMETRO MACRO (AUTO-REFRESH 60s) ---
@st.fragment(run_every=60)
def renderizar_termometro():
    st.subheader("🌐 Termômetro Macro Global")
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br)
    texto_status = "🟢 B3 Aberta" if (10 <= agora.hour < 18 and agora.weekday() < 5) else "🔴 B3 Fechada"
    st.caption(f"{texto_status} | Atualização Automática (60s) | Leitura: {agora.strftime('%H:%M:%S')}")

    with st.spinner("Atualizando os dados da pagina, isso pode demorar. Aguarde!"):
        dados_macro = buscar_dados_macro()

    if dados_macro:
        for i in range(0, len(dados_macro), 5):
            cols = st.columns(5)
            for j, col in enumerate(cols):
                if i + j < len(dados_macro):
                    item = dados_macro[i + j]
                    with col:
                        st.metric(label=item['nome'], value=item['valor'], delta=f"{item['variacao']:.2f}%" if item['valor'] != 'N/A' else None)
                        st.markdown(f"<a href='{item['url']}' target='_blank' style='text-decoration: none; font-size: 13px; color: #4da6ff;'>📊 Ver Gráfico</a>", unsafe_allow_html=True)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

renderizar_termometro()
st.divider()

# --- RADAR DE DESTAQUES (AUTO-REFRESH 10 min) ---
@st.fragment(run_every=600)
def renderizar_radar_destaques():
    col_title, col_menu = st.columns([1, 1], vertical_alignment="center")
    with col_title:
        st.subheader("🔥 Radar de Destaques (IBrX + BDRs)")
        fuso_br = timezone(timedelta(hours=-3))
        agora = datetime.now(fuso_br)
        st.caption(f"Rankings atualizados automaticamente (10 min) | Última Varredura: {agora.strftime('%H:%M')}")

    with col_menu:
        horizonte = st.segmented_control("Prazo Analítico", options=["Dia", "Semana", "Mês", "Ano"], default="Dia", label_visibility="collapsed")

    # MUDANÇA: O spinner foi removido daqui e substituído pela barra azul dentro da função
    df_ranking, df_topos = buscar_ranking_ativos_com_progresso(todos_ativos)

    col_altas, col_quedas, col_topos = st.columns(3)

    if not df_ranking.empty:
        df_altas = df_ranking[['Ativo', 'Preço', horizonte]].sort_values(by=horizonte, ascending=False).head(5).copy()
        df_altas.rename(columns={horizonte: 'Variação (%)'}, inplace=True); df_altas['Preço'] = df_altas['Preço'].apply(formata_moeda_pct); df_altas['Variação (%)'] = df_altas['Variação (%)'].apply(lambda x: formata_moeda_pct(x, True))

        df_quedas = df_ranking[['Ativo', 'Preço', horizonte]].sort_values(by=horizonte, ascending=True).head(5).copy()
        df_quedas.rename(columns={horizonte: 'Variação (%)'}, inplace=True); df_quedas['Preço'] = df_quedas['Preço'].apply(formata_moeda_pct); df_quedas['Variação (%)'] = df_quedas['Variação (%)'].apply(lambda x: formata_moeda_pct(x, True))

        with col_altas:
            st.success("### 🚀 Maiores Altas")
            st.dataframe(df_altas.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)
        with col_quedas:
            st.error("### 🩸 Maiores Quedas")
            st.dataframe(df_quedas.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)
        with col_topos:
            st.warning("### 👑 Rompendo Topo Histórico")
            if not df_topos.empty:
                df_topos_fmt = df_topos[['Ativo', 'Preço', horizonte]].sort_values(by=horizonte, ascending=False).copy()
                df_topos_fmt.rename(columns={horizonte: 'Variação (%)'}, inplace=True); df_topos_fmt['Preço'] = df_topos_fmt['Preço'].apply(formata_moeda_pct); df_topos_fmt['Variação (%)'] = df_topos_fmt['Variação (%)'].apply(lambda x: formata_moeda_pct(x, True))
                st.dataframe(df_topos_fmt.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)
            else: st.info("Nenhum ativo rompendo topo agora.")
    else: st.info("Aguardando cotações...")

renderizar_radar_destaques()
st.divider()

# ==========================================
# 🦉 RADAR DO AFTER-MARKET E CONSULTA INDIVIDUAL
# ==========================================
st.subheader("🦉 Como as stocks estão agora? (Radar After-Market)")
st.markdown("Confira a movimentação nos Estados Unidos neste exato momento e antecipe o humor da B3.")

bdr_setup_home = {
    'NVDC34': {'us': 'NVDA', 'exchange': 'NASDAQ'}, 'P2LT34': {'us': 'PLTR', 'exchange': 'NASDAQ'},
    'ROXO34': {'us': 'NU', 'exchange': 'NYSE'}, 'INBR32': {'us': 'INTR', 'exchange': 'NASDAQ'},
    'M1TA34': {'us': 'META', 'exchange': 'NASDAQ'}, 'TSLA34': {'us': 'TSLA', 'exchange': 'NASDAQ'},
    'LILY34': {'us': 'LLY', 'exchange': 'NYSE'}, 'AMZO34': {'us': 'AMZN', 'exchange': 'NASDAQ'},
    'AURA33': {'us': 'AUGO', 'exchange': 'NASDAQ'}, 'GOGL34': {'us': 'GOOGL', 'exchange': 'NASDAQ'},
    'MSFT34': {'us': 'MSFT', 'exchange': 'NASDAQ'}, 'MUTC34': {'us': 'MU', 'exchange': 'NASDAQ'},
    'MELI34': {'us': 'MELI', 'exchange': 'NASDAQ'}, 'C2OI34': {'us': 'COIN', 'exchange': 'NASDAQ'},
    'ORCL34': {'us': 'ORCL', 'exchange': 'NYSE'}, 'M2ST34': {'us': 'MSTR', 'exchange': 'NASDAQ'},
    'A1MD34': {'us': 'AMD', 'exchange': 'NASDAQ'}, 'NFLX34': {'us': 'NFLX', 'exchange': 'NASDAQ'},
    'ITLC34': {'us': 'INTC', 'exchange': 'NASDAQ'}, 'AVGO34': {'us': 'AVGO', 'exchange': 'NASDAQ'},
    'COCA34': {'us': 'KO', 'exchange': 'NYSE'}, 'JBSS32': {'us': 'JBSAY', 'exchange': 'OTC'},
    'AAPL34': {'us': 'AAPL', 'exchange': 'NASDAQ'}, 'XPBR31': {'us': 'XP', 'exchange': 'NASDAQ'},
    'STOC34': {'us': 'STNE', 'exchange': 'NASDAQ'}
}

@st.cache_resource
def get_tv_conn_home():
    return TvDatafeed()

if st.button("🔍 Escanear TUDO no After-Market Agora", type="primary", use_container_width=True):
    ls_after = []
    p_bar_after = st.progress(0); status_after = st.empty(); tv_home = get_tv_conn_home()
    for idx, (bdr, info) in enumerate(bdr_setup_home.items()):
        status_after.text(f"Atualizando os dados da pagina, isso pode demorar. Aguarde! ({idx+1}/{len(bdr_setup_home)})")
        p_bar_after.progress((idx + 1) / len(bdr_setup_home))
        fecho_reg = None; preco_at = None
        try:
            df_reg = tv_home.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_daily, n_bars=2)
            if df_reg is not None and not df_reg.empty and len(df_reg) >= 2: 
                fecho_reg = df_reg['close'].iloc[-2] 
            if fecho_reg:
                df_ext = tv_home.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2, extended_session=True)
                if df_ext is not None and not df_ext.empty: preco_at = df_ext['close'].iloc[-1]
                else:
                    df_fb = tv_home.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2)
                    if df_fb is not None and not df_fb.empty: preco_at = df_fb['close'].iloc[-1]
        except: pass 
        if fecho_reg and preco_at:
            var = ((preco_at / fecho_reg) - 1) * 100; ls_after.append({'BDR (B3)': bdr, 'Ticker EUA': info['us'], 'Fecho Oficial': f"$ {fecho_reg:.2f}", 'Preço After-Market': f"$ {preco_at:.2f}", 'Variação (%)': f"+{var:.2f}%" if var > 0 else f"{var:.2f}%", '_var_raw': var})
        else: ls_after.append({'BDR (B3)': bdr, 'Ticker EUA': info['us'], 'Fecho Oficial': f"$ {fecho_reg:.2f}" if fecho_reg else "S/ Dados", 'Preço After-Market': "Desatualizado", 'Variação (%)': "-", '_var_raw': -999.0})
        time.sleep(0.05)
    p_bar_after.empty(); status_after.empty()
    if ls_after:
        df_after = pd.DataFrame(ls_after).sort_values(by='_var_raw', ascending=False).drop(columns=['_var_raw'])
        def colorir_after(row):
            try:
                if row['Variação (%)'] == "-": return ['color: #a5a5a5'] * len(row)
                val = float(row['Variação (%)'].replace('%', '').replace('+', ''))
                return [f'color: {"#00FF00" if val > 0 else "#ff4d4d"}; font-weight: bold'] * len(row)
            except: return [''] * len(row)
        st.dataframe(df_after.style.apply(colorir_after, axis=1), use_container_width=True, hide_index=True)

st.markdown("#### 🎯 Alguma Stock específica?")

col_sel, col_btn = st.columns([3, 1], vertical_alignment="bottom")

with col_sel:
    ativo_sel = st.selectbox(
        "Selecione a ação americana:", 
        options=sorted(list(bdr_setup_home.keys())), 
        format_func=lambda x: f"{bdr_setup_home[x]['us']} (Ref: {x})"
    )

with col_btn:
    btn_indiv = st.button("🔍 Consultar Ativo", use_container_width=True)

if btn_indiv:
    info = bdr_setup_home[ativo_sel]
    tv_ind = get_tv_conn_home()
    
    f_reg = None
    p_at = None
    p_bdr = None
    v_bdr = None
    
    with st.spinner("Atualizando os dados da pagina, isso pode demorar. Aguarde!"):
        try:
            df_r = tv_ind.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_daily, n_bars=2)
            if df_r is not None and not df_r.empty and len(df_r) >= 2: 
                f_reg = df_r['close'].iloc[-2] 
                
            if f_reg:
                df_e = tv_ind.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2, extended_session=True)
                if df_e is not None and not df_e.empty: p_at = df_e['close'].iloc[-1]
                else:
                    df_fb = tv_ind.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2)
                    if df_fb is not None and not df_fb.empty: p_at = df_fb['close'].iloc[-1]
            
            df_bdr = tv_ind.get_hist(symbol=ativo_sel, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=2)
            if df_bdr is not None and not df_bdr.empty:
                p_bdr = df_bdr['close'].iloc[-1]
                if len(df_bdr) >= 2:
                    v_bdr = ((p_bdr / df_bdr['close'].iloc[-2]) - 1) * 100
        except: pass
        
    if f_reg and p_at:
        v = ((p_at / f_reg) - 1) * 100
        
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ação (EUA)", info['us'])
        c2.metric(f"Cotação {info['us']} (Real-Time)", f"$ {p_at:.2f}", f"{v:.2f}%")
        c3.metric("BDR (Brasil)", ativo_sel)
        
        if p_bdr:
            c4.metric(f"Cotação {ativo_sel} (B3)", f"R$ {p_bdr:.2f}", f"{v_bdr:.2f}%" if v_bdr is not None else None)
        else:
            c4.metric(f"Cotação {ativo_sel} (B3)", "S/ Dados")
        
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        st.info("""
        🕒 **Relógio Oficial das Bolsas Americanas (NASDAQ / NYSE):**
        * **Pré-Market:** 05h00 às 10h30 (Horário de Brasília)
        * **Mercado Regular:** 10h30 às 17h00 (Horário de Brasília)
        * **After-Hours:** 17h00 às 21h00 (Horário de Brasília)
        
        ⚠️ *Atenção: Das 21h00 às 05h00 (Horário de Brasília), o mercado oficial entra em "Zona Morta". Os preços das cotações permanecem congelados no último valor negociado.*
        """)
    else: 
        st.error("Desatualizado. Não foi possível puxar os dados do servidor americano.")

# ==========================================
# 5. ARSENAL, INTELIGÊNCIA E LINKS ÚTEIS
# ==========================================
st.divider()
st.subheader("🛠️ O Seu Arsenal de Ferramentas")
c1, c2, c3 = st.columns(3)
with c1:
    st.info("### 📉 Regressão à Média\nVarreduras de **IFR** e **Canais de Keltner**.")
    st.success("### 📊 Fluxo Institucional\nEncontre defesas de tubarões na **VWAP**.")
with c2:
    st.warning("### 🔥 Seguidores de Tendência\nMonitore o **Setup 9.1** e **Fura-Teto**.")
    st.error("### 📐 Fibo & Smart Money\nOpere com o **Rastreador Fibonacci**.")
with c3:
    st.markdown("<div style='background-color: #2b2b2b; padding: 15px; border-radius: 10px; border-left: 5px solid #a3a3a3;'><h3 style='margin-top: 0;'>🕯️ Price Action</h3>Padrões de Candles em zonas de valor.</div>", unsafe_allow_html=True)

st.divider()
st.subheader("🧭 Inteligência de Mercado & Dados de Ativos")
cl1, cl2, cl3 = st.columns(3)
with cl1:
    st.markdown("#### 📅 Central de Calendários")
    st.link_button("Acessar Calendários", "https://br.investing.com/economic-calendar", use_container_width=True)
with cl2:
    st.markdown("#### 🔍 Rastreadores")
    st.link_button("Filtro Investing", "https://br.investing.com/stock-screener", use_container_width=True)
    st.link_button("Screener TradingView", "https://br.tradingview.com/screener/", use_container_width=True)
with cl3:
    st.markdown("#### 🐋 Smart Money")
    st.link_button("Investing Pro Ideas", "https://br.investing.com/pro/ideas", use_container_width=True)
    st.link_button("HedgeFollow (Fundos)", "https://hedgefollow.com/", use_container_width=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
cl4, cl5, cl6 = st.columns(3)
with cl4:
    st.markdown("#### 📊 Plataformas de Dados")
    st.link_button("StatusInvest", "https://statusinvest.com.br/", use_container_width=True)
with cl5:
    st.markdown("#### 🏢 Raio-X Fundamentalista")
    st.link_button("Fundamentus", "https://www.fundamentus.com.br/", use_container_width=True)
with cl6:
    st.markdown("#### 🌍 Portais Globais")
    st.link_button("Investing.com", "https://br.investing.com/", use_container_width=True)

st.divider()
st.info(aviso_risco)
