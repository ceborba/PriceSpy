import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup
import sqlite3
from discord_webhook import DiscordWebhook, DiscordEmbed


# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calcular_desconto(preco_antigo, preco_novo):
    if preco_antigo == 0:
        return 0
    desconto = ((preco_antigo - preco_novo) / preco_antigo) * 100
    return f"{desconto:.2f}"

class BelezanaWeb:
    def __init__(self):
        self.base_url = "https://www.belezanaweb.com.br/api/htmls/showcase?"
        self.params_url = ["/perfumes", "/outlet", "/maquiagem", "/cabelos", "/cuidados-para-pele"]
        self.name_params = ["Perfumes Importados e Nacionais", "Produtos de Beleza com no Mínimo 30% de Desconto",
                            "Maquiagem", "Produtos para Cabelos", "Skincare"
                            ]
        self.permanentId_params = ["da515f48-d398-437a-82e9-e16b7f5def78", "62822e15-1237-4f8b-b877-4d27dfdef57b", 
                                    "1a36a238-8ff9-4631-b540-d262127d80d8", "53f4f262-f6c1-4deb-a10e-8cb9e1452a48",
                                    "018598c7-9d7b-4137-b658-beba885f063f"
                            ]
        self.headers_template = {
            "x-newrelic-id": 'Vg4OUlZRGwIJV1RXDwIDVw==',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": '?0',
            "x-requested-with": 'XMLHttpRequest',
            "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            "accept": '*/*',
            "sec-fetch-site": 'same-origin',
            "sec-fetch-mode": 'cors',
            "sec-fetch-dest": 'empty',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

    async def fetch_page(self, param, permanentId, name_params, page_number, session):
        url = self.base_url
        headers = self.headers_template.copy()
        headers["referer"] = f'https://www.belezanaweb.com.br{param}'
        params = {
            "size": "50",
            "fieldList": "gift,featured,imageObjects,compositionId,marketable.isMarketable,marketable.discontinued,inventory.quantity,advertisements,priceSpecification,sku,brand.name,brand.slugName,group.total,slugName,label,badge,hasGiftBenefits,organization,name,details.shortDescription,aggregateRating",
            "pageName": name_params,
            "permanentId": permanentId,
            "uri": param,
            "pagina": str(page_number),
            "ordem": "priceSpecification.percent desc"
        }
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                logging.error(f"Erro na requisição: Status {response.status}")
                return None
        except Exception as e:
            logging.error(f"Erro na requisição: {e}")
            return None

    async def monitor_pages(self, start_page=1, end_page=201):
        async with aiohttp.ClientSession() as session:
            for param, permanentId, name_params in zip(self.params_url, self.permanentId_params, self.name_params):
                for page_number in range(start_page, end_page + 1):
                    # logging.info(f"Consultando {param} - página {page_number}...")
                    content = await self.fetch_page(param, permanentId, name_params, page_number, session)
                    
                    if content:
                        products = self.extract_product_info(content)
                        logging.info(f"Página {page_number} carregada com sucesso. {len(products)} produtos encontrados.")
                        
                        # Se não encontrar produtos, pula para a próxima URL
                        if not products:
                            # logging.info(f"Nenhum produto encontrado na página {page_number}. Pulando para a próxima página.")
                            break  # Isso vai interromper o loop da página atual e irá para a próxima página URL
                    
                        # Salvar os dados no banco de dados
                        salvar_dados_no_banco(products)
                        # logging.info(f"Produtos da página {page_number} salvos no banco de dados.")
                    else:
                        logging.warning(f"Falha ao carregar {param} - página {page_number}.")


    def extract_product_info(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        for item in soup.find_all('div', class_='showcase-item'):
            name_element = item.find('a', class_='showcase-item-title')
            price_element = item.find('span', class_='price-value')
            
            if not name_element or not price_element:
                continue
            
            name = name_element.text.strip()
            price = price_element.text.strip()
            url = 'https://www.belezanaweb.com.br' + name_element['href']
            url_key = name_element['href'].strip('/')
            
            price = price.replace('R$', '').replace('.', '').replace(',', '.').strip()
            
            try:
                price_float = float(price)
            except ValueError:
                logging.warning(f"Não foi possível converter o preço '{price}' para float. Ignorando este produto.")
                continue

            products.append({
                'url_key': url_key,
                'name': name,
                'price': price_float,
                'url': url
            })

        return products


def enviar_notificacoes_discord(mudancas):
    webhooks = {
        "novos": "https://discord.com/api/webhooks/1333557849275498618/FWzHc4lQkDg9BEwD3AeGCqxWZyop47cC8NaKzKNWpGfPBQlslS4E0Xy9p70qhNMvqVVJ",
        "1-49": "https://discord.com/api/webhooks/1333331706941280300/K0OAmCNsYvoOSksjGZPY26ubE0-HdNciWMtSPGAOBZ5Q0VG87DCKLZ_scSqyslZ_QScT",
        "50-69": "https://discord.com/api/webhooks/1333332616367181907/wXwb3NfEeB31vejTWkTAnjSdGPxntAxwhHGz8xIQ8lyYwHyyO6NzjxsiTdFhFS6KySKr",
        "70-100": "https://discord.com/api/webhooks/1333332722520817716/MBKpm6fEBiv_pAn6NDiL6fUyJb9XhbvCmzdXLRrZOSMfTuKcLkaAQn0wGpiG6NKf6uBG",
    }

    for url_key, nome_produto, preco_antigo, preco_novo, url_completa in mudancas:
        if preco_antigo == 0:
            logging.warning(f"Preço antigo inválido para o produto {nome_produto}. Ignorando...")
            continue

        desconto_percentual = ((preco_antigo - preco_novo) / preco_antigo) * 100
        link_produto = url_completa  # Usando a URL completa passada

        # if desconto_percentual == 0:
        #     webhook_url = webhooks["novos"]
        # elif 1 <= desconto_percentual <= 49:
        #     webhook_url = webhooks["1-49"]
        if 50 <= desconto_percentual <= 69:
            webhook_url = webhooks["50-69"]
        elif 70 <= desconto_percentual <= 100:
            webhook_url = webhooks["70-100"]
        else:
            logging.warning(f"Desconto percentual fora das faixas: {desconto_percentual:.2f}%. Ignorando...")
            continue

        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(title=nome_produto, description="Alteração de preço detectada!", color='03b2f8')
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {preco_novo:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique aqui]({link_produto})")
        webhook.add_embed(embed)

        response = webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {nome_produto} - Novo preço: R$ {preco_novo:.2f} - Desconto: {desconto_percentual:.2f}%")
        else:
            logging.error(f"Erro ao enviar webhook ({response.status_code}): {response.text}")


def salvar_dados_no_banco(dados):
    conexao = sqlite3.connect('produtosBW.db')
    cursor = conexao.cursor()

    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS produtosBW (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_key TEXT UNIQUE,
            name TEXT,
            price REAL,
            url TEXT
        )
    ''')

    novos_produtos = []
    produtos_alterados = []

    for produto in dados:
        cursor.execute('''SELECT id, price FROM produtosBW WHERE url_key = ?''', (produto['url_key'],))
        resultado = cursor.fetchone()
        
        if resultado:
            id_produto, preco_antigo = resultado
            if preco_antigo != produto['price']:
                cursor.execute('''
                    UPDATE produtosBW SET price = ? WHERE id = ?
                ''', (produto['price'], id_produto))
                produtos_alterados.append((produto['url_key'], produto['name'], preco_antigo, produto['price'], produto['url']))
        else:
            cursor.execute(''' 
                INSERT INTO produtosBW (url_key, name, price, url)
                VALUES (?, ?, ?, ?)
            ''', (produto['url_key'], produto['name'], produto['price'], produto['url']))
            id_produto = cursor.lastrowid
            novos_produtos.append((produto['url_key'], produto['name'], produto['price'], produto['price'], produto['url']))
            logging.info(f"Produto inserido no banco de dados: {produto['name']}")

    conexao.commit()
    conexao.close()

    if novos_produtos:
        enviar_notificacoes_discord(novos_produtos)
    if produtos_alterados:
        enviar_notificacoes_discord(produtos_alterados)

async def monitor_belezanaweb():
    scraper = BelezanaWeb()
    while True:
        await scraper.monitor_pages(start_page=1, end_page=201)  # Modifique o intervalo conforme necessário
        
        logging.info("Processo de scraping concluído.")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(monitor_belezanaweb())
