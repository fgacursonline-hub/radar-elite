import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E BLOQUEIO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# IMPORTAÇÃO CENTRALIZADA DOS ATIVOS E MOTOR
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

todos_ativos = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

tradutor_periodo_nome = {
    '1mo': '1 Mês', '3mo': '3 Meses', '6mo': '6 Meses',
    '1y': '1 Ano', '2y': '2 Anos', '5y': '5 Anos', 'max': 'Máximo'
}

def colorir_lucro(row):
    if 'Resultado Atual' in row and isinstance(row['Resultado Atual'], str) and row['Resultado Atual'].startswith('+'):
        return ['color: #00FF00; font-weight: bold'] * len(row)
    if 'Situação' in row and isinstance(row['Situação'], str) and 'Gain' in row['Situação']:
        return ['color: #2eeb5c; font-weight: bold'] * len(row)
    return [''] * len(row)

# ==========================================
# 2. MOTORES MATEMÁTICOS (HULL SUITE)
# ==========================================
def calcular_hull_suite(df, mode, length, src_col='Close'):
    """
    Réplica exata da matemática do InSilico/DashTrader
    """
    if df is None or len(df) < length + 5:
        return df
        
    src = df[src_col]
    
    try:
        if mode == 'HMA (Padrão)':
            half_len = max(1, int(length / 2))
            sqrt_len = max(1, int(np.round(np.sqrt(length))))
            wmaf = ta.wma(src, length=half_len)
            wmas = ta.wma(src, length=length)
            raw_hull = 2 * wmaf - wmas
            df['HULL'] = ta.wma(raw_hull, length=sqrt_len)
            
        elif mode == 'EHMA (Exponencial Rápida)':
            half_len = max(1, int(length / 2))
            sqrt_len = max(1, int(np.round(np.sqrt(length))))
            emaf = ta.ema(src, length=half_len)
            emas = ta.ema(src, length=length)
            raw_hull = 2 * emaf - emas
            df['HULL'] = ta.ema(raw_hull, length=sqrt_len)
            
        elif mode == 'THMA (Tripla Suavizada)':
            third_len = max(1, int(length / 3))
            half_len = max(1, int(length / 2))
            wma3 = ta.wma(src, length=third_len)
            wma2 = ta.wma(src, length=half_len)
            wma1 = ta.wma(src, length=length)
            raw_hull = (wma3 * 3) - wma2 - wma1
            df['HULL'] = ta.wma(raw_hull, length=length)
            
        # Lógica de Gatilho do PineScript: HULL[0] > HULL[2]
        df['HULL_2'] = df['HULL'].shift(2)
        df['HULL_2_Prev'] = df['HULL_2'].shift(1)
        df['HULL_Prev'] = df['HULL'].shift(1)
        
        df = df.dropna()
    except:
        pass
        
    return df

def renderizar_grafico_tv(simbolo_tv, altura=600):
    html_tv = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_hull"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
      "width": "100%", "height": {altura}, "symbol": "{simbolo_tv}", "interval": "D", 
      "timezone": "America/Sao_Paulo", "theme": "dark", "style": "1", "locale": "br", 
      "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_hull"
      }});
      </script>
    </div>
    """
    components.html(html_tv, height=altura)

# ==========================================
# 3. INTERFACE DA PÁGINA
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo: st.title("🛳️ Estratégia: Hull Suite")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Manual", "https://seusite.com/manual_hull", use_container_width=True)

st.info("📊 **Trend Following sem Atraso:** A Hull Suite elimina a lentidão das médias tradicionais. O robô dispara compra no momento em que a inclinação da linha vira para cima (fica verde). A saída ocorre no Alvo de Lucro ou se a linha virar para baixo (sinal vermelho), o que atua como um Stop Loss técnico dinâmico.")

aba_radar, aba_raiox = st.tabs(["📡 Radar (Caçador de Tendências)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR PADRÃO (HULL SUITE)
# ==========================================
with aba_radar:
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_hull = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="h_lista")
        ativos_hull = bdrs_elite if lista_hull == "BDRs Elite" else ibrx_selecao if lista_hull == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        periodo_estudo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="h_per")
    with c2:
        modo_hull = st.selectbox("Motor da Hull:", ["HMA (Padrão)", "EHMA (Exponencial Rápida)", "THMA (Tripla Suavizada)"], index=0, key="h_modo")
        periodo_hull = st.number_input("Período da Linha:", min_value=2, max_value=300, value=55, step=1, key="h_len", help="55 é o padrão institucional para Swing Trade.")
    with c3:
        alvo_lucro = st.number_input("Alvo de Lucro (%):", value=10.0, step=1.0, key="h_alvo")
        capital_trade = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="h_cap")
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="h_tmp")

    btn_iniciar = st.button("🚀 Iniciar Varredura Hull", type="primary", use_container_width=True)

    if btn_iniciar:
        alvo_dec = alvo_lucro / 100
        ls_sinais, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_txt = st.empty()

        for idx, ativo_raw in enumerate(ativos_hull):
            ativo = ativo_raw.replace('.SA', '')
            s_txt.text(f"🔍 Escaneando Tendência: {ativo} ({idx+1}/{len(ativos_hull)})")
            p_bar.progress((idx + 1) / len(ativos_hull))

            try:
                df_full = puxar_dados_blindados(ativo, tempo_grafico=tempo_grafico, barras=2000)
                df_full = calcular_hull_suite(df_full, modo_hull, periodo_hull)
                
                if df_full is None or df_full.empty: continue

                data_atual = df_full.index[-1]
                offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60, '60d': 2}
                data_corte = data_atual - pd.DateOffset(months=offset_map.get(periodo_estudo, 120)) if periodo_estudo != 'max' else df_full.index[0]

                df = df_full[df_full.index >= data_corte].copy()
                if len(df) == 0: continue

                trades, em_pos = [], False
                df_back = df.reset_index()
                col_data = df_back.columns[0]
                vit, der = 0, 0

                for i in range(1, len(df_back)):
                    linha = df_back.iloc[i]
                    
                    if em_pos:
                        if linha['Low'] < min_price_in_trade:
                            min_price_in_trade = linha['Low']
                            
                        # 1. Checa Alvo
                        if linha['High'] >= take_profit:
                            trades.append({'Lucro (R$)': float(capital_trade) * alvo_dec, 'Situação': 'Gain'})
                            vit += 1; em_pos = False; continue
                            
                        # 2. Checa Stop Técnico (Linha virou pra baixo: HULL < HULL[2])
                        virou_venda = linha['HULL'] < linha['HULL_2']
                        if virou_venda:
                            resultado_saida = (linha['Close'] / preco_entrada) - 1
                            trades.append({'Lucro (R$)': float(capital_trade) * resultado_saida, 'Situação': 'Stop Técnico'})
                            if resultado_saida > 0: vit += 1
                            else: der += 1
                            em_pos = False; continue

                    # Gatilho de Entrada: Linha virou para cima (Era vermelha, ficou verde)
                    era_vermelha = linha['HULL_Prev'] <= linha['HULL_2_Prev']
                    ficou_verde = linha['HULL'] > linha['HULL_2']
                    
                    if era_vermelha and ficou_verde and not em_pos:
                        em_pos = True
                        d_ent = linha[col_data]
                        preco_entrada = linha['Close']
                        min_price_in_trade = linha['Low']
                        take_profit = preco_entrada * (1 + alvo_dec)

                if em_pos:
                    res_atual = ((df_back['Close'].iloc[-1] / preco_entrada) - 1) * 100
                    ls_abertos.append({
                        'Ativo': ativo, 'Entrada': d_ent.strftime('%d/%m %H:%M') if tempo_grafico in ['15m', '60m'] else d_ent.strftime('%d/%m/%Y'),
                        'PM Compra': f"R$ {preco_entrada:.2f}",
                        'Alvo Armado': f"R$ {take_profit:.2f}",
                        'Cotação Atual': f"R$ {df_back['Close'].iloc[-1]:.2f}",
                        'Resultado Atual': f"+{res_atual:.2f}%" if res_atual > 0 else f"{res_atual:.2f}%"
                    })
                else:
                    hoje = df_full.iloc[-1]
                    era_verm = hoje['HULL_Prev'] <= hoje['HULL_2_Prev']
                    ficou_vd = hoje['HULL'] > hoje['HULL_2']
                    if era_verm and ficou_vd: 
                        ls_sinais.append({'Ativo': ativo, 'Preço (Gatilho)': f"R$ {hoje['Close']:.2f}", 'Tendência': '🟢 Alta Iniciada'})

                if len(trades) > 0:
                    df_t = pd.DataFrame(trades)
                    lucro_tot = df_t['Lucro (R$)'].sum()
                    invest = float(capital_trade) * len(df_t)
                    tx_acerto = f"{(vit/len(df_t))*100:.1f}%"
                    ls_resumo.append({'Ativo': ativo, 'Trades': len(df_t), 'Taxa Acerto': tx_acerto, 'Lucro R$': lucro_tot})
            except: pass

        s_txt.empty(); p_bar.empty()

        st.subheader(f"🚀 Ignição de Tendência Hoje ({modo_hull} - Período {periodo_hull})")
        if len(ls_sinais) > 0: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo virou a Hull para alta na última barra.")

        st.subheader("⏳ Surfando a Tendência (Aguardando Alvo ou Curva)")
        if len(ls_abertos) > 0:
            st.dataframe(pd.DataFrame(ls_abertos).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_estudo, periodo_estudo)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL
# ==========================================
with aba_raio_x:
    st.subheader("🔬 Raio-X Detalhado: Backtest Hull Suite")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        rx_ativo = st.selectbox("Selecione o Ativo:", todos_ativos, index=todos_ativos.index('PETR4') if 'PETR4' in todos_ativos else 0)
        rx_modo = st.selectbox("Motor da Hull:", ["HMA (Padrão)", "EHMA (Exponencial Rápida)", "THMA (Tripla Suavizada)"])
        rx_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3)
    with col2:
        rx_alvo = st.number_input("Alvo de Lucro (%):", value=10.0, step=1.0)
        rx_len = st.number_input("Período da Linha:", min_value=2, max_value=300, value=55, step=1)
    with col3:
        rx_cap = st.number_input("Capital Base (R$):", value=10000.0, step=1000.0)
        rx_tmp = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk', '1mo'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal', '1mo': 'Mensal'}[x])
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_rx = st.button("🔍 Rodar Análise Completa", type="primary", use_container_width=True)

    if btn_rx:
        with st.spinner(f'Calculando matemática Hull para {rx_ativo}...'):
            try:
                df_full = puxar_dados_blindados(rx_ativo, tempo_grafico=rx_tmp, barras=5000)
                df_full = calcular_hull_suite(df_full, rx_modo, rx_len)
                
                if df_full is not None and not df_full.empty:
                    data_atual = df_full.index[-1]
                    offset_map = {'1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60}
                    data_corte = data_atual - pd.DateOffset(months=offset_map.get(rx_periodo, 120)) if rx_periodo != 'max' else df_full.index[0]

                    df_b = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_dt = df_b.columns[0]
                    
                    trades = []
                    em_pos = False
                    alvo_d = rx_alvo / 100
                    vitorias, derrotas = 0, 0

                    for i in range(1, len(df_b)):
                        linha = df_b.iloc[i]
                        
                        if em_pos:
                            if linha['High'] >= take_p:
                                lucro = float(rx_cap) * alvo_d
                                duracao = (linha[col_dt] - d_ent).days
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': linha[col_dt].strftime('%d/%m/%Y'), 'Duração': duracao, 'Lucro (R$)': lucro, 'Situação': 'Gain ✅ (Alvo)'})
                                vitorias += 1; em_pos = False; continue

                            if linha['HULL'] < linha['HULL_2']:
                                perc_saida = (linha['Close'] / p_ent) - 1
                                lucro = float(rx_cap) * perc_saida
                                duracao = (linha[col_dt] - d_ent).days
                                if lucro > 0:
                                    sit = 'Gain ✅ (Saída Téc.)'
                                    vitorias += 1
                                else:
                                    sit = 'Loss 🔴 (Stop Téc.)'
                                    derrotas += 1
                                trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': linha[col_dt].strftime('%d/%m/%Y'), 'Duração': duracao, 'Lucro (R$)': lucro, 'Situação': sit})
                                em_pos = False; continue

                        era_verm = linha['HULL_Prev'] <= linha['HULL_2_Prev']
                        ficou_vd = linha['HULL'] > linha['HULL_2']
                        if era_verm and ficou_vd and not em_pos:
                            em_pos = True
                            d_ent, p_ent = linha[col_dt], linha['Close']
                            take_p = p_ent * (1 + alvo_d)

                    st.divider()
                    if em_pos:
                        st.warning(f"⚠️ **OPERAÇÃO EM CURSO: {rx_ativo}**")
                        cotacao_atual = df_b['Close'].iloc[-1]
                        dias_em_op = (pd.Timestamp.today().normalize() - d_ent).days
                        res_pct = ((cotacao_atual / p_ent) - 1) * 100
                        res_rs = rx_cap * res_pct / 100

                        c1, c2, c3 = st.columns(3)
                        c1.metric("Data Entrada", d_ent.strftime('%d/%m/%Y'))
                        c2.metric("Preço Compra", f"R$ {p_ent:.2f}")
                        c3.metric("Resultado Atual", f"{res_pct:.2f}%", delta=f"R$ {res_rs:.2f}")
                    else: st.success(f"✅ **{rx_ativo}: Aguardando Virada para Alta**")

                    st.divider()
                    st.markdown(f"### 📊 Resultado: {rx_ativo} ({rx_modo})")
                    
                    if trades:
                        df_t = pd.DataFrame(trades)
                        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                        l_tot = df_t['Lucro (R$)'].sum()
                        tx_acerto = (vitorias/len(df_t))*100
                        
                        m_ganho = df_t[df_t['Lucro (R$)'] > 0]['Lucro (R$)'].mean() if vitorias > 0 else 0
                        m_perda = abs(df_t[df_t['Lucro (R$)'] <= 0]['Lucro (R$)'].mean()) if derrotas > 0 else 1
                        payoff = m_ganho / m_perda
                        
                        c_m1.metric("Lucro Total", f"R$ {l_tot:,.2f}")
                        c_m2.metric("Operações", len(df_t))
                        c_m3.metric("Taxa Acerto", f"{tx_acerto:.1f}%")
                        c_m4.metric("Payoff", f"{payoff:.2f}")

                        st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                    else: st.warning("Nenhuma operação concluída usando essa configuração.")
                        
                    st.divider()
                    st.markdown(f"### 📈 Gráfico Interativo: {rx_ativo}")
                    renderizar_grafico_tv(f"BMFBOVESPA:{rx_ativo}")
                else: st.error("Dados insuficientes para este ativo.")
            except Exception as e: st.error(f"Erro ao processar: {e}")
