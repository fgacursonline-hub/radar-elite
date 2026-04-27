# CÓDIGO NOVO BLINDADO (INSERIR)
import sys
import os

# Puxa o motor da raiz do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from motor_dados import puxar_dados_blindados

# ... lá embaixo no meio do código, a chamada vira apenas 1 linha ...
df = puxar_dados_blindados(ativo, tempo_grafico=tempo_grafico, barras=150)
