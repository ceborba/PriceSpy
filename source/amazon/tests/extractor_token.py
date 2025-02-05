from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import re

# Configurar o WebDriver
chrome_options = Options()
chrome_options.add_argument("--headless")  # Para executar em segundo plano
driver = webdriver.Chrome(options=chrome_options)

# Acessar a página
url = "https://www.amazon.com.br/gp/goldbox"
driver.get(url)

# Capturar o conteúdo do meta tag
encrypted_token = driver.find_element(By.CSS_SELECTOR, "meta[name='encrypted-slate-token']").get_attribute("content")
print(f"Encrypted Token: {encrypted_token}")

page_source = driver.page_source

csrf_token_match = re.search(r'"csrfToken":\s*"([^"]+)"', page_source)
if csrf_token_match:
    csrf_token = csrf_token_match.group(1)
    print(f"CSRF Token: {csrf_token}")
else:
    print("CSRF Token não encontrado!")

driver.quit()
