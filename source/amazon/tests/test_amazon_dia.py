import httpx
import asyncio
import json
import sqlite3
from datetime import datetime
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import aiohttp


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('amazon_monitor.log', 'w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Configuração da API Amazon
url = "https://data.amazon.com.br/api/marketplaces/A2Q3Y263D00KWC/promotions"
params = {
    "pageSize": 300,
    "startIndex": 1,
    "calculateRefinements": "false",
    "_enableNestedRefs": "true",
    "rankingContext": '{"pageTypeId":"deals","rankGroup":"PARENT_ASIN_RANKING"}',
    "filters": '{"includedDepartments":[],"excludedDepartments":[],"includedTags":[],"excludedTags":[],"promotionTypes":["LIGHTNING_DEAL","BEST_DEAL"],"accessTypes":[],"brandIds":[]}',
    # "refinementFilters": '[{"id":"percentOff","value":["1"]},{"id":"price","value":[]}]'
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
    "session-token": '"lu2LcmhusueL/LslAt0kisod34FHoSY4sMqzAwv6sYfOTp06dTURDCgcdcx9r1tTimaVPxn/RJ0WLRyGhv9yFMnq2q7bqMe0hxO+JuYc5R2nwtZ92lszyYAxQb02gPAW3OLY1Kc6HiMJn8Gtk+bLWdTdzu6YhRTVrl+3zipITCLd4Qtot7LEOiGsxHVZUnHz30dupt2NevMxKq45ThmnxTIEOthAKI+EBShA/TvR4UVtSsIt/ckbcWqVPhmZ5ty8+a86bKWD0X8m4arQaFVSuTsEBSkLJ24IHjXPnPWKL543CPNj8RBPCVyDX3cFHdgetf2ODcDK14L06VOgSMWDD8G+r/MYFXd+DOo/c2mZT7M="'
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
        "1-20": "https://discord.com/api/webhooks/1330720391131299912/0l8sZdDGFqDBH94u4fG2n60qgzKbTH-ipOtvhT2T-0Aw_NUFZb9sCOWTr9Zl88TcPH4O",
        "21-50": "https://discord.com/api/webhooks/1330720426313256970/HtWig9CEGG90wGhdoTg3NbEkepuBbx8-95unJJPbFUoSU4dBqsNazeRvUH3iwIF-kRSE",
        "51-70": "https://discord.com/api/webhooks/1330720474866388992/okh2v-CW_db1U3nn-Kn1vMM8O0Q2DEoaSJAIv2ZKIbki_6avoqeLXNkgmlQ1b4W-XafM",
        "71-100": "https://discord.com/api/webhooks/1330720600095850547/CrpD-7kwcTN9YnncvSCt9DP8YXCyf4vz2Cs-un5y0GQUnihN1Crb2arri3fuOu3K5Fa0",
        "novos": "https://discord.com/api/webhooks/1330756753423597589/NU4l2KLWZjtcWPz7feQmHLip7a1k5qLglIjSNPWNZeVDFXTW2TjTKEF165tPhNnN2yEc"
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
    total_loaded = 0  # Contador de produtos carregados

    while True:
        async with httpx.AsyncClient() as client:
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
                "x-amzn-encrypted-slate-token": "AnYx6YQej1nzvulhWqeaSxraz9xhVD1jajvKw+eVoxloxX6XCpaMqsIVhRJ/kOD0+vQDqBrOKWuET4O7Dw7b1e9Cd7fB2NpzQsSYasOLxxcRFaA2YoEAgTDcwFzQNNEgTuwYsfT5GKJzbFe2zgZlerNed4WqyhLGrFxwCEiSQwTFAFWvWwkslfjCeFzgbfbd0Y2i73Wg/UZvwDuhwC2nNh8lZ3N/OurfdrcIoRnpd7lxy8dMbtbO+h7INSLqdOlU3/D56Y1gXXDbcmmX8MV3krt6Ivj+BT5WvLM=",
                "x-api-csrf-token": "1@g4KI+WPNjE8a7Qi46ArYrR+ByWams6+XoqKcLwNhmM3HAAAAAQAAAABnj6iCcmF3AAAAAGfA1H5nd8xGEcC33NuKVw==@RQ2CWZ",
                "accept": 'application/vnd.com.amazon.api+json; type="promotions.search.result/v1"; expand="rankedPromotions[].product(product/v2).title(product.offer.title/v1),rankedPromotions[].product(product/v2).links(product.links/v2),rankedPromotions[].product(product/v2).buyingOptions[].dealBadge(product.deal-badge/v1),rankedPromotions[].product(product/v2).buyingOptions[].dealDetails(product.deal-details/v1),rankedPromotions[].product(product/v2).buyingOptions[].promotionsUnified(product.promotions-unified/v1),rankedPromotions[].product(product/v2).productImages(product.product-images/v2),rankedPromotions[].product(product/v2).buyingOptions[].price(product.price/v1),rankedPromotions[].product(product/v2).twisterVariations(product.twister-variations/v2)"',
                "content-type": "application/json",
                "x-cc-currency-of-preference": "BRL",
            }

            params["startIndex"] = start_index

            try:
                await client.options(url, headers=options_headers, cookies=cookies)
                response = await client.get(url, params=params, headers=get_headers, cookies=cookies)
                response.raise_for_status()  # Levanta uma exceção em caso de erro de status HTTP

                if response.status_code == 200:
                    json_data = response.json()
                    products = extract_product_data(json_data)
                    logging.info(f"Produtos encontrados: {len(products)}")

                    if products:  # Verifica se existem produtos
                        total_loaded += len(products)  # Atualiza o contador de produtos carregados
                        logging.info(f"Total de produtos carregados até agora: {total_loaded}")
                        
                        # Inserindo os produtos no banco de dados
                        for product in products:
                            await insert_product(product)
                            await update_product(product)
                            # print(json.dumps(product, indent=4, ensure_ascii=False))  # Exibe o produto no formato JSON

                        start_index += 300  # Avança o start_index quando há produtos
                    else:
                        logging.info("Nenhum produto encontrado.")
                        start_index = 0  # Reseta o start_index para 0
                        
                    # Lógica de parada inteligente, caso não haja mais produtos
                    if len(products) < params["pageSize"]:
                        logging.info(f"Todos os produtos foram carregados. Total final: {total_loaded}")
                        break
                else:
                    logging.error(f"Falha ao acessar a API da Amazon, código de status: {response.status_code}")
            except httpx.RequestError as e:
                logging.error(f"Erro de conexão: {e}")
                continue
            except httpx.HTTPStatusError as e:
                logging.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
                continue


if __name__ == "__main__":
    create_database()  # Cria o banco de dados e a tabela
    asyncio.run(make_requests())  # Executa a função assíncrona
