import flet as ft
from datetime import datetime
from funcoes import (
    carregar_dados_fluxoderotas, 
    salvar_dados_fluxoderotas
)

def mostrar_aba_condos_3(page: ft.Page, alvo: ft.Column):
    # --- ESTADO LOCAL ---
    if not page.session.get("temp_enderecos_multi_casas"):
        page.session.set("temp_enderecos_multi_casas", [])

    def mostrar_snack(texto, cor="orange"):
        snack = ft.SnackBar(ft.Text(texto), bgcolor=cor)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # --- CAMPOS DE ENTRADA ---
    txt_nome_grupo = ft.TextField(label="Nome do Loteamento/Condomínio", expand=True)
    txt_portaria = ft.TextField(label="Endereço da Portaria Principal", expand=True)

    # Campos para Condomínio de Casas (Sem número conforme solicitado)
    txt_rua = ft.TextField(label="Nome da Rua (Qualquer número será aceito)", expand=True)
    txt_bairro = ft.TextField(label="Bairro", expand=True)
    txt_cidade = ft.TextField(label="Cidade", value="CAMPINAS", expand=True)

    lista_view = ft.Column()
    lista_cadastrados = ft.Column()

    def adicionar_rua_lista(e):
        if not txt_rua.value or not txt_bairro.value:
            mostrar_snack("Rua e Bairro são obrigatórios!", "red")
            return

        novo = {
            "rua": txt_rua.value.upper().strip(),
            "bairro": txt_bairro.value.upper().strip(),
            "cidade": txt_cidade.value.upper().strip(),
            "numero": "QUALQUER" # Marcador interno para a lógica de busca saber que ignora número
        }
        
        lista_atual = page.session.get("temp_enderecos_multi_casas")
        lista_atual.append(novo)
        page.session.set("temp_enderecos_multi_casas", lista_atual)
        
        txt_rua.value = "" # Limpa apenas a rua para facilitar a próxima
        atualizar_lista_visual()
        page.update()

    def atualizar_lista_visual():
        lista_view.controls.clear()
        for i, end in enumerate(page.session.get("temp_enderecos_multi_casas")):
            lista_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.MAP_OUTLINED, color="orange"),
                    title=ft.Text(f"Rua: {end['rua']}"),
                    subtitle=ft.Text(f"Bairro: {end['bairro']} (Números ignorados)"),
                    trailing=ft.IconButton(
                        ft.icons.DELETE, 
                        icon_color="red",
                        on_click=lambda _, idx=i: remover_item(idx)
                    )
                )
            )
        page.update()

    def remover_item(index):
        lista = page.session.get("temp_enderecos_multi_casas")
        lista.pop(index)
        page.session.set("temp_enderecos_multi_casas", lista)
        atualizar_lista_visual()

    def salvar_no_firebase(e):
        if not txt_nome_grupo.value or not page.session.get("temp_enderecos_multi_casas"):
            mostrar_snack("Preencha o nome e adicione ao menos uma rua!", "red")
            return

        dados = {
            "portaria": txt_portaria.value.upper().strip(),
            "tipo": "multi_casas", 
            "enderecos": page.session.get("temp_enderecos_multi_casas"),
            "ultima_atualizacao": datetime.now().isoformat()
        }

        sucesso = salvar_dados_fluxoderotas(f"fluxoderotas_config/condominios", {txt_nome_grupo.value.upper(): dados})
        
        if sucesso:
            mostrar_snack("Loteamento salvo com sucesso!", "green")
            txt_nome_grupo.value = ""
            txt_portaria.value = ""
            page.session.set("temp_enderecos_multi_casas", [])
            atualizar_lista_visual()
            carregar_lista_cadastrados()
        else:
            mostrar_snack("Erro ao salvar no banco.", "red")

    def carregar_lista_cadastrados():
        lista_cadastrados.controls.clear()
        db_condos = carregar_dados_fluxoderotas("fluxoderotas_config/condominios") or {}
        
        for nome, info in db_condos.items():
            if info.get("tipo") == "multi_casas":
                lista_cadastrados.controls.append(
                    ft.Container(
                        padding=10, bgcolor="#333333", border_radius=8,
                        content=ft.Row([
                            ft.Icon(ft.icons.HOME_WORK, color="orange"),
                            ft.Text(nome, weight="bold", expand=True),
                            ft.Text(f"{len(info.get('enderecos', []))} Ruas", size=12),
                        ])
                    )
                )
        page.update()

    # --- MONTAGEM DA INTERFACE ---
    alvo.controls.clear()
    alvo.controls.append(
        ft.Column([
            ft.Text("🏡 Condomínios de Casas (Rua Inteira)", size=22, weight="bold"),
            
            ft.ExpansionTile(
                leading=ft.Icon(ft.icons.INFO_ROUNDED, color="orange"),
                title=ft.Text("Como funciona este modelo?", weight="bold"),
                controls=[
                    ft.Container(
                        padding=15, bgcolor="#2A2A2A", border_radius=10,
                        content=ft.Text(
                            "Ideal para condomínios horizontais. Você cadastra o nome da rua e, "
                            "independente do número da casa que vier na planilha, o sistema "
                            "entenderá que deve agrupar para a portaria principal.",
                            size=14
                        )
                    )
                ]
            ),
            
            ft.Divider(color="orange"),
            ft.Row([txt_nome_grupo, txt_portaria]),
            
            ft.Container(
                bgcolor="#2A2A2A", padding=15, border_radius=10,
                content=ft.Column([
                    ft.Text("Cadastrar Ruas do Condomínio", size=14, color="orange", weight="bold"),
                    ft.Row([txt_rua, txt_bairro]),
                    txt_cidade,
                    ft.ElevatedButton(
                        "ADICIONAR RUA À LISTA", 
                        icon=ft.icons.ADD_LOCATION_ALT, 
                        on_click=adicionar_rua_lista
                    ),
                ])
            ),
            
            ft.Text("Ruas para Salvar:", size=16, weight="bold"),
            lista_view,
            ft.ElevatedButton("SALVAR LOTEAMENTO", icon=ft.icons.SAVE, on_click=salvar_no_firebase, bgcolor="orange", color="white"),
            
            ft.Divider(height=30),
            ft.Text("🔍 Loteamentos Cadastrados", size=18, weight="bold"),
            lista_cadastrados
        ], scroll=ft.ScrollMode.AUTO)
    )
    
    carregar_lista_cadastrados()
    page.update()