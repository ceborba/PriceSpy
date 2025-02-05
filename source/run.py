import asyncio
import logging
import threading
from Pelando.pelando_recents import monitor_pelando
from Promobit.promobit_recents import monitor_promobit
from Americanas.americanas import monitor_americanas
from amazon.amazon_dia import make_requests
from amazon.amazon_all import make_requests_hardware
from EletroClub.eletroclub import monitor_eletroclub
from BelezaNaWeb.beleza_na_web import monitor_belezanaweb
from casasBahia.casasbahia import monitor_casasbahia
from ShopClub.shopclub import monitor_shopclub
from casasBahia.extra import monitor_extra
from casasBahia.pontofrio import monitor_pontofrio
from vestuario.artwalk import monitor_artwalk
from vestuario.authenticfeet import monitor_authenticfeet
from vestuario.magicfeet import monitor_magicfeet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_promobit():
    logging.info(f"Iniciando a thread para PROMOBIT, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_promobit())

def run_pelando():
    logging.info(f"Iniciando a thread para PELANDO, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_pelando())

def run_americanas():
    logging.info(f"Iniciando a thread para AMERICANAS, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_americanas())

def run_amazon():
    logging.info(f"Iniciando a thread para AMAZON - DIA, Thread ID: {threading.get_ident()}")
    asyncio.run(make_requests())

def run_amazon_all():
    logging.info(f"Iniciando a thread para AMAZON - HARDWARE/TECNOLOGIA, Thread ID: {threading.get_ident()}")
    asyncio.run(make_requests_hardware())

# def run_eletroclub():
#     logging.info(f"Iniciando a thread para EletroClub , Thread ID: {threading.get_ident()}")
#     asyncio.run(monitor_eletroclub())

def run_belezanaweb():
    logging.info(f"Iniciando a thread para Beleza Na Web , Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_belezanaweb())

# def run_embalados_casasbahia():
#     logging.info(f"Iniciando a thread para Casas Bahia , Thread ID: {threading.get_ident()}")
#     asyncio.run(monitor_casasbahia())

# def run_embalados_extra():
#     logging.info(f"Iniciando a thread para Extra, Thread ID: {threading.get_ident()}")
#     asyncio.run(monitor_extra())

# def run_embalados_pontofrio():
#     logging.info(f"Iniciando a thread para Ponto Frio, Thread ID: {threading.get_ident()}")
#     asyncio.run(monitor_pontofrio())

def run_embalados_shopclub():
    logging.info(f"Iniciando a thread para ShopClub, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_shopclub())

def run_artwalk():
    logging.info(f"Iniciando a thread para ArtWalk, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_artwalk())

def run_authenticfeet():
    logging.info(f"Iniciando a thread para AuthenticFeet, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_authenticfeet())

def run_magicfeet():
    logging.info(f"Iniciando a thread para MagicFeet, Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_magicfeet())



if __name__ == "__main__":
    try:
        promobit_thread = threading.Thread(target=run_promobit)
        promobit_thread.start()

        pelando_thread = threading.Thread(target=run_pelando)
        pelando_thread.start()

        americanas_thread = threading.Thread(target=run_americanas)
        americanas_thread.start()

        amazon_thread = threading.Thread(target=run_amazon)
        amazon_thread.start()

        amazon_all_thread = threading.Thread(target=run_amazon_all)
        amazon_all_thread.start()

        # eletroclub_thread = threading.Thread(target=run_eletroclub)
        # eletroclub_thread.start()

        belezanaweb_thread = threading.Thread(target=run_belezanaweb)
        belezanaweb_thread.start()

        # embalados_thread = threading.Thread(target=run_embalados_casasbahia)
        # embalados_thread.start()

        # embalados_pf_thread = threading.Thread(target=run_embalados_pontofrio)
        # embalados_pf_thread.start()

        embalados_shopclub_thread = threading.Thread(target=run_embalados_shopclub)
        embalados_shopclub_thread.start()

        # embalados_extra_thread = threading.Thread(target=run_embalados_extra)
        # embalados_extra_thread.start()

        artwalk_thread = threading.Thread(target=run_artwalk)
        artwalk_thread.start()

        authenticfeet_thread = threading.Thread(target=run_authenticfeet)
        authenticfeet_thread.start()

        magicfeet_thread = threading.Thread(target=run_magicfeet)
        magicfeet_thread.start()

        promobit_thread.join()
        pelando_thread.join()
        americanas_thread.join()
        amazon_thread.join()
        amazon_all_thread.join()
        # eletroclub_thread.join()
        belezanaweb_thread.join()
        # embalados_extra_thread.join()
        # embalados_thread.join()
        # embalados_pf_thread.join()
        embalados_shopclub_thread.join()
        artwalk_thread.join()
        authenticfeet_thread.join()
        magicfeet_thread.join()

    except: 
        logging.info("Execução interrompida pelo usúario")
