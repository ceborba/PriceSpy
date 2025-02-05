import asyncio
import tls_client
import logging
from datetime import datetime

# Configuração do logging
log_filename = f"casasbahia_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_casasbahia_data(session, page, max_retries=3, delay=1):
    url = "https://api-partner-prd.casasbahia.com.br/api/v2/Search"
    params = {
        "ResultsPerPage": "37",
        "ApiKey": "casasbahia",
        "Filter": "L139420",
        "Page": str(page),
        "Banner": "true",
        "PlatformType": "1",
        "VariantConfiguration": "A",
        "multiselection": "false",
        "PartnerKey": "solr",
        "Sortby": "popularidade"
    }
    
    headers = {
        "accept": "*/*",
        "origin": "https://www.casasbahia.com.br",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Dados obtidos com sucesso para a página {page}")
                return data
            else:
                logging.warning(f"Tentativa {attempt + 1}: Erro na requisição GET para a página {page}: {response.status_code}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logging.error(f"Todas as tentativas falharam para a página {page}")
                    return None
        except Exception as e:
            logging.error(f"Erro na tentativa {attempt + 1} para a página {page}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logging.error(f"Todas as tentativas falharam para a página {page}")
                return None

async def extract_products(response):
    if not response or "products" not in response:
        return []

    products = response["products"]
    extracted_data = [
        {
            "id": product["id"],
            "name": product["name"],
            "url": product["url"],
            "sku": product["sku"]
        }
        for product in products
    ]
    return extracted_data

async def extrair_produtos():
    session = tls_client.Session(client_identifier="firefox_102")
    
    all_products = []
    for page in range(0, 8):
        response = await fetch_casasbahia_data(session, page)
        if response:
            products = await extract_products(response)
            all_products.extend(products)
        else:
            break  # Sai do loop se não houver mais páginas

    logging.info(f"Total de produtos extraídos: {len(all_products)}")
    return all_products

async def fetch_preco_produtos():
    produtos = await extrair_produtos()

    logging.info("\nProdutos extraídos:")
    # for i, produto in enumerate(produtos, 1):
    #     # logging.info(f"{i}. ID: {produto['id']}")
    #     # logging.info(f"   Nome: {produto['name']}")
    #     # logging.info(f"   URL: {produto['url']}")
    #     # logging.info(f"   SKU: {produto['sku']}")
    #     # logging.info("-" * 50)

    ids_produtos_str = ",".join(str(produto["id"]) for produto in produtos)

    url = "https://api.casasbahia.com.br/merchandising/oferta/v1/Preco/Produto/PrecoVenda/"
    params = {
        "idRegiao": "",
        "idsProduto": ids_produtos_str,
        "composicao": "DescontoFormaPagamento,MelhoresParcelamentos",
        "apiKey": "d081fef8c2c44645bb082712ed32a047"
    }

    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="122", "Google Chrome";v="122", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'accept': '*/*',
        'origin': 'https://www.casasbahia.com.br',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://www.casasbahia.com.br/',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority': 'u=1, i'
    }

    session = tls_client.Session(client_identifier="chrome_122", random_tls_extension_order=True)

    response = session.get(url, headers=headers, params=params)
    logging.info(f"Status: {response.status_code}")

    new_cookies = session.cookies.get_dict()
    # logging.info(f"Novos Cookies: {new_cookies}")

    session.cookies.update(new_cookies)

    response2 = session.get(url, headers=headers, params=params)
    logging.info(f"Status Segunda Requisição: {response2.status_code}")

    data = response2.json()
    # logging.info(f"Resposta da API de preços: {data}")


    return produtos, data.get('PrecoProdutos', [])

async def juntar_e_exibir_produtos():
    produtos, precos = await fetch_preco_produtos()
    
    produto_dict = {str(produto['sku']): produto for produto in produtos}
    
    for preco in precos:
        produto_id = str(preco['PrecoVenda']['IdSku'])
        if produto_id in produto_dict:
            produto = produto_dict[produto_id]
            preco_pix = preco['DescontoFormaPagamento']['PrecoVendaComDesconto']
            
            # logging.info(f"Produto ID: {produto['id']}")
            logging.info(f"Nome: {produto['name']}")
            logging.info(f"URL: {produto['url']}")
            logging.info(f"Preço: R$ {preco_pix:.2f}")
            logging.info(f"SKU: {produto['sku']}")
            # logging.info("-" * 50)
    
    if not precos:
        logging.info("Nenhum preço foi retornado. Verifique a resposta da API.")


if __name__ == "__main__":
    asyncio.run(juntar_e_exibir_produtos())
