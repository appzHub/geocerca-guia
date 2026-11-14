# -*- coding: utf-8 -*-
"""Convierte las claves que Carlos escribe en C:/Users/andre/geocerca-claves.txt (fuera del repositorio) en
datos/usuarios.json: sal aleatoria + hash PBKDF2-SHA256 (150.000 vueltas), lo mismo que verifica index.html.
No imprime claves. Despues de correrlo, el archivo de claves se borra."""
import hashlib, json, os, secrets, sys

ORIGEN = r"C:\Users\andre\geocerca-claves.txt"
DESTINO = os.path.join(os.path.dirname(__file__), "..", "datos", "usuarios.json")

usuarios = {}
for linea in open(ORIGEN, encoding="utf-8-sig"):
    if "=" not in linea or linea.lstrip().startswith("#"): continue
    u, c = linea.split("=", 1); u, c = u.strip().lower(), c.strip()
    if not c: sys.exit(f"falta la clave de {u}")
    sal = secrets.token_bytes(16)
    usuarios[u] = {"sal": sal.hex(), "hash": hashlib.pbkdf2_hmac("sha256", c.encode(), sal, 150000).hex()}
if set(usuarios) != {"operaciones", "admin"}: sys.exit("se esperan los usuarios operaciones y admin")
json.dump(usuarios, open(DESTINO, "w", encoding="utf-8"), indent=1)
os.remove(ORIGEN)
print("usuarios:", ", ".join(usuarios), "· archivo de claves borrado")
