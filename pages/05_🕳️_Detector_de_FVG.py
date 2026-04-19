import streamlit as st
import pandas as pd
import pandas_ta as ta
from tvDatafeed import TvDatafeed, Interval

# 1. Configuração da Página
st.set_page_config(page_title="Detector de FVG", layout="wide")

# Inicializa o TradingView
# (Certifique-se de que a instância 'tv' está acessível ou crie uma nova)
if 'tv' not in st.session_state:
    st.session_state.tv = TvDatafeed()
tv = st.session_state.tv

# --- Cabeçalho com link para o Manual ---
col_tit, col_man = st.columns([4, 1])
with col_tit:
    st.title("🕳️ Detector de Fair Value Gap (FVG)")
with col_man:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    # Substitua pelo seu link real quando tiver o manual do FVG
    st.link_button("📖 Manual FVG", "https://seusite.com/manual_fvg")

st.markdown("---")

# 2. Configurações de Busca
c1, c2, c3 = st.columns(3)
with c1:
    lupa_ativo = st.text_input("Ativo (Ex: PETR4):", value="PETR4").upper()
with c2:
    lupa_tempo = st.selectbox("Tempo Gráfico:", 
                               ['15m', '60m', '1d', '1wk', '1mo'], 
                               index=2,
                               format_func=lambda x: {'15m':'15 min','60m':'60 min','1d':'Diário','1wk':'Semanal','1mo':'Mensal'}[x])
with c3:
    lupa_bars = st.number_input("Qtd. de Velas:", value=300, step=50)

btn_fvg = st.button("🔍 Escanear Desequilíbrios", type="primary", use_container_width=True)

if btn_fvg:
    ativo = lupa_ativo.strip()
    
    mapa_intervalos = {
        '15m': Interval.in_15_minute, '60m': Interval.in_1_hour,
        '1d': Interval.in_daily, '1wk': Interval.in_weekly, '1mo': Interval.in_monthly
    }
    intervalo_tv = mapa_intervalos.get(lupa_tempo, Interval.in_daily)

    with st.spinner(f"Caçando Gaps em {ativo}..."):
        try:
            df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=lupa_bars)
            
            if df is not None and len(df) > 3:
                df.rename(columns={'high': 'High', 'low': 'Low', 'close': 'Close', 'open': 'Open'}, inplace=True)
                
                lista_gaps = []
                preco_atual = df['Close'].iloc[-1]
                alerta_oportunidade = False # Gatilho para disparar o aviso
                
                # Loop para calcular os limites de preço de cada Gap
                for i in range(2, len(df)):
                    
                    # Lógica FVG Alta (Bullish) - ZONA DE SUPORTE (DEMANDA)
                    if df['Low'].iloc[i] > df['High'].iloc[i-2]:
                        topo = df['Low'].iloc[i]
                        fundo = df['High'].iloc[i-2]
                        
                        # Verifica se o preço já fechou esse gap no futuro
                        aberto = df['Low'].iloc[i:].min() > fundo
                        status = "Aberto" if aberto else "Preenchido"
                        
                        # Se estiver Aberto e o preço atual estiver DENTRO do Gap: Dispara Alerta!
                        if aberto and (fundo <= preco_atual <= topo):
                            alerta_oportunidade = True
                            
                        lista_gaps.append({
                            'Data': df.index[i].strftime('%d/%m %H:%M'),
                            'Tipo': 'Alta 🟢',
                            'Zona': 'Suporte (Demanda)',
                            'Limite Superior': topo,
                            'Limite Inferior': fundo,
                            'Status': status
                        })

                    # Lógica FVG Baixa (Bearish) - ZONA DE RESISTÊNCIA (OFERTA)
                    if df['High'].iloc[i] < df['Low'].iloc[i-2]:
                        topo = df['Low'].iloc[i-2]
                        fundo = df['High'].iloc[i]
                        
                        # Verifica se o preço já fechou esse gap no futuro
                        aberto = df['High'].iloc[i:].max() < topo
                        status = "Aberto" if aberto else "Preenchido"
                        
                        # Se estiver Aberto e o preço atual estiver DENTRO do Gap: Dispara Alerta!
                        if aberto and (fundo <= preco_atual <= topo):
                            alerta_oportunidade = True
                            
                        lista_gaps.append({
                            'Data': df.index[i].strftime('%d/%m %H:%M'),
                            'Tipo': 'Baixa 🔴',
                            'Zona': 'Resistência (Oferta)',
                            'Limite Superior': topo,
                            'Limite Inferior': fundo,
                            'Status': status
                        })

                # --- EXIBIÇÃO DOS RESULTADOS ---
                st.subheader(f"📊 Zonas de Desequilíbrio: {ativo}")
                st.markdown(f"**Cotação Atual:** R$ {preco_atual:.2f}")
                
                # O GRITO DE ALERTA!
                if alerta_oportunidade:
                    st.error(f"🚨 **OPORTUNIDADE:** O preço atual de {ativo} está exatamente DENTRO de uma zona de Gap Institucional ABERTO! Fique atento a reações nesta faixa de preço.")
                
                if lista_gaps:
                    # Filtra os Gaps que ainda estão abertos para destacar (se houver)
                    gaps_abertos = [g for g in lista_gaps if g['Status'] == 'Aberto']
                    destaques = gaps_abertos[-3:] if gaps_abertos else lista_gaps[-3:]
                        
                    # Mostra os 3 Gaps mais importantes em cards
                    cols = st.columns(len(destaques))
                    for idx, gap in enumerate(destaques):
                        with cols[idx]:
                            st.markdown(f"### {gap['Tipo']}")
                            st.markdown(f"*{gap['Zona']}*")
                            st.metric("Topo da Zona", f"R$ {gap['Limite Superior']:.2f}")
                            st.metric("Fundo da Zona", f"R$ {gap['Limite Inferior']:.2f}")
                            st.caption(f"Status: **{gap['Status']}** | Detectado: {gap['Data']}")
                    
                    st.divider()
                    
                    # Explicação didática na tela
                    st.info("💡 **Guia de Ação Institucional:** \n"
                            "- **FVG de Alta:** Funciona como um ímã e uma zona de **Suporte (Demanda)**. O preço tende a cair até este buraco, atrair compradores institucionais e voltar a subir.\n"
                            "- **FVG de Baixa:** Funciona como um ímã e uma zona de **Resistência (Oferta)**. O preço tende a subir até este buraco, atrair vendedores e voltar a cair.")
                    
                    # Tabela completa com histórico formatado
                    df_final = pd.DataFrame(lista_gaps).sort_index(ascending=False)
                    df_final['Limite Superior'] = df_final['Limite Superior'].apply(lambda x: f"R$ {x:.2f}")
                    df_final['Limite Inferior'] = df_final['Limite Inferior'].apply(lambda x: f"R$ {x:.2f}")
                    st.dataframe(df_final, use_container_width=True, hide_index=True)
                else:
                    st.success("Mercado em equilíbrio. Nenhum Gap relevante encontrado nas últimas velas.")
            else:
                st.error("Ativo não encontrado ou dados insuficientes.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
            else:
                st.error("Ativo não encontrado ou dados insuficientes.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
