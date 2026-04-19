# ==========================================
# 2. BACKTEST
# ==========================================
with aba_backtest:
    st.subheader("📊 Simulador de Resultados Históricos")
    st.markdown("Testa o que aconteceria se você tivesse entrado em todos os rompimentos passados deste ativo.")
    
    bk1, bk2, bk3 = st.columns(3)
    with bk1: at_bk = st.text_input("Ativo para Teste:", value="AURA33", key="bk_ativo").upper()
    with bk2: alvo_bk = st.number_input("Alvo do Backtest (%):", value=50.0, step=10.0, key="alvo_bk")
    with bk3: hist_bk = st.number_input("Histórico (Velas Diárias):", value=1000, step=500, key="bk_hist")

    if st.button("⚙️ Rodar Backtest de Rompimento", type="primary", use_container_width=True, key="btn_bk"):
        try:
            df = tv.get_hist(symbol=at_bk, exchange='BMFBOVESPA', interval=Interval.in_daily, n_bars=hist_bk)
            if df is not None:
                df.columns = [c.capitalize() for c in df.columns]
                # Define a máxima anual móvel (252 dias úteis = 1 ano)
                df['Max_Anual'] = df['High'].rolling(window=252).max().shift(1)
                
                trades = []
                em_trade = False
                
                for i in range(252, len(df)):
                    if not em_trade:
                        # Gatilho de entrada no rompimento da máxima anual
                        if df['Close'].iloc[i] > df['Max_Anual'].iloc[i]:
                            em_trade = True
                            p_entrada = df['Close'].iloc[i]
                            p_alvo = p_entrada * (1 + (alvo_bk / 100))
                            data_entrada = df.index[i]
                    else:
                        # Monitora se bateu no alvo
                        if df['High'].iloc[i] >= p_alvo:
                            # Calcula os dias corridos em que o dinheiro ficou na operação
                            dias_na_operacao = (df.index[i] - data_entrada).days
                            
                            trades.append({
                                'Data Entrada': data_entrada.strftime('%d/%m/%Y'),
                                'Preço Entrada': f"R$ {p_entrada:.2f}",
                                'Data Saída': df.index[i].strftime('%d/%m/%Y'),
                                'Preço Saída': f"R$ {p_alvo:.2f}",
                                'Duração': f"{dias_na_operacao} dias",
                                'Resultado': f"🟢 GAIN (+{alvo_bk}%)"
                            })
                            em_trade = False
                
                if trades:
                    st.success(f"Backtest concluído para {at_bk}!")
                    st.dataframe(pd.DataFrame(trades), use_container_width=True)
                else:
                    st.warning("Nenhum trade finalizado (atingiu o alvo) encontrado no histórico recente.")
        except Exception as e: 
            st.error(f"Erro no Backtest: {e}")
