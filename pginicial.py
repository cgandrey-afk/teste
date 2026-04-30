import flet as ft
from funcoes import preparar_download_logic, iniciar_processamento_logic, salvar_arquivo_no_disco_logic, obter_nome_logado

def mostrar_aba_inicio(page, state, renderizar_conteudo):

    nome_usuario = obter_nome_logado(page)

    fp_importar = ft.FilePicker(on_result=lambda e: iniciar_processamento_logic(page, state, renderizar_conteudo))
    fp_exportar = ft.FilePicker(on_result=lambda e: salvar_arquivo_no_disco_logic(e, state))

    # Garanta que eles entrem no overlay da página principal
    page.overlay.append(fp_importar)
    page.overlay.append(fp_exportar)

    # Salve na sessão
    page.session.set("meu_file_picker", fp_importar)
    page.session.set("meu_file_picker_export", fp_exportar)   

    file_picker = page.session.get("meu_file_picker")
    file_picker_export = page.session.get("meu_file_picker_export")
    navegar = page.session.get("navegar_callback")


    foi_processado = state.get("processamento_concluido", False)
    df_result = state.get("df_processado")
    
    # --- BOTÕES ---
    btn_selecionar = ft.ElevatedButton(
        "1. Selecionar Planilha da Shopee",
        icon=ft.icons.UPLOAD_FILE,
        on_click=lambda _: file_picker.pick_files(allowed_extensions=["xlsx", "xls"]),
        width=350, height=50
    )



    botoes_finais = ft.Row([
        ft.ElevatedButton("📍 Ver Mapa", icon=ft.icons.MAP, 
                          on_click=lambda _: navegar("📍 Mapa"), width=170),
        ft.ElevatedButton("📥 Baixar", icon=ft.icons.DOWNLOAD,
                          on_click=lambda e: preparar_download_logic(e, state, file_picker_export), width=170),
    ], alignment=ft.MainAxisAlignment.CENTER, visible=foi_processado)

    # --- ÁREA DE DESENHO (RESULTADOS) ---
    coluna_resultados = ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    if foi_processado and df_result is not None:
        # 1. Reset visual: garante que a coluna de resultados comece do zero antes de desenhar
        coluna_resultados.controls.clear() 

        # Mostra o total de paradas (linhas do dataframe final)
        coluna_resultados.controls.append(
            ft.Text(f"✅ Total: {len(df_result)} Paradas", size=20, weight="bold", color="orange")
        )

        # Usamos enumerate para criar o número da parada (1, 2, 3...)
        for i, (_, linha) in enumerate(df_result.iterrows(), start=1):
            # 1. Dados da linha principal
            sequencia = str(linha.get("Sequence", ""))
            endereco = str(linha.get("Destination Address", ""))
            
            # 2. Dados da linha secundária (Bairro, City, CEP)
            bairro = str(linha.get("Bairro", "")).upper()
            cidade = str(linha.get("City", "")).upper()
            cep = str(linha.get("Zipcode/Postal code", ""))
            info_detalhada = f"{bairro} - {cidade} | CEP: {cep}"
            
            coluna_resultados.controls.append(
                ft.Container(
                    content=ft.Row([
                        # Marcador com o NÚMERO DA PARADA
                        ft.Container(
                            content=ft.Text(str(i), color="white", weight="bold", size=14),
                            alignment=ft.alignment.center,
                            width=30,
                            height=30,
                            bgcolor="red",
                            border_radius=15,
                        ),
                        # Coluna de texto (Sequência + Endereço com 📍 / Detalhes embaixo)
                        ft.Column([
                            ft.Text(
                                f"{sequencia} {endereco}", # Mantém o 📍 que já vem no 'endereco'
                                size=14, 
                                weight="bold",
                                color="white"
                            ),
                            ft.Text(
                                info_detalhada,
                                size=11,
                                color="grey700",
                                italic=True
                            ),
                        ], spacing=2, expand=True),
                    ]),
                    padding=12,
                    border=ft.border.all(1, "white24"),
                    border_radius=8,
                    bgcolor="white10"
                )
            )
            
    return ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text(f"Bem-vindo, {nome_usuario}!",  color="orange", size=32, weight="bold"),
            ft.Text(state.get("nome_arquivo", ""), color="orange", size=12),
            ft.Divider(height=10, color="transparent"),
            btn_selecionar,

            botoes_finais,
            ft.Divider(height=20, visible=foi_processado),
            coluna_resultados 
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
    )