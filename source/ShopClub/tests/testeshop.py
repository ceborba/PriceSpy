import tls_client
import sqlite3
import time
import logging
from datetime import datetime
import json
from discord_webhook import DiscordWebhook, DiscordEmbed


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ShopclubWatcher:
    def __init__(self):
        self.session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        self.conn = sqlite3.connect('prices_shopclub.db')
        self.cursor = self.conn.cursor()
        self._create_table()
        self.webhooks = {
            "com-desconto": "https://discord.com/api/webhooks/1332230389015773235/sHaaOjhaNvv2_fBE0c9i4SFqTY1349q_Hi5stA8M7bmS8ND6A85fxoZ2lKkC0WoVPwc2",
            "novos": "https://discord.com/api/webhooks/1336100720981708932/cVRdMpaPj0lrIHHEpLTAviuNBnnB__POsRscvVlDXXwDEQ5MMzQe5BpJ5EMOvUj0fuzG"
        }

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                product_id TEXT,
                item_id TEXT,
                nome TEXT,
                preco REAL,
                estoque INTEGER,
                link TEXT,
                voltagem TEXT,
                atualizado_em DATETIME,
                PRIMARY KEY (product_id, item_id)
            )
        ''')
        self.conn.commit()

    def enviar_webhook_discord(self, nome_produto, preco_antigo, preco_novo, link_produto, link_carrinho, desconto_percentual, novo_produto=False):
        webhook_url = self.webhooks["novos"] if novo_produto else self.webhooks["com-desconto"]
        webhook = DiscordWebhook(url=webhook_url)
        
        embed = DiscordEmbed(
            title=nome_produto,
            description="Novo produto adicionado!" if novo_produto else "Alteração detectada!",
            color='03b2f8'
        )
        
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {preco_novo:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Loja", value="ShopClub")
        embed.add_embed_field(name="Comprar", value=f"[🛒 Adicionar ao carrinho]({link_carrinho})")
        embed.add_embed_field(name="Detalhes", value=f"[🔍 Ver produto]({link_produto})")
        
        webhook.add_embed(embed)
        response = webhook.execute()
        
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {nome_produto}")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")


    def fetch_products(self, page=0):
        params = {
            'workspace': 'master',
            'maxAge': 'short',
            'appsEtag': 'remove',
            'domain': 'store',
            'locale': 'pt-BR',
            # '__bindingId': '378597e2-4c99-4a15-b5b0-ed9a10bd1a78',
            'operationName': 'productSearchV3',
            'variables': json.dumps({
                "hideUnavailableItems": True,
                "skusFilter": "ALL_AVAILABLE",
                "simulationBehavior": "default",
                "installmentCriteria": "MAX_WITHOUT_INTEREST",
                "productOriginVtex": True,
                "map": "productClusterIds",
                "query": "1953",
                "orderBy": "OrderByScoreDESC",
                "from": page * 12,
                "to": (page + 1) * 12 - 1,
                "selectedFacets": [{"key": "productClusterIds", "value": "1953"}],
                "operator": "and",
                "fuzzy": "0",
                "searchState": None,
                "facetsBehavior": "Static",
                "categoryTreeBehavior": "default",
                "withFacets": False,
                "advertisementOptions": {
                    "showSponsored": True,
                    "sponsoredCount": 3,
                    "advertisementPlacement": "top_search",
                    "repeatSponsoredProducts": True
                }
            }),
            'extensions': '{"persistedQuery":{"version":1,"sha256Hash":"9177ba6f883473505dc99fcf2b679a6e270af6320a157f0798b92efeab98d5d3","sender":"vtex.store-resources@0.x","provider":"vtex.search-graphql@0.x"}}'
        }
        
        headers = {
            'authority': 'www.shopclub.com.br',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'accept': '*/*',
            'referer': 'https://www.shopclub.com.br/outlet',
        }
        
        try:
            response = self.session.get(
                'https://www.shopclub.com.br/_v/segment/graphql/v1',
                params=params,
                headers=headers
            )
            return response.json()
        except Exception as e:
            logging.error(f"Erro na requisição: {str(e)}")
            return None


    def parse_products(self, data):
        products = []
        try:
            for product in data['data']['productSearch']['products']:
                for item in product['items']:
                    nome_completo = item['nameComplete']
                    voltagem = next((v['values'][0] for v in item['variations'] if v['name'] == 'Voltagem'), 'N/A')
                    
                    for seller in item['sellers']:
                        offer = seller['commertialOffer']
                        products.append({
                            'product_id': product['productId'],
                            'item_id': item['itemId'],
                            'nome': nome_completo,
                            'preco': offer['Price'],
                            'estoque': offer['AvailableQuantity'],
                            'link': f"https://www.shopclub.com.br{product['link']}",
                            'voltagem': voltagem,
                            'atualizado_em': datetime.now().isoformat()
                        })
            return products
        except KeyError as e:
            logging.error(f"Erro ao parsear resposta: {str(e)}")
            return []



    def save_to_db(self, products):
        new_products = []
        price_drops = []
        restocked_products = []

        for product in products:
            self.cursor.execute('''
                SELECT preco, estoque FROM produtos 
                WHERE product_id = ? AND item_id = ?
            ''', (product['product_id'], product['item_id']))
            result = self.cursor.fetchone()

            if result is None:
                if product['estoque'] > 0:
                    new_products.append(product)
                    link_carrinho = f"https://www.shopclub.com.br/checkout/cart/add?sku={product['item_id']}&qty=1&seller=1&sc=5"
                    self.enviar_webhook_discord(
                        nome_produto=product['nome'],
                        preco_antigo=0,
                        preco_novo=product['preco'],
                        link_produto=product['link'],
                        link_carrinho=link_carrinho,
                        desconto_percentual=0,
                        novo_produto=True
                    )
            else:
                old_price, old_stock = result
                if product['preco'] != 0 and product['preco'] < old_price:
                    price_drops.append((product, old_price))
                    desconto_percentual = ((old_price - product['preco']) / old_price) * 100
                    link_carrinho = f"https://www.shopclub.com.br/checkout/cart/add?sku={product['item_id']}&qty=1&seller=1&sc=5"
                    self.enviar_webhook_discord(
                        nome_produto=product['nome'],
                        preco_antigo=old_price,
                        preco_novo=product['preco'],
                        link_produto=product['link'],
                        link_carrinho=link_carrinho,
                        desconto_percentual=desconto_percentual
                    )
                if old_stock == 0 and product['estoque'] > 0:
                    restocked_products.append(product)
                    link_carrinho = f"https://www.shopclub.com.br/checkout/cart/add?sku={product['item_id']}&qty=1&seller=1&sc=5"
                    self.enviar_webhook_discord(
                        nome_produto=product['nome'],
                        preco_antigo=old_price,
                        preco_novo=product['preco'],
                        link_produto=product['link'],
                        link_carrinho=link_carrinho,
                        desconto_percentual=0
                    )

            self.cursor.execute('''
                REPLACE INTO produtos 
                (product_id, item_id, nome, preco, estoque, link, voltagem, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['product_id'],
                product['item_id'],
                product['nome'],
                product['preco'],
                product['estoque'],
                product['link'],
                product['voltagem'],
                product['atualizado_em']
            ))
            self.conn.commit()

        if new_products:
            logging.info(f"Novos produtos com estoque cadastrados: {len(new_products)}")
            for product in new_products:
                logging.info(f"Novo produto: {product['nome']} - R${product['preco']} - Estoque: {product['estoque']}")

        if price_drops:
            logging.info(f"Produtos com queda de preço: {len(price_drops)}")
            for product, old_price in price_drops:
                logging.info(f"Queda de preço: {product['nome']} - De R${old_price} para R${product['preco']}")

        if restocked_products:
            logging.info(f"Produtos reabastecidos: {len(restocked_products)}")
            for product in restocked_products:
                logging.info(f"Reabastecido: {product['nome']} - Novo estoque: {product['estoque']}")


    def run(self, interval=1, max_pages=10):
        while True:
            try:
                page = 0
                total_products = 0
                while page < max_pages:
                    data = self.fetch_products(page)
                    if data and 'data' in data and 'productSearch' in data['data']:
                        products = self.parse_products(data)
                        if not products:
                            break
                        self.save_to_db(products)
                        total_products += len(products)
                        page += 1
                        time.sleep(0.1)
                    else:
                        break
                
                logging.info(f"Total de produtos processados: {total_products}")
                if total_products == 0:
                    logging.warning("Nenhum produto encontrado. Verifique a consulta ou os parâmetros.")
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                logging.error(f"Erro geral: {str(e)}")
                time.sleep(0.1)

if __name__ == "__main__":
    monitor = ShopclubWatcher()
    monitor.run(interval=1, max_pages=30)  # Executar a cada 10 minutos, máximo de 10 páginas