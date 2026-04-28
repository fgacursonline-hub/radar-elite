import pandas as pd
import pandas_ta as ta
from tvDatafeed import TvDatafeed, Interval
from datetime import datetime

# 1. Configurações
ativo = "GOGL34"
exchange = "BMFBOVESPA"
data_alvo_str = "2025-10-24" # Data do falso positivo (ou próximo a ele, dependendo do fechamento)
adx_len = 14

print(f"📡 Iniciando diagnóstico para {ativo} na data {data_alvo_str}...")

# 2. Conecta e puxa os dados (bastante histórico para tentar igualar o "aquecimento" do RMA)
tv = TvDatafeed()
df = tv.get_hist(symbol=ativo, exchange=exchange, interval=Interval.in_daily, n_bars=1000)

if df is None or df.empty:
    print("❌ Falha ao obter dados.")
    exit()

df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
df.index = df.index.tz_localize(None)

# 3. Calcula o ADX com pandas_ta (igual ao primeiro código)
adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=adx_len)

col_adx = [c for c in adx_df.columns if c.startswith('ADX')][0]
col_dmp = [c for c in adx_df.columns if c.startswith('DMP')][0]
col_dmn = [c for c in adx_df.columns if c.startswith('DMN')][0]

df['ADX'] = adx_df[col_adx]
df['+DI'] = adx_df[col_dmp]
df['-DI'] = adx_df[col_dmn]

# 4. Busca o dia específico e o dia anterior
try:
    # Garante que a data está no formato correto para busca
    data_alvo = pd.to_datetime(data_alvo_str)
    
    # Procura a linha correspondente à data (ou a mais próxima anterior se for fim de semana/feriado)
    idx_hoje = df.index.get_indexer([data_alvo], method='pad')[0]
    idx_ontem = idx_hoje - 1

    linha_hoje = df.iloc[idx_hoje]
    linha_ontem = df.iloc[idx_ontem]

    print("\n" + "="*40)
    print(f"📊 DIAGNÓSTICO EXATO DO PYTHON PARA: {linha_hoje.name.strftime('%d/%m/%Y')}")
    print("="*40)
    
    print("\n--- VALORES NO DIA (HOJE) ---")
    print(f"Preço de Fechamento: R$ {linha_hoje['Close']:.2f}")
    print(f"ADX (Preto):         {linha_hoje['ADX']:.4f}")
    print(f"+DI (Verde):         {linha_hoje['+DI']:.4f}")
    print(f"-DI (Vermelho):      {linha_hoje['-DI']:.4f}")

    print("\n--- VALORES NO DIA ANTERIOR (ONTEM) ---")
    print(f"ADX (Preto):         {linha_ontem['ADX']:.4f}")
    print(f"-DI (Vermelho):      {linha_ontem['-DI']:.4f}")

    print("\n--- AVALIAÇÃO DA LÓGICA DO SINAL ---")
    
    # Regra 1: ADX > -DI hoje
    adx_maior_hoje = linha_hoje['ADX'] > linha_hoje['-DI']
    print(f"1. ADX > -DI hoje?       {'✅ SIM' if adx_maior_hoje else '❌ NÃO'} ({linha_hoje['ADX']:.4f} > {linha_hoje['-DI']:.4f})")
    
    # Regra 2: ADX <= -DI ontem (para confirmar o cruzamento)
    adx_menor_ontem = linha_ontem['ADX'] <= linha_ontem['-DI']
    print(f"2. ADX <= -DI ontem?     {'✅ SIM' if adx_menor_ontem else '❌ NÃO'} ({linha_ontem['ADX']:.4f} <= {linha_ontem['-DI']:.4f})")
    
    # Conclusão do Cruzamento
    cruzou = adx_maior_hoje and adx_menor_ontem
    print(f"-> O Python registrou cruzamento? {'✅ SIM, DEU CRUZAMENTO FALSO' if cruzou else '❌ NÃO, NADA DE CRUZAMENTO'}")

except Exception as e:
    print(f"Erro ao processar a data: {e}")
