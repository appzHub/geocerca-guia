# -*- coding: utf-8 -*-
"""Direcciones oficiales de Cali (IDESC, capa dapm:pdt_nmc_nomenclatura_domiciliaria, ~692.000 predios con coordenada).
Con esto «Calle 5 # 66-20» se ubica en la placa, no solo en la cuadra (Carlos 17/11/2026).
Salida: datos/placas/<VIA>.json, un archivo por via principal para que la pagina baje solo lo que necesita:
    {"<cruce>": [[placa, lat, lng], ...]}     ej. datos/placas/CL5.json -> {"KR66": [[20, 3.40112, -76.54321], ...]}
Las claves usan la misma normalizacion que index.html (CL, KR, AV, DG, TV + numero + letras/BIS/sufijo N-O-S-E)."""
import glob, json, os, re, shutil, sys, urllib.request
from collections import defaultdict

WFS = ("https://ws-idesc.cali.gov.co/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature"
       "&typeNames=dapm:pdt_nmc_nomenclatura_domiciliaria&propertyName=nddirecc,the_geom&outputFormat=application/json"
       "&srsName=EPSG:4326&sortBy=gid&count=50000&startIndex={}")
TIPO = {"CL": "CL", "C": "CL", "K": "KR", "AVV": "AV", "CALLE": "CL", "KR": "KR", "CRA": "KR", "CARRERA": "KR", "AK": "KR", "AC": "CL", "AV": "AV", "AVENIDA": "AV",
        "DG": "DG", "DIAGONAL": "DG", "TV": "TV", "TRANSVERSAL": "TV"}
SUF = [("NORTE", "N"), ("OESTE", "O"), ("SUR", "S"), ("ESTE", "E")]
PAT = re.compile(r"^([A-Z]+)\.?\s+(.+?)\s*#\s*(.+?)\s*-\s*(\d+)")


def parte(t):
    t = t.upper()
    for a, b in SUF: t = re.sub(rf"\b{a}\b", b, t)
    t = re.sub(r"[^0-9A-Z]", "", t)
    return t if re.fullmatch(r"\d+[A-Z0-9]*", t) else None


def clave(direccion):
    m = PAT.match(re.sub(r"\(.*?\)", "", str(direccion or "")).strip().upper())
    if not m or m.group(1) not in TIPO: return None
    p, c = parte(m.group(2)), parte(re.sub(r"^(AV|AK|AC|KR|CL|DG|TV)\.?\s+", "", m.group(3)))   # «# AV 2B - 19» -> cruce 2B
    return (TIPO[m.group(1)] + p, c, int(m.group(4))) if p and c else None


def paginas(carpeta):
    if carpeta: yield from (json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(carpeta, "p*.json"))))
    else:
        i = 0
        while True:
            d = json.load(urllib.request.urlopen(urllib.request.Request(WFS.format(i), headers={"User-Agent": "geocerca-guia"}), timeout=900))
            if not d["features"]: return
            yield d; i += 50000


def main():
    via = defaultdict(lambda: defaultdict(set)); total = malas = 0
    for d in paginas(sys.argv[1] if len(sys.argv) > 1 else None):
        for f in d["features"]:
            total += 1
            k = clave(f["properties"].get("nddirecc")); g = f.get("geometry")
            if not k or not g: malas += 1; continue
            x, y = g["coordinates"][:2]
            via[k[0]][k[1]].add((k[2], round(y, 5), round(x, 5)))
    if total < 600000: sys.exit(f"muy pocas direcciones ({total}); no se sobrescribe")
    shutil.rmtree("datos/placas", ignore_errors=True); os.makedirs("datos/placas")
    for v, cruces in via.items():
        # una placa repetida (varios predios) -> un solo punto, el promedio
        out = {}
        for c, s in cruces.items():
            por = defaultdict(list)
            for pl, la, ln in s: por[pl].append((la, ln))
            out[c] = sorted([pl, round(sum(p[0] for p in ps) / len(ps), 5), round(sum(p[1] for p in ps) / len(ps), 5)] for pl, ps in por.items())
        json.dump(out, open(f"datos/placas/{v}.json", "w", encoding="utf-8"), separators=(",", ":"))
    tam = sum(os.path.getsize(f) for f in glob.glob("datos/placas/*.json"))
    print(f"direcciones {total} · sin leer {malas} · vias {len(via)} · {tam / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
