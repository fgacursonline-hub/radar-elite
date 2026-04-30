import streamlit as st
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys
import os
import warnings

# ==============================================================================
# ESTRATÉGIA: ICHIMOKU MOMENTUM + FILTRO INSTITUCIONAL
# DESENVOLVIDO PARA: CAÇADORES DE ELITE
# OBJETIVO: Capturar o início de tendências fortes evitando ruídos de lateralização.
# ==============================================================================

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Ichimoku TK Elite", layout="wide", page_icon="☁️")

# --- Verificação de Autenticação ---
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial.")
    st.stop()

# --- Importação de Dependências do Bunker ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao, macro_elite
    from motor_dados import puxar_dados_blindados
    ativos_lista = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)] + list(macro_elite.keys()))))
except ImportError:
    st.error("❌ Erro: Arquivos de configuração não encontrados.")
    st.stop()

# ==============================================================================
# 1. MOTOR MATEMÁTICO (A Lógica por trás do Robô)
# ==============================================================================
def calcular_ichimoku_tk(df, tenkan=20, kijun=60, senkou=120, displacement=30, ema_p=50):
    """
    Explicação Técnica:
    - Tenkan (Conversão): Média de curto prazo. Mede o momentum rápido.
    - Kijun (Base): Média de médio prazo. Representa o equilíbrio do preço.
    - EMA (Filtro): Define a tendência institucional (Bull ou Bear Market).
    """
    if df is None or len(df) < 5: return None
    df = df.copy()
    
    # Padronização para evitar erros de nomes de colunas (High vs high)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    
    # Função Donchian: Calcula o meio do caminho entre a Máxima e a Mínima
    def donchian(len_p):
        return (df['high'].rolling(window=len_p, min_periods=1).max() + 
                df['low'].rolling(window=len_p, min_periods=1).min()) / 2

    # A 'Alma' do Ichimoku
    df['tenkan_sen'] = donchian(tenkan) # Linha Azul: Reage rápido ao preço
    df['kijun_sen'] = donchian(kijun)   # Linha Vermelha: O suporte/resistência real
    
    # O Filtro Institucional: Só caçamos se o preço estiver do lado certo da EMA
    ema_series = ta.ema(df['close'], length=ema_p)
    df['ma_filtro'] = ema_series.bfill() if ema_series is not None else df['close']
    
    # GATILHO 1: O Cruzamento das Médias (TK Cross)
    # Up: Quando a rápida passa a lenta para cima / Down: Quando passa para baixo
    df['tk_cross_up'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['tenkan_sen'].shift(1) <= df['kijun_sen'].shift(1))
    df['tk_cross_down'] = (df['tenkan_sen'] < df['kijun_sen']) & (df['tenkan_sen'].shift(1) >= df['kijun_sen'].shift(1))
    
    # CONDIÇÃO FINAL DE COMPRA (SET-UP CAÇADORES):
    # 1. O cruzamento ocorreu (TK Cross Up)
    # 2. O preço está acima da Média Filtro (Tendência Institucional de Alta)
    # 3. O momentum atual é positivo (Tenkan > Kijun)
    df['entry_long'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['close'] > df['ma_filtro']) & df['tk_cross_up']
    
    # SAÍDA DE EMERGÊNCIA: Perda de momentum (TK Cross Down)
    df['exit_long'] = df['tk_cross_down']
    
    return df

# ==============================================================================
# 2. INTERFACE E EXPLICAÇÃO DIDÁTICA (O que o Aluno vê)
# ==============================================================================
st.title("☁️ Ichimoku Cloud + Filtro Móvel")

# Painel de Teoria para o curso
with st.expander("🎓 METODOLOGIA: Como este Robô toma decisões?"):
    st.markdown("""
    ### 🧱 Os Três Pilares da Entrada
    Para o sistema autorizar uma **🟢 COMPRA**, ele verifica três camadas de segurança:
    
    1. **O Momentum (Tenkan vs Kijun):** A linha rápida deve cruzar a linha média para cima. Isso prova que os compradores ganharam o equilíbrio do mercado.
    2. **O Filtro de Tendência (EMA):** O preço **DEVE** estar acima da média móvel. Não compramos ativos em tendência de baixa macro, mesmo que deem repiques.
    3. **O Fechamento:** O sinal só é válido no fechamento do candle para evitar alarmes falsos.
    
    ---
    ### 🚦 Significado dos Status no Radar
    - **🟢 COMPRA:** Sinal exato gerado no fechamento anterior. Hora de avaliar entrada.
    - **📈 Alta:** O ativo já está subindo. O setup autoriza a continuidade do trade.
    - **📉 Baixa:** O ativo perdeu força de curto prazo. Indica cautela ou saída.
    - **🟡 Neutro:** Ativo sem direção clara ou brigando com a média filtro.
    """)

# Seção de Ajustes
with st.container(border=True):
    st.markdown("#### ⚙️ Calibragem do Setup")
    c1, c2, c3, c4, c5 = st.columns(5)
    p_tenkan = c1.number_input("Tenkan (Rápida):", value=20, min_value=1)
    p_kijun = c2.number_input("Kijun (Média):", value=60, min_value=1)
    p_senkou = c3.number_input("Senkou B (Nuvem):", value=120, min_value=1)
    p_disp = c4.number_input("Deslocamento:", value=30, min_value=0)
    p_ema = c5.number_input("Média de Filtro:", value=50, min_value=1)

aba_radar, aba_test = st.tabs(["📡 Radar de Mercado", "🔬 Raio-X Individual"])

# --- ABA 1: RADAR (ESCANEAMENTO) ---
with aba_radar:
    r1, r2 = st.columns(2)
    lista_r = r1.selectbox("Selecione a Lista:", ["BDRs Elite", "IBrX Seleção", "Cripto/Macros"])
    tempo_r = r2.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1)
    
    if st.button("🚀 Iniciar Escaneamento de Elite", type="primary", use_container_width=True):
        ativos_tr = bdrs_elite if lista_r == "BDRs Elite" else ibrx_selecao if lista_r == "IBrX Seleção" else list(macro_elite.keys())
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_res = []
        p_bar = st.progress(0); s_text = st.empty()
        
        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"Caçador analisando {ativo}...")
            p_bar.progress((idx + 1) / len(ativos_tr))
            try:
                df_cru = puxar_dados_blindados(ativo, tempo_r)
                df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp, p_ema)
                if df is not None:
                    hoje = df.iloc[-1]
                    if hoje['entry_long']: status = "🟢 COMPRA"
                    elif hoje['tenkan_sen'] > hoje['kijun_sen'] and hoje['close'] > hoje['ma_filtro']: status = "📈 Alta"
                    elif hoje['tenkan_sen'] < hoje['kijun_sen']: status = "📉 Baixa"
                    else: status = "🟡 Neutro"
                    
                    ls_res.append({
                        'Ativo': ativo, 'Preço': f"R$ {hoje['close']:.2f}",
                        'Status': status, f'Média ({p_ema})': f"{hoje['ma_filtro']:.2f}"
                    })
            except: pass
        
        s_text.empty(); p_bar.empty()
        if ls_res:
            st.dataframe(pd.DataFrame(ls_res), use_container_width=True, hide_index=True)

# --- ABA 2: RAIO-X (BACKTEST) ---
with aba_test:
    t1, t2 = st.columns(2)
    atv_test = t1.selectbox("Escolha o Ativo para o Raio-X:", ativos_lista)
    tmp_test = t2.selectbox("Tempo Gráfico Backtest:", ['60m', '1d', '1wk'], index=1, key='tk_raiox_aba')
    
    if st.button("📊 Rodar Prova Real", type="primary", use_container_width=True):
        try:
            df_cru = puxar_dados_blindados(atv_test, tmp_test)
            df = calcular_ichimoku_tk(df_cru, p_tenkan, p_kijun, p_senkou, p_disp, p_ema)
            
            if df is not None:
                trades, em_posicao = [], False
                df_b = df.reset_index()
                col_dt = df_b.columns[0]
                
                for i in range(1, len(df_b)):
                    candle = df_b.iloc[i]
                    if not em_posicao and candle['entry_long']:
                        em_posicao, preco_ent, data_ent = True, candle['close'], candle[col_dt]
                    elif em_posicao and candle['exit_long']:
                        lucro = ((candle['close'] / preco_ent) - 1) * 100
                        trades.append({'Entrada': data_ent.strftime('%d/%m/%Y'), 'Saída': candle[col_dt].strftime('%d/%m/%Y'), 'Retorno (%)': lucro})
                        em_posicao = False
                
                if trades:
                    df_res = pd.DataFrame(trades)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Trades Realizados", len(df_res))
                    c2.metric("Assertividade", f"{(len(df_res[df_res['Retorno (%)'] > 0])/len(df_res)*100):.1f}%")
                    c3.metric("Lucro Acumulado", f"{df_res['Retorno (%)'].sum():.2f}%")
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else:
                    st.warning("O sistema não encontrou sinais lucrativos para este ativo com esses parâmetros.")
        except Exception as e:
            st.error(f"Erro no Raio-X: {e}")
