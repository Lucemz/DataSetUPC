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


def ruta_greedy_cobertura(G: nx.Graph, origen: int, destinos: list[int]):
    """
    Devuelve una lista de nodos que representa una ruta (no necesariamente óptima)
    que parte en `origen` y visita todos los nodos en `destinos` usando Dijkstra
    para ir siempre al punto pendiente más cercano.
    """
    pendientes = set(destinos)
    ruta = [origen]
    actual = origen
    while pendientes:
        # descarta los que NO son alcanzables
        pendientes = {p for p in pendientes if nx.has_path(G, actual, p)}
        if not pendientes:
            break
        # nodo pendiente más cercano al nodo actual
        siguiente, _ = min(
            ((p, nx.dijkstra_path_length(G, actual, p, weight="length"))
             for p in pendientes),
            key=lambda x: x[1]
        )
        # concatenar la ruta parcial (sin repetir el nodo actual)
        tramo = nx.dijkstra_path(G, actual, siguiente, weight="length")
        ruta.extend(tramo[1:])
        actual = siguiente
        pendientes.remove(siguiente)
    return ruta


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

    # --- seleccionar nodos SOLO de la componente conexa más grande ----
    largest_cc = max(nx.connected_components(G), key=len)
    comp_nodes = list(largest_cc)

    # si la componente fuese aún >1500 nodos ya se redujo antes
    nodos   = comp_nodes
    random.shuffle(nodos)

    # escoger centros y puntos dentro de la misma componente
    centros = nodos[:min(4, len(nodos))]
    puntos  = nodos[4:4 + min(10, len(nodos) - 4)]

    for n in puntos:
        G.nodes[n]["tipo"] = "punto_recoleccion"
    for n in centros:
        G.nodes[n]["tipo"] = "centro_acopio"

    # --- filtrar puntos alcanzables desde el primer centro -------------
    origen_centro = centros[0]
    alcanzables = set(nx.single_source_dijkstra_path_length(G, origen_centro, weight="length").keys())
    puntos = [p for p in puntos if p in alcanzables]
    if not puntos:
        sys.exit("❌  Ningún punto de recolección es alcanzable desde el centro elegido.")


    if centros and puntos:
        o, d = centros[0], puntos[0]     # ya filtrado y garantizado alcanzable
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
        # --------------------------------------------------------------
        # Ruta que cubre todos los puntos de recolección (heurística)
        ruta_camion = ruta_greedy_cobertura(G, centros[0], puntos)
        dist_camion = sum(G[u][v]["length"] for u, v in zip(ruta_camion[:-1], ruta_camion[1:]))
        print("\nRuta (heurística) que recorre todos los puntos desde el centro 0:")
        print(" → ".join(map(str, ruta_camion[:10])) + (" …" if len(ruta_camion) > 10 else ""))
        print(f"Distancia total aproximada: {dist_camion:,.1f} m")
        # ---------- Visualizar la ruta sobre la red completa ----------
        pos = layout_seguro(G)  # reutilizamos el mismo layout
        plt.figure(figsize=(10, 10))

        # fondo gris tenue
        nx.draw_networkx_edges(G, pos, width=0.3, edge_color="#dddddd", alpha=0.4)
        nx.draw_networkx_nodes(G, pos,
                               nodelist=list(G.nodes),
                               node_color="#dddddd", node_size=15, alpha=0.6)

        # puntos y centros destacados
        nx.draw_networkx_nodes(G, pos,
                               nodelist=puntos, node_color="#33a02c", node_size=70, label="Punto")
        nx.draw_networkx_nodes(G, pos,
                               nodelist=centros, node_color="#1f78b4", node_size=110, label="Centro")

        # ruta más corta centro→primer punto (Dijkstra) en naranja
        edges_short = list(zip(ruta_astar[:-1], ruta_astar[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=edges_short,
                               width=3, edge_color="orange", alpha=0.9)

        # ruta en rojo
        edges_route = list(zip(ruta_camion[:-1], ruta_camion[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=edges_route,
                               width=2.5, edge_color="red", alpha=0.9)
        plt.title("Ruta heurística sobre la red")
        plt.axis("off")
        plt.tight_layout()
        plt.show()
        # --------------------------------------------------------------
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