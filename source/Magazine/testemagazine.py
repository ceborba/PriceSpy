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
        "page": 1,
        "path0": "monitores",
        "path1": "informatica",
        "path3": "in",
        "path4": "mlcd"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            print(f"Status Code: {response.status}")  # Exibe o status code
            
            data = await response.text()  # Obtém a resposta como string
            return data[:500]  # Retorna apenas os primeiros 500 caracteres

# Função para rodar o código assíncrono
async def run_async_code():
    data = await make_post_request()
    return data

# Executar o código
result = asyncio.run(run_async_code())
print(result)
