import logging
import tls_client
import ssl
import time
import asyncio
from bs4 import BeautifulSoup
import sqlite3
import re
from datetime import datetime, timedelta
from discord_webhook import DiscordWebhook, DiscordEmbed


price_change_logger = logging.getLogger('price_changes')
price_change_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('price_changes.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
price_change_logger.addHandler(file_handler)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração SSL
sslcontext = ssl.create_default_context()
sslcontext.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256')

# Lista de parâmetros rh
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
]
rh_params = [
'n:16364923011',
'n:16364922011',
'n:16364766011',
'n:16339926011,n:16364748011,n:16364843011,p_n_condition-type:13862762011',
'n:16339926011,n:16364748011,n:16364768011,p_n_condition-type:13862762011',
'n:16339926011,n:16364748011,n:16364777011,n:16364913011,p_n_condition-type:13862762011',
'n:16339926011,n:16364748011,n:16364777011,n:16364980011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364752011,n:16364778011,n:16364922011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364752011,n:16364778011,n:16364923011,p_n_condition-type:13862762011',
'n:16364917011,p_n_condition-type:13862762011,p_n_feature_nine_browse-bin:23680019011',
'n:16339926011,n:16364748011,n:16364777011,n:16364919011,p_n_condition-type:13862762011',
'n:16339926011,n:16364751011,n:16364820011,p_n_condition-type:13862762011',
'n:16339926011,n:16364751011,n:16364819011,p_n_condition-type:13862762011',
'n:16339926011,n:16364757011,n:16364834011,p_n_condition-type:13862762011',
'n:16339926011,n:16364752011,n:16364778011,n:16364922011,p_n_condition-type:13862762011',
'n:16339926011,n:16364752011,n:16364778011,n:16364923011,p_n_condition-type:13862762011',
'n:16339926011,n:16364752011,n:17028669011,p_n_condition-type:13862762011',
'n:16339926011,n:16364756011,p_n_condition-type:13862762011',
'n:16339926011,n:16364755011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364817011,n:16364935011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364817011,n:16364936011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364803011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364806011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364807011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364781011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364809011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364811011,p_n_condition-type:13862762011',
'n:16339926011,n:16364750011,n:16364815011,p_n_condition-type:13862762011',
'n:16209062011,n:16243793011,n:16243872011,n:16244069011,p_n_condition-type:13862762011',
'n:16209062011,n:16243793011,n:16243803011,n:16243888011,n:16244083011,p_n_condition-type:13862762011',
'n:16209062011,n:16243793011,n:16243803011,n:16243888011,n:21213411011,p_n_condition-type:13862762011',
'n:16209062011,n:16243793011,n:16243803011,n:16243888011,n:21213406011,n:16244311011,p_n_condition-type:13862762011',
'n:16209062011,n:16243803011,n:16243890011,p_n_condition-type:13862762011',
'n:16209062011,n:16243803011,n:16243897011,p_n_condition-type:13862762011',
'n:16209062011,n:16243800011,p_n_condition-type:13862762011',
'n:16209062011,n:16364762011,p_n_condition-type:13862762011',
'n:16209062011,n:16243804011,p_n_condition-type:13862762011',
'n:16209062011,n:16243809011,n:16243811011,p_n_condition-type:13862762011',
'n:16209062011,n:16243809011,n:16243814011,p_n_condition-type:13862762011',
'n:16209062011,n:16243809011,n:16243820011,p_n_condition-type:13862762011',
'n:16209062011,n:16243809011,n:16243822011,p_n_condition-type:13862762011',
'n:16209062011,n:16243809011,n:16243930011,p_n_condition-type:13862762011',
'n:16209062011,n:16243802011,n:16244295011,p_n_condition-type:13862762011',
'n:16209062011,n:16243802011,n:21213411011,p_n_condition-type:13862762011',
'n:16209062011,n:16243802011,n:16243897011,p_n_condition-type:13862762011',
'n:16209062011,n:16243802011,n:16244073011,p_n_condition-type:13862762011',
'n:16209062011,n:24035344011,n:16244120011,n:99528904011,p_n_condition-type:13862762011',
'n:16209062011,n:24035344011,n:16244120011,p_n_condition-type:13862762011',
'n:16209062011,n:24035345011,n:16243853011,p_n_condition-type:13862762011',
'n:16209062011,n:24035345011,n:16243854011,p_n_condition-type:13862762011'
]

# Headers para a requisição
headers = {
    'Host': 'www.amazon.com.br',
    'sec-ch-ua-platform': '"Windows"',
    'viewport-width': '1920',
    'device-memory': '8',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    'sec-ch-dpr': '1',
    'x-amazon-s-swrs-version': '034889A6C5CDE6D14E94398ABA13E102,D41D8CD98F00B204E9800998ECF8427E',
    'sec-ch-ua-mobile': '?0',
    'x-requested-with': 'XMLHttpRequest',
    'accept': 'text/html,image/webp,*/*',
    'content-type': 'application/json',
    'sec-ch-viewport-width': '1920',
    'downlink': '10',
    'x-amazon-rush-fingerprints': 'AmazonRushAssetLoader:1202F8AA9B9E3A62A246BF3FA42812770110C222|AmazonRushFramework:C4F15D41D092333A22D9CCE4CB5FABCEAD581F47|AmazonRushRouter:A759EF121ED95F83515EC8D9FF59265AD3B87EDB',
    'ect': '4g',
    'x-amazon-s-fallback-url': 'https://www.amazon.com.br/s?k=Acess%C3%B3rios+de+%C3%81udio+e+V%C3%ADdeo+para+Computador&i=computers&rh=n%3A16339926011%2Cn%3A16364748011%2Cn%3A16364843011%2Cp_n_condition-type%3A13862762011&dc&page=2&c=ts&qid=1737645044&ts_id=16364843011&xpid=9O59DsoV-eAGH&ref=sr_pg_2',
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
    'referer': 'https://www.amazon.com.br/s?k=Acess%C3%B3rios+de+%C3%81udio+e+V%C3%ADdeo+para+Computador&i=computers&rh=n%3A16339926011%2Cn%3A16364748011%2Cn%3A16364843011%2Cp_n_condition-type%3A13862762011&dc&page=3&xpid=9O59DsoV-eAGH&c=ts&qid=1737644897&ts_id=16364843011&ref=sr_pg_3',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'priority': 'u=1, i',
}

# Configuração do banco de dados
def create_database():
    conn = sqlite3.connect('amazon_all_categories.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            url TEXT,
            UNIQUE(title, price)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historic_price (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            title TEXT,
            url TEXT,
            price TEXT,
            date DATETIME,
            FOREIGN KEY (product_id) REFERENCES categories(id)
        )
    ''')
    conn.commit()
    conn.close()

# Função para realizar requisição
async def fetch_data(page, rh):
    params = {
        'fs': 'true',
        'i': 'games',
        'page': f'{page}',
        'qid': int(time.time()),
        'ref': f'sr_pg_{page}',
        'rh': rh,
        's': 'popularity-rank',
        'xpid': '9O59DsoV-eAGH',
    }
    attempts = 0

    while True:
        user_agent = user_agents[attempts % len(user_agents)]
        headers = {"User-Agent": user_agent}

        try:
            session = tls_client.Session(
                client_identifier="chrome_110",
                random_tls_extension_order=True
            )
            response = await asyncio.to_thread(
                session.get,
                'https://www.amazon.com.br/s',
                headers=headers,
                params=params,
                allow_redirects=True
            )
            if response.status_code == 200:
                return response.text
            else:
                logging.warning(f"Status code {response.status_code} recebido. Tentativa {attempts + 1}.")
        except Exception as e:
            logging.error(f"Erro ao buscar dados (tentativa {attempts + 1}): {e}")

        attempts += 1
        if attempts >= 3:
            logging.error(f"Falha após {attempts} tentativas. Desistindo.")
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

async def compare_and_update_prices(product_id, title, old_price, new_price, url):
    conn = sqlite3.connect('amazon_all_categories.db')
    cursor = conn.cursor()
    try:
        def clean_price(price):
            if price == 'N/A' or not price:
                return None
            return float(price.replace('R$', '').replace('.', '').replace(',', '.').strip())

        old_price_float = clean_price(old_price)
        new_price_float = clean_price(new_price)
        
        discount_percentage = ((old_price_float - new_price_float) / old_price_float) * 100
        
        if new_price_float < old_price_float and discount_percentage >= 2:
            # Atualizar o preço na tabela categories
            cursor.execute('UPDATE categories SET price = ? WHERE id = ?', (new_price, id))

            # Verificar quantos preços históricos existem para este produto
            cursor.execute('SELECT COUNT(*) FROM historic_price WHERE product_id = ?', (product_id,))
            count = cursor.fetchone()[0]
            
            if count < 4:
                # Adicionar novo preço ao histórico
                cursor.execute('INSERT INTO historic_price (product_id, title, url, price, date) VALUES (?, ?, ?, ?, ?)',
                               (product_id, title, url, new_price, datetime.now()))
            else:
                # Encontrar o maior preço no histórico
                cursor.execute('SELECT id, price FROM historic_price WHERE product_id = ? ORDER BY price DESC LIMIT 1',
                               (product_id,))
                highest_price_record = cursor.fetchone()
                
                if highest_price_record:
                    highest_price_id, highest_price = highest_price_record
                    highest_price_float = clean_price(highest_price)
                    
                    if new_price_float < highest_price_float:
                        # Substituir o maior preço pelo novo preço menor
                        cursor.execute('UPDATE historic_price SET price = ?, title = ?, url = ?, date = ? WHERE id = ?',
                                       (new_price, title, url, datetime.now(), highest_price_id))
            
            await send_discord_notification(title, old_price_float, new_price_float, url, discount_percentage)
        
        conn.commit()
    except Exception as e:
        logging.error(f"Erro ao comparar e atualizar preços para o produto '{title}': {str(e)}")
    finally:
        conn.close()


# Função para salvar no banco
async def insert_product(product):
    conn = sqlite3.connect('amazon_all_categories.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, price FROM categories WHERE title = ?', (product['title'],))
        existing_product = cursor.fetchone()
        
        if existing_product is None:
            cursor.execute('''
                INSERT INTO categories (title, price, url) 
                VALUES (?, ?, ?)
            ''', (product['title'], product['price'], product['url']))
            product_id = cursor.lastrowid
            logging.info(f"Novo produto adicionado: ID {product_id} - {product['title']}")
            
            # Adicionar o primeiro preço ao histórico
            cursor.execute('INSERT INTO historic_price (product_id, price, date) VALUES (?, ?, ?)',
                           (product_id, product['price'], datetime.now()))
            
            # Enviar notificação para o Discord sobre novo produto
            await send_discord_notification(product['title'], 0, float(product['price'].replace('R$', '').replace('.', '').replace(',', '.')), product['url'], 0, new_product=True)
        else:
            product_id, old_price = existing_product
            if old_price != product['price']:
                await compare_and_update_prices(product_id, product['title'], old_price, product['price'], product['url'])
            # else:
            #     logging.info(f"Produto já existe e não foi alterado: ID {product_id} - {product['title']}")
    except Exception as e:
        logging.error(f"Erro ao inserir/atualizar produto no banco de dados: {str(e)}")
        logging.error(f"Detalhes do produto: {product}")

    conn.commit()
    conn.close()


# Função para processar uma categoria
async def process_category(semaphore, rh):
    async with semaphore:
        for page in range(1, 402):  # Vai de 1 a 401
            logging.info(f"Buscando categoria {rh}, página {page}")
            html_content = await fetch_data(page, rh)
            if html_content:
                products = extract_product_data(html_content)
                if not products:
                    logging.info(f"Nenhum produto encontrado na categoria {rh}, página {page}. Passando para a próxima categoria.")
                    break
                for product in products:
                    await insert_product(product)
                logging.info(f"Categoria {rh}, página {page} processada com sucesso!")
            else:
                logging.warning(f"Falha ao buscar dados para a categoria {rh}, página {page}. Passando para a próxima categoria.")
                break
            
            if page == 401:
                logging.info(f"Atingido o limite máximo de 401 páginas para a categoria {rh}. Pausando por 5 minutos.")
                await asyncio.sleep(300)  # Pausa de 5 minutos (300 segundos)

async def send_discord_notification(title, old_price, new_price, url, desconto_percentual, new_product=False):
    webhooks = {
        "1-20": "https://discord.com/api/webhooks/1331322843916664944/6-lXqiaxkzo8hYbTl6fD71aZkdF2Yxi8T5r_JjbdVJ_sQghNVT2tj51Of6Igg1t7geAC",
        "21-50": "https://discord.com/api/webhooks/1331322896299327509/_oM_OZRRZDIN9yZxKRYV0tSsb3zyVV3mDIM1bfpoDvxt9908IwyZfV-E9VpBR-Cjtp9k",
        "51-70": "https://discord.com/api/webhooks/1331322954428186726/vIU1ATo1GlkrsjeQrcOCMz6uyO3XZKUpeHk6Y904pZy1MLkVwE9vZcx9jceAfovANzws",
        "71-100": "https://discord.com/api/webhooks/1331323022388494457/WMlszZnhJ3xuUvx6x_ZnWs6b-_MJlmazc1xor0VWNG9ED8VU_31fMERDY8ndU_LXb7Y_",
        "novos": "https://discord.com/api/webhooks/1331322778028212294/QRguTNyM0Uiu1XBvQwrvJkIFUZ2vlYID7Y_b3D3CKiTUYVP8iB7c0ntKS3rh4mVrrsTn"
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

# Função principal
async def make_requests_hardware():
    create_database()
    semaphore = asyncio.Semaphore(1)
    
    # Crie tarefas explicitamente
    tasks = [asyncio.create_task(process_category(semaphore, rh)) for rh in rh_params]
    
    while tasks:
        completed, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in completed:
            await task
        
        if not tasks:
            logging.info("Todas as categorias foram processadas. Pausando por 5 minutos antes de reiniciar.")
            await asyncio.sleep(300)
            tasks = [asyncio.create_task(process_category(semaphore, rh)) for rh in rh_params]

if __name__ == '__main__':
    asyncio.run(make_requests_hardware())
