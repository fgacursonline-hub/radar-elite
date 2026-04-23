# ==========================================
# ABA 2: RAIO-X INDIVIDUAL (COM RESUMO TÁTICO)
# ==========================================
with aba_individual:
    st.subheader("🔬 Laboratório de Microestrutura")
    col1, col2 = st.columns([1, 2])
    with col1:
        rx_ativo = st.text_input("Ativo (Ex: PETR4):", value="PETR4").upper().replace('.SA', '')
        rx_tempo = st.selectbox("Tempo:", ['1d', '60m'], key="rx_inst_t")
        rx_btn = st.button("🔬 Analisar DNA do Fluxo", use_container_width=True)
    
    if rx_btn:
        with st.spinner("Mapeando ordens institucionais..."):
            df = tv.get_hist(symbol=rx_ativo, exchange='BMFBOVESPA', interval=tradutor_intervalo[rx_tempo], n_bars=100)
            if df is not None:
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df['POC'] = calcular_rolling_poc(df, periodo_lookback=30)
                df['VWAP'] = ta.vwma(df['Close'], df['Volume'], length=20)
                df = aplicar_fluxo_agressao(df)
                
                res = df.iloc[-1] # Última Linha (Hoje)
                
                # --- PAINEL DE MÉTRICAS ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Preço Atual", f"R$ {res['Close']:.2f}")
                c2.metric("POC (30d)", f"R$ {res['POC']:.2f}", f"{(res['Close']/res['POC']-1)*100:.2f}%")
                c3.metric("VWAP (VWMA20)", f"R$ {res['VWAP']:.2f}")
                delta_val = res['Delta_Acumulado']
                c4.metric("Saldo Agres. (5p)", f"{delta_val:,.0f}", delta="COMPRADOR" if delta_val > 0 else "VENDEDOR", delta_color="normal" if delta_val > 0 else "inverse")

                st.divider()
                
                # --- TABELA DE DADOS ---
                st.markdown("### 📋 Histórico Recente de Agressão")
                df_view = df[['Close', 'POC', 'VWAP', 'Saldo_Ag', 'Delta_Acumulado']].tail(10).copy()
                st.dataframe(df_view, use_container_width=True)

                # ==========================================
                # NOVO: RESUMO TÁTICO AUTOMATIZADO
                # ==========================================
                st.markdown("---")
                st.subheader("🎯 Resumo Tático (Leitura Institucional)")
                
                # 1. Análise da POC (Viés Macro)
                if res['Close'] > res['POC']:
                    txt_poc = f"✅ **Preço ({res['Close']:.2f}) acima da POC ({res['POC']:.2f}):** Viés institucional de ALTA. O mercado aceita preços mais caros, indicando valorização."
                    status_poc = True
                else:
                    txt_poc = f"❌ **Preço ({res['Close']:.2f}) abaixo da POC ({res['POC']:.2f}):** Viés institucional de BAIXA. O mercado está 'barateando' o ativo."
                    status_poc = False

                # 2. Análise da VWAP (Ponto de Defesa)
                dist_vwap = abs(res['Close'] - res['VWAP']) / res['VWAP'] * 100
                if dist_vwap < 0.5:
                    txt_vwap = f"⚠️ **Colado na VWAP:** O preço está exatamente na média institucional ({res['VWAP']:.2f}). Zona de briga intensa entre compradores e vendedores."
                elif res['Close'] > res['VWAP']:
                    txt_vwap = f"✅ **Acima da VWAP:** Os compradores ganharam a briga do dia e estão defendendo o preço médio acima de {res['VWAP']:.2f}."
                else:
                    txt_vwap = f"❌ **Abaixo da VWAP:** Os vendedores dominam o dia, empurrando o preço para baixo da média institucional ({res['VWAP']:.2f})."

                # 3. Análise da Agressão (Delta)
                if res['Delta_Acumulado'] > 0:
                    txt_delta = f"✅ **Delta Positivo ({res['Delta_Acumulado']:,.0f}):** Há uma pressão acumulada de COMPRA. Os tubarões estão agredindo o book para montar posição."
                    status_delta = True
                else:
                    txt_delta = f"❌ **Delta Negativo ({res['Delta_Acumulado']:,.0f}):** Há pressão de VENDA. Estão 'marretando' o bid ou realizando lucros de forma agressiva."
                    status_delta = False

                # Exibição dos pontos
                st.markdown(f"""
                * {txt_poc}
                * {txt_vwap}
                * {txt_delta}
                """)

                # --- VEREDITO FINAL ---
                if status_poc and status_delta and res['Close'] >= res['VWAP']:
                    st.success(f"⚖️ **VEREDITO:** Cenario de **FORTE COMPRA**. O ativo tem POC, VWAP e Delta alinhados. Probabilidade de explosão caso rompa a máxima atual.")
                elif not status_poc and not status_delta and res['Close'] <= res['VWAP']:
                    st.error(f"⚖️ **VEREDITO:** Cenario de **FORTE VENDA**. Fluxo institucional vendedor confirmado. Evite compras até que o preço recupere a POC.")
                else:
                    st.warning(f"⚖️ **VEREDITO:** Mercado em **EQUILÍBRIO / INDECISÃO**. Os indicadores de fluxo estão divergentes. Aguarde o alinhamento de Delta + POC para tomar posição.")
