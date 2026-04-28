import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os
from datetime import datetime

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
# 2. CONFIGURAÇÃO DA PÁGINA & TVDATAFEED
# ==========================================
st.set_page_config(page_title="Trend Machine", layout="wide", page_icon="🤖")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos',
    'max': 'Máximo', '60d': '60 Dias'
}

tradutor_intervalo = {
    '15m': Interval.in_15_minute,
    '60m': Interval.in_1_hour,
    '1d': Interval.in_daily,
    '1wk': Interval.in_weekly
}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 3. MOTOR MATEMÁTICO: ADX + SUPERTREND 
# ==========================================
def calcular_indicadores_trend(df, adx_len=14, st_len=10, st_mult=3.0):
    if df is None or len(df) < max(adx_len, st_len) * 2:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_localize(None)
    
    # 1. Calcula ADX e DMI 
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=adx_len)
    if adx_df is None or adx_df.empty: return None
    
    col_adx = [c for c in adx_df.columns if c.startswith('ADX')][0]
    col_dmp = [c for c in adx_df.columns if c.startswith('DMP')][0]
    col_dmn = [c for c in adx_df.columns if c.startswith('DMN')][0]
    
    df['ADX'] = adx_df[col_adx]
    df['+DI'] = adx_df[col_dmp]
    df['-DI'] = adx_df[col_dmn]
    
    # 2. Calcula SuperTrend
    st_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=st_len, multiplier=st_mult)
    if st_df is None or st_df.empty: return None
    
    col_st = [c for c in st_df.columns if c.startswith('SUPERT_')][0]
    col_st_dir = [c for c in st_df.columns if c.startswith('SUPERTd_')][0]
    
    df['SuperTrend'] = st_df[col_st]
    df['ST_Dir'] = st_df[col_st_dir] # 1 (Alta) ou -1 (Baixa)
    
    # Memórias de ontem para calcular o cruzamento EXATO
    df['ADX_Prev'] = df['ADX'].shift(1)
    df['-DI_Prev'] = df['-DI'].shift(1)
    df['+DI_Prev'] = df['+DI'].shift(1)
    return df.dropna()

def renderizar_grafico_tv(symbol):
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tv_chart_{symbol.replace(':', '')}" style="height: 600px; width: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "autosize": true,
      "symbol": "{symbol}",
      "interval": "D",
      "timezone": "America/Sao_Paulo",
      "theme": "dark",
      "style": "1",
      "locale": "br",
      "enable_publishing": false,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tv_chart_{symbol.replace(':', '')}"
    }}
      );
      </script>
    </div>
    """
    components.html(html_code, height=600)

st.title("🤖 Máquina de Tendência (ADX + SuperTrend)")
st.info("📊 **Estratégia (Trend Following Extremo):** Um sistema blindado contra ruídos laterais. \n\n🟢 **Gatilho de Compra:** A compra só é acionada no EXATO momento em que o ADX (Preto) cruza o DI- (Vermelho) para cima. Para validar, o DI+ (Verde) tem que estar acima do DI- e o SuperTrend tem que estar verde. \n🔴 **Defesas:** Você pode montar o seu escudo desativando ou ativando a Saída pela Reversão do SuperTrend, Reversão do DMI, Alvo de Lucro ou Stop Loss fixo.")

aba_padrao, aba_individual, aba_futuros = st.tabs([
    "📡 Radar Padrão", "🔬 Raio-X Individual", "📉 Raio-X Futuros"
])

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
            c_adx1 = st.columns(1)[0]
            adx_len = c_adx1.number_input("Período ADX:", min_value=2, value=14, step=1, key="tr_adx_len")
            
            c_st1, c_st2 = st.columns(2)
            st_len = c_st1.number_input("ST Período:", min_value=2, value=10, step=1, key="tr_st_len")
            st_mult = c_st2.number_input("ST Mult:", min_value=0.5, value=3.0, step=0.1, key="tr_st_mult")
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
        intervalo_tv = tradutor_intervalo.get(tempo_tr, Interval.in_daily)
        ativos_tr = bdrs_elite if lista_tr == "BDRs Elite" else ibrx_selecao if lista_tr == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🔍 Medindo Força Institucional: {ativo} ({idx+1}/{len(ativos_tr)})")
            p_bar.progress((idx + 1) / len(ativos_tr))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                if df_full is None or len(df_full) < 50: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df_full = calcular_indicadores_trend(df_full, adx_len, st_len, st_mult)
                if df_full is None: continue

                data_atual = df_full.index[-1]
                offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                data_corte = data_atual - pd.DateOffset(months=offset_map.get(periodo_tr, 120)) if periodo_tr != 'max' else df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                min_price_in_trade = 0.0

                alvo_d = alvo_g / 100.0
                stop_d = stop_g / 100.0

                for i in range(1, len(df_back)):
                    
                    # === GATILHO ESTrito DE COMPRA ===
                    adx_cruzou_di_menos = (df_back['ADX'].iloc[i] > df_back['-DI'].iloc[i]) and (df_back['ADX_Prev'].iloc[i] <= df_back['-DI_Prev'].iloc[i])
                    di_mais_acima = df_back['+DI'].iloc[i] > df_back['-DI'].iloc[i]
                    st_verde = df_back['ST_Dir'].iloc[i] == 1
                    
                    sinal_compra = adx_cruzou_di_menos and di_mais_acima and st_verde
                    
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
                            if reverteu_st:
                                motivo = 'Saída ST ✅' if lucro_rs > 0 else 'Saída ST ❌'
                            else:
                                motivo = 'Saída DMI ✅' if lucro_rs > 0 else 'Saída DMI ❌'
                            trades.append({'Lucro (R$)': lucro_rs, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100, 'Motivo': motivo})
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
                    adx_cruzou_di_menos_hoje = (hoje['ADX'] > hoje['-DI']) and (hoje['ADX_Prev'] <= hoje['-DI_Prev'])
                    sinal_hoje = adx_cruzou_di_menos_hoje and (hoje['+DI'] > hoje['-DI']) and (hoje['ST_Dir'] == 1)
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
        else: st.info("Nenhum ativo atingiu o cruzamento triplo perfeito hoje.")

        st.subheader("⏳ Operações em Andamento")
        if len(ls_abertos) > 0:
            st.dataframe(pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_tr, periodo_tr)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (SIMULADOR HISTÓRICO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada de Ativo Único (ADX + SuperTrend)")
    st.markdown("Faça o teste de estresse de um ativo específico para ver se a blindagem funciona bem nele.")
    
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
            c_rx_adx1 = st.columns(1)[0]
            lupa_adx_len = c_rx_adx1.number_input("ADX Per:", min_value=2, value=14, key="i_tr_adxlen")
            
            c_rx_st1, c_rx_st2 = st.columns(2)
            lupa_st_len = c_rx_st1.number_input("ST Per:", value=10, key="i_tr_stlen")
            lupa_st_mult = c_rx_st2.number_input("ST Mult:", value=3.0, step=0.1, key="i_tr_stmult")
        with ci4:
            st.markdown("##### 🛡️ Gestão de Risco")
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_rx")
            lupa_alvo = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not usar_alvo_rx, key="i_tr_alvo")
            usar_stop_rx = st.toggle("🛡️ Stop Loss Fixo", value=False, key="tg_stop_rx")
            lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, disabled=not usar_stop_rx, key="i_tr_stop")
            usar_saida_st_rx = st.toggle("📉 Saída pela Reversão (ST)", value=True, key="tg_st_rx")
            usar_saida_dmi_rx = st.toggle("📉 Saída Reversão DMI (+DI < -DI)", value=False, key="tg_dmi_rx")

    if st.button("🔍 Gerar Raio-X da Máquina", type="primary", use_container_width=True, key="i_tr_btn"):
        intervalo_tv = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        alvo_d, stop_d = lupa_alvo / 100.0, lupa_stop / 100.0

        with st.spinner(f'Processando matemática pesada para {ativo_rx}...'):
            try:
                exc = 'BITSTAMP' if 'BTC' in ativo_rx else 'BMFBOVESPA'
                df_full = tv.get_hist(symbol=ativo_rx, exchange=exc, interval=intervalo_tv, n_bars=5000)
                
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, lupa_adx_len, lupa_st_len, lupa_st_mult)
                    
                    if df_full is not None:
                        data_atual_dt = df_full.index[-1]
                        offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                        data_corte = data_atual_dt - pd.DateOffset(months=offset_map.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]

                        df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                        col_dt = df_b.columns[0]

                        trades, em_pos, vitorias, derrotas, posicao_atual = [], False, 0, 0, None

                        for i in range(1, len(df_b)):
                            # === GATILHO ESTrito DE COMPRA (Aba 2) ===
                            adx_cruzou_di_menos = (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i])
                            di_mais_acima = df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]
                            st_verde = df_b['ST_Dir'].iloc[i] == 1
                            
                            sinal = adx_cruzou_di_menos and di_mais_acima and st_verde
                            
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

                        # STATUS ATUAL
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
                            st.success(f"✅ **{ativo_rx}: Aguardando Alinhamento do SuperTrend + DMI + ADX**")

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
                        else:
                            st.info("Nenhum trade fechado no período de estudo selecionado.")
                else:
                    st.error("Base de dados vazia para este ativo no TradingView.")
            except Exception as e: st.error(f"Erro no processamento: {e}")

# ==========================================
# ABA 3: RAIO-X FUTUROS (DAY TRADE / WIN e WDO)
# ==========================================
with aba_futuros:
    st.subheader("📉 Raio-X Mercado Futuro (O Trator do Intraday)")
    st.markdown("Teste a estratégia no Índice ou Dólar (ou Cripto). Entradas blindadas, saída com alvo em pontos e zeragem automática.")
    
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        mapa_fut = {"WINFUT (Mini Índice)": "WIN1!", "WDOFUT (Mini Dólar)": "WDO1!", "BITCOIN (Cripto)": "BTCUSD"}
        f_selecionado = st.selectbox("Selecione o Ativo:", options=list(mapa_fut.keys()), key="f_tr_ativo")
        f_ativo = mapa_fut[f_selecionado] 
        f_dir = st.selectbox("Direção do Trade:", ["Ambas", "Apenas Compra", "Apenas Venda"], key="f_tr_dir")
        f_tmp = st.selectbox("Tempo Gráfico:", ['15m', '60m'], key="f_tr_tmp")
    with cf2:
        st.markdown("##### ⚙️ ADX / DMI")
        f_adx_len = st.number_input("Período ADX:", value=14, key="f_tr_adx")
        
        st.markdown("##### ⚙️ SuperTrend")
        c_f1, c_f2 = st.columns(2)
        f_st_len = c_f1.number_input("Período ST:", value=10, key="f_tr_st")
        f_st_mult = c_f2.number_input("Mult ST:", value=3.0, step=0.1, key="f_tr_stm")
    with cf3:
        f_alvo = st.number_input("Alvo (Pontos):", value=300 if "WIN" in f_selecionado else 10, step=50, key="f_tr_alvo")
        f_contratos = st.number_input("Contratos/Lotes:", value=1, step=1, key="f_tr_cont")
        
        val_m = 0.20 if "WIN" in f_selecionado else (10.0 if "WDO" in f_selecionado else 1.0)
        f_multi = st.number_input("Valor R$ por Ponto:", value=val_m, key="f_tr_mult")
        f_zerar = st.checkbox("⏰ Zeragem Auto. Fim do Dia", value=True, key="f_tr_zerar")
        f_saida_dmi = st.checkbox("📉 Saída Reversão DMI", value=False, key="f_tr_sdmi")
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_fut = st.button("🚀 Gerar Raio-X Futuros", type="primary", use_container_width=True, key="f_tr_btn")

    if btn_fut:
        intervalo_tv = tradutor_intervalo.get(f_tmp, Interval.in_15_minute)
        
        with st.spinner(f'Simulando Tanque de Guerra em {f_selecionado}...'):
            try:
                exc = 'BITSTAMP' if 'BTC' in f_ativo else 'BMFBOVESPA'
                df_full = tv.get_hist(symbol=f_ativo, exchange=exc, interval=intervalo_tv, n_bars=10000)
                if df_full is not None:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_indicadores_trend(df_full, f_adx_len, f_st_len, f_st_mult)
                    
                    if df_full is not None:
                        trades, posicao = [], 0 
                        vits, derrs = 0, 0
                        df_b = df_full.reset_index()
                        col_dt = df_b.columns[0]

                        for i in range(1, len(df_b)):
                            d_at, d_ant = df_b[col_dt].iloc[i], df_b[col_dt].iloc[i-1]
                            
                            # === GATILHO ESTrito DE COMPRA ===
                            adx_cruzou_di_menos = (df_b['ADX'].iloc[i] > df_b['-DI'].iloc[i]) and (df_b['ADX_Prev'].iloc[i] <= df_b['-DI_Prev'].iloc[i])
                            di_mais_acima = df_b['+DI'].iloc[i] > df_b['-DI'].iloc[i]
                            st_verde = df_b['ST_Dir'].iloc[i] == 1
                            sinal_compra = adx_cruzou_di_menos and di_mais_acima and st_verde
                            
                            # === GATILHO ESTrito DE VENDA ===
                            adx_cruzou_di_mais = (df_b['ADX'].iloc[i] > df_b['+DI'].iloc[i]) and (df_b['ADX_Prev'].iloc[i] <= df_b['+DI_Prev'].iloc[i])
                            di_menos_acima = df_b['-DI'].iloc[i] > df_b['+DI'].iloc[i]
                            st_vermelho = df_b['ST_Dir'].iloc[i] == -1
                            sinal_venda = adx_cruzou_di_mais and di_menos_acima and st_vermelho

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
                            
                            if sinal_compra and posicao == 0 and f_dir != "Apenas Venda":
                                posicao, d_ent, p_ent = 1, d_at, df_b['Close'].iloc[i]
                                take_p = p_ent + f_alvo
                            elif sinal_venda and posicao == 0 and f_dir != "Apenas Compra":
                                posicao, d_ent, p_ent = -1, d_at, df_b['Close'].iloc[i]
                                take_p = p_ent - f_alvo

                        st.divider()
                        if trades:
                            df_res = pd.DataFrame(trades)
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Lucro Total Estimado", f"R$ {df_res['Lucro (R$)'].sum():,.2f}")
                            m2.metric("Total de Tiros (Operações)", len(df_res))
                            m3.metric("Taxa de Acerto", f"{(vits/len(df_res)*100):.1f}%")
                            m4.metric("Saldo de Pontos", f"{df_res['Pontos'].sum():.0f}")
                            
                            st.dataframe(df_res, use_container_width=True, hide_index=True)
                        else:
                            st.warning("A Máquina não disparou nenhum tiro no período (Nenhum alinhamento exato de Cruzamento ADX+SuperTrend encontrado).")
            except Exception as e: st.error(f"Erro no processamento da blindagem: {e}")
