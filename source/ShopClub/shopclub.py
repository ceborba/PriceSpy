import aiohttp
import asyncio
import json
from datetime import datetime
import sqlite3
import logging
from discord_webhook import DiscordWebhook, DiscordEmbed


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calcular_desconto(preco_antigo, preco_novo):
    if preco_antigo == 0:
        return 0
    preco_antigo = float(preco_antigo) if isinstance(preco_antigo, str) else preco_antigo
    preco_novo = float(preco_novo) if isinstance(preco_novo, str) else preco_novo
    desconto = ((preco_antigo - preco_novo) / preco_antigo) * 100
    return f"{desconto:.2f}"

class ShopClubMonitor:
    def __init__(self):
        self.base_url = "https://www.shopclub.com.br/_v/segment/graphql/v1"
        self.variables = [
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6dHJ1ZSwic2t1c0ZpbHRlciI6IkFMTF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6InByb2R1Y3RDbHVzdGVySWRzIiwicXVlcnkiOiIxOTUzIiwib3JkZXJCeSI6Ik9yZGVyQnlSZWxlYXNlRGF0ZURFU0MiLCJmcm9tIjowLCJ0byI6MjMsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJwcm9kdWN0Q2x1c3RlcklkcyIsInZhbHVlIjoiMTk1MyJ9XSwiZmFjZXRzQmVoYXZpb3IiOiJTdGF0aWMiLCJ3aXRoRmFjZXRzIjpmYWxzZSwiYWR2ZXJ0aXNlbWVudE9wdGlvbnMiOnsic2hvd1Nwb25zb3JlZCI6dHJ1ZSwic3BvbnNvcmVkQ291bnQiOjMsImFkdmVydGlzZW1lbnRQbGFjZW1lbnQiOiJ0b3Bfc2VhcmNoIiwicmVwZWF0U3BvbnNvcmVkUHJvZHVjdHMiOnRydWV9fQ",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6dHJ1ZSwic2t1c0ZpbHRlciI6IkFMTF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6InByb2R1Y3RDbHVzdGVySWRzIiwicXVlcnkiOiIxOTUzIiwib3JkZXJCeSI6Ik9yZGVyQnlSZWxlYXNlRGF0ZURFU0MiLCJmcm9tIjoyNCwidG8iOjQ3LCJzZWxlY3RlZEZhY2V0cyI6W3sia2V5IjoicHJvZHVjdENsdXN0ZXJJZHMiLCJ2YWx1ZSI6IjE5NTMifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeUJlc3REaXNjb3VudERFU0MiLCJmcm9tIjowLCJ0byI6MTEsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeUJlc3REaXNjb3VudERFU0MiLCJmcm9tIjoxMiwidG8iOjIzLCJzZWxlY3RlZEZhY2V0cyI6W3sia2V5IjoiYyIsInZhbHVlIjoiZWxldHJvZG9tZXN0aWNvcyJ9XSwib3BlcmF0b3IiOiJhbmQiLCJmdXp6eSI6IjAiLCJzZWFyY2hTdGF0ZSI6bnVsbCwiZmFjZXRzQmVoYXZpb3IiOiJTdGF0aWMiLCJjYXRlZ29yeVRyZWVCZWhhdmlvciI6ImRlZmF1bHQiLCJ3aXRoRmFjZXRzIjpmYWxzZSwiYWR2ZXJ0aXNlbWVudE9wdGlvbnMiOnsic2hvd1Nwb25zb3JlZCI6dHJ1ZSwic3BvbnNvcmVkQ291bnQiOjMsImFkdmVydGlzZW1lbnRQbGFjZW1lbnQiOiJ0b3Bfc2VhcmNoIiwicmVwZWF0U3BvbnNvcmVkUHJvZHVjdHMiOnRydWV9fQ",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjEyLCJ0byI6MjMsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjI0LCJ0byI6MzUsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjM2LCJ0byI6NDcsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjQ4LCJ0byI6NTksInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjYwLCJ0byI6NzEsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjcyLCJ0byI6ODMsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjg0LCJ0byI6OTUsInNlbGVjdGVkRmFjZXRzIjpbeyJrZXkiOiJjIiwidmFsdWUiOiJlbGV0cm9kb21lc3RpY29zIn1dLCJvcGVyYXRvciI6ImFuZCIsImZ1enp5IjoiMCIsInNlYXJjaFN0YXRlIjpudWxsLCJmYWNldHNCZWhhdmlvciI6IlN0YXRpYyIsImNhdGVnb3J5VHJlZUJlaGF2aW9yIjoiZGVmYXVsdCIsIndpdGhGYWNldHMiOmZhbHNlLCJhZHZlcnRpc2VtZW50T3B0aW9ucyI6eyJzaG93U3BvbnNvcmVkIjp0cnVlLCJzcG9uc29yZWRDb3VudCI6MywiYWR2ZXJ0aXNlbWVudFBsYWNlbWVudCI6InRvcF9zZWFyY2giLCJyZXBlYXRTcG9uc29yZWRQcm9kdWN0cyI6dHJ1ZX19",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjk2LCJ0byI6MTA3LCJzZWxlY3RlZEZhY2V0cyI6W3sia2V5IjoiYyIsInZhbHVlIjoiZWxldHJvZG9tZXN0aWNvcyJ9XSwib3BlcmF0b3IiOiJhbmQiLCJmdXp6eSI6IjAiLCJzZWFyY2hTdGF0ZSI6bnVsbCwiZmFjZXRzQmVoYXZpb3IiOiJTdGF0aWMiLCJjYXRlZ29yeVRyZWVCZWhhdmlvciI6ImRlZmF1bHQiLCJ3aXRoRmFjZXRzIjpmYWxzZSwiYWR2ZXJ0aXNlbWVudE9wdGlvbnMiOnsic2hvd1Nwb25zb3JlZCI6dHJ1ZSwic3BvbnNvcmVkQ291bnQiOjMsImFkdmVydGlzZW1lbnRQbGFjZW1lbnQiOiJ0b3Bfc2VhcmNoIiwicmVwZWF0U3BvbnNvcmVkUHJvZHVjdHMiOnRydWV9fQ",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjIyOCwidG8iOjIzOSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjI0MCwidG8iOjI1MSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjI1MiwidG8iOjI2Mywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjI2NCwidG8iOjI3NSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjI3NiwidG8iOjI4Nywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjI4OCwidG8iOjI5OSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjMwMCwidG8iOjMxMSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjMxMiwidG8iOjMyMywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjMyNCwidG8iOjMzNSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjMzNiwidG8iOjM0Nywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjM0OCwidG8iOjM1OSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjM2MCwidG8iOjM3MSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjM3MiwidG8iOjM4Mywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjM4NCwidG8iOjM5NSwic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
                "eyJoaWRlVW5hdmFpbGFibGVJdGVtcyI6ZmFsc2UsInNrdXNGaWx0ZXIiOiJGSVJTVF9BVkFJTEFCTEUiLCJzaW11bGF0aW9uQmVoYXZpb3IiOiJkZWZhdWx0IiwiaW5zdGFsbG1lbnRDcml0ZXJpYSI6Ik1BWF9XSVRIT1VUX0lOVEVSRVNUIiwicHJvZHVjdE9yaWdpblZ0ZXgiOnRydWUsIm1hcCI6ImMiLCJxdWVyeSI6ImVsZXRyb2RvbWVzdGljb3MiLCJvcmRlckJ5IjoiT3JkZXJCeVJlbGVhc2VEYXRlREVTQyIsImZyb20iOjM5NiwidG8iOjQwNywic2VsZWN0ZWRGYWNldHMiOlt7ImtleSI6ImMiLCJ2YWx1ZSI6ImVsZXRyb2RvbWVzdGljb3MifV0sIm9wZXJhdG9yIjoiYW5kIiwiZnV6enkiOiIwIiwic2VhcmNoU3RhdGUiOm51bGwsImZhY2V0c0JlaGF2aW9yIjoiU3RhdGljIiwiY2F0ZWdvcnlUcmVlQmVoYXZpb3IiOiJkZWZhdWx0Iiwid2l0aEZhY2V0cyI6ZmFsc2UsImFkdmVydGlzZW1lbnRPcHRpb25zIjp7InNob3dTcG9uc29yZWQiOnRydWUsInNwb25zb3JlZENvdW50IjozLCJhZHZlcnRpc2VtZW50UGxhY2VtZW50IjoidG9wX3NlYXJjaCIsInJlcGVhdFNwb25zb3JlZFByb2R1Y3RzIjp0cnVlfX0",
            ]
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "referer": "https://www.shopclub.com.br/bbb",
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        }
        self.conn = self.create_db()
            
    def create_db(self):
        conn = sqlite3.connect('productsShopClub.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productsShopClub (
                id TEXT PRIMARY KEY,
                name TEXT,
                url_key TEXT,
                price_discount REAL,
                price_promotional REAL,
                new_price REAL,
                condition TEXT,
                garantia TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id TEXT,
                name TEXT,
                price REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            )
        ''')
        conn.commit()
        return conn
    

    def atualizar_preco(self, item_id, nome, preco_atual, link, preco_desc=None, condition=None, garantia=None, quantidade_disponivel=0):

        preco_atual = preco_atual or 0
        preco_desc = preco_desc or 0

        cursor = self.conn.cursor()
        cursor.execute("SELECT price_promotional, name FROM productsShopClub WHERE id = ?", (item_id,))
        result = cursor.fetchone()

        if result:
            preco_antigo, nome_antigo = result
            preco_antigo = preco_antigo or 0
            mudancas = []
            if preco_atual != preco_antigo:
                mudancas.append(f"Preço: {float(preco_antigo):.2f} -> {float(preco_atual):.2f}")
            if nome != nome_antigo:
                mudancas.append(f"Nome: '{nome_antigo}' -> '{nome}'")

            if mudancas:
                cursor.execute('''
                    UPDATE productsShopClub
                    SET price_promotional = ?, price_discount = ?, name = ?, condition = ?, garantia = ?
                    WHERE id = ?
                ''', (preco_atual, preco_desc, nome, condition, garantia, item_id))

                cursor.execute('''
                    INSERT OR REPLACE INTO price_history (id, name, price)
                    VALUES (?, ?, ?)
                ''', (item_id, nome, preco_atual))

                self.conn.commit()
                mudancas_str = ", ".join(mudancas)
                logging.info(f"Produto {nome} atualizado: {mudancas_str}")

            if preco_atual != preco_antigo:
                link_produto = f"https://www.shopclub.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=5"
                link_produto2 = f"https://www.shopclub.com.br{link.split('/', 1)[-1]}"
                desconto_percentual = calcular_desconto(preco_antigo, preco_atual)
                self.enviar_webhook_discord(nome, preco_antigo, preco_atual, link_produto, link_produto2, desconto_percentual)
            return True
        else:
            cursor.execute('''
                INSERT INTO productsShopClub (id, name, url_key, price_discount, price_promotional, condition, garantia)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (item_id, nome, link, preco_desc, preco_atual, condition, garantia))

            cursor.execute('''
                INSERT INTO price_history (id, name, price)
                VALUES (?, ?, ?)
            ''', (item_id, nome, preco_atual))

            self.conn.commit()
            logging.info(f"Novo produto adicionado: {nome} - Preço: {preco_atual:.2f}")

            link_produto = f"https://www.shopclub.com.br/checkout/cart/add?sku={item_id}&qty=1&seller=1&sc=5"
            link_produto2 = f"https://www.shopclub.com.br{link.split('/', 1)[-1]}"
            self.enviar_webhook_discord(nome, preco_atual, preco_atual, link_produto, link_produto2, 0, novo_produto=True)
        return False


    def enviar_webhook_discord(self, nome_produto, preco_antigo, preco_novo, link_produto, link_produto2, desconto_percentual, novo_produto=False):
        webhooks = {
            "com-desconto": "https://discord.com/api/webhooks/1332230389015773235/sHaaOjhaNvv2_fBE0c9i4SFqTY1349q_Hi5stA8M7bmS8ND6A85fxoZ2lKkC0WoVPwc2",
            "novos": "https://discord.com/api/webhooks/1332934129481814108/6WJFC0p7DsCamzbqUrB-P87sGTf3-xChr8uJJtKmWE4Y1v0Pi4LZil8GZy7tGF4XU73M"
        }

        if novo_produto:
            webhook_url = webhooks["novos"]
        else:
            webhook_url = webhooks["com-desconto"]

        webhook = DiscordWebhook(url=webhook_url)
        embed = DiscordEmbed(title=nome_produto, description="Alteração de preço detectada!" if not novo_produto else "Novo produto adicionado!", color='03b2f8')
        embed.add_embed_field(name="Preço Antigo", value=f"R$ {preco_antigo:.2f}")
        embed.add_embed_field(name="Novo Preço", value=f"R$ {preco_novo:.2f}")
        embed.add_embed_field(name="Desconto", value=f"{desconto_percentual:.2f}%")
        embed.add_embed_field(name="Loja", value=f"ShopClub")
        embed.add_embed_field(name="Comprar", value=f"[Clique para adicionar no carrinho]({link_produto})")
        embed.add_embed_field(name="Link do Produto", value=f"[Clique para ir ao produto]({link_produto2})")
        webhook.add_embed(embed)
        response = webhook.execute()
        if response.status_code == 200:
            logging.info(f"Webhook enviado: {nome_produto} - Novo preço: R$ {preco_novo:.2f} - Desconto: {desconto_percentual:.2f}%")
        else:
            logging.error(f"Erro ao enviar webhook: {response.status_code}")

    async def fetch_page(self, variables):
        url = f"{self.base_url}"
        params = {
            "workspace": "master",
            "maxAge": "short",
            "appsEtag": "remove",
            "domain": "store",
            "locale": "pt-BR",
            # "__bindingId": "378597e2-4c99-4a15-b5b0-ed9a10bd1a78",
            "operationName": "productSearchV3",
            "variables": "{}",
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9177ba6f883473505dc99fcf2b679a6e270af6320a157f0798b92efeab98d5d3",
                    "sender": "vtex.store-resources@0.x",
                    "provider": "vtex.search-graphql@0.x"
                },
                "variables": variables
            })
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    print(f"ShopClub - Status Code: {response.status}")

                    try:
                        if response.status == 200:
                            return await response.json(content_type=None)
                        elif response.status == 500:
                            logging.error(f"Erro 500 na requisição. URL: {response.url}, Método: {response.method}")
                        else:
                            logging.error(f"Erro na requisição: Status {response.status}")
                        return None
                    except Exception as e:
                        logging.error(f"Erro na requisição: {e}")
                        return None
        except Exception as e:
            print(f"porra")

    async def monitor_pages(self):
        while True:
            for variable in self.variables:
                data = await self.fetch_page(variable)
                if data and 'data' in data and 'productSearch' in data['data'] and 'products' in data['data']['productSearch']:
                    products = data['data']['productSearch']['products']
                    for product in products:
                        try:
                            produto_id = product['productId']
                            nome_base = product['productName']
                            link = product['link']
                            
                            # Extrair especificações
                            specs = {}
                            for group in product['specificationGroups']:
                                if group['name'] == 'allSpecifications':
                                    for spec in group['specifications']:
                                        specs[spec['name']] = spec['values'][0] if spec['values'] else None
                            
                            condition = specs.get('Estado', None)
                            garantia = specs.get('Garantia (Dias)', None)
                            
                            # Processar cada item (variação) do produto
                            for item in product['items']:
                                item_id = item['itemId']
                                # print(item_id)
                                nome_completo = item['nameComplete']
                                ean = item['ean']
                                
                                # Extrair preços e quantidade disponível
                                for seller in item['sellers']:
                                    offer = seller['commertialOffer']
                                    preco_base = offer['Price']
                                    preco_list = offer['ListPrice']
                                    available_quantity = offer['AvailableQuantity']
                                    
                                    preco_desc = preco_list - preco_base if preco_list > preco_base else 0
                                    
                                    # Atualizar preço para cada variação
                                    self.atualizar_preco(
                                        f"{item_id}", nome_completo, preco_base, link,
                                        preco_desc=preco_desc, condition=condition, garantia=garantia,
                                        quantidade_disponivel=available_quantity
                                    )
                                    
                                    # Se você quiser processar apenas o primeiro seller, descomente a linha abaixo
                                    # break
                            
                        except Exception as e:
                            logging.error(f"Erro ao processar produto {item_id}: {e}")
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.5)
            print("Monitoramento finalizado: Iniciando novamente em 1 segundo")




async def monitor_shopclub():
    monitor = ShopClubMonitor()
    try:
        await monitor.monitor_pages()
    except KeyboardInterrupt:
        logging.info("\nMonitoramento finalizado pelo usuário")

if __name__ == "__main__":
    try:
        asyncio.run(monitor_shopclub())
    except KeyboardInterrupt:
        logging.info("\nPrograma finalizado pelo usuário")

