import asyncio
import threading
from watcherPichau import run_pichau_watcher1
from watcherPichau2 import run_pichau_watcher2
from watcherPichau3 import run_pichau_watcher3
from watcherPichau4 import run_pichau_watcher4
from watcherPichau5 import run_pichau_watcher5
from watcherPichau6 import run_pichau_watcher6
from watcherPichau7 import run_pichau_watcher7
from watcherPichau8 import run_pichau_watcher8

def run_pichau1():
    asyncio.run(run_pichau_watcher1())

def run_pichau2():
    asyncio.run(run_pichau_watcher2())

def run_pichau3():
    asyncio.run(run_pichau_watcher3())

def run_pichau4():
    asyncio.run(run_pichau_watcher4())

def run_pichau5():
    asyncio.run(run_pichau_watcher5())

def run_pichau6():
    asyncio.run(run_pichau_watcher6())

def run_pichau7():
    asyncio.run(run_pichau_watcher7())

def run_pichau8():
    asyncio.run(run_pichau_watcher8())

if __name__ == "__main__":
    # Cria e inicia a thread para o watcher da Pichau
    pichau_thread1 = threading.Thread(target=run_pichau1)
    pichau_thread1.start()

    pichau_thread2 = threading.Thread(target=run_pichau2)
    pichau_thread2.start()

    pichau_thread3 = threading.Thread(target=run_pichau3)
    pichau_thread3.start()

    pichau_thread4 = threading.Thread(target=run_pichau4)
    pichau_thread4.start()

    pichau_thread5 = threading.Thread(target=run_pichau5)
    pichau_thread5.start()

    pichau_thread6 = threading.Thread(target=run_pichau6)
    pichau_thread6.start()

    pichau_thread7 = threading.Thread(target=run_pichau7)
    pichau_thread7.start()

    pichau_thread8 = threading.Thread(target=run_pichau8)
    pichau_thread8.start()



    pichau_thread1.join()
    pichau_thread2.join()
    pichau_thread3.join()
    pichau_thread4.join()
    pichau_thread5.join()
    pichau_thread6.join()
    pichau_thread7.join()
    pichau_thread8.join()
