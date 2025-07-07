import streamlit as st
import networkx as nx
from pathlib import Path
from streamlit_folium import st_folium

try:
    import hito2
except ImportError:
    st.error("❌ Error crítico: No se pudo encontrar el archivo 'hito2.py'. Asegúrate de que esté en la misma carpeta que 'app_gui.py'.")
    st.stop()

st.set_page_config(layout="wide", page_title="OptiRuta Urbana", page_icon="🗺️")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] > .main {
    background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
h1 {
    color: #0d47a1;
    text-shadow: 2px 2px 4px #cccccc;
    font-family: 'Arial', sans-serif;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    border: 1px solid #90a4ae;
    border-radius: 10px;
    padding: 25px;
    background-color: rgba(255, 255, 255, 0.85);
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    transition: 0.3s;
}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:hover {
    box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
}
[data-testid="stSidebar"] {
    background-image: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] > div,
[data-testid="stSidebar"] [data-testid="stRadio"] label,
[data-testid="stSidebar"] [data-testid="stRadio"] p {
    color: #ffffff;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    color: #31333F !important;
    background-color: white;
}
[data-baseweb="popover"] ul li {
    color: #31333F;
}
</style>
""", unsafe_allow_html=True)

st.title("🗺️ OptiRuta Urbana")
st.caption("Una herramienta inteligente para el análisis de la red vial.")

if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'last_map' not in st.session_state:
    st.session_state.last_map = None

@st.cache_data
def cargar_datos_iniciales():
    archivo = Path("export2.json")
    if not archivo.is_file():
        return None
    G_completo = hito2.cargar_grafo(archivo)
    componentes = list(nx.connected_components(G_completo))
    if not componentes:
        return None
    componente_mas_grande = max(componentes, key=len)
    G_principal = G_completo.subgraph(componente_mas_grande).copy()
    return G_principal

with st.spinner("Cargando y procesando el grafo... ⏳"):
    G = cargar_datos_iniciales()

if G is None:
    st.error("❌ Error al cargar los datos. Asegúrate de que 'export2.json' existe y es válido.")
    st.stop()

st.success(f"✅ ¡Grafo cargado! Contiene {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas.")
st.markdown("---")

st.sidebar.header("⚙️ Configuración de Ruta")
analisis_elegido = st.sidebar.radio(
    "Selecciona un tipo de optimización:",
    ("Búsqueda por Recorrido (BFS)", "Búsqueda Voraz (A*)"),
    captions=["Ruta más simple (menos paradas)", "Ruta más corta (menos distancia)"],
    key="algoritmo_radio"
)

st.sidebar.subheader("📍 Puntos de la Ruta")
nodos_disponibles = sorted(list(G.nodes()))
origen = st.sidebar.selectbox("Punto de Origen:", nodos_disponibles, index=0, key="origen_select")
destino = st.sidebar.selectbox("Punto de Destino:", nodos_disponibles, index=len(nodos_disponibles) // 2, key="destino_select")

if st.sidebar.button("🔍 Encontrar Ruta", type="primary", use_container_width=True):
    st.session_state.last_result = None
    st.session_state.last_map = None

    if origen == destino:
        st.warning("⚠️ El origen y el destino no pueden ser los mismos.")
    else:
        with st.spinner(f"Buscando la mejor ruta con {analisis_elegido.split('(')[0]}... 🧠"):
            try:
                if "BFS" in analisis_elegido:
                    ruta = nx.shortest_path(G, origen, destino)
                    distancia = sum(G.edges[u, v]["length"] for u, v in zip(ruta[:-1], ruta[1:]))
                    st.session_state.last_result = {"tipo": "BFS", "ruta": ruta, "distancia": distancia}
                
                elif "A*" in analisis_elegido:
                    ruta = nx.astar_path(G, origen, destino,
                                         heuristic=lambda u, v: hito2.haversine(G.nodes[u]["lat"], G.nodes[u]["lon"], G.nodes[v]["lat"], G.nodes[v]["lon"]),
                                         weight="length")
                    distancia = sum(G.edges[u, v]["length"] for u, v in zip(ruta[:-1], ruta[1:]))
                    st.session_state.last_result = {"tipo": "A*", "ruta": ruta, "distancia": distancia}
                
                mapa = hito2.crear_mapa_interactivo(G, st.session_state.last_result['ruta'])
                st.session_state.last_map = mapa

            except nx.NetworkXNoPath:
                st.session_state.last_result = {"error": "❌ No se encontró una ruta entre los nodos seleccionados."}
            except Exception as e:
                st.session_state.last_result = {"error": f"Ocurrió un error inesperado: {e}"}

col1, col2 = st.columns([1, 1.5])

with col1:
    with st.container():
        st.subheader("📊 Resultados del Algoritmo")
        if st.session_state.last_result is None:
            st.info("Selecciona los parámetros y haz clic en 'Encontrar Ruta' para ver los resultados.")
        elif "error" in st.session_state.last_result:
            st.error(st.session_state.last_result["error"])
        else:
            resultado = st.session_state.last_result
            if resultado['tipo'] == 'BFS':
                st.success("✅ Ruta BFS encontrada (la más simple)")
            elif resultado['tipo'] == 'A*':
                st.success("✅ Ruta A* encontrada (la más corta)")
            metric_col1, metric_col2 = st.columns(2)
            num_paradas = len(resultado['ruta']) - 1
            texto_paradas = f"{num_paradas} parada" if num_paradas == 1 else f"{num_paradas} paradas"
            metric_col1.metric(label="Paradas en la Ruta", value=texto_paradas)
            metric_col2.metric(label="Distancia Total", value=f"{resultado['distancia']:,.2f} metros")
            st.markdown("---")
            st.write("**Detalle de la ruta (nodos):**")
            with st.expander("Ver secuencia de nodos"):
                st.write(" -> ".join(map(str, resultado['ruta'])))

with col2:
    with st.container():
        st.subheader("📍 Visualización del Mapa")
        if st.session_state.last_map:
            st_folium(st.session_state.last_map, width='100%', height=500)
        else:
            st.info("Aquí se mostrará el mapa con la ruta resaltada después de la búsqueda.")