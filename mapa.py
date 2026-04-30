import flet as ft
import pandas as pd
import folium # Folium é excelente para gerar o HTML que o Flet vai exibir
from geopy.distance import geodesic
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import io

# --- 1. LÓGICA DE ROTEIRIZAÇÃO (IDÊNTICA À ORIGINAL) ---

def extrair_logradouro(endereco):
    texto = str(endereco).replace("📍", "").strip().upper()
    return texto.split(',')[0].strip()

def otimizar_com_ortools(df):
    """Motor Lógico estilo Circuit usando Google OR-Tools"""
    coords = df[['Latitude', 'Longitude']].values
    num_locations = len(coords)
    
    manager = pywrapcp.RoutingIndexManager(num_locations, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        p1, p2 = coords[from_node], coords[to_node]
        
        dist = geodesic(p1, p2).meters
        
        # PENALIZAÇÃO: Se mudar de rua, a "distância" aumenta para o algoritmo
        rua_a = extrair_logradouro(df.iloc[from_node]['Destination Address'])
        rua_b = extrair_logradouro(df.iloc[to_node]['Destination Address'])
        
        if rua_a != rua_b:
            dist += 500 # Mantém o motorista na mesma rua antes de ir para a próxima
        return int(dist)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        index = routing.Start(0)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        return df.iloc[route].reset_index(drop=True)
    return df

# --- 2. INTERFACE DO MAPA (ADAPTADO PARA FLET) ---

def mostrar_aba_mapa(page: ft.Page, state):
    """
    Renderiza o mapa e os controles de navegação.
    No Flet, usamos Folium para gerar o mapa e exibimos em um HTML/WebView.
    """
    
    if state["df_processado"] is None:
        return ft.Column([
            ft.icon(ft.icons.MAP_OUTLINED, size=50, color="grey"),
            ft.Text("Nenhuma rota carregada. Vá em 'Início' e envie sua planilha.", color="grey")
        ], horizontal_alignment="center")

    # Inicializa variáveis de navegação se não existirem
    if "indice_parada" not in state: state["indice_parada"] = 0
    if "entregas_concluidas" not in state: state["entregas_concluidas"] = set()

    df = state["df_processado"]
    parada_atual = df.iloc[state["indice_parada"]]
    
    # --- GERAÇÃO DO MAPA (HTML) ---
    def gerar_mapa_html():
        m = folium.Map(
            location=[parada_atual['Latitude'], parada_atual['Longitude']],
            zoom_start=16,
            tiles="CartoDB dark_matter" # Estilo noturno Montana
        )

        for i, row in df.iterrows():
            cor = "green" if i in state["entregas_concluidas"] else "orange"
            if i == state["indice_parada"]: cor = "blue" # Parada atual
            
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=8 if i == state["indice_parada"] else 5,
                color=cor,
                fill=True,
                fill_opacity=0.7,
                popup=f"Parada {i+1}: {row['Destination Address']}"
            ).add_to(m)
        
        # Converte para string HTML
        data = io.BytesIO()
        m.save(data, close=False)
        return data.getvalue().decode()

    # --- CONTROLES DE NAVEGAÇÃO ---
    def proxima_parada(e):
        state["indice_parada"] = min(len(df) - 1, state["indice_parada"] + 1)
        page.update() # O app.py vai disparar a atualização visual

    def parada_anterior(e):
        state["indice_parada"] = max(0, state["indice_parada"] - 1)
        page.update()

    def alternar_concluido(e):
        if state["indice_parada"] in state["entregas_concluidas"]:
            state["entregas_concluidas"].remove(state["indice_parada"])
        else:
            state["entregas_concluidas"].add(state["indice_parada"])
        page.update()

    # --- COMPONENTES VISUAIS ---
    # WebView para o mapa (Nota: No Flet Desktop/Mobile funciona como navegador interno)
    mapa_view = ft.Html(
        data=gerar_mapa_html(),
        expand=True
    )

    controles = ft.Container(
        padding=10,
        bgcolor="#1E1E1E",
        content=ft.Column([
            ft.Text(f"📍 {parada_atual['Destination Address']}", size=16, weight="bold", max_lines=1),
            ft.Row([
                ft.IconButton(ft.icons.ARROW_BACK, on_click=parada_anterior),
                ft.ElevatedButton(
                    "CONCLUIR" if state["indice_parada"] not in state["entregas_concluidas"] else "REFAZER",
                    bgcolor="green" if state["indice_parada"] not in state["entregas_concluidas"] else "orange",
                    color="white",
                    expand=True,
                    on_click=alternar_concluido
                ),
                ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=proxima_parada),
            ]),
            ft.Row([
                ft.ElevatedButton(
                    "WAZE", 
                    icon=ft.Icons.NAVIGATION, 
                    expand=True,
                    on_click=lambda _: page.launch_url(f"https://waze.com/ul?ll={parada_atual['Latitude']},{parada_atual['Longitude']}&navigate=yes")
                ),
                ft.Text(f"{state['indice_parada'] + 1} / {len(df)}", size=14)
            ])
        ])
    )

    return ft.Column([
        ft.Container(content=mapa_view, expand=True), # Mapa no topo
        controles # Controles embaixo (estilo aplicativo de entrega)
    ], spacing=0, expand=True)