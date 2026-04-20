# ==========================================
# ABA 1: RADAR DE COMPRESSÃO (NR4 / NR7)
# ==========================================
with aba_radar:
    st.subheader("📡 Radar de Latinhas Chacoalhadas")
    st.markdown("Varre o mercado em busca de ativos em congestão que formaram o menor candle dos últimos 4 (NR4) ou 7 (NR7) períodos. Uma mola pronta para disparar.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        lista_sel = st.selectbox("Lista de Ativos:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"], key="lat_lst")
        tipo_setup = st.selectbox("Setup de Volatilidade:", ["NR4 (Latinha Clássica)", "NR7 (Latinha Estendida)"], key="lat_setup")
    with c2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['1d', '1wk', '60m', '15m'], index=0, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x], key="lat_tmp")
        # --- NOVO MENU DE FILTROS DE CAIXOTE AQUI ---
        tipo_filtro = st.selectbox("Filtro de Congestão (Caixote):", [
            "Bollinger Squeeze (Bandas Estreitas)", 
            "Médias Emboladas (MME9 próxima a MM21)", 
            "ADX < 25 (Clássico)", 
            "Sem Filtro (Basta ser NR4/NR7)"
        ], key="lat_filtro")
    with c3:
        st.info("💡 **Ação:** Rompendo a máxima, é Compra. Perdendo a mínima, é Venda. O Stop inicial fica no outro extremo da 'Latinha'.")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    btn_iniciar = st.button(f"🚀 Caçar Setups {tipo_setup[:3]} Armados Hoje", type="primary", use_container_width=True)

    if btn_iniciar:
        ativos_analise = bdrs_elite if lista_sel == "BDRs Elite" else ibrx_selecao if lista_sel == "IBrX Seleção" else bdrs_elite + ibrx_selecao
        intervalo_tv = tradutor_intervalo.get(tempo_grafico, Interval.in_daily)
        
        janela_nr = 4 if "NR4" in tipo_setup else 7

        ls_armados = []
        p_bar = st.progress(0)
        s_text = st.empty()

        for idx, ativo_raw in enumerate(ativos_analise):
            ativo = ativo_raw.replace('.SA', '')
            s_text.text(f"🔍 Medindo volatilidade de {ativo} ({idx+1}/{len(ativos_analise)})")
            p_bar.progress((idx + 1) / len(ativos_analise))

            try:
                df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=150)
                if df is None or len(df) < 30: continue

                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                # --- MATEMÁTICA DA LATINHA (NR4/NR7) ---
                df['Range'] = df['High'] - df['Low']
                df[f'Min_Range_{janela_nr}'] = df['Range'].rolling(window=janela_nr).min()
                df['Is_Latinha'] = df['Range'] == df[f'Min_Range_{janela_nr}']
                
                # --- MOTOR DE LEITURA DO CAIXOTE ---
                df['Mercado_Lateral'] = True # Padrão para "Sem Filtro"

                if "ADX" in tipo_filtro:
                    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                    if adx_df is not None: df['Mercado_Lateral'] = adx_df['ADX_14'] < 25
                        
                elif "Bollinger" in tipo_filtro:
                    bb = ta.bbands(df['Close'], length=20, std=2)
                    if bb is not None:
                        # Calcula a largura da banda atual
                        bb_width = (bb['BBU_20_2.0'] - bb['BBL_20_2.0']) / bb['BBM_20_2.0']
                        # Se a largura atual for menor que a média das larguras dos últimos 20 candles, há compressão
                        bb_width_media = bb_width.rolling(window=20).mean()
                        df['Mercado_Lateral'] = bb_width < bb_width_media
                        
                elif "Médias" in tipo_filtro:
                    mme9 = ta.ema(df['Close'], length=9)
                    mm21 = ta.sma(df['Close'], length=21)
                    if mme9 is not None and mm21 is not None:
                        # Verifica se a diferença percentual entre as médias é menor que 1.5%
                        distancia_pct = abs(mme9 - mm21) / df['Close'] * 100
                        df['Mercado_Lateral'] = distancia_pct < 1.5

                # --- VERIFICA O ÚLTIMO CANDLE FECHADO ---
                ultimo = df.iloc[-1]
                
                if ultimo['Is_Latinha'] and ultimo['Mercado_Lateral']:
                    gatilho_compra = ultimo['High'] + 0.01
                    gatilho_venda = ultimo['Low'] - 0.01
                    
                    ls_armados.append({
                        'Ativo': ativo,
                        'Data Formação': df.index[-1].strftime('%d/%m/%Y'),
                        'Tamanho (R$)': f"R$ {ultimo['Range']:.2f}",
                        'Gatilho COMPRA': f"R$ {gatilho_compra:.2f}",
                        'Gatilho VENDA': f"R$ {gatilho_venda:.2f}",
                        'Fechamento Atual': f"R$ {ultimo['Close']:.2f}"
                    })

            except Exception as e: pass
            time.sleep(0.05)

        s_text.empty()
        p_bar.empty()

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.divider()
        if len(ls_armados) > 0:
            st.success(f"🎯 Encontramos {len(ls_armados)} 'Latinhas' validadas pelo filtro de {tipo_filtro.split()[0]}!")
            df_res = pd.DataFrame(ls_armados)
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        else:
            st.warning(f"Nenhuma latinha encontrada hoje com as condições do filtro ({tipo_filtro.split()[0]}). O mercado pode estar muito direcional.")
