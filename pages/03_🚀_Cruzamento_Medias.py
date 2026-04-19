# ==========================================
# ABA 1: RADAR PADRÃO (CRUZAMENTO DINÂMICO & ALVO)
# ==========================================
with aba_padrao:
    st.subheader("📡 Radar Padrão (Cruzamento Universal & Alvo Fixo)")
    st.markdown("O robô compra no exato momento em que a Média Curta cruza a Média Longa para cima, usando a configuração exata que você definir.")
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        lista_cm = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="cm_lista")
        periodo_cm = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=3, key="cm_per")
        capital_cm = st.number_input("Capital por Trade (R$):", value=10000.0, step=1000.0, key="cm_cap")
    with cp2:
        tipo_media_cm = st.selectbox("Tipo de Média:", ["Exponencial (EMA)", "Aritmética (SMA)", "Welles Wilder (RMA)"], index=0, key="cm_tipo")
        curta_cm = st.number_input("Período da Média Curta:", min_value=2, max_value=200, value=16, step=1, key="cm_curta")
        longa_cm = st.number_input("Período da Média Longa:", min_value=3, max_value=200, value=42, step=1, key="cm_longa")
    with cp3:
        alvo_cm = st.number_input("Alvo de Lucro (%):", value=5.0, step=0.5, key="cm_alvo")
        tempo_cm = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="cm_tmp")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Espaçamento para alinhar

    # Trava de Segurança Visual
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
                
                # --- CÁLCULO DAS MÉDIAS DINÂMICAS ---
                if tipo_media_cm == "Exponencial (EMA)":
                    df_full['Curta'] = ta.ema(df_full['Close'], length=curta_cm)
                    df_full['Longa'] = ta.ema(df_full['Close'], length=longa_cm)
                elif tipo_media_cm == "Aritmética (SMA)":
                    df_full['Curta'] = ta.sma(df_full['Close'], length=curta_cm)
                    df_full['Longa'] = ta.sma(df_full['Close'], length=longa_cm)
                else: # Welles Wilder (RMA)
                    df_full['Curta'] = ta.rma(df_full['Close'], length=curta_cm)
                    df_full['Longa'] = ta.rma(df_full['Close'], length=longa_cm)
                
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

                    # CONDIÇÃO DE ENTRADA: Curta cruza Longa para CIMA
                    cruzou_cima = (df_back['Curta'].iloc[i] > df_back['Longa'].iloc[i]) and (df_back['Curta_Prev'].iloc[i] <= df_back['Longa_Prev'].iloc[i])
                    
                    if cruzou_cima and not em_pos:
                        em_pos = True
                        d_ent = df_back[col_data].iloc[i]
                        preco_entrada = df_back['Close'].iloc[i] # Compra no fechamento do candle do cruzamento
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
                    # Sinal de Hoje: Cruzou pra cima na última barra
                    cruzou_hoje = (df_full['Curta'].iloc[-1] > df_full['Longa'].iloc[-1]) and (df_full['Curta_Prev'].iloc[-1] <= df_full['Longa_Prev'].iloc[-1])
                    if cruzou_hoje: 
                        ls_sinais.append({'Ativo': ativo, 'Preço Atual': f"R$ {df_full['Close'].iloc[-1]:.2f}", f'{tipo_media_cm.split()[0]} {curta_cm}': f"{df_full['Curta'].iloc[-1]:.2f}", f'{tipo_media_cm.split()[0]} {longa_cm}': f"{df_full['Longa'].iloc[-1]:.2f}"})

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
        if len(ls_sinais) > 0: st.dataframe(pd.DataFrame(ls_sinais), use_container_width=True, hide_index=True)
        else: st.info(f"Nenhum ativo apresentou cruzamento ({curta_cm}x{longa_cm}) para cima no último candle.")

        st.subheader("⏳ Operações em Andamento (Aguardando Alvo)")
        if len(ls_abertos) > 0:
            df_abertos = pd.DataFrame(ls_abertos).sort_values(by='Dias', ascending=False)
            st.dataframe(df_abertos.style.apply(colorir_lucro, axis=1), use_container_width=True, hide_index=True)
        else: st.success("Sua carteira está limpa.")

        st.subheader(f"📊 Top 10 Histórico ({tradutor_periodo_nome.get(periodo_cm, periodo_cm)})")
        if len(ls_resumo) > 0:
            df_resumo = pd.DataFrame(ls_resumo).sort_values(by='Lucro R$', ascending=False).head(10)
            df_resumo['Lucro R$'] = df_resumo['Lucro R$'].apply(lambda x: f"R$ {x:,.2f}")
            st.dataframe(df_resumo, use_container_width=True, hide_index=True)
        else: st.warning("Nenhuma operação finalizada.")

# ESPAÇO PARA AS PRÓXIMAS ABAS
with aba_pm: st.info("Em breve: Radar PM Dinâmico de Médias.")
with aba_stop: st.info("Em breve: Radar Alvo & Stop de Médias.")
with aba_individual: st.info("Em breve: Raio-X Individual.")
with aba_futuros: st.info("Em breve: Raio-X Futuros.")
