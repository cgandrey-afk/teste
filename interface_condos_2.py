import flet as ft
from datetime import datetime
from funcoes import (
    carregar_dados_fluxoderotas, 
    salvar_dados_fluxoderotas
)

def mostrar_aba_condos_2(page: ft.Page, alvo: ft.Column):
    # --- ESTADO LOCAL ---
    if not page.session.get("temp_enderecos_multi_portarias"):
        page.session.set("temp_enderecos_multi_portarias", [])

    def mostrar_snack(texto, cor="orange"):
        snack = ft.SnackBar(ft.Text(texto), bgcolor=cor)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # --- CAMPOS DE ENTRADA ---
    txt_nome_grupo = ft.TextField(label="Nome da rua", border_color="orange", expand=True)
    txt_portaria = ft.TextField(label="Endereço da Portaria Principal (Opcional)", expand=True)

    # Campos Obrigatórios conforme solicitado
    txt_rua = ft.TextField(label="Rua (Obrigatório)", expand=True)
    txt_num = ft.TextField(label="Nº (Obrigatório)", width=100)
    txt_complemento = ft.TextField(label="Bloco/Torre (Obrigatório)", width=150)
    txt_bairro = ft.TextField(label="Bairro (Obrigatório)", expand=True)
    txt_cidade = ft.TextField(label="Cidade", value="CAMPINAS", expand=True)
    txt_cep = ft.TextField(label="CEP", width=150)

    lista_view = ft.Column()
    lista_cadastrados = ft.Column()

    def adicionar_endereco_lista(e):
        # Validação de campos obrigatórios
        if not all([txt_rua.value, txt_num.value, txt_complemento.value, txt_bairro.value]):
            mostrar_snack("Preencha todos os campos obrigatórios!", "red")
            return

        novo = {
            "rua": txt_rua.value.upper().strip(),
            "numero": txt_num.value.upper().strip(),
            "complemento": txt_complemento.value.upper().strip(),
            "bairro": txt_bairro.value.upper().strip(),
            "cidade": txt_cidade.value.upper().strip(),
            "cep": txt_cep.value.strip()
        }
        
        lista_atual = page.session.get("temp_enderecos_multi_portarias")
        lista_atual.append(novo)
        page.session.set("temp_enderecos_multi_portarias", lista_atual)
        
        # Limpa campos de endereço para o próximo
        txt_rua.value = ""
        txt_num.value = ""
        txt_complemento.value = ""
        
        atualizar_lista_visual()
        page.update()

    def atualizar_lista_visual():
        lista_view.controls.clear()
        for i, end in enumerate(page.session.get("temp_enderecos_multi_portarias")):
            lista_view.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.LOCATION_ON, color="orange"),
                    title=ft.Text(f"{end['rua']}, {end['numero']} - {end['complemento']}"),
                    subtitle=ft.Text(f"{end['bairro']}, {end['cidade']}"),
                    trailing=ft.IconButton(
                        ft.icons.DELETE, 
                        icon_color="red",
                        on_click=lambda _, idx=i: remover_item(idx)
                    )
                )
            )
        page.update()

    def remover_item(index):
        lista = page.session.get("temp_enderecos_multi_portarias")
        lista.pop(index)
        page.session.set("temp_enderecos_multi_portarias", lista)
        atualizar_lista_visual()

    def salvar_no_firebase(e):
        if not txt_nome_grupo.value or not page.session.get("temp_enderecos_multi_portarias"):
            mostrar_snack("Nome do grupo e pelo menos um endereço são necessários!", "red")
            return

        dados = {
            "portaria": txt_portaria.value.upper().strip(),
            "tipo": "multi_portarias", # Alterado conforme solicitado
            "enderecos": page.session.get("temp_enderecos_multi_portarias"),
            "ultima_atualizacao": datetime.now().isoformat()
        }

        # Salva no nó de condominios
        sucesso = salvar_dados_fluxoderotas(f"fluxoderotas_config/condominios", {txt_nome_grupo.value.upper(): dados})
        
        if sucesso:
            mostrar_snack("Condomínio salvo com sucesso!", "green")
            txt_nome_grupo.value = ""
            txt_portaria.value = ""
            page.session.set("temp_enderecos_multi_portarias", [])
            atualizar_lista_visual()
            carregar_lista_cadastrados()
        else:
            mostrar_snack("Erro ao salvar no banco.", "red")

    def carregar_lista_cadastrados():
        lista_cadastrados.controls.clear()
        db_condos = carregar_dados_fluxoderotas("fluxoderotas_config/condominios") or {}
        
        for nome, info in db_condos.items():
            if info.get("tipo") == "multi_portarias":
                lista_cadastrados.controls.append(
                    ft.Container(
                        padding=10, bgcolor="#333333", border_radius=8,
                        content=ft.Row([
                            ft.Icon(ft.icons.BUSINESS, color="orange"),
                            ft.Text(nome, weight="bold", expand=True),
                            ft.Text(f"{len(info.get('enderecos', []))} Blocos", size=12),
                        ])
                    )
                )
        page.update()

    # --- BOTÕES ---
    btn_salvar = ft.ElevatedButton("SALVAR NA NUVEM", icon=ft.icons.CLOUD_UPLOAD, on_click=salvar_no_firebase, bgcolor="orange", color="white")

    # --- MONTAGEM DA INTERFACE ---
    alvo.controls.clear()
    alvo.controls.append(
        ft.Column([
            ft.Text("🏢 Cadastro por Blocos/Torres", size=22, weight="bold"),
            
            # Tutorial mantido como solicitado
            ft.ExpansionTile(
                leading=ft.Icon(ft.icons.LIGHTBULB_OUTLINE, color="orange"),
                title=ft.Text("Como funciona este cadastro?", weight="bold"),
                controls=[
                    ft.Container(
                        padding=15, bgcolor="#2A2A2A", border_radius=10,
                        content=ft.Text(
                            "Cadastre o nome do condomínio e a portaria principal. "
                            "Depois, adicione as ruas internas. O sistema agrupará "
                            "automaticamente as entregas desses endereços para a portaria.",
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
                    ft.Text("Logradouros e Blocos", size=14, color="orange", weight="bold"),
                    ft.Row([txt_rua, txt_num, txt_complemento]),
                    ft.Row([txt_bairro, txt_cidade, txt_cep]),
                    ft.ElevatedButton(
                        "ADICIONAR BLOCO À LISTA", 
                        icon=ft.icons.ADD, 
                        on_click=adicionar_endereco_lista
                    ),
                ])
            ),
            
            ft.Text("Itens para Salvar:", size=16, weight="bold"),
            lista_view,
            btn_salvar,
            
            ft.Divider(height=30),
            ft.Text("🔍 Cadastros Existentes (Blocos)", size=18, weight="bold"),
            lista_cadastrados
        ], scroll=ft.ScrollMode.AUTO)
    )
    
    carregar_lista_cadastrados()
    page.update()