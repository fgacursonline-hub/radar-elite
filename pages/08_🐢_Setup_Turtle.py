import streamlit as st
import streamlit.components.v1 as components
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import pandas_ta as ta
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SEGURANÇA E BLOQUEIO
# ==========================================
if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

tradutor_periodo_nome = {
    '6mo': '6 Meses', '1y': '1 Ano', '2y': '2 Anos', 
    '5y': '5 Anos', '10y': '10 Anos', 'max': 'Máximo'
}

bdrs_elite = [
    'NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 'TSLA34.SA',
    'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 'MSFT34.SA', 'MUTC34.SA',
    'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA',
    'ITLC34.SA', 'AVGO34.SA', 'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA',
    'STOC34.SA'
]

ibrx_selecao = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA',
    'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 'EQTL3.SA', 'LREN3.SA',
    'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA',
    'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA',
    'VIVT3.SA', 'KLBN11.SA', 'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA',
    'ISAE3.SA', 'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA',
    'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 'YDUQ3.SA',
    'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 'BRAV3.SA', 'EZTC3.SA',
    'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA',
    'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA',
    'LIGT3.SA', 'LOGG3.SA', 'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA',
    'ROMI3.SA', 'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA',
    'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 'CSMG3.SA',
    'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 'ITSA3.SA', 'ALUP11.SA',
    'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA',
    'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA',
    'SHUL4.SA', 'BRSR6.SA',
]

def colorir_lucro(row):
    try:
        val_str = str(row.get('Resultado Atual', row.get('Lucro (R$)', '0')))
        val = float(val_str.replace('R$', '').replace('%', '').replace('+', '').replace(',', '').strip())
        cor = 'lightgreen' if val > 0 else 'lightcoral' if val < 0 else 'white'
        return [f'color: {cor}'] * len(row)
    except: return [''] * len(row)

def renderizar_grafico_tv(simbolo_tv, altura=600):
    html_tv = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_turtle"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
      "width": "100%",
      "height": {altura},
      "symbol": "{simbolo_tv}",
      "interval": "D",
      "timezone": "America/Sao_Paulo",
      "theme": "dark",
      "style": "1",
      "locale": "br",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": "tradingview_turtle"
    }}
      );
      </script>
    </div>
    """
    components.html(html_tv, height=altura)

# ==========================================
# 2. INTERFACE DE ABAS
# ==========================================
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.title("🐢 O Sistema Turtle (Trend Following)")
with col_botao:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.link_button("📖 Ler Regras", "https://seusite.com/manual_turtle", use_container_width=True)

aba_radar, aba_individual = st.tabs(["📡 Radar do Cardume (Varredura)", "🔬 Raio-X Individual"])

# ==========================================
# ABA 1: RADAR DO CARDUME
# ==========================================
with aba_radar:
    st.markdown("Varredura de quebra de máximas históricas usando as regras puras de Richard Dennis.")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["IBrX Seleção", "BDRs Elite", "Todos"], key="rad_tur_lst")
    with c2:
        sistema_sel = st.selectbox("Sistema Turtle:", ["Sistema 1 (20 Ent / 10 Sai)", "Sistema 2 (55 Ent / 20 Sai)"], key="rad_tur_sys")
    with c3:
        periodo_sel = st.selectbox("Período Histórico:", ['1y', '2y', '5y', '10y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="rad_tur_per")
    with c4:
        capital_sel = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="rad_tur_cap")

    btn_iniciar = st.button("🚀 Iniciar Varredura de Rompimentos", type="primary", use_container_width=True)

    if btn_iniciar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        
        janela_entrada = 20 if "Sistema 1" in sistema_sel else 55
        janela_saida = 10 if "Sistema 1" in sistema_sel else 20

        ls_armados, ls_abertos, ls_resumo = [], [], []
        p_bar = st.progress(0); s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Caçando tendências em {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=5000)
                if df_full is None or len(df_full) < janela_entrada * 2: continue

                df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # --- CÁLCULO DOS CANAIS DE DONCHIAN (Regras Turtle) ---
                df_full['Canal_Compra'] = df_full['High'].rolling(window=janela_entrada).max().shift(1)
                df_full['Canal_Venda'] = df_full['Low'].rolling(window=janela_saida).min().shift(1)
                df_full = df_full.dropna()

                if periodo_sel == 'max': data_corte = df_full.index[0]
                else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(periodo_sel.replace('y','')))
                
                df = df_full[df_full.index >= data_corte].copy().reset_index()
                col_data = df.columns[0]

                em_pos = False
                preco_entrada = 0.0
                vitorias, total_trades, lucro_total = 0, 0, 0.0

                for i in range(1, len(df)):
                    atual = df.iloc[i]

                    if em_pos:
                        # Regra de Saída: Rompeu a mínima de N dias?
                        if atual['Low'] <= atual['Canal_Venda']:
                            preco_saida = min(atual['Canal_Venda'] - 0.01, atual['Open'])
                            lucro_rs = capital_sel * ((preco_saida / preco_entrada) - 1)
                            lucro_total += lucro_rs
                            total_trades += 1
                            if lucro_rs > 0: vitorias += 1
                            em_pos = False
                    else:
                        # Regra de Entrada: Rompeu a máxima de N dias?
                        if atual['High'] >= atual['Canal_Compra']:
                            em_pos = True
                            preco_entrada = max(atual['Canal_Compra'] + 0.01, atual['Open'])
                            d_ent = atual[col_data]

                if em_pos:
                    cot_atual = df['Close'].iloc[-1]
                    res_pct = ((cot_atual / preco_entrada) - 1) * 100
                    stop_atual = df['Canal_Venda'].iloc[-1]
                    ls_abertos.append({
                        'Ativo': ativo, 'Dias Surfando': (df[col_data].iloc[-1] - d_ent).days,
                        'PM': f"R$ {preco_entrada:.2f}", 'Stop Móvel (Saída)': f"R$ {stop_atual:.2f}",
                        'Cotação': f"R$ {cot_atual:.2f}", 'Resultado Atual': f"+{res_pct:.2f}%" if res_pct > 0 else f"{res_pct:.2f}%"
                    })
                else:
                    # Verifica se armou HOJE
                    hoje = df.iloc[-1]
                    distancia = ((hoje['Canal_Compra'] / hoje['Close']) - 1) * 100
                    if distancia > 0 and distancia < 2.0: # Está a menos de 2% de romper
                        ls_armados.append({
                            'Ativo': ativo, 'Gatilho de Compra': f"R$ {hoje['Canal_Compra'] + 0.01:.2f}",
                            'Distância Atual': f"{distancia:.2f}%", 'Status': "Pronto para Romper"
                        })

                if total_trades > 0:
                    ls_resumo.append({
                        'Ativo': ativo, 'Trades': total_trades, 'Acertos': f"{(vitorias/total_trades)*100:.1f}%", 'Lucro Total R$': lucro_total
                    })

            except Exception as e: pass
            time.sleep(0.01)

        s_text.empty(); p_bar.empty()
        
        st.divider()
        st.subheader(f"🚀 Quase Rompendo! (Gatilhos a menos de 2% da máxima de {janela_entrada}d)")
        if ls_armados: st.dataframe(pd.DataFrame(ls_armados).sort_values(by='Distância Atual'), use_container_width=True, hide_index=True)
        else: st.info("Nenhum ativo próximo do ponto de explosão hoje.")

        st.subheader(f"🌊 Posições Abertas (Surfando a Tendência)")
        if ls_abertos: st.dataframe(pd.DataFrame(ls_abertos).style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.info("Sua carteira está limpa.")

        st.subheader(f"🏆 Top 20 Histórico Turtle ({tradutor_periodo_nome[periodo_sel]})")
        if ls_resumo:
            df_hist = pd.DataFrame(ls_resumo).sort_values(by='Lucro Total R$', ascending=False).head(20)
            df_hist['Lucro Total R$'] = df_hist['Lucro Total R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

# ==========================================
# ABA 2: RAIO-X INDIVIDUAL
# ==========================================
with aba_individual:
    st.subheader("🔬 Laboratório Turtle (Estresse do Sistema)")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: rx_ativo = st.text_input("Ativo (Ex: PRIO3):", value="PRIO3", key="rx_tur_atv").upper().replace('.SA', '')
    with col2: rx_sys = st.selectbox("Sistema:", ["Sistema 1 (20/10)", "Sistema 2 (55/20)"], key="rx_tur_sys")
    with col3: rx_per = st.selectbox("Período de Backtest:", ['1y', '2y', '5y', '10y', 'max'], index=2, format_func=lambda x: tradutor_periodo_nome[x], key="rx_tur_per")
    with col4: rx_cap = st.number_input("Capital (R$):", value=10000.0, step=1000.0, key="rx_tur_cap")

    btn_rx = st.button("🔍 Iniciar Backtest Turtle", type="primary", use_container_width=True)

    if btn_rx and rx_ativo:
        janela_ent = 20 if "Sistema 1" in rx_sys else 55
        janela_sai = 10 if "Sistema 1" in rx_sys else 20
        
        with st.spinner(f'Calculando a matemática das Tartarugas em {rx_ativo}...'):
            try:
                df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=5000)
                if df_full is None or len(df_full) < janela_ent * 2: st.error("Dados insuficientes.")
                else:
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full['Canal_Compra'] = df_full['High'].rolling(window=janela_ent).max().shift(1)
                    df_full['Canal_Venda'] = df_full['Low'].rolling(window=janela_sai).min().shift(1)
                    df_full = df_full.dropna()

                    if rx_per == 'max': data_corte = df_full.index[0]
                    else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rx_per.replace('y','')))
                    df = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_data = df.columns[0]

                    trades, em_pos, vitorias = [], False, 0
                    preco_entrada = 0.0

                    for i in range(1, len(df)):
                        atual = df.iloc[i]
                        if em_pos:
                            if atual['Low'] <= atual['Canal_Venda']:
                                preco_saida = min(atual['Canal_Venda'] - 0.01, atual['Open'])
                                luc_rs = rx_cap * ((preco_saida / preco_entrada) - 1)
                                trades.append({
                                    'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'),
                                    'Duração (Dias)': (atual[col_data] - d_ent).days, 'Lucro (R$)': luc_rs,
                                    'Situação': 'Gain ✅' if luc_rs > 0 else 'Loss ❌'
                                })
                                if luc_rs > 0: vitorias += 1
                                em_pos = False
                        else:
                            if atual['High'] >= atual['Canal_Compra']:
                                em_pos = True
                                preco_entrada = max(atual['Canal_Compra'] + 0.01, atual['Open'])
                                d_ent = atual[col_data]

                    st.divider()
                    st.markdown(f"### 📊 Resultado Turtle: {rx_ativo} ({rx_sys})")
                    
                    url_tv_turtle = f"https://br.tradingview.com/chart/?symbol=BMFBOVESPA%3A{rx_ativo}"
                    st.markdown(f"<a href='{url_tv_turtle}' target='_blank' style='text-decoration: none; font-size: 14px; color: #4da6ff;'>🔗 Abrir no TradingView</a>", unsafe_allow_html=True)
                    
                    if trades:
                        df_t = pd.DataFrame(trades)
                        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                        l_tot = df_t['Lucro (R$)'].sum()
                        
                        m_ganho = df_t[df_t['Lucro (R$)'] > 0]['Lucro (R$)'].mean() if vitorias > 0 else 0
                        m_perda = abs(df_t[df_t['Lucro (R$)'] <= 0]['Lucro (R$)'].mean()) if (len(df_t) - vitorias) > 0 else 1
                        payoff = m_ganho / m_perda
                        
                        c_m1.metric("Lucro Total", f"R$ {l_tot:,.2f}")
                        c_m2.metric("Operações Fechadas", len(df_t))
                        c_m3.metric("Taxa de Acerto", f"{(vitorias/len(df_t))*100:.1f}%")
                        c_m4.metric("Payoff (Risco/Retorno)", f"{payoff:.2f}")

                        if payoff > 2.0 and l_tot > 0: st.success("🎯 **Excelente!** O sistema confirmou o seu poder. Poucos acertos, mas vitórias esmagadoras que cobrem as perdas.")
                        elif l_tot < 0: st.error("🚨 **Cuidado:** Este ativo passou os últimos anos lateralizado. O sistema Turtle sangra quando não há tendência clara.")

                        st.dataframe(df_t.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhuma operação finalizada.")
                        
                    # Integração do Gráfico
                    st.divider()
                    st.markdown(f"### 📈 Gráfico Interativo: {rx_ativo}")
                    renderizar_grafico_tv(f"BMFBOVESPA:{rx_ativo}")

            except Exception as e: st.error(f"Erro ao processar: {e}")
