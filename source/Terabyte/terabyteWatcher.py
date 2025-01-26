import aiohttp
import asyncio
from asyncio import Semaphore
import random
from discord_webhook import DiscordWebhook, DiscordEmbed
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import time
import json

# Configuração do SQLAlchemy
Base = declarative_base()

class Produto(Base):
    __tablename__ = 'produtos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    link = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    desconto = Column(Integer, nullable=False)
    parcelas = Column(Integer, nullable=False)
    valor_parcela = Column(Float, nullable=False)

# Configuração do banco de dados
DATABASE_URL = "sqlite:///produtos.db"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Lista de User-Agents
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
]

async def extrair_produto(produto):
    try:
        nome = produto.find("a", class_="product-item__name").find("h2").text.strip()
        link = produto.find("a", class_="product-item__name")['href']
        try:
            preco_texto = produto.find("div", class_="product-item__new-price").find("span").text.strip()
            preco = float(preco_texto.replace('R$', '').replace('.', '').replace(',', '.').strip())
        except AttributeError:
            preco = 0.0
        try:
            desconto_texto = produto.find("div", class_="product-promo-bar__percent").find("span", class_="number").text.strip()
            desconto = int(desconto_texto.replace('%', '').strip())
        except AttributeError:
            desconto = 0
        try:
            parcelas_elementos = produto.find("div", class_="product-item__juros").find_all("span")
            parcelas_texto = parcelas_elementos[0].text.strip()
            parcelas = int(parcelas_texto.replace('x', '').strip())
            valor_parcela_texto = parcelas_elementos[2].text.strip()
            valor_parcela = float(valor_parcela_texto.replace('R$', '').replace(',', '.').strip())
        except (AttributeError, IndexError):
            parcelas = 1
            valor_parcela = preco
        return {
            "nome": nome,
            "link": link,
            "preco": preco,
            "desconto": desconto,
            "parcelas": parcelas,
            "valor_parcela": valor_parcela,
        }
    except Exception as e:
        print(f"Erro ao extrair produto: {e}")
        return None

def enviar_notificacao_discord(produto, preco_antigo, eh_novo=False):
    webhooks = {
        "1-20": "https://discord.com/api/webhooks/1328901213999071283/cQprCnbc5ghizWbq-Qd1OhKJ_FYk3DKxAk3QmjRUABbm5glptF4O_m83JYGu6UAxvTyfTESTE",
        "21-50": "https://discord.com/api/webhooks/1328902690071117886/2kUxBdZaR8KlBUtGrpxgzO_Znw0B94imH3YDkvrcnE3S_Prkh-2t8T9OHgnmA4eL_6YdTESTE",
        "51-70": "https://discord.com/api/webhooks/1328902914177105920/oZo3QRbI7LzGSkJplzh0fqId-ZWCKDdgKuAJmI-ymjc1dMwX4Jpq_yrwS4YfFty7ud-KTESTE",
        "71-100": "https://discord.com/api/webhooks/1328902975439245404/S1i_wIw8baiyPP-LfJhw7jgjQNm5--izgAKRvRFtndxjjZTQEHgrjdlmzzqKzDJPVpuITESTE",
        "novos": "https://discord.com/api/webhooks/1328903035040043049/_An8yyR-nRZSVr8s4Q80uQzlM34yWe4K5sZdJCgRU36ubYYgnJ1vdwGTYtoALWYRqln7TESTE"
    }
    try:
        if preco_antigo == 0 and produto['preco'] == 0:
            desconto_percentual = 0
        elif preco_antigo == 0:
            desconto_percentual = 100
        elif produto['preco'] == 0:
            desconto_percentual = 100
        else:
            desconto_percentual = ((preco_antigo - produto['preco']) / preco_antigo) * 100

        if desconto_percentual < 0:
            return

        if eh_novo:
            webhook_url = webhooks["novos"]
            mensagem = "Novo produto adicionado ao estoque"
        elif desconto_percentual == 0:
            webhook_url = webhooks["novos"]
            mensagem = "Produto adicionado ao estoque novamente ou novo produto"
        elif desconto_percentual <= 20.1:
            webhook_url = webhooks["1-20"]
            mensagem = "Alteração de preço detectada!"
        elif desconto_percentual <= 50.1:
            webhook_url = webhooks["21-50"]
            mensagem = "Alteração de preço detectada!"
        elif desconto_percentual <= 70:
            webhook_url = webhooks["51-70"]
            mensagem = "Alteração de preço detectada!"
        elif 71 <= desconto_percentual <= 100:
            webhook_url = webhooks["71-100"]
            mensagem = "Alteração de preço detectada!"
        else:
            raise ValueError("Desconto inválido. O desconto deve estar entre 0 e 100.")
        
        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(title=produto['nome'], description=mensagem, color='03b2f8')

        if eh_novo:
            embed.add_embed_field(name="Preço Atual", value=f"R$ {produto['preco']:.2f}")
        else:
            if desconto_percentual > 0:
                embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
                embed.add_embed_field(name="Novo Preço", value=f"R$ {produto['preco']:.2f}")
                embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")

        embed.add_embed_field(name="Promoção", value="Não foi localizado a promoção vigente desse item")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique aqui]({produto['link']})")
        webhook.add_embed(embed)
        response = webhook.execute()

        if response.status_code == 200:
            print(f"Webhook enviado: {produto['nome']} - {'Novo produto' if eh_novo else f'Novo preço: R$ {produto['preco']:.2f} - Desconto: {desconto_percentual:.2f}%'}")
        else:
            print(f"Erro ao enviar webhook: {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")

def inserir_ou_atualizar_produto(produto_data):
    produto_existente = session.query(Produto).filter_by(link=produto_data['link']).first()
    if produto_existente:
        if produto_existente.preco == 0 and produto_data['preco'] == 0:
            desconto_percentual = 0
        elif produto_existente.preco == 0:
            desconto_percentual = 100
        elif produto_data['preco'] == 0:
            desconto_percentual = 100
        else:
            desconto_percentual = ((produto_existente.preco - produto_data['preco']) / produto_existente.preco) * 100

        if desconto_percentual >= 0:
            if produto_existente.preco != produto_data['preco']:
                enviar_notificacao_discord(produto_data, produto_existente.preco)
            produto_existente.preco = produto_data['preco']
            produto_existente.desconto = produto_data['desconto']
            produto_existente.valor_parcela = produto_data['valor_parcela']
            session.commit()
    else:
        enviar_notificacao_discord(produto_data, 0, eh_novo=True)
        produto = Produto(**produto_data)
        session.add(produto)
        session.commit()

async def buscar_dados_url_com_retentativa(url, semaphore, pagina=1):
    async with semaphore:
        headers = {
            "Accept": "text/html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "3.12.26.127",
            "User-Agent": random.choice(user_agents),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": url.replace("http://3.12.26.127", ""),
            "Origin": "http://3.12.26.127"
        }
        payload = {
            "app": "true",
            "url": url.replace("http://3.12.26.127", ""),
            "more": "true",
            "filter[marca]": "0",
            "filter[order]": "ordem_asc",
            "filter[pg]": str(pagina)
        }
        print(f"Payload: {payload['url']}")
        tentativa = 0
        while True:
            tentativa += 1
            try:
                print(f"\n{'='*50}")
                print(f"Acessando URL: {url}")
                print(f"Payload: {payload}")
                print(f"Página: {pagina}")
                print(f"Tentativa: {tentativa}")
                print(f"{'='*50}\n")
                async with aiohttp.ClientSession(headers=headers) as session:
                    if pagina == 1:
                        async with session.get(url, allow_redirects=True) as response:
                            return await processar_resposta(response)
                    else:
                        async with session.post(url, data=payload) as response:
                            return await processar_resposta(response)
            except Exception as e:
                print(f"Erro na requisição: {e}")
                await asyncio.sleep(10)

async def processar_resposta(response):
    status = response.status
    print(f"Status Code: {status}")
    if status in [200, 201]:
        texto = await response.text()
        texto = texto.encode('utf-8').decode('utf-8-sig')
        try:
            dados = json.loads(texto)
            html = dados.get("more", "")
        except json.JSONDecodeError:
            html = texto
        soup = BeautifulSoup(html, 'html.parser')
        produtos = soup.find_all("div", class_="product-item")
        produtos_disponiveis = [p for p in produtos if not p.find('div', class_='tbt_esgotado')]
        print(f"Total de produtos na página: {len(produtos)}")
        print(f"Produtos disponíveis: {len(produtos_disponiveis)}")
        if len(produtos) == 0:
            print("Nenhum produto encontrado na página.")
            return False
        produtos_encontrados = []
        for produto in produtos_disponiveis:
            dados_produto = await extrair_produto(produto)
            if dados_produto:
                # print(f"\nProduto encontrado:")
                # print(f"Nome: {dados_produto['nome']}")
                # print(f"Preço: R${dados_produto['preco']:.2f}")
                # print(f"Link: {dados_produto['link']}")
                # print(f"{'_'*30}")
                inserir_ou_atualizar_produto(dados_produto)
                produtos_encontrados.append(dados_produto['nome'])
        return produtos_encontrados if produtos_encontrados else False
    else:
        print(f"Falha na requisição. Status: {status}. Tentando novamente...")
        await asyncio.sleep(1)
        return False

def comparar_produtos(produtos_atuais, produtos_anteriores):
    return set(produtos_atuais) == set(produtos_anteriores)

async def run_terabyte_watcher():
    urls = [
        "http://3.12.26.127/diversos/open-box",
        "http://3.12.26.127/cadeira/cadeira-gamer",
        "http://3.12.26.127/cadeira/cadeira-office",
        "http://3.12.26.127/gabinetes",
        "http://3.12.26.127/monitores",
        "http://3.12.26.127/hardware/processadores",
        "http://3.12.26.127/kit-upgrade",
        "http://3.12.26.127/hardware/placas-de-video",
        "http://3.12.26.127/hardware/placas-mae",
        "http://3.12.26.127/perifericos/fone-de-ouvido",
        "http://3.12.26.127/perifericos/mouse",
        "http://3.12.26.127/perifericos/teclado",
        "http://3.12.26.127/perifericos/microfone",
        "http://3.12.26.127/hardware/memorias",
        "http://3.12.26.127/hardware/hard-disk",
        "http://3.12.26.127/hardware/fontes",
        "http://3.12.26.127/refrigeracao/watercooler",
    ]

    semaphore = Semaphore(3)  # Limita a 3 requisições simultâneas

    while True:
        start_time = time.time()
        tasks = []
        for url in urls:
            task = asyncio.create_task(process_url(url, semaphore))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        print(f"Tempo total de execução: {end_time - start_time:.2f} segundos")
        await asyncio.sleep(1)  # Espera 1 minuto antes de iniciar o próximo ciclo

async def process_url(url, semaphore):
    print(f"\nProcessando URL: {url}")
    pagina = 1
    produtos_anteriores = set()
    
    while True:
        print(f"\nProcessando página {pagina}")
        produtos_atuais = await buscar_dados_url_com_retentativa(url, semaphore, pagina)
        
        if not produtos_atuais:
            break
        
        if comparar_produtos(produtos_atuais, produtos_anteriores):
            print("Produtos repetidos detectados. Passando para a próxima URL.")
            break
        
        produtos_anteriores = set(produtos_atuais)
        pagina += 1
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_terabyte_watcher())
