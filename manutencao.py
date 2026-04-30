import flet as ft
import time
import random

def mostrar_tela_manutencao(page: ft.Page, mudar_tela_callback):
    def animar_progresso():
        for i in range(0, 96):
            barra_progresso.value = i / 100
            texto_status.value = f"🔵 Otimizando módulos... {i}%"
            page.update()
            time.sleep(random.uniform(0.01, 0.05))
        texto_status.value = "🔵 Módulos em fase de homologação... 95%"
        page.update()

    barra_progresso = ft.ProgressBar(width=400, color="blue", bgcolor="#262626", value=0)
    texto_status = ft.Text(value="Iniciando...", size=12, italic=True, color="blue400")

    return ft.Container(
        padding=30,
        expand=True,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.icons.CONSTRUCTION_ROUNDED, size=60, color="orange"),
                ft.Text("O Futuro do Fluxo de Rotas", size=24, weight="bold"),
                barra_progresso,
                texto_status,
                ft.Container(
                    bgcolor="#1E1E1E",
                    padding=20,
                    border_radius=15,
                    content=ft.Column([
                        ft.Text("🚧 O que está chegando:", size=18, weight="w600"),
                        ft.ListTile(leading=ft.Icon(ft.icons.MAP_SHARP, color="blue"), title=ft.Text("Roteirizador Nativo")),
                        ft.ListTile(leading=ft.Icon(ft.icons.PERSON_PIN, color="blue"), title=ft.Text("Perfil Profissional")),
                    ])
                ),
                ft.ElevatedButton("⬅️ Voltar", icon=ft.icons.ARROW_BACK, on_click=lambda _: mudar_tela_callback("🏠 Início")),
            ]
        )
    )