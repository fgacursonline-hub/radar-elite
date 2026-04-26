import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# 1. SEGURANÇA E BLOQUEIO
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

# 2. CONEXÃO E LISTAS (Padrão de Elite)
@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_intervalo = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly, '1mo': Interval.in_monthly}
tradutor_periodo_nome = {
    '1mo': '1 Mês',
    '3mo': '3 Meses',
    '6mo': '6 Meses',
    '1y': '1 Ano',
    '2y': '2 Anos',
    '5y': '5 Anos',
    'max': 'Máximo'
}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# 3. INTERFACE DE ABAS
# Criamos duas colunas: a primeira bem larga (para o título) e a segunda mais estreita (para o botão)
col_titulo, col_botao = st.columns([4, 1])

with col_titulo:
    st.title("🚀 Cruzamento de Médias")

with col_botao:
    # Esse espaço em branco alinha o botão mais para baixo, para ficar na mesma altura do texto do título
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_ifr", use_container_width=True)

st.info("📊 **Estratégia (Trend Following Clássico):** O robô realiza a compra no exato momento em que a Média Curta (rápida) cruza a Média Longa (lenta) para cima, utilizando as configurações e preços de referência (Fechamento, Máxima, etc) definidos por você. Esse setup busca surfar grandes pernadas de alta. \n\n⚠️ **Aviso:** É uma tática atrasada (Lagging Indicator), você nunca vai comprar o fundo exato, mas terá a confirmação estatística de que a tendência virou ao seu favor.")

aba_padrao, aba_pm, aba_stop, aba_individual, aba_futuros = st.tabs([
    "📡 Radar Padrão", "📡 Radar (PM)", "🛡️ Alvo & Stop", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

# ==========================================
# ABA 1: RADAR PADRÃO (CRUZAMENTO DINÂMICO & ALVO)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Cruzamento Universal & Alvo Fixo)")
    st.markdown("O robô compra no exato momento em que a Média Curta cruza a Média Longa para cima, usando a configuração e os preços de referência que você definir.")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_cm = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="cm_lista")
        ativos_cm = bdrs_elite if lista_cm == "BDRs Elite" else ibrx_selecao if lista_cm == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_cm = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="cm_per")
        capital_cm = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="cm_cap")
    with cp2:
        tipo_media_cm = st.selectbox("Tipo de Média:", ["Exponencial (EMA)", "Aritmética (SMA)", "Welles Wilder (RMA)"], index=0, key="cm_tipo")
        
        # Colunas internas para organizar Período + Fonte lado a lado com Dicas
        c_curta1, c_curta2 = st.columns(2)
        curta_cm = c_curta1.number_input("Período Curta:", min_value=2, max_value=200, value=16, step=1, key="cm_curta")
        fonte_curta_pt = c_curta2.selectbox("Fonte (Curta):", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=1, key="cm_fcurta") # Index 1 = Máxima por padrão
        c_curta2.caption("🎯 IDEAL: MÁXIMA")
        
        c_longa1, c_longa2 = st.columns(2)
        longa_cm = c_longa1.number_input("Período Longa:", min_value=3, max_value=200, value=42, step=1, key="cm_longa")
        fonte_longa_pt = c_longa2.selectbox("Fonte (Longa):", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=0, key="cm_flonga") # Index 0 = Fechamento por padrão
        c_longa2.caption("🎯 IDEAL: FECHAMENTO")
        
        # Tradutor interno para a biblioteca matemática
        mapa_fontes = {"Fechamento": "Close", "Máxima": "High", "Mínima": "Low", "Abertura": "Open"}
        fonte_curta = mapa_fontes[fonte_curta_pt]
        fonte_longa = mapa_fontes[fonte_longa_pt]
        
    with cp3:
        alvo_cm = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="cm_alvo")
        # ALTERAÇÃO AQUI: Adicionado '1mo' na lista e 'Mensal' no dicionário
        tempo_cm = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x], key="cm_tmp")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 

    if curta_cm >= longa_cm:
        st.warning("⚠️ Atenção: O período da Média Curta deve ser menor que o da Média Longa para o cruzamento fazer sentido.")

    btn_iniciar_cm = st.button("🚀 Iniciar Varredura de Cruzamentos", type="primary", use_container_width=True, key="cm_btn")

    if btn_iniciar_cm and curta_cm < longa_cm:
        if tempo_cm == '15m' and periodo_cm not in ['1mo', '3mo']: periodo_cm = '60d'
        elif tempo_cm == '60m' and periodo_cm in ['5y', 'max']: periodo_cm = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_cm, Interval.in_daily)
        alvo_dec = alvo_cm / 100

        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_cm):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Analisando Cruzamentos ({curta_cm}x{longa_cm}): {ativo} ({idx+1}/{len(ativos_cm)})")
            p_bar.progress((idx + 1) / len(ativos_cm))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                # --- CÁLCULO DAS MÉDIAS COM FONTE DINÂMICA ---
                if tipo_media_cm == "Exponencial (EMA)":
                    df_full['Curta'] = ta.ema(df_full[fonte_curta], length=curta_cm)
                    df_full['Longa'] = ta.ema(df_full[fonte_longa], length=longa_cm)
                elif tipo_media_cm == "Aritmética (SMA)":
                    df_full['Curta'] = ta.sma(df_full[fonte_curta], length=curta_cm)
                    df_full['Longa'] = ta.sma(df_full[fonte_longa], length=longa_cm)
                else: 
                    df_full['Curta'] = ta.rma(df_full[fonte_curta], length=curta_cm)
                    df_full['Longa'] = ta.rma(df_full[fonte_longa], length=longa_cm)
                
                df_full['Curta_Prev'] = df_full['Curta'].shift(1)
                df_full['Longa_Prev'] = df_full['Longa'].shift(1)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_cm == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_cm == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_cm == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_cm == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_cm == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_cm == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_cm == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                min_price_in_trade = 0.0

                for i in range(1, len(df_back)):
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade:
                            min_price_in_trade = df_back['Low'].iloc[i]
                        
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_cm) * alvo_dec, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            em_pos = False
                            continue

                    cruzou_cima = (df_back['Curta'].iloc[i] > df_back['Longa'].iloc[i]) and (df_back['Curta_Prev'].iloc[i] <= df_back['Longa_Prev'].iloc[i])
                    
                    if cruzou_cima and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i] 
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_dec)

                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    queda_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_cm in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{queda_max:.2f}%",
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    cruzou_hoje = (df_full['Curta'].iloc[-1] > df_full['Longa'].iloc[-1]) and (df_full['Curta_Prev'].iloc[-1] <= df_full['Longa_Prev'].iloc[-1])
                    if cruzou_hoje:
                        nome_m = tipo_media_cm.split()[0]
                        # Mostra no cabeçalho qual foi a fonte usada (ex: EMA 16 (Máx))
                        col_curta = f"{nome_m} {curta_cm} ({fonte_curta_pt[:3]})"
                        col_longa = f"{nome_m} {longa_cm} ({fonte_longa_pt[:3]})"
                        ls_sinais.append({
                            'Ativo': ativo, 
                            'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 
                            col_curta: f"{df_full['Curta'].iloc[-1]:.2f}", 
                            col_longa: f"{df_full['Longa'].iloc[-1]:.2f}"
                        })

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    ls_resumo.append({
                        'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })
            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty()
        p_bar.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.subheader(f"🚀 Cruzamentos de Alta Hoje ({tipo_media_cm.split()[0]} {curta_cm}x{longa_cm})")
        if len(ls_sinais) > 0: 
            st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else: 
            st.info(f"Nenhum ativo apresentou cruzamento ({curta_cm}x{longa_cm}) para cima no último candle.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if len(ls_abertos) > 0:
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: 
            st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_cm, periodo_cm)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: 
            st.warning("Nenhuma operação finalizada.")
# ESPAÇO PARA AS PRÓXIMAS ABAS
# ==========================================
# ABA 2: RADAR PM (CRUZAMENTO COM PREÇO MÉDIO)
# ==========================================
with aba_pm:
    st.subheader("📡 Radar PM (Aportes em Novos Cruzamentos)")
    st.markdown("Se o alvo não for atingido e as médias cruzarem para baixo, o robô aguarda. Quando cruzarem para cima **novamente**, ele faz um novo aporte (PM), baixando o alvo.")
    
    cp_pm1, cp_pm2, cp_pm3 = st.columns(3)
    with cp_pm1:
        lista_cmp = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="cmp_lista")
        ativos_cmp = bdrs_elite if lista_cmp == "BDRs Elite" else ibrx_selecao if lista_cmp == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_cmp = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="cmp_per")
        capital_cmp = st.number_input("Aporte por Cruzamento (R$):", value=10000.0, step=1000.0, key="cmp_cap")
    with cp_pm2:
        tipo_media_cmp = st.selectbox("Tipo de Média:", ["Exponencial (EMA)", "Aritmética (SMA)", "Welles Wilder (RMA)"], index=0, key="cmp_tipo")
        
        c_pcurta1, c_pcurta2 = st.columns(2)
        curta_cmp = c_pcurta1.number_input("Período Curta:", min_value=2, max_value=200, value=16, step=1, key="cmp_curta")
        fonte_curta_pt_pm = c_pcurta2.selectbox("Fonte (Curta):", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=1, key="cmp_fcurta") 
        c_pcurta2.caption("🎯 IDEAL: MÁXIMA")
        
        c_plonga1, c_plonga2 = st.columns(2)
        longa_cmp = c_plonga1.number_input("Período Longa:", min_value=3, max_value=200, value=42, step=1, key="cmp_longa")
        fonte_longa_pt_pm = c_plonga2.selectbox("Fonte (Longa):", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=0, key="cmp_flonga") 
        c_plonga2.caption("🎯 IDEAL: FECHAMENTO")
        
        mapa_fontes_pm = {"Fechamento": "Close", "Máxima": "High", "Mínima": "Low", "Abertura": "Open"}
        fonte_curta_pm = mapa_fontes_pm[fonte_curta_pt_pm]
        fonte_longa_pm = mapa_fontes_pm[fonte_longa_pt_pm]
        
    with cp_pm3:
        alvo_cmp = st.number_input("Alvo de Lucro Global (%):", value=5.0, step=0.5, key="cmp_alvo")
        tempo_cmp = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="cmp_tmp")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 

    if curta_cmp >= longa_cmp:
        st.warning("⚠️ Atenção: O período da Média Curta deve ser menor que o da Média Longa.")

    btn_iniciar_cmp = st.button("🚀 Iniciar Varredura PM", type="primary", use_container_width=True, key="cmp_btn")

    if btn_iniciar_cmp and curta_cmp < longa_cmp:
        if tempo_cmp == '15m' and periodo_cmp not in ['1mo', '3mo']: periodo_cmp = '60d'
        elif tempo_cmp == '60m' and periodo_cmp in ['5y', 'max']: periodo_cmp = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_cmp, Interval.in_daily)
        alvo_dec = alvo_cmp / 100

        ls_sinais_pm, ls_abertos_pm, ls_resumo_pm = [], [], []
        p_bar_pm = st.progress(0)
        s_text_pm = st.empty()

        for idx, ativo_raw in enumerate(ativos_cmp):
            ativo = ativo_raw.replace('.SA', '')
            s_text_pm.text(f"🔍 Analisando Cruzamentos PM ({curta_cmp}x{longa_cmp}): {ativo} ({idx+1}/{len(ativos_cmp)})")
            p_bar_pm.progress((idx + 1) / len(ativos_cmp))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                if tipo_media_cmp == "Exponencial (EMA)":
                    df_full['Curta'] = ta.ema(df_full[fonte_curta_pm], length=curta_cmp)
                    df_full['Longa'] = ta.ema(df_full[fonte_longa_pm], length=longa_cmp)
                elif tipo_media_cmp == "Aritmética (SMA)":
                    df_full['Curta'] = ta.sma(df_full[fonte_curta_pm], length=curta_cmp)
                    df_full['Longa'] = ta.sma(df_full[fonte_longa_pm], length=longa_cmp)
                else: 
                    df_full['Curta'] = ta.rma(df_full[fonte_curta_pm], length=curta_cmp)
                    df_full['Longa'] = ta.rma(df_full[fonte_longa_pm], length=longa_cmp)
                
                df_full['Curta_Prev'] = df_full['Curta'].shift(1)
                df_full['Longa_Prev'] = df_full['Longa'].shift(1)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_cmp == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_cmp == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_cmp == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_cmp == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_cmp == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_cmp == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_cmp == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades = []
                em_pos = False
                qtd_acoes = 0.0
                capital_investido = 0.0
                preco_medio = 0.0
                pms_realizados = 0
                
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                min_price_in_trade = 0.0

                for i in range(1, len(df_back)):
                    cruzou_cima = (df_back['Curta'].iloc[i] > df_back['Longa'].iloc[i]) and (df_back['Curta_Prev'].iloc[i] <= df_back['Longa_Prev'].iloc[i])
                    
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade:
                            min_price_in_trade = df_back['Low'].iloc[i]
                        
                        # Checa se bateu o alvo do Preço Médio
                        if df_back['High'].iloc[i] >= take_profit:
                            lucro_rs = capital_investido * alvo_dec
                            drawdown_pct = ((min_price_in_trade / preco_entrada_inicial) - 1) * 100
                            trades.append({'Lucro (R$)': lucro_rs, 'Drawdown_Raw': drawdown_pct, 'PMs': pms_realizados})
                            em_pos = False
                            continue
                        
                        # Se cruzou para cima de novo (estando na operação), faz novo PM!
                        if cruzou_cima:
                            preco_compra = df_back['Close'].iloc[i]
                            capital_investido += float(capital_cmp)
                            qtd_acoes += float(capital_cmp) / preco_compra
                            preco_medio = capital_investido / qtd_acoes
                            take_profit = preco_medio * (1 + alvo_dec)
                            pms_realizados += 1

                    if cruzou_cima and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada_inicial = df_back['Close'].iloc[i] 
                        min_price_in_trade = df_back['Low'].iloc[i]
                        
                        capital_investido = float(capital_cmp)
                        qtd_acoes = capital_investido / preco_entrada_inicial
                        preco_medio = preco_entrada_inicial
                        pms_realizados = 0
                        take_profit = preco_medio * (1 + alvo_dec)

                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_medio) - 1) * 100
                    queda_max = ((min_price_in_trade / preco_entrada_inicial) - 1) * 100
                    
                    curta_atual = df_full['Curta'].iloc[-1]
                    longa_atual = df_full['Longa'].iloc[-1]
                    if curta_atual > longa_atual:
                        status_medias = "Curta > Longa (Buscando Alvo 📈)"
                    else:
                        status_medias = "Curta < Longa (Aguardando PM ⏳)"

                    ls_abertos_pm.append({
                        'Ativo': ativo, 'Entrada Inicial': d_ent.strftime('%d/%m %H:%M') if tempo_cmp in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Preço Médio': f"R$ {preco_medio:.2f}",
                        'Aportes (PM)': pms_realizados,
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Status das Médias': status_medias,
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    cruzou_hoje = (df_full['Curta'].iloc[-1] > df_full['Longa'].iloc[-1]) and (df_full['Curta_Prev'].iloc[-1] <= df_full['Longa_Prev'].iloc[-1])
                    if cruzou_hoje:
                        nome_m = tipo_media_cmp.split()[0]
                        col_curta = f"{nome_m} {curta_cmp} ({fonte_curta_pt_pm[:3]})"
                        col_longa = f"{nome_m} {longa_cmp} ({fonte_longa_pt_pm[:3]})"
                        ls_sinais_pm.append({
                            'Ativo': ativo, 
                            'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 
                            col_curta: f"{df_full['Curta'].iloc[-1]:.2f}", 
                            col_longa: f"{df_full['Longa'].iloc[-1]:.2f}"
                        })

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    ls_resumo_pm.append({
                        'Ativo': ativo, 'Trades Fechados': len(df_t), 'Maior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })
            except Exception as e: pass
            time.sleep(0.05)

        s_text_pm.empty()
        p_bar_pm.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.subheader(f"🚀 Novos Cruzamentos de Alta Hoje ({tipo_media_cmp.split()[0]} {curta_cmp}x{longa_cmp})")
        if len(ls_sinais_pm) > 0: 
            st.dataframe(pd.DataFrame(ls_sinais_pm), use_container_width=True, hide_index=True)
        else: 
            st.info(f"Nenhum ativo apresentou novo cruzamento de alta no último candle.")

        st.subheader("⏳ Operações em Andamento (Gerenciando Preço Médio)")
        if len(ls_abertos_pm) > 0:
            df_abertos = pd.DataFrame(ls_abertos_pm).sort_values(by='Aportes (PM)', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: 
            st.success("Sua carteira está limpa. Nenhum PM em aberto.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_cmp, periodo_cmp)})")
        if len(ls_resumo_pm) > 0:
            df_resumo = pd.DataFrame(ls_resumo_pm).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: 
            st.warning("Nenhuma operação finalizada neste período.")
# ==========================================
# ABA 3: RADAR ALVO & STOP (CRUZAMENTO CLÁSSICO)
# ==========================================
with aba_stop:
    st.subheader("🛡️ Radar Alvo & Stop Clássico")
    st.markdown("Estratégia 'Dispare e Esqueça'. Compra no cruzamento e só sai quando atingir o Alvo estipulado ou bater no Stop Loss de segurança.")
    
    cs1, cs2, cs3 = st.columns(3)
    with cs1:
        lista_cms = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="cms_lista")
        ativos_cms = bdrs_elite if lista_cms == "BDRs Elite" else ibrx_selecao if lista_cms == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_cms = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="cms_per")
        capital_cms = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="cms_cap")
    with cs2:
        tipo_media_cms = st.selectbox("Tipo de Média:", ["Exponencial (EMA)", "Aritmética (SMA)", "Welles Wilder (RMA)"], index=0, key="cms_tipo")
        
        c_scurta1, c_scurta2 = st.columns(2)
        curta_cms = c_scurta1.number_input("Período Curta:", min_value=2, max_value=200, value=16, step=1, key="cms_curta")
        fonte_curta_pt_cms = c_scurta2.selectbox("Fonte (Curta):", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=1, key="cms_fcurta") 
        
        c_slonga1, c_slonga2 = st.columns(2)
        longa_cms = c_slonga1.number_input("Período Longa:", min_value=3, max_value=200, value=42, step=1, key="cms_longa")
        fonte_longa_pt_cms = c_slonga2.selectbox("Fonte (Longa):", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=0, key="cms_flonga") 
        
        mapa_fontes_cms = {"Fechamento": "Close", "Máxima": "High", "Mínima": "Low", "Abertura": "Open"}
        fonte_curta_cms = mapa_fontes_cms[fonte_curta_pt_cms]
        fonte_longa_cms = mapa_fontes_cms[fonte_longa_pt_cms]
        
    with cs3:
        alvo_cms = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="cms_alvo")
        stop_cms = st.number_input("Stop Loss (%):", value=3.0, step=0.5, key="cms_stop")
        tempo_cms = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="cms_tmp")

    if curta_cms >= longa_cms:
        st.warning("⚠️ Atenção: O período da Média Curta deve ser menor que o da Média Longa.")

    btn_iniciar_cms = st.button("🚀 Iniciar Varredura Alvo/Stop", type="primary", use_container_width=True, key="cms_btn")

    if btn_iniciar_cms and curta_cms < longa_cms:
        if tempo_cms == '15m' and periodo_cms not in ['1mo', '3mo']: periodo_cms = '60d'
        elif tempo_cms == '60m' and periodo_cms in ['5y', 'max']: periodo_cms = '2y'

        intervalo_tv = tradutor_intervalo.get(tempo_cms, Interval.in_daily)
        alvo_dec = alvo_cms / 100
        stop_dec = stop_cms / 100

        ls_sinais_cms, ls_abertos_cms, ls_resumo_cms = [], [], []
        p_bar_cms = st.progress(0)
        s_text_cms = st.empty()

        for idx, ativo_raw in enumerate(ativos_cms):
            ativo = ativo_raw.replace('.SA', '')
            s_text_cms.text(f"🔍 Analisando Alvo/Stop ({curta_cms}x{longa_cms}): {ativo} ({idx+1}/{len(ativos_cms)})")
            p_bar_cms.progress((idx + 1) / len(ativos_cms))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                df_full = df_full.dropna()
                
                if tipo_media_cms == "Exponencial (EMA)":
                    df_full['Curta'] = ta.ema(df_full[fonte_curta_cms], length=curta_cms)
                    df_full['Longa'] = ta.ema(df_full[fonte_longa_cms], length=longa_cms)
                elif tipo_media_cms == "Aritmética (SMA)":
                    df_full['Curta'] = ta.sma(df_full[fonte_curta_cms], length=curta_cms)
                    df_full['Longa'] = ta.sma(df_full[fonte_longa_cms], length=longa_cms)
                else: 
                    df_full['Curta'] = ta.rma(df_full[fonte_curta_cms], length=curta_cms)
                    df_full['Longa'] = ta.rma(df_full[fonte_longa_cms], length=longa_cms)
                
                df_full['Curta_Prev'] = df_full['Curta'].shift(1)
                df_full['Longa_Prev'] = df_full['Longa'].shift(1)
                df_full = df_full.dropna()

                data_atual = df_full.index[-1]
                if periodo_cms == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                elif periodo_cms == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                elif periodo_cms == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                elif periodo_cms == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                elif periodo_cms == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                elif periodo_cms == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                elif periodo_cms == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                else: data_corte = df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                vitorias, derrotas = 0, 0
                df_back = df.reset_index()
                col_data = df_back.columns[0]

                for i in range(1, len(df_back)):
                    cruzou_cima = (df_back['Curta'].iloc[i] > df_back['Longa'].iloc[i]) and (df_back['Curta_Prev'].iloc[i] <= df_back['Longa_Prev'].iloc[i])
                    
                    if em_pos:
                        # Verifica Stop Loss
                        if df_back['Low'].iloc[i] <= stop_price:
                            trades.append({'Lucro (R$)': - (float(capital_cms) * stop_dec), 'Resultado': 'Stop'})
                            derrotas += 1
                            em_pos = False
                            continue
                            
                        # Verifica Alvo
                        if df_back['High'].iloc[i] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_cms) * alvo_dec, 'Resultado': 'Gain'})
                            vitorias += 1
                            em_pos = False
                            continue

                    if cruzou_cima and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i] 
                        take_profit = preco_entrada * (1 + alvo_dec)
                        stop_price = preco_entrada * (1 - stop_dec)

                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    ls_abertos_cms.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_cms in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Preço Entrada': f"R$ {preco_entrada:.2f}",
                        'Alvo 🎯': f"R$ {take_profit:.2f}",
                        'Stop 🛡️': f"R$ {stop_price:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    cruzou_hoje = (df_full['Curta'].iloc[-1] > df_full['Longa'].iloc[-1]) and (df_full['Curta_Prev'].iloc[-1] <= df_full['Longa_Prev'].iloc[-1])
                    if cruzou_hoje:
                        nome_m = tipo_media_cms.split()[0]
                        col_curta = f"{nome_m} {curta_cms} ({fonte_curta_pt_cms[:3]})"
                        col_longa = f"{nome_m} {longa_cms} ({fonte_longa_pt_cms[:3]})"
                        ls_sinais_cms.append({
                            'Ativo': ativo, 
                            'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", 
                            col_curta: f"{df_full['Curta'].iloc[-1]:.2f}", 
                            col_longa: f"{df_full['Longa'].iloc[-1]:.2f}"
                        })

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    taxa_acerto = (vitorias / len(df_t)) * 100
                    ls_resumo_cms.append({
                        'Ativo': ativo, 'Total Trades': len(df_t), 'Taxa de Acerto': f"{taxa_acerto:.1f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()
                    })
            except Exception as e: pass
            time.sleep(0.05)

        s_text_cms.empty()
        p_bar_cms.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.subheader(f"🚀 Sinais de Compra Hoje ({tipo_media_cms.split()[0]} {curta_cms}x{longa_cms})")
        if len(ls_sinais_cms) > 0: 
            st.dataframe(pd.DataFrame(ls_sinais_cms), use_container_width=True, hide_index=True)
        else: 
            st.info(f"Nenhum ativo apresentou sinal de entrada no último candle.")

        st.subheader("⏳ Operações em Andamento (Com Stop Armado)")
        if len(ls_abertos_cms) > 0:
            st.dataframe(pd.DataFrame(ls_abertos_cms).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: 
            st.success("Sua carteira está limpa. Nenhuma operação em risco no momento.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_cms, periodo_cms)})")
        if len(ls_resumo_cms) > 0:
            df_resumo = pd.DataFrame(ls_resumo_cms).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: 
            st.warning("Nenhuma operação finalizada neste período.")

# ==========================================
# ABA 4: RAIO-X DO ATIVO INDIVIDUAL (CRUZAMENTO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada de Ativo Único (Cruzamento)")
    st.markdown("Teste o histórico de um ativo específico alternando entre as 3 variações da estratégia de médias.")
    
    # 1. Configurações de Entrada
    ci1, ci2, ci3 = st.columns(3)
    with ci1:
        lupa_ativo = st.text_input("Ativo (Ex: PETR4 ou TSLA34):", value="PETR4", key="i_cm_ativo")
        lupa_est = st.selectbox("Estratégia a Testar:", ["Padrão (Só Alvo)", "PM Dinâmico (Re-cruzamento)", "Alvo & Stop Loss"], key="i_cm_est")
        lupa_per = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="i_cm_per")
    with ci2:
        lupa_tipo = st.selectbox("Tipo de Média:", ["Exponencial (EMA)", "Aritmética (SMA)", "Welles Wilder (RMA)"], index=0, key="i_cm_tipo")
        
        c_i1, c_i2 = st.columns(2)
        lupa_curta = c_i1.number_input("Curta:", min_value=2, value=16, key="i_cm_curta")
        lupa_fcurta_pt = c_i2.selectbox("Fonte C:", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=1, key="i_cm_fcurta")
        c_i2.caption("🎯 IDEAL: MÁXIMA")
        
        c_i3, c_i4 = st.columns(2)
        lupa_longa = c_i3.number_input("Longa:", min_value=3, value=42, key="i_cm_longa")
        lupa_flonga_pt = c_i4.selectbox("Fonte L:", ["Fechamento", "Máxima", "Mínima", "Abertura"], index=0, key="i_cm_flonga")
        c_i4.caption("🎯 IDEAL: FECHAMENTO")
    with ci3:
        lupa_alvo = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="i_cm_alvo")
        if lupa_est == "Alvo & Stop Loss":
            lupa_stop = st.number_input("Stop Loss (%):", value=3.0, step=0.5, key="i_cm_stop")
        else:
            st.markdown("<div style='height: 75px;'></div>", unsafe_allow_html=True)
        lupa_cap = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="i_cm_cap")
        
        # ADICIONADO '1mo' (Mensal) aqui também
        lupa_tmp = st.selectbox(
            "Tempo Gráfico:", 
            options=['15m', '60m', '1d', '1wk', '1mo'], 
            index=2, 
            format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x], 
            key="i_cm_tmp"
        )

    btn_raiox = st.button("🔍 Gerar Raio-X Individual", type="primary", use_container_width=True, key="i_cm_btn")

    if btn_raiox:
        if lupa_curta >= lupa_longa:
            st.error("Erro: A média curta deve ser menor que a longa.")
        else:
            ativo_limpo = lupa_ativo.strip().upper().replace('.SA', '')
            
            # --- TENTATIVA DE BUSCAR METADADOS (YFINANCE) ---
            try:
                import yfinance as yf
                import requests
                session = requests.Session()
                session.headers.update({'User-Agent': 'Mozilla/5.0'})
                ticker_yf = f"{ativo_limpo}.SA"
                inf = yf.Ticker(ticker_yf, session=session).info
                if inf and 'longName' in inf:
                    st.info(f"🏢 **Empresa:** {inf.get('longName')} | 📂 **Setor:** {inf.get('sector')}")
            except:
                st.caption(f"Analisando ativo: {ativo_limpo}")

            # --- PROCESSAMENTO DO BACKTEST ---
            # MAPEAMENTO FORÇADO DO TEMPO GRÁFICO (Igual ao IFR)
            mapa_intervalos = {
                '15m': Interval.in_15_minute,
                '60m': Interval.in_1_hour,
                '1d': Interval.in_daily,
                '1wk': Interval.in_weekly,
                '1mo': Interval.in_monthly
            }
            intervalo_tv = mapa_intervalos.get(lupa_tmp, Interval.in_daily)
            
            mapa_f = {"Fechamento": "Close", "Máxima": "High", "Mínima": "Low", "Abertura": "Open"}
            f_c, f_l = mapa_f[lupa_fcurta_pt], mapa_f[lupa_flonga_pt]
            alvo_d = lupa_alvo / 100
            stop_d = (lupa_stop / 100 if lupa_est == "Alvo & Stop Loss" else 0)

            with st.spinner(f'Calculando dados de {ativo_limpo}...'):
                try:
                    df_full = tv.get_hist(symbol=ativo_limpo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                    
                    if df_full is not None and len(df_full) > 50:
                        df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                        
                        # Calcula as médias no histórico total
                        if lupa_tipo == "Exponencial (EMA)":
                            df_full['Curta'] = ta.ema(df_full[f_c], length=lupa_curta)
                            df_full['Longa'] = ta.ema(df_full[f_l], length=lupa_longa)
                        elif lupa_tipo == "Aritmética (SMA)":
                            df_full['Curta'] = ta.sma(df_full[f_c], length=lupa_curta)
                            df_full['Longa'] = ta.sma(df_full[f_l], length=lupa_longa)
                        else:
                            df_full['Curta'] = ta.rma(df_full[f_c], length=lupa_curta)
                            df_full['Longa'] = ta.rma(df_full[f_l], length=lupa_longa)
                        
                        df_full['C_P'] = df_full['Curta'].shift(1)
                        df_full['L_P'] = df_full['Longa'].shift(1)
                        df_full = df_full.dropna()

                        # Lógica de Corte de Tempo (ADICIONADO PARA CORRIGIR O FILTRO DE ESTUDO)
                        data_atual_dt = df_full.index[-1]
                        offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                        data_corte = data_atual_dt - pd.DateOffset(months=offset_map.get(lupa_per, 120)) if lupa_per != 'max' else df_full.index[0]

                        df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                        col_dt = df_b.columns[0]

                        trades = []
                        em_pos = False
                        posicao_atual = None
                        vitorias, derrotas = 0, 0

                        for i in range(1, len(df_b)):
                            # Cruzamento de Baixo para Cima
                            c_cima = (df_b['Curta'].iloc[i] > df_b['Longa'].iloc[i]) and (df_b['C_P'].iloc[i] <= df_b['L_P'].iloc[i])
                            
                            if not em_pos:
                                if c_cima:
                                    em_pos = True
                                    d_ent = df_b[col_dt].iloc[i]
                                    p_ent = df_b['Close'].iloc[i]
                                    min_na_op = p_ent # Inicia a mínima no preço de compra
                                    
                                    cap_inv = float(lupa_cap)
                                    qtd_acoes = cap_inv / p_ent
                                    p_medio = p_ent
                                    pms = 0
                                    take_p = p_medio * (1 + alvo_d)
                                    stop_p = p_medio * (1 - stop_d)
                                    
                                    posicao_atual = {'Data': d_ent, 'PM': p_medio, 'Cap': cap_inv, 'PMs': pms}
                            else:
                                # Monitora a pior queda da operação em aberto
                                if df_b['Low'].iloc[i] < min_na_op: min_na_op = df_b['Low'].iloc[i]
                                
                                saiu = False
                                if df_b['High'].iloc[i] >= take_p:
                                    lucro = (cap_inv * alvo_d) if lupa_est == "PM Dinâmico (Re-cruzamento)" else (float(lupa_cap) * alvo_d)
                                    vitorias += 1; situacao = "Gain ✅"; saiu = True
                                elif lupa_est == "Alvo & Stop Loss" and df_b['Low'].iloc[i] <= stop_p:
                                    lucro = -(float(lupa_cap) * stop_d)
                                    derrotas += 1; situacao = "Stop ❌"; saiu = True

                                if saiu:
                                    duracao = (df_b[col_dt].iloc[i] - d_ent).days
                                    dd = ((min_na_op / p_medio) - 1) * 100
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%Y'), 'Duração': f"{duracao} d", 'Lucro (R$)': lucro, 'Queda Máx': dd, 'PMs': pms, 'Situação': situacao})
                                    em_pos = False
                                    posicao_atual = None
                                    
                                elif lupa_est == "PM Dinâmico (Re-cruzamento)" and c_cima:
                                    p_c = df_b['Close'].iloc[i]
                                    cap_inv += float(lupa_cap)
                                    qtd_acoes += float(lupa_cap) / p_c
                                    p_medio = cap_inv / qtd_acoes
                                    take_p = p_medio * (1 + alvo_d)
                                    pms += 1
                                    
                                    posicao_atual['PM'] = p_medio
                                    posicao_atual['Cap'] = cap_inv
                                    posicao_atual['PMs'] = pms

                        # --- EXIBIÇÃO: STATUS ATUAL ---
                        st.divider()
                        if em_pos and posicao_atual:
                            st.warning(f"⚠️ **OPERAÇÃO EM CURSO: {ativo_limpo} ({lupa_tmp})**")
                            
                            cotacao_atual = df_b['Close'].iloc[-1]
                            hoje = pd.Timestamp.today().normalize()
                            dias_em_op = (hoje - posicao_atual['Data']).days
                            
                            res_pct = ((cotacao_atual / posicao_atual['PM']) - 1) * 100
                            res_rs = posicao_atual['Cap'] * res_pct / 100
                            prej_max = ((min_na_op / posicao_atual['PM']) - 1) * 100

                            c1, c2, c3 = st.columns(3)
                            c1.metric("Data Entrada", posicao_atual['Data'].strftime('%d/%m/%Y'))
                            c2.metric("Dias em Operação", f"{dias_em_op} dias")
                            c3.metric("Cotação Atual", f"R$ {cotacao_atual:.2f}")
                            
                            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                            
                            c4, c5, c6 = st.columns(3)
                            pm_str = f"R$ {posicao_atual['PM']:.2f}"
                            if posicao_atual['PMs'] > 0: pm_str += f" ({posicao_atual['PMs']}x PM)"
                            
                            c4.metric("Preço Médio (PM)", pm_str)
                            c5.metric("Prejuízo Máximo (DD)", f"{prej_max:.2f}%")
                            c6.metric("Resultado Atual", f"{res_pct:.2f}%", delta=f"R$ {res_rs:.2f}")
                            
                        else:
                            st.success(f"✅ **{ativo_limpo}: Aguardando Novo Sinal de Cruzamento**")

                        # --- EXIBIÇÃO: MÉTRICAS DE RESUMO DO HISTÓRICO ---
                        if trades:
                            df_res = pd.DataFrame(trades)
                            st.markdown(f"### 📊 Resultado Consolidado: {ativo_limpo}")
                            
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total Estimado", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Operações Fechadas", len(df_res))
                            
                            if lupa_est == "Alvo & Stop Loss":
                                taxa_acerto = (vitorias / len(df_res)) * 100
                                m3.metric("Taxa de Acerto", f"{taxa_acerto:.1f}%")
                            else:
                                m3.metric("Pior Queda Enfrentada", f"{df_res['Queda Máx'].min():.2f}%")
                                
                            m4.metric("Média de PMs", f"{df_res['PMs'].mean():.1f}")
                            
                            # Formatação da tabela antes de exibir
                            df_res['Queda Máx'] = df_res['Queda Máx'].map("{:.2f}%".format)
                            st.dataframe(df_res, use_container_width=True, hide_index=True)
                        else:
                            st.info("Nenhum trade fechado no período de estudo selecionado.")
                            
                    else:
                        st.error("Ativo não encontrado ou base de dados vazia no TradingView.")
                except Exception as e: 
                    st.error(f"Erro no processamento: {e}")
# ==========================================
# ABA 5: RAIO-X FUTUROS (CRUZAMENTO DINÂMICO DAY TRADE)
# ==========================================
with aba_futuros:
    st.subheader("📉 Raio-X Mercado Futuro (WIN, WDO) - Cruzamento")
    st.markdown("Teste o desempenho em ativos alavancados. Entradas no cruzamento com alvo em **pontos** e saída obrigatória no fim do dia.")
    
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_fut = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!"}
        f_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_fut.keys()), key="f_cm_ativo")
        f_ativo = mapa_fut[f_selecionado] 
        f_dir = st.selectbox("Direção do Trade:", ["Ambas", "Apenas Compra", "Apenas Venda"], key="f_cm_dir")
        f_tmp = st.selectbox("Tempo Gráfico:", ['15m', '60m'], key="f_cm_tmp")
    with cf2:
        f_tipo = st.selectbox("Tipo de Média:", ["Exponencial (EMA)", "Aritmética (SMA)", "Welles Wilder (RMA)"], key="f_cm_tipo")
        
        c_f1, c_f2 = st.columns(2)
        f_curta = c_f1.number_input("Período Curta:", value=16, key="f_cm_curta")
        f_fcurta_pt = c_f2.selectbox("Fonte (Curta):", ["Fechamento", "Máxima", "Mínima"], index=1, key="f_cm_fcurta")
        
        c_f3, c_f4 = st.columns(2)
        f_longa = c_f3.number_input("Período Longa:", value=42, key="f_cm_longa")
        f_flonga_pt = c_f4.selectbox("Fonte (Longa):", ["Fechamento", "Máxima", "Mínima"], index=0, key="f_cm_flonga")
    with cf3:
        f_alvo = st.number_input("Alvo (Pontos):", value=300, step=50, key="f_cm_alvo")
        f_contratos = st.number_input("Contratos:", value=1, step=1, key="f_cm_cont")
        f_multi = st.number_input("Valor R$ por Ponto:", value=0.20 if "WIN" in f_selecionado else 10.0, key="f_cm_mult")
        f_zerar = st.checkbox("⏰ Zeragem Automática no Fim do Dia", value=True, key="f_cm_zerar")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_fut = st.button("🚀 Gerar Raio-X Futuros", type="primary", use_container_width=True, key="f_cm_btn")

    if btn_fut:
        mapa_f = {"Fechamento": "Close", "Máxima": "High", "Mínima": "Low"}
        intervalo_tv = tradutor_intervalo.get(f_tmp, Interval.in_15_minute)
        
        with st.spinner(f'Testando cruzamento {f_curta}x{f_longa} no {f_selecionado}...'):
            try:
                # Puxamos um histórico maior para o robô ter contexto das médias
                df_full = tv.get_hist(symbol=f_ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=10000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    
                    # Cálculo das Médias Universais
                    if f_tipo == "Exponencial (EMA)":
                        df_full['Curta'] = ta.ema(df_full[mapa_f[f_fcurta_pt]], length=f_curta)
                        df_full['Longa'] = ta.ema(df_full[mapa_f[f_flonga_pt]], length=f_longa)
                    elif f_tipo == "Aritmética (SMA)":
                        df_full['Curta'] = ta.sma(df_full[mapa_f[f_fcurta_pt]], length=f_curta)
                        df_full['Longa'] = ta.sma(df_full[mapa_f[f_flonga_pt]], length=f_longa)
                    else:
                        df_full['Curta'] = ta.rma(df_full[mapa_f[f_fcurta_pt]], length=f_curta)
                        df_full['Longa'] = ta.rma(df_full[mapa_f[f_flonga_pt]], length=f_longa)
                    
                    df_full['C_Prev'] = df_full['Curta'].shift(1)
                    df_full['L_Prev'] = df_full['Longa'].shift(1)
                    df_full = df_full.dropna()

                    trades, posicao = [], 0 # 0: Fora, 1: Comprado, -1: Vendido
                    vits, derrs = 0, 0
                    df_b = df_full.reset_index()
                    col_dt = df_b.columns[0]

                    for i in range(1, len(df_b)):
                        d_at, d_ant = df_b[col_dt].iloc[i], df_b[col_dt].iloc[i-1]
                        c_cima = (df_b['Curta'].iloc[i] > df_b['Longa'].iloc[i]) and (df_b['C_Prev'].iloc[i] <= df_b['L_Prev'].iloc[i])
                        c_baixo = (df_b['Curta'].iloc[i] < df_b['Longa'].iloc[i]) and (df_b['C_Prev'].iloc[i] >= df_b['L_Prev'].iloc[i])

                        # REGRA DE DAY TRADE: Zeragem no Fim do Dia
                        if posicao != 0 and f_zerar and d_at.date() != d_ant.date():
                            p_sai = df_b['Close'].iloc[i-1]
                            luc = (p_sai - p_ent) * f_contratos * f_multi if posicao == 1 else (p_ent - p_sai) * f_contratos * f_multi
                            trades.append({
                                'Entrada': d_ent.strftime('%d/%m %H:%M'), 
                                'Saída': d_ant.strftime('%d/%m %H:%M'), 
                                'Tipo': 'Compra 🟢' if posicao == 1 else 'Venda 🔴', 
                                'Pontos': (p_sai - p_ent) if posicao == 1 else (p_ent - p_sai),
                                'Lucro (R$)': luc, 
                                'Status': 'Zerad. Fim Dia'
                            })
                            if luc > 0: vits += 1 
                            else: derrs += 1
                            posicao = 0

                        # GESTÃO DA OPERAÇÃO ABERTA
                        if posicao == 1: # COMPRADO
                            if df_b['High'].iloc[i] >= take_p:
                                luc = f_alvo * f_contratos * f_multi
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢', 'Pontos': f_alvo, 'Lucro (R$)': luc, 'Status': 'Gain ✅'})
                                vits += 1; posicao = 0
                        elif posicao == -1: # VENDIDO
                            if df_b['Low'].iloc[i] <= take_p:
                                luc = f_alvo * f_contratos * f_multi
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Venda 🔴', 'Pontos': f_alvo, 'Lucro (R$)': luc, 'Status': 'Gain ✅'})
                                vits += 1; posicao = 0
                        
                        # GATILHOS DE ENTRADA
                        if c_cima and posicao == 0 and f_dir != "Apenas Venda":
                            posicao, d_ent, p_ent = 1, d_at, df_b['Close'].iloc[i]
                            take_p = p_ent + f_alvo
                        elif c_baixo and posicao == 0 and f_dir != "Apenas Compra":
                            posicao, d_ent, p_ent = -1, d_at, df_b['Close'].iloc[i]
                            take_p = p_ent - f_alvo

                    st.divider()
                    if trades:
                        df_res = pd.DataFrame(trades)
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lucro Total", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                        m2.metric("Quantidade de Operações", len(df_res))
                        m3.metric("Taxa de Acerto", f"{(vits/len(df_res)*100):.1f}%")
                        m4.metric("Saldo de Pontos", f"{df_res['Pontos'].sum():.0f}")
                        
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação de cruzamento concluída no período.")
            except Exception as e: st.error(f"Erro no processamento de Futuros: {e}")
