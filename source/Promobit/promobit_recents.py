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
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts
                      (id TEXT PRIMARY KEY, title TEXT, old_price REAL, 
                       current_price REAL, coupon TEXT, timestamp TEXT)''')
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
    return {
        'id': offer.get('offer_id'),
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
        INSERT INTO posts (id, title, old_price, current_price, coupon, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        (offer['id'], offer['title'], offer['old_price'] or 0, 
         offer['price'], offer['coupon'], offer['timestamp']))
    conn.commit()

def send_discord_notification(offer):
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    
    offer_link = f"https://www.promobit.com.br/oferta/{offer['offer_slug']}"
    
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
    
    webhook.add_embed(embed)
    webhook.execute()

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
