# ==========================================
    # ABA 5: RAIO-X FUTUROS (COM ZERAGEM 17H)
    # ==========================================
    with aba_futuros:
        st.subheader("📈 Raio-X Mercado Futuro (WIN, WDO, etc)")
        st.markdown("Especializado para contratos que operam por **Pontos** e não por porcentagem de preço.")
        
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            fut_ativo = st.text_input("Ativo Futuro (Ex: WIN1!, WDO1!):", value="WIN1!", key="f_ativo")
            fut_estrategia = st.selectbox("Estratégia a Testar:", ["Padrão (Sem PM)", "PM Dinâmico", "Alvo & Stop Loss"], key="f_est")
            fut_periodo = st.selectbox("Período de Estudo:", options=['1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=2, key="f_per")
        with cf2:
            fut_alvo = st.number_input("Alvo (em Pontos):", value=300, step=50, key="f_alvo")
            if fut_estrategia == "Alvo & Stop Loss":
                fut_stop = st.number_input("Stop Loss (em Pontos):", value=200, step=50, key="f_stop")
            else:
                fut_stop = 0 
                st.markdown("<div style='height: 75px;'></div>", unsafe_allow_html=True) 
            fut_contratos = st.number_input("Qtd. Contratos por Entrada:", value=1, step=1, key="f_cont")
        with cf3:
            fut_multiplicador = st.number_input("Multiplicador Financeiro por Ponto (R$):", value=0.20, step=0.10, format="%.2f", help="Ex: WIN1!=0.20 | WDO1!=10.00", key="f_mult")
            fut_tempo = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=0, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="f_tmp")
            fut_ifr = st.number_input("Período do IFR:", min_value=2, max_value=50, value=8, step=1, key="f_ifr")
            
        fut_zerar_17h = st.checkbox("⏰ Forçar Zeragem Compulsória às 17h00 (Obrigatório para Day Trade real)", value=True, help="Zera a operação a mercado às 17h se o alvo/stop não for atingido, assumindo o lucro/prejuízo real.")
            
        btn_raiox_futuros = st.button("🔍 Gerar Raio-X Futuros", type="primary", use_container_width=True, key="f_btn")

        if btn_raiox_futuros:
            ativo_input = fut_ativo.strip().upper()
            if not ativo_input:
                st.error("Por favor, digite o código do ativo futuro.")
            else:
                ativo = ativo_input
                if fut_tempo == '15m' and fut_periodo not in ['1mo', '3mo']: fut_periodo = '60d'
                elif fut_tempo == '60m' and fut_periodo in ['5y', 'max']: fut_periodo = '2y'
                intervalo_tv = tradutor_intervalo.get(fut_tempo, Interval.in_daily)

                with st.spinner(f'Testando Backtest Futuro ({fut_estrategia}) em {ativo}...'):
                    try:
                        df_full = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=5000)
                        if df_full is None or len(df_full) < 50:
                            st.error("Dados insuficientes no TradingView para este ativo.")
                        else:
                            df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                            df_full = df_full.dropna()
                            
                            df_full['IFR'] = ta.rsi(df_full['Close'], length=fut_ifr)
                            df_full['IFR_Prev'] = df_full['IFR'].shift(1)
                            df_full = df_full.dropna()

                            data_atual = df_full.index[-1]
                            if fut_periodo == '1mo': data_corte = data_atual - pd.DateOffset(months=1)
                            elif fut_periodo == '3mo': data_corte = data_atual - pd.DateOffset(months=3)
                            elif fut_periodo == '6mo': data_corte = data_atual - pd.DateOffset(months=6)
                            elif fut_periodo == '1y': data_corte = data_atual - pd.DateOffset(years=1)
                            elif fut_periodo == '2y': data_corte = data_atual - pd.DateOffset(years=2)
                            elif fut_periodo == '5y': data_corte = data_atual - pd.DateOffset(years=5)
                            elif fut_periodo == '60d': data_corte = data_atual - pd.DateOffset(days=60)
                            else: data_corte = df_full.index[0]

                            df = df_full[df_full.index >= data_corte].copy()
                            trades = []
                            em_pos = False
                            df_back = df.reset_index()
                            col_data = df_back.columns[0]
                            vitorias = 0
                            derrotas = 0

                            for i in range(1, len(df_back)):
                                hora_atual = df_back[col_data].iloc[i].hour if hasattr(df_back[col_data].iloc[i], 'hour') else 0
                                
                                # === LÓGICA DE ZERAGEM COMPULSÓRIA ÀS 17h ===
                                if em_pos and fut_zerar_17h and fut_tempo in ['15m', '60m'] and hora_atual >= 17:
                                    d_sai = df_back[col_data].iloc[i]
                                    preco_saida = df_back['Close'].iloc[i]
                                    duracao = (d_sai - d_ent).days
                                    
                                    if fut_estrategia == "Padrão (Sem PM)":
                                        lucro_rs = (preco_saida - preco_entrada) * fut_contratos * fut_multiplicador
                                        drawdown_pts = (preco_entrada - min_price_in_trade)
                                        situacao = 'Zerad. 17h ✅' if lucro_rs > 0 else 'Zerad. 17h ❌'
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Queda Máx': f"{drawdown_pts:.2f} pts", 'Situação': situacao})
                                        if lucro_rs > 0: vitorias += 1
                                        else: derrotas += 1
                                        em_pos = False
                                        continue

                                    elif fut_estrategia == "PM Dinâmico":
                                        lucro_rs = (preco_saida - preco_medio) * contratos_atuais * fut_multiplicador
                                        drawdown_pts = (preco_entrada_inicial - min_price_in_trade)
                                        situacao = 'Zerad. 17h ✅' if lucro_rs > 0 else 'Zerad. 17h ❌'
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Queda Máx': f"{drawdown_pts:.2f} pts", 'Fez PM?': f"Sim ({qtd_pms}x)" if qtd_pms > 0 else 'Não', 'Situação': situacao})
                                        if lucro_rs > 0: vitorias += 1
                                        else: derrotas += 1
                                        em_pos = False
                                        continue

                                    elif fut_estrategia == "Alvo & Stop Loss":
                                        lucro_rs = (preco_saida - preco_entrada) * fut_contratos * fut_multiplicador
                                        situacao = 'Zerad. 17h ✅' if lucro_rs > 0 else 'Zerad. 17h ❌'
                                        trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': situacao})
                                        if lucro_rs > 0: vitorias += 1
                                        else: derrotas += 1
                                        em_pos = False
                                        continue

                                # Impede entrada nova no final do dia se a zeragem estiver ativada
                                condicao_entrada = (df_back['IFR_Prev'].iloc[i] < 25) and (df_back['IFR'].iloc[i] >= 25)
                                if fut_zerar_17h and fut_tempo in ['15m', '60m'] and hora_atual >= 17:
                                    condicao_entrada = False

                                # === MOTORES NORMAIS ===
                                if fut_estrategia == "Padrão (Sem PM)":
                                    if em_pos:
                                        if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                                        if df_back['High'].iloc[i] >= take_profit:
                                            d_sai = df_back[col_data].iloc[i]
                                            duracao = (d_sai - d_ent).days
                                            lucro_rs = fut_alvo * fut_contratos * fut_multiplicador
                                            drawdown_pts = (preco_entrada - min_price_in_trade)
                                            trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Queda Máx': f"{drawdown_pts:.2f} pts", 'Situação': 'Gain ✅'})
                                            vitorias += 1
                                            em_pos = False
                                            continue

                                    if condicao_entrada and not em_pos:
                                        em_pos = True
                                        d_ent = df_back[col_data].iloc[i]
                                        preco_entrada = df_back['Close'].iloc[i]
                                        min_price_in_trade = df_back['Low'].iloc[i]
                                        take_profit = preco_entrada + fut_alvo

                                elif fut_estrategia == "PM Dinâmico":
                                    if em_pos:
                                        if df_back['Low'].iloc[i] < min_price_in_trade: min_price_in_trade = df_back['Low'].iloc[i]
                                        if df_back['High'].iloc[i] >= take_profit:
                                            d_sai = df_back[col_data].iloc[i]
                                            duracao = (d_sai - d_ent).days
                                            lucro_rs = fut_alvo * contratos_atuais * fut_multiplicador
                                            drawdown_pts = (preco_entrada_inicial - min_price_in_trade)
                                            trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Queda Máx': f"{drawdown_pts:.2f} pts", 'Fez PM?': f"Sim ({qtd_pms}x)" if qtd_pms > 0 else 'Não', 'Situação': 'Gain ✅'})
                                            vitorias += 1
                                            em_pos = False
                                            continue

                                    if condicao_entrada:
                                        if not em_pos:
                                            em_pos = True
                                            d_ent = df_back[col_data].iloc[i]
                                            preco_entrada_inicial = df_back['Close'].iloc[i]
                                            min_price_in_trade = df_back['Low'].iloc[i]
                                            qtd_pms = 0
                                            contratos_atuais = fut_contratos
                                            preco_medio = preco_entrada_inicial
                                            take_profit = preco_medio + fut_alvo
                                        else:
                                            qtd_pms += 1
                                            preco_compra = df_back['Close'].iloc[i]
                                            total_gasto = (preco_medio * contratos_atuais) + (preco_compra * fut_contratos)
                                            contratos_atuais += fut_contratos
                                            preco_medio = total_gasto / contratos_atuais
                                            take_profit = preco_medio + fut_alvo

                                elif fut_estrategia == "Alvo & Stop Loss":
                                    if em_pos:
                                        if df_back['Low'].iloc[i] <= stop_price:
                                            d_sai = df_back[col_data].iloc[i]
                                            duracao = (d_sai - d_ent).days
                                            lucro_rs = - (fut_stop * fut_contratos * fut_multiplicador)
                                            trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Stop ❌'})
                                            derrotas += 1
                                            em_pos = False
                                            continue
                                        elif df_back['High'].iloc[i] >= take_profit:
                                            d_sai = df_back[col_data].iloc[i]
                                            duracao = (d_sai - d_ent).days
                                            lucro_rs = fut_alvo * fut_contratos * fut_multiplicador
                                            trades.append({'Entrada': d_ent.strftime('%d/%m/%Y %H:%M'), 'Saída': d_sai.strftime('%d/%m/%Y %H:%M'), 'Duração': duracao, 'Lucro (R$)': lucro_rs, 'Situação': 'Gain ✅'})
                                            vitorias += 1
                                            em_pos = False
                                            continue

                                    if condicao_entrada and not em_pos:
                                        em_pos = True
                                        d_ent = df_back[col_data].iloc[i]
                                        preco_entrada = df_back['Close'].iloc[i]
                                        take_profit = preco_entrada + fut_alvo
                                        stop_price = preco_entrada - fut_stop

                            st.divider()
                            st.markdown(f"### 📊 Resultado: {ativo} ({fut_estrategia})")
                            
                            if len(trades) > 0:
                                df_t = pd.DataFrame(trades)
                                mc1, mc2, mc3, mc4 = st.columns(4)
                                mc1.metric("Lucro Total Estimado", f"R$ {df_t['Lucro (R$)'].sum():,.2f}")
                                mc2.metric("Tempo Preso (Médio)", f"{round(df_t['Duração'].mean(), 1)} dias")
                                mc3.metric("Operações Fechadas", f"{len(df_t)}")
                                
                                taxa_acerto = (vitorias / len(df_t)) * 100
                                mc4.metric("Taxa de Acerto", f"{taxa_acerto:.1f}%")
                                
                                st.dataframe(df_t, use_container_width=True, hide_index=True)
                            else:
                                st.warning("Nenhuma operação concluída usando essa estratégia neste período.")
                    except Exception as e: st.error(f"Erro: {e}")
