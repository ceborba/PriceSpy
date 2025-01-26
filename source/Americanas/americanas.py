import aiohttp
import asyncio
import json
import sqlite3
from discord_webhook import DiscordWebhook, DiscordEmbed
import logging
import traceback

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_data(session, url, headers, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Erro na requisição: {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Erro ao fazer a requisição (tentativa {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                return None

def create_table(conn):
    try:
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                slug TEXT,
                link TEXT,
                price REAL,
                cashback REAL
            )
            ''')
    except sqlite3.Error as e:
        logging.error(f"Erro ao criar tabela: {e}")

def enviar_webhook_discord(nome_produto, preco_antigo, preco_novo, link_produto, promocao_nome, desconto_percentual, novo_produto=False):
    webhooks = {
        "1-19": "https://discord.com/api/webhooks/1331322843916664944/6-lXqiaxkzo8hYbTl6fD71aZkdF2Yxi8T5r_JjbdVJ_sQghNVT2tj51Of6Igg1t7geAC",
        "20-49": "https://discord.com/api/webhooks/1331322896299327509/_oM_OZRRZDIN9yZxKRYV0tSsb3zyVV3mDIM1bfpoDvxt9908IwyZfV-E9VpBR-Cjtp9k",
        "50-69": "https://discord.com/api/webhooks/1331322954428186726/vIU1ATo1GlkrsjeQrcOCMz6uyO3XZKUpeHk6Y904pZy1MLkVwE9vZcx9jceAfovANzws",
        "70-100": "https://discord.com/api/webhooks/1331323022388494457/WMlszZnhJ3xuUvx6x_ZnWs6b-_MJlmazc1xor0VWNG9ED8VU_31fMERDY8ndU_LXb7Y_",
        "novos": "https://discord.com/api/webhooks/1331322778028212294/QRguTNyM0Uiu1XBvQwrvJkIFUZ2vlYID7Y_b3D3CKiTUYVP8iB7c0ntKS3rh4mVrrsTn"
    }

    try:
        if novo_produto:
            webhook_url = webhooks["novos"]
        elif desconto_percentual <= 20:
            webhook_url = webhooks["1-19"]
        elif desconto_percentual <= 50:
            webhook_url = webhooks["20-49"]
        elif desconto_percentual <= 70:
            webhook_url = webhooks["50-69"]
        else:
            webhook_url = webhooks["70-100"]

        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(title=nome_produto, description="Alteração de preço detectada!" if not novo_produto else "Novo produto adicionado!", color='03b2f8')
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {preco_novo:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Promoção", value=promocao_nome or "Sem Promoção")
        embed.add_embed_field(name="Loja", value="Americanas")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique aqui]({link_produto})")
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {nome_produto} - Novo preço: R$ {preco_novo:.2f} - Desconto: {desconto_percentual:.2f}%")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")
    except Exception as e:
        logging.error(f"Erro ao enviar webhook: {str(e)}")

async def process_product(conn, product, seen_products):
    try:
        product_id = product.get('id')
        if not product_id or product_id in seen_products:
            return False

        seen_products.add(product_id)
        name = product.get('name')
        slug = product.get('slug')
        link = f"https://www.americanas.com.br/produto/{product_id}/{slug}"

        if product is None:
            logging.error(f"Produto é None para o ID {product_id}. Ignorando processamento.")
            return False

        offers = product.get('offers', {}).get('result', [])
        if offers:
            offer = offers[0]
            # Extraindo diretamente o preço do campo 'price'
            best_payment = offer.get('bestPaymentOption', {})
            price = best_payment.get('price')  # Considerar 'salesPrice' como o preço principal
            cashback_data = offer.get('cashback', {})
            cashback = cashback_data.get('value') if cashback_data else None
        else:
            price = None
            cashback = None

        if price is None:
            logging.warning(f"Preço não encontrado para o produto {product_id} ({name})")
            return False

        with conn:
            cursor = conn.cursor()
            cursor.execute('SELECT price FROM products WHERE id = ?', (product_id,))
            result = cursor.fetchone()
            
            if result:
                preco_antigo = result[0]
                if price < preco_antigo:
                    desconto_percentual = ((preco_antigo - price) / preco_antigo) * 100
                    enviar_webhook_discord(
                        nome_produto=name,
                        preco_antigo=preco_antigo,
                        preco_novo=price,
                        link_produto=link,
                        promocao_nome=cashback or "Sem Promoção",
                        desconto_percentual=desconto_percentual,
                        novo_produto=False
                    )
            else:
                enviar_webhook_discord(
                    nome_produto=name,
                    preco_antigo=0,
                    preco_novo=price,
                    link_produto=link,
                    promocao_nome=cashback or "Sem Promoção",
                    desconto_percentual=0,
                    novo_produto=True
                )

            cursor.execute('''
            INSERT OR REPLACE INTO products (id, name, slug, link, price, cashback)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (product_id, name, slug, link, price, cashback))

        return True
    except Exception as e:
        logging.error(f"Erro ao processar produto {product_id if 'product_id' in locals() else 'desconhecido'}: {str(e)}")
        logging.debug(f"Traceback: {traceback.format_exc()}")
        return False

async def monitor_americanas():
    while True:
        url = "https://catalogo-bff-v2-americanas.b2w.io/graphql"
        headers = {
            "authority": "catalogo-bff-v2-americanas.b2w.io",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "apollographql-client-name": "catalogo-v3",
            "content-type": "application/json",
            "device": "desktop",
            "origin": "https://www.americanas.com.br",
            "referer": "https://www.americanas.com.br/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "macroregion": "PR_CAPITAL",
            "mesoregion": "4101",
            "onedaydeliveryfiltered": "false",
            "opn": "WZRBJFFW",
            "sec-fetch-mode": "cors"
        }

        limit = 100
        total_products = 0
        seen_products = set()

        max_pages = 50  
        empty_pages_threshold = 1

        paths = [
            "/categoria/celulares-e-smartphones/f/loja-Americanas",
            "/categoria/tv-e-home-theater/f/loja-Americanas",
            "/categoria/games/f/loja-Americanas",
            "/categoria/audio/f/loja-Americanas",
            "/categoria/cameras-e-drones/f/loja-Americanas",
            "/categoria/telefonia-fixa/f/loja-Americanas",
            "/categoria/informatica/f/loja-Americanas",
            "/categoria/informatica-e-acessorios/f/loja-Americanas",
            "/categoria/pc-gamer/f/loja-Americanas",
            "/categoria/agro-industria-e-comercio/f/loja-Americanas",
            "/categoria/sinalizacao-e-seguranca/f/loja-Americanas",
            "/categoria/enfeites-de-natal/f/loja-Americanas",
            "/categoria/eletrodomesticos/f/loja-Americanas",
            "/categoria/eletroportateis/f/loja-Americanas",
            "/categoria/ar-condicionado-e-aquecedores/f/loja-Americanas",
            "/categoria/moveis/f/loja-Americanas",
            "/categoria/casa-e-construcao/f/loja-Americanas",
            "/categoria/utilidades-domesticas/f/loja-Americanas",
            "/categoria/cama-mesa-e-banho/f/loja-Americanas",
            "/categoria/livros/f/loja-Americanas",
            "/categoria/instrumentos-musicais/f/loja-Americanas",
            "/categoria/artigos-de-festas/f/loja-Americanas",
            "/categoria/artesanato/f/loja-Americanas",
            "/categoria/automotivo/f/loja-Americanas",
            "/categoria/brinquedos/f/loja-Americanas",
            "/categoria/bebes/f/loja-Americanas",
            "/categoria/gift-card/f/loja-Americanas",
            "/categoria/pet-shop/f/loja-Americanas",
            "/categoria/malas-mochilas-e-acessorios/f/loja-Americanas",
            "/categoria/papelaria/f/loja-Americanas",
            "/categoria/vale-presente/f/loja-Americanas",
            "/categoria/esporte-e-lazer/f/loja-Americanas",
            "/categoria/saude-e-bem-estar/f/loja-Americanas",
            "/categoria/suplementos-e-vitaminas/f/loja-Americanas",
            "/categoria/vestuario-esportivo/f/loja-Americanas",
            "/categoria/bem-estar-sexual/f/loja-Americanas",
            "/categoria/relogios-e-joias/relogios/f/loja-Americanas",
            "/categoria/beleza-e-perfumaria/cabelos/f/loja-Americanas",
            "/categoria/beleza-e-perfumaria/dermocosmeticos/f/loja-Americanas",
            "/categoria/beleza-e-perfumaria/cuidados-com-a-pele/f/loja-Americanas",
            "/categoria/beleza-e-perfumaria/barbearia/f/loja-Americanas",
            "/categoria/beleza-e-perfumaria/unhas/f/loja-Americanas",
            "/categoria/beleza-e-perfumaria/perfumes/f/loja-Americanas",
            "/categoria/games/jogos-para-pc-e-acessorios/headset-gamer/f/loja-Webcontinental+Marketplace/loja-OFICINA+DOS+BITS/loja-CLICK+COMPROU/loja-Carrefour.com/loja-Obabox+Oficial/loja-Login+Informática/loja-CASA+&+VIDEO/loja-Americanas/loja-e-Store/loja-INPOWER/loja-MIRANDA/loja-IBYTE/loja-Concordia+Informática/loja-Alligator+Shop/loja-Primetek/loja-BITS+&+BYTES/loja-Mixtou/loja-Gigantec/loja-HD+ELETRÔNICOS+/loja-MMPLACE/loja-WEBCONTINENTAL/loja-ELG+Store",
            "/categoria/celulares-e-smartphones/g/tipo-de-produto-fone+de+ouvido",
            "/categoria/celulares-e-smartphones/f/loja-Americanas/loja-Motorola+Oficial/loja-Trocafone/loja-Webcontinental+Marketplace/loja-Carrefour.com/loja-Loja+Samsung+Oficial/loja-WEBCONTINENTAL/loja-BOM+&+BARATO/loja-Gshield/loja-Trip+Info/loja-MMSANTOS/loja-MMPLACE/loja-ALLMIXSHOP+?viewMode=list"
        ]

        try:
            conn = sqlite3.connect('americanas_products.db')
            create_table(conn)

            async with aiohttp.ClientSession() as session:
                for path in paths:
                    logging.info(f"Processando path: {path}")
                    page = 0
                    empty_pages_count = 0

                    while page < max_pages:
                        logging.info(f"Processando página {page}...")
                        offset = page * limit

                        params = {
                            "operationName": "searchCategory",
                            "variables": json.dumps({
                                "path": path,
                                "sortBy": "relevance",
                                "source": "blanca",
                                "limit": limit,
                                "offset": offset
                            }),
                            "extensions": json.dumps({
                                "persistedQuery": {
                                    "version": 1,
                                    "sha256Hash": "84c6b915064db527392f7f7fd846949a64259ae90a487e81cd652f6d77752461"
                                }
                            })
                        }

                        try:
                            data = await fetch_data(session, url, headers=headers, params=params)
                            
                            if data is None or 'data' not in data or 'search' not in data['data'] or 'products' not in data['data']['search']:
                                empty_pages_count += 1
                                if empty_pages_count >= empty_pages_threshold:
                                    logging.info(f"Encontradas {empty_pages_threshold} páginas vazias consecutivas. Encerrando.")
                                    break
                                continue

                            products = data['data']['search']['products']

                            if not products:
                                empty_pages_count += 1
                                if empty_pages_count >= empty_pages_threshold:
                                    logging.info(f"Encontradas {empty_pages_threshold} páginas vazias consecutivas. Encerrando.")
                                    break
                                continue

                            empty_pages_count = 0
                            logging.info(f"Produtos encontrados na página {page}: {len(products)}")

                            new_products_count = 0
                            for item in products:
                                product = item.get('product', {})
                                if product and await process_product(conn, product, seen_products):
                                    new_products_count += 1
                                    total_products += 1

                            if new_products_count == 0:
                                logging.info(f"Nenhum novo produto encontrado na página {page}. Encerrando.")
                                break

                        except Exception as e:
                            logging.error(f"Erro ao processar a página {page}: {str(e)}")
                            logging.debug(f"Traceback: {traceback.format_exc()}")
                            empty_pages_count += 1
                            if empty_pages_count >= empty_pages_threshold:
                                logging.info(f"Encontrados {empty_pages_threshold} erros consecutivos. Encerrando.")
                                break

                        page += 1
                        await asyncio.sleep(0.1)

                    logging.info(f"Pausa de 0.1 segundos após processar o path {path}.")
                    await asyncio.sleep(0.1)

        except Exception as e:
            logging.error(f"Erro geral: {str(e)}")
            logging.debug(f"Traceback: {traceback.format_exc()}")
        finally:
            conn.close()
            logging.info(f"\nTotal de produtos coletados: {total_products}")

if __name__ == "__main__":
    asyncio.run(monitor_americanas())
