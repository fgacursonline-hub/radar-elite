# --- CONFIGURAÇÃO CENTRAL DE ATIVOS - CAÇADORES DE ELITE ---

# 1. BDRs de Elite (Foco Internacional)
bdrs_elite = [
    'NVDC34.SA', 'P2LT34.SA', 'ROXO34.SA', 'INBR32.SA', 'M1TA34.SA', 
    'TSLA34.SA', 'LILY34.SA', 'AMZO34.SA', 'AURA33.SA', 'GOGL34.SA', 
    'MSFT34.SA', 'MUTC34.SA', 'MELI34.SA', 'C2OI34.SA', 'ORCL34.SA', 
    'M2ST34.SA', 'A1MD34.SA', 'NFLX34.SA', 'ITLC34.SA', 'AVGO34.SA', 
    'COCA34.SA', 'JBSS32.SA', 'AAPL34.SA', 'XPBR31.SA', 'STOC34.SA'
]

# 2. IBrX Seleção (Foco Nacional)
ibrx_selecao = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 
    'ABEV3.SA', 'WEGE3.SA', 'AXIA3.SA', 'SUZB3.SA', 'RENT3.SA', 'RADL3.SA', 
    'EQTL3.SA', 'LREN3.SA', 'PRIO3.SA', 'HAPV3.SA', 'GGBR4.SA', 'VBBR3.SA', 
    'SBSP3.SA', 'CMIG4.SA', 'CPLE3.SA', 'ENEV3.SA', 'TIMS3.SA', 'TOTS3.SA', 
    'EGIE3.SA', 'CSAN3.SA', 'ALOS3.SA', 'DIRR3.SA', 'VIVT3.SA', 'KLBN11.SA', 
    'UGPA3.SA', 'PSSA3.SA', 'CYRE3.SA', 'ASAI3.SA', 'RAIL3.SA', 'ISAE3.SA', 
    'CSNA3.SA', 'MGLU3.SA', 'EMBJ3.SA', 'TAEE11.SA', 'BBSE3.SA', 'FLRY3.SA', 
    'MULT3.SA', 'TFCO4.SA', 'LEVE3.SA', 'CPFE3.SA', 'GOAU4.SA', 'MRVE3.SA', 
    'YDUQ3.SA', 'SMTO3.SA', 'SLCE3.SA', 'CVCB3.SA', 'USIM5.SA', 'BRAP4.SA', 
    'BRAV3.SA', 'EZTC3.SA', 'PCAR3.SA', 'AUAU3.SA', 'DXCO3.SA', 'CASH3.SA', 
    'VAMO3.SA', 'AZZA3.SA', 'AURE3.SA', 'BEEF3.SA', 'ECOR3.SA', 'FESA4.SA', 
    'POMO4.SA', 'CURY3.SA', 'INTB3.SA', 'JHSF3.SA', 'LIGT3.SA', 'LOGG3.SA', 
    'MDIA3.SA', 'MBRF3.SA', 'NEOE3.SA', 'QUAL3.SA', 'RAPT4.SA', 'ROMI3.SA', 
    'SANB11.SA', 'SIMH3.SA', 'TEND3.SA', 'VULC3.SA', 'PLPL3.SA', 'CEAB3.SA', 
    'UNIP6.SA', 'LWSA3.SA', 'BPAC11.SA', 'GMAT3.SA', 'CXSE3.SA', 'ABCB4.SA', 
    'CSMG3.SA', 'SAPR11.SA', 'GRND3.SA', 'BRAP3.SA', 'LAVV3.SA', 'RANI3.SA', 
    'ITSA3.SA', 'ALUP11.SA', 'FIQE3.SA', 'COGN3.SA', 'IRBR3.SA', 'SEER3.SA', 
    'ANIM3.SA', 'JSLG3.SA', 'POSI3.SA', 'MYPK3.SA', 'SOJA3.SA', 'BLAU3.SA', 
    'PGMN3.SA', 'TUPY3.SA', 'VVEO3.SA', 'MELK3.SA', 'SHUL4.SA', 'BRSR6.SA'
]

# 3. Mapeamento BDR ↔ STOCK (Para Arbitragem)
pares_elite = {
    'NVDC34': 'NVDA', 'P2LT34': 'PLTR', 'ROXO34': 'NU', 'INBR32': 'INTR',
    'M1TA34': 'META', 'TSLA34': 'TSLA', 'LILY34': 'LLY', 'AMZO34': 'AMZN',
    'AURA33': 'AUY',  'GOGL34': 'GOOGL','MSFT34': 'MSFT', 'MUTC34': 'MU',
    'MELI34': 'MELI', 'C2OI34': 'COIN', 'ORCL34': 'ORCL', 'M2ST34': 'MA',
    'A1MD34': 'AMD',  'NFLX34': 'NFLX', 'ITLC34': 'INTC', 'AVGO34': 'AVGO',
    'COCA34': 'KO',   'JBSS32': 'JBS',  'AAPL34': 'AAPL', 'XPBR31': 'XP',
    'STOC34': 'STNE'
}

# 4. Índices e Benchmarks Setoriais (Termômetros do Mercado)
benchmarks_elite = [
    'IBOV',    # Índice Bovespa Principal
    'SMLL',    # Índice de Small Caps
    'IFNC',    # Índice Financeiro (Bancos)
    'IMAT',    # Índice de Materiais Básicos (Commodities)
    'IEEX',    # Índice de Energia Elétrica
    'UTIL',    # Índice Utilidade Pública (Energia e Saneamento)
    'ICON',    # Índice de Consumo e Varejo
    'IMOB',    # Índice Imobiliário (Construtoras e Shoppings)
    'INDX',    # Índice Industrial
    'AGRO',    # Índice do Agronegócio
    'IFIX',    # Índice de Fundos Imobiliários
    'BOVA11',  # ETF do Ibovespa
    'IVVB11'   # ETF do S&P 500 (EUA) negociado no Brasil
]

# 5. Ativos Macro e Futuros (Comparação Global)
# Dicionário mapeia: 'Símbolo': 'Bolsa de Origem'
macro_elite = {
    'DXY': 'TVC',          # Índice Dólar
    'WDO1!': 'BMFBOVESPA', # Mini Dólar Futuro Contínuo
    'WIN1!': 'BMFBOVESPA', # Mini Índice Futuro Contínuo
    'BIT1!': 'BMFBOVESPA', # Bitcoin Futuro B3 (Variação Financeira)
    'DI1!': 'BMFBOVESPA',  # Taxa DI Futuro
    'FEF2!': 'SGX',        # Minério de Ferro (Singapura)
    'BRN1!': 'TVC',        # Petróleo Brent Contínuo
    'XAUUSD': 'OANDA',     # Ouro Global
    'EWZ': 'AMEX',         # ETF MSCI Brazil
    'BTCUSDT': 'BINANCE'   # Bitcoin vs Tether (Referência Cripto Global)
}
