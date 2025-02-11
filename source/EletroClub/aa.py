import aiohttp
import asyncio
import sqlite3
import requests
import json
import time
import uuid

async def fetch_products(session, url, from_item, to_item):
    params = {
        "_from": from_item,
        "_to": to_item,
        "O": "OrderByNameASC",
        "randomInfoRemoveCache": str(uuid.uuid4())  # Timestamp em milissegundos
    }
    headers = {
            'Sec-Ch-Ua-Platform': '"macOS"',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': '/',
            'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
            'Content-Type': 'application/json',
            'Dnt': '1',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': f'https://www.eletroclub.com.br/outlet',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Priority': 'u=1, i'
    }
    try:
        async with session.post(url, params=params, headers=headers) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        print(f"Erro ao buscar produtos: {e}")
        return None

    
def extract_product_info(product):
    product_name = product.get("productName", "N/A")
    product_link = product.get("link", "N/A")
    
    variations = []
    
    if product.get("items"):
        for item in product["items"]:
            item_name = item.get("name", "N/A")
            voltage = item.get("Voltagem", ["N/A"])[0] if item.get("Voltagem") else "N/A"
            item_id = item.get("itemId", "N/A")
            
            if item.get("sellers") and item["sellers"]:
                commercial_offer = item["sellers"][0].get("commertialOffer", {})
                available_quantity = commercial_offer.get("AvailableQuantity", 0)
                price = commercial_offer.get("Price", 0.0)
            else:
                available_quantity = 0
                price = 0.0
                
            variation_info = {
                "nome": f"{product_name} ({item_name})",
                "link": product_link,
                "estoque": available_quantity,
                "valor": price,
                "voltagem": voltage,
                "item_id": item_id
            }
            variations.append(variation_info)
    
    return variations

def send_discord_notification(webhook_url, embed):
    data = {
        "embeds": [embed]
    }
    try:
        response = requests.get(webhook_url, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar notificação para o Discord: {e}")

async def check_and_notify(cursor, conn, product_info, webhook_url):
    cursor.execute("SELECT estoque, valor FROM products WHERE nome = ?", (product_info['nome'],))
    result = cursor.fetchone()

    link_carrinho = f"https://www.eletroclub.com.br/checkout/cart/add?sku={product_info['item_id']}&qty=1&seller=1&sc=5"

    if result is None:
        if product_info['estoque'] > 0:
            embed = {
                "title": "Novo produto encontrado com estoque",
                "color": 5814783,  # Cor azul
                "fields": [
                    {"name": "Nome", "value": product_info['nome'], "inline": False},
                    {"name": "Estoque", "value": str(product_info['estoque']), "inline": True},
                    {"name": "Valor", "value": f"R$ {product_info['valor']:.2f}", "inline": True},
                    {"name": "Link do Produto", "value": product_info['link'], "inline": False},
                    {"name": "Link do Carrinho", "value": link_carrinho, "inline": False}
                ]
            }
            send_discord_notification(webhook_url, embed)
            
            cursor.execute('''
            INSERT INTO products (nome, link, estoque, valor, voltagem, item_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                product_info['nome'],
                product_info['link'],
                product_info['estoque'],
                product_info['valor'],
                product_info['voltagem'],
                product_info['item_id']
            ))
            conn.commit()
            return True
    else:
        old_stock, old_price = result
        if old_stock == 0 and product_info['estoque'] > 0:
            embed = {
                "title": "Produto voltou a ter estoque",
                "color": 5814783,  # Cor azul
                "fields": [
                    {"name": "Nome", "value": product_info['nome'], "inline": False},
                    {"name": "Novo Estoque", "value": str(product_info['estoque']), "inline": True},
                    {"name": "Valor", "value": f"R$ {product_info['valor']:.2f}", "inline": True},
                    {"name": "Link do Produto", "value": product_info['link'], "inline": False},
                    {"name": "Link do Carrinho", "value": link_carrinho, "inline": False}
                ]
            }
            send_discord_notification(webhook_url, embed)
            
            cursor.execute('''
            UPDATE products SET estoque = ?, valor = ? WHERE nome = ?
            ''', (product_info['estoque'], product_info['valor'], product_info['nome']))
            conn.commit()
            return False

    return False

async def main():
    url = "https://eletroclub.com.br/api/catalog_system/pub/products/search"
    total_items = 2500
    items_per_page = 50
    webhook_url = "https://discord.com/api/webhooks/1338535110215073923/cC1GCM5xS6EfTGJsw_HFJdC72kLY8gEHvvaK8lXjpGv2VrmYEweOgMigwfMWixIE0Ayo"

    conn = sqlite3.connect('testeeletro.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        link TEXT,
        estoque INTEGER,
        valor REAL,
        voltagem TEXT,
        item_id TEXT
    )
    ''')

    while True:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for start in range(0, total_items, items_per_page):
                end = min(start + items_per_page, total_items)
                task = asyncio.create_task(fetch_products(session, url, start + 1, end))
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            total_inserted = 0
            total_updated = 0
            for result in results:
                if isinstance(result, list):
                    for product in result:
                        extracted_products = extract_product_info(product)
                        for product_info in extracted_products:
                            insert_needed = await check_and_notify(cursor, conn, product_info, webhook_url)
                            if insert_needed:
                                total_inserted += 1
                            else:
                                total_updated += 1
                else:
                    print(f"Unexpected result: {result}")

            print(f"Inseridos {total_inserted} novos produtos. Atualizados {total_updated} produtos.")

        await asyncio.sleep(1)

asyncio.run(main())
