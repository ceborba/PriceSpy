import tls_client

url = "https://api.casasbahia.com.br/merchandising/oferta/v1/Preco/Produto/PrecoVenda/"
params = {
    "idRegiao": "",
    "idsProduto": "79722187,80421487,79929675,79701495,79689361,81802806,80882887,79838684,79703875,82188176,79702928,81888612,80655937,80882857,79701585,81974932,79929683,80882737,79701459,80725029",
    "composicao": "DescontoFormaPagamento,MelhoresParcelamentos",
    "apiKey": "d081fef8c2c44645bb082712ed32a047"
}

headers = {
    'sec-ch-ua-platform': '"Windows"',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="122", "Google Chrome";v="122", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'accept': '*/*',
    'origin': 'https://www.casasbahia.com.br',
    'sec-fetch-site': 'same-site',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://www.casasbahia.com.br/',
    'accept-encoding': 'gzip, deflate, br, zstd',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'priority': 'u=1, i'
}

# Criar uma sessão TLS
session = tls_client.Session(client_identifier="chrome_122", random_tls_extension_order=True)

# Fazer a requisição inicial
response = session.get(url, headers=headers, params=params)

print(f"Status: {response.status_code}")
# print(f"Response: {response.text}")

# Capturar os novos cookies
new_cookies = session.cookies.get_dict()
print("Novos Cookies:", new_cookies)

# Atualizar os cookies e enviar nova requisição
session.cookies.update(new_cookies)

response2 = session.get(url, headers=headers, params=params)
print(f"Status Segunda Requisição: {response2.status_code}")
# print(f"Response Segunda Requisição: {response2.text}")
data = response.json()

# Extrair e imprimir informações de cada produto
for produto in data['PrecoProdutos']:
    print(f"Produto ID: {produto['PrecoVenda']['IdSku']}")
    print(f"Preço: R$ {produto['PrecoVenda']['Preco']:.2f}")
    print(f"Desconto PIX: {produto['DescontoFormaPagamento']['PercentualDesconto']}%")
    print(f"Preço com desconto PIX: R$ {produto['DescontoFormaPagamento']['PrecoVendaComDesconto']:.2f}")
    print("Opções de Parcelamento:")
    for parcelamento in produto['MelhoresParcelamentos']:
        print(f"  {parcelamento['QtdParcela']}x de R$ {parcelamento['ValorParcela']:.2f}")
    print("-" * 30)