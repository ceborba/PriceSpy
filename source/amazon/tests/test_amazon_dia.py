import tls_client
import asyncio
import json
import sqlite3
from datetime import datetime
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import ssl

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)


sslcontext = ssl.create_default_context()
sslcontext.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256')

# Configuração da API Amazon
url = "https://data.amazon.com.br/api/marketplaces/A2Q3Y263D00KWC/promotions"
params = {
    "pageSize": 300,
    "startIndex": 1,
    "calculateRefinements": "false",
    "_enableNestedRefs": "true",
    "rankingContext": '{"pageTypeId":"deals","rankGroup":"PARENT_ASIN_RANKING"}',
    "filters": '{"includedDepartments":[],"excludedDepartments":[],"includedTags":[],"excludedTags":[],"promotionTypes":["LIGHTNING_DEAL","BEST_DEAL"],"accessTypes":[],"brandIds":[]}',
    "refinementFilters": '[{"id":"percentOff","value":["2"]},{"id":"price","value":[]}]'
}

common_headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "origin": "https://www.amazon.com.br",
    "referer": "https://www.amazon.com.br/",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
}

cookies = {
    "session-id": "132-5024224-3828564",
    "session-id-time": "2082787201l",
    "i18n-prefs": "BRL",
    "ubid-acbbr": "132-8992665-0074450",
    "session-token": '"KIypQQMtYGwha/t+d2ndhXvAp4p23+ZITVBqDIo2wx5vPNaMFrsqEN8yAa+kVrI43600Ysq89zrXWgOuyEHfemEQes91uTvU/UGs7RlW3ZKCVSkq5cmrxIWtNbs1X/fhy+VN+pDgME0zCkAY7dxgs0oh9KRkafJbArguwMOPtoF42arnH9WtefNQBdFYg0lRhka9286aDaBkBJpvJ+VTRcu0ARAIs15hUPHmzXqZrGr+jcEzneDXtHimfWM89AJ1KTp0d2nz10PwLuHx1SiebY5HsEO2WXwwnKK5e2K59bhXVywALmL5vAE3MFyDyXa9837JJwe1MfzCh7WrT6vK2qPETgsN2MqJRdjhUdeR3jI="'
}

def extract_product_data(json_data):
    products = []
    if "entity" in json_data and "rankedPromotions" in json_data["entity"]:
        for promotion in json_data["entity"]["rankedPromotions"]:
            product = promotion.get("product", {}).get("entity", {})
            
            if "asin" in product:
                asin = product["asin"]
                price_info = product.get("buyingOptions", [{}])[0].get("price", {}).get("entity", {})
                price = price_info.get("priceToPay", {}).get("moneyValueOrRange", {}).get("value", {}).get("amount", "N/A")
                currency = price_info.get("priceToPay", {}).get("moneyValueOrRange", {}).get("value", {}).get("currencyCode", "BRL")
                title = product.get("title", {}).get("entity", {}).get("displayString", "N/A")
                url =  "https://www.amazon.com.br" + product.get("links", {}).get("entity", {}).get("viewOnAmazon", {}).get("url", "N/A")
                
                products.append({
                    "asin": asin,
                    "price": price,
                    "currency": currency,
                    "title": title,
                    "url": url
                })
    return products

def create_database():
    conn = sqlite3.connect('amazon_products.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            asin TEXT PRIMARY KEY,
            title TEXT,
            price TEXT,
            currency TEXT,
            url TEXT
        )
    ''')
    
    conn.commit()
    conn.close()



async def send_discord_notification(title, old_price, new_price, url, desconto_percentual, new_product=False):
    webhooks = {
        "1-19": "https://discord.com/api/webhooks/1331322843916664944/6-lXqiaxkzo8hYbTl6fD71aZkdF2Yxi8T5r_JjbdVJ_sQghNVT2tj51Of6Igg1t7geAC",
        "20-49": "https://discord.com/api/webhooks/1331322896299327509/_oM_OZRRZDIN9yZxKRYV0tSsb3zyVV3mDIM1bfpoDvxt9908IwyZfV-E9VpBR-Cjtp9k",
        "50-69": "https://discord.com/api/webhooks/1331322954428186726/vIU1ATo1GlkrsjeQrcOCMz6uyO3XZKUpeHk6Y904pZy1MLkVwE9vZcx9jceAfovANzws",
        "70-100": "https://discord.com/api/webhooks/1331323022388494457/WMlszZnhJ3xuUvx6x_ZnWs6b-_MJlmazc1xor0VWNG9ED8VU_31fMERDY8ndU_LXb7Y_",
        "novos": "https://discord.com/api/webhooks/1331322778028212294/QRguTNyM0Uiu1XBvQwrvJkIFUZ2vlYID7Y_b3D3CKiTUYVP8iB7c0ntKS3rh4mVrrsTn"
    }

    try:
        if new_product:
            webhook_url = webhooks["novos"]
        elif 1 <= desconto_percentual <= 20:
            webhook_url = webhooks["1-19"]
        elif 20 < desconto_percentual <= 50:
            webhook_url = webhooks["20-49"]
        elif 50 < desconto_percentual < 70:
            webhook_url = webhooks["50-69"]
        elif 70 <= desconto_percentual <= 100:
            webhook_url = webhooks["70-100"]
        else:
            return

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

async def insert_product(product):
    conn = sqlite3.connect('amazon_products.db')
    cursor = conn.cursor()

    try:
        # Verifica se o produto já existe
        cursor.execute('SELECT * FROM products WHERE asin = ?', (product['asin'],))
        existing_product = cursor.fetchone()

        if existing_product is None:
            # O produto não existe, então inserimos
            cursor.execute('''
                INSERT INTO products (asin, title, price, currency, url) 
                VALUES (?, ?, ?, ?, ?)
            ''', (product['asin'], product['title'], product['price'], product['currency'], product['url']))
            
            logging.info(f"Novo produto adicionado: {product['title']}")
            
            if product['price'] != 'N/A':
                try:
                    new_price = float(product['price'])
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
            # O produto já existe, então atualizamos
            await update_product(product)
    except Exception as e:
        logging.error(f"Erro ao inserir/atualizar produto no banco de dados: {e}")

    conn.commit()
    conn.close()

async def update_product(product):
    conn = sqlite3.connect('amazon_products.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT price FROM products WHERE asin = ?
    ''', (product['asin'],))
    
    result = cursor.fetchone()
    
    if result:
        old_price = result[0]
        
        try:
            new_price = float(product['price']) if product['price'] != 'N/A' else None
            old_price_float = float(old_price) if old_price != 'N/A' else None
            
            if new_price is not None and old_price_float is not None and new_price != old_price_float:
                cursor.execute(''' 
                    UPDATE products 
                    SET price = ?, title = ?, currency = ?, url = ? 
                    WHERE asin = ?
                ''', (product['price'], product['title'], product['currency'], product['url'], product['asin']))
                
                logging.info(f"Produto atualizado: {product['title']}")
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
            logging.error(f"Preço inválido para o produto {product['asin']}: {product['price']}")

    conn.commit()
    conn.close()


async def make_requests():
    start_index = 0
    total_loaded = 0

    session = tls_client.Session(
        client_identifier="chrome_120",
        random_tls_extension_order=True
    )

    while True:
        options_headers = {
            **common_headers,
            "access-control-request-method": "GET",
            "access-control-request-headers": "accept,content-type,x-amzn-encrypted-slate-token,x-api-csrf-token,x-cc-currency-of-preference",
        }

        get_headers = {
            **common_headers,
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": "?0",
            "x-amzn-encrypted-slate-token": "AnYxs0V7xztGqWeSz910LT5TW8veetmml9D1uRHyxni3M1+HQcba46vHqCBfW92+C4nR+utvEgTm3a3LYGN9BPqy57oaW9GYvZLDKWNZFG40ei+AoUlo9uVu+lZ3ikxVUBdLcSlEHlLS2ZAcH5Tnu8Z5V8TRBEnDaiOTXznNwyInPzgmkYhmhc/yYDmeJZnGhAQT58XLCxLuvTEkzVhSfHDUab9z+mnPb/3/iSC45285IVUsVN2acGc2bq9G+/irC6uhPJ6UIbfcgwaqC4BO30rnrNRyendyfLI=",
            "x-api-csrf-token": "1@g5waicvBFAqheCqlEYm9bp3RWIQT6qW5+d1QrV8FgiP2AAAAAQAAAABnojq1cmF3AAAAAGfA1H5nd8xGEcC33NuKVw==@RQ2CWZ",
            "accept": 'application/vnd.com.amazon.api+json; type="promotions.search.result/v1"; expand="rankedPromotions[].product(product/v2).title(product.offer.title/v1),rankedPromotions[].product(product/v2).links(product.links/v2),rankedPromotions[].product(product/v2).buyingOptions[].dealBadge(product.deal-badge/v1),rankedPromotions[].product(product/v2).buyingOptions[].dealDetails(product.deal-details/v1),rankedPromotions[].product(product/v2).buyingOptions[].promotionsUnified(product.promotions-unified/v1),rankedPromotions[].product(product/v2).productImages(product.product-images/v2),rankedPromotions[].product(product/v2).buyingOptions[].price(product.price/v1),rankedPromotions[].product(product/v2).twisterVariations(product.twister-variations/v2)"',
            "content-type": "application/json",
            "x-cc-currency-of-preference": "BRL",
        }

        params["startIndex"] = start_index

        try:
            session.options(url, headers=options_headers, cookies=cookies)
            response = session.get(url, params=params, headers=get_headers, cookies=cookies)

            if response.status_code == 200:
                json_data = response.json()
                products = extract_product_data(json_data)

                if products:
                    total_loaded += len(products)
                    logging.info(f"Total de produtos carregados até agora: {total_loaded}")
                    
                    for product in products:
                        await insert_product(product)
                        await update_product(product)

                    start_index += 300
                else:
                    logging.info("Nenhum produto encontrado.")
                    start_index = 0
                    
                if len(products) < params["pageSize"]:
                    logging.info("Todos os produtos foram carregados. Reiniciando o carregamento.")
                    start_index = 0
                    total_loaded = 0
            else:
                logging.error(f"Falha ao acessar a API da Amazon, código de status: {response.status_code}")
                continue
        except Exception as e:
            logging.error(f"Erro ao fazer a requisição: {str(e)}")
            continue

        await asyncio.sleep(1)  # Pausa de 1 segundo entre as requisições


if __name__ == "__main__":
    create_database()
    asyncio.run(make_requests())