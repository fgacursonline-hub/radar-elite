import streamlit as st
import pandas as pd

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CAMUFLAGEM
# ==========================================
st.set_page_config(page_title="Manual IFR | Caçadores de Elite", layout="wide", page_icon="📖")

# --- CAMUFLAGEM AGRESSIVA: OCULTAR O MANUAL DO MENU LATERAL ---
st.markdown("""
    <style>
    /* Força o desaparecimento de qualquer link no menu lateral que contenha a palavra 'Manual' */
    [data-testid="stSidebarNav"] a[href*="Manual"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
    st.error("🚫 Por favor, faça login na página inicial (Home).")
    st.stop()

# ==========================================
# 2. CABEÇALHO DO MANUAL
# ==========================================
st.title("📖 Manual de Operações Especiais: IFR & Connors")
st.markdown("### Bem-vindo ao guia definitivo do sistema de Regressão à Média.")
st.divider()

# ==========================================
# 3. CONCEITO GERAL DO SETUP
# ==========================================
st.header("🧠 1. A Filosofia do Setup (Regressão à Média)")
st.markdown("""
A estratégia de **Índice de Força Relativa (IFR)** é baseada num princípio matemático imutável do mercado: o efeito "elástico". 
Quando um ativo cai por muitos dias consecutivos, ele fica "esticado" para baixo. A força vendedora entra em exaustão, e os institucionais que estavam vendidos começam a recomprar (zerar posições) para garantir os lucros. Isso gera um repique rápido e violento de alta. 

**O nosso objetivo não é adivinhar se a ação vai subir nos próximos 5 anos.** O nosso objetivo é comprar o pânico extremo num dia e vender no alívio desse pânico poucos dias depois. É uma operação de giro tático (Swing Trade curto).
""")

# ==========================================
# 4. OS INDICADORES UTILIZADOS
# ==========================================
st.header("⚙️ 2. O Arsenal de Indicadores")
col1, col2 = st.columns(2)

with col1:
    st.info("""
    #### 📉 IFR (Índice de Força Relativa)
    É o motor do sistema. Ele varia de 0 a 100.
    * **Acima de 70:** Ativo sobrecomprado (Caro).
    * **Abaixo de 30 (ou 25):** Ativo sobrevendido (Barato/Pânico).
    * **O nosso gatilho Padrão:** O robô entra comprando quando o IFR cai abaixo de 25 e, em seguida, vira para cima, sinalizando que a queda parou.
    """)
    st.success("""
    #### 📈 MME5 (Média Móvel Exponencial de 5 períodos)
    Usada como **Alvo Móvel** no Setup IFR2 de Connors. Ela rastreia o preço muito de perto. Quando o preço cruza essa média para cima, significa que o repique de curto prazo terminou e é hora de colocar o lucro no bolso.
    """)

with col2:
    st.warning("""
    #### 📏 MM200 (Média Móvel Simples de 200 períodos)
    O grande filtro de tendência. Utilizada no Setup Connors para proteger o seu capital. Se o preço estiver acima da MM200, estamos em "Bull Market" e as compras são seguras. Se estiver abaixo, estamos a tentar apanhar uma faca a cair num "Bear Market" (alto risco).
    """)
    st.error("""
    #### 👑 Máxima dos Últimos 2 Dias
    Outra forma de alvo móvel. Exige uma saída agressiva e rápida. Se você comprou hoje, a sua saída será posicionada no ponto mais alto atingido pelo ativo nos dois dias anteriores.
    """)

st.divider()

# ==========================================
# 5. AS DIFERENTES ABAS DO TERMINAL
# ==========================================
st.header("🗂️ 3. O Mapa do Terminal (O que faz cada Aba)")

st.markdown("""
A sua tela de rastreamento possui múltiplas abas, cada uma projetada para um nível de risco e tipo de gestão de capital diferente:

1.  **📡 Radar Padrão (Sem PM):** Faz uma única entrada de compra assim que o IFR atinge o gatilho. Você define um alvo fixo (Ex: 5%). Ele fica segurando a operação até bater esse alvo. Não usa Stop Loss (conta com a reversão matemática a longo prazo).
2.  **📡 Radar (PM Dinâmico):** Estratégia pesada para grandes capitais. Se a ação continuar caindo após a primeira entrada e der um novo sinal de IFR, o robô faz uma nova compra (Aporte), puxando o seu Preço Médio (PM) para baixo. Quando a ação respira, você sai no lucro muito mais rápido.
3.  **🛡️ Alvo & Stop:** A proteção máxima. Faz uma entrada e arma uma ordem OCO (One Cancels Other). Se bater o alvo, lucro. Se o mercado desabar além da sua proteção (Ex: 5% de queda), ele zera a posição e assume o prejuízo.
4.  **🔬 Raio-X Individual:** O laboratório de testes. Em vez de varrer todas as ações, você digita apenas uma (Ex: VALE3) e o robô destrincha o comportamento passado dela para provar se a estratégia funciona para aquele ativo específico.
5.  **📉 Raio-X Futuros:** Exclusivo para operações de Day Trade e Swing em contratos de Índice (WIN) e Dólar (WDO) no gráfico de 15 minutos.
6.  **🩸 IFR2 (Connors):** A "Máquina de Pânico". Usa o IFR calibrado em apenas **2 períodos**. É extremamente agressivo. Só compra quedas violentas e tenta sair no dia seguinte ou em 2 dias.
""")

st.divider()

# ==========================================
# 6. COMO PREENCHER OS CAMPOS (PASSO A PASSO)
# ==========================================
st.header("🎛️ 4. Manual de Configuração dos Parâmetros")
st.markdown("Antes de apertar o botão de varredura, você deve abastecer o robô com a sua gestão de risco:")

campos = [
    {"campo": "Lista de Ativos", "desc": "Selecione se o robô deve procurar oportunidades nas 100 ações mais líquidas do Brasil (IBrX), apenas nas tecnológicas americanas (BDRs) ou em ambas."},
    {"campo": "Período de Estudo", "desc": "Para testes de Backtest. Define quão longe no passado o robô deve ir para testar a matemática. (Recomendado: 1 a 2 anos para não pegar ciclos econômicos muito antigos)."},
    {"campo": "Alvo de Lucro (%)", "desc": "A sua meta. Assim que a ação subir este valor a partir do seu preço de entrada, o robô marca como 'Gain'. Em Swing Trade, alvos entre 3% e 6% são o padrão de ouro."},
    {"campo": "Stop Loss (%)", "desc": "(Apenas na aba 3). O seu limite de dor. Se a ação cair este valor a partir da sua compra, você corta a posição para proteger o patrimônio."},
    {"campo": "Período do IFR", "desc": "A sensibilidade do indicador. O padrão do mercado é IFR de 14. O nosso setup acelerado usa IFR de 8. (O setup Connors usa sempre 2)."},
    {"campo": "Capital por Trade / Sinal (R$)", "desc": "O tamanho do lote financeiro. Se você colocar R$ 10.000 e o robô achar 3 sinais, ele vai calcular a simulação como se você tivesse comprado R$ 10.000 de cada um das 3 ações."},
    {"campo": "Tempo Gráfico", "desc": "Qual vela o robô deve olhar? Diário (1d) para operações de Swing Trade que duram dias/semanas. 15 minutos (15m) ou 60 minutos (60m) para giro rápido intraday."}
]

df_campos = pd.DataFrame(campos)
st.table(df_campos)

st.divider()

# ==========================================
# 7. COMO FAZER AS ENTRADAS E INTERPRETAR OS RESULTADOS
# ==========================================
st.header("🎯 5. Interpretação e Execução na Corretora")

st.markdown("""
### 🟢 A Interpretação das Cores
* **Cores Verdes / "Gain ✅":** Operações que já bateram o seu alvo de lucro.
* **Cores Vermelhas / "Stop ❌":** Operações que atingiram o seu limite de prejuízo estipulado.
* **Cor Branca (Em Aberto):** O trade foi iniciado e está flutuando ao sabor do mercado, aguardando tocar na linha do alvo.

### 📝 O Fluxo da Operação Perfeita
1. **O Sinal (Fim de Tarde):** O robô de IFR trabalha melhor nos últimos 30 minutos do pregão (entre as 16h30 e as 17h00). Você roda a aba que preferir (Ex: IFR2 Connors).
2. **A Descoberta:** O painel "Oportunidades Hoje" vai listar os ativos que deram sinal de compra. O Telegram também vai enviar o alerta para o seu celular.
3. **O Gatilho:** Vá ao Home Broker da sua corretora e **Compre o ativo a mercado** nos minutos finais do pregão.
4. **Armando a Armadilha (Noite):** Após o mercado fechar, vá ao Home Broker e pendure a sua ordem de **Venda** no preço exato que o robô marcou no campo "Alvo (Saída)" do painel "Posições em Aberto". Se você usar Stop, pendure a sua ordem de Stop Loss no valor indicado.
5. **A Saída:** No dia seguinte, deixe o mercado correr. Se bater no alvo, a corretora vende sozinha e o dinheiro entra na sua conta. Volte ao painel no final do dia para repetir o processo.
""")

st.divider()
st.markdown("#### 💡 Mentalidade da Caçadora:")
st.info("*O mercado fará de tudo para tirar você do eixo. Confie no backtest, siga o tamanho do lote financeiro estipulado e jamais hesite ao receber um sinal quantitativo. A matemática protege aqueles que têm disciplina.*")

st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
col_voltar, col_vazia = st.columns([1, 4])
with col_voltar:
    # Substituído por link_button que é blindado contra erros de rota interna do Streamlit
    st.link_button("⬅️ Voltar ao Terminal IFR", "/IFR", use_container_width=True)
