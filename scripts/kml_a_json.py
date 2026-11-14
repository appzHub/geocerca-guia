# Convierte el KML público del mapa «Mapa Zonificar PE CALI 2026» (Google My Maps) en datos/geocercas.json.
# Lo corre la tarea diaria de GitHub (y se puede correr a mano). Sin dependencias.
import json, sys, urllib.request, xml.etree.ElementTree as ET
MID = "1c_u45guUSbjJAE_27n_zxM4sSPwKaSw"
URL = f"https://www.google.com/maps/d/kml?mid={MID}&forcekml=1"
NS = {"k": "http://www.opengis.net/kml/2.2"}
xml = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "geocerca-guia"}), timeout=60).read()
root = ET.fromstring(xml)
out = []
def recorrer(el, capa):
    for h in el:
        tag = h.tag.split("}")[1]
        if tag == "Folder":
            n = h.find("k:name", NS); recorrer(h, n.text if n is not None else capa)
        elif tag == "Document":
            recorrer(h, capa)
        elif tag == "Placemark":
            n = h.find("k:name", NS); anillos = []
            for ob in h.iter("{http://www.opengis.net/kml/2.2}outerBoundaryIs"):
                for c in ob.iter("{http://www.opengis.net/kml/2.2}coordinates"):
                    anillos.append([[round(float(v.split(",")[0]), 6), round(float(v.split(",")[1]), 6)] for v in c.text.split()])
            if anillos:
                out.append({"nombre": (n.text or "").strip() if n is not None else "(sin nombre)", "capa": capa, "anillos": anillos})
recorrer(root, "")
if len(out) < 10:
    sys.exit("muy pocas geocercas: no se reemplaza el archivo")
json.dump(out, open("datos/geocercas.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(out), "geocercas")
