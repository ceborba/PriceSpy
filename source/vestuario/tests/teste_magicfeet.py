import aiohttp
import asyncio
import json
from datetime import datetime
import sqlite3
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def decode_and_modify_variables(encoded_variables, start, end):
    decoded = json.loads(base64.b64decode(encoded_variables).decode('utf-8'))
    decoded['from'] = start
    decoded['to'] = end
    return base64.b64encode(json.dumps(decoded).encode('utf-8')).decode('utf-8')

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('magicfeet_products.db')
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                produto_id TEXT,
                nome TEXT,
                link TEXT,
                list_price_high REAL,
                selling_price_low REAL,
                item_id TEXT,
                nome_completo TEXT,
                ean TEXT,
                tamanho TEXT,
                PRIMARY KEY (produto_id, item_id)
            )
        ''')
        self.conn.commit()

    def insert_product(self, product_data):
        self.cursor.execute('''
            INSERT OR REPLACE INTO products
            (produto_id, nome, link, list_price_high, selling_price_low, item_id, nome_completo, ean, tamanho)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_data['produto_id'],
            product_data['nome'],
            product_data['link'],
            product_data['list_price_high'],
            product_data['selling_price_low'],
            product_data['item_id'],
            product_data['nome_completo'],
            product_data['ean'],
            product_data['tamanho']
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()

class MagicFeetMonitor:
    def __init__(self):
        self.base_url = "https://www.magicfeet.com.br/_v/segment/graphql/v1"
        self.variables = [
            "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6dHJ1ZSwic2t1c0ZpbHRlciI6IkFMTF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOmZhbHNlLCJtYXAiOiJzcGVjaWZpY2F0aW9uRmlsdGVyXzExIiwicXVlcnkiOiJvdXRsZXQiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjAsInRvIjoyMywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6InNwZWNpZmljYXRpb25GaWx0ZXJfMTEiLCJ2YWx1ZSI6Im91dGxldCJ9XSwiZmFjZXRzQmVoYXZpb3IiOiJTdGF0aWMiLCJ3aXRoRmFjZXRzIjpmYWxzZSwiYWR2ZXJ0aXNlbWVudE9wdGlvbnMiOnsic2hvd1Nwb25zb3JlZCI6dHJ1ZSwic3BvbnNvcmVkQ291bnQiOjMsImFkdmVydGlzZW1lbnRQbGFjZW1lbnQiOiJ0b3Bfc2VhcmNoIiwicmVwZWF0U3BvbnNvcmVkUHJvZHVjdHMiOnRydWV9fQ=="
        ]
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "referer": "https://www.magicfeet.com.br/outlet",
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        }
        self.items_per_page = 50
        self.db_manager = DatabaseManager()
        self.webhooks = {
            "30-50": "https://discord.com/api/webhooks/1334728482625687624/v1Xj1ocmnNEAi-zzvXbL2Cmz1xh_MEyd6iErCwzxYCyRckMwKaiS15cKFR4u5ZDR99pK",
            "50-70": "https://discord.com/api/webhooks/1334728553740374046/T71p5GwAgVLxLkbQT2VxZ5Sin4lWZt95-I5lo0ESqUJOuqYvUNTt3wsnhZqtykutZWKg",
            "70-100": "https://discord.com/api/webhooks/1334728592457732219/7BzmRCDI0L_LwL8McXpaEp_0pAKmPKWCRRXLZ56mfyhvT0E8JYFvdv_Dp8HIYV9pPQyt"
        }

    async def fetch_page(self, variables):
        url = f"{self.base_url}"
        params = {
            "workspace": "master",
            "maxAge": "short",
            "appsEtag": "remove",
            "domain": "store",
            "locale": "pt-BR",
            "operationName": "productSearchV3",
            "variables": "{}",
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9177ba6f883473505dc99fcf2b679a6e270af6320a157f0798b92efeab98d5d3",
                    "sender": "vtex.store-resources@0.x",
                    "provider": "vtex.search-graphql@0.x"
                },
                "variables": variables
            })
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    print(f"MagicFeet - Status Code: {response.status}")

                    try:
                        if response.status == 200:
                            return await response.json(content_type=None)
                        elif response.status == 500:
                            logging.error(f"Erro 500 na requisição. URL: {response.url}, Método: {response.method}")
                        else:
                            logging.error(f"Erro na requisição: Status {response.status}")
                        return None
                    except Exception as e:
                        logging.error(f"Erro na requisição: {e}")
                        return None
        except Exception as e:
            print(f"Erro na conexão: {e}")

    def enviar_webhook_discord(self, nome_produto, preco_antigo, preco_novo, link_produto, link2, desconto_percentual, novo_produto=False):
        if desconto_percentual < 30:
            return  # Não envia o webhook se o desconto for menor que 30%

        if 30 <= desconto_percentual <= 50:
            webhook_url = self.webhooks["30-50"]
        elif 50 < desconto_percentual <= 70:
            webhook_url = self.webhooks["50-70"]
        elif 70 < desconto_percentual <= 100:
            webhook_url = self.webhooks["70-100"]
        else:
            print("Desconto não está nas faixas mencionadas")
            return

        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(title=nome_produto, description="Alteração de preço detectada!" if not novo_produto else "Novo produto adicionado!", color='03b2f8')
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {preco_novo:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Loja", value=f"MagicFeet")
        embed.add_embed_field(name="Comprar", value=f"[Clique para adicionar no carrinho]({link2})")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique para ir ao produto]({link_produto})")
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {nome_produto} - Novo preço: R$ {preco_novo:.2f} - Desconto: {desconto_percentual:.2f}%")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")

    async def monitor_pages(self):
        while True:
            for encoded_variable in self.variables:
                page = 0
                while True:
                    start = page * self.items_per_page
                    end = start + self.items_per_page - 1
                    modified_variable = decode_and_modify_variables(encoded_variable, start, end)
                    
                    data = await self.fetch_page(modified_variable)
                    if data and 'data' in data and 'productSearch' in data['data'] and 'products' in data['data']['productSearch']:
                        products = data['data']['productSearch']['products']
                        if not products:
                            break
                        
                        for product in products:
                            try:
                                produto_id = product['productId']
                                nome = product['productName']
                                link = f"https://www.magicfeet.com.br{product['link']}"
                                
                                list_price_high = product['priceRange']['listPrice']['highPrice']
                                selling_price_low = product['priceRange']['sellingPrice']['lowPrice']
                                
                                for item in product['items']:
                                    item_id = item['itemId']
                                    nome_completo = item['nameComplete']
                                    ean = item['ean']
                                    
                                    tamanho = nome_completo.split()[-1]
                                    
                                    desconto_percentual = ((list_price_high - selling_price_low) / list_price_high) * 100
                                    
                                    self.db_manager.cursor.execute("SELECT * FROM products WHERE produto_id = ? AND item_id = ?", (produto_id, item_id))
                                    existing_product = self.db_manager.cursor.fetchone()
                                    
                                    if existing_product:
                                        old_selling_price = existing_product[4]
                                        if selling_price_low != old_selling_price:
                                            desconto_percentual = ((old_selling_price - selling_price_low) / old_selling_price) * 100
                                            if desconto_percentual >= 30:
                                                link2 = f"https://www.magicfeet.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=1"
                                                self.enviar_webhook_discord(nome_completo, old_selling_price, selling_price_low, link, link2, desconto_percentual)
                                    else:
                                        desconto_percentual = ((list_price_high - selling_price_low) / list_price_high) * 100
                                        if desconto_percentual >= 30:
                                            link2 = f"https://www.magicfeet.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=1"
                                            self.enviar_webhook_discord(nome_completo, list_price_high, selling_price_low, link, link2, desconto_percentual, novo_produto=True)

                                    
                                    product_data = {
                                        'produto_id': produto_id,
                                        'nome': nome,
                                        'link': link,
                                        'list_price_high': list_price_high,
                                        'selling_price_low': selling_price_low,
                                        'item_id': item_id,
                                        'nome_completo': nome_completo,
                                        'ean': ean,
                                        'tamanho': tamanho
                                    }
                                    self.db_manager.insert_product(product_data)
                                    
                                    # print(f"Produto: {nome_completo}")
                                    # print(f"Link: {link}")
                                    # print(f"Preço de lista mais alto: {list_price_high}")
                                    # print(f"Preço de venda mais baixo: {selling_price_low}")
                                    # print(f"Desconto: {desconto_percentual:.2f}%")
                                    # print(f"Tamanho: {tamanho}")
                                    # print("---")
                                
                            except Exception as e:
                                logging.error(f"Erro ao processar produto: {e}")
                    
                    page += 1
                    await asyncio.sleep(0.5)
                
            await asyncio.sleep(0.5)
            print("Monitoramento finalizado: Iniciando novamente em 1 segundo")

async def monitor_magicfeet():
    monitor = MagicFeetMonitor()
    try:
        await monitor.monitor_pages()
    except KeyboardInterrupt:
        logging.info("\nMonitoramento finalizado pelo usuário")
    finally:
        monitor.db_manager.close()

if __name__ == "__main__":
    try:
        asyncio.run(monitor_magicfeet())
    except KeyboardInterrupt:
        logging.info("\nPrograma finalizado pelo usuário")
