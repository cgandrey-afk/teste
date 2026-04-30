import flet as ft
import pandas as pd
import io
import uuid
import time
import threading
# Importando lógica e ferramentas
from funcoes import (
    carregar_dados_fluxoderotas, 
    processar_agrupamento, 
    db,
    realizar_login_logic, 
    realizar_logout_logic, 
    iniciar_processamento_logic,
    atualizar_sidebar_logic,
    renderizar_conteudo_logic,
    gerar_view_inicio_logic,
    verificar_sessao_ativa,
    salvar_arquivo_no_disco_logic,
    preparar_download_logic,
    obter_nome_logado    
)
from interface_seletor import mostrar_seletor_condominios
from interface_notas import mostrar_aba_notas
from interface_condos import mostrar_aba_condos
from mapa import mostrar_aba_mapa
# IMPORTAÇÃO DA SUA PÁGINA INICIAL
from pginicial import mostrar_aba_inicio 

def main(page: ft.Page):
    # --- CONFIGURAÇÃO ---
    page.title = "Fluxo de Rotas - Versao 5.16"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1200
    page.window.height = 850              

    # --- 1º PASSO: DEFINIR O ESTADO PRIMEIRO ---
    state = {
        "arquivo_bytes": None,
        "df_processado": None,
        "aba_atual": "🏠 Início",
        "df_processado": None,
        "mapa_state": {"indice_parada": 0, "entregas_concluidas": set()}
    }

    # --- 2º PASSO: DEFINIR AS FUNÇÕES DE APOIO ---
    def navegar(label):
        if not verificar_sessao_ativa(page, state, atualizar_sidebar, renderizar_conteudo):
            page.open(drawer)
            return 

        state["aba_atual"] = label
        drawer.open = False
        
        renderizar_conteudo()
        page.update()

    # --- 3º PASSO: CONFIGURAR PICKERS (Agora 'navegar' e 'state' já existem) ---[cite: 12]
    fp_importar = ft.FilePicker(on_result=lambda e: iniciar_processamento_logic(page, state, renderizar_conteudo))
    fp_exportar = ft.FilePicker(on_result=lambda e: salvar_arquivo_no_disco_logic(e, state))
    
    page.overlay.append(fp_importar)
    page.overlay.append(fp_exportar)

    page.session.set("meu_file_picker", fp_importar)
    page.session.set("meu_file_picker_export", fp_exportar)
    page.session.set("navegar_callback", navegar)

    # --- 4º PASSO: CONTINUAR COM O RESTANTE DO CÓDIGO ---
    if verificar_sessao_ativa(page):
        state["aba_atual"] = "🏠 Início"
    else:
        page.session.set("logado", False)

    def monitor_seguranca():
        while True:
            time.sleep(10)
            try:
                if page.session.get("logado") == True:
                    verificar_sessao_ativa(
                        page, state, atualizar_sidebar, renderizar_conteudo, 
                        email_tf, senha_tf
                    )
            except:
                break
    
    coluna_scroll = ft.Column(
        expand=True, 
        scroll=ft.ScrollMode.ADAPTIVE,
        tight=True, 
        spacing=10
    )

    container_principal = ft.Container(
        content=coluna_scroll,
        padding=30, 
        expand=True
    )

    # --- FUNÇÕES DE APOIO ---
    def esta_logado():
        return page.session.get("logado") == True



    # --- CAMPOS DE LOGIN ---
    email_tf = ft.TextField(label="E-mail", border_color="red", height=50)
    senha_tf = ft.TextField(label="Senha", password=True, can_reveal_password=True, height=50)

    # --- SIDEBAR DINÂMICA ---
    def atualizar_sidebar():
        atualizar_sidebar_logic(        
            page, 
            state, 
            drawer, 
            email_tf, 
            senha_tf, 
            login_cb=lambda e: realizar_login_logic(page, state, email_tf.value, senha_tf.value, atualizar_sidebar, renderizar_conteudo),
            logout_cb=lambda e: realizar_logout_logic(page, state, atualizar_sidebar, renderizar_conteudo, email_tf, senha_tf)
        )

    # --- RENDERIZAR CONTEÚDO ---
    def renderizar_conteudo():       
        coluna_scroll.controls.clear()
        aba = state["aba_atual"]
        
        
        if aba == "🏠 Início":
            # Agora adicionamos corretamente o retorno da função
            coluna_scroll.controls.append(mostrar_aba_inicio(page, state, renderizar_conteudo))
            state["arquivo_bytes"] = None
            state["processamento_concluido"] = False
            state["df_processado"] = None
            state["nome_arquivo"] = ""
            mostrar_aba_inicio
            
        elif aba == "🏢 Condomínios":
            # Esta função geralmente limpa e desenha dentro da coluna fornecida
            mostrar_seletor_condominios(page, coluna_scroll)
            
        elif aba == "📝 Gerenciar Notas": # Ajuste o nome para bater com a sidebar
            mostrar_aba_notas(coluna_scroll)
            
        elif aba == "📍 Mapa":
            if state["df_processado"] is not None:
                mostrar_aba_mapa(coluna_scroll, state)
            else:
                coluna_scroll.controls.append(ft.Text("Processe uma planilha primeiro!"))
            
        page.update()

    # --- ESTRUTURA FINAL ---
    drawer = ft.NavigationDrawer(
        on_change=lambda e: navegar(e.control.controls[e.control.selected_index].label),
        controls=[]
    )

    header = ft.Container(
        content=ft.Row([
            ft.IconButton(ft.icons.MENU, icon_color="white", on_click=lambda _: page.open(drawer)),
            ft.Text("FLUXO DE ROTAS", weight="bold", color="white", expand=True),
        ]),
        bgcolor="#FF4B4B", padding=10
    )

    page.add(
        header, 
        ft.Divider(height=1, color="white24"), 
        container_principal
    )

    atualizar_sidebar()  
    renderizar_conteudo()
    
    t = threading.Thread(target=monitor_seguranca, daemon=True)
    t.start()  



    # Agora sim, inicialize a interface
    atualizar_sidebar()  
    renderizar_conteudo() 
    
ft.app(target=main)