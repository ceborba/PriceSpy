import asyncio
import json
import sqlite3
import time
import pyperclip
from discord_webhook import DiscordWebhook, DiscordEmbed
import aiohttp

url = 'https://www.pichau.com.br/api/catalog'

headers = {
    'Host': 'www.pichau.com.br',
    'Content-Type': 'application/json',
    'User-Agent': 'okhttp/4.2.3',
    'Authorization': '',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Ch-UA-Platform-Version': '15.0.0',
    'Sec-Ch-UA-Platform': 'Android',
    'Sec-Ch-UA-Model': '',
    'Sec-Ch-UA-Mobile': '?0',
    'Sec-Ch-UA-Full-Version-List': 'Chromium";v="124.0.6367.208", "Google Chrome";v="124.0.6367.208", "Not-A.Brand";v="99.0.0.0"',
    'Sec-Ch-UA-Full-Version': '124.0.6367.208',
    'Sec-Ch-UA-Bitness': '64',
    'Sec-Ch-UA-Arch': 'x86',
    'Sec-Ch-UA': 'Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    'Referer': 'https://www.pichau.com.br/',
    'Priority': 'u=1, i',
    'Origin': 'https://www.pichau.com.br',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept': '*/*'
}

data_template = {
    "query": """
    query category($id: String!, $pageSize: Int!, $currentPage: Int!, $from: String!, $to: String!) {
      products(
        pageSize: $pageSize
        currentPage: $currentPage
        filter: {
          category_id: {eq: $id}
          price: { from: $from, to: $to}
          hide_from_search: { eq: "0" }
        }
        sort: { price: ASC }
      ) 
      {
        total_count
        page_info {
          total_pages
          current_page
        }
        
        items {
          id
          sku
          name
          stock_status
          url_key
          pichau_prices {
            avista
          }
          mysales_promotion {
            promotion_name
            price_discount
            price_promotional
            qty_available
            qty_sold
          }
        }
      }
    }
    """,
    "variables": {
        "id": "",  
        "pageSize": 500,  
        "currentPage": 1,
        "from": "4",  # Preço INICIAL
        "to": "20000"  # Preço FINAL
    },
    "operationName": "category"
}

# Função para criar o banco de dados
def create_db():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        sku TEXT,
        name TEXT,
        stock_status TEXT,
        url_key TEXT,
        avista REAL,
        promotion_name TEXT,
        price_discount REAL,
        price_promotional REAL,
        qty_available INTEGER,
        qty_sold INTEGER
    )
    ''')

    # Tabela para o histórico de preços
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS price_history (
        id TEXT,
        name TEXT,
        price REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id, date)
    )
    ''')

    conn.commit()
    return conn

# Função para verificar se há mudanças nos itens
def has_changes(existing_item, new_item):
    return (
        existing_item is None or
        existing_item[5] != new_item['pichau_prices']['avista'] or  # Mudança no preço à vista
        existing_item[6] != (new_item['mysales_promotion']['promotion_name'] if new_item['mysales_promotion'] else None) or  # Mudança na tag de promoção
        existing_item[7] != (new_item['mysales_promotion']['price_discount'] if new_item['mysales_promotion'] else None) or  # Mudança no desconto
        existing_item[8] != (new_item['mysales_promotion']['price_promotional'] if new_item['mysales_promotion'] else None) # Mudança no preço promocional
        # existing_item[9] != (new_item['mysales_promotion']['qty_available'] if new_item['mysales_promotion'] else None) or  # Mudança na quantidade disponível
        # existing_item[10] != (new_item['mysales_promotion']['qty_sold'] if new_item['mysales_promotion'] else None)  # Mudança na quantidade vendida
    )

# Função para inserir ou atualizar dados no banco de dados
def insert_or_update_data(conn, items):
    cursor = conn.cursor()
    changed_items = []

    for item in items:
        cursor.execute('SELECT * FROM products WHERE id = ?', (item['id'],))
        existing_item = cursor.fetchone()

        if has_changes(existing_item, item):
            cursor.execute('''
            INSERT OR REPLACE INTO products (
                id, sku, name, stock_status, url_key, avista, promotion_name, price_discount, price_promotional, qty_available, qty_sold
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['id'],
                item['sku'],
                item['name'],
                item['stock_status'],
                item['url_key'],
                item['pichau_prices']['avista'] if item['pichau_prices'] else None,
                item['mysales_promotion']['promotion_name'] if item['mysales_promotion'] else None,
                item['mysales_promotion']['price_discount'] if item['mysales_promotion'] else None,
                item['mysales_promotion']['price_promotional'] if item['mysales_promotion'] else None,
                item['mysales_promotion']['qty_available'] if item['mysales_promotion'] else None,
                item['mysales_promotion']['qty_sold'] if item['mysales_promotion'] else None
            ))
            changed_items.append(item)

            # Verifica e notifica se o preço é o menor já visto
            check_and_notify_lowest_price(conn, item)

    conn.commit()
    return changed_items

# Função para registrar o preço no histórico
def insert_price_history(conn, item):
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO price_history (id, name, price)
    VALUES (?, ?, ?)
    ''', (item['id'], item['name'], item['pichau_prices']['avista']))
    conn.commit()

# Função para verificar se o produto atingiu o menor preço
def check_and_notify_lowest_price(conn, item):
    cursor = conn.cursor()
    cursor.execute('''
    SELECT MIN(price) FROM price_history WHERE id = ?
    ''', (item['id'],))
    min_price = cursor.fetchone()[0]

    if min_price is None or item['pichau_prices']['avista'] < min_price:
        # Enviar mensagem que o produto está com o menor preço
        print(f"Atenção! O produto {item['name']} atingiu o menor preço visto: R${item['pichau_prices']['avista']}")
        send_discord_webhook(item, "Menor preço visto!")
        
        # Insere o novo preço no histórico
        insert_price_history(conn, item)

# Função para enviar mensagem para o Discord via webhook
def send_discord_webhook(item, alert="Alteração de Preço Detectada"):
    green_circle = "🟢"
    red_circle = "🔴"
    yellow_circle = "🟡"
    gray_circle = "⚪"  # Adicionando uma bolinha cinza para 0% de desconto
    webhook_url = 'https://discord.com/api/webhooks/1328825554585124946/fihRKqvWeb2VYXduB3irWROHHV0uNxP33tXFngWE_oz3Zc1nvfawMC9zvOhcqAo4bxw0'

    # Verificando se o produto tem promoção
    if item['mysales_promotion']:
        promotion_name = item['mysales_promotion']['promotion_name']
        price_discount = item['mysales_promotion']['price_discount']
        price_promotional = item['mysales_promotion']['price_promotional']
    else:
        promotion_name = "Sem promoção"
        price_discount = 0
        price_promotional = "N/A"

    # Preparando a mensagem de notificação
    embed = DiscordEmbed(
        title=alert,
        description=f"Nome: {item['name']}\n"
                    f"Preço à vista: {item['pichau_prices']['avista']}\n"
                    f"Quantidade disponível: {item['mysales_promotion']['qty_available'] if item['mysales_promotion'] else 'N/A'}\n"
                    f"Quantidade vendida: {item['mysales_promotion']['qty_sold'] if item['mysales_promotion'] else 'N/A'}\n"
                    f"Promoção: {promotion_name}",
        color='03b2f8'
    )

    # Lógica para o desconto
    if price_discount == 0:
        # Se o desconto for 0%, usa uma bolinha cinza (⚪)
        embed.add_embed_field(
            name='Desconto',
            value=f"{gray_circle}  {price_discount}% - Sem Desconto"
        )
    elif 1 <= price_discount <= 30:
        # Se o desconto estiver entre 1% e 30%, usa a bolinha vermelha (🔴)
        embed.add_embed_field(
            name='Desconto',
            value=f"{red_circle}  {price_discount}%"
        )
    elif 31 <= price_discount <= 60:
        # Se o desconto estiver entre 31% e 60%, usa a bolinha amarela (🟡)
        embed.add_embed_field(
            name='Desconto',
            value=f"{yellow_circle}  {price_discount}%"
        )
    else:
        # Se o desconto for maior que 60%, usa a bolinha verde (🟢)
        embed.add_embed_field(
            name='Desconto',
            value=f"{green_circle}  {price_discount}%"
        )

    embed.add_embed_field(
        name='Página do produto',
        value=f"[Clique aqui](https://www.pichau.com.br/{item['url_key']})"
    )

    # Enviando o webhook para o primeiro Discord
    webhook1 = DiscordWebhook(url=webhook_url, embeds=[embed])
    webhook1.execute()

    # Enviando o webhook para o segundo Discord
    send_discord_webhook2(item, alert)


def send_discord_webhook2(item, alert="Alteração de Preço Detectada"):
    green_circle = "🟢"
    red_circle = "🔴"
    yellow_circle = "🟡"
    gray_circle = "⚪"  # Adicionando uma bolinha cinza para 0% de desconto
    webhook_url = 'https://discord.com/api/webhooks/1322963786398830734/hxwTp0iiZ4Hpfl95W-0NbtLV7sSTGbBr64CvOfWdR20PQ0kKDEMy3TiPWU8Y9Rr9aRLH'

    # Verificando se o produto tem promoção
    if item['mysales_promotion']:
        promotion_name = item['mysales_promotion']['promotion_name']
        price_discount = item['mysales_promotion']['price_discount']
        price_promotional = item['mysales_promotion']['price_promotional']
    else:
        promotion_name = "Sem promoção"
        price_discount = 0
        price_promotional = "N/A"

    # Preparando a mensagem de notificação
    embed = DiscordEmbed(
        title=alert,
        description=f"Nome: {item['name']}\n"
                    f"Preço à vista: {item['pichau_prices']['avista']}\n"
                    f"Quantidade disponível: {item['mysales_promotion']['qty_available'] if item['mysales_promotion'] else 'N/A'}\n"
                    f"Quantidade vendida: {item['mysales_promotion']['qty_sold'] if item['mysales_promotion'] else 'N/A'}\n"
                    f"Promoção: {promotion_name}",
        color='03b2f8'
    )

    # Lógica para o desconto
    if price_discount == 0:
        # Se o desconto for 0%, usa uma bolinha cinza (⚪)
        embed.add_embed_field(
            name='Desconto',
            value=f"{gray_circle}  {price_discount}% - Sem Desconto"
        )
    elif 1 <= price_discount <= 30:
        # Se o desconto estiver entre 1% e 30%, usa a bolinha vermelha (🔴)
        embed.add_embed_field(
            name='Desconto',
            value=f"{red_circle}  {price_discount}%"
        )
    elif 31 <= price_discount <= 60:
        # Se o desconto estiver entre 31% e 60%, usa a bolinha amarela (🟡)
        embed.add_embed_field(
            name='Desconto',
            value=f"{yellow_circle}  {price_discount}%"
        )
    else:
        # Se o desconto for maior que 60%, usa a bolinha verde (🟢)
        embed.add_embed_field(
            name='Desconto',
            value=f"{green_circle}  {price_discount}%"
        )

    embed.add_embed_field(
        name='Página do produto',
        value=f"[Clique aqui](https://www.pichau.com.br/{item['url_key']})"
    )

    # Enviando o webhook para o segundo Discord
    webhook2 = DiscordWebhook(url=webhook_url, embeds=[embed])
    webhook2.execute()

    print(f"Webhook enviado para os Discords com SKU: {item['sku']}")


async def fetch(session, url, category_id, conn, semaphore):
    async with semaphore:
        current_page = 1
        total_pages = float('inf')

        while current_page <= total_pages:
            start_time = time.time()

            data = json.loads(json.dumps(data_template))
            data["variables"]["id"] = category_id
            data["variables"]["currentPage"] = current_page

            async with session.post(url, headers=headers, data=json.dumps(data)) as response:
                end_time = time.time()
                elapsed_time = end_time - start_time

                print(f"Código de Status: (Category ID: {category_id}, Page: {current_page}):", response.status)

                try:
                    response_json = await response.json()

                    items = response_json['data']['products']['items']
                    if not items:
                        print(f"Não foram encontrados mais itens para o ID da categoria: {category_id} na Página: {current_page}. Parando.")
                        break

                    total_pages = response_json['data']['products']['page_info']['total_pages']
                    in_stock_items = [
                        item for item in items
                        if item['stock_status'] != "OUT_OF_STOCK"
                    ]

                    changed_items = insert_or_update_data(conn, in_stock_items)
                    if changed_items:
                        print("ATENÇÃO: Itens alterados:")
                        for item in changed_items:
                                print(f"  - ID: {item['id']}, SKU: {item['sku']}, Nome: {item['name']}")
                                send_discord_webhook(item)  

                except json.JSONDecodeError as e:
                    print("Falha ao analisar o JSON:", e)

                except Exception as e:
                    print("Erro ao processar a resposta:", e)

                print(f"Tempo corrido (Category ID: {category_id}, Page: {current_page}): {elapsed_time} segundos")

            current_page += 1

async def run_pichau_watcher7():
    conn = create_db()
    semaphore = asyncio.Semaphore(15)

    while True:
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            category_ids = ["9", "102", "131", "14"]
            tasks = [fetch(session, url, category_id, conn, semaphore) for category_id in category_ids]
            await asyncio.gather(*tasks)

        end_time = time.time()
        total_elapsed_time = end_time - start_time
        total_elapsed_time_rounded = round(total_elapsed_time, 4)
        print(f"Tempo total: {total_elapsed_time_rounded} segundos") 

        await asyncio.sleep(1)


