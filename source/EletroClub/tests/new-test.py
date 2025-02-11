import aiohttp
import asyncio
import json
import sqlite3
import uuid
from urllib.parse import quote

# Configurações do banco de dados
DATABASE_NAME = "TESTEDAELETRO.DB"
TABLE_NAME = "produtos"

# Configuração do webhook do Discord
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1338535110215073923/cC1GCM5xS6EfTGJsw_HFJdC72kLY8gEHvvaK8lXjpGv2VrmYEweOgMigwfMWixIE0Ayo"

async def fetch_data(category, page):
    """
    Faz uma requisição assíncrona para o endpoint da Eletroclub, permitindo paginação.

    Args:
        category (str): A categoria para a qual a requisição será feita.
        page (int): O número da página a ser requisitada.
    """

    page_size = 12  # Ajuste conforme necessário
    start_index = (page - 1) * page_size
    end_index = start_index + page_size - 1

    url = "https://www.eletroclub.com.br/_v/segment/graphql/v1"
    params = {
        "workspace": "master",
        "maxAge": "short",
        "appsEtag": "remove",
        "domain": "store",
        "locale": "pt-BR",
        "__bindingId": "378597e2-4c99-4a15-b5b0-ed9a10bd1a78",
        "operationName": "productSearchV3",
        "variables": json.dumps({
            "hideUnavailableItems": False,
            "skusFilter": "ALL",
            "simulationBehavior": "default",
            "installmentCriteria": "MAX_WITHOUT_INTEREST",
            "productOriginVtex": False,
            "map": "c",
            "query": "outlet",
            "orderBy": "OrderByPriceASC",
            "from": start_index,
            "to": end_index,
            "selectedFacets": [{"key": "c", "value": "outlet"}],
            "operator": "and",
            "fuzzy": "1",
            "searchState": None,
            "facetsBehavior": "Static",
            "categoryTreeBehavior": "default",
            "withFacets": False
        }),
        "extensions": json.dumps({
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "9177ba6f883473505dc99fcf2b679a6e270af6320a157f0798b92efeab98d5d3",
                "sender": "vtex.store-resources@0.x",
                "provider": "vtex.search-graphql@0.x"
            }
        })
    }

    headers = {
        'Sec-Ch-Ua-Platform': '"macOS"',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
        'Content-Type': 'application/json',
        'Dnt': '1',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': f'https://www.eletroclub.com.br/{category}',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Priority': 'u=1, i',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Session-ID': str(uuid.uuid4())
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['data']['productSearch']['products']
                else:
                    print(f"Erro na requisição (página {page}): {response.status}")
                    text = await response.text()
                    print(f"Conteúdo do erro: {text}")
                    return []  # Retorna uma lista vazia em caso de erro
    except Exception as e:
        print(f"Erro ao fazer a requisição (página {page}): {e}")
        return []  # Retorna uma lista vazia em caso de erro

def create_database():
    """
    Cria o banco de dados SQLite e a tabela para armazenar os produtos, se não existirem.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            product_id TEXT PRIMARY KEY,
            product_name TEXT,
            product_link TEXT,
            item_id TEXT,
            item_name TEXT,
            price REAL,
            available_quantity INTEGER,
            voltage TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Banco de dados criado/verificado.")  # Adicione este log


def get_product_from_db(item_id):
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE item_id = ?", (item_id,))
            product = cursor.fetchone()

            if product:
                print(f"Produto encontrado no banco de dados para item_id {item_id}: {product}")
            else:
                print(f"Produto NÃO encontrado no banco de dados para item_id {item_id}")

            return product
    except Exception as e:
        print(f"Erro ao acessar o banco de dados: {e}")
        return None



def save_product_to_db(product, item):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        product_id = product['productId']
        product_name = product['productName']
        product_link = f"https://www.eletroclub.com.br{product['link']}"
        item_id = item['itemId']
        item_name = item['nameComplete']
        price = item['sellers'][0]['commertialOffer']['Price']
        available_quantity = item['sellers'][0]['commertialOffer']['AvailableQuantity']

        # Verificar se o produto já existe no banco
        cursor.execute(f"SELECT price, available_quantity FROM {TABLE_NAME} WHERE item_id = ?", (item_id,))
        existing_product = cursor.fetchone()

        if existing_product:
            old_price, old_stock = existing_product

            # Só atualiza e notifica se houver mudança
            if price != old_price or available_quantity != old_stock:
                cursor.execute(f"""
                    UPDATE {TABLE_NAME} 
                    SET price = ?, available_quantity = ?
                    WHERE item_id = ?
                """, (price, available_quantity, item_id))
                
                conn.commit()
                print(f"Produto atualizado: {product_name} (item_id: {item_id})")

                # Enviar notificação ao Discord
                asyncio.create_task(send_to_discord(product_name, item_id, available_quantity, price, old_price))
        else:
            # Produto novo, então insere
            cursor.execute(f"""
                INSERT INTO {TABLE_NAME} (
                    product_id, product_name, product_link, item_id, item_name, price, available_quantity
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (product_id, product_name, product_link, item_id, item_name, price, available_quantity))
            
            conn.commit()
            print(f"Novo produto adicionado: {product_name} (item_id: {item_id})")

            # Enviar notificação ao Discord para novo produto
            asyncio.create_task(send_to_discord(product_name, item_id, available_quantity, price))

    except Exception as e:
        print(f"Erro ao salvar produto no banco de dados: {e}")
    finally:
        conn.close()



async def process_product(product, item):

    # Extrai os dados do produto/item
    item_id = item['itemId']
    product_name = product['productName']
    available_quantity = item['sellers'][0]['commertialOffer']['AvailableQuantity']
    price = item['sellers'][0]['commertialOffer']['Price']



async def main():
    category = "outlet"
    num_pages = 40  # Ajuste conforme necessário

    for page in range(1, num_pages + 1):
        products = await fetch_data(category, page)
        if products:
            for product in products:
                for item in product['items']:
                    await process_product(product, item)
            print(f"Página {page} processada e salva no banco de dados.")
        else:
            print(f"Nenhum produto encontrado na página {page}.")

if __name__ == "__main__":
    asyncio.run(main())
