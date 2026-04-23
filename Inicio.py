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

# --- INJEÇÃO CSS PARA CORREÇÃO DO TERMÔMETRO (OS 3 PONTINHOS) ---
st.markdown("""
    <style>
    /* Reduz o tamanho do número principal para caber na coluna */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    /* Reduz ligeiramente o nome do ativo para ficar proporcional */
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
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
        'BRENT': {'symbol': 'UKOIL', 'exchange': 'TVC', 'nome': 'Petróleo Brent', 'prefix': '$', 'formato': '{:.2f}', 'url': 'https://br.tradingview.com/chart/?symbol=TVC%3AUKOIL'},
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

@st.cache_data(ttl=900)
def buscar_ranking_ativos(ativos):
    tv_local = TvDatafeed()
    lista_rank = []
    rompendo_topo = []
    
    for ativo in ativos:
        try:
            df = tv_local.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=4000)
            if df is not None and len(df) >= 2:
                c = df['close']
                hj = c.iloc[-1]
                
                v_dia = ((hj - c.iloc[-2]) / c.iloc[-2]) * 100 if len(c) >= 2 else 0
                v_sem = ((hj - c.iloc[-6]) / c.iloc[-6]) * 100 if len(c) >= 6 else v_dia
                v_mes = ((hj - c.iloc[-22]) / c.iloc[-22]) * 100 if len(c) >= 22 else v_sem
                v_ano = ((hj - c.iloc[-253]) / c.iloc[-253]) * 100 if len(c) >= 253 else v_mes
                
                lista_rank.append({
                    'Ativo': ativo, 'Preço': hj, 
                    'Dia': v_dia, 'Semana': v_sem, 'Mês': v_mes, 'Ano': v_ano
                })
                
                max_historica = df['high'].iloc[:-1].max()
                if df['high'].iloc[-1] > max_historica:
                    rompendo_topo.append({
                        'Ativo': ativo, 'Preço': hj, 
                        'Dia': v_dia, 'Semana': v_sem, 'Mês': v_mes, 'Ano': v_ano
                    })
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
    for i in range(0, len(dados_macro), 5):
        cols = st.columns(5)
        for j, col in enumerate(cols):
            if i + j < len(dados_macro):
                item = dados_macro[i + j]
                with col:
                    st.metric(
                        label=item['nome'], 
                        value=item['valor'], 
                        delta=f"{item['variacao']:.2f}%" if item['valor'] != 'N/A' else None
                    )
                    st.markdown(f"<a href='{item['url']}' target='_blank' style='text-decoration: none; font-size: 13px; color: #4da6ff;'>📊 Ver Gráfico</a>", unsafe_allow_html=True)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

st.divider()

# ==========================================
# 4. PAINEL DE DESTAQUES (ALTAS, QUEDAS E TOPOS)
# ==========================================
col_title, col_menu = st.columns([1, 1], vertical_alignment="center")

with col_title:
    st.subheader("🔥 Radar de Destaques (IBrX + BDRs)")
    st.markdown("Monitoramento das maiores forças e fraquezas do mercado de capitais brasileiro.")

with col_menu:
    horizonte = st.segmented_control(
        "Prazo Analítico",
        options=["Dia", "Semana", "Mês", "Ano"],
        default="Dia",
        label_visibility="collapsed" 
    )

with st.spinner("Varrendo o mercado em busca de oportunidades extremas..."):
    df_ranking, df_topos = buscar_ranking_ativos(todos_ativos)

col_altas, col_quedas, col_topos = st.columns(3)

if not df_ranking.empty:
    df_altas = df_ranking[['Ativo', 'Preço', horizonte]].sort_values(by=horizonte, ascending=False).head(5).copy()
    df_altas.rename(columns={horizonte: 'Variação (%)'}, inplace=True)
    df_altas['Preço'] = df_altas['Preço'].apply(lambda x: formata_moeda_pct(x))
    df_altas['Variação (%)'] = df_altas['Variação (%)'].apply(lambda x: formata_moeda_pct(x, True))

    df_quedas = df_ranking[['Ativo', 'Preço', horizonte]].sort_values(by=horizonte, ascending=True).head(5).copy()
    df_quedas.rename(columns={horizonte: 'Variação (%)'}, inplace=True)
    df_quedas['Preço'] = df_quedas['Preço'].apply(lambda x: formata_moeda_pct(x))
    df_quedas['Variação (%)'] = df_quedas['Variação (%)'].apply(lambda x: formata_moeda_pct(x, True))

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
            df_topos_fmt.rename(columns={horizonte: 'Variação (%)'}, inplace=True)
            df_topos_fmt['Preço'] = df_topos_fmt['Preço'].apply(lambda x: formata_moeda_pct(x))
            df_topos_fmt['Variação (%)'] = df_topos_fmt['Variação (%)'].apply(lambda x: formata_moeda_pct(x, True))
            st.dataframe(df_topos_fmt.style.apply(colorir_tabela, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ativo está a romper o topo histórico hoje.")
else:
    st.info("Aguardando cotações para gerar o ranking.")

st.divider()
# ==========================================
# 🦉 RADAR DO AFTER-MARKET E CONSULTA INDIVIDUAL
# ==========================================
st.subheader("🦉 Como as stocks estão agora? (Radar After-Market)")
st.markdown("Confira a movimentação nos Estados Unidos neste exato momento e antecipe o humor da B3.")

# Dicionário resumido (Tirado do clique do botão para ser usado em ambos os módulos)
bdr_setup_home = {
    'NVDC34': {'us': 'NVDA', 'exchange': 'NASDAQ'},
    'P2LT34': {'us': 'PLTR', 'exchange': 'NASDAQ'},
    'ROXO34': {'us': 'NU', 'exchange': 'NYSE'},
    'INBR32': {'us': 'INTR', 'exchange': 'NASDAQ'},
    'M1TA34': {'us': 'META', 'exchange': 'NASDAQ'},
    'TSLA34': {'us': 'TSLA', 'exchange': 'NASDAQ'},
    'LILY34': {'us': 'LLY', 'exchange': 'NYSE'},
    'AMZO34': {'us': 'AMZN', 'exchange': 'NASDAQ'},  
    'AURA33': {'us': 'AUGO', 'exchange': 'NASDAQ'},       
    'GOGL34': {'us': 'GOOGL', 'exchange': 'NASDAQ'}, 
    'MSFT34': {'us': 'MSFT', 'exchange': 'NASDAQ'},  
    'MUTC34': {'us': 'MU', 'exchange': 'NASDAQ'},    
    'MELI34': {'us': 'MELI', 'exchange': 'NASDAQ'},
    'C2OI34': {'us': 'COIN', 'exchange': 'NASDAQ'},
    'ORCL34': {'us': 'ORCL', 'exchange': 'NYSE'},
    'M2ST34': {'us': 'MSTR', 'exchange': 'NASDAQ'},  
    'A1MD34': {'us': 'AMD', 'exchange': 'NASDAQ'},    
    'NFLX34': {'us': 'NFLX', 'exchange': 'NASDAQ'},  
    'ITLC34': {'us': 'INTC', 'exchange': 'NASDAQ'},    
    'AVGO34': {'us': 'AVGO', 'exchange': 'NASDAQ'},  
    'COCA34': {'us': 'KO', 'exchange': 'NYSE'},       
    'JBSS32': {'us': 'JBSAY', 'exchange': 'OTC'},
    'AAPL34': {'us': 'AAPL', 'exchange': 'NASDAQ'},
    'XPBR31': {'us': 'XP', 'exchange': 'NASDAQ'},
    'STOC34': {'us': 'STNE', 'exchange': 'NASDAQ'}
}

@st.cache_resource
def get_tv_conn_home():
    return TvDatafeed()

if st.button("🔍 Escanear TUDO no After-Market Agora", type="primary", use_container_width=True):
    ls_after = []
    p_bar_after = st.progress(0)
    status_after = st.empty()
    
    tv_home = get_tv_conn_home()
        
    for idx, (bdr, info) in enumerate(bdr_setup_home.items()):
        status_after.text(f"Corujando {info['us']} no mercado internacional... ({idx+1}/{len(bdr_setup_home)})")
        p_bar_after.progress((idx + 1) / len(bdr_setup_home))
        
        fecho_regular = None
        preco_atual = None
        
        try:
            df_reg = tv_home.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_daily, n_bars=2)
            if df_reg is not None and not df_reg.empty:
                fecho_regular = df_reg['close'].iloc[-1]
                
            if fecho_regular is not None:
                df_ext = tv_home.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2, extended_session=True)
                
                if df_ext is not None and not df_ext.empty:
                    preco_atual = df_ext['close'].iloc[-1]
                else:
                    df_fallback = tv_home.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2)
                    if df_fallback is not None and not df_fallback.empty:
                        preco_atual = df_fallback['close'].iloc[-1]
        except:
            pass 
            
        if fecho_regular is not None and preco_atual is not None:
            var_pct = ((preco_atual / fecho_regular) - 1) * 100
            str_after = f"$ {preco_atual:.2f}"
            str_var = f"+{var_pct:.2f}%" if var_pct > 0 else f"{var_pct:.2f}%"
            raw_var = var_pct
            str_fecho = f"$ {fecho_regular:.2f}"
        else:
            str_after = "Desatualizado"
            str_var = "-"
            raw_var = -999.0 
            str_fecho = f"$ {fecho_regular:.2f}" if fecho_regular is not None else "S/ Dados"
            
        ls_after.append({
            'BDR (B3)': bdr,
            'Ticker EUA': info['us'],
            'Fecho Oficial': str_fecho,
            'Preço After-Market': str_after,
            'Variação (%)': str_var,
            '_var_raw': raw_var
        })
        time.sleep(0.05)
        
    p_bar_after.empty()
    status_after.empty()
    
    if ls_after:
        df_after = pd.DataFrame(ls_after)
        df_after = df_after.sort_values(by='_var_raw', ascending=False).drop(columns=['_var_raw'])
        
        def colorir_after(row):
            try:
                if row['Variação (%)'] == "-": return ['color: #a5a5a5'] * len(row)
                val = float(row['Variação (%)'].replace('%', '').replace('+', ''))
                if val > 0: return ['color: #00FF00; font-weight: bold'] * len(row)
                elif val < 0: return ['color: #ff4d4d; font-weight: bold'] * len(row)
            except: pass
            return [''] * len(row)
            
        st.dataframe(df_after.style.apply(colorir_after, axis=1), use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum dado capturado no momento.")

# --- NOVO BLOCO: VERIFICAÇÃO INDIVIDUAL DE STOCK ---
st.markdown("---")
st.markdown("#### 🎯 Alguma Stock específica?")

col_sel, col_btn = st.columns([3, 1], vertical_alignment="bottom")
with col_sel:
    ativo_escolhido = st.selectbox(
        "Selecione a ação americana:", 
        options=list(bdr_setup_home.keys()), 
        format_func=lambda x: f"{bdr_setup_home[x]['us']} (Ref: {x})"
    )
with col_btn:
    btn_indiv = st.button("🔍 Consultar Ativo", use_container_width=True)

if btn_indiv:
    info = bdr_setup_home[ativo_escolhido]
    tv_indiv = get_tv_conn_home()
    
    fecho_regular = None
    preco_atual = None
    
    with st.spinner(f"Puxando cotação de {info['us']}..."):
        try:
            df_reg = tv_indiv.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_daily, n_bars=2)
            if df_reg is not None and not df_reg.empty:
                fecho_regular = df_reg['close'].iloc[-1]
                
            if fecho_regular is not None:
                df_ext = tv_indiv.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2, extended_session=True)
                if df_ext is not None and not df_ext.empty:
                    preco_atual = df_ext['close'].iloc[-1]
                else:
                    df_fallback = tv_indiv.get_hist(symbol=info['us'], exchange=info['exchange'], interval=Interval.in_15_minute, n_bars=2)
                    if df_fallback is not None and not df_fallback.empty:
                        preco_atual = df_fallback['close'].iloc[-1]
        except Exception as e:
            pass
            
    if fecho_regular is not None and preco_atual is not None:
        var_pct = ((preco_atual / fecho_regular) - 1) * 100
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ação (US)", info['us'])
        c2.metric("BDR Correspondente", ativo_escolhido)
        # O delta já colore automaticamente de verde (subida) ou vermelho (queda)
        c3.metric("Preço Atual", f"$ {preco_atual:.2f}", f"{var_pct:.2f}%")
    else:
        st.error("Desatualizado. O mercado americano não retornou os dados em tempo real.")

# ==========================================
# 5. O SEU ARSENAL E LINKS ÚTEIS
# ==========================================
st.divider()
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

# --- NOVA SEÇÃO DE INTELIGÊNCIA (EXPANDIDA) ---
st.subheader("🧭 Inteligência de Mercado & Dados de Ativos")

cl1, cl2, cl3 = st.columns(3)

with cl1:
    st.markdown("#### 📅 Central de Calendários")
    st.link_button("Acessar Calendários", "https://br.investing.com/economic-calendar", use_container_width=True)
    st.caption("Econômico, Feriados, Balanços e Resultados, Dividendos, Desdobramento, IPO e Contratos Futuros.")

with cl2:
    st.markdown("#### 🔍 Rastreadores")
    st.link_button("Filtro | Comparador de Ações", "https://br.investing.com/stock-screener", use_container_width=True)
    st.link_button("Screener TradingView", "https://br.tradingview.com/screener/", use_container_width=True)
    st.caption("Filtre o mercado através de múltiplos indicadores técnicos e fundamentalistas.")

with cl3:
    st.markdown("#### 🐋 Smart Money")
    st.link_button("Investing Pro Ideas", "https://br.investing.com/pro/ideas", use_container_width=True)
    st.link_button("HedgeFollow (Fundos)", "https://hedgefollow.com/", use_container_width=True)
    st.caption("Investidores famosos, hedge funds e assessores de investimento.")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

cl4, cl5, cl6 = st.columns(3)

with cl4:
    st.markdown("#### 📊 Plataformas de Dados")
    st.link_button("StatusInvest", "https://statusinvest.com.br/", use_container_width=True)
    st.link_button("Investidor10", "https://investidor10.com.br/", use_container_width=True)

with cl5:
    st.markdown("#### 🏢 Raio-X Fundamentalista")
    st.link_button("Fundamentus", "https://www.fundamentus.com.br/", use_container_width=True)
    st.link_button("Oceans14", "https://www.oceans14.com.br/", use_container_width=True)

with cl6:
    st.markdown("#### 🌍 Portais Globais")
    st.link_button("Investing.com", "https://br.investing.com/", use_container_width=True)
    st.link_button("Google Finance", "https://www.google.com/finance/", use_container_width=True)


# ==========================================
# 6. RADAR DE NOTÍCIAS MULTI-FONTE
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
        
        palavras_proibidas = ['futebol', 'copa', 'assistir', 'corinthians', 'vasco', 'palmeiras', 'flamengo', 'brasileirão', 'fofoca', 'bbb', 'novela', 'filme']
        
        for item in root.findall('./channel/item'): 
            titulo = item.find('title').text
            link = item.find('link').text
            
            titulo_lower = titulo.lower()
            if any(palavra in titulo_lower for palavra in palavras_proibidas):
                continue
                
            itens.append({"titulo": titulo, "link": link})
            if len(itens) >= 8: break
                
        return itens
    except: return None

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

# ==========================================
# 7. RODAPÉ DE SEGURANÇA E RESPONSABILIDADE
# ==========================================
st.divider()
st.info(aviso_risco)
