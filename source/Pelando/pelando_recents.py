import aiohttp
import asyncio
from datetime import datetime, UTC
import logging
import sqlite3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def adapt_datetime(dt):
    return dt.isoformat()

sqlite3.register_adapter(datetime, adapt_datetime)

async def get_db_connection():
    conn = sqlite3.connect('pelando_monitor.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            title TEXT,
            price REAL,
            url TEXT,
            image_url TEXT,
            timestamp DATETIME,
            couponCode TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1329907475524227143/Q3EM-wdqi9i8ko1k8imnY-BqzL_Fceho7LulmSse703VhlkKfEFC4hswucM68s-zwIiD"
API_URL = "https://www.pelando.com.br/api/graphql"

async def fetch_recent_posts(session):
    query = """
    query RecentOffersQuery($limit:Int$after:String$filters:OfferFilterOptions$page:Int){
        public{
            recentOffers(limit:$limit,after:$after,filters:$filters,page:$page){
                edges{
                    id
                    couponCode
                    sourceUrl
                    status
                    title
                    price
                    image {
                        url(height: 238)
                    }
                }
            }
        }
    }
    """
    
    variables = {"limit": 30}
    payload = {
        "query": query,
        "variables": variables
    }
    
    async with session.post(API_URL, json=payload) as response:
        if response.status == 200:
            data = await response.json()
            return data['data']['public']['recentOffers']['edges']
        else:
            logging.error(f"Falha ao acessar a API. Status: {response.status}")
            return []

async def check_new_posts():
    async with aiohttp.ClientSession() as session:
        conn, cursor = await get_db_connection()
        try:
            while True:
                try:
                    posts = await fetch_recent_posts(session)
                    for post in posts:
                        cursor.execute("SELECT id FROM posts WHERE id = ?", (post['id'],))
                        if cursor.fetchone() is None:
                            cursor.execute(
                                """INSERT INTO posts 
                                (id, title, price, url, image_url, timestamp, couponCode, status) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    post['id'],
                                    post['title'],
                                    post.get('price'),
                                    post['sourceUrl'],
                                    post['image']['url'] if post.get('image') and post['image'].get('url') else None,
                                    datetime.now(UTC),
                                    post.get('couponCode'),
                                    post['status']
                                )
                            )
                            conn.commit()
                            logging.info(f"Novo post encontrado: {post['title']}")
                            await send_discord_notification(post)
                except Exception as e:
                    logging.error(f"Erro ao verificar novos posts: {e}")
                await asyncio.sleep(1)
        finally:
            conn.close()

async def send_discord_notification(post):
    async with aiohttp.ClientSession() as session:
        webhook_data = {
            "embeds": [{
                "title": f"[PELANDO] {post['title']}",
                "description": "",
                "color": 0x03b2f8,
                "timestamp": datetime.now(UTC).isoformat(),
                "image": {"url": post['image']['url']} if post.get('image') and post['image'].get('url') else None
            }]
        }

        if post.get('price'):
            webhook_data['embeds'][0]['description'] += f"Novo Preço: R$ {post['price']:.2f}\n"
        if post.get('old_price'):
            webhook_data['embeds'][0]['description'] = f"Antigo Preço: R$ {post['old_price']:.2f}\n" + webhook_data['embeds'][0]['description']
        if post.get('couponCode'):
            webhook_data['embeds'][0]['description'] += f"Cupom: {post['couponCode']}\n"
        if post.get('sourceUrl'):
            webhook_data['embeds'][0]['description'] += f"\n🔗 Link: {post['sourceUrl']}"

        async with session.post(DISCORD_WEBHOOK_URL, json=webhook_data) as response:
            if response.status != 204:
                logging.error(f"Falha ao enviar notificação para o Discord. Status: {response.status}")

async def monitor_pelando():
    try:
        await check_new_posts()
    except KeyboardInterrupt:
        logging.info("Monitoramento interrompido pelo usuário")

if __name__ == "__main__":
    asyncio.run(monitor_pelando())
