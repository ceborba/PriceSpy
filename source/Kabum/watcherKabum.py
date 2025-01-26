import aiohttp
import asyncio
from datetime import datetime
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calcular_desconto(preco_antigo, preco_novo):
    if preco_antigo == 0:
        return 0
    desconto = ((preco_antigo - preco_novo) / preco_antigo) * 100
    return f"{desconto:.2f}"

class KabumMonitor:
    def __init__(self):
        self.base_url = "https://servicespub.prod.api.aws.grupokabum.com.br/catalog/v2/products-by-category/"
        self.categories = ["hardware", "perifericos", "computadores"]
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
        conn = sqlite3.connect('productsKabum.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productsKabum (
                id TEXT PRIMARY KEY,
                name TEXT,
                url_key TEXT,
                promotion_name TEXT,
                price_discount REAL,
                price_promotional REAL,
                new_price REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id TEXT,
                name TEXT,
                price REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            )
        ''')
        conn.commit()
        return conn

    def atualizar_preco(self, produto_id, nome, preco_atual, link, promocao_nome=None, preco_desc=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT price_promotional, promotion_name, name FROM productsKabum WHERE id = ?", (produto_id,))
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
                    UPDATE productsKabum
                    SET price_promotional = ?, promotion_name = ?, price_discount = ?, name = ?
                    WHERE id = ?
                ''', (preco_atual, promocao_nome, preco_desc, nome, produto_id))

                cursor.execute('''
                    INSERT OR REPLACE INTO price_history (id, name, price)
                    VALUES (?, ?, ?)
                ''', (produto_id, nome, preco_atual))

                self.conn.commit()
                mudancas_str = ", ".join(mudancas)
                logging.info(f"Produto {nome} atualizado: {mudancas_str}")

                if preco_atual < preco_antigo:
                    link_produto = f"https://www.kabum.com.br/produto/{produto_id}"
                    desconto_percentual = calcular_desconto(preco_antigo, preco_atual)
                    self.enviar_webhook_discord(nome, preco_antigo, preco_atual, link_produto, promocao_nome, desconto_percentual)
            return True
        else:
            cursor.execute('''
                INSERT INTO productsKabum (id, name, url_key, promotion_name, price_discount, price_promotional)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (produto_id, nome, link, promocao_nome, preco_desc, preco_atual))

            cursor.execute('''
                INSERT INTO price_history (id, name, price)
                VALUES (?, ?, ?)
            ''', (produto_id, nome, preco_atual))

            self.conn.commit()
            logging.info(f"Novo produto adicionado: {nome} - Preço: {preco_atual:.2f}, Promoção: {promocao_nome or 'Sem promoção'}")

            link_produto = f"https://www.kabum.com.br/produto/{produto_id}"
            self.enviar_webhook_discord(nome, preco_atual, preco_atual, link_produto, promocao_nome, 0, novo_produto=True)
        return False

    def enviar_webhook_discord(self, nome_produto, preco_antigo, preco_novo, link_produto, promocao_nome, desconto_percentual, novo_produto=False):
        webhooks = {
            "1-20": "https://discord.com/api/webhooks/1328901213999071283/cQprCnbc5ghizWbq-Qd1OhKJ_FYk3DKxAk3QmjRUABbm5glptF4O_m83JYGu6UAxvTyf",
            "21-50": "https://discord.com/api/webhooks/1328902690071117886/2kUxBdZaR8KlBUtGrpxgzO_Znw0B94imH3YDkvrcnE3S_Prkh-2t8T9OHgnmA4eL_6Yd",
            "51-70": "https://discord.com/api/webhooks/1328902914177105920/oZo3QRbI7LzGSkJplzh0fqId-ZWCKDdgKuAJmI-ymjc1dMwX4Jpq_yrwS4YfFty7ud-K",
            "71-100": "https://discord.com/api/webhooks/1328902975439245404/S1i_wIw8baiyPP-LfJhw7jgjQNm5--izgAKRvRFtndxjjZTQEHgrjdlmzzqKzDJPVpuI",
            "novos": "https://discord.com/api/webhooks/1328903035040043049/_An8yyR-nRZSVr8s4Q80uQzlM34yWe4K5sZdJCgRU36ubYYgnJ1vdwGTYtoALWYRqln7"
        }

        if novo_produto:
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
        embed = DiscordEmbed(title=nome_produto, description="Alteração de preço detectada!" if not novo_produto else "Novo produto adicionado!", color='03b2f8')
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {preco_novo:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Promoção", value=promocao_nome or "Sem Promoção")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique aqui]({link_produto})")
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {nome_produto} - Novo preço: R$ {preco_novo:.2f} - Desconto: {desconto_percentual:.2f}%")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")

    async def fetch_page(self, category, page_number):
        url = f"{self.base_url}{category}"
        params = {
            "page_number": str(page_number),
            "page_size": "100",
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

    async def monitor_pages(self, start_page=1, end_page=150):
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
                            except Exception as e:
                                logging.error(f"Erro ao processar produto {produto_id}: {e}")
                    await asyncio.sleep(1)
            await asyncio.sleep(1)


async def main():
    monitor = KabumMonitor()
    try:
        await monitor.monitor_pages()
    except KeyboardInterrupt:
        logging.info("\nMonitoramento finalizado pelo usuário")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nPrograma finalizado pelo usuário")
