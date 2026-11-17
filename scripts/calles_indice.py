# -*- coding: utf-8 -*-
"""Indice de cruces de calles para ubicar direcciones colombianas (Carlos 14/11/2026).
«Calle 5 # 66-20» = sobre la Calle 5, a 20 m del cruce con la Carrera 66. OpenStreetMap no tiene placas en Cali,
pero si las calles: dos vias que se cruzan comparten un nodo con las mismas coordenadas. Este script baja las vias
con nombre (Overpass) y guarda, por cada via, sus cruces: datos/cruces.json = {via: [[cruce, lat, lng], ...]}."""
import json, re, sys, unicodedata, urllib.parse, urllib.request
from collections import defaultdict

# toda el area de las geocercas (17/11/2026): Santander de Quilichao, Cali, Palmira, Buga, Tulua, Buenaventura
TILES = [(2.95, -76.70, 3.62, -76.12), (3.62, -76.70, 4.25, -76.12), (3.70, -77.12, 3.95, -76.70)]
TIPOS = [(r"avenida calle|av\.? calle", "CL"), (r"avenida carrera|av\.? carrera", "KR"), (r"calle", "CL"), (r"carrera", "KR"),
         (r"diagonal", "DG"), (r"transversal", "TV"), (r"avenida", "AV")]
SUF = {"NORTE": "N", "OESTE": "O", "SUR": "S", "ESTE": "E"}


SERVIDORES = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
              "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def overpass(q):
    """Overpass a veces responde 502/504 por carga: se reintenta en servidores alternos antes de rendirse."""
    import time
    ultimo = None
    for intento in range(2):
        for url in SERVIDORES:
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "geocerca-guia"})
                d = json.load(urllib.request.urlopen(req, timeout=320))
                if "elements" in d: return d
            except Exception as e:
                ultimo = e
        time.sleep(30)
    raise RuntimeError(f"Overpass no respondio: {ultimo}")


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def clave(nombre):
    """'Carrera 66A Bis Norte' -> 'KR66ABISN'. None si no es una via numerada."""
    t = sin_tildes(nombre).lower().strip()
    for pat, tipo in TIPOS:
        m = re.match(rf"^(?:{pat})\s+(\d+)\s*(.*)$", t)
        if m:
            resto = m.group(2).upper().replace(" ", "")
            for largo, corto in SUF.items():
                if resto.endswith(largo): resto = resto[: -len(largo)] + corto
            if not re.fullmatch(r"[A-Z]{0,2}\d?(BIS)?[A-Z]?\d?[NOSE]?", resto): return None
            return tipo + m.group(1) + resto
    return None


def bajar():
    els = []
    for t in TILES:
        q = f'[out:json][timeout:280];way["highway"]["name"]({",".join(map(str, t))});out tags geom;'
        els += overpass(q)["elements"]
    return els


def main():
    els = json.load(open(sys.argv[1], encoding="utf-8"))["elements"] if len(sys.argv) > 1 else bajar()
    nodo = defaultdict(set)
    for e in els:
        k = clave(e.get("tags", {}).get("name", ""))
        if not k: continue
        for p in e.get("geometry", []):
            nodo[(round(p["lat"], 6), round(p["lon"], 6))].add(k)
    cruces = defaultdict(set)
    for (lat, lng), ks in nodo.items():
        if len(ks) < 2: continue
        for a in ks:
            for b in ks:
                if a != b: cruces[a].add((b, round(lat, 5), round(lng, 5)))
    out = {a: sorted(v) for a, v in sorted(cruces.items())}
    n = sum(len(v) for v in out.values())
    if n < 5000: sys.exit(f"muy pocos cruces ({n}); no se sobrescribe")
    json.dump(out, open("datos/cruces.json", "w", encoding="utf-8"), separators=(",", ":"))
    print("vias", len(out), "cruces", n)


if __name__ == "__main__":
    main()
