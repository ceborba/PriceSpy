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
        self.params_url = ["/perfumes", "/outlet"]
        self.name_params = ["Perfumes Importados e Nacionais", "Produtos de Beleza com no Mínimo 30% de Desconto"]
        self.permanentId_params = ["da515f48-d398-437a-82e9-e16b7f5def78", "62822e15-1237-4f8b-b877-4d27dfdef57b"]
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
                    logging.info(f"Consultando {param} - página {page_number}...")
                    content = await self.fetch_page(param, permanentId, name_params, page_number, session)
                    
                    if content:
                        products = self.extract_product_info(content)
                        logging.info(f"Página {page_number} carregada com sucesso. {len(products)} produtos encontrados.")
                        
                        # Se não encontrar produtos, pula para a próxima URL
                        if not products:
                            logging.info(f"Nenhum produto encontrado na página {page_number}. Pulando para a próxima página.")
                            break  # Isso vai interromper o loop da página atual e irá para a próxima página URL
                    
                        # Salvar os dados no banco de dados
                        salvar_dados_no_banco(products)
                        logging.info(f"Produtos da página {page_number} salvos no banco de dados.")
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
            url_key = name_element['href'].split('/')[1].split('/')[0]
            
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
        "20-49": "https://discord.com/api/webhooks/1333331706941280300/K0OAmCNsYvoOSksjGZPY26ubE0-HdNciWMtSPGAOBZ5Q0VG87DCKLZ_scSqyslZ_QScT",
        "50-69": "https://discord.com/api/webhooks/1333332616367181907/wXwb3NfEeB31vejTWkTAnjSdGPxntAxwhHGz8xIQ8lyYwHyyO6NzjxsiTdFhFS6KySKr",
        "70-100": "https://discord.com/api/webhooks/1333332722520817716/MBKpm6fEBiv_pAn6NDiL6fUyJb9XhbvCmzdXLRrZOSMfTuKcLkaAQn0wGpiG6NKf6uBG",
    }

    for id_produto, nome_produto, preco_antigo, preco_novo in mudancas:
        desconto_percentual = ((preco_antigo - preco_novo) / preco_antigo) * 100
        link_produto = f"https://belezanaweb.com.br/produto/{id_produto}"

        if desconto_percentual < 20:
            continue  # Pula para a próxima iteração se o desconto for menor que 20%

        if 20 <= desconto_percentual < 50:
            webhook_url = webhooks["20-49"]
        elif 50 <= desconto_percentual < 70:
            webhook_url = webhooks["50-69"]
        else:
            webhook_url = webhooks["70-100"]

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
            logging.error(f"Erro ao enviar webhook: {response.status_code}")


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

    for produto in dados:
        # Verificar se o produto já existe no banco de dados
        cursor.execute('''SELECT id FROM produtosBW WHERE url_key = ?''', (produto['url_key'],))
        if cursor.fetchone():
            continue
        else:
            cursor.execute(''' 
                INSERT INTO produtosBW (url_key, name, price, url)
                VALUES (?, ?, ?, ?)
            ''', (produto['url_key'], produto['name'], produto['price'], produto['url']))
            logging.info(f"Produto inserido no banco de dados: {produto['name']}")

    conexao.commit()
    conexao.close()


async def main():
    scraper = BelezanaWeb()
    while True:
        await scraper.monitor_pages(start_page=1, end_page=201)  # Modifique o intervalo conforme necessário
        
        logging.info("Processo de scraping concluído.")
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
