import aiohttp
import asyncio
import json
from datetime import datetime

async def monitor_csgo_items():
    url = "https://csgoempire.com/api/v2/trading/items"
    
    headers = {
        "authority": "csgoempire.com",
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "referer": "https://csgoempire.com/withdraw/steam/market",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not?A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    params = {
        "per_page": 160,
        "page": 1,
        "wear_min": 0,
        "wear_max": 0.07,
        "wear_names[]": "Factory New",
        "price_max_above": 15,
        "delivery_time_long_max": 720,
        "auction": "yes",
        "sort": "desc",
        "order": "market_value"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('success'):
                            process_items(data['data'])
                    else:
                        print(f"Erro na requisição: {response.status}")
            except Exception as e:
                print(f"Erro ao fazer a requisição: {e}")
            
            await asyncio.sleep(1)

def process_items(items):
    print("\n=== Itens Disponíveis ===")
    print(f"Atualizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    for item in items:
        nome = item.get('market_name', 'Nome não disponível')
        valor = item.get('market_value', 0)
        valor_sugerido = item.get('suggested_price', 0)
        wear = item.get('wear', 'N/A')
        
        print(f"Nome: {nome}")
        print(f"Valor: ${valor/100:.2f}")
        print(f"Valor Sugerido: ${valor_sugerido/100:.2f}")
        print(f"Wear: {wear}")
        print("-" * 50)

async def main():
    await monitor_csgo_items()

if __name__ == "__main__":
    asyncio.run(main())
