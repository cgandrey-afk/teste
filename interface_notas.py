import flet as ft
from funcoes import (
    carregar_dados_fluxoderotas, 
    salvar_dados_fluxoderotas,
    padronizar_complemento
)

def mostrar_aba_notas(page: ft.Page):
    """
    Interface para gerenciamento de notas e alertas adaptada para Flet.
    Mantém a lógica de chaves compostas para o banco de dados 'observacoes'.
    """
    
    # --- BUSCA INICIAL NA NUVEM ---
    banco = carregar_dados_fluxoderotas("observacoes")

    # --- CAMPOS DE ENTRADA (MANTENDO LÓGICA ORIGINAL) ---
    txt_rua = ft.TextField(label="Rua *", border_color="orange", capitalizaton=ft.TextCapitalization.CHARACTERS)
    txt_num = ft.TextField(label="Número *", border_color="orange")
    txt_comp = ft.TextField(label="Complemento", border_color="orange", capitalizaton=ft.TextCapitalization.CHARACTERS)
    txt_bairro = ft.TextField(label="Bairro *", border_color="orange", capitalizaton=ft.TextCapitalization.CHARACTERS)
    
    # Campo da Nota (O "Alerta")
    txt_nota_texto = ft.TextField(
        label="Nota/Alerta (Ex: CUIDADO CÃO, GOLPE, PORTÃO MARROM)",
        multiline=True,
        min_lines=2,
        border_color="orange"
    )

    def mostrar_snack(texto, cor):
        page.overlay.append(ft.SnackBar(ft.Text(texto), bgcolor=cor, open=True))
        page.update()

    def salvar_nota_evento(e):
        # Validação Idêntica à Original
        rua_in = txt_rua.value.upper().strip()
        num_in = txt_num.value.strip()
        bairro_in = txt_bairro.value.upper().strip()
        nota_raw = txt_nota_texto.value.upper().strip()

        if not rua_in or not num_in or not bairro_in or not nota_raw:
            mostrar_snack("⚠️ Rua, Número, Bairro e Nota são obrigatórios!", "red")
            return

        # Limpeza de prefixos conforme sua lógica original
        nota_final = nota_raw.replace("🏠 ", "").replace("📌 ", "").upper()
        
        # Criação da Chave Composta (Logica Crucial)
        complemento_limpo = padronizar_complemento(txt_comp.value)
        chave = f"{rua_in}|{num_in}|{complemento_limpo}"
        
        # Salva no dicionário local e sobe para o Firebase
        banco[chave] = f"{nota_final} ({bairro_in})"
        
        if salvar_dados_fluxoderotas(banco, "observacoes"):
            mostrar_snack("✅ Nota salva com sucesso!", "green")
            # Limpa campos
            for campo in [txt_rua, txt_num, txt_comp, txt_bairro, txt_nota_texto]:
                campo.value = ""
            page.update()
            # O ideal aqui é disparar um refresh na lista abaixo

    def excluir_nota(chave):
        if chave in banco:
            del banco[chave]
            if salvar_dados_fluxoderotas(banco, "observacoes"):
                mostrar_snack("Nota removida.", "orange")
                page.update()

    # --- LISTAGEM DE NOTAS ATIVAS ---
    def gerar_lista_notas():
        if not banco:
            return ft.Text("Nenhuma nota cadastrada.", italic=True, color="grey")
        
        controles = []
        for chave, nota in list(banco.items()):
            partes = chave.split('|')
            # Reconstrói endereço visual: Rua, Num - Comp
            end_visual = f"{partes[0]}, {partes[1]}"
            if len(partes) > 2 and partes[2]: 
                end_visual += f" - {partes[2]}"
            
            # Lógica de cor original (GOLPE em vermelho)
            cor_alerta = ft.Colors.RED_400 if "GOLPE" in nota else ft.Colors.BLUE_400

            controles.append(
                ft.Container(
                    padding=10,
                    border=ft.border.all(1, "#444444"),
                    border_radius=8,
                    margin=ft.margin.only(bottom=10),
                    content=ft.Row([
                        ft.Column([
                            ft.Text(end_visual, weight="bold", size=14),
                            ft.Text(nota, color=cor_alerta, size=13),
                        ], expand=True),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE, 
                            icon_color="red", 
                            on_click=lambda _, c=chave: excluir_nota(c)
                        )
                    ])
                )
            )
        return ft.Column(controles, scroll=ft.ScrollMode.AUTO, max_height=400)

    # --- LAYOUT PRINCIPAL ---
    return ft.Container(
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.EDIT_NOTE, color="orange", size=30),
                ft.Text("Gerenciar Notas e Alertas", size=22, weight="bold"),
            ]),
            ft.Divider(color="orange"),
            
            # Formulário de Entrada
            ft.Text("🏠 Dados do Endereço", size=16, weight="w500"),
            txt_rua,
            ft.Row([txt_num, txt_comp], spacing=10),
            txt_bairro,
            ft.Divider(height=10, color="transparent"),
            
            ft.Text("📝 Conteúdo da Nota", size=16, weight="w500"),
            txt_nota_texto,
            
            ft.ElevatedButton(
                "SALVAR NOTA NA NUVEM",
                icon=ft.Icons.SAVE,
                bgcolor="orange",
                color="white",
                width=400,
                on_click=salvar_nota_evento
            ),
            
            ft.Divider(height=40),
            ft.Text("📋 Notas Ativas", size=18, weight="bold"),
            gerar_lista_notas()
        ], scroll=ft.ScrollMode.ALWAYS, expand=True)
    )