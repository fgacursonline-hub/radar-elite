import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import streamlit.components.v1 as components
import pandas as pd
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
st.set_page_config(page_title="Duplo CCI Elite", layout="wide", page_icon="🎯")

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
# 3. MOTOR MATEMÁTICO: DUPLO CCI (NATIVO & BLINDADO)
# ==========================================
def calcular_duplo_cci(df, cci_longo=50, cci_curto=14):
    try:
        if df.empty or len(df) < max(cci_longo, cci_curto) + 5:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        
        # Garante que as colunas são float e não strings perdidas
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col].astype(float)
        
        # FUNÇÃO NATIVA DE CCI (À prova de falhas de bibliotecas externas)
        def calc_cci(d_frame, per):
            tp = (d_frame['High'] + d_frame['Low'] + d_frame['Close']) / 3.0
            sma_tp = tp.rolling(window=per).mean()
            # Mean Absolute Deviation
            mad = tp.rolling(window=per).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            return (tp - sma_tp) / (0.015 * mad)
        
        # Injeta os CCIs no DataFrame
        df['CCI_Longo'] = calc_cci(df, cci_longo)
        df['CCI_Curto'] = calc_cci(df, cci_curto)
        
        # Limpa os NaNs iniciais da matemática rolante
        df = df.dropna(subset=['CCI_Longo', 'CCI_Curto']).copy()
        
        # Regra de Compra: Tendência Longa de Alta (CCI Longo > 0) + Gatilho Curto cruzando ZERO pra cima
        tendencia_alta = df['CCI_Longo'] > 0
        gatilho_compra = (df['CCI_Curto'] > 0) & (df['CCI_Curto'].shift(1) <= 0)
        df['Cruzou_Compra'] = tendencia_alta & gatilho_compra
        
        # Regra de Saída (Reversão): CCI Curto perde a força e cruza ZERO para baixo
        df['Cruzou_Venda'] = (df['CCI_Curto'] < 0) & (df['CCI_Curto'].shift(1) >= 0)
        
        return df
    except Exception as e:
        # Alarme de emergência: se o Python quebrar a matemática, ele grita na tela.
        st.error(f"Erro Crítico de Matemática no Motor Duplo CCI: {e}")
        return None

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

st.title("🎯 Máquina Quantitativa: Duplo CCI")
st.info("📊 **Estratégia (Filtro de Tendência + Gatilho):** Usa duas velocidades de CCI para limpar o ruído. \n\n🟢 **Gatilho de Compra:** O CCI Longo precisa estar acima de ZERO (tendência de alta confirmada) no exato momento em que o CCI Curto cruza o ZERO de baixo para cima (explosão de momento). \n🔴 **Defesas Opcionais:** Desligue Stop, Alvo e Reversão (CCI Curto < 0) para gerir sua operação livremente.")

aba_padrao, aba_individual = st.tabs(["📡 Radar Padrão (Scanner Global)", "🔬 Raio-X Individual (Laboratório)"])

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
            tempo_tr = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="tr_tmp")
            periodo_tr = st.selectbox("Histórico (Backtest):", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="tr_per")
        with c3:
            st.markdown("##### ⚙️ Setup Duplo CCI")
            cci_l_g = st.number_input("CCI Longo (Tendência):", min_value=10, value=50, step=1, key="tr_cci_l")
            cci_s_g = st.number_input("CCI Curto (Gatilho):", min_value=2, value=14, step=1, key="tr_cci_s")
        with c4:
            st.markdown("##### 🛡️ Gestão Opcional")
            usar_alvo_g = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_g")
            alvo_g = st.number_input("Alvo (%):", value=15.0, step=1.0, disabled=not usar_alvo_g, key="val_alvo_g")
            usar_stop_g = st.toggle("🛡️ Stop Loss Fixo", value=False, key="tg_stop_g")
            stop_g = st.number_input("Stop Loss (%):", value=5.0, step=1.0, disabled=not usar_stop_g, key="val_stop_g")
            usar_saida_rev_g = st.toggle("📉 Saída Reversão (CCI Curto < 0)", value=True, key="tg_rev_g")

    btn_iniciar_tr = st.button("🚀 Iniciar Varredura Duplo CCI", type="primary", use_container_width=True, key="tr_btn")

    if btn_iniciar_tr:
        intervalo_tv = tradutor_intervalo.get(tempo_tr, Interval.in_daily)
        ativos_tr = bdrs_elite if lista_tr == "BDRs Elite" else ibrx_selecao if lista_tr == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        ativos_tr = sorted(list(set([a.replace('.SA', '') for a in ativos_tr])))
        
        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo in enumerate(ativos_tr):
            s_text.text(f"🔍 Calculando Duplo CCI: {ativo} ({idx+1}/{len(ativos_tr)})")
            p_bar.progress((idx + 1) / len(ativos_tr))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=3000)
                if df_full is None or len(df_full) < 50: continue
                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                df_full = calcular_duplo_cci(df_full, cci_l_g, cci_s_g)
                if df_full is None: continue

                data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo':1, '3mo':3, '6mo':6, '1y':12, '2y':24, '5y':60}.get(periodo_tr, 120)) if periodo_tr != 'max' else df_full.index[0]
                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                min_price_in_trade = 0.0

                alvo_d = alvo_g / 100.0
                stop_d = stop_g / 100.0

                for i in range(1, len(df_back)):
                    sinal_compra = df_back['Cruzou_Compra'].iloc[i]
                    
                    if em_pos:
                        if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                        
                        bateu_alvo = usar_alvo_g and (df_back['High'].iloc[i] >= take_profit)
                        bateu_stop = usar_stop_g and (df_back['Low'].iloc[i] <= stop_price)
                        reverteu_st = usar_saida_rev_g and df_back['Cruzou_Venda'].iloc[i]
                        
                        if bateu_stop:
                            trades.append({'Lucro (R$)': -(float(capital_tr) * stop_d), 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            em_pos = False; continue
                        elif bateu_alvo:
                            trades.append({'Lucro (R$)': float(capital_tr) * alvo_d, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
                            em_pos = False; continue
                        elif reverteu_st:
                            lucro_rs = float(capital_tr) * ((df_back['Close'].iloc[i] / preco_entrada) - 1)
                            trades.append({'Lucro (R$)': lucro_rs, 'Drawdown_Raw': ((min_price_in_trade / preco_entrada) - 1) * 100})
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
                    if hoje['Cruzou_Compra']:
                        ls_sinais.append({'Ativo': ativo, 'Preço Atual': f"R$ {hoje['Close']:.2f}", 'CCI': f"Alinhado 🟢"})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    ls_resumo.append({'Ativo': ativo, 'Trades': len(df_t), 'Pior Queda': f"{df_t['Drawdown_Raw'].min():.2f}%", 'Lucro R$': df_t['Lucro (R$)'].sum()})
            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty(); p_bar.empty()

        st.subheader(f"🚀 Sinais de Ignição Hoje (Ambos CCI Alinhados)")
        if len(ls_sinais) > 0: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else: st.info("Nenhum cruzamento direcional validado hoje.")

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
# ABA 2: RAIO-X INDIVIDUAL (O LABORATÓRIO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Análise Detalhada Duplo CCI")
    
    with st.container(border=True):
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            ativo_rx = st.selectbox("Ativo a Testar:", ativos_para_rastrear, key="i_tr_ativo")
            capital_rx = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0, key="i_tr_cap")
        with ci2:
            tempo_rx = st.selectbox("Tempo Gráfico:", options=['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="i_tr_tmp")
            periodo_rx = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="i_tr_per")
        with ci3:
            st.markdown("##### ⚙️ Calibragem CCI")
            lupa_cci_l = st.number_input("CCI Longo (Tendência):", min_value=10, value=50, key="i_tr_ccil")
            lupa_cci_s = st.number_input("CCI Curto (Gatilho):", min_value=2, value=14, key="i_tr_ccis")
        with ci4:
            st.markdown("##### 🛡️ Gestão Opcional")
            usar_alvo_rx = st.toggle("🎯 Alvo Fixo", value=True, key="tg_alvo_rx")
            lupa_alvo = st.number_input("Alvo (%):", value=15.0, step=0.5, disabled=not usar_alvo_rx, key="i_tr_alvo")
            usar_stop_rx = st.toggle("🛡️ Stop Loss Fixo", value=False, key="tg_stop_rx")
            lupa_stop = st.number_input("Stop Loss (%):", value=5.0, step=0.5, disabled=not usar_stop_rx, key="i_tr_stop")
            usar_saida_rev_rx = st.toggle("📉 Saída Reversão (CCI Curto < 0)", value=True, key="tg_rev_rx")

    if st.button("🔍 Gerar Raio-X Duplo CCI", type="primary", use_container_width=True, key="i_tr_btn"):
        intervalo_tv = tradutor_intervalo.get(tempo_rx, Interval.in_daily)
        alvo_d, stop_d = lupa_alvo / 100.0, lupa_stop / 100.0

        with st.spinner(f'Calculando força de tendência para {ativo_rx}...'):
            try:
                df_full = tv.get_hist(symbol=ativo_rx, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                
                if df_full is not None and len(df_full) > 50:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = calcular_duplo_cci(df_full, lupa_cci_l, lupa_cci_s)
                    
                    if df_full is not None:
                        data_corte = df_full.index[-1] - pd.DateOffset(months={'1mo':1, '3mo':3, '6mo':6, '1y':12, '2y':24, '5y':60}.get(periodo_rx, 120)) if periodo_rx != 'max' else df_full.index[0]
                        df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                        col_dt = df_b.columns[0]

                        trades, em_pos, vitorias, derrotas, posicao_atual = [], False, 0, 0, None

                        for i in range(1, len(df_b)):
                            sinal = df_b['Cruzou_Compra'].iloc[i]
                            
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
                                reverteu_st = usar_saida_rev_rx and df_b['Cruzou_Venda'].iloc[i]
                                
                                saiu = False
                                if bateu_stop:
                                    lucro = -(float(capital_rx) * stop_d)
                                    derrotas += 1; situacao = "Stop ❌"; saiu = True
                                elif bateu_alvo:
                                    lucro = float(capital_rx) * alvo_d
                                    vitorias += 1; situacao = "Alvo ✅"; saiu = True
                                elif reverteu_st:
                                    lucro = float(capital_rx) * ((df_b['Close'].iloc[i] / p_ent) - 1)
                                    if lucro > 0: vitorias += 1; situacao = "Saída CCI < 0 ✅"
                                    else: derrotas += 1; situacao = "Reversão ❌"
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
                            
                            st.caption(f"🛡️ *Defesas Ativas:* Alvo: {'ON' if usar_alvo_rx else 'OFF'} | Stop Fixo: {'ON' if usar_stop_rx else 'OFF'} | Saída Reversão: {'ON' if usar_saida_rev_rx else 'OFF'}")

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
                            st.success(f"✅ **{ativo_rx}: Aguardando Gatilho (CCI Curto cruzar Zero).**")

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
                        
                        st.divider()
                        st.markdown(f"### 📈 Gráfico Interativo: {ativo_rx}")
                        renderizar_grafico_tv(f"BMFBOVESPA:{ativo_rx}")
                else:
                    st.error("Base de dados vazia para este ativo no TradingView.")
            except Exception as e: 
                st.error(f"⚠️ Erro de processamento no ativo {ativo_rx}: {e}")
