import nest_asyncio
import aiohttp
import asyncio
import json

nest_asyncio.apply()

async def make_get_request(page):
    url = "https://www.magazineluiza.com.br/_next/data/V6doRLyMk5tkdAJ9aJ-XO/monitores/informatica/s/in/mlcd.json"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    params = {
        "page": page,
        "path0": "monitores",
        "path1": "informatica",
        "path3": "in",
        "path4": "mlcd"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"Erro na requisição: {response.status}", "details": await response.text()}

def extract_product_info(data):
    products = data.get('pageProps', {}).get('data', {}).get('search', {}).get('products', [])
    total_count = data.get('pageProps', {}).get('data', {}).get('search', {}).get('totalCount', 0)

    extracted_data = []
    for product in products:
        id = product.get('id')
        title = product.get('title')
        price_info = product.get('price', {})
        price = price_info.get('bestPrice')
        quantity = product.get('stock', {}).get('quantity', 0)
        link = f"https://www.magazineluiza.com.br/{product.get('path')}"

        extracted_data.append({
            "ID": id,
            "Título": title,
            "Melhor Preço": f"R$ {price}" if price else "Não disponível",
            "Quantidade": quantity,
            "Link": link
        })
    
    return extracted_data, total_count

async def fetch_all_pages():
    all_products = []
    page = 2
    total_count = 0

    while True:
        data = await make_get_request(page)
        if "error" in data:
            print(f"Erro na página {page}: {data['error']}")
            break

        products, total_count = extract_product_info(data)
        all_products.extend(products)

        if len(all_products) >= total_count:
            break

        page += 1

    return all_products, total_count

async def run_async_code():
    products, total_count = await fetch_all_pages()
    return {
        "total_products": total_count,
        "products": products
    }

result = asyncio.run(run_async_code())
print(json.dumps(result, ensure_ascii=False, indent=2))
