# -*- coding: utf-8 -*-
"""Indice de lugares para ubicar guias sin direccion exacta (Carlos 17/11/2026).
«Si el barrio esta bien, tienes la ubicacion»: la geocerca no necesita el punto exacto.
- Barrios oficiales de Cali (IDESC, Divipola 2026, 342 poligonos): se mide que parte de cada barrio cae en cada geocerca.
- Lugares de OpenStreetMap en toda el area de las geocercas: barrios, veredas, ingenios, conjuntos, hospitales, centros comerciales.
- Ciudades y pueblos: centro y si todo el casco urbano cae en una sola geocerca (entonces la ciudad sola basta).
Salida: datos/lugares.json = {"ciudades": [[clave, nombre, lat, lng, radio_m, geocerca_unica]],
                              "lugares": [[clave, nombre, lat, lng, tipo, ciudad, geocerca, parte]]}"""
import json, math, re, sys, unicodedata, urllib.parse, urllib.request

AREA = (2.95, -77.12, 4.25, -76.12)
WFS = ("https://ws-idesc.cali.gov.co/geoserver/wfs?service=WFS&version=1.0.0&request=GetFeature"
       "&typeName=dapm:pdt_dpa_barrios_sectores&outputFormat=application/json&srsName=EPSG:4326")
GENERICOS = (r"^(barrio|urbanizacion|urb|conjunto residencial|conjunto|condominio|unidad residencial|ciudadela|parcelacion|sector|asentamiento|"
             r"vereda|corregimiento|centro comercial|c c|cc|ciudad)\s+")
ARTICULO = r"^(el|la|los|las)\s+"
ETAPA = r"\s+((primera|segunda|tercera|cuarta|quinta|1a|2a|3a|4a|[0-9]+)\s+etapa|etapa\s+\w+|i|ii|iii|iv|v|vi)$"
# primera palabra sola ("desepaz" por «Desepaz Invicali»): solo barrios oficiales y si no es una palabra comun
NO_PRIMERA = {"altos", "bosques", "brisas", "prados", "villa", "santa", "nueva", "nuevo", "ciudad", "sector", "barrio", "urbanizacion", "camino",
              "jardin", "colinas", "lomas", "parques", "portal", "puerta", "valle", "cristo", "alfonso", "antonio", "manuela", "mariano", "simon",
              "jose", "juan", "pedro", "francisco", "jorge", "julio", "rafael", "ricardo", "primero", "industrial", "unidad", "multicentro"}
# alias que la gente escribe en lugar del nombre oficial
ALIAS = {"guadalajara de buga": ["buga"], "santiago de cali": ["cali"], "santander de quilichao": ["santander"],
         "buenaventura": ["bventura"], "tulua": ["tulua"], "jamundi": ["jamundi"]}


def norm(t):
    t = "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def bajar(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "geocerca-guia"})
    return json.load(urllib.request.urlopen(req, timeout=320))


def dentro(x, y, an):
    c = False; j = len(an) - 1
    for i in range(len(an)):
        xi, yi = an[i]; xj, yj = an[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
        j = i
    return c


ZONAS = json.load(open("datos/geocercas.json", encoding="utf-8"))
CAJA = [(z["nombre"], [(min(p[0] for p in a), max(p[0] for p in a), min(p[1] for p in a), max(p[1] for p in a), a) for a in z["anillos"]]) for z in ZONAS]


def geocerca(x, y):
    for n, ans in CAJA:
        for x0, x1, y0, y1, a in ans:
            if x0 <= x <= x1 and y0 <= y <= y1 and dentro(x, y, a): return n
    return None


def reparto(puntos):
    """[(x, y)] -> (geocerca dominante, fraccion, punto representativo dentro de ella)"""
    cuenta = {}
    for x, y in puntos:
        g = geocerca(x, y); cuenta.setdefault(g, []).append((x, y))
    if not puntos: return None, 0, None
    g, pts = max(cuenta.items(), key=lambda kv: len(kv[1]))
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    mejor = min(pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)    # un punto real del barrio, no el centroide
    return g, round(len(pts) / len(puntos), 2), mejor


def muestras_poligono(geom, paso=0.0003):     # ~33 m
    polis = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    out = []
    for poli in polis:
        ext = poli[0]; xs = [p[0] for p in ext]; ys = [p[1] for p in ext]
        y = min(ys) + paso / 2
        while y < max(ys):
            x = min(xs) + paso / 2
            while x < max(xs):
                if dentro(x, y, ext) and not any(dentro(x, y, h) for h in poli[1:]): out.append((x, y))
                x += paso
            y += paso
        if not out: out.append((sum(xs) / len(xs), sum(ys) / len(ys)))
    return out


def variantes(nombre, oficial=False):
    """'El Limonar' -> limonar · 'Chiminangos Primera Etapa' -> chiminangos · 'Camino Real - Los Fundadores' -> los fundadores ·
    'Centro Comercial Unicentro' -> unicentro"""
    v = set()
    for trozo in [nombre] + (str(nombre).split(" - ") if " - " in str(nombre) else []):
        n = norm(trozo); v.add(n)
        for _ in range(2):
            n = re.sub(ARTICULO, "", re.sub(GENERICOS, "", re.sub(ETAPA, "", n))).strip(); v.add(n)
        p = n.split(" ")[0]
        if oficial and len(n.split(" ")) > 1 and len(p) >= 6 and p not in NO_PRIMERA: v.add(p)
    for k, al in ALIAS.items():
        if norm(nombre) == k: v.update(al)
    return [x for x in v if len(x) >= 4]


def main():
    osm_q = f'''[out:json][timeout:300];(
 nwr["place"~"^(city|town|village|hamlet|suburb|neighbourhood|quarter|locality)$"]["name"]{AREA};
 nwr["landuse"~"^(residential|industrial|commercial|retail)$"]["name"]{AREA};
 nwr["man_made"="works"]["name"]{AREA};
 nwr["amenity"~"^(university|college|hospital|clinic|marketplace|prison)$"]["name"]{AREA};
 nwr["shop"="mall"]["name"]{AREA};
 nwr["aeroway"="aerodrome"]["name"]{AREA};
);out tags center;'''
    osm = (json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else
           bajar("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": osm_q}).encode()))["elements"]
    barrios = (json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else bajar(WFS))["features"]
    if len(barrios) < 300 or len(osm) < 2000: sys.exit(f"pocos datos ({len(barrios)} barrios, {len(osm)} lugares); no se sobrescribe")

    # ---- ciudades y pueblos
    ciudades = []
    for e in osm:
        t = e.get("tags", {}); tipo = t.get("place")
        if tipo not in ("city", "town", "village"): continue
        y, x = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        radio = {"city": 12000, "town": 5000, "village": 2500}[tipo]
        urbano = {"city": 0, "town": 1200, "village": 500}[tipo]     # casco urbano para decidir si basta la ciudad
        unica = None
        if urbano:
            pts = [(x, y)] + [(x + urbano / 111320 / math.cos(math.radians(y)) * r * math.cos(a), y + urbano / 111320 * r * math.sin(a))
                              for r in (0.5, 1) for a in [k * math.pi / 6 for k in range(12)]]
            gs = [geocerca(px, py) for px, py in pts]
            dentro_ = [g for g in gs if g]       # puntos fuera de toda geocerca (potreros) no cuentan
            if dentro_:
                top = max(set(dentro_), key=dentro_.count)
                if dentro_.count(top) >= .85 * len(dentro_) and len(dentro_) >= 5: unica = top
        for v in variantes(t["name"]):
            ciudades.append([v, t["name"], round(y, 5), round(x, 5), radio, unica])
    ciudades.sort(key=lambda c: -len(c[0]))
    cerca = lambda y, x: min((c for c in ciudades if (c[2] - y) ** 2 + ((c[3] - x) * math.cos(math.radians(y))) ** 2 < (c[4] / 111320) ** 2),
                             key=lambda c: (c[2] - y) ** 2 + (c[3] - x) ** 2, default=None)

    # ---- barrios oficiales de Cali
    lugares = []
    for f in barrios:
        p = f["properties"]; g, parte, pt = reparto(muestras_poligono(f["geometry"]))
        for v in variantes(p["barnombre"], oficial=True):
            lugares.append([v, p["barnombre"], round(pt[1], 5), round(pt[0], 5), "barrio Cali", "cali", g, parte])
    # ---- lugares de OSM (los barrios de Cali que ya estan en la capa oficial no se repiten)
    oficiales = {l[0] for l in lugares}
    for e in osm:
        t = e.get("tags", {}); tipo = t.get("place") or t.get("landuse") or t.get("man_made") or t.get("amenity") or t.get("shop") or t.get("aeroway")
        if tipo in ("city", "town"): continue
        y, x = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        c = cerca(y, x); ciudad = c[0] if c else ""
        for v in variantes(t["name"]):
            if v in oficiales and ciudad == "cali": continue
            lugares.append([v, t["name"], round(y, 5), round(x, 5), tipo, ciudad, geocerca(x, y), 1])
    json.dump({"ciudades": ciudades, "lugares": lugares}, open("datos/lugares.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("ciudades", len(ciudades), "con una sola geocerca", sum(1 for c in ciudades if c[5]), "· lugares", len(lugares),
          "· barrios Cali partidos (<80 %)", sum(1 for l in lugares if l[4] == "barrio Cali" and l[7] < .8))


if __name__ == "__main__":
    main()
