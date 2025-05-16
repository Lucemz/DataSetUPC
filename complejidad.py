
import json, math, random, sys
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt


def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    dlat, dlon = map(math.radians, [lat2 - lat1, lon2 - lon1])
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cargar_grafo(path_json: Path):
    datos = json.load(path_json.open(encoding="utf-8"))["elements"]
    nodos = {e["id"]: e for e in datos if e["type"] == "node"}
    ways  = [e for e in datos if e["type"] == "way" and
             "highway" in e.get("tags", {})]

    G = nx.Graph()
    for nid, n in nodos.items():
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


def layout_seguro(G):
    try:
        import scipy  # noqa: F401
        return nx.spring_layout(G, seed=42, k=0.6)
    except ModuleNotFoundError:
        try:
            return nx.kamada_kawai_layout(G)
        except ModuleNotFoundError:
            return nx.random_layout(G)


def dibujar(G, titulo="Red vial"):
    pos = layout_seguro(G)
    colores, sizes = [], []
    for _, d in G.nodes(data=True):
        if d["tipo"] == "punto_recoleccion":
            colores.append("#33a02c"); sizes.append(70)
        elif d["tipo"] == "centro_acopio":
            colores.append("#1f78b4"); sizes.append(110)
        else:
            colores.append("#cccccc"); sizes.append(18)
    plt.figure(figsize=(10, 10))
    nx.draw_networkx_nodes(G, pos, node_color=colores, node_size=sizes, alpha=0.9)
    nx.draw_networkx_edges(G, pos, width=0.3, alpha=0.4)
    plt.title(titulo); plt.axis("off"); plt.tight_layout(); plt.show()


def main():
    archivo = Path("export2.json")
    if not archivo.is_file():
        sys.exit("❌  Coloca export.json en la misma carpeta del script.")

    print("Construyendo grafo…")
    G = cargar_grafo(archivo)
    print(f"  • {G.number_of_nodes():,} nodos, {G.number_of_edges():,} aristas")

    G = subgrafo_aleatorio(G, 1500)
    if G.number_of_nodes() == 1500:
        print("Subgrafo aleatorio de 1500 nodos generado.")

    nodos = list(G.nodes)
    puntos  = random.sample(nodos, min(100, len(nodos)))
    centros = random.sample([n for n in nodos if n not in puntos],
                            min(3, len(nodos)))
    for n in puntos:
        G.nodes[n]["tipo"] = "punto_recoleccion"
    for n in centros:
        G.nodes[n]["tipo"] = "centro_acopio"

    print("Mostrando grafo… (cierra la ventana para continuar)")
    dibujar(G)

    if centros and puntos:
        o, d = centros[0], puntos[0]
        dist_dij = nx.dijkstra_path_length(G, o, d, weight="length")
        ruta_astar = nx.astar_path(
            G, o, d,
            heuristic=lambda u, v: haversine(G.nodes[u]["lat"], G.nodes[u]["lon"],
                                             G.nodes[v]["lat"], G.nodes[v]["lon"]),
            weight="length")
        dist_astar = sum(G[u][v]["length"]
                         for u, v in zip(ruta_astar[:-1], ruta_astar[1:]))
        mst = nx.minimum_spanning_tree(G, weight="length")
        long_mst = sum(d["length"] for _, _, d in mst.edges(data=True))
        print("\n───────── RESULTADOS ─────────")
        print(f"Nodos en grafo:        {G.number_of_nodes():,}")
        print(f"Puntos de recolección: {len(puntos)}")
        print(f"Centros de acopio:     {len(centros)}")
        print(f"Dijkstra centro→punto: {dist_dij:,.1f} m")
        print(f"A*      centro→punto:  {dist_astar:,.1f} m")
        print(f"Longitud MST (Kruskal): {long_mst:,.0f} m")
        print("─────────────────────────────")


if __name__ == "__main__":
    main()