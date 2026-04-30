import flet as ft
from datetime import datetime
from funcoes import (
    carregar_lista_cadastrados,    
    atualizar_lista_visual,
    cancelar_edicao,
    adicionar_endereco_lista,    
    salvar_condo_completo,
    excluir_grupo
)



def mostrar_aba_condos(page: ft.Page, alvo: ft.Column):
    alvo.controls.clear() # Limpa o menu anterior
    
    # 1. Definimos a função de voltar com o import interno para evitar erro circular
    def voltar(e):
        from interface_seletor import mostrar_seletor_condominios
        mostrar_seletor_condominios(page, alvo)

    # 2. Criamos o objeto do botão
    btn_voltar = ft.ElevatedButton(
        "Voltar", 
        icon=ft.icons.ARROW_BACK, 
        icon_color="orange",
        on_click=voltar # Chama a função que criamos acima
    )
    
    editando = ft.Ref[bool]()
    # --- ESTADO LOCAL ---
    if not page.session.get("temp_enderecos_grupo"):
        page.session.set("temp_enderecos_grupo", [])
    
    
    
    # --- ELEMENTOS VISUAIS ---
    txt_nome_grupo = ft.TextField(label="Nome do Condomínio", border_color="orange", expand=True)
    txt_portaria = ft.TextField(label="Link Portaria (Maps/Waze)", border_color="orange", expand=True)
    txt_rua = ft.TextField(label="Rua", border_color="orange", expand=True)
    txt_num = ft.TextField(label="Nº", border_color="orange", width=80)
    txt_bairro = ft.TextField(label="Bairro", border_color="orange", expand=True)
    txt_cidade = ft.TextField(label="Cidade", border_color="orange", expand=True)
    
    page.session.set("ref_txt_rua", txt_rua)
    page.session.set("ref_txt_num", txt_num)
    page.session.set("ref_txt_bairro", txt_bairro)
    page.session.set("ref_txt_cidade", txt_cidade)
    
    btn_add_lista = ft.ElevatedButton(
        "ADICIONAR À LISTA", 
        icon=ft.icons.ADD, 
        on_click=lambda _: adicionar_endereco_lista(
            page, txt_rua, txt_num, txt_bairro, txt_cidade, atualizar_lista_visual, lista_view
        )
    )
    page.session.set("ref_btn_add", btn_add_lista)

    lista_view = ft.Column() 
    lista_cadastrados = ft.Column()

    # 1. DEFINIÇÃO DOS BOTÕES DE AÇÃO (Antes da montagem)
    btn_cancelar = ft.OutlinedButton(
        "CANCELAR EDIÇÃO", 
        icon=ft.icons.CANCEL, 
        visible=False, # Começa invisível
        style=ft.ButtonStyle(color="red"),
        on_click=lambda _: cancelar_edicao(
            page, 
            txt_nome_grupo, 
            txt_portaria, 
            txt_bairro,     # 4º
            txt_rua,        # 5º
            txt_num,        # 6º
            txt_cidade,     # 7º
            btn_cancelar,   # 8º - AGORA BATE COM A FUNÇÃO
            atualizar_lista_visual, 
            lista_view
        )
        
    )
        
    btn_salvar = ft.ElevatedButton(
        "SALVAR NA NUVEM", 
        icon=ft.icons.CLOUD_UPLOAD, 
        bgcolor="orange", 
        color="white", 
        expand=True,
        on_click = lambda _: salvar_condo_completo(
        page, 
        txt_nome_grupo, 
        txt_portaria, 
        lista_cadastrados, 
        atualizar_lista_visual, 
        excluir_grupo, 
        btn_cancelar, 
        lista_view
        )
            
    )
    
    # --- MONTAGEM DO CONTEÚDO NO ALVO ---
    alvo.controls.append(        
        ft.Column([
            btn_voltar, 
            ft.Text("🏢 Cadastro de Condomínios de Apartamento", size=22, weight="bold"),
            ft.Text("💡 Cadastre diferentes logradouros que pertencem ao mesmo condomínio e possuem portaria única para entrega.", 
                    size=12, weight="italic"),
            ft.ExpansionTile(
                title=ft.Text("📖 Como funciona o Cadastro de Condomínios de Apartamento?", color="orange", weight="bold"),
                subtitle=ft.Text("Clique para entender como agrupar suas entregas e economizar tempo."),
                controls=[
                    ft.Container(
                        padding=20,
                        bgcolor="#2A2A2A",
                        border_radius=10,
                        content=ft.Column([
                            ft.Text(
                                "Esta tela permite que você ensine ao sistema quais ruas e números pertencem a um mesmo condomínio ou conjunto residencial.",
                                size=14,
                            ),
                            ft.Text("1. Identificação Principal", weight="bold", color="orange"),
                            ft.Text(
                                "• Nome: Escolha um nome fácil (ex: Residencial Maria Tereza).\n"
                                "• Portaria Principal: O endereço onde você estaciona (ex: Rua Jornalista Ernesto Napoli, 726). O mapa será direcionado para cá.",
                                size=14,
                            ),
                            ft.Text("2. Logradouros ", weight="bold", color="orange"),
                            ft.Text(
                                "Cadastre o nome do condomínio e a portaria principal. Depois, adicione as ruas internas. "
                                "O sistema agrupará automaticamente as entregas desses endereços para a portaria.\n\n"
                                "Dica: Não precisa cadastrar tudo de uma vez; vá adicionando conforme as ruas aparecerem nas suas rotas.",
                                size=14,
                            ),
                            ft.Text("3. Salvando na Nuvem", weight="bold", color="orange"),
                            ft.Text(
                                "Após adicionar as ruas, clique em SALVAR NA NUVEM. Os dados ficam sincronizados e você pode editá-los quando quiser.",
                                size=14,
                            ),
                            ft.Divider(color="white24"),
                            ft.Text(
                                "🚚 Por que usar isso? Em vez de 10 paradas diferentes, o sistema mostrará uma única parada na portaria com o total de pacotes. Menos manobras, mais entregas!",
                                size=14,
                                italic=True,
                                color="green"
                            ),
                        ], spacing=10)
                    )
                ]
            ),
            ft.Divider(color="orange"),
            ft.Row([txt_nome_grupo, txt_portaria]),
            ft.Container(
                bgcolor="#2A2A2A", padding=15, border_radius=10,
                content=ft.Column([
                    ft.Text("Logradouros", size=14, color="orange"),
                    ft.Row([txt_rua, txt_num, txt_bairro, txt_cidade]),
                    ft.ElevatedButton(
                    "ADICIONAR À LISTA", 
                    icon=ft.icons.ADD, 
                    on_click=lambda _: adicionar_endereco_lista(
                        page, 
                        txt_rua, 
                        txt_num, 
                        txt_bairro, 
                        txt_cidade, 
                        atualizar_lista_visual, # Aqui passamos a FUNÇÃO
                        lista_view              # Aqui passamos a LISTA VISUAL
                        
                    )
                    
                ),
                ])
            ),
            lista_view,
            # 2. COLOCANDO OS BOTÕES LADO A LADO
            ft.Row([btn_salvar, btn_cancelar]), 
            
            ft.Divider(height=30),
            ft.Text("🔍 Condomínios Cadastrados", size=18, weight="bold"),
            lista_cadastrados
        ], scroll=ft.ScrollMode.AUTO)
    )


    
    # Inicialização da tela
    carregar_lista_cadastrados(
    page=page,
    lista_cadastrados=lista_cadastrados,
    txt_nome_grupo=txt_nome_grupo,
    txt_portaria=txt_portaria,
    btn_cancelar=btn_cancelar,
    atualizar_lista_visual_fn=atualizar_lista_visual,
    excluir_grupo_fn=excluir_grupo,
    lista_view=lista_view  # <--- ADICIONE ESTA LINHA AQUI
)
    page.update()