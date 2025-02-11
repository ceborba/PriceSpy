import aiohttp
import asyncio
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_page(session, page_number):
    url = "https://www.magazineluiza.com.br/_next/data/A7KRakZBtQmeQGtJ2CRQN/informatica/l/in/seller---magazineluiza.json"
    params = {
        "page": str(page_number),
        "path0": "informatica",
        "path2": "in",
        "path3": "seller---magazineluiza"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        async with session.get(url, params=params, headers=headers) as response:
            logging.info(f"URL: {response.url}")  # Log da URL completa
            logging.info(f"Status: {response.status}")
            text = await response.text()
            logging.info(f"Response: {text}")
            if response.status == 200:
                try:
                    return await response.json()
                except json.JSONDecodeError as e:
                    logging.error(f"JSONDecodeError: {e}")
                    return None
            else:
                logging.error(f"Request failed with status {response.status}")
                return None
    except Exception as e:
        logging.error(f"Exception: {e}")
        return None


def extract_product_info(product):
    """
    Extrai informações de nome, link, valor e estoque de um produto.

    Args:
        product (dict): Um dicionário representando um produto do JSON.

    Returns:
        dict: Um dicionário contendo o nome, link, valor e estoque do produto.
    """
    try:
        nome = product.get('title', 'Nome não encontrado')
        path = product.get('path')
        link = f"https://www.magazineluiza.com.br/{path}" if path else 'Link não encontrado'
        valor = product.get('price', {}).get('bestPrice', 'Valor não encontrado')
        seller = product.get('seller', {})
        details = seller.get('details') if seller else None  
        estoque = details.get('stock_quantity') if details else 'Estoque não encontrado'  

        return {
            'nome': nome,
            'link': link,
            'valor': valor,
            'estoque': estoque
        }
    except Exception as e:
        logging.error(f"Erro ao extrair informações do produto: {e}")
        return None


async def main():
    async with aiohttp.ClientSession() as session:
        for page_number in range(1, 6):  # Exemplo: páginas 1 a 5
            data = await fetch_page(session, page_number)
            if data:
                print(f"Data from page {page_number}:")
                # Modifique esta parte para usar a função extract_product_info
                products = data.get('pageProps', {}).get('data', {}).get('search', {}).get('products', [])
                for product in products:
                    product_info = extract_product_info(product)
                    if product_info:
                        print(json.dumps(product_info, indent=2, ensure_ascii=False))
            else:
                print(f"Failed to fetch data from page {page_number}")
            await asyncio.sleep(10) # Espera 10 segundos

if __name__ == "__main__":
    asyncio.run(main())
