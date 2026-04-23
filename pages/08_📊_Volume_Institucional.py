# --- DENTRO DO BLOCO DE RESUMO TÁTICO ---

# Checklist Detalhado (MELHORADO COM O NÚMERO DO DELTA)
st.markdown(f"""
* {'✅' if p_poc else '❌'} **Filtro POC:** Preço {'acima' if p_poc else 'abaixo'} do valor de maior volume (R$ {res['POC']:.2f}).
* {'✅' if p_vwap else '❌'} **Filtro VWAP:** O preço {'domina' if p_vwap else 'perdeu'} a média de execução institucional (R$ {res['VWAP']:.2f}).
* {'✅' if p_delta else '❌'} **Filtro Delta:** O saldo acumulado é de **{res['Delta_Acumulado']:,.0f}** ({'Positivo' if p_delta else 'Negativo'}).
""")

# Explicação Específica no Veredito
if p_delta and res['Delta_Acumulado'] > 50000000: # Exemplo: Alerta para Delta > 50M
    st.info(f"🚀 **ANÁLISE DE ELITE:** O Delta de {res['Delta_Acumulado']:,.0f} indica uma urgência institucional raríssima. Os tubarões estão 'limpando o book' sem se importar com o preço atual.")
