import aiohttp
import asyncio
from datetime import datetime
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

WEBHOOK_URL = "https://discord.com/api/webhooks/1337607448843780267/UCCyxom7eglKd12GBiTXn90gfAKDm9hPIATUGRuMXhRIhAJSoe9B-cddshi0Bzn-btL4"  # Substitua pela sua URL

def calcular_desconto(preco_antigo, preco_novo):
    if preco_antigo == 0:
        return 0
    desconto = ((preco_antigo - preco_novo) / preco_antigo) * 100
    return f"{desconto:.2f}"

class KabumMonitorOP:
    def __init__(self):
        self.base_url = "https://servicespub.prod.api.aws.grupokabum.com.br/catalog/v2/products-by-category/"
        self.openbox_url = "https://servicespub.prod.api.aws.grupokabum.com.br/descricao/v1/openbox/"
        self.categories = ["hardware", "perifericos", "computadores", "gamer", "celular-smartphone", "tv", "espaco-gamer", "tablets-ipads-e-e-readers", "escritorio", "eletrodomesticos", "ar-e-ventilacao"]
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "pt-PT;q=0.9,en-US;q=0.8,en;q=0.7",
            "Client-id": "",
            "Origin": "https://www.kabum.com.br",
            "Referer": "https://www.kabum.com.br/",
            "Priority": "u=1,i",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A_Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Session": "3025e53c6b1c331fc3a6242aa570b002",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        self.conn = self.create_db()

    def create_db(self):
        conn = sqlite3.connect('teste.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teste (
                id TEXT PRIMARY KEY,
                name TEXT,
                url_key TEXT,
                promotion_name TEXT,
                price_discount REAL,
                price_promotional REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id TEXT,
                name TEXT,
                price REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, date)
            )
        ''')
        # New table for Open Box products
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS openbox_products (
                codigo INTEGER,
                nome TEXT,
                mercadoria_codigo INTEGER,
                condicao TEXT,
                garantia_info TEXT,
                observacao TEXT,
                preco REAL,
                preco_parcelado REAL,
                parcelas INTEGER,
                PRIMARY KEY (mercadoria_codigo)
            )
        ''')
        conn.commit()
        return conn

    def atualizar_preco(self, produto_id, nome, preco_atual, link, promocao_nome=None, preco_desc=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT price_promotional, promotion_name, name FROM teste WHERE id = ?", (produto_id,))
        result = cursor.fetchone()

        if result:
            preco_antigo, promocao_antiga, nome_antigo = result
            mudancas = []
            if preco_atual != preco_antigo:
                mudancas.append(f"Preço: {preco_antigo:.2f} -> {preco_atual:.2f}")
            if promocao_nome != promocao_antiga:
                mudancas.append(f"Promoção: '{promocao_antiga or 'Sem promoção'}' -> '{promocao_nome or 'Sem promoção'}'")
            if nome != nome_antigo:
                mudancas.append(f"Nome: '{nome_antigo}' -> '{nome}'")

            if mudancas:
                cursor.execute('''
                    UPDATE teste
                    SET price_promotional = ?, promotion_name = ?, price_discount = ?, name = ?
                    WHERE id = ?
                ''', (preco_atual, promocao_nome, preco_desc, nome, produto_id))

                cursor.execute('''
                    INSERT INTO price_history (id, name, price, date)
                    VALUES (?, ?, ?, ?)
                ''', (produto_id, nome, preco_atual, datetime.now()))

                self.conn.commit()
                mudancas_str = ", ".join(mudancas)
                logging.info(f"Produto {nome} atualizado: {mudancas_str}")

                if preco_atual < preco_antigo:
                    link_produto = f"https://www.kabum.com.br/produto/{produto_id}"
                    desconto_percentual = calcular_desconto(preco_antigo, preco_atual)
                    asyncio.create_task(self.send_discord_webhook(nome, preco_atual, link_produto)) # Envia o webhook aqui se houver alteração de preço
                return True
        else:
            cursor.execute('''
                INSERT INTO teste (id, name, url_key, promotion_name, price_discount, price_promotional)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (produto_id, nome, link, promocao_nome, preco_desc, preco_atual))

            cursor.execute('''
                INSERT INTO price_history (id, name, price, date)
                VALUES (?, ?, ?, ?)
            ''', (produto_id, nome, preco_atual, datetime.now()))

            self.conn.commit()
            logging.info(f"Novo produto adicionado: {nome} - Preço: {preco_atual:.2f}, Promoção: {promocao_nome or 'Sem promoção'}")

            link_produto = f"https://www.kabum.com.br/produto/{produto_id}"
            asyncio.create_task(self.send_discord_webhook(nome, preco_atual, link_produto)) #Envia o webhook aqui se for um novo produto
        return False

    async def fetch_page(self, category, page_number):
        url = f"{self.base_url}{category}"
        params = {
            "page_number": str(page_number),
            "page_size": "100",
            "facet_filters": "eyJoYXNfb3Blbl9ib3giOlsidHJ1ZSJdfQ==",
            "sort": "most_searched",
            "is_prime": "false",
            "payload_data": "products_category_filters",
            "include": "gift"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
                    logging.error(f"Erro na requisição: Status {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Erro na requisição: {e}")
            return None

    async def fetch_openbox_data(self, product_id):
        url = f"{self.openbox_url}{product_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        # The API returns a list of open box products
                        return await response.json(content_type=None)
                    else:
                        logging.error(f"Erro ao buscar openbox data para o produto {product_id}: Status {response.status}")
                        return None
        except Exception as e:
            logging.error(f"Erro ao buscar openbox data para o produto {product_id}: {e}")
            return None

    def store_openbox_data(self, data):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO openbox_products (codigo, nome, mercadoria_codigo, condicao, garantia_info, observacao, preco, preco_parcelado, parcelas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['codigo'], data['nome'], data['mercadoria_codigo'], data['condicao'],
                data['garantia_info'], data['observacao'], data['preco'], data['preco_parcelado'], data['parcelas']
            ))
            self.conn.commit()
            logging.info(f"Dados Open Box do produto {data['nome']} (Mercadoria Código: {data['mercadoria_codigo']}) armazenados.")
            return True #retorna true se o produto for inserido
        except sqlite3.IntegrityError:
            # logging.warning(f"Produto Open Box com código {data['codigo']} já existe no banco de dados.")
            return False #retorna false se o produto já existir
        except Exception as e:
            logging.error(f"Erro ao inserir dados Open Box no banco de dados: {e}")
            return False

    async def send_discord_webhook(self, nome, preco, link, observacao=None, garantia=None):
        webhook = DiscordWebhook(url=WEBHOOK_URL, username="Kabum Monitor") # Create embed
        embed = DiscordEmbed(title=nome, description=f"Novo produto adicionado!", color='03b2f8')
        embed.add_embed_field(name="Preço", value=f"R$ {preco:.2f}")
        embed.add_embed_field(name="Link", value=link)
        if observacao:
            embed.add_embed_field(name="Observação", value=observacao, inline=False)
        if garantia:
            embed.add_embed_field(name="Garantia", value=garantia, inline=False)
        embed.set_timestamp()

        # Add embed to webhook
        webhook.add_embed(embed)

        try:
            response = webhook.execute()  # Execute the webhook
            if response.status_code == 200:
                logging.info(f"Webhook enviado com sucesso para o produto: {nome}")
            else:
                logging.error(f"Erro ao enviar webhook: Status Code {response.status_code}, Response: {response.text}")
        except Exception as e:
            logging.error(f"Erro ao enviar webhook: {e}")

    async def monitor_pages(self, start_page=1, end_page=11):
        while True:
            for category in self.categories:
                for page_number in range(start_page, end_page + 1):
                    logging.info(f"Consultando {category} - página {page_number}...")
                    produtos = await self.fetch_page(category, page_number)
                    if produtos and 'data' in produtos and produtos['data']:
                        for produto in produtos['data']:
                            try:
                                attr = produto['attributes']
                                produto_id = produto['id']
                                preco_base = float(attr.get('price', 0))
                                preco_final = preco_base
                                promocao_nome = None
                                preco_desc = None
                                if 'offer' in attr and attr['offer']:
                                    preco_final = float(attr['offer'].get('price_with_discount', preco_base))
                                    promocao_nome = attr['offer'].get('name', "Desconto")
                                    preco_desc = attr['offer'].get('discount_percentage', 0)
                                elif 'price_with_discount' in attr and attr['price_with_discount']:
                                    preco_final = float(attr['price_with_discount'])
                                    preco_desc = attr.get('discount_percentage', 0)
                                self.atualizar_preco(
                                    produto_id, attr['title'], preco_final, produto['links']['self'],
                                    promocao_nome, preco_desc
                                )

                                # Fetch and store Open Box data
                                openbox_data = await self.fetch_openbox_data(produto_id)
                                # Check if openbox_data is a list and iterate over it
                                if isinstance(openbox_data, list):
                                    for item in openbox_data:
                                        if self.store_openbox_data(item): #verifica se o produto é novo antes de enviar o webhook
                                            await self.send_discord_webhook(
                                                item['nome'], item['preco'], f"[Clique Aqui](https://www.kabum.com.br/produto/{produto_id})",
                                                item['observacao'], item['garantia_info']
                                            )
                                elif openbox_data:
                                    if self.store_openbox_data(openbox_data): #verifica se o produto é novo antes de enviar o webhook
                                        await self.send_discord_webhook(
                                            openbox_data['nome'], openbox_data['preco'], f"[Clique Aqui](https://www.kabum.com.br/produto/{produto_id})",
                                            openbox_data['observacao'], openbox_data['garantia_info']
                                        )

                            except Exception as e:
                                logging.error(f"Erro ao processar produto {produto_id}: {e}")
                    await asyncio.sleep(0.1)
            await asyncio.sleep(0.1)


async def monitor_open_box():
    monitor = KabumMonitorOP()
    try:
        await monitor.monitor_pages()
    except KeyboardInterrupt:
        logging.info("\nMonitoramento finalizado pelo usuário")

if __name__ == "__main__":
    try:
        asyncio.run(monitor_open_box())
    except KeyboardInterrupt:
        logging.info("\nPrograma finalizado pelo usuário")
