import logging
import httpx
import ssl
import time
import asyncio
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook, DiscordEmbed
import sqlite3

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
    'x-amazon-s-fallback-url': 'https://www.amazon.com.br/s?i=computers&rh=n%3A16339926011%2Cp_n_condition-type%3A13862762011&dc&page=2&qid=1737521104&rnid=13862761011&xpid=_FGNf-OQgb0DZ&ref=sr_pg_3',
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
    

# Configurar banco de dados
def create_database():
    conn = sqlite3.connect('amazon_hardware.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hardware (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            url TEXT,
            UNIQUE(title, price)
        )
    ''')
    conn.commit()
    conn.close()

# Função para realizar requisição
async def fetch_data(page, max_retries=10, retry_delay=1):
    params = {
        'fs': 'true',
        'i': 'computers',
        'page': f'{page}',
        'qid': int(time.time()),
        'ref': f'sr_pg_{page}',
        'rh': 'n:16243803011,p_n_availability:16254085011',
        's': 'popularity-rank',
        'xpid': 'Z1Oxh6GbzhECR',
    }
    attempts = 0

    while attempts < max_retries:
        try:
            async with httpx.AsyncClient(verify=sslcontext, timeout=30.0) as client:
                response = await client.get(
                    'https://www.amazon.com.br/s',
                    headers=headers,
                    params=params,
                    follow_redirects=True
                )
                if response.status_code == 200:
                    return response.text
                else:
                    logging.warning(f"Status code {response.status_code} recebido. Tentativa {attempts + 1} de {max_retries}.")
        except Exception as e:
            logging.error(f"Erro ao buscar dados (tentativa {attempts + 1}): {e}")

        attempts += 1
        if attempts < max_retries:
            logging.info(f"Aguardando {retry_delay} segundos antes de tentar novamente...")
            await asyncio.sleep(retry_delay)

    logging.error("Número máximo de tentativas alcançado. Falha ao obter dados.")
    return None

# Função para extrair dados
def extract_product_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    product_items = soup.find_all('div', {'data-component-type': 's-search-result'})
    products = []
    for item in product_items:
        title = item.find('h2')
        title = title.text.strip() if title else "N/A"
        price = item.find('span', {'class': 'a-price-whole'})
        price = price.text.strip() if price else "N/A"
        link = item.find('a', {'class': 'a-link-normal'})
        link = 'https://www.amazon.com.br' + link['href'] if link else "N/A"
        products.append({"title": title, "price": price, "url": link})
    return products

async def send_discord_notification(title, old_price, new_price, url, desconto_percentual, new_product=False):
    webhooks = {
        "1-20": "https://discord.com/api/webhooks/1331322843916664944/6-lXqiaxkzo8hYbTl6fD71aZkdF2Yxi8T5r_JjbdVJ_sQghNVT2tj51Of6Igg1t7geAC",
        "21-50": "https://discord.com/api/webhooks/1331322896299327509/_oM_OZRRZDIN9yZxKRYV0tSsb3zyVV3mDIM1bfpoDvxt9908IwyZfV-E9VpBR-Cjtp9k",
        "51-70": "https://discord.com/api/webhooks/1331322954428186726/vIU1ATo1GlkrsjeQrcOCMz6uyO3XZKUpeHk6Y904pZy1MLkVwE9vZcx9jceAfovANzws",
        "71-100": "https://discord.com/api/webhooks/1331323022388494457/WMlszZnhJ3xuUvx6x_ZnWs6b-_MJlmazc1xor0VWNG9ED8VU_31fMERDY8ndU_LXb7Y_",
        "novos": "https://discord.com/api/webhooks/1331322778028212294/QRguTNyM0Uiu1XBvQwrvJkIFUZ2vlYID7Y_b3D3CKiTUYVP8iB7c0ntKS3rh4mVrrsTnTIRAR"
    }

    try:
        if new_product:
            webhook_url = webhooks["novos"]
        elif desconto_percentual <= 20:
            webhook_url = webhooks["1-20"]
        elif desconto_percentual <= 50:
            webhook_url = webhooks["21-50"]
        elif desconto_percentual <= 70:
            webhook_url = webhooks["51-70"]
        else:
            webhook_url = webhooks["71-100"]

        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(title=title, description="Alteração de preço detectada!" if not new_product else "Novo produto adicionado!", color='03b2f8')
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {old_price:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {new_price:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Loja", value=f"Amazon")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique aqui]({url})")
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {title} - Novo preço: R$ {new_price:.2f} - Desconto: {desconto_percentual:.2f}%")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")
    except Exception as e:
        logging.error(f"Erro ao enviar webhook: {str(e)}")

# Função para salvar no banco
async def insert_product(product):
    conn = sqlite3.connect('amazon_hardware.db')
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id, price FROM hardware WHERE title = ? AND price = ?', (product['title'], product['price']))
        existing_product = cursor.fetchone()

        if existing_product is None:
            cursor.execute('''
                INSERT INTO hardware (title, price, url) 
                VALUES (?, ?, ?)
            ''', (product['title'], product['price'], product['url']))

            product_id = cursor.lastrowid
            
            logging.info(f"Novo produto adicionado: ID {product_id} - {product['title']}")
            
            if product['price'] != 'N/A':
                try:
                    new_price = float(product['price'].replace(',', '.'))
                    await send_discord_notification(
                        product['title'],
                        new_price,
                        new_price,
                        product['url'],
                        0,
                        True
                    )
                except ValueError:
                    logging.error(f"Preço inválido para o novo produto: {product['title']}")
        else:
            product_id, old_price = existing_product
            await update_product(product_id, product, old_price)
    except Exception as e:
        logging.error(f"Erro ao inserir/atualizar produto no banco de dados: {e}")

    conn.commit()
    conn.close()

async def update_product(product_id, product, old_price):
    conn = sqlite3.connect('amazon_hardware.db')
    cursor = conn.cursor()

    try:
        new_price = float(product['price'].replace(',', '.')) if product['price'] != 'N/A' else None
        old_price_float = float(old_price.replace(',', '.')) if old_price != 'N/A' else None

        if new_price is not None and old_price_float is not None and new_price != old_price_float:
            cursor.execute(''' 
                UPDATE hardware 
                SET price = ?, title = ?, url = ? 
                WHERE id = ?
            ''', (product['price'], product['title'], product['url'], product_id))

            logging.info(f"Produto atualizado: ID {product_id} - {product['title']}")
            logging.info(f"Preço antigo: {old_price}, Novo preço: {product['price']}")

            if new_price < old_price_float:
                desconto = ((old_price_float - new_price) / old_price_float) * 100
                await send_discord_notification(
                    product['title'],
                    old_price_float,
                    new_price,
                    product['url'],
                    desconto,
                    False
                )
    except ValueError:
        logging.error(f"Preço inválido para o produto ID {product_id}: {product['price']}")

    conn.commit()
    conn.close()

# Função principal
async def make_requests_hardware():
    create_database()
    for page in range(1, 371):  # Pode ajustar o número de páginas
        logging.info(f"Buscando página {page}...")
        html_content = await fetch_data(page)
        if html_content:
            products = extract_product_data(html_content)
            for product in products:
                await insert_product(product)
            logging.info(f"Página {page} processada com sucesso!")

if __name__ == "__main__":
    asyncio.run(make_requests_hardware())
