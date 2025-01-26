import httpx
import asyncio
import json

async def fetch_data():
    url = "https://www.nike.com.br/_next/data/v11-32-3/snkrs/estoque.json"
    headers = {
        "path": "/_next/data/v11-30-0/snkrs/estoque.json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "x-nextjs-data": "1",  # Garantir que este cabeçalho esteja presente
        "sec-fetch-mode": "cors",
        "referer": "https://www.nike.com.br/snkrs",
        "authority": "www.nike.com.br",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd"
    }

    async with httpx.AsyncClient(http2=True) as client:
        response = await client.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")

        if response.status_code == 200:
            # Extrair cookies da resposta
            cookies = response.cookies.jar
            # Retornar dados e cookies
            return response.json(), cookies
        else:
            return None, None

async def make_new_request(cookies):
    url = "https://www.nike.com.br/_next/data/v11-32-3/snkrs/estoque.json"
    headers = {
        "path": "/_next/data/v11-30-0/snkrs/estoque.json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "x-nextjs-data": "1",  
        "referer": "https://www.nike.com.br/snkrs",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd"
    }

    async with httpx.AsyncClient(http2=True, cookies=cookies) as client:
        response = await client.get(url, headers=headers)
        print(f"New Request Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Nova requisição bem-sucedida!")
            products = response.json().get('pageProps', {}).get('dehydratedState', {}).get('queries', [{}])[0].get('state', {}).get('data', {}).get('pages', [{}])[0].get('products', [])
            result = [{
                "name": product.get('name'),
                "url": f"https://www.nike.com.br{product.get('url')}",  # Modificar a URL
                "price": product.get('price'),
                "oldPrice": product.get('oldPrice')
            } for product in products]
            return result
        else:
            print("Falha na nova requisição.")
            return None

async def main():
    data, cookies = await fetch_data()
    if data:
        print("Dados da primeira requisição processados!")
        # Fazer uma nova requisição com os cookies
        new_data = await make_new_request(cookies)
        if new_data:
            print("Nova requisição realizada com sucesso:")
            print(json.dumps(new_data, indent=2, ensure_ascii=False))
        else:
            print("Falha ao processar nova requisição.")
    else:
        print("Falha ao obter dados iniciais.")

if __name__ == "__main__":
    asyncio.run(main())
