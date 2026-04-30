import flet as ft
import time
from datetime import datetime
# Importação das tuas funções originais do funcoes.py
from funcoes import verificar_email_existente, criar_novo_usuario

def mostrar_tela_cadastro(page: ft.Page, mudar_tela_callback):
    """
    Renderiza a interface de criação de conta no Flet.
    """
    
    # --- CAMPOS DE ENTRADA ---
    txt_nome = ft.TextField(
        label="Nome Completo",
        hint_text="Ex: Carlos Costa",
        border_color="orange",
        prefix_icon=ft.Icons.PERSON_OUTLINED,
        on_submit=lambda _: txt_email.focus()
    )
    
    txt_email = ft.TextField(
        label="E-mail",
        hint_text="seu@email.com",
        border_color="orange",
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        on_submit=lambda _: txt_senha.focus()
    )
    
    txt_senha = ft.TextField(
        label="Senha",
        password=True,
        can_reveal_password=True,
        border_color="orange",
        prefix_icon=ft.Icons.LOCK_OUTLINED,
        on_submit=lambda _: txt_confirmar.focus()
    )
    
    txt_confirmar = ft.TextField(
        label="Confirme a Senha",
        password=True,
        can_reveal_password=True,
        border_color="orange",
        prefix_icon=ft.Icons.LOCK_RESET_OUTLINED
    )

    lbl_erro = ft.Text("", color="red", weight="bold")

    def realizar_cadastro(e):
        # Feedback visual de carregamento
        btn_registrar.disabled = True
        btn_registrar.text = "CONSULTANDO..."
        lbl_erro.value = ""
        page.update()

        nome = txt_nome.value.strip()
        email = txt_email.value.lower().strip()
        senha = txt_senha.value
        confirmar = txt_confirmar.value

        # Validações básicas
        if not nome or not email or not senha:
            lbl_erro.value = "⚠️ Preencha todos os campos obrigatórios."
        elif senha != confirmar:
            lbl_erro.value = "❌ As senhas não coincidem."
        elif "@" not in email:
            lbl_erro.value = "❌ Digite um e-mail válido."
        else:
            try:
                if verificar_email_existente(email):
                    lbl_erro.value = f"⚠️ O e-mail {email} já está cadastrado."
                else:
                    dados = {
                        "nome": nome,
                        "email": email,
                        "senha": senha,
                        "nivel": "usuario",
                        "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "pendente"
                    }
                    
                    if criar_novo_usuario(dados):
                        page.overlay.append(
                            ft.SnackBar(ft.Text(f"✅ Conta de {nome} criada com sucesso!"), bgcolor="green")
                        )
                        page.update()
                        time.sleep(2)
                        mudar_tela_callback("🏠 Início") # Volta para a home/login
                        return
                    else:
                        lbl_erro.value = "❌ Erro ao conectar com o banco de dados."
            except Exception as ex:
                lbl_erro.value = f"❌ Erro técnico: {ex}"

        # Restaura o botão se houver erro
        btn_registrar.disabled = False
        btn_registrar.text = "SOLICITAR ACESSO"
        page.update()

    btn_registrar = ft.ElevatedButton(
        text="SOLICITAR ACESSO",
        bgcolor="orange",
        color="white",
        height=50,
        on_click=realizar_cadastro
    )

    # --- LAYOUT DA TELA ---
    return ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            width=450,
            spacing=20,
            controls=[
                ft.Icon(ft.Icons.PERSON_ADD_ROUNDED, size=60, color="orange"),
                ft.Text("📝 Criar Nova Conta", size=28, weight="bold"),
                ft.Text(
                    "Preencha os dados para solicitar acesso ao sistema",
                    color="grey",
                    text_align="center"
                ),
                ft.Divider(height=10, color="transparent"),
                txt_nome,
                txt_email,
                ft.Row([txt_senha, txt_confirmar], spacing=10),
                lbl_erro,
                btn_registrar,
                ft.TextButton(
                    "⬅️ Voltar para o Início", 
                    on_click=lambda _: mudar_tela_callback("🏠 Início")
                ),
                ft.Text("v 5.6.1 - Montana Edition", size=10, color="grey")
            ]
        )
    )