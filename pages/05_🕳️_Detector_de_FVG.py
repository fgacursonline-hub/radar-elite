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
    
    # Mapeamento de intervalos que já validamos
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
                
                # --- Lógica Matemática do FVG ---
                # FVG de Alta: Mínima da vela 3 > Máxima da vela 1
                df['FVG_Alta'] = df['Low'] > df['High'].shift(2)
                # FVG de Baixa: Máxima da vela 3 < Mínima da vela 1
                df['FVG_Baixa'] = df['High'] < df['Low'].shift(2)
                
                # Filtra apenas onde ocorreram Gaps
                gaps_alta = df[df['FVG_Alta'] == True].copy()
                gaps_baixa = df[df['FVG_Baixa'] == True].copy()
                
                # Interface de Resultados
                st.subheader(f"📊 Resultados para {ativo}")
                
                res1, res2 = st.columns(2)
                res1.metric("Gaps de Alta (Bullish)", len(gaps_alta))
                res2.metric("Gaps de Baixa (Bearish)", len(gaps_baixa))
                
                if not gaps_alta.empty or not gaps_baixa.empty:
                    st.info("💡 **Dica:** O preço tende a retornar para preencher esses 'buracos' antes de seguir a tendência.")
                    st.write("Últimos Gaps Detectados:")
                    st.dataframe(df[['Open', 'High', 'Low', 'Close', 'FVG_Alta', 'FVG_Baixa']].tail(20))
                else:
                    st.success("Nenhum desequilíbrio recente detectado. Mercado em equilíbrio.")
                    
            else:
                st.error("Dados insuficientes para este ativo.")
        except Exception as e:
            st.error(f"Erro na conexão: {e}")
