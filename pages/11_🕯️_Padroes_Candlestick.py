import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar de Candlesticks", layout="wide", page_icon="🕯️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

st.title("🕯️ Laboratório de Price Action: Padrões de Candlestick")
st.markdown("Rastreador de reversão baseado puramente na anatomia dos candles de hoje. A psicologia crua dos touros e ursos, sem atraso de indicadores.")

# ==========================================
# 3. DICIONÁRIO DE EXPLICAÇÕES TÁTICAS
# ==========================================
dicionario_padroes = {
    'Doji': {'Tipo': '⚪ Neutro', 'Desc': 'Indecisão extrema. Abertura e fechamento no mesmo preço. O mercado pisou no freio.'},
    'Engolfo de Alta': {'Tipo': '🟢 Alta', 'Desc': 'O candle verde de hoje engole totalmente o corpo do candle vermelho anterior. Força compradora brutal assumindo o controle.'},
    'Engolfo de Baixa': {'Tipo': '🔴 Baixa', 'Desc': 'O candle vermelho de hoje engole o verde anterior. Os ursos aniquilaram as defesas compradoras.'},
    'Harami de Alta': {'Tipo': '🟢 Alta', 'Desc': 'Mulher grávida de alta. O corpo verde de hoje está contido no vermelho de ontem. A pressão de venda estancou.'},
    'Harami de Baixa': {'Tipo': '🔴 Baixa', 'Desc': 'Mulher grávida de baixa. A exaustão da compra. O mercado parou de subir repentinamente.'},
    'Martelo': {'Tipo': '🟢 Alta', 'Desc': 'Rejeição de fundo. Um longo pavio inferior mostra que os ursos bateram, mas os touros devolveram com juros.'},
    'Martelo Invertido': {'Tipo': '🟢 Alta', 'Desc': 'Tentativa de alta em um fundo. Os compradores testaram as máximas, deixando um longo pavio para cima.'},
    'Estrela Cadente': {'Tipo': '🔴 Baixa', 'Desc': 'Rejeição de topo (Sniper). Os touros tentaram subir, mas levaram um tiro dos ursos e devolveram tudo (pavio longo).'},
    'Enforcado': {'Tipo': '🔴 Baixa', 'Desc': 'Idêntico ao martelo, mas no TOPO de uma tendência. Mostra que o chão dos compradores começou a ceder.'},
    'Estrela da Manhã': {'Tipo': '🟢 Alta', 'Desc': 'Padrão de 3 dias. O sol nascendo: Queda, indecisão com gap, e um forte salto comprador no terceiro dia.'},
    'Estrela da Noite': {'Tipo': '🔴 Baixa', 'Desc': 'Padrão de 3 dias. O anoitecer: Alta forte, indecisão no topo, e uma paulada de queda no terceiro dia.'},
    'Linha de Perfuração': {'Tipo': '🟢 Alta', 'Desc': 'O preço abriu caindo feio, mas os touros perfuraram a queda e fecharam acima da metade do candle de ontem.'},
    'Cinturão de Alta': {'Tipo': '🟢 Alta', 'Desc': 'Abre na mínima do dia e só sobe, fechando forte. Um trator comprador triturando vendas.'},
    'Gap de Fuga de Alta': {'Tipo': '🟢 Alta', 'Desc': 'Voadora nos ursos! O mercado vinha caindo, mas abre em um Gap de Alta gigante e sobe rasgando (Kicker).'},
    'Gap de Fuga de Baixa': {'Tipo': '🔴 Baixa', 'Desc': 'Rasteira nos touros! O mercado vinha subindo, mas abre em Gap de Baixa rasgando as defesas e despencando (Kicker).'}
}

# ==========================================
# 4. MOTOR DE TRADUÇÃO (PINESCRIPT -> PYTHON)
# ==========================================
def escanear_padroes(df, trend=5, dojiSize=0.05):
    if df.empty or len(df) < 15:
        return []
    
    # Prepara as Séries OHLC (Hoje, Ontem e Anteontem)
    O = df['Open']
    C = df['Close']
    H = df['High']
    L = df['Low']
    
    O1, C1, H1, L1 = O.shift(1), C.shift(1), H.shift(1), L.shift(1)
    O2, C2, H2, L2 = O.shift(2), C.shift(2), H.shift(2), L.shift(2)
    O_trend = O.shift(trend) # Referência de tendência de 5 barras atrás
    
    # ------------------------------------
    # FÓRMULAS MATEMÁTICAS DOS CANDLES
    # ------------------------------------
    padroes_hoje = []
    
    doji = (abs(O - C) <= (H - L) * dojiSize).iloc[-1]
    
    bearHarami = ((C1 > O1) & (O > C) & (O <= C1) & (O1 <= C) & ((O - C) < (C1 - O1)) & (O_trend < O)).iloc[-1]
    bullHarami = ((O1 > C1) & (C > O) & (C <= O1) & (C1 <= O) & ((C - O) < (O1 - C1)) & (O_trend > O)).iloc[-1]
    
    bearEng = ((C1 > O1) & (O > C) & (O >= C1) & (O1 >= C) & ((O - C) > (C1 - O1)) & (O_trend < O)).iloc[-1]
    bullEng = ((O1 > C1) & (C > O) & (C >= O1) & (C1 >= O) & ((C - O) > (O1 - C1)) & (O_trend > O)).iloc[-1]
    
    piercing = ((C1 < O1) & (O < L1) & (C > C1 + ((O1 - C1) / 2)) & (C < O1) & (O_trend > O)).iloc[-1]
    
    lower = L.rolling(10).min().shift(1)
    bullBelt = ((L == O) & (O < lower) & (O < C) & (C > ((H1 - L1) / 2) + L1) & (O_trend > O)).iloc[-1]
    
    bullKick = ((O1 > C1) & (O >= O1) & (C > O) & (O_trend > O)).iloc[-1]
    bearKick = ((O1 < C1) & (O <= O1) & (C <= O) & (O_trend < O)).iloc[-1]
    
    hangingMan = (((H - L) > 4 * abs(O - C)) & (((C - L) / (0.001 + H - L)) >= 0.75) & (((O - L) / (0.001 + H - L)) >= 0.75) & (O_trend < O) & (H1 < O) & (H2 < O)).iloc[-1]
    
    min_O1_C1 = np.minimum(O1, C1)
    max_O1_C1 = np.maximum(O1, C1)
    
    eveningStar = ((C2 > O2) & (min_O1_C1 > C2) & (O < min_O1_C1) & (C < O)).iloc[-1]
    morningStar = ((C2 < O2) & (max_O1_C1 < C2) & (O > max_O1_C1) & (C > O)).iloc[-1]
    
    max_O_C = np.maximum(O, C)
    min_C_O = np.minimum(C, O)
    shootingStar = ((O1 < C1) & (O > C1) & ((H - max_O_C) >= abs(O - C) * 3) & ((min_C_O - L) <= abs(O - C))).iloc[-1]
    
    hammer = (((H - L) > 3 * abs(O - C)) & (((C - L) / (0.001 + H - L)) > 0.6) & (((O - L) / (0.001 + H - L)) > 0.6)).iloc[-1]
    invHammer = (((H - L) > 3 * abs(O - C)) & (((H - C) / (0.001 + H - L)) > 0.6) & (((H - O) / (0.001 + H - L)) > 0.6)).iloc[-1]

    # Coleta tudo o que for "True" no último candle do gráfico
    if doji: padroes_hoje.append('Doji')
    if bearHarami: padroes_hoje.append('Harami de Baixa')
    if bullHarami: padroes_hoje.append('Harami de Alta')
    if bearEng: padroes_hoje.append('Engolfo de Baixa')
    if bullEng: padroes_hoje.append('Engolfo de Alta')
    if piercing: padroes_hoje.append('Linha de Perfuração')
    if bullBelt: padroes_hoje.append('Cinturão de Alta')
    if bullKick: padroes_hoje.append('Gap de Fuga de Alta')
    if bearKick: padroes_hoje.append('Gap de Fuga de Baixa')
    if hangingMan: padroes_hoje.append('Enforcado')
    if eveningStar: padroes_hoje.append('Estrela da Noite')
    if morningStar: padroes_hoje.append('Estrela da Manhã')
    if shootingStar: padroes_hoje.append('Estrela Cadente')
    if hammer: padroes_hoje.append('Martelo')
    if invHammer: padroes_hoje.append('Martelo Invertido')
    
    return padroes_hoje

# ==========================================
# 5. INTERFACE DO SCANNER
# ==========================================
with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        lista_alvo = st.selectbox("Selecione a Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
    with col2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x])
    with col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_radar = st.button("🔍 Escanear Price Action Agora", type="primary", use_container_width=True)

if btn_radar:
    ativos = bdrs_elite if lista_alvo == "BDRs Elite" else ibrx_selecao if lista_alvo == "IBrX Seleção" else bdrs_elite + ibrx_selecao
    ativos = sorted(list(set([a.replace('.SA', '') for a in ativos])))
    
    intervalo_tv = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}[tempo_grafico]
    
    resultados = []
    p_bar = st.progress(0)
    s_text = st.empty()
    
    # ------------------------------------
    # VARREDURA SILENCIOSA
    # ------------------------------------
    for i, ativo in enumerate(ativos):
        s_text.text(f"Auditando velas: {ativo} ({i+1}/{len(ativos)})")
        p_bar.progress((i + 1) / len(ativos))
        
        try:
            # Puxa poucas barras só para ler os últimos dias rapidamente
            df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=20)
            if df is not None and not df.empty:
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # Executa o Motor de Tradução
                padroes_encontrados = escanear_padroes(df)
                
                if padroes_encontrados:
                    cotacao = df['Close'].iloc[-1]
                    for padrao in padroes_encontrados:
                        # Limpa redundâncias (ex: não avisa que é Doji se for um Estrela da Manhã que tem um Doji no meio)
                        if padrao == 'Doji' and len(padroes_encontrados) > 1: continue
                        
                        info = dicionario_padroes[padrao]
                        resultados.append({
                            'Ativo': ativo,
                            'Cotação': f"R$ {cotacao:.2f}",
                            'Padrão Formado': padrao,
                            'Direção': info['Tipo'],
                            'Leitura Psicológica': info['Desc']
                        })
        except Exception as e:
            pass
        time.sleep(0.01) # Pequena pausa para a API
        
    p_bar.empty(); s_text.empty()
    
    # ------------------------------------
    # EXIBIÇÃO DE RESULTADOS
    # ------------------------------------
    st.divider()
    if resultados:
        st.success(f"🎯 Varredura concluída! Encontramos **{len(resultados)}** padrões sendo desenhados no fechamento atual.")
        df_res = pd.DataFrame(resultados)
        
        # Função para colorir a tabela baseada no emoji da direção
        def colorir_direcao(val):
            if isinstance(val, str):
                if '🟢' in val:
                    return 'color: #00FF00; font-weight: bold'
                elif '🔴' in val:
                    return 'color: #FF4D4D; font-weight: bold'
                elif '⚪' in val:
                    return 'color: #d3d3d3; font-weight: bold'
            return ''

        try:
            styled_df = df_res.style.map(colorir_direcao, subset=['Direção'])
        except AttributeError:
            styled_df = df_res.style.applymap(colorir_direcao, subset=['Direção'])

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("🤷‍♂️ Nenhum padrão clássico de Candlestick foi detectado no último candle dos ativos mapeados.")
