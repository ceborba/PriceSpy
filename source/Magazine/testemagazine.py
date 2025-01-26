import nest_asyncio
import aiohttp
import asyncio
import json

# Permitir que o loop do asyncio seja reutilizado
nest_asyncio.apply()

async def make_post_request():
    url = "https://www.magazineluiza.com.br/_next/data/V6doRLyMk5tkdAJ9aJ-XO/monitores/informatica/s/in/mlcd.json?"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    params = {
        "page": 2,
        "path0": "monitores",
        "path1": "informatica",
        "path3": "in",
        "path4": "mlcd"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                return {"error": f"Erro na requisição: {response.status}", "details": await response.text()}

def extract_product_info(data):
    products = data.get('pageProps', {}).get('data', {}).get('search', {}).get('products', [])

    extracted_data = []
    for product in products:
        id = product.get('path')
        title = product.get('title')

        # Extraindo o preço correto a partir da estrutura fornecida
        price_info = product.get('price', {})
        price = price_info.get('bestPrice')

        extracted_data.append({
            "Link": f"https://www.magazineluiza.com.br/{id}",
            "Título": title,
            "Melhor Preço": f"R$ {price}" if price else "Não disponível"
        })
    return extracted_data

# Função para rodar o código assíncrono
async def run_async_code():
    data = await make_post_request()
    if "error" in data:
        return data
    return extract_product_info(data)

# Executar o código
result = asyncio.run(run_async_code())
print(json.dumps(result, ensure_ascii=False, indent=2))
