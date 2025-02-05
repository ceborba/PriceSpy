import aiohttp
import asyncio
from datetime import datetime
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROMOBIT_API_URL = 'https://api.promobit.com.br/offers/recents'
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1329907475524227143/Q3EM-wdqi9i8ko1k8imnY-BqzL_Fceho7LulmSse703VhlkKfEFC4hswucM68s-zwIiD'

def get_db_connection():
    conn = sqlite3.connect('promobit_monitor.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS posts
                   (id TEXT PRIMARY KEY,
                   title TEXT, old_price REAL, 
                   current_price REAL,
                   coupon TEXT,
                   photo TEXT,
                   timestamp TEXT
                   )
                   ''')
    conn.commit()
    return conn, cursor

async def fetch_posts(session):
    params = {
        'sort': 'latest',
        'limit': 24
    }
    async with session.get(PROMOBIT_API_URL, params=params) as response:
        if response.status == 200:
            data = await response.json()
            return data.get('offers', [])
        return []

def extract_offer_info(offer):
    base_url = "https://www.promobit.com.br"
    photo_url = offer.get('offer_photo', '')
    
    # Verifica se a foto já começa com /static/p/
    if photo_url and not photo_url.startswith('/static/p/'):
        photo_url = f"/static/p{photo_url}" if photo_url.startswith('/') else f"/static/p/{photo_url}"
    
    return {
        'id': offer.get('offer_id'),
        'photo': f"{base_url}{photo_url}" if photo_url else None,
        'title': offer.get('offer_title'),
        'old_price': offer.get('offer_old_price'),
        'price': offer.get('offer_price'),
        'coupon': offer.get('offer_coupon'),
        'timestamp': offer.get('offer_published'),
        'offer_slug': offer.get('offer_slug')
    }

def is_new_post(cursor, offer_id):
    cursor.execute("SELECT * FROM posts WHERE id = ?", (offer_id,))
    return cursor.fetchone() is None

def save_post(conn, cursor, offer):
    cursor.execute("""
        INSERT INTO posts (id, title, old_price, current_price, coupon, photo, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (offer['id'], offer['title'], offer['old_price'] or 0, 
         offer['price'], offer['coupon'], offer['photo'], offer['timestamp']))
    conn.commit()


def normalize_photo_url(url):
    if not url:
        return None
        
    base_url = "https://www.promobit.com.br"
    
    # Remove base URL se já existir
    if url.startswith(base_url):
        url = url.replace(base_url, '')
    
    # Adiciona /static/p/ se necessário
    if not url.startswith('/static/p/') and not url.startswith('/static/'):
        url = f"/static/p{url}" if url.startswith('/') else f"/static/p/{url}"
    
    return f"{base_url}{url}"


def send_discord_notification(offer):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    
    offer_link = f"https://www.promobit.com.br/oferta/{offer['offer_slug']}"
    offer_img = offer['photo']
    
    logging.debug(f"URL da imagem: {offer_img}")
    
    description = f"Novo Preço: R$ {offer['price']}\n"
    if offer['old_price']:
        description = f"Antigo Preço: R$ {offer['old_price']}\n" + description
    if offer['coupon']:
        description += f"Cupom: {offer['coupon']}\n"
    if offer['offer_slug']:
        description += f"\n🔗 Link: {offer_link}"

    title = f"[PROMOBIT] {offer['title']}"

    embed = DiscordEmbed(
        title=title,
        description=description,
        color='03b2f8'
    )
    embed.set_timestamp()

    if offer_img:
        try:
            embed.set_image(url=offer_img)
        except Exception as e:
            logging.error(f"Erro ao definir imagem: {str(e)}")
            logging.error(f"URL problemática: {offer_img}")
    
    webhook.add_embed(embed)
    response = webhook.execute()
    
    if response.status_code != 200:
        logging.error(f"Erro ao enviar webhook: {response.status_code}")

async def monitor_promobit():
    conn, cursor = get_db_connection()
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    offers = await fetch_posts(session)
                    
                    for offer_data in offers:
                        offer = extract_offer_info(offer_data)
                        if is_new_post(cursor, offer['id']):
                            logging.info(f"Nova oferta encontrada: {offer['title']}")
                            save_post(conn, cursor, offer)
                            send_discord_notification(offer)
                    
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"Erro ao monitorar: {str(e)}")
                    await asyncio.sleep(1)
    finally:
        conn.close()

if __name__ == '__main__':
    asyncio.run(monitor_promobit())
