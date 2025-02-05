import asyncio
import tls_client
import logging
import sqlite3
from datetime import datetime
import time
from discord_webhook import DiscordWebhook, DiscordEmbed
import json


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().addHandler(logging.StreamHandler())

# Conectar ao banco de dados SQLite
def connect_db():
    conn = sqlite3.connect('pontofrio.db')
    return conn

# Criar a tabela no banco de dados
def create_table():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    sku TEXT,
                    preco REAL)''')
    conn.commit()
    conn.close()

# Adicione esta função para enviar notificações para o Discord
async def send_discord_notification(product, old_price, new_price, is_new_product):
    webhooks = {
        "1-100": "https://discord.com/api/webhooks/1334653358933413909/rbqtqXQ-3UyA_o07Qtj0Xg0gutjYFSjjX8VojILIQmdYTBtLS3NKumjtVLbkAGo2IMtl",
        "novos": "https://discord.com/api/webhooks/1334659073206915293/PIsIgkMzbBUbNW3KCudznhCnWdKq23qn8R4BSKnVXh8nm5Rnvleamfb2cBTrZsIjKy3O"
    }

    try:
        if is_new_product:
            webhook_url = webhooks["novos"]
            desconto_percentual = 0
        else:
            desconto_percentual = ((old_price - new_price) / old_price) * 100
            if 1 <= desconto_percentual <= 99:
                webhook_url = webhooks["1-100"]
            else:
                return  # Não enviar notificação se não se encaixar em nenhuma categoria

        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(
            title=product['name'],
            description="Alteração de preço detectada!" if not is_new_product else "Novo produto adicionado!",
            color='03b2f8'
        )
        
        if not is_new_product:
            embed.add_embed_field(name="Preço Antigo", value=f"R$ {old_price:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {new_price:.2f}")
        
        if not is_new_product:
            embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        
        embed.add_embed_field(name="Loja", value="PontoFrio")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique aqui]({product['url']})")
        
        webhook.add_embed(embed)
        response = await webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {product['name']} - Novo preço: R$ {new_price:.2f}" + 
                         (f" - Desconto: {desconto_percentual:.2f}%" if not is_new_product else ""))
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")
    except Exception as e:
        logging.error(f"Erro ao enviar webhook: {str(e)}")

# Modifique a função insert_produto para verificar alterações de preço
def insert_produto(id, name, url, sku, preco):
    conn = connect_db()
    c = conn.cursor()

    c.execute('''SELECT preco FROM produtos WHERE sku = ?''', (sku,))
    existing_product = c.fetchone()

    if existing_product:
        old_price = existing_product[0]
        if preco != old_price:
            c.execute('''UPDATE produtos SET preco = ? WHERE sku = ?''', (preco, sku))
            conn.commit()
            logging.info(f"Preço atualizado para o produto: {name} (SKU: {sku})")
            asyncio.create_task(send_discord_notification({
                'name': name,
                'url': url
            }, old_price, preco, False))
    else:
        c.execute('''INSERT INTO produtos (id, name, url, sku, preco)
                     VALUES (?, ?, ?, ?, ?)''', (id, name, url, sku, preco))
        conn.commit()
        logging.info(f"Produto novo adicionado: {name} (SKU: {sku})")
        asyncio.create_task(send_discord_notification({
            'name': name,
            'url': url
        }, 0, preco, True))

    conn.close()

async def fetch_pontofrio_data(session, page, max_retries=3, delay=1):
    url = "https://api-partner-prd.pontofrio.com.br/api/v2/Search"
    params = {
        "ResultsPerPage": "37",
        "ApiKey": "pontofrio",
        "Filter": "L139420",
        "Page": str(page),
        "Banner": "true",
        "PlatformType": "1",
        "VariantConfiguration": "A",
        "multiselection": "false",
        "PartnerKey": "solr",
        "Sortby": "popularidade"
    }
    
    headers = {
        "accept": "*/*",
        "access-control-request-method": "GET",
        "access-control-request-headers": "xaplication",
        "origin": "https://www.pontofrio.com.br",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-fetch-dest": "empty",
        "referer": "https://www.pontofrio.com.br",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Dados obtidos com sucesso para a página {page}")
                return data
            else:
                logging.warning(f"Tentativa {attempt + 1}: Erro na requisição GET para a página {page}: {response.status_code}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    logging.error(f"Todas as tentativas falharam para a página {page}")
                    return None
        except Exception as e:
            logging.error(f"Erro na tentativa {attempt + 1} para a página {page}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                logging.error(f"Todas as tentativas falharam para a página {page}")
                return None

async def extract_products(response):
    if not response or "products" not in response:
        return []

    products = response["products"]
    extracted_data = [
        {
            "id": product["id"],
            "name": product["name"],
            "url": product["url"],
            "sku": product["sku"]
        }
        for product in products
    ]
    return extracted_data

async def extrair_produtos():
    session = tls_client.Session(client_identifier="firefox_102")
    
    all_products = []
    for page in range(-3, 0):
        response = await fetch_pontofrio_data(session, page)
        if response:
            products = await extract_products(response)
            all_products.extend(products)
        else:
            break  # Sai do loop se não houver mais páginas

    logging.info(f"Total de produtos extraídos: {len(all_products)}")
    
    with open("produtos.json", "w", encoding="utf-8") as file:
        json.dump(all_products, file, ensure_ascii=False, indent=4)
    
    return all_products

async def fetch_preco_produtos(max_retries=3, delay=1):
    produtos = await extrair_produtos()

    logging.info("\nProdutos extraídos:")

    ids_produtos_str = ",".join(str(produto["id"]) for produto in produtos)

    url = "https://api.pontofrio.com.br/merchandising/oferta/v1/Preco/Produto/PrecoVenda/"
    params = {
        "idRegiao": "",
        "idsProduto": ids_produtos_str,
        "composicao": "DescontoFormaPagamento,MelhoresParcelamentos",
        "apiKey": "d081fef8c2c44645bb082712ed32a047"
    }

    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'accept': '*/*',
        'origin': 'https://www.pontofrio.com.br',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://www.pontofrio.com.br',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    session = tls_client.Session(client_identifier="chrome_122", random_tls_extension_order=True)

    for attempt in range(max_retries):
        try:
            response = session.get(url, headers=headers, params=params)
            logging.info(f"Tentativa {attempt + 1} - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                return produtos, data.get('PrecoProdutos', [])
            else:
                logging.warning(f"PONTO FRIO - Tentativa {attempt + 1} falhou. Código de status: {response.status_code}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
        except Exception as e:
            logging.error(f"Erro na tentativa {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)

    logging.error("Todas as tentativas falharam ao buscar preços dos produtos.")
    return produtos, []

async def juntar_e_exibir_produtos_pontofrio():
    produtos, precos = await fetch_preco_produtos()
    
    logging.info(f"Produtos extraídos: {len(produtos)}")
    logging.info(f"PONTO FRIO - Preços obtidos: {len(precos)}")

    produto_dict = {str(produto['sku']): produto for produto in produtos}
    
    for preco in precos:
        produto_id = str(preco['PrecoVenda']['IdSku'])
        if produto_id in produto_dict:
            produto = produto_dict[produto_id]
            preco_pix = preco['DescontoFormaPagamento']['PrecoVendaComDesconto']

            # Inserir os dados no banco de dados
            insert_produto(produto['id'], produto['name'], produto['url'], produto['sku'], preco_pix)
    
    if not precos:
        logging.info("Nenhum preço foi retornado. Verifique a resposta da API.")

async def exportar_produtos_realtime():
    produtos, precos = await fetch_preco_produtos()
    
    # Criar dicionário combinado de produtos e preços
    produtos_completos = []
    produto_dict = {str(produto['sku']): produto for produto in produtos}
    
    for preco in precos:
        sku = str(preco['PrecoVenda']['IdSku'])
        if sku in produto_dict:
            produto = produto_dict[sku]
            produtos_completos.append({
                "codigo": sku,
                "nome": produto['name'],
                "url": produto['url'],
                "preco_atual": preco['DescontoFormaPagamento']['PrecoVendaComDesconto'],
                "timestamp": datetime.now().isoformat()
            })
    
    # Exportar para JSON
    with open('produtos_realtime.json', 'w', encoding='utf-8') as f:
        json.dump(produtos_completos, f, ensure_ascii=False, indent=4)
    
    logging.info(f"JSON com {len(produtos_completos)} produtos atualizado")


async def monitor_pontofrio():
    create_table()  # Cria a tabela antes de iniciar o processo
    while True:
        await exportar_produtos_realtime()  # Substitui a chamada ao 
        await juntar_e_exibir_produtos_pontofrio()
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(monitor_pontofrio())
