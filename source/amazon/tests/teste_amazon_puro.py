import logging
import httpx
import ssl
import time
import asyncio
from bs4 import BeautifulSoup
import re

# Configurar o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sslcontext = ssl.create_default_context()
sslcontext.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256')

headers = {
    'Host': 'www.amazon.com.br',
    'sec-ch-ua-platform': '"Windows"',
    'viewport-width': '1920',
    'device-memory': '8',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    'sec-ch-dpr': '1',
    'x-amazon-s-swrs-version': '8E83CA948322840B8AF73E2432C7803A,D41D8CD98F00B204E9800998ECF8427E',
    'sec-ch-ua-mobile': '?0',
    'x-requested-with': 'XMLHttpRequest',
    'accept': 'text/html,image/webp,*/*',
    'content-type': 'application/json',
    'sec-ch-viewport-width': '1920',
    'downlink': '10',
    'x-amazon-rush-fingerprints': 'AmazonRushAssetLoader:1202F8AA9B9E3A62A246BF3FA42812770110C222|AmazonRushFramework:DFA9B38DBF57C5DF6CB87A2FE4193F766423B51E|AmazonRushRouter:C5072DBFC6A5BCBC893C5127493034CF2A276286',
    'ect': '4g',
    'x-amazon-s-fallback-url': 'https://www.amazon.com.br/s?i=computers&rh=n%3A16339926011%2Cp_n_condition-type%3A13862762011&dc&page=3&qid=1737521104&rnid=13862761011&xpid=_FGNf-OQgb0DZ&ref=sr_pg_3',
    'sec-ch-device-memory': '8',
    'x-amazon-s-mismatch-behavior': 'FALLBACK',
    'dpr': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'rtt': '50',
    'sec-ch-ua-platform-version': '"10.0.0"',
    'origin': 'https://www.amazon.com.br',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://www.amazon.com.br/s?i=computers&rh=n%3A16339926011%2Cp_n_condition-type%3A13862762011&dc&page=2&qid=1737521055&rnid=13862761011&xpid=_FGNf-OQgb0DZ&ref=sr_pg_2',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'priority': 'u=1, i',
}

# Parameters
params = {
    'fs': 'true',
    'i': 'computers',
    'page': '1',
    'qid': f'{time.time()}',
    'ref': 'sr_pg_1',
    'rh': 'n:16339926011',
    's': 'popularity-rank',
    'xpid': 'Z1Oxh6GbzhECR',
}

# Função para realizar a requisição usando GET
async def fetch_data():
    logging.info("Iniciando a requisição GET...")
    try:
        async with httpx.AsyncClient(verify=sslcontext, timeout=30.0) as client:
            response = await client.post(
                'https://www.amazon.com.br/s',
                headers=headers,
                params=params
            )
            logging.info(f"Requisição GET concluída. Status code: {response.status_code}")
            response.raise_for_status()
            return response
    except httpx.RequestError as e:
        logging.error(f"Erro na requisição: {e}")
    except httpx.HTTPStatusError as e:
        logging.error(f"Erro HTTP: {e}")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
    return None

# Função para extrair os dados de produtos da resposta HTML
def extract_product_data(html_content):
    logging.info("Iniciando extração de dados dos produtos...")
    soup = BeautifulSoup(html_content, 'html.parser')

    # Adiciona log para verificar o conteúdo HTML
    logging.info(f"HTML recebido: {soup.prettify()[:500]}")  # Exibe os primeiros 500 caracteres
    
    # Busca pelos itens de produto
    product_items = soup.find_all('div', {'data-component-type': 's-search-result'})
    
    products = []
    for item in product_items:
        title = item.find('h2')
        title = title.text.strip() if title else "N/A"
        
        price = item.find('span', {'class': 'a-price-whole'})
        if not price:
            price = item.find('span', {'class': 'a-pricewhole'})
        price = price.text.strip() if price else "N/A"
        
        
        # Extraindo o link do produto
        link = item.find('a', {'class': 'a-link-normal'})
        link = 'https://www.amazon.com.br' + link['href'] if link else "N/A"
        
        products.append({
            "Título": title,
            "Preço": price,
            "Link": link
        })

    logging.info(f"Extração concluída. {len(products)} produtos encontrados.")
    return products

# Função principal para coordenar o processo
async def main():
    logging.info("Iniciando o programa...")
    response = await fetch_data()
    
    if response:
        logging.info("Salvando resposta bruta...")
        with open('response.log', 'w', encoding='utf-8') as log_file:
            log_file.write(f"Status Code: {response.status_code}\n")
            log_file.write(response.text)
        
        logging.info("Extraindo dados dos produtos...")
        products = extract_product_data(response.text)
        
        logging.info("Salvando dados dos produtos...")
        with open('products.log', 'w', encoding='utf-8') as product_file:
            for product in products:
                product_file.write(f"Título: {product['Título']}\n")
                product_file.write(f"Preço: {product['Preço']}\n")
                product_file.write(f"Link: {product['Link']}\n")
                product_file.write("---\n")
        
        logging.info("Processo concluído com sucesso.")
    else:
        logging.error("Não foi possível obter uma resposta válida.")

# Executando o código
if __name__ == "__main__":
    asyncio.run(main())
