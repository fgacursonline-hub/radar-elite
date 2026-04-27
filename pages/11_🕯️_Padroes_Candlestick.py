import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import time
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. IMPORTAÇÃO CENTRALIZADA DOS ATIVOS
# ==========================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from config_ativos import bdrs_elite, ibrx_selecao
except ImportError:
    st.error("❌ Arquivo 'config_ativos.py' não encontrado na raiz do projeto.")
    st.stop()

ativos_para_rastrear = sorted(list(set([a.replace('.SA', '') for a in (bdrs_elite + ibrx_selecao)])))

# ==========================================
# 2. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar Price Action Elite", layout="wide", page_icon="🕯️")

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

@st.cache_resource
def get_tv_connection():
    return TvDatafeed()

tv = get_tv_connection()

st.title("🕯️ Laboratório de Price Action: Mamona Candles")
st.markdown("Rastreador de reversão com 33 padrões de alta precisão baseados puramente na anatomia gráfica. A psicologia crua dos touros e ursos, sem atraso de indicadores.")

# ==========================================
# 3. DICIONÁRIO DE EXPLICAÇÕES TÁTICAS
# ==========================================
dicionario_padroes = {
    'Nuvem Negra (Dark Cloud)': {'Tipo': '🔴 Baixa', 'Desc': 'Ataque bloqueado! O preço abre alto, mas os ursos empurram o fechamento para baixo da metade do candle verde de ontem.'},
    'Doji': {'Tipo': '⚪ Neutro', 'Desc': 'Indecisão absoluta. Abertura e fechamento no mesmo milímetro. Forças empatadas.'},
    'Doji Estrela (Baixa)': {'Tipo': '🔴 Baixa', 'Desc': 'Após um candle de força compradora, surge um Doji fora do corpo anterior. Exaustão de alta.'},
    'Doji Libélula (Dragonfly)': {'Tipo': '🟢 Alta', 'Desc': 'Pavio longo para baixo, sem pavio em cima. Os ursos bateram forte, mas os touros devolveram absolutamente tudo.'},
    'Estrela da Noite': {'Tipo': '🔴 Baixa', 'Desc': 'Padrão de 3 dias. Alta forte, indecisão no topo, e uma paulada de queda no terceiro dia. Fim da festa.'},
    'Estrela da Noite Doji': {'Tipo': '🔴 Baixa', 'Desc': 'Variante fatal da Estrela da Noite, onde a indecisão do topo é marcada por um Doji exato.'},
    'Doji Lápide (Gravestone)': {'Tipo': '🔴 Baixa', 'Desc': 'Pavio longo para cima, fechamento na mínima. Os touros tentaram, mas os ursos enterraram a alta.'},
    'Enforcado Vermelho': {'Tipo': '🔴 Baixa', 'Desc': 'Pavio inferior longo no topo de uma tendência, fechando negativo. O chão começou a ceder.'},
    'Enforcado Verde': {'Tipo': '🔴 Baixa', 'Desc': 'Pavio inferior longo no topo, fechando positivo. Alerta amarelo de exaustão.'},
    'Estrela da Manhã': {'Tipo': '🟢 Alta', 'Desc': 'Padrão de 3 dias. Queda, indecisão no fundo, e um forte salto comprador no terceiro dia. O sol nascendo.'},
    'Estrela da Manhã Doji': {'Tipo': '🟢 Alta', 'Desc': 'A retomada compradora iniciada a partir de um Doji exato no fundo do poço.'},
    'Linha de Perfuração (Piercing)': {'Tipo': '🟢 Alta', 'Desc': 'O preço abriu caindo feio, mas os touros perfuraram a queda e fecharam ACIMA da metade do candle de ontem.'},
    'Gota de Chuva (Raindrop)': {'Tipo': '🟢 Alta', 'Desc': 'Padrão sutil de absorção compradora no fundo de uma pequena queda.'},
    'Gota de Chuva Doji': {'Tipo': '🟢 Alta', 'Desc': 'Absorção compradora finalizada com um Doji perfeito.'},
    'Martelo Invertido Vermelho': {'Tipo': '🟢 Alta', 'Desc': 'Tentativa de alta em um fundo. Deixa pavio para cima, mas sinaliza a presença de touros acordando.'},
    'Martelo Invertido Verde': {'Tipo': '🟢 Alta', 'Desc': 'Touros testaram a máxima no fundo e conseguiram fechar positivo. Bom sinal de reversão.'},
    'Estrela de Baixa (Star)': {'Tipo': '🔴 Baixa', 'Desc': 'Candle pequeno após uma grande barra verde. O fôlego comprador secou.'},
    'Avanço de Baixa (Bearish Thrusting)': {'Tipo': '🔴 Baixa', 'Desc': 'Tentativa falha de reversão de alta. O mercado não consegue furar o meio da barra de queda.'},
    'Avanço de Alta (Bullish Thrusting)': {'Tipo': '🟢 Alta', 'Desc': 'Tentativa falha de reversão de baixa. A pressão vendedora é absorvida no meio do caminho.'},
    'Pinça de Fundo (Tweezers Bottom)': {'Tipo': '🟢 Alta', 'Desc': 'Dois dias batendo exatamente no mesmo centavo de mínima. Suporte de concreto armado criado pelos institucionais.'},
    'Pinça de Topo (Tweezers Top)': {'Tipo': '🔴 Baixa', 'Desc': 'Dois dias batendo exatamente na mesma máxima. Teto de chumbo formado por grandes ordens de venda.'},
    'Torre de Fundo (Tower Bottom)': {'Tipo': '🟢 Alta', 'Desc': 'Padrão longo. Grande queda, dias de consolidação no fundo, e uma explosão de alta rompendo as defesas.'},
    'Torre de Topo (Tower Top)': {'Tipo': '🔴 Baixa', 'Desc': 'Padrão longo. Grande alta, consolidação lateral no topo, seguida de um colapso em bloco.'},
    'No Pescoço (Bullish In Neck)': {'Tipo': '🟢 Alta', 'Desc': 'Padrão de continuação compradora disfarçado de correção curta.'},
    'No Pescoço (Bearish In Neck)': {'Tipo': '🔴 Baixa', 'Desc': 'Padrão de continuação vendedora. Correção falha.'},
    'Linhas Separadas de Alta': {'Tipo': '🟢 Alta', 'Desc': 'Gap surpreendente de abertura apagando toda a intenção de queda do dia anterior.'},
    'Linhas Separadas de Baixa': {'Tipo': '🔴 Baixa', 'Desc': 'Gap de abertura afundando o preço, ignorando a alta de ontem.'},
    'Harami de Alta': {'Tipo': '🟢 Alta', 'Desc': 'Mulher grávida de alta. Corpo pequeno verde contido no grande vermelho de ontem.'},
    'Harami de Baixa': {'Tipo': '🔴 Baixa', 'Desc': 'Mulher grávida de baixa. Corpo pequeno vermelho contido no grande verde de ontem.'},
    'Engolfo de Alta': {'Tipo': '🟢 Alta', 'Desc': 'Tsunami comprador. A barra verde de hoje devora inteiramente a barra vermelha de ontem.'},
    'Engolfo de Baixa': {'Tipo': '🔴 Baixa', 'Desc': 'Colapso. A barra vermelha de hoje engole toda a esperança verde do dia anterior.'},
    'Engolfo de Alta com Doji': {'Tipo': '🟢 Alta', 'Desc': 'Um Doji de indecisão no fundo é violentamente engolido por um ataque trator dos touros.'},
    'Engolfo de Baixa com Doji': {'Tipo': '🔴 Baixa', 'Desc': 'Um Doji de indecisão no topo é subitamente aniquilado por uma avalanche de ursos.'}
}

# ==========================================
# 4. MOTOR DE TRADUÇÃO DAS 33 FÓRMULAS
# ==========================================
def escanear_padroes(df):
    if df.empty or len(df) < 15:
        return []
    
    eps = 0.00001 # Proteção contra divisão por zero
    O, C, H, L = df['Open'], df['Close'], df['High'], df['Low']
    
    O1, C1, H1, L1 = O.shift(1), C.shift(1), H.shift(1), L.shift(1)
    O2, C2, H2, L2 = O.shift(2), C.shift(2), H.shift(2), L.shift(2)
    O3, C3, H3, L3 = O.shift(3), C.shift(3), H.shift(3), L.shift(3)
    
    # Proporções
    body = abs(C - O)
    body1 = abs(C1 - O1)
    body2 = abs(C2 - O2)
    body3 = abs(C3 - O3)
    
    rng = H - L + eps
    rng1 = H1 - L1 + eps
    rng2 = H2 - L2 + eps
    rng3 = H3 - L3 + eps
    
    r = body / rng
    r1 = body1 / rng1
    r2 = body2 / rng2
    r3 = body3 / rng3
    
    max_co = np.maximum(C, O)
    min_co = np.minimum(C, O)
    max_co1 = np.maximum(C1, O1)
    min_co1 = np.minimum(C1, O1)
    
    us = H - max_co # Upper Shadow
    ls = min_co - L # Lower Shadow
    us1 = H1 - max_co1
    ls1 = min_co1 - L1
    
    # ------------------------------------
    # BATERIA DE 33 CONDIÇÕES (MAMONA)
    # ------------------------------------
    p = []
    
    # 1. Dark Cloud Cover
    if ((C1 > O1) & (r1 >= 0.7) & (C < O) & (r >= 0.7) & (O >= C1) & (C > O1) & (C < ((O1+C1)/2))).iloc[-1]: p.append('Nuvem Negra (Dark Cloud)')
    # 2. Doji
    if ((r < 0.1) & (us > 3*body) & (ls > 3*body)).iloc[-1]: p.append('Doji')
    # 3. Doji Star
    if ((C1 > O1) & (r1 >= 0.7) & (r < 0.1) & (C1 < C) & (C1 < O) & (us > 3*body) & (ls > 3*body)).iloc[-1]: p.append('Doji Estrela (Baixa)')
    # 4. Dragonfly Doji
    if ((r < 0.1) & (ls > 3*body) & (us < body)).iloc[-1]: p.append('Doji Libélula (Dragonfly)')
    # 5. Evening Star
    if ((C2 > O2) & (r2 >= 0.7) & (r1 < 0.3) & (r1 >= 0.1) & (C < O) & (r >= 0.7) & (C2 < C1) & (C2 < O1) & (C1 > O) & (O1 > O) & (C < C2)).iloc[-1]: p.append('Estrela da Noite')
    # 6. Evening Star Doji
    if ((C2 > O2) & (r2 >= 0.7) & (r1 < 0.1) & (C < O) & (r >= 0.7) & (C2 < C1) & (C2 < O1) & (C1 > O) & (O1 > O) & (C < C2) & (us1 > 3*body1) & (ls1 > 3*body1)).iloc[-1]: p.append('Estrela da Noite Doji')
    # 7. Gravestone Doji
    if ((r < 0.1) & (us > 3*body) & (ls <= body)).iloc[-1]: p.append('Doji Lápide (Gravestone)')
    # 8. Hanging Man Red
    if ((C < O) & (r < 0.3) & (r >= 0.1) & (ls >= 2*body) & (us > 0.25*body)).iloc[-1]: p.append('Enforcado Vermelho')
    # 9. Hanging Man Green
    if ((C > O) & (r < 0.3) & (r >= 0.1) & (ls >= 2*body) & (us > 0.25*body)).iloc[-1]: p.append('Enforcado Verde')
    # 10. Morning Star
    if ((C2 < O2) & (r2 >= 0.7) & (r1 < 0.3) & (r1 >= 0.1) & (C > O) & (r >= 0.7) & (C2 > C1) & (C2 > O1) & (C1 < O) & (O1 < O) & (C > C2)).iloc[-1]: p.append('Estrela da Manhã')
    # 11. Morning Star Doji
    if ((C2 < O2) & (r2 >= 0.7) & (r1 < 0.1) & (C > O) & (r >= 0.7) & (C2 > C1) & (C2 > O1) & (C1 < O) & (O1 < O) & (C > C2) & (us1 > 3*body1) & (ls1 > 3*body1)).iloc[-1]: p.append('Estrela da Manhã Doji')
    # 12. Piercing Pattern (Corrigido para fechamento ACIMA da metade)
    if ((C1 < O1) & (r1 >= 0.7) & (C > O) & (r >= 0.7) & (O <= C1) & (C < O1) & (C > ((O1+C1)/2))).iloc[-1]: p.append('Linha de Perfuração (Piercing)')
    # 13. Raindrop
    if ((C1 < O1) & (r1 >= 0.7) & (r < 0.3) & (r >= 0.1) & (C1 > C) & (C1 > O)).iloc[-1]: p.append('Gota de Chuva (Raindrop)')
    # 14. Raindrop Doji
    if ((C1 < O1) & (r1 >= 0.7) & (r < 0.1) & (C1 > C) & (C1 > O) & (us > 3*body) & (ls > 3*body)).iloc[-1]: p.append('Gota de Chuva Doji')
    # 15. Inverted Hammer Red
    if ((C < O) & (r < 0.3) & (r >= 0.1) & (us >= 2*body) & (ls <= 0.25*body)).iloc[-1]: p.append('Martelo Invertido Vermelho')
    # 16. Inverted Hammer Green
    if ((C > O) & (r < 0.3) & (r >= 0.1) & (us >= 2*body) & (ls <= 0.25*body)).iloc[-1]: p.append('Martelo Invertido Verde')
    # 17. Star
    if ((C1 > O1) & (r1 >= 0.7) & (r < 0.3) & (r >= 0.1) & (C1 < C) & (C1 < O)).iloc[-1]: p.append('Estrela de Baixa (Star)')
    # 18. Bearish Thrusting
    if ((C1 > O1) & (r1 >= 0.7) & (C < O) & (r >= 0.7) & (O >= C1) & (C < C1) & (C >= ((O1+C1)/2))).iloc[-1]: p.append('Avanço de Baixa (Bearish Thrusting)')
    # 19. Bullish Thrusting
    if ((C1 < O1) & (r1 >= 0.7) & (C > O) & (r >= 0.7) & (O <= C1) & (C > C1) & (C <= ((O1+C1)/2))).iloc[-1]: p.append('Avanço de Alta (Bullish Thrusting)')
    # 20. Tweezers Bottom
    if ((C1 < O1) & (r1 >= 0.7) & (C < O) & (r < 0.3) & (r >= 0.1) & (abs((L/L1)-1) < 0.05) & (body < 2*ls)).iloc[-1]: p.append('Pinça de Fundo (Tweezers Bottom)')
    # 21. Tweezers Top
    if ((C1 > O1) & (r1 >= 0.7) & (C > O) & (r < 0.3) & (r >= 0.1) & (abs((H/H1)-1) < 0.05) & (body1 < 2*us1)).iloc[-1]: p.append('Pinça de Topo (Tweezers Top)')
    # 22. Tower Bottom
    if ((C3 < O3) & (r3 >= 0.7) & (C2 > O2) & (r2 < 0.3) & (r2 >= 0.1) & (C1 > O1) & (r1 < 0.3) & (r1 >= 0.1) & (C > O) & (r >= 0.7) & (C2 > C1) & (C1 > C3) & (O2 < C3) & (O1 < C3) & (C > ((O3+C3)/2))).iloc[-1]: p.append('Torre de Fundo (Tower Bottom)')
    # 23. Tower Top
    if ((C3 > O3) & (r3 >= 0.7) & (C2 < O2) & (r2 < 0.3) & (r2 >= 0.1) & (C1 < O1) & (r1 < 0.3) & (r1 >= 0.1) & (C < O) & (r >= 0.7) & (C2 < C1) & (C1 < C3) & (O2 > C3) & (O1 > C3) & (C < ((O3+C3)/2))).iloc[-1]: p.append('Torre de Topo (Tower Top)')
    # 24. Bullish In Neck
    if ((C1 < O1) & (r1 < 0.7) & (r1 >= 0.3) & (C > O) & (r < 0.7) & (r >= 0.3) & (C <= C1) & (C > L1)).iloc[-1]: p.append('No Pescoço (Bullish In Neck)')
    # 25. Bearish In Neck
    if ((C1 > O1) & (r1 < 0.7) & (r1 >= 0.3) & (C < O) & (r < 0.7) & (r >= 0.3) & (C >= C1) & (C < H1)).iloc[-1]: p.append('No Pescoço (Bearish In Neck)')
    # 26. Bullish Separating Lines
    if ((C1 > O1) & (r1 < 0.7) & (r1 >= 0.3) & (C < O) & (r < 0.7) & (r >= 0.3) & (O <= O1) & (O > L1)).iloc[-1]: p.append('Linhas Separadas de Alta')
    # 27. Bearish Separating Lines
    if ((C1 < O1) & (r1 < 0.7) & (r1 >= 0.3) & (C > O) & (r < 0.7) & (r >= 0.3) & (O >= O1) & (O < H1)).iloc[-1]: p.append('Linhas Separadas de Baixa')
    # 28. Bullish Harami
    if ((C1 < O1) & (r1 >= 0.7) & (r < 0.3) & (r >= 0.1) & (H < O1) & (L > C1)).iloc[-1]: p.append('Harami de Alta')
    # 29. Bearish Harami
    if ((C1 > O1) & (r1 >= 0.7) & (r < 0.3) & (r >= 0.1) & (H < C1) & (L > O1)).iloc[-1]: p.append('Harami de Baixa')
    # 30. Bullish Engulfing
    if ((C1 < O1) & (r1 < 0.3) & (r1 >= 0.1) & (C > O) & (r >= 0.7) & (H1 < C) & (L1 > O)).iloc[-1]: p.append('Engolfo de Alta')
    # 31. Bearish Engulfing
    if ((C1 > O1) & (r1 < 0.3) & (r1 >= 0.1) & (C < O) & (r >= 0.7) & (H1 < O) & (L1 > C)).iloc[-1]: p.append('Engolfo de Baixa')
    # 32. Doji Bullish Engulfing
    if ((r1 < 0.1) & (C > O) & (r >= 0.7) & (H1 < C) & (L1 > O) & (us1 > 3*body1) & (ls1 <= body1)).iloc[-1]: p.append('Engolfo de Alta com Doji')
    # 33. Doji Bearish Engulfing
    if ((r1 < 0.1) & (C < O) & (r >= 0.7) & (H1 < O) & (L1 > C) & (us1 > 3*body1) & (ls1 <= body1)).iloc[-1]: p.append('Engolfo de Baixa com Doji')

    return p

# ==========================================
# 5. INTERFACE DO SCANNER
# ==========================================
with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        lista_alvo = st.selectbox("Selecione a Lista:", ["BDRs Elite", "IBrX Seleção", "Todos (BDRs + IBrX)"])
    with col2:
        tempo_grafico = st.selectbox("Tempo Gráfico:", ['15m', '60m', '1d', '1wk'], index=2, format_func=lambda x: {'15m': '15 min', '60m': '60 min', '1d': 'Diário', '1wk': 'Semanal'}[x])
    with col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_radar = st.button("🔍 Escanear Price Action Avançado", type="primary", use_container_width=True)

if btn_radar:
    ativos = bdrs_elite if lista_alvo == "BDRs Elite" else ibrx_selecao if lista_alvo == "IBrX Seleção" else bdrs_elite + ibrx_selecao
    ativos = sorted(list(set([a.replace('.SA', '') for a in ativos])))
    
    intervalo_tv = {'15m': Interval.in_15_minute, '60m': Interval.in_1_hour, '1d': Interval.in_daily, '1wk': Interval.in_weekly}[tempo_grafico]
    
    resultados = []
    p_bar = st.progress(0)
    s_text = st.empty()
    
    # ------------------------------------
    # VARREDURA SILENCIOSA
    # ------------------------------------
    for i, ativo in enumerate(ativos):
        s_text.text(f"Mapeando velas institucionais: {ativo} ({i+1}/{len(ativos)})")
        p_bar.progress((i + 1) / len(ativos))
        
        try:
            df = tv.get_hist(symbol=ativo, exchange='BMFBOVESPA', interval=intervalo_tv, n_bars=20)
            if df is not None and not df.empty:
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
                
                padroes_encontrados = escanear_padroes(df)
                
                if padroes_encontrados:
                    cotacao = df['Close'].iloc[-1]
                    for padrao in padroes_encontrados:
                        # Limpa redundâncias básicas (se houver engolfo, ignora se a sub-classificação menor apitar junto)
                        if 'Doji' in padrao and len(padroes_encontrados) > 1 and padrao == 'Doji': continue
                        
                        info = dicionario_padroes.get(padrao, {'Tipo': '⚪ Neutro', 'Desc': 'Padrão mapeado pelo radar.'})
                        resultados.append({
                            'Ativo': ativo,
                            'Cotação': f"R$ {cotacao:.2f}",
                            'Padrão Formado': padrao,
                            'Direção': info['Tipo'],
                            'Leitura Psicológica': info['Desc']
                        })
        except Exception as e:
            pass
        time.sleep(0.01)
        
    p_bar.empty(); s_text.empty()
    
    # ------------------------------------
    # EXIBIÇÃO DE RESULTADOS
    # ------------------------------------
    st.divider()
    if resultados:
        st.success(f"🎯 Varredura concluída! O Scanner Mamona detectou **{len(resultados)}** formações táticas ativas no mercado agora.")
        df_res = pd.DataFrame(resultados)
        
        def colorir_direcao(val):
            if isinstance(val, str):
                if '🟢' in val: return 'color: #00FF00; font-weight: bold'
                elif '🔴' in val: return 'color: #FF4D4D; font-weight: bold'
                elif '⚪' in val: return 'color: #d3d3d3; font-weight: bold'
            return ''

        try:
            styled_df = df_res.style.map(colorir_direcao, subset=['Direção'])
        except AttributeError:
            styled_df = df_res.style.applymap(colorir_direcao, subset=['Direção'])

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("🤷‍♂️ Calmaria nas trincheiras. Nenhum padrão tático foi detectado neste tempo gráfico.")
