# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (BACKTEST DETALHADO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Raio-X Individual: Laboratório de Price Action")
    
    cr1, cr2, cr3, cr4 = st.columns(4)
    with cr1:
        rx_ativo = st.text_input("Ativo Base:", value="PETR4", key="rx_c_ativo").upper().replace('.SA', '')
        rx_padrao = st.selectbox("Buscar Padrão:", ["Martelo (Compra)", "Estrela Cadente (Venda)", "Enforcado (Venda)", "Inside Bar (Rompimento)"], key="rx_c_padrao")
        rx_capital = st.number_input("Capital Operado (R$):", value=10000.0, step=1000.0, key="rx_c_cap")
    with cr2:
        rx_periodo = st.selectbox("Período:", options=['6mo', '1y', '2y', '5y', 'max'], format_func=lambda x: tradutor_periodo_nome[x], index=1, key="rx_c_per")
        rx_tempo = st.selectbox("Tempo Gráfico:", ['60m', '1d', '1wk'], index=1, format_func=lambda x: {'60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="rx_c_tmp")
    with cr3:
        rx_tipo_alvo = st.selectbox("Tipo de Alvo:", ["Técnico (Risco Projetado)", "Porcentagem (%)"], key="rx_c_tipo_alvo")
        rx_alvo_val = st.number_input("Valor do Alvo:", value=2.0, step=0.5, key="rx_c_alvo")
    with cr4:
        rx_usar_stop = st.checkbox("Usar Stop Loss", value=True, key="rx_c_chk")
        rx_tipo_stop = st.selectbox("Tipo de Stop:", ["Técnico (1 cent. do Sinal)", "Porcentagem (%)"], disabled=not rx_usar_stop, key="rx_c_tipo_stop")
        rx_stop_val = st.number_input("Valor do Stop (%) [Se %]:", value=2.0, step=0.5, disabled=not rx_usar_stop, key="rx_c_stop_pct") / 100

    btn_raiox = st.button("🔍 Rodar Backtest de Price Action", type="primary", use_container_width=True, key="rx_c_btn")

    if btn_raiox:
        if not rx_ativo: st.error("Digite o código de um ativo.")
        else:
            with st.spinner(f'A desenhar velas de {rx_ativo}...'):
                try:
                    df_full = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo.get(rx_tempo, Interval.in_daily), n_bars=5000)
                    df_full.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                    df_full = identificar_padroes(df_full).dropna()

                    if rx_periodo == '6mo': data_corte = df_full.index[-1] - pd.DateOffset(months=6)
                    elif rx_periodo == 'max': data_corte = df_full.index[0]
                    else: data_corte = df_full.index[-1] - pd.DateOffset(years=int(rx_periodo[0]))
                    
                    df_back = df_full[df_full.index >= data_corte].copy().reset_index()
                    col_data = df_back.columns[0]

                    trades, em_pos = [], False
                    preco_entrada, stop_loss, alvo, d_ent, direcao = 0.0, 0.0, 0.0, None, 0
                    vitorias, derrotas = 0, 0
                    extremo_trade = 0.0 # Controla a Queda Máxima
                    col_sinal = 'Is_Martelo' if 'Martelo' in rx_padrao else 'Is_Estrela' if 'Estrela' in rx_padrao else 'Is_Enforcado' if 'Enforcado' in rx_padrao else 'Is_InsideBar'

                    for i in range(1, len(df_back)):
                        atual, ontem = df_back.iloc[i], df_back.iloc[i-1]

                        if em_pos:
                            if direcao == 1: # Comprado
                                extremo_trade = min(extremo_trade, atual['Low'])
                                queda_max = (extremo_trade / preco_entrada) - 1
                                if rx_usar_stop and atual['Low'] <= stop_loss:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((stop_loss/preco_entrada)-1), 'Queda Máx': queda_max, 'Situação': 'Stop ❌'})
                                    derrotas += 1; em_pos = False
                                elif atual['High'] >= alvo:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((alvo/preco_entrada)-1), 'Queda Máx': queda_max, 'Situação': 'Gain ✅'})
                                    vitorias += 1; em_pos = False
                            elif direcao == -1: # Vendido
                                extremo_trade = max(extremo_trade, atual['High'])
                                queda_max = (preco_entrada - extremo_trade) / preco_entrada
                                if rx_usar_stop and atual['High'] >= stop_loss:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((preco_entrada - stop_loss)/preco_entrada), 'Queda Máx': queda_max, 'Situação': 'Stop ❌'})
                                    derrotas += 1; em_pos = False
                                elif atual['Low'] <= alvo:
                                    trades.append({'Entrada': d_ent.strftime('%d/%m/%Y'), 'Saída': atual[col_data].strftime('%d/%m/%Y'), 'Duração': (atual[col_data] - d_ent).days, 'Lucro (R$)': rx_capital * ((preco_entrada - alvo)/preco_entrada), 'Queda Máx': queda_max, 'Situação': 'Gain ✅'})
                                    vitorias += 1; em_pos = False
                            continue

                        if ontem[col_sinal] and not em_pos:
                            if rx_padrao == "Martelo (Compra)" or rx_padrao == "Inside Bar (Rompimento)":
                                if atual['High'] > ontem['High']:
                                    em_pos, direcao, preco_entrada, d_ent = True, 1, max(ontem['High'] + 0.01, atual['Open']), atual[col_data]
                                    extremo_trade = atual['Low']
                                    stop_loss = ontem['Low'] - 0.01 if "Técnico" in rx_tipo_stop else preco_entrada * (1 - rx_stop_val)
                                    alvo = preco_entrada + ((preco_entrada - (ontem['Low'] - 0.01)) * rx_alvo_val) if "Técnico" in rx_tipo_alvo else preco_entrada * (1 + (rx_alvo_val/100))
                            
                            elif rx_padrao in ["Estrela Cadente (Venda)", "Enforcado (Venda)"]:
                                if atual['Low'] < ontem['Low']:
                                    em_pos, direcao, preco_entrada, d_ent = True, -1, min(ontem['Low'] - 0.01, atual['Open']), atual[col_data]
                                    extremo_trade = atual['High']
                                    stop_loss = ontem['High'] + 0.01 if "Técnico" in rx_tipo_stop else preco_entrada * (1 + rx_stop_val)
                                    alvo = preco_entrada - (((ontem['High'] + 0.01) - preco_entrada) * rx_alvo_val) if "Técnico" in rx_tipo_alvo else preco_entrada * (1 - (rx_alvo_val/100))
                                    
                    st.divider()
                    
                    # --- CAIXAS DE ESTADO EM DESTAQUE ---
                    if em_pos:
                        cot_atual = df_back['Close'].iloc[-1]
                        dias_aberto = (df_back[col_data].iloc[-1] - d_ent).days
                        res_pct = (cot_atual / preco_entrada) - 1 if direcao == 1 else (preco_entrada - cot_atual) / preco_entrada
                        queda_max_aberta = (extremo_trade / preco_entrada) - 1 if direcao == 1 else (preco_entrada - extremo_trade) / preco_entrada
                        
                        st.warning(f"""
                        **⏳ {rx_ativo}: Em Operação (Aguardando Alvo)**
                        * **Entrada:** {d_ent.strftime('%d/%m/%Y')} | **Dias na Operação:** {dias_aberto}
                        * **PM:** R$ {preco_entrada:.2f} | **Cotação Atual:** R$ {cot_atual:.2f}
                        * **Queda Máx:** {queda_max_aberta*100:.2f}% | **Resultado Atual:** {res_pct*100:.2f}%
                        """)
                    else:
                        st.success(f"✅ **{rx_ativo}: Aguardando Novo Sinal de Entrada**")
                    
                    st.markdown(f"### 📊 Resultado Consolidado: {rx_ativo} ({rx_padrao})")
                    if len(trades) > 0:
                        df_t = pd.DataFrame(trades)
                        
                        l_total = df_t['Lucro (R$)'].sum()
                        media_dias = df_t['Duração'].mean()
                        pior_queda = df_t['Queda Máx'].min()
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lucro Total", f"R$ {l_total:,.2f}")
                        m2.metric("Duração Média", f"{media_dias:.1f} dias")
                        m3.metric("Operações Fechadas", len(df_t))
                        m4.metric("Pior Queda", f"{pior_queda*100:.2f}%")

                        df_t['Queda Máx'] = df_t['Queda Máx'].apply(lambda x: f"{x*100:.2f}%")
                        st.dataframe(df_t, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Nenhuma operação validada no período com os parâmetros selecionados.")
                except Exception as e: st.error(f"Erro: {e}")
