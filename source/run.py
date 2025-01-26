import asyncio
import logging
import threading
from Pelando.pelando_recents import monitor_pelando
from Promobit.promobit_recents import monitor_promobit
from Americanas.americanas import monitor_americanas
from amazon.amazon_dia import make_requests
from amazon.amazon_all import make_requests_hardware
from EletroClub.eletroclub import monitor_eletroclub

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

# def run_amazon_all():
#     logging.info(f"Iniciando a thread para AMAZON - HARDWARE/TECNOLOGIA, Thread ID: {threading.get_ident()}")
#     asyncio.run(make_requests_hardware())

def run_eletroclub():
    logging.info(f"Iniciando a thread para ELETROCLUB , Thread ID: {threading.get_ident()}")
    asyncio.run(monitor_eletroclub())



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

        # amazon_all_thread = threading.Thread(target=run_amazon_all)
        # amazon_all_thread.start()

        eletroclub_thread = threading.Thread(target=run_eletroclub)
        eletroclub_thread.start()

        promobit_thread.join()
        pelando_thread.join()
        americanas_thread.join()
        amazon_thread.join()
        # amazon_all_thread.join()
        eletroclub_thread.join()

        
    except: 
        logging.info("Execução interrompida pelo usúario")
