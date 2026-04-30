import streamlit as st
import pandas as pd

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CAMUFLAGEM
# ==========================================
st.set_page_config(page_title="Manuais de Estratégia | Caçadores de Elite", layout="wide", page_icon="📖")

# CAMUFLAGEM AGRESSIVA: OCULTAR DO MENU LATERAL
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] a[href*="Manual"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# 2. CABEÇALHO
# ==========================================
st.title("📖 Manuais de Operações Especiais (IFR)")
st.markdown("Selecione abaixo o manual da arma que você pretende utilizar no pregão de hoje.")

# Seleção do Manual para não poluir a tela
manual_selecionado = st.selectbox(
    "📚 Qual manual deseja consultar?",
    ["Radar (Padrão, PM e Stop) + Raio-X", "Raio-X Futuros (Day Trade)", "IFR2 Connors (Máquina de Pânico)"]
)

st.divider()

# ==========================================
# MANUAL 1: RADAR PADRÃO, PM, STOP E RAIO-X
# ==========================================
if manual_selecionado == "Radar (Padrão, PM e Stop) + Raio-X":
    st.header("📡 Seção 1: Varredura de Ações (Setup IFR Clássico)")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        O Setup clássico de IFR busca o **ponto de inflexão**. O indicador mede a velocidade e a mudança dos movimentos de preço. 
        Neste sistema, operamos o **cruzamento ascendente do nível 25**.
        
        * **A Lógica:** Quando o IFR cai abaixo de 25, o ativo está "vencido". Quando ele volta a cruzar o 25 para cima, o robô entende que a pressão vendedora acabou e o repique começou.
        """)
    with col2:
        st.info("**Indicador Principal:** IFR (RSI) de 8 períodos.")

    st.subheader("🛠️ As 4 Variações da Estratégia")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Padrão", "PM Dinâmico", "Alvo & Stop", "Raio-X Individual"])
    
    with tab1:
        st.markdown("""
        **1. Radar Padrão (Entrada Única):**
        * **Como funciona:** Faz uma única compra. Não aceita novos aportes se o preço continuar caindo.
        * **Saída:** Apenas no Alvo de Lucro fixo definido por você (Ex: 5%).
        * **Indicação:** Para quem tem pouco capital ou quer deixar o trade "correr" sem se preocupar com stops curtos.
        """)
        
    with tab2:
        st.markdown("""
        **2. Radar PM (Preço Médio Dinâmico):**
        * **Como funciona:** Se você comprou e o IFR deu um **novo sinal** ainda mais baixo, o robô faz um novo aporte.
        * **Vantagem:** O seu custo médio cai. O lucro (Alvo %) passa a ser calculado sobre o novo PM, fazendo você sair do trade muito mais rápido no primeiro respiro do mercado.
        * **Risco:** Exposição financeira aumenta a cada novo aporte.
        """)
        
    with tab3:
        st.markdown("""
        **3. Alvo & Stop Loss:**
        * **Como funciona:** Operação "matar ou morrer". Ao entrar, o robô define o Alvo (ex: 5%) e o Stop de proteção (ex: 5%).
        * **Diferencial:** Protege o patrimônio contra quedas estruturais (Black Swans). Ideal para traders que não aceitam ficar "presos" em ativos por muito tempo.
        """)

    with tab4:
        st.markdown("""
        **4. Raio-X Individual (Laboratório):**
        * **Como funciona:** É a sua ferramenta de validação. Antes de operar, você testa o ativo.
        * **O que olhar:** Olhe a "Taxa de Acerto" e a "Duração Média". Se um ativo demora 30 dias para dar 3% de lucro, talvez não valha o seu capital parado.
        """)

# ==========================================
# MANUAL 2: FUTUROS (DAY TRADE)
# ==========================================
elif manual_selecionado == "Raio-X Futuros (Day Trade)":
    st.header("📉 Seção 2: Mercado Futuro (WIN & WDO)")
    
    
    st.warning("⚠️ **ALERTA DE RISCO:** O mercado futuro é alavancado. Use este manual para entender a proteção de capital.")

    st.markdown("""
    Este módulo é focado em **Intraday (Day Trade)** utilizando o gráfico de **15 minutos**. 
    
    ### ⚙️ Campos Específicos:
    1.  **Alvo e Stop (Pontos):** Diferente de ações, aqui usamos pontos. 
        * *Mini Índice (WIN):* Alvos comuns de 300 a 500 pontos.
        * *Mini Dólar (WDO):* Alvos comuns de 10 a 20 pontos.
    2.  **Multiplicador (R$):** * WIN: R$ 0,20 por ponto.
        * WDO: R$ 10,00 por ponto.
    3.  **Zeragem Automática:** Se marcado, o robô simula a saída obrigatória no fechamento do dia (17h55), mesmo que não tenha batido no alvo ou stop. Isso evita "dormir posicionado" e pagar margens extras à B3.

    ### 🎯 Como Interpretar o Resultado:
    * **Expectativa Real (Payoff):** Se o seu ganho médio for maior que a sua perda média, o sistema é lucrativo no longo prazo.
    * **Margem de Gordura:** Mostra o quanto você pode errar antes da estratégia se tornar perdedora.
    """)

# ==========================================
# MANUAL 3: IFR2 CONNORS
# ==========================================
elif manual_selecionado == "IFR2 Connors (Máquina de Pânico)":
    st.header("🩸 Seção 3: IFR2 de Larry Connors (Reversão Extrema)")
    
    st.error("""
    **A Filosofia do Pânico:** O IFR2 não busca tendências. Ele busca "Crashes" de curto prazo. 
    A ideia é comprar quando ninguém mais quer, no auge do medo, e vender no primeiro suspiro de alívio.
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        ### 📥 A Entrada (O Gatilho)
        * **IFR2 < 25 (ou 10):** O ativo está em colapso momentâneo.
        * **Filtro MM200:** O segredo dos profissionais. Só compramos a "faca caindo" se o ativo estiver acima da média de 200 dias (tendência de alta de longo prazo). Isso garante que estamos comprando uma correção, não uma falência.
        """)
    with col_b:
        st.markdown("""
        ### 📤 A Saída (O Alvo)
        * **Máxima de 2 Dias:** Saída agressiva. Vendemos assim que o preço tocar na máxima dos dois dias anteriores.
        * **Fechamento > MME5:** Saída técnica. Aguardamos o preço fechar acima da média rápida de 5 dias.
        """)

    st.info("💡 **Dica de Elite:** O IFR2 tem uma taxa de acerto altíssima (geralmente > 75%), mas os ganhos são pequenos e rápidos. É um sistema para quem gosta de girar o capital rapidamente.")

# ==========================================
# 3. RODAPÉ
# ==========================================
st.divider()
col_v, col_m = st.columns([1, 4])
with col_v:
    st.link_button("⬅️ Voltar ao Terminal", "/IFR", use_container_width=True)
with col_m:
    st.caption("Manual atualizado em Abril de 2026. Reservado aos alunos Caçadores de Elite.")
