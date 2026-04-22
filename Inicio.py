# ==========================================
# 6. RADAR DE NOTÍCIAS MULTI-FONTE (FILTRADO)
# ==========================================
st.divider()
st.subheader("📰 Radar de Notícias Caçadores de Elite")
import xml.etree.ElementTree as ET
import requests

def carregar_feed(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.content)
        itens = []
        
        # Filtro blindado contra lixo da internet e esportes
        palavras_proibidas = ['futebol', 'copa', 'assistir', 'corinthians', 'vasco', 'palmeiras', 'flamengo', 'brasileirão', 'fofoca', 'bbb', 'novela', 'filme']
        
        for item in root.findall('./channel/item'): 
            titulo = item.find('title').text
            link = item.find('link').text
            
            # Converte para minúsculas para a verificação não falhar
            titulo_lower = titulo.lower()
            
            # Se encontrar qualquer palavra proibida, ignora a notícia
            if any(palavra in titulo_lower for palavra in palavras_proibidas):
                continue
                
            itens.append({"titulo": titulo, "link": link})
            
            # Quando atingir 8 notícias limpas, pára de procurar
            if len(itens) >= 8:
                break
                
        return itens
    except: return None

# Trocamos o G1 pelo Money Times para focar 100% no mercado
tab_info, tab_inv, tab_mt = st.tabs(["💰 InfoMoney", "📈 Investing.com", "🗞️ Money Times"])

with tab_info:
    n_im = carregar_feed("https://www.infomoney.com.br/feed/")
    if n_im:
        for n in n_im: st.markdown(f"• **{n['titulo']}** [Ler mais]({n['link']})")
with tab_inv:
    n_inv = carregar_feed("https://br.investing.com/rss/news_25.rss")
    if n_inv:
        for n in n_inv: st.markdown(f"• **{n['titulo']}** [Ler mais]({n['link']})")
with tab_mt:
    n_mt = carregar_feed("https://www.moneytimes.com.br/feed/")
    if n_mt:
        for n in n_mt: st.markdown(f"• **{n['titulo']}** [Ler mais]({n['link']})")
