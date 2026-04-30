import flet as ft
from interface_condos import mostrar_aba_condos
from interface_condos_2 import mostrar_aba_condos_2
from interface_condos_3 import mostrar_aba_condos_3

def mostrar_seletor_condominios(page, alvo):
    alvo.controls.clear()
    
    def ir_para(aba_especifica):
        # Aqui você define qual função de interface chamar
        if aba_especifica == 1:  
            alvo.controls.clear()          
            mostrar_aba_condos(page, alvo)
        elif aba_especifica == 2:
            alvo.controls.clear()
            mostrar_aba_condos_2(page, alvo) # Sua futura interface_condos_2
        elif aba_especifica == 3:
            alvo.controls.clear()
            mostrar_aba_condos_3(page, alvo)  # Sua futura interface_condos_3
        page.update()

    # Criando o Menu de Opções
    opcoes = ft.Column([
        ft.Text("Escolha o modelo de agrupamento:", size=20, weight="bold"),
        
        # OPÇÃO 1: O que já temos
        criar_card_opcao(
            "Múltiplas Ruas → 1 Portaria", 
            "Vários endereços que entregam em um único lugar central.",
            ft.icons.APARTMENT,
            lambda _: ir_para(1)
        ),
        
        # OPÇÃO 2: Prédios com Portarias Individuais
        criar_card_opcao(
            "Blocos / Torres Individuais", 
            "Cada Bloco/Torre tem sua própria portaria ou recepção.",
            ft.icons.BUSINESS,
            lambda _: ir_para(2)
        ),
        
        # OPÇÃO 3: Loteamentos / Condomínios de Casas
        criar_card_opcao(
            "Rua Inteira (Ignorar Número)", 
            "Agrupa qualquer número daquela rua para a portaria principal.",
            ft.icons.COTTAGE, # ou ft.icons.HOME
            lambda _: ir_para(3)
        ),
    ], spacing=15)

    alvo.controls.append(opcoes)
    page.update()

def criar_card_opcao(titulo, subtitulo, icone, acao):
    return ft.Container(
        content=ft.ListTile(
            leading=ft.Icon(icone, color="orange", size=30),
            title=ft.Text(titulo, weight="bold"),
            subtitle=ft.Text(subtitulo),
            on_click=acao,
        ),
        bgcolor="#2A2A2A",
        border_radius=10,
        border=ft.border.all(1, "white24"),
    )