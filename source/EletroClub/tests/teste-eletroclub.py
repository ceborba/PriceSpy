import aiohttp
import asyncio
import json
from datetime import datetime
import sqlite3
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import base64
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calcular_desconto(preco_antigo, preco_novo):
    if preco_antigo == 0:
        return 0
    preco_antigo = float(preco_antigo) if isinstance(preco_antigo, str) else preco_antigo
    preco_novo = float(preco_novo) if isinstance(preco_novo, str) else preco_novo
    desconto = ((preco_antigo - preco_novo) / preco_antigo) * 100
    return f"{desconto:.2f}"

def decode_and_modify_variables(encoded_variables, start, end):
    decoded = json.loads(base64.b64decode(encoded_variables).decode('utf-8'))
    decoded['from'] = start
    decoded['to'] = end
    return base64.b64encode(json.dumps(decoded).encode('utf-8')).decode('utf-8')

class EletroclubMonitor:
    def __init__(self):
        self.base_url = "https://www.eletroclub.com.br/_v/segment/graphql/v1"
        self.variables = [
                # "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJBTEwiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOmZhbHNlLCJtYXAiOiJjIiwicXVlcnkiOiJhY2Vzc29yaW9zIiwib3JkZXJCeSI6Ik9yZGVyQnlCZXN0RGlzY291bnRERVNDIiwiZnJvbSI6MCwidG8iOjExLCJzZWxlY3RlZEZhY2V0cyI6W3sia2V5IjoiYyIsInZhbHVlIjoiYWNlc3NvcmlvcyJ9XSwiZmFjZXRzQmVoYXZpb3IiOiJTdGF0aWMiLCJjYXRlZ29yeVRyZWVCZWhhdmlvciI6ImRlZmF1bHQiLCJ3aXRoRmFjZXRzIjpmYWxzZSwiYWR2ZXJ0aXNlbWVudE9wdGlvbnMiOnsic2hvd1Nwb25zb3JlZCI6dHJ1ZSwic3BvbnNvcmVkQ291bnQiOjMsImFkdmVydGlzZW1lbnRQbGFjZW1lbnQiOiJ0b3Bfc2VhcmNoIiwicmVwZWF0U3BvbnNvcmVkUHJvZHVjdHMiOnRydWV9fQ==",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJBTEwiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOmZhbHNlLCJtYXAiOiJjIiwicXVlcnkiOiJvdXRsZXQiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjAsInRvIjoxMSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6Im91dGxldCJ9XSwiZmFjZXRzQmVoYXZpb3IiOiJTdGF0aWMiLCJjYXRlZ29yeVRyZWVCZWhhdmlvciI6ImRlZmF1bHQiLCJ3aXRoRmFjZXRzIjpmYWxzZSwiYWR2ZXJ0aXNlbWVudE9wdGlvbnMiOnsic2hvd1Nwb25zb3JlZCI6dHJ1ZSwic3BvbnNvcmVkQ291bnQiOjMsImFkdmVydGlzZW1lbnRQbGFjZW1lbnQiOiJ0b3Bfc2VhcmNoIiwicmVwZWF0U3BvbnNvcmVkUHJvZHVjdHMiOnRydWV9fQ=="
        ]       
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "referer": "https://www.eletroclub.com.br/outlet",
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        }
        self.items_per_page = 50
        self.conn = self.create_db()
            
    def create_db(self):
        conn = sqlite3.connect('productsEletroclub.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productsEletroclub (
                id TEXT PRIMARY KEY,
                name TEXT,
                url_key TEXT,
                price_discount REAL,
                price_promotional REAL,
                new_price REAL,
                condition TEXT,
                garantia TEXT,
                em_estoque BOOLEAN DEFAULT FALSE  -- Nova coluna
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
    

    def atualizar_preco(self, item_id, nome, preco_atual, link, preco_desc=None, condition=None, garantia=None, quantidade_disponivel=0):
        preco_atual = preco_atual or 0
        preco_desc = preco_desc or 0

        cursor = self.conn.cursor()
        em_estoque = quantidade_disponivel > 0

        cursor.execute("SELECT price_promotional, name, em_estoque FROM productsEletroclub WHERE id = ?", (item_id,))
        result = cursor.fetchone()

        if result:
            preco_antigo, nome_antigo, estoque_antigo = result
            preco_antigo = preco_antigo or 0
            mudancas = []

            if estoque_antigo != em_estoque:
                mudancas.append(f"Estoque: {'Disponível' if em_estoque else 'Esgotado'}")
                # Só envia webhook se o produto estiver em estoque
                if not estoque_antigo and em_estoque:
                    self.enviar_webhook_discord(nome, preco_atual, preco_atual, 
                        f"https://www.eletroclub.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=5", 
                        f"https://www.eletroclub.com.br{link}", 
                        0, webhook_key="novos")
            
            if preco_atual != preco_antigo:
                mudancas.append(f"Preço: {float(preco_antigo):.2f} -> {float(preco_atual):.2f}")
                # Só envia webhook de alteração de preço se tiver estoque
                if em_estoque and preco_atual != 0:
                    link_produto = f"https://www.eletroclub.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=5"
                    link_produto2 = f"https://www.eletroclub.com.br{link}"
                    desconto_percentual = calcular_desconto(preco_antigo, preco_atual)
                    self.enviar_webhook_discord(nome, preco_antigo, preco_atual, link_produto, link_produto2, desconto_percentual)

            if nome != nome_antigo:
                mudancas.append(f"Nome: '{nome_antigo}' -> '{nome}'")

            if mudancas:
                cursor.execute('''
                    UPDATE productsEletroclub
                    SET price_promotional = ?, price_discount = ?, name = ?, condition = ?, garantia = ?, em_estoque = ?
                    WHERE id = ?
                ''', (preco_atual, preco_desc, nome, condition, garantia, em_estoque, item_id))

                cursor.execute('''
                    INSERT OR REPLACE INTO price_history (id, name, price)
                    VALUES (?, ?, ?)
                ''', (item_id, nome, preco_atual))

                self.conn.commit()
                logging.info(f"Produto {nome} atualizado: {', '.join(mudancas)}")

        else:
            cursor.execute('''
                INSERT INTO productsEletroclub (id, name, url_key, price_discount, price_promotional, condition, garantia, em_estoque)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item_id, nome, link, preco_desc, preco_atual, condition, garantia, em_estoque))

            cursor.execute('''
                INSERT INTO price_history (id, name, price)
                VALUES (?, ?, ?)
            ''', (item_id, nome, preco_atual))

            self.conn.commit()
            logging.info(f"Novo produto adicionado: {nome} - Preço: {preco_atual:.2f}")

            # Só envia webhook de novo produto se tiver estoque
            if em_estoque and preco_atual != 0:
                link_produto = f"https://www.eletroclub.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=5"
                link_produto2 = f"https://www.eletroclub.com.br{link}"
                self.enviar_webhook_discord(nome, preco_atual, preco_atual, link_produto, link_produto2, 0, webhook_key="novos")
        
        return True if result else False


    def enviar_webhook_discord(self, nome_produto, preco_antigo, preco_novo, link_produto, link_produto2, desconto_percentual, webhook_key="com-desconto"):
        webhooks = {
            "com-desconto": "https://discord.com/api/webhooks/1332230389015773235/sHaaOjhaNvv2_fBE0c9i4SFqTY1349q_Hi5stA8M7bmS8ND6A85fxoZ2lKkC0WoVPwc2",
            "novos": "https://discord.com/api/webhooks/1332934129481814108/6WJFC0p7DsCamzbqUrB-P87sGTf3-xChr8uJJtKmWE4Y1v0Pi4LZil8GZy7tGF4XU73M"
        }

        webhook_url = webhooks.get(webhook_key, webhooks["com-desconto"])
        is_novo_produto = webhook_key == "novos"

        webhook = DiscordWebhook(url=webhook_url)
        
        embed = DiscordEmbed(
            title=f"{'🆕 ' if is_novo_produto else '💰 '}{nome_produto}",
            description="Produto disponível em estoque!" if is_novo_produto else f"Desconto de {desconto_percentual:.2f}%",
            color='00ff00' if is_novo_produto else '03b2f8'
        )
        
        if not is_novo_produto:
            embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        
        embed.add_embed_field(name="Preço Atual", value=f"R$ {preco_novo:.2f}")
        
        if not is_novo_produto:
            embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        
        embed.add_embed_field(name="Disponibilidade", value="✅ Em estoque" if is_novo_produto else "🛒 Comprar agora")
        embed.add_embed_field(name="Link Direto", value=f"[Adicionar ao carrinho]({link_produto})")
        embed.add_embed_field(name="Página do Produto", value=f"[Ver detalhes]({link_produto2})")
        
        webhook.add_embed(embed)
        response = webhook.execute()
        
        if response.status_code == 200:
            tipo = "novo produto" if is_novo_produto else "desconto"
            logging.info(f"Notificação de {tipo} enviada: {nome_produto}")
        else:
            logging.error(f"Erro no webhook ({webhook_key}): {response.status_code}")


    async def fetch_page(self, variables):
        url = f"{self.base_url}"
        params = {
            "workspace": "master",
            "maxAge": "short",
            "appsEtag": "remove",
            "domain": "store",
            "locale": "pt-BR",
            "__bindingId": "378597e2-4c99-4a15-b5b0-ed9a10bd1a78",
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
                    print(f"EletroClub - Status Code: {response.status}")

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

    async def monitor_pages(self):
        semaphore = asyncio.Semaphore(8)
        start_time = time.perf_counter()

        async def process_page(encoded_var, page):
            nonlocal total_products
            async with semaphore:
                start = page * self.items_per_page
                end = start + self.items_per_page - 1
                modified_var = decode_and_modify_variables(encoded_var, start, end)

                data = await self.fetch_page(modified_var)
                if data and 'data' in data and 'productSearch' in data['data'] and 'products' in data['data']['productSearch']:
                    products = data['data']['productSearch']['products']
                    for product in products:
                        try:
                            # produto_id = product['productId']
                            nome_base = product['productName']
                            link = product['link']
                            
                            # Extrair especificações
                            specs = {}
                            for group in product['specificationGroups']:
                                if group['name'] == 'allSpecifications':
                                    for spec in group['specifications']:
                                        specs[spec['name']] = spec['values'][0] if spec['values'] else None
                            
                            condition = specs.get('Estado', None)
                            garantia = specs.get('Garantia (Dias)', None)
                            
                            # Processar cada item (variação) do produto
                            for item in product['items']:
                                item_id = item['itemId']
                                # print(item_id)
                                nome_completo = item['nameComplete']
                                ean = item['ean']
                                
                                # Extrair preços e quantidade disponível
                            for seller in item['sellers']:
                                offer = seller['commertialOffer']
                                preco_base = offer['Price']
                                preco_list = offer['ListPrice']
                                available_quantity = offer.get('AvailableQuantity', 0)  # Pega quantidade disponível
                                
                                preco_desc = preco_list - preco_base if preco_list > preco_base else 0
                                
                                self.atualizar_preco(
                                    f"{item_id}",
                                    nome_completo,
                                    preco_base,
                                    link,
                                    preco_desc=preco_desc,
                                    condition=condition,
                                    garantia=garantia,
                                    quantidade_disponivel=available_quantity  # Passa a quantidade disponível
                                )
                                    
                                    # Se você quiser processar apenas o primeiro seller, descomente a linha abaixo
                                    # break
                            
                        except Exception as e:
                            logging.error(f"Erro ao processar produto {item_id}: {e}")
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.5)
            print("Monitoramento finalizado: Iniciando novamente em 1 segundo")

        while True:
            total_products = 0  # Reseta o contador antes do novo ciclo
            start_time = time.perf_counter()  # Reinicia o cronômetro

            for encoded_var in self.variables:
                page = 0
                while True:
                    tasks = [process_page(encoded_var, page + i) for i in range(50)]
                    results = await asyncio.gather(*tasks)

                    if not any(results):  # Interrompe se nenhuma página retornar produtos
                        break

                    page += 5
                    await asyncio.sleep(0.001)

            elapsed_time = time.perf_counter() - start_time  # Tempo total de execução
            print(f"Monitoramento finalizado: {total_products} produtos coletados em {elapsed_time:.2f} segundos.")

            await asyncio.sleep(0.001)  # Espera antes de reiniciar



async def monitor_eletroclub():
    monitor = EletroclubMonitor()
    try:
        await monitor.monitor_pages()
    except KeyboardInterrupt:
        logging.info("\nMonitoramento finalizado pelo usuário")

if __name__ == "__main__":
    try:
        asyncio.run(monitor_eletroclub())
    except KeyboardInterrupt:
        logging.info("\nPrograma finalizado pelo usuário")

