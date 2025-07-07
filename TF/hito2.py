import json
import math
import random
from pathlib import Path
import networkx as nx
import folium

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    dlat, dlon = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def cargar_grafo(path_json: Path):
    with open(path_json, 'r', encoding="utf-8") as f:
        datos = json.load(f)["elements"]

    nodos = {e["id"]: e for e in datos if e["type"] == "node"}
    ways = [e for e in datos if e["type"] == "way" and
            "highway" in e.get("tags", {})]

    G = nx.Graph()
    for nid, n in nodos.items():
        if "lat" in n and "lon" in n:
            G.add_node(nid, lat=n["lat"], lon=n["lon"], tipo="transito")

    for w in ways:
        seq = w["nodes"]
        for u, v in zip(seq[:-1], seq[1:]):
            if u in G and v in G and not G.has_edge(u, v):
                n1, n2 = nodos[u], nodos[v]
                dist = haversine(n1["lat"], n1["lon"], n2["lat"], n2["lon"])
                G.add_edge(u, v, length=dist)
    return G

def subgrafo_aleatorio(G: nx.Graph, n=1500):
    return G if G.number_of_nodes() <= n else G.subgraph(
        random.sample(list(G.nodes), n)).copy()

def crear_mapa_interactivo(G, ruta):
    if not ruta:
        return None

    lats = [G.nodes[nodo]['lat'] for nodo in ruta]
    lons = [G.nodes[nodo]['lon'] for nodo in ruta]
    centro_mapa = [sum(lats) / len(lats), sum(lons) / len(lons)]

    mapa = folium.Map(location=centro_mapa, zoom_start=15, tiles="CartoDB positron")

    puntos_ruta = [(G.nodes[nodo]['lat'], G.nodes[nodo]['lon']) for nodo in ruta]
    folium.PolyLine(
        puntos_ruta,
        color='#3388ff',
        weight=5,
        opacity=0.8,
        tooltip="Ruta Calculada"
    ).add_to(mapa)

    for i, nodo in enumerate(ruta):
        lat, lon = G.nodes[nodo]['lat'], G.nodes[nodo]['lon']
        
        if i == 0:
            folium.Marker(
                location=[lat, lon],
                popup=f"📍 <strong>Inicio</strong><br>Nodo: {nodo}",
                tooltip="Punto de Origen",
                icon=folium.Icon(color='green', icon='play', prefix='fa')
            ).add_to(mapa)
        elif i == len(ruta) - 1:
            folium.Marker(
                location=[lat, lon],
                popup=f"🏁 <strong>Destino</strong><br>Nodo: {nodo}",
                tooltip="Punto de Destino",
                icon=folium.Icon(color='red', icon='flag', prefix='fa')
            ).add_to(mapa)
        else:
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color='#ff7800',
                fill=True,
                fill_color='#ff7800',
                fill_opacity=0.7,
                popup=f"Parada intermedia<br>Nodo: {nodo}"
            ).add_to(mapa)
            
    return mapa

def main():
    print("Este es un módulo de ayuda para la aplicación Streamlit.")
    print("Para usar la interfaz gráfica, ejecuta: streamlit run app_gui.py")

if __name__ == "__main__":
    main()