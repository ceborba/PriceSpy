import json
import base64
import random
import aiohttp
import asyncio

def random_string(length=5):
    return ''.join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length))

class VariablesQuery:
    def __init__(self, props, per_page):
        self.HideUnavailableItems = True
        self.SkusFilter = "ALL_AVAILABLE"
        self.SimulationBehavior = "default"
        self.InstallmentCriteria = "MAX_WITHOUT_INTEREST"
        self.ProductOriginVtex = False
        self.Map = "c"
        self.Query = props["Category"]
        self.OrderBy = "OrderByBestDiscountDESC"
        self.From = per_page * (props["Page"] - 1)
        self.To = per_page * props["Page"]
        self.SelectedFacets = [{"Key": "c", "Value": props["Category"]}]
        self.FacetsBehavior = "Dynamic"
        self.CategoryTreeBehavior = "default"
        self.WithFacets = False
        self.Variant = "null-null"
        self.AdvertisementOptions = {
            "ShowSponsored": False,
            "SponsoredCount": 3,
            "AdvertisementPlacement": "top_search",
            "RepeatSponsoredProducts": True
        }
        self.Page = props["Page"]
        self.NextPage = props["Page"] + 1
        self.PreviousPage = props["Page"] - 1

async def fetch_data(props, per_page):
    # Criando o objeto da query
    variables = VariablesQuery(props, per_page).__dict__

    try:
        json_bytes = json.dumps(variables).encode('utf-8')
        base64_string = base64.b64encode(json_bytes).decode('utf-8')
    except Exception as e:
        print("Erro ao serializar VariablesQuery:", e)
        return None, e

    # Criando a extensão JSON
    extensions = {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "9177ba6f883473505dc99fcf2b679a6e270af6320a157f0798b92efeab98d5d3",
            "sender": "vtex.store-resources@0.x",
            "provider": "vtex.search-graphql@0.x"
        },
        "variables": base64_string
    }

    # Construindo a URL base
    url = "https://www.carrefour.com.br/_v/segment/graphql/v1"

    # Criando os headers
    headers = {
        "Sec-Ch-Ua-Platform": '"macOS"',
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "Content-Type": "application/json",
        "Dnt": "1",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.carrefour.com.br/automotivo/autopecas?initialMap=c&initialQuery=automotivo&map=category-1,category-2",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Priority": "u=1, i"
    }

    # Criando o corpo da requisição
    payload = {
        "query": "",
        "variables": {},
        "extensions": extensions
    }

    # Criando a requisição assíncrona com aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                return await response.text()
        except Exception as e:
            return None, e

# Função para extrair os dados formatados
def extract_product_data(json_data):
    try:
        data = json.loads(json_data)
        products = data['data']['productSearch']['products']

        product_list = []
        for product in products:
            product_info = {
                'Nome': product['productName'],
                'Link': product['link'],
                'Quantidade': len(product['items']),  # Assuming 'items' represents quantity
                'Valor': product['priceRange']['sellingPrice']['lowPrice'],
            }

            # Extract variations if available
            if product['skuSpecifications']:
                variations = {}
                for spec in product['skuSpecifications']:
                    variations[spec['name']] = [v['name'] for v in spec['values']]
                product_info['Variações'] = variations

            product_list.append(product_info)

        return product_list
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Erro ao processar o JSON: {e}")
        return None

# Exemplo de uso
async def main():
    props = {"Category": "autopecas", "Page": 1}
    per_page = 10
    
    response = await fetch_data(props, per_page)

    if response:
        product_data = extract_product_data(response)
        if product_data:
            for product in product_data:
                print(json.dumps(product, indent=4, ensure_ascii=False)) # Printa formatado
        else:
            print("Não foi possível extrair os dados dos produtos.")
    else:
        print("Erro na requisição:", response)

# Executando o código assíncrono
asyncio.run(main())
