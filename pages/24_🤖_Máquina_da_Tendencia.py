import streamlit as st
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os
import plotly.graph_objects as go 
from plotly.subplots import make_subplots # <-- NOVO: Gerador de gráficos sobrepostos

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Trend Machine", layout="wide", page_icon="🤖")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# 2. IMPORTAÇÃO CENTRALIZADA (ATIVOS E MOTOR)
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

try:
    from motor_dados import puxar_dados_blindados
except ImportError:
    st.error("❌ Arquivo 'motor_dados.py' não encontrado na raiz do projeto. Crie o Bunker de Dados primeiro.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. MOTOR MATEMÁTICO E GERADOR DE GRÁFICO DUPLO
# ==========================================
def calcular_indicadores_trend(df, di_len=13, adx_len=8, st_len=10, st_mult=3.0):
    if df is None or len(df) < max(di_len, adx_len, st_len) * 2:
        return None
        
    df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)

    def wilder_rma(series, length):
        rma = np.full_like(series, np.nan, dtype=float)
        valid_idx = np.where(~np.isnan(series))[0]
        if len(valid_idx) == 0: return rma
        start = valid_idx[0]
        rma[start + length - 1] = np.mean(series[start : start + length])
        alpha = 1.0 / length
        for i in range(start + length, len(series)):
            rma[i] = alpha * series[i] + (1 - alpha) * rma[i-1]
        return rma

    high, low, close = df['High'].values, df['Low'].values, df['Close'].values
    
    up = np.append(0, high[1:] - high[:-1])
    down = np.append(0, low[:-1] - low[1:])
    pdm = np.where((up > down) & (up > 0), up, 0.0)
    mdm = np.where((down > up) & (down > 0), down, 0.0)
    
    tr_a = np.abs(high - low)
    tr_b = np.abs(high - np.append(0, close[:-1]))
    tr_c = np.abs(low - np.append(0, close[:-1]))
    tr = np.maximum(tr_a, np.maximum(tr_b, tr_c))
    tr[0] = np.nan

    tr_di = wilder_rma(tr, di_len)
    pdm_di = wilder_rma(pdm, di_len)
    mdm_di = wilder_rma(mdm, di_len)
    
    df['+DI'] = 100 * (pdm_di / np.where(tr_di == 0, 1e-10, tr_di))
    df['-DI'] = 100 * (mdm_di / np.where(tr_di == 0, 1e-10, tr_di))

    tr_adx = wilder_rma(tr, adx_len)
    pdm_adx = wilder_rma(pdm, adx_len)
    mdm_adx = wilder_rma(mdm, adx_len)
    
    pdi_adx = 100 * (pdm_adx / np.where(tr_adx == 0, 1e-10, tr_adx))
    mdi_adx = 100 * (mdm_adx / np.where(tr_adx == 0, 1e-10, tr_adx))
    
    dx_adx = 100 * np.abs(pdi_adx - mdi_adx) / np.where((pdi_adx + mdi_adx) == 0, 1e-10, (pdi_adx + mdi_adx))
    df['ADX'] = wilder_rma(dx_adx, adx_len)

    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    if st_df is not None and not st_df.empty:
        df['SuperTrend'] = st_df[[col for col in st_df.columns if col.startswith('SUPERT_')][0]]
        df['ST_Dir'] = st_df[[col for col in st_df.columns if col.startswith('SUPERTd_')][0]]

    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    df['+DI_Prev'] = df['+DI'].shift(1)

    return df.dropna()

def plotar_grafico_supertrend(df, trades_df, mostrar_adx=False):
    col_dt = df.columns[0]
    
    if mostrar_adx:
        # Se for mostrar o ADX, cria 2 linhas (1 para preço, 1 para ADX)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        altura_fig = 750
        l_preco = 1
        l_adx = 2
    else:
        # Se não for mostrar, cria só o principal
        fig = make_subplots(rows=1, cols=1)
        altura_fig = 550
        l_preco = 1

    # 1. Os Candles
    fig.add_trace(go.Candlestick(
        x=df[col_dt], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Preço'
    ), row=l_preco, col=1)

    # 2. SuperTrend Dividido por Cores
    st_verde = df.copy()
    st_verde.loc[st_verde['ST_Dir'] == -1, 'SuperTrend'] = np.nan
    st_vermelho = df.copy()
    st_vermelho.loc[st_vermelho['ST_Dir'] == 1, 'SuperTrend'] = np.nan

    fig.add_trace(go.Scatter(x=st_verde[col_dt], y=st_verde['SuperTrend'], mode='lines', line=dict(color='lime', width=3), name='ST Alta'), row=l_preco, col=1)
    fig.add_trace(go.Scatter(x=st_vermelho[col_dt], y=st_vermelho['SuperTrend'], mode='lines', line=dict(color='red', width=3), name='ST Baixa'), row=l_preco, col=1)

    # 3. Setas de Entrada do Robô
    if trades_df is not None and not trades_df.empty:
        try:
            entradas = df[df[col_dt].dt.strftime('%d/%m/%Y').isin(trades_df['Entrada'])]
            fig.add_trace(go.Scatter(
                x=entradas[col_dt], y=entradas['Low'] * 0.98, mode='markers',
                marker=dict(symbol='triangle-up', size=14, color='cyan', line=dict(width=2, color='white')),
                name='Entrada ADX'
            ), row=l_preco, col=1)
        except: pass

    # 4. PLOTAGEM DO ADX (Se habilitado)
    if mostrar_adx:
        fig.add_trace(go.Scatter(x=df[col_dt], y=df['+DI'], mode='lines', line=dict(color='lime', width=1.5), name='+DI'), row=l_adx, col=1)
        fig.add_trace(go.Scatter(x=df[col_dt], y=df['-DI'], mode='lines', line=dict(color='red', width=1.5), name='-DI'), row=l_adx, col=1)
        fig.add_trace(go.Scatter(x=df[col_dt], y=df['ADX'], mode='lines', line=dict(color='white', width=2), name='ADX (Força)'), row=l_adx, col=1)

    # Ajustes finais visuais
    titulo = 'Ação do Preço + SuperTrend' + (' + Indicador ADX/DMI' if mostrar_adx else '')
    fig.update_layout(
        title=titulo, yaxis_title='Cotação',
        xaxis_rangeslider_visible=False, template='plotly_dark',
        height=altura_fig, margin=dict(l=20, r=20, t=50, b=20)
    )
    
    # Esconde a barrinha de baixo (rangeslider) em todos os eixos X
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.title("🤖 Máquina de Tendência (Com Gráfico Interativo)")
st.info("📊 **Regra Estrita:** O robô entra na operação APENAS SE o ADX cruzar o DI- para cima **no mesmo dia** em que o DI+ está maior que o DI- e o SuperTrend está Verde.")

aba_padrao, aba_individual, aba_futuros = st.tabs(["📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"])

# ==========================================
# ABA 1: RADAR PADRÃO
# ==========================================
with aba_padrao:
    with st.container(border=True):
        st.markdown("**1. Parâmetros Base**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            lista_tr = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="tr_lista")
            capital_tr = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="tr_cap")
        with c2:
            tempo_tr = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x], key="tr_tmp")
            periodo_tr = st.selectbox("Histórico (Backtest):", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="tr_per")
        with c3:
            st.markdown("##### ⚙️ ADX & SuperTrend")
            c_adx1, c_adx2 = st.columns(2)
            di_len_g = c_adx1.number_input("Período DI (+/-):", min_value=2, value=13, step=1, key="tr_di_len")
            adx_len_g = c_adx2.number_input("Período ADX:", min_value=2, value=8, step=1, key="tr_adx_len")
            
            c_st1, c_st2 = st.columns(2)
            st_len_g = c_st1.number_input("ST Período:", min_value=2, value=10, step=1, key="tr_st_len")
            st_mult_g = c_st2.number_input("ST Mult:", min_value=0.5, value=3.0, step=0.1, key="tr_st_mult")
        with c4:
            st.markdown("##### 🛡️ Gestão de Risco")
            usar_alvo_g = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_g")
            alvo_g = st.number_input("Alvo (%):", value=15.0, step=1.0, disabled=not usar_alvo_g, key="val_alvo_g")
            usar_stop_g = st.toggle("🛡️ Stop Loss", value=False, key="tg_stop_g")
            stop_g = st.number_input("Stop Loss (%):", value=5.0, step=1.0, disabled=not usar_stop_g, key="val_stop_g")
            usar_saida_st_g = st.toggle("📉 Saída pela Reversão (ST)", value=True, key="tg_st_g")
            usar_saida_dmi_g = st.toggle("📉 Saída Reversão DMI (+DI < -DI)", value=False, key="tg_dmi_g")

    btn_iniciar_tr = st.button("🚀 Iniciar Varredura de Tendência", type="primary", use_container_width=True, key="tr_btn")

    if btn_iniciar_tr:
        ativos_tr = bdrs_elite if lista_tr == "BDRs Elite" else ibrx_selecao if lista_tr == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🔍 Medindo Força Institucional: {ativo} ({idx+1}/{len(ativos_tr)})")
            p_bar.progress((idx + 1) / len(ativos_tr))

            try:
                df_full = puxar_dados_blindados(ativo, tempo_tr)
                
                if df_full is None or len(df_full) < 50: continue
                
                df_full = calcular_indicadores_trend(df_full, di_len_g, adx_len_g, st_len_g, st_mult_g)
                if df_full is None: continue

                data_atual = df_full.index[-1]
                offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                data_corte = data_atual - pd.DateOffset(months=offset_map.get(periodo_tr, 120)) if periodo_tr != 'max' else df_full.index[0]

                df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                
                trades, em_pos = [], False
                col_data = df_back.columns[0]
                min_price_in_trade = 0.0
                alvo_d, stop_d = alvo_g / 100.0, stop_g / 100.0

                for i in range(1, len(df_back)):
                    cruzou_adx = (df_back['ADX_Prev'].iloc[i] <= df_back['-DI_Prev'].iloc[i]) and (df_back['ADX'].iloc[i] > df_back['-DI'].iloc[i])
                    di_ok = df_back['+DI'].iloc[i] > df_back['-DI'].iloc[i]
                    st_ok = df_back['ST_Dir'].iloc[i] == 1
                    sinal_compra = cruzou_adx and di_ok and st_ok
                    
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                        
                        bateu_alvo = usar_alvo_g and (df_back['High'].iloc[i] >= take_profit)
                        bateu_stop = usar_stop_g and (df_back['Low'].iloc[i] <= stop_price)
                        reverteu_st = usar_saida_st_g and (df_back['ST_Dir'].iloc[i] == -1)
                        reverteu_dmi = usar_saida_dmi_g and (df_back['+DI'].iloc[i] < df_back['-DI'].iloc[i])
                        
                        if bateu_stop:
                            trades.append({'Lucro (R$)': -(float(capital_tr) * stop_d), 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100, 'Motivo': 'Stop ❌'})
                            em_pos = False; continue
                        elif bateu_alvo:
                            trades.append({'Lucro (R$)': float(capital_tr) * alvo_d, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100, 'Motivo': 'Alvo ✅'})
                            em_pos = False; continue
                        elif reverteu_st or reverteu_dmi:
                            lucro_rs = float(capital_tr) * ((df_back['Close'].iloc[i] / preco_entrada) - 1)
                            motivo = 'Saída ST' if reverteu_st else 'Saída DMI'
                            trades.append({'Lucro (R$)': lucro_rs, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100, 'Motivo': f"{motivo} {'✅' if lucro_rs > 0 else '❌'}"})
                            em_pos = False; continue

                    if sinal_compra and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i] 
                        min_price_in_trade = df_back['Low'].iloc[i]
                        take_profit = preco_entrada * (1 + alvo_d)
                        stop_price = preco_entrada * (1 - stop_d)

                if em_pos:
                    resultado_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    queda_max = ((min_price_in_trade / preco_entrada) - 1) * 100
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_tr in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'Dias': (df_back[col_data].iloc[-1] - d_ent).days, 'PM': f"R$ {preco_entrada:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Prej. Máx': f"{queda_max:.2f}%", 'Resultado Atual': f"+{resultado_atual:.2f}%" if resultado_atual > 0 else f"{resultado_atual:.2f}%"
                    })
                else:
                    hoje = df_full.iloc[-1]
                    hoje_cruzou = (hoje['ADX_Prev'] <= hoje['-DI_Prev']) and (hoje['ADX'] > hoje['-DI'])
                    sinal_hoje = hoje_cruzou and (hoje['+DI'] > hoje['-DI']) and (hoje['ST_Dir'] == 1)
                    if sinal_hoje:
                        ls_sinais.append({'Ativo': ativo, 'Preço Atual': f"R$ {hoje['Close']:.2f}", 'ADX (Força)': f"{hoje['ADX']:.1f}", 'SuperTrend': "Verde 🟢"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    ls_resumo.append({'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()})
            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty(); p_bar.empty()
        st.subheader(f"🚀 Sinais Confirmados Hoje")
        if len(ls_sinais) > 0: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo confirmou o cruzamento hoje.")

        st.subheader("⏳ Operações em Andamento")
        if len(ls_abertos) > 0: st.dataframe(pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_tr, periodo_tr)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (COM GRÁFICO E ADX!)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada de Ativo Único (ADX + SuperTrend)")
    with st.container(border=True):
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            ativo_rx = st.selectbox("Ativo a Testar:", ativos_para_rastrear, key="i_tr_ativo")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="i_tr_cap")
        with ci2:
            tempo_rx = st.selectbox("Tempo Gráfico:", options=['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x], key="i_tr_tmp")
            periodo_rx = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="i_tr_per")
        with ci3:
            st.markdown("##### ⚙️ ADX & SuperTrend")
            c_rx_adx1, c_rx_adx2 = st.columns(2)
            di_len_rx = c_rx_adx1.number_input("Período DI:", min_value=2, value=13, key="i_tr_dilen")
            adx_len_rx = c_rx_adx2.number_input("Período ADX:", min_value=2, value=8, key="i_tr_adxlen") 
            
            c_rx_st1, c_rx_st2 = st.columns(2)
            st_len_rx = c_rx_st1.number_input("ST Período:", value=10, key="i_tr_stlen")
            st_mult_rx = c_rx_st2.number_input("ST Mult:", value=3.0, step=0.1, key="i_tr_stmult")
            
            # --- O BOTÃO MÁGICO DO GRÁFICO ADX ---
            mostrar_adx_rx = st.toggle("📊 Mostrar Gráfico ADX no Raio-X", value=False, key="tg_grafico_adx")
            
        with ci4:
            st.markdown("##### 🛡️ Gestão de Risco")
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_rx")
            lupa_alvo = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not usar_alvo_rx, key="i_tr_alvo")
            usar_stop_rx = st.toggle("🛡️ Stop Loss Fixo", value=False, key="tg_stop_rx")
            lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, disabled=not usar_stop_rx, key="i_tr_stop")
            usar_saida_st_rx = st.toggle("📉 Saída pela Reversão (ST)", value=True, key="tg_st_rx")
            usar_saida_dmi_rx = st.toggle("📉 Saída Reversão DMI (+DI < -DI)", value=False, key="tg_dmi_rx")

    if st.button("🔍 Gerar Raio-X da Máquina", type="primary", use_container_width=True, key="i_tr_btn"):
        alvo_d, stop_d = lupa_alvo / 100.0, lupa_stop / 100.0

        with st.spinner(f'Processando matemática para {ativo_rx}...'):
            try:
                df_full = puxar_dados_blindados(ativo_rx, tempo_rx)
                
                if df_full is not None and len(df_full) > 50:
                    df_full = calcular_indicadores_trend(df_full, di_len_rx, adx_len_rx, st_len_rx, st_mult_rx)
                    
                    if df_full is not None:
                        data_atual_dt = df_full.index[-1]
                        offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                        data_corte = data_atual_dt - pd.DateOffset(months=offset_map.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]

                        df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                        col_dt = df_b.columns[0]
                        trades, em_pos, vitorias, derrotas, posicao_atual = [], False, 0, 0, None

                        for i in range(1, len(df_b)):
                            cruzou_adx = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                            di_ok = df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]
                            st_ok = df_b['ST_Dir'].iloc[i] == 1
                            sinal = cruzou_adx and di_ok and st_ok
                            
                            if not em_pos:
                                if sinal:
                                    em_pos = True
                                    d_ent = df_b[col_dt].iloc[i]
                                    p_ent = df_b['Close'].iloc[i]
                                    min_na_op = p_ent 
                                    cap_inv = float(capital_rx)
                                    take_p = p_ent * (1 + alvo_d)
                                    stop_p = p_ent * (1 - stop_d)
                                    posicao_atual = {'Data': d_ent, 'PM': p_ent, 'Cap': cap_inv}
                            else:
                                if df_b['Low'].iloc[i] < min_na_op: min_na_op = df_b['Low'].iloc[i]
                                
                                bateu_alvo = usar_alvo_rx and (df_b['High'].iloc[i] >= take_p)
                                bateu_stop = usar_stop_rx and (df_b['Low'].iloc[i] <= stop_p)
                                reverteu_st = usar_saida_st_rx and (df_b['ST_Dir'].iloc[i] == -1)
                                reverteu_dmi = usar_saida_dmi_rx and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i])
                                
                                saiu = False
                                if bateu_stop:
                                    lucro = -(float(capital_rx) * stop_d)
                                    derrotas += 1; situacao = "Stop ❌"; saiu = True
                                elif bateu_alvo:
                                    lucro = float(capital_rx) * alvo_d
                                    vitorias += 1; situacao = "Alvo ✅"; saiu = True
                                elif reverteu_st or reverteu_dmi:
                                    lucro = float(capital_rx) * ((df_b['Close'].iloc[i] / p_ent) - 1)
                                    if reverteu_st:
                                        if lucro > 0: vitorias += 1; situacao = "Saída ST ✅"
                                        else: derrotas += 1; situacao = "Reversão ST ❌"
                                    else:
                                        if lucro > 0: vitorias += 1; situacao = "Saída DMI ✅"
                                        else: derrotas += 1; situacao = "Reversão DMI ❌"
                                    saiu = True

                                if saiu:
                                    duracao = (df_b[col_dt].iloc[i] - d_ent).days
                                    dd = ((min_na_op / p_ent) - 1) * 100
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': df_b[col_dt].iloc[i].strftime('%d/%m/%Y'), 'Duração': f"{duracao} d", 'Lucro (R$)': lucro, 'Queda Máx': dd, 'Situação': situacao})
                                    em_pos, posicao_atual = False, None

                        st.divider()
                        
                        # ---> RENDERIZA O GRÁFICO INTERATIVO COM A OPÇÃO DO ADX AQUI <---
                        st.markdown(f"### 📈 Visualização do Gráfico ({ativo_rx})")
                        df_trades_plot = pd.DataFrame(trades) if trades else pd.DataFrame()
                        corte_grafico = df_b.tail(250) # Mostra os últimos 250 dias
                        
                        # Passando a variável mostrar_adx_rx do toggle para a função!
                        st.plotly_chart(plotar_grafico_supertrend(corte_grafico, df_trades_plot, mostrar_adx_rx), use_container_width=True)
                        st.divider()

                        if em_pos and posicao_atual:
                            st.warning(f"⚠️ **OPERAÇÃO EM CURSO: {ativo_rx} ({tempo_rx})**")
                            cotacao_atual = df_b['Close'].iloc[-1]
                            dias_em_op = (pd.Timestamp.today().normalize() - posicao_atual['Data']).days
                            res_pct = ((cotacao_atual / posicao_atual['PM']) - 1) * 100
                            res_rs = posicao_atual['Cap'] * res_pct / 100
                            prej_max = ((min_na_op / posicao_atual['PM']) - 1) * 100

                            c1, c2, c3 = st.columns(3)
                            c1.metric("Data Entrada", posicao_atual['Data'].strftime('%d/%m/%Y'))
                            c2.metric("Dias em Operação", f"{dias_em_op} dias")
                            c3.metric("Cotação Atual", f"R$ {cotacao_atual:.2f}")
                            
                            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                            c4, c5, c6 = st.columns(3)
                            c4.metric("Preço Entrada", f"R$ {posicao_atual['PM']:.2f}")
                            c5.metric("Prejuízo Máximo (DD)", f"{prej_max:.2f}%")
                            c6.metric("Resultado Atual", f"{res_pct:.2f}%", delta=f"R$ {res_rs:.2f}")
                        else:
                            st.success(f"✅ **{ativo_rx}: Aguardando Cruzamento do ADX**")

                        if trades:
                            df_res = pd.DataFrame(trades)
                            st.markdown(f"### 📊 Resultado Consolidado: {ativo_rx}")
                            
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total Estimado", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Operações Fechadas", len(df_res))
                            m3.metric("Taxa de Acerto", f"{(vitorias / len(df_res) * 100):.1f}%")
                            m4.metric("Pior Queda Enfrentada", f"{df_res['Queda Máx'].min():.2f}%")
                            
                            df_res['Queda Máx'] = df_res['Queda Máx'].map("{:.2f}%".format)
                            
                            def colorir_res_indiv(val):
                                if '✅' in str(val): return 'color: #28a745; font-weight: bold'
                                elif '❌' in str(val): return 'color: #dc3545; font-weight: bold'
                                return ''
                            
                            st.dataframe(df_res.style.map(colorir_res_indiv, subset=['Situação']), use_container_width=True, hide_index=True)
                        else: st.info("Nenhum trade fechado no período de estudo selecionado.")
                else: st.error("Base de dados vazia para este ativo no motor_dados.")
            except Exception as e: st.error(f"Erro no processamento: {e}")

# ==========================================
# ABA 3: RAIO-X FUTUROS (DAY TRADE)
# ==========================================
with aba_futuros:
    st.subheader("📉 Raio-X Mercado Futuro (O Trator do Intraday)")
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_fut = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!", "BITCOIN (Cripto)": "BTCUSD"}
        f_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_fut.keys()), key="f_tr_ativo")
        f_ativo = mapa_fut[f_selecionado] 
        f_dir = st.selectbox("Direção do Trade:", ["Ambas", "Apenas Compra", "Apenas Venda"], key="f_tr_dir")
        f_tmp = st.selectbox("Tempo Gráfico:", ['15m', '60m'], key="f_tr_tmp")
    with cf2:
        c_fadx1, c_fadx2 = st.columns(2)
        f_di_len = c_fadx1.number_input("Período DI F:", value=13, key="f_tr_dilen")
        f_adx_len = c_fadx2.number_input("Período ADX F:", value=8, key="f_tr_adxlen")
        
        c_f1, c_f2 = st.columns(2)
        f_st_len = c_f1.number_input("Período ST F:", value=10, key="f_tr_st")
        f_st_mult = c_f2.number_input("Mult ST F:", value=3.0, step=0.1, key="f_tr_stm")
    with cf3:
        f_alvo = st.number_input("Alvo (Pontos):", value=300 if "WIN" in f_selecionado else 10, step=50, key="f_tr_alvo")
        f_contratos = st.number_input("Contratos:", value=1, step=1, key="f_tr_cont")
        f_multi = st.number_input("R$ por Ponto:", value=0.20 if "WIN" in f_selecionado else 10.0, key="f_tr_mult")
        f_zerar = st.checkbox("⏰ Zeragem Auto. Fim do Dia", value=True, key="f_tr_zerar")
        f_saida_dmi = st.checkbox("📉 Saída Reversão DMI", value=False, key="f_tr_sdmi")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_fut = st.button("🚀 Gerar Raio-X Futuros", type="primary", use_container_width=True, key="f_tr_btn")

    if btn_fut:
        with st.spinner(f'Simulando Tanque de Guerra em {f_selecionado}...'):
            try:
                df_full = puxar_dados_blindados(f_ativo, f_tmp)
                
                if df_full is not None:
                    df_full = calcular_indicadores_trend(df_full, f_di_len, f_adx_len, f_st_len, f_st_mult)
                    
                    if df_full is not None:
                        trades, posicao = [], 0 
                        vits, derrs = 0, 0
                        df_b = df_full.reset_index()
                        col_dt = df_b.columns[0]

                        for i in range(1, len(df_b)):
                            d_at, d_ant = df_b[col_dt].iloc[i], df_b[col_dt].iloc[i-1]
                            
                            cruz_compra = (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i])
                            sinal_compra = cruz_compra and (df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == 1)
                            
                            cruz_venda = (df_b['ADX_Prev'].iloc[i] <= df_b['+DI_Prev'].iloc[i]) and (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i])
                            sinal_venda = cruz_venda and (df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ST_Dir'].iloc[i] == -1)

                            if posicao != 0 and f_zerar and d_at.date() != d_ant.date():
                                p_sai = df_b['Close'].iloc[i-1]
                                pts = (p_sai - p_ent) if posicao == 1 else (p_ent - p_sai)
                                luc = pts * f_contratos * f_multi
                                trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_ant.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢' if posicao == 1 else 'Venda 🔴', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': 'Zerad. Fim Dia'})
                                if luc > 0: vits += 1 
                                else: derrs += 1
                                posicao = 0

                            if posicao == 1: 
                                if df_b['High'].iloc[i] >= take_p:
                                    luc = f_alvo * f_contratos * f_multi
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢', 'Pontos': f_alvo, 'Lucro (R$)': luc, 'Status': 'Gain ✅'})
                                    vits += 1; posicao = 0
                                elif df_b['ST_Dir'].iloc[i] == -1:
                                    pts = (df_b['Close'].iloc[i] - p_ent)
                                    luc = pts * f_contratos * f_multi
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': 'Reversão ST ❌'})
                                    derrs += 1; posicao = 0
                                elif f_saida_dmi and (df_b['+DI'].iloc[i] < df_b['-DI'].iloc[i]):
                                    pts = (df_b['Close'].iloc[i] - p_ent)
                                    luc = pts * f_contratos * f_multi
                                    status = 'Saída DMI ✅' if luc > 0 else 'Saída DMI ❌'
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Compra 🟢', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': status})
                                    if luc > 0: vits += 1
                                    else: derrs += 1
                                    posicao = 0
                                    
                            elif posicao == -1: 
                                if df_b['Low'].iloc[i] <= take_p:
                                    luc = f_alvo * f_contratos * f_multi
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Venda 🔴', 'Pontos': f_alvo, 'Lucro (R$)': luc, 'Status': 'Gain ✅'})
                                    vits += 1; posicao = 0
                                elif df_b['ST_Dir'].iloc[i] == 1:
                                    pts = (p_ent - df_b['Close'].iloc[i])
                                    luc = pts * f_contratos * f_multi
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Venda 🔴', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': 'Reversão ST ❌'})
                                    derrs += 1; posicao = 0
                                elif f_saida_dmi and (df_b['-DI'].iloc[i] < df_b['+DI'].iloc[i]):
                                    pts = (p_ent - df_b['Close'].iloc[i])
                                    luc = pts * f_contratos * f_multi
                                    status = 'Saída DMI ✅' if luc > 0 else 'Saída DMI ❌'
                                    trades.append({'Entrada': d_ent.strftime('%d/%m %H:%M'), 'Saída': d_at.strftime('%d/%m %H:%M'), 'Tipo': 'Venda 🔴', 'Pontos': pts, 'Lucro (R$)': luc, 'Status': status})
                                    if luc > 0: vits += 1
                                    else: derrs += 1
                                    posicao = 0
                            
                            if posicao == 0:
                                if sinal_compra and f_dir != "Apenas Venda":
                                    posicao, d_ent, p_ent = 1, d_at, df_b['Close'].iloc[i]
                                    take_p = p_ent + f_alvo
                                elif sinal_venda and f_dir != "Apenas Compra":
                                    posicao, d_ent, p_ent = -1, d_at, df_b['Close'].iloc[i]
                                    take_p = p_ent - f_alvo

                        st.divider()
                        if trades:
                            df_res = pd.DataFrame(trades)
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total Estimado", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Total de Tiros", len(df_res))
                            m3.metric("Taxa de Acerto", f"{(vits/len(df_res)*100):.1f}%")
                            m4.metric("Saldo de Pontos", f"{df_res['Pontos'].sum():.0f}")
                            st.dataframe(df_res, use_container_width=True, hide_index=True)
                        else: st.warning("A Máquina não disparou nenhum tiro no período.")
            except Exception as e: st.error(f"Erro no processamento da blindagem: {e}")
