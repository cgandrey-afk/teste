import pandas as pd
import numpy as np
import json
import os
import hashlib
import re
from datetime import datetime
from difflib import SequenceMatcher
from num2words import num2words
from geopy.distance import geodesic
from google.cloud import firestore
from google.oauth2 import service_account
import flet as ft
import io
import uuid

# --- CONFIGURAÇÃO INICIAL FIREBASE ---
db = None
try:
    path_secrets = "secrets.toml" 
    if os.path.exists(path_secrets):
        import toml
        config = toml.load(path_secrets)
        fb_data = config["firestoredb"]
        private_key = fb_data["private_key"].replace("\\n", "\n")
        creds = service_account.Credentials.from_service_account_info({
            "type": fb_data["type"],
            "project_id": fb_data["project_id"],
            "private_key_id": fb_data["private_key_id"],
            "private_key": private_key,
            "client_email": fb_data["client_email"],
            "token_uri": fb_data["token_uri"],
        })
        db = firestore.Client(credentials=creds)
        print("CONEXAO: Firebase conectado com sucesso!")
except Exception as e:
    print(f"Erro Firebase: {e}")

# Função 1
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Função 2
def verificar_email_existente(email):
    try:
        if db:
            doc = db.collection("usuarios").document(email.lower().strip()).get()
            return doc.exists
        return False
    except: return False

# Função 3
def criar_novo_usuario(dados):
    try:
        if db:
            if 'nivel' not in dados: dados['nivel'] = 'usuario'
            dados['senha'] = criptografar_senha(dados['senha'])
            db.collection("usuarios").document(dados['email']).set(dados)
            return True
        return False
    except: return False

# Função 4
def carregar_dados_fluxoderotas(caminho):
    try:
        doc_ref = db.document(caminho)
        doc = doc_ref.get()
        if doc.exists:
            dados = doc.to_dict()
            # Se o documento existe mas não tem campos, dados será {}
            return dados if dados else {}
        return {}
    except Exception as e:
        print(f"Erro ao ler Firebase: {e}")
        return {}

# Função 5
def salvar_dados_db(colecao, documento, dados):
    try:
        if db:
            db.collection(colecao).document(documento).set(dados, merge=True)
            return True
        return False
    except: return False

# Função 6
def extrair_numero(texto):
    """
    Mantém a lógica exata:
    1. Limpa pontuação (vírgula e ponto) para evitar que o número fique grudado.
    2. Busca o primeiro conjunto de dígitos que pode ter uma letra opcional.
    """
    if pd.isna(texto): 
        return ""
    
    # 1. Normaliza o texto para maiúsculo e remove separadores
    # Isso garante que 'RUA EMA,150' vire 'RUA EMA 150' antes da busca
    t = str(texto).upper().replace(',', ' ').replace('.', ' ')
    
    # 2. Regex de busca:
    # \b      -> Fronteira de palavra (garante que não pegue números no meio de palavras)
    # \d+     -> Um ou mais dígitos
    # [A-Z]?  -> Uma letra opcional (ex: captura o 'B' em '150B')
    # \b      -> Fronteira final
    match = re.search(r'\b(\d+[A-Z]?)\b', t)
    
    # Retorna o que foi encontrado ou vazio se não houver número
    return match.group(1) if match else ""

# Função 7
def padronizar_complemento(texto):
    """
    Mantém a lógica exata:
    1. Remove traços e pontos que costumam separar o número do AP (ex: AP-12).
    2. Encurta termos longos para o padrão do seu agrupador (AP, BL).
    """
    if not texto: 
        return ""
    
    # Remove pontuação básica para unificar formatos (ex: 'AP-12' vira 'AP 12')
    t = str(texto).upper().replace('-', ' ').replace('.', '').strip()
    
    # Padronização de termos para economizar espaço e facilitar o agrupamento
    # APARTAMENTO/APTO/APT -> AP
    t = re.sub(r'\b(APARTAMENTO|APTO|APT)\b', 'AP', t)
    
    # BLOCO -> BL
    t = re.sub(r'\b(BLOCO)\b', 'BL', t)
    
    # Remove espaços duplos que possam ter surgido
    t = re.sub(r'\s+', ' ', t).strip()
    
    return t

# Função 8
def eh_nome_rua_generico(nome_rua):
    """
    Mantém a trava de segurança para nomes numéricos ou genéricos.
    Se retornar True, o agrupador exigirá que o bairro seja idêntico.
    """
    if not nome_rua: 
        return False
    
    # Normaliza para comparação (Maiúsculas e sem espaços extras)
    n = str(nome_rua).upper().strip()
    
    # 1. Se o nome da rua for apenas números (Ex: "10", "1")
    if n.isdigit(): 
        return True
    
    # 2. Lista expandida de nomes numéricos e genéricos (Idêntica ao Streamlit)
    nomes_genericos = [
        "UM", "DOIS", "TRES", "QUATRO", "CINCO", "SEIS", "SETE", "OITO", "NOVE", "DEZ",
        "ONZE", "DOZE", "TREZE", "QUATORZE", "QUINZE", "DEZESSEIS", "DEZESSETE", "DEZOITO", "DEZENOVE", "VINTE",
        "PRIMEIRA", "SEGUNDA", "TERCEIRA", "QUARTA", "QUINTA", "PROJETADA", "SEM NOME",
        "RUA A", "RUA B", "RUA C", "RUA D", "RUA E"
    ]
    
    # Verifica se o nome da rua contém EXATAMENTE uma dessas palavras isoladas
    # O uso do \b garante que "RUA DEZ" seja genérico, mas "DEZEMBRO" não.
    for g in nomes_genericos:
        if re.search(rf'\b{g}\b', n):
            return True
            
    return False

# Função 9
def converter_numero_da_rua_ate_100(texto):
    """
    Mantém a lógica exata: Converte 'RUA 10' em 'RUA DEZ'.
    Isso é vital para que o agrupamento não se perca entre números e extensos.
    """
    if not texto: 
        return ""
    
    # Normaliza para garantir que a Regex pegue tudo em maiúsculo
    t = str(texto).upper().strip()

    def realizar_conversao(match):
        # match.group(1) é a palavra "RUA " ou similar
        # match.group(2) é o número encontrado logo depois
        palavra_chave = match.group(1)
        num_str = match.group(2)
        
        try:
            num_int = int(num_str)
            # Mantém a trava de segurança (1 a 100) para evitar anos ou números de casa
            if 1 <= num_int <= 100:
                extenso = num2words(num_int, lang='pt_BR').upper()
                return f"{palavra_chave}{extenso}"
            else:
                # Se for maior que 100, devolve o número original (Ex: RUA 500)
                return f"{palavra_chave}{num_str}"
        except:
            # Em caso de erro na conversão, não quebra o código, apenas devolve o original
            return f"{palavra_chave}{num_str}"

    # REGEX IGUAL À DO STREAMLIT:
    # (\bRUA\s+) -> Grupo 1: Palavra RUA com limite de borda e espaços
    # (\d+)      -> Grupo 2: Sequência de dígitos
    # (?=\b)     -> Garante que não pegue números no meio de palavras
    padrao = r'(\bRUA\s+)(\d+)(?=\b)'

    # Executa a substituição usando a função de callback
    t = re.sub(padrao, realizar_conversao, t, flags=re.IGNORECASE)
    
    return t

# Função 10 Abre o seletor para o usuário escolher onde salvar
def preparar_download_logic(e, state, file_picker_export):
    if state.get("df_processado") is not None:
        # Pega o nome original (ex: dados.xlsx) e remove a extensão .xlsx para não repetir
        nome_original = state.get("nome_arquivo", "planilha")
        nome_limpo = nome_original.replace(".xlsx", "").replace(".xls", "")
        
        # Define o nome final como rota_NOME_DA_PLANILHA.xlsx
        novo_nome = f"rota_{nome_limpo}.xlsx"
        
        file_picker_export.save_file(
            file_name=novo_nome,
            allowed_extensions=["xlsx"]
        )

# Função 11 Grava o arquivo físico no computador
def salvar_arquivo_no_disco_logic(e, state):
    if e.path:
        try:
            df = state["df_processado"]
            df.to_excel(e.path, index=False)
            print(f"Sucesso: Arquivo salvo em {e.path}")
        except Exception as ex:
            print(f"Erro ao salvar: {ex}")
    if e.path:
        try:
            df = state["df_processado"]
            df.to_excel(e.path, index=False)
            print(f"Sucesso: Arquivo salvo em {e.path}")
        except Exception as ex:
            print(f"Erro ao salvar: {ex}")

# Função 12
def extrair_bloco(texto):
    """
    Mantém a lógica exata de extração:
    1. Identifica palavras-chave (BLOCO, TORRE, AP).
    2. Se não houver palavra-chave, busca letra isolada após o número (ex: 150-B).
    """
    if pd.isna(texto): 
        return ""
    
    # Normaliza: remove vírgulas e pontos para facilitar a busca por bordas de palavras (\b)
    t = str(texto).upper().replace(',', ' ').replace('.', ' ')
    
    # 1. Tenta o padrão clássico: PALAVRA + IDENTIFICADOR
    # BLOCO, BLC, BL ou PORTARIA seguidos de letras/números
    bl_match = re.search(r'\b(?:BLOCO|BLC|BL|PORTARIA)\s*([A-Z0-9/]+)\b', t)
    # TORRE ou T seguidos de letras/números
    tr_match = re.search(r'\b(?:TORRE|T)\s*([A-Z0-9/]+)\b', t)
    
    # Nota: AP_MATCH é extraído mas não é usado na composição final de 'partes' no seu original
    # ap_match = re.search(r'\b(?:AP|APT|APTO|UNIDADE)\s*([0-9/]+)\b', t)

    partes = []
    if bl_match: 
        partes.append(f"BL {bl_match.group(1)}")
    if tr_match: 
        partes.append(f"TORRE {tr_match.group(1)}")
    
    # 2. Se não achou "BLOCO" explicitamente, tenta pegar letra após o número da casa
    # Ex: Rua Ema, 150 - B -> Pega o "B"
    if not partes:
        # Busca por: NUMERO + (HIFEN/BARRA opcional) + LETRA ISOLADA
        match_isolado = re.search(r'\d+\s*[-/]?\s*\b([A-Z])\b', t)
        if match_isolado:
            partes.append(f"BL {match_isolado.group(1)}")

    # Retorna os blocos/torres encontrados unidos por espaço
    return " ".join(partes)

# Função 13
def sao_ruas_similares(rua1, rua2):
    """
    Mantém a lógica de comparação por similaridade.
    Utiliza o SequenceMatcher para identificar se duas ruas são a mesma,
    mesmo com pequenas variações de digitação.
    """
    # 1. Comparação exata (mais rápida)
    if rua1 == rua2: 
        return True
    
    # 2. Comparação por proximidade (Fuzzy)
    # O ratio > 0.85 é o padrão que você usa para garantir que "Rua Ema" e "Rua Emaa" sejam a mesma.
    return SequenceMatcher(None, str(rua1), str(rua2)).ratio() > 0.85

# Função 14
def limpar_duplicidade_numero(texto):
    """
    Mantém a lógica exata:
    1. Normaliza separadores (vírgula/ponto para espaço).
    2. Remove espaços duplos.
    3. Elimina números repetidos sequencialmente (ex: '150 150' -> '150').
    """
    if pd.isna(texto): 
        return ""
    
    # Converte para string e coloca em maiúsculo
    texto = str(texto).upper().strip()
    
    # 1. Remove vírgulas e pontos para não interferir na posição do número
    # Isso evita que '150, 150' falhe na detecção de duplicidade
    texto = texto.replace(',', ' ').replace('.', ' ')
    
    # 2. Remove espaços duplos que sobraram da limpeza anterior
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # 3. Remove números repetidos (Regex de Backreference)
    # \b(\d+[A-Z]?) -> Grupo 1: Número seguido opcionalmente de uma letra (ex: 150 ou 150A)
    # [\s]+         -> Um ou mais espaços
    # \1            -> Exige que o que foi achado no Grupo 1 se repita exatamente igual
    # \b            -> Fronteira de palavra para garantir que não pegue parte de outro número
    texto = re.sub(r'\b(\d+[A-Z]?)[\s]+\1\b', r'\1', texto)
    
    return texto

# Função 15
def limpar_rua_com_bairro(endereco, bairro_oficial):
    """
    Mantém a lógica exata:
    1. Limpa pontuação.
    2. Corta o texto em termos de 'sujeira' (AP, BLOCO, etc).
    3. Remove o nome do bairro do meio do endereço (usando prefixos JD, PQ, etc).
    4. Remove o número da casa e tudo que vem depois para isolar a Rua Base.
    """
    if pd.isna(endereco): 
        return ""
    
    t = str(endereco).upper().strip()
    
    # 1. Limpeza inicial de pontuação
    t = t.replace(',', ' ').replace('.', ' ')
    
    # 2. Remover termos de "sujeira" que costumam grudar no nome da rua
    # Se encontrar AP, BLOCO ou EDIFICIO, cortamos tudo o que vem depois
    termos_corte = [r'\bAP\b', r'\bAPT\b', r'\bAPTO\b', r'\bEDIFICIO\b', r'\bED\b', r'\bCONDOMINIO\b', r'\bCD\b']
    for termo in termos_corte:
        t = re.split(termo, t)[0].strip()

    # 3. Lista de prefixos de bairro (Padronização Montana/Shopee)
    prefixos = {
        "JARDIM": ["JD", "JARD", "JARDIM"],
        "PARQUE": ["PQ", "PRQ", "PARQUE"],
        "VILA": ["V", "VL", "VILA"],
        "RESIDENCIAL": ["RES", "RESI", "RESIDENCIAL"]
    }

    bairro = str(bairro_oficial).upper().strip() if pd.notna(bairro_oficial) else ""
    
    if bairro:
        # Tenta remover o nome do bairro como ele está no banco
        t = t.replace(bairro, "")
        
        # Tenta remover variações (Ex: se o bairro é JARDIM AEROPORTO, remove JD AEROPORTO)
        for nome_cheio, abrevs in prefixos.items():
            if bairro.startswith(nome_cheio):
                nome_base_bairro = bairro.replace(nome_cheio, "").strip()
                for abrev in abrevs:
                    # Remove a combinação da abreviação + o nome do bairro
                    t = t.replace(f"{abrev} {nome_base_bairro}", "")

    # 4. Limpeza de espaços duplos
    t = re.sub(r'\s+', ' ', t).strip()
    
    # 5. Remove o número da casa e qualquer coisa que venha depois dele
    # Isso é essencial para sobrar apenas "RUA EMA" em vez de "RUA EMA 150"
    t = re.sub(r'\s\d+.*', '', t)
    
    # Chama a normalização final (Certifique-se de que normalizar_rua existe no funcoes.py)
    return normalizar_rua(t)

# Função 16
def normalizar_rua(texto):
    """
    Mantém a lógica exata:
    1. Padroniza prefixos (R, AV, DR, PROF).
    2. Remove termos residuais de condomínio/edifício que sobram no fim.
    3. Isola apenas o nome da rua, cortando qualquer número residencial.
    """
    if pd.isna(texto): 
        return ""
    
    # Normalização inicial: Maiúsculo e limpeza de pontuação
    t = str(texto).upper().replace(',', ' ').replace('.', ' ').strip()
    
    # 1. Padronização de prefixos (usando \b para garantir palavras inteiras)
    subs = {
        # Logradouros (Tipos de via)
        r'\bR\b': 'RUA',
        r'\bAV\b': 'AVENIDA',
        r'\bAL\b': 'ALAMEDA',
        r'\bEST\b': 'ESTRADA',
        r'\bTRAV\b': 'TRAVESSA',
        r'\bPC\b': 'PRACA',
        r'\bROD\b': 'RODOVIA',
        r'\bVCO\b': 'VICINAL',
        r'\bV\b': 'VIA', # Cuidado, \bV\b isolado
        
        # Títulos Profissionais e Acadêmicos
        r'\bDR\b': 'DOUTOR',
        r'\bDRA\b': 'DOUTORA',
        r'\bPROF\b': 'PROFESSOR',
        r'\bPROFA\b': 'PROFESSORA',
        r'\bENG\b': 'ENGENHEIRO',
        r'\bENGO\b': 'ENGENHEIRO',
        r'\bARQ\b': 'ARQUITETO',
        r'\bJORN\b': 'JORNALISTA',
        r'\bADV\b': 'ADVOGADO',
        r'\bMED\b': 'MEDICO',
        r'\bVET\b': 'VETERINARIO',
        r'\bME\b': 'MESTRE',
        
        # Títulos Militares
        r'\bMAL\b': 'MARECHAL',
        r'\bGEN\b': 'GENERAL',
        r'\bCEL\b': 'CORONEL',
        r'\bCAP\b': 'CAPITAO',
        r'\bSGT\b': 'SARGENTO',
        r'\bTEN\b': 'TENENTE',
        r'\bASP\b': 'ASPIRANTE',
        r'\bCABO\b': 'CABO',
        r'\bSOLD\b': 'SOLDADO',
        r'\bBRIG\b': 'BRIGADEIRO',
        r'\bALM\b': 'ALMIRANTE',
        
        # Títulos Políticos e Judiciários
        r'\bPRES\b': 'PRESIDENTE',
        r'\bGOV\b': 'GOVERNADOR',
        r'\bDEP\b': 'DEPUTADO',
        r'\bVEREAD\b': 'VEREADOR',
        r'\bMIN\b': 'MINISTRO',
        r'\bDES\b': 'DESEMBARGADOR',
        r'\bCONS\b': 'CONSELHEIRO',
        r'\bEMB\b': 'EMBAIXADOR',
        
        # Títulos Nobreza e Religiosos
        r'\bBAR\b': 'BARAO',
        r'\bVISC\b': 'VISCONDE',
        r'\bP\b': 'PADRE',
        r'\bPE\b': 'PADRE',
        r'\bBPO\b': 'BISPO',
        r'\bMONS\b': 'MONSENHOR',
        r'\bFREI\b': 'FREI',
        r'\bSTA\b': 'SANTA',
        r'\bSTO\b': 'SANTO',
        r'\bS\b': 'SAO'
    }
    for p, s in subs.items(): 
        t = re.sub(p, s, t)
        
    # 2. Limpeza de termos finais indesejados
    # Isso evita que o nome da rua fique "RUA TAL CONDOMINIO"
    travas_finais = [r'\bCONDOMINIO\b', r'\bEDIFICIO\b', r'\bED\b', r'\bAP\b']
    for trava in travas_finais:
        # O r'.*' remove a trava e TUDO que vier depois dela
        t = re.sub(trava + r'.*', '', t).strip()

    # 3. Pega apenas o que vem ANTES do primeiro número isolado
    # Exemplo: "AVENIDA PAPA JOAO PAULO II 150" -> "AVENIDA PAPA JOAO PAULO II"
    partes = re.split(r'\s\d+', t, maxsplit=1)
    
    return partes[0].strip()

# Função 17
def extrair_complemento_puro(texto):
    """
    Mantém a lógica exata:
    Localiza a primeira palavra-chave de complemento (AP, BLOCO, CASA, etc)
    e captura TUDO o que vier depois dela.
    Ex: "RUA EMA, 150 AP 12 BL B" -> "AP 12 BL B"
    """
    if pd.isna(texto): 
        return ""
    
    # O Regex busca a primeira ocorrência de um termo de moradia
    # \b          -> Fronteira de palavra (não pega 'CAP' como 'AP')
    # (APT|...)   -> Lista de termos que indicam início de complemento
    # \b          -> Fronteira final
    # .* -> O ponto e o asterisco garantem que pegue o resto da linha toda
    match = re.search(r'\b(APT|APTO|AP|BLOCO|BL|TORRE|CASA)\b.*', str(texto).upper())
    
    # Se der match, retorna o texto completo a partir da palavra encontrada
    return match.group(0).strip() if match else ""

# Função 18
def formatar_endereco_condo(texto):
    """
    Garante o padrão RUA, NUMERO BL X mesmo que digitado sem vírgula.
    Utiliza as funções auxiliares (normalizar_rua, extrair_numero, extrair_bloco).
    """
    if pd.isna(texto): 
        return ""
    
    # 1. Limpeza inicial de sujeira e espaços
    # Remove vírgulas existentes para reconstruir o endereço do zero no padrão correto
    t = str(texto).upper().replace(',', ' ').strip()
    t = re.sub(r'\s+', ' ', t)
    
    # 2. Extrai as partes separadamente usando as funções que já criamos
    rua = normalizar_rua(t)
    num = extrair_numero(t)
    bloco = extrair_bloco(t) # Captura BL A, TORRE 1, etc.
    
    if rua and num:
        # Monta o padrão clássico: RUA, NUMERO
        base = f"{rua}, {num}"
        
        # Se houver bloco ou torre, anexa ao final
        if bloco:
            # Segurança: Remove o bloco da 'base' caso a normalização da rua 
            # tenha deixado passar algum fragmento do bloco por engano
            base = base.replace(bloco, "").strip().rstrip(',')
            
            # Retorna o endereço formatado: RUA, NUMERO BL X
            return f"{base} {bloco}".strip()
            
        return base
    
    # Caso não consiga extrair rua ou número, retorna o texto original limpo
    return t

# Função 19
def verificar_separacao_bloco(row, db_condos):
    """
    Verifica se o endereço atual pertence a um condomínio que exige
    separação por bloco (ex: portarias diferentes ou blocos muito distantes).
    """
    # Cria a chave de busca combinando Rua e Número (ex: "RUA EMA, 150")
    rua_num = f"{row['Rua_Base']}, {row['Num_Casa']}".upper().strip()
    
    # Percorre o seu dicionário de base de dados de condomínios (db_condos)
    for info in db_condos.values():
        # Verifica se o condomínio está marcado com a flag de separação
        if info.get('tipo') == "separado_por_bloco":
            # Pega a lista de portarias cadastradas para esse condomínio
            # e garante que todas estejam em maiúsculo para comparação
            portarias = [str(p).upper() for p in info.get('portarias', [])]
            
            # Se o endereço da entrega (rua_num) estiver na lista de portarias desse prédio:
            if any(rua_num in p for p in portarias):
                return True
                
    # Se não encontrou o endereço na lista de 'especiais', retorna False (agrupamento normal)
    return False

# Função 20
def normalizar_termos_condo(texto):
    """
    Padroniza as nomenclaturas de condomínio para um formato único.
    BLOCO/BLC/BL -> 'BL'
    TORRE/T -> 'TORRE'
    Ex: 'BLOCO B' vira 'BL B' | 'T 1' vira 'TORRE 1'
    """
    if not texto: 
        return ""
    
    # 1. Limpeza inicial de pontuação
    t = str(texto).upper().replace(',', ' ').replace('.', ' ')
    
    # 2. Padroniza BLOCO usando o Grupo de Captura \2 para manter o nome/número do bloco
    # \b(BLOCO|BLC|BL) -> Grupo 1: As variações da palavra
    # \s* -> Espaços opcionais
    # ([A-Z0-9]+)      -> Grupo 2: O identificador (A, 1, B, etc)
    t = re.sub(r'\b(BLOCO|BLC|BL)\s*([A-Z0-9]+)\b', r'BL \2', t)
    
    # 3. Padroniza TORRE
    t = re.sub(r'\b(TORRE|T)\s*([A-Z0-9]+)\b', r'TORRE \2', t)
    
    # 4. Remove espaços duplos que possam ter surgido nas substituições
    return re.sub(r'\s+', ' ', t).strip()

# Função 21
def formatar_endereco_agrupado(row, db_condos):
    """
    Versão Flet da lógica de agrupamento.
    Mantém 100% a compatibilidade com a lógica que você já validou.
    """
    # 1. Preparação dos dados da planilha atual
    # Usamos o .get() para evitar erros caso a coluna falte na planilha da Shopee
    rua_planilha = str(row.get('Rua_Base', '')).upper().strip()
    num_planilha = str(row.get('Num_Casa', '')).upper().strip()
    bairro_planilha = str(row.get('Bairro', '')).upper().strip()
    cidade_planilha = str(row.get('City', '')).upper().strip()
    
    # Limpa CEP deixando apenas números
    cep_raw = str(row.get('Zipcode/Postal code', ''))
    cep_planilha = "".join(filter(str.isdigit, cep_raw))
    
    # Endereço completo original para filtros
    dest_address = str(row.get('Destination Address', ''))
    end_original = normalizar_termos_condo(dest_address)
    
    # --- TRAVAS DE RUA PURA ---
    travas_rua = ["VIELA", "CAMINHO", "CASA", "TERREO", "FUNDOS", "GARAGEM", "LOJA", "SALA"]
    if any(p in end_original for p in travas_rua):
        return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

    # 2. BUSCA NO CADASTRO DO FIREBASE (db_condos)
    for nome_grupo, info in db_condos.items():
        
        # CASO A: MULTI-RUAS (Ex: Maria Tereza, condomínios de casas)
        if info.get('tipo') == "multi_ruas":
            for item in info.get('enderecos', []):
                if not isinstance(item, dict): 
                    continue 

                # Extrai dados do cadastro
                rua_cad = str(item.get('rua', '')).upper().strip()
                num_cad = str(item.get('numero', '')).upper().strip()
                bairro_cad = str(item.get('bairro', '')).upper().strip()
                cidade_cad = str(item.get('cidade', '')).upper().strip()
                cep_cad = "".join(filter(str.isdigit, str(item.get('cep', ''))))

                # --- VALIDAÇÃO DE LOCALIDADE ---
                local_bate = False
                if cep_cad and cep_planilha == cep_cad:
                    local_bate = True
                elif cidade_planilha == cidade_cad:
                    # Verifica similaridade de bairro
                    if bairro_cad in bairro_planilha or bairro_planilha in bairro_cad:
                        local_bate = True
                    elif SequenceMatcher(None, bairro_planilha, bairro_cad).ratio() > 0.8:
                        local_bate = True

                # --- SE A LOCALIDADE BATEU, TESTA RUA E NÚMERO ---
                if local_bate:
                    if rua_planilha == rua_cad and num_planilha == num_cad:
                        portaria = str(info.get('portaria', '')).upper()
                        # Retorna o nome da portaria que você cadastrou no Flet
                        return f"📍 {portaria}"

        # CASO B: SEPARADO POR BLOCO (Edifícios/Torres)
        elif info.get('tipo') == "separado_por_bloco":
            bloco_planilha = normalizar_termos_condo(str(row.get('Bloco', '')))
            match_condo_base = False
            
            for portaria_cadastrada in info.get('portarias', []):
                p_cad_norm = normalizar_termos_condo(portaria_cadastrada)
                if rua_planilha in p_cad_norm and num_planilha in p_cad_norm:
                    match_condo_base = True
                    
                    # Lógica de Torre/Bloco
                    match_t_json = re.search(r'TORRE\s*([A-Z0-9]+)', p_cad_norm)
                    if match_t_json and f"TORRE {match_t_json.group(1)}" in bloco_planilha:
                        return f"📍 {rua_planilha}, {num_planilha} T{match_t_json.group(1)}"
                    
                    match_bl_json = re.search(r'BL\s*([A-Z0-9]+)', p_cad_norm)
                    if match_bl_json and f"BL {match_bl_json.group(1)}" in bloco_planilha:
                        return f"📍 {rua_planilha}, {num_planilha} BL {match_bl_json.group(1)}"
            
            if match_condo_base:
                return f"📍 {rua_planilha}, {num_planilha}"

    # 3. IDENTIFICAÇÃO GENÉRICA (Padrões comuns de condomínio não cadastrados)
    termos_condominio = [r'\bAP\b', r'\bAPT\b', r'\bAPTO\b', r'\bBL\b', r'\bBLOCO\b', r'\bTORRE\b', r'\bEDIFICIO\b']
    if any(re.search(p, end_original) for p in termos_condominio):
        return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

    # Retorno padrão se nada for encontrado
    return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

# Função 22
def montar_endereco_limpo(texto_completo, rua, num):
    """
    Mantém a lógica exata:
    1. Localiza o número da casa no texto original.
    2. Captura tudo o que vem DEPOIS do número (apartamento, bloco, torre).
    3. Monta o endereço final: RUA, NUMERO + COMPLEMENTO.
    """
    if not num:
        return f"{rua}".strip()

    # Escapa o número para evitar erros em caso de caracteres especiais (ex: 150-A)
    num_esc = re.escape(str(num))
    
    # Regex inteligente: 
    # Procura o número isolado (\b) e captura o resto da string (.*)
    # Ignora se há vírgula ou espaços entre o número e o complemento
    match = re.search(rf"\b{num_esc}\b\s*,?\s*(.*)", str(texto_completo).upper(), re.IGNORECASE)
    
    if match:
        sobra = match.group(1).strip()
        # Se houver algo após o número (ex: 'AP 12'), anexa à rua e número limpos
        if sobra:
            return f"{rua}, {num} {sobra}"
    
    # Se não houver complemento, retorna apenas o padrão RUA, NUMERO
    return f"{rua}, {num}"

# Função 23
def formatar_sequencia_visual(lista_seq):
    """
    Transforma uma lista de sequências em um resumo legível.
    Ex: [1, 2, 3, 5, 8, 9] -> "Qtd: 6 (1–3, 5, 8 e 9)"
    Também contabiliza pacotes sem número (Adds).
    """
    numeros, adds = [], 0
    
    # 1. Triagem inicial
    for s in lista_seq:
        s = str(s).strip()
        # Se for vazio ou hífen, conta como pacote extra sem número (Add)
        if not s or s == "-": 
            adds += 1
            continue
        
        # Extrai apenas os dígitos para evitar erro se houver letras
        n = "".join(filter(str.isdigit, s))
        if n: 
            numeros.append(int(n))
        else: 
            adds += 1

    # 2. Ordenação e remoção de duplicatas
    numeros = sorted(set(numeros))
    partes, i = [], 0
    
    # 3. Lógica de agrupamento de intervalos (Range)
    while i < len(numeros):
        ini = numeros[i]
        fim = ini
        # Enquanto o próximo número for a sequência exata do atual (+1)
        while i + 1 < len(numeros) and numeros[i + 1] == fim + 1:
            i += 1
            fim = numeros[i]
        
        # Formata a saída do grupo
        if ini == fim: 
            partes.append(f"{ini}")
        elif fim == ini + 1: 
            partes.append(f"{ini} e {fim}")
        else: 
            partes.append(f"{ini} ao {fim}")
        i += 1

    # 4. Construção do texto final
    total = len(numeros) + adds
    texto_numeros = ", ".join(partes)
    
    if adds > 0:
        # Se já tiver números, adiciona ", Adds: X". Se não, apenas "Adds: X"
        if texto_numeros:
            texto_final = f"{texto_numeros}, Adds: {adds}"
        else:
            texto_final = f"Adds: {adds}"
    else:
        texto_final = texto_numeros

    return f"Qtd Pacote: {total} - Ordem: ({texto_final})"

# Função 24
def aplicar_formatacao_final(row, notas_vivas):
    """
    Une a sequência dos pacotes com uma nota personalizada, se existir.
    Ex: "Interfone quebrado | Qtd: 3 (1-3)"
    """
    # 1. Gera o texto base com a contagem de pacotes
    texto = formatar_sequencia_visual(row['Sequence'])
    
    # 2. Varre as notas ativas (vindas do seu Firebase ou JSON de notas)
    for chave, nota in notas_vivas.items():
        try:
            # A chave é salva no formato "RUA|NUMERO|COMPLEMENTO"
            r, n, c = chave.split('|')
            
            # Validação tripla: Número igual, Complemento igual e Rua Similar (>80%)
            if (row['Num_Casa'] == n and 
                row['Comp_Padrao'] == c and 
                SequenceMatcher(None, row['Rua_Base'], r).ratio() > 0.8):
                
                # Se achou a nota, coloca ela na frente do texto da sequência
                return f"{nota} | {texto}"
        except:
            continue
            
    return texto

# Função 25
def verificar_nota_local(row, notas_vivas):
    """
    Função booleana para o Flet decidir se deve mudar a cor do card
    ou exibir um ícone de 'alerta' de nota.
    """
    for chave in notas_vivas.keys():
        try:
            r, n, c = chave.split('|')
            # Mesma lógica de validação de endereço
            if (row['Num_Casa'] == n and 
                row['Comp_Padrao'] == c and 
                SequenceMatcher(None, row['Rua_Base'], r).ratio() > 0.8):
                return True
        except:
            continue
            
    return False

# Função 26 - Adaptada para Flet com a inteligência completa do Streamlit
def processar_agrupamento(df_bruto, notas_vivas, db_condos):
    df = df_bruto.copy()
    
    # =========================================================
    # PASSO 1: PADRONIZAÇÃO TOTAL (RIGOROSAMENTE IGUAL)
    # =========================================================
    df['Destination Address'] = df['Destination Address'].apply(converter_numero_da_rua_ate_100)
    df['Destination Address'] = df['Destination Address'].apply(limpar_duplicidade_numero)
    df['Num_Casa'] = df['Destination Address'].apply(extrair_numero)    
    df['Rua_Base'] = df.apply(lambda r: limpar_rua_com_bairro(r['Destination Address'], r['Bairro']), axis=1)
    df['Comp_Padrao'] = df['Destination Address'].apply(extrair_complemento_puro).apply(padronizar_complemento)
    df['Bloco'] = df['Destination Address'].apply(extrair_bloco)
    df['Separar_Bloco'] = df.apply(lambda r: verificar_separacao_bloco(r, db_condos), axis=1)
    df['Endereco_Formatado'] = df.apply(lambda r: formatar_endereco_agrupado(r, db_condos), axis=1)    
    
    df['Tem_Minha_Nota'] = df.apply(lambda r: verificar_nota_local(r, notas_vivas), axis=1)

    # =========================================================
    # PASSO 2: LÓGICA DE AGRUPAMENTO HIERÁRQUICA
    # =========================================================
    group_ids = np.zeros(len(df))
    curr = 1

    # DEBUG DE CONEXÃO
    print(f"DEBUG: O banco db_condos tem {len(db_condos)} grupos cadastrados.")
    if len(db_condos) > 0:        
        dados_limpos = carregar_dados_fluxoderotas("fluxoderotas_config/condominios")
        print(f"DEBUG NOVO: {list(dados_limpos.keys())}")
    else:
        print("DEBUG: ALERTA! O banco de dados chegou VAZIO na função.")

    def norm_b(b):
        if not b: return ""
        t = str(b).upper().strip()
        t = re.sub(r'\b(JD|JARD)\b', 'JARDIM', t)
        t = re.sub(r'\b(V|VL)\b', 'VILA', t)
        t = re.sub(r'\b(PQ|PRQ)\b', 'PARQUE', t)
        t = re.sub(r'\b(RES|RESI)\b', 'RESIDENCIAL', t)
        return t

    for i in range(len(df)):
        if group_ids[i] == 0:
            group_ids[i] = curr
            row_i = df.iloc[i]
            
            rua_i = str(row_i['Rua_Base']).upper().strip()
            num_i = "".join(filter(str.isdigit, str(row_i['Num_Casa'])))
            bairro_i_norm = norm_b(row_i['Bairro'])
            nota_i = row_i['Tem_Minha_Nota']
            coord_i = (row_i['Latitude'], row_i['Longitude'])
            
            # RETORNO À LÓGICA ORIGINAL: Usa a função eh_nome_rua_generico para precisão
            is_gen_i = eh_nome_rua_generico(rua_i) 

            end_i = str(row_i['Endereco_Formatado']).upper().strip()
            # Mantemos a comparação sem espaços para evitar erros de digitação no Banco
            comparar_i = end_i.replace("📍", "").replace(" ", "")

            for j in range(i + 1, len(df)):
                if group_ids[j] != 0: continue
                row_j = df.iloc[j]
                
                rua_j = str(row_j['Rua_Base']).upper().strip()
                bairro_j_norm = norm_b(row_j['Bairro'])

                # --- TRAVA DE SEGURANÇA: RUAS GENÉRICAS ---
                if is_gen_i or eh_nome_rua_generico(rua_j):
                    if bairro_i_norm != bairro_j_norm:
                        continue 

                if nota_i != row_j['Tem_Minha_Nota']: continue

                # --- 2ª REGRA: BLOCOS E CONDOMÍNIOS (📍) ---
                end_j = str(row_j['Endereco_Formatado']).upper().strip()
                comparar_j = end_j.replace("📍", "").replace(" ", "")
                
                if (row_i['Separar_Bloco'] or row_j['Separar_Bloco'] or "📍" in end_i):
                    if comparar_i == comparar_j and comparar_i != "":
                        group_ids[j] = curr
                    continue 

                # --- 3ª REGRA: DISTÂNCIA GEOGRÁFICA ---
                num_j = "".join(filter(str.isdigit, str(row_j['Num_Casa'])))
                
                try:
                    distancia = geodesic(coord_i, (row_j['Latitude'], row_j['Longitude'])).meters
                    if distancia <= 100 and num_i == num_j and num_i != "":
                        if rua_i == rua_j or is_gen_i or eh_nome_rua_generico(rua_j):
                            group_ids[j] = curr
                        elif SequenceMatcher(None, rua_i, rua_j).ratio() > 0.90:
                            group_ids[j] = curr
                except: pass

            curr += 1

    df['GroupID'] = group_ids  

    # --- DEBUG PARA VOCÊ VALIDAR O BANCO ---
    df['Pertence_ao_Banco'] = df['Endereco_Formatado'].apply(lambda x: "SIM" if "📍" in str(x) else "NÃO")
    df[['GroupID', 'Pertence_ao_Banco', 'Destination Address', 'Endereco_Formatado', 'Rua_Base', 'Num_Casa']].to_csv("debug_agrupamento.csv", index=False, sep=';', encoding='utf-8-sig')

    # =========================================================
    # PASSO 3: AGRUPAMENTO E FORMATAÇÃO FINAL
    # =========================================================
    df_agrupado = df.groupby('GroupID').agg({
        'Sequence': lambda x: list(x),
        'Endereco_Formatado': 'first',
        'Bairro': 'first',
        'City': 'first',
        'Zipcode/Postal code': 'first',
        'Latitude': 'first',
        'Longitude': 'first',
        
    }).reset_index(drop=True)

    df_agrupado['Sequence'] = df_agrupado.apply(lambda row: aplicar_formatacao_final(row, notas_vivas), axis=1)
    df_agrupado = df_agrupado.rename(columns={'Endereco_Formatado': 'Destination Address'})
    
    # Adiciona o emoji apenas se não tiver (Garante o visual no Flet)
    df_agrupado['Destination Address'] = df_agrupado['Destination Address'].apply(
        lambda x: f"📍 {x}" if not str(x).startswith("📍") else x
    )

    return df_agrupado

# Função 27 - Ajustada para limpar campos na expulsão
def verificar_sessao_ativa(page, state=None, atualizar_sidebar_cb=None, renderizar_conteudo_cb=None, email_tf=None, senha_tf=None):
    email = page.client_storage.get("usuario_email")
    auth_id = page.client_storage.get("auth_session_id")
    
    if email and auth_id:
        try:
            if db:
                doc = db.collection("usuarios").document(email).get()
                if doc.exists:
                    sessoes_ativas = doc.to_dict().get("sessoes_ativas", [])
                    if auth_id in sessoes_ativas:
                        page.session.set("logado", True)
                        page.session.set("usuario_email", email)
                        page.session.set("auth_session_id", auth_id)
                        return True
        except Exception as e:
            print(f"Erro na verificação: {e}")

    if page.session.get("logado") == True:
        page.session.set("logado", False)
        page.client_storage.remove("auth_session_id")
        
        # Limpa os campos de texto do login
        if email_tf: email_tf.value = ""
        if senha_tf: senha_tf.value = ""
        
        if state and atualizar_sidebar_cb and renderizar_conteudo_cb:
            state["aba_atual"] = "🏠 Início"
            atualizar_sidebar_cb()
            renderizar_conteudo_cb()
            page.open(ft.SnackBar(ft.Text("⚠️ Sessão encerrada: Outro acesso detectado."), bgcolor="orange"))
            page.update()
            
    return False

# Função 28
def salvar_dados_fluxoderotas(dados, caminho, usar_merge=True): # Adicionamos o parâmetro aqui
    try:
        doc_ref = db.document(caminho)
        # Agora ele usa o merge por padrão, mas aceita False quando for deletar
        doc_ref.set(dados, merge=usar_merge) 
        print(f"SUCESSO: Dados processados em {caminho}")
        return True
    except Exception as e:
        print(f"ERRO FIREBASE: {e}")
        return False
    
# Função 29 - Ajustada para Fila de 2 Logins
def realizar_login_logic(page, state, email, senha, atualizar_sidebar_cb, renderizar_conteudo_cb):
    if email and senha:
        session_id = str(uuid.uuid4())
        email_limpo = email.lower().strip()

        if db:
            try:
                doc_ref = db.collection("usuarios").document(email_limpo)
                doc = doc_ref.get()
                
                sessoes_ativas = []
                if doc.exists:
                    # Pega a lista atual ou cria uma vazia
                    sessoes_ativas = doc.to_dict().get("sessoes_ativas", [])

                # LÓGICA DA FILA:
                sessoes_ativas.append(session_id)
                if len(sessoes_ativas) > 2:
                    sessoes_ativas.pop(0) # Remove a primeira (mais antiga)

                # Salva de volta no Firebase
                doc_ref.set({
                    "ultima_sessao": session_id,
                    "sessoes_ativas": sessoes_ativas,
                    "logado_em": datetime.now().isoformat()
                }, merge=True)
                
                # Salva localmente
                page.client_storage.set("usuario_email", email_limpo)
                page.client_storage.set("auth_session_id", session_id)
                page.session.set("logado", True)
                page.session.set("usuario_email", email_limpo)
                page.session.set("auth_session_id", session_id)
                
                atualizar_sidebar_cb()
                renderizar_conteudo_cb()
            except Exception as e:
                print(f"Erro no login: {e}")
    page.update()

# Função 30 - Ajustada para limpar campos no logout manual
def realizar_logout_logic(page, state, atualizar_sidebar_cb, renderizar_conteudo_cb, email_tf=None, senha_tf=None):
    email = page.session.get("usuario_email")
    auth_id = page.session.get("auth_session_id")

    if db and email and auth_id:
        try:
            doc_ref = db.collection("usuarios").document(email)
            doc = doc_ref.get()
            if doc.exists:
                sessoes = doc.to_dict().get("sessoes_ativas", [])
                if auth_id in sessoes:
                    sessoes.remove(auth_id)
                    doc_ref.update({"sessoes_ativas": sessoes})
        except Exception as e:
            print(f"Erro no logout: {e}")

    # Limpa os campos de texto do login
    if email_tf: email_tf.value = ""
    if senha_tf: senha_tf.value = ""
    
    page.client_storage.remove("auth_session_id")
    page.session.clear()
    state["aba_atual"] = "🏠 Início"
    
    atualizar_sidebar_cb()
    renderizar_conteudo_cb()
    page.update()

# Função 31
def iniciar_processamento_logic(page, state, renderizar_conteudo_cb):
    # 1. Recupera o FilePicker da sessão (definido no main.py)
    file_picker = page.session.get("meu_file_picker")
    
    # Valida se um arquivo foi realmente selecionado
    if not file_picker or not file_picker.result or not file_picker.result.files:
        page.open(ft.SnackBar(ft.Text("Nenhum arquivo selecionado!"), bgcolor="orange"))
        return

    arquivo_selecionado = file_picker.result.files[0]
    
    # 2. Captura os bytes do arquivo (essencial para evitar o KeyError)
    try:
        if arquivo_selecionado.path:  # Caminho local (Desktop/Windows)
            with open(arquivo_selecionado.path, "rb") as f:
                state["arquivo_bytes"] = f.read()
        else:  # Buffer de memória (Web)
            state["arquivo_bytes"] = arquivo_selecionado.content
    except Exception as e:
        page.open(ft.SnackBar(ft.Text(f"Erro ao ler arquivo: {e}"), bgcolor="red"))
        return

    # Mensagem de feedback inicial
    page.open(ft.SnackBar(ft.Text("Processando agrupamentos... aguarde."), bgcolor="blue"))
    
    try:
        # 3. Carrega configurações do Firebase/Config
        notas = carregar_dados_fluxoderotas("fluxoderotas_config/observacoes")
        condos = carregar_dados_fluxoderotas("fluxoderotas_config/condominios")
        
        # 4. Lê o Excel usando os bytes recém-capturados
        df_bruto = pd.read_excel(io.BytesIO(state["arquivo_bytes"]))
        
        # 5. Tratamento de colunas para evitar erros de tipo (int/str)
        colunas_criticas = ['Destination Address', 'Num_Casa', 'Sequence', 'Rua_Base']
        for col in colunas_criticas:
            if col in df_bruto.columns:
                df_bruto[col] = df_bruto[col].astype(str).replace('nan', '')

        # 6. Executa o processamento da rota
        state["df_processado"] = processar_agrupamento(df_bruto, notas, condos)
        state["processamento_concluido"] = True
        
        # 7. Atualiza a interface (Callback)
        renderizar_conteudo_cb()
        page.open(ft.SnackBar(ft.Text("Rota processada com sucesso!"), bgcolor="green"))
        
    except Exception as ex:
        print(f"Erro detalhado no processamento: {ex}")
        page.open(ft.SnackBar(ft.Text(f"Erro no processamento: {ex}"), bgcolor="red"))
    
    page.update()

# Função 32 - Ajustada para refletir o estado de deslogado
def atualizar_sidebar_logic(page, state, drawer, email_tf, senha_tf, login_cb, logout_cb):
    drawer.controls.clear()
    
    # Verifica se o usuário está logado na sessão atual
    logado = page.session.get("logado") == True

    if logado:
        drawer.controls.extend([
            ft.NavigationDrawerDestination(icon=ft.icons.HOME, label="🏠 Início"),
            ft.NavigationDrawerDestination(icon=ft.icons.NOTE_ALT, label="📝 Gerenciar Notas"),
            ft.NavigationDrawerDestination(icon=ft.icons.BUSINESS, label="🏢 Condomínios"),
            ft.NavigationDrawerDestination(icon=ft.icons.MAP, label="📍 Mapa"),
            ft.Divider(),
            ft.Container(
                content=ft.TextButton(
                    "Sair da Conta", 
                    icon=ft.icons.LOGOUT, 
                    icon_color="red", 
                    on_click=logout_cb
                ),
                padding=10
            )
        ])
    else:
        # Se não estiver logado, mostra o formulário de login
        drawer.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Área do Motorista", size=20, weight="bold"),
                    email_tf,
                    senha_tf,
                    ft.ElevatedButton(
                        "ENTRAR", 
                        bgcolor="red", 
                        color="white", 
                        on_click=login_cb, 
                        width=300
                    ),
                    ft.Text("Login necessário para editar dados.", size=12, italic=True)
                ]), padding=20
            )
        )
    page.update()

# Função 33 - Ajustada para redirecionamento
def renderizar_conteudo_logic(page, state, container_principal, dict_abas, abrir_drawer_cb):
    container_principal.content = None
    aba = state["aba_atual"]
    logado = page.session.get("logado") == True
    
    # 1. ABA INÍCIO (Sempre visível)
    if aba == "🏠 Início":
        container_principal.content = dict_abas["inicio"]()
    
    # 2. ABA MAPA
    elif aba == "📍 Mapa":
        if state["df_processado"] is not None:
            container_principal.content = dict_abas["mapa"](page, state["df_processado"], state["mapa_state"])
        else:
            container_principal.content = ft.Text("Processe uma planilha no Início primeiro.")
            
    # 3. SEGURANÇA: Se a aba for restrita e não estiver logado
    elif not logado:
        # Força o estado para Início para evitar loops
        state["aba_atual"] = "🏠 Início"
        container_principal.content = dict_abas["inicio"]()
        
        # Abre o drawer para o usuário logar novamente
        abrir_drawer_cb(None)
        
    # 4. ABAS RESTRITAS (Só entra aqui se logado for True)
    else:
        if aba == "📝 Gerenciar Notas":
            container_principal.content = dict_abas["notas"](page)
        elif aba == "🏢 Condomínios":
            container_principal.content = dict_abas["condos"](page)
            
    page.update()

# Função 34 - Layout do botão processar atualizado
def gerar_view_inicio_logic(page, state, file_picker, processar_cb, navegar_mapa_cb, salvar_cb):
    coluna = ft.Column([
        ft.Text("Fluxo de Rotas", size=30, weight="bold", color="red"),
        ft.Text("Selecione sua planilha da Shopee para organizar as paradas."),
        ft.Divider(),
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("1. Upload de Dados", size=18, weight="bold"),
                    ft.Text("Status: " + (state["nome_arquivo"] if state["nome_arquivo"] else "Aguardando arquivo...")),
                    ft.ElevatedButton(
                        "Selecionar Planilha Excel",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=lambda _: file_picker.pick_files(allowed_extensions=["xlsx", "xls"])
                    ),
                ])
            )
        )
    ], spacing=20)

    if state["arquivo_bytes"]:
        # Botão Centralizado, sem o Card vermelho e sem o texto "2. Processamento"
        coluna.controls.append(
            ft.Container(
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=10, bottom=10),
                content=ft.ElevatedButton(
                    "PROCESSAR ROTA AGORA",
                    icon=ft.icons.PLAY_ARROW,
                    bgcolor="green",
                    color="white",
                    height=50,
                    width=350,
                    on_click=processar_cb
                )
            )
        )
    
    if state["df_processado"] is not None:
        # Calcula o total de paradas
        total_paradas = len(state["df_processado"])
        
        # Exibe o título com a contagem total
        coluna.controls.append(
            ft.Text(
                f"📍 Paradas Identificadas: {total_paradas}", 
                size=20, 
                weight="bold"
            )
        )
        
        lista_paradas = ft.Column(scroll=ft.ScrollMode.AUTO, height=300)
        
        for i, row in state["df_processado"].iterrows():
            # Pegamos a sequência formatada (ex: 1 → 2) e o endereço
            sequencia = row['Sequence'] 
            endereco = row['Destination Address']
            
            lista_paradas.controls.append(
                ft.ListTile(
                    leading=ft.CircleAvatar(
                        content=ft.Text(str(i+1)), 
                        bgcolor="red"
                    ),
                    # Título mostra a Ordem (ex: 1 → 2 → 3)
                    title=ft.Text(f"{sequencia}", weight="bold", color="green"),
                    subtitle=ft.Column([
                        ft.Text(endereco, size=16),
                        ft.Text(f"Bairro: {row.get('Bairro', 'N/A')}", size=12, italic=True),
                    ], spacing=2),
                    is_three_line=True
                )
            )
        
        coluna.controls.append(ft.Container(content=lista_paradas, padding=10, border=ft.border.all(1, "grey")))        
        coluna.controls.append(
            ft.Row([
                ft.ElevatedButton("ABRIR MAPA", icon=ft.icons.MAP, on_click=navegar_mapa_cb),
                ft.ElevatedButton("BAIXAR EXCEL", icon=ft.icons.DOWNLOAD, on_click=salvar_cb)
            ], alignment=ft.MainAxisAlignment.CENTER)
        )

    return coluna

# Função 35
def deletar_condominio_firebase(nome_grupo):    
    try:
        caminho = "fluxoderotas_config/condominios"
        doc_ref = db.document(caminho)
        
        # O Firestore usa o ponto para caminhos aninhados, 
        # mas como seu nome_grupo pode ter espaços, passamos como dicionário
        doc_ref.update({
            nome_grupo: firestore.DELETE_FIELD
        })
        print(f"✅ {nome_grupo} removido do Firebase.")
        return True
    except Exception as e:
        print(f"Erro ao deletar: {e}")
        return False

# Funçao 36
def mostrar_snack(page, texto, cor="orange"):
    try:
        if not page: return
        page.overlay.clear() # Limpa avisos antigos
        snack = ft.SnackBar(ft.Text(texto), bgcolor=cor)
        page.overlay.append(snack)
        snack.open = True
        page.update()
    except Exception as e:
        print(f"Erro ao mostrar snack: {e}")

# Função 37
def preparar_edicao(page, nome_grupo, dados_do_grupo, txt_nome, txt_portaria, btn_cancelar, lista_view, atualizar_lista_fn):
    """
    Função 37: Prepara a interface para edição.
    Mantém o nome original conforme solicitado.
    """
    # 1. Alimenta os campos com os dados existentes
    txt_nome.value = nome_grupo
    txt_portaria.value = dados_do_grupo.get("portaria", "")
    
    # 2. Sincroniza a lista de endereços com a sessão temporária
    enderecos = dados_do_grupo.get("enderecos", [])
    page.session.set("temp_enderecos_grupo", list(enderecos))
    
    # 3. Muda o estado visual para "Modo Edição"
    btn_cancelar.visible = True
    txt_nome.disabled = True # Trava o nome para não criar duplicados no Firebase
    
    # 4. Atualiza a lista visual de logradouros na tela
    atualizar_lista_fn(lista_view, page)
    
    # Exibe o aviso de status
    from funcoes import mostrar_snack
    mostrar_snack(page, f"Editando: {nome_grupo}", "blue")
    
    page.update()
    lista_view.update()

# Função 38
def carregar_lista_cadastrados(
    page, 
    lista_cadastrados, 
    txt_nome_grupo, 
    txt_portaria, 
    btn_cancelar, 
    atualizar_lista_visual_fn,
    excluir_grupo_fn,
    lista_view
):
    """
    Função 38: Busca os dados no Firebase e reconstrói a lista visual 
    de condomínios com botões de Editar e Excluir.
    """
    from funcoes import carregar_dados_fluxoderotas, preparar_edicao
    
    # 1. Busca os dados no Firebase
    dados_totais = carregar_dados_fluxoderotas("fluxoderotas_config/condominios")
    print(f"DEBUG REAL: {dados_totais}")
    
    # 2. Limpa a lista atual na interface
    lista_cadastrados.controls.clear()
    
    if dados_totais:
        for nome_id, info in dados_totais.items():
            lista_cadastrados.controls.append(
                ft.Container(
                    bgcolor="#333333", 
                    padding=10, 
                    border_radius=8, 
                    margin=ft.margin.only(bottom=5),
                    content=ft.Row([
                        ft.Icon(ft.icons.BUSINESS, color="orange"),
                        ft.Text(nome_id, weight="bold", expand=True),
                        
                        # BOTÃO EDITAR (Chama a Função 37)
                        ft.IconButton(
                            ft.icons.EDIT, 
                            icon_color="blue",
                            on_click=lambda _, n=nome_id, i=info: preparar_edicao(
                                page, n, i, txt_nome_grupo, txt_portaria, btn_cancelar, lista_view, atualizar_lista_visual_fn
                            )
                        ),
                        
                        # BOTÃO EXCLUIR (Chama a função de exclusão da interface)                        
                        ft.IconButton(
                        icon=ft.icons.DELETE,
                        icon_color="red",
                        on_click=lambda _, n=nome_id: excluir_grupo_fn(
                            page,                   # 1. Objeto da página
                            n,                      # 2. Nome do condomínio
                            lista_view,             # 3. Lista de endereços (parte de cima)
                            lista_cadastrados,      # 4. Lista de condomínios (parte de baixo)
                            txt_nome_grupo,         # 5. Campo de texto do nome
                            txt_portaria,           # 6. Campo de texto da portaria
                            btn_cancelar,           # 7. Botão de cancelar
                            atualizar_lista_visual_fn # 8. Função que desenha os endereços
                        )
                    )
                    ])
                )
            )
    else:
        lista_cadastrados.controls.append(
            ft.Text("Nenhum condomínio localizado.", color="grey", italic=True)
        )
    
    page.update()

# Função 39
def remover_item(page, indice, atualizar_fn, lista_view):
    # 1. Puxa a lista da sessão
    enderecos = page.session.get("temp_enderecos_grupo") or []
    
    # 2. Remove o item pelo índice
    if 0 <= indice < len(enderecos):
        print(f"[DEBUG] Removendo endereço no índice: {indice}")
        enderecos.pop(indice)
        
        # 3. Salva a lista atualizada na sessão
        page.session.set("temp_enderecos_grupo", enderecos)
        
        # 4. Se estávamos a editar este item, cancela o modo edição
        if page.session.get("index_editando") == indice:
            page.session.set("index_editando", None)
            # Reseta o botão de adicionar se ele estiver no modo "Atualizar"
            btn_add = page.session.get("ref_btn_add")
            if btn_add:
                btn_add.text = "ADICIONAR À LISTA"
                btn_add.icon = ft.icons.ADD
                btn_add.bgcolor = None

        # 5. Atualiza a visualização
        atualizar_fn(lista_view, page)
        page.update()

# Função 40
def atualizar_lista_visual(lista_view, page):
    lista_view.controls.clear()
    enderecos = page.session.get("temp_enderecos_grupo") or []
    
    for i, end in enumerate(enderecos):
        lista_view.controls.append(
            ft.ListTile(
                leading=ft.Icon(ft.icons.LOCATION_ON, color="orange"),
                title=ft.Text(f"{end['rua']}, {end['numero']}"),
                subtitle=ft.Text(end['bairro']),
                trailing=ft.Row([
                    # NOVO: BOTÃO EDITAR ENDEREÇO
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        icon_color="blue",
                        on_click=lambda _, idx=i, d=end: preparar_edicao_endereco(page, idx, d)
                    ),
                    # EXCLUIR (Já existente, apenas mantendo o padrão)
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINE,
                        icon_color="red",
                        on_click=lambda _, idx=i: remover_item(page, idx, atualizar_lista_visual, lista_view)
                    ),
                ], tight=True)
            )
        )
    page.update()

# Funçao 41
def cancelar_edicao(page, txt_nome_grupo, txt_portaria, txt_bairro, txt_rua, txt_num, txt_cidade, btn_cancelar, atualizar_lista_fn, lista_view):
    # 1. Limpa os textos
    txt_nome_grupo.value = ""
    txt_portaria.value = ""
    txt_bairro.value = ""
    txt_cidade.value = ""
    txt_num.value = ""
    txt_rua.value = ""
    
    # 2. Reseta estados visuais
    txt_nome_grupo.disabled = False
    btn_cancelar.visible = False # AGORA VAI FUNCIONAR
    
    # 3. Limpa a memória de edição
    page.session.set("temp_enderecos_grupo", [])
    page.session.set("index_editando", None) 
    
    # 4. Reseta o botão de adicionar rua (caso estivesse em modo "Atualizar")
    btn_add = page.session.get("ref_btn_add")
    if btn_add:
        btn_add.text = "ADICIONAR À LISTA"
        btn_add.icon = ft.icons.ADD
        btn_add.bgcolor = None

    # 5. Atualiza a lista para aparecer vazia
    atualizar_lista_fn(lista_view, page)
    
    # 6. O MAIS IMPORTANTE: Update na página para processar o visible=False
    page.update()

# Função 42
def adicionar_endereco_lista(page, txt_rua, txt_num, txt_bairro, txt_cidade, atualizar_fn, lista_view):
    if not txt_rua.value or not txt_num.value:
        return

    enderecos = page.session.get("temp_enderecos_grupo")
    index_editando = page.session.get("index_editando")

    novo_item = {
        "rua": txt_rua.value.upper(),
        "numero": txt_num.value,
        "bairro": txt_bairro.value.upper(),
        "cidade": txt_cidade.value.upper()
    }

    if index_editando is not None:
        # REGRA: SUBSTITUIR O ANTIGO
        enderecos[index_editando] = novo_item
        page.session.set("index_editando", None) # Limpa o modo edição
        
        # Volta o botão ao normal
        btn_add = page.session.get("ref_btn_add")
        btn_add.text = "ADICIONAR À LISTA"
        btn_add.icon = ft.icons.ADD
        btn_add.bgcolor = None
    else:
        # REGRA: ADICIONAR NOVO
        enderecos.append(novo_item)

    page.session.set("temp_enderecos_grupo", enderecos)
    
    # Limpa campos
    txt_rua.value = ""
    txt_num.value = ""
    txt_bairro.value = ""
    txt_cidade.value = ""
    
    atualizar_fn(lista_view, page)
        
# Função 43
def salvar_condo_completo(page, txt_nome_grupo, txt_portaria, lista_cadastrados, atualizar_lista_visual, excluir_grupo, btn_cancelar, lista_view):
    print("\n--- [DEBUG] SALVAMENTO: NOME DO GRUPO COMO CAMPO (MAP) ---")
    nome_grupo = txt_nome_grupo.value.strip().upper() 
    
    if not nome_grupo:
        mostrar_snack(page, "O nome do condomínio é obrigatório!", "red")
        return

    # O CAMINHO PARA O DOCUMENTO PAI
    caminho_documento = "fluxoderotas_config/condominios" 

    # Organizando os endereços (Array de Maps)
    enderecos_sessao = page.session.get("temp_enderecos_grupo") or []
    lista_enderecos_final = []
    
    for end in enderecos_sessao:
        lista_enderecos_final.append({
            "bairro": str(end.get("bairro", "")).upper(),
            "cep": str(end.get("cep", "")),
            "cidade": str(end.get("cidade", "")).upper(),
            "numero": str(end.get("numero", "")),
            "rua": str(end.get("rua", "")).upper()
        })

    # A ESTRUTURA: O nome do grupo é a CHAVE do mapa
    dados_para_nuvem = {
        nome_grupo: {
            "portaria": txt_portaria.value.strip().upper(),
            "tipo": "multi_ruas",
            "enderecos": lista_enderecos_final
        }
    }
    
    try:
        print(f"[DEBUG] Tentando salvar campo '{nome_grupo}' em {caminho_documento}")
        
        # CRÍTICO: usar_merge=True para adicionar o campo sem deletar os outros condomínios
        if salvar_dados_fluxoderotas(dados_para_nuvem, caminho_documento, usar_merge=True):
            print("[DEBUG] SUCESSO! Campo criado/atualizado.")
            mostrar_snack(page, f"✅ {nome_grupo} salvo com sucesso!", "green")
            
            # Limpa a interface
            txt_nome_grupo.disabled = False
            txt_nome_grupo.value = ""
            txt_portaria.value = ""
            btn_cancelar.visible = False
            page.session.set("temp_enderecos_grupo", [])
            
            # Atualiza os visuais
            atualizar_lista_visual(lista_view, page)
            
            carregar_lista_cadastrados(
                page=page,
                lista_cadastrados=lista_cadastrados,
                txt_nome_grupo=txt_nome_grupo,
                txt_portaria=txt_portaria,
                btn_cancelar=btn_cancelar,
                atualizar_lista_visual_fn=atualizar_lista_visual,
                excluir_grupo_fn=excluir_grupo,
                lista_view=lista_view
            )
            page.update()
        else:
            print("[DEBUG] Falha no salvamento.")
            mostrar_snack(page, "Erro ao salvar no Firebase.", "red")
            
    except Exception as ex:
        print(f"[DEBUG CRÍTICO] Erro: {ex}")
        mostrar_snack(page, f"Erro técnico: {ex}", "red")

# Funçao 44
def excluir_grupo(page, nome_grupo, lista_view, lista_cadastrados, txt_nome_grupo, txt_portaria, btn_cancelar, atualizar_lista_visual):
    
    def confirmar_exclusao(e):
        print(f"\n--- [DEBUG] INÍCIO DO PROCESSO DE EXCLUSÃO: {nome_grupo} ---")
        try:
            # CORREÇÃO AQUI: Adicionado o 'f' na frente da string
            caminho_documento_pai = f"fluxoderotas_config/condominios" 
            
            # Se o seu Firebase estiver organizado como Coleção/Documento/Coleção/Documento:
            # O caminho correto para carregar os dados costuma ser o documento PAI.
            # Se você quer deletar o condomínio de dentro de um documento chamado 'lista', seria:
            # caminho_documento_pai = "fluxoderotas_config/condominios"
            
            print(f"[DEBUG] 1. Tentando carregar dados de: {caminho_documento_pai}")
            dados_atuais = carregar_dados_fluxoderotas(caminho_documento_pai)
            
            if not dados_atuais:
                print("[DEBUG] ERRO: dados_atuais veio vazio!")
                mostrar_snack(page, "Não foi possível carregar os dados do Firebase.", "red")
                dlg_confirma.open = False # Fecha o diálogo para não travar a tela
                page.update()
                return

            # A lógica de exclusão no dicionário permanece, mas verifique a estrutura:
            conteudo = dados_atuais.get("condominios", dados_atuais)

            if nome_grupo in conteudo:
                print(f"[DEBUG] 3. Encontrado! Deletando {nome_grupo} do dicionário local.")
                del conteudo[nome_grupo]
                
                dados_para_salvar = {"condominios": conteudo} if "condominios" in dados_atuais else conteudo

                print("[DEBUG] 4. Enviando atualização para o Firebase...")
                if salvar_dados_fluxoderotas(dados_para_salvar, caminho_documento_pai, usar_merge=False):
                    print("[DEBUG] 5. FIREBASE OK! Fechando diálogo...")
                    
                    dlg_confirma.open = False
                    page.update()
                    
                    print("[DEBUG] 6. Limpando sessão e lista_view...")
                    page.session.set("temp_enderecos_grupo", []) 
                    atualizar_lista_visual(lista_view, page)
                    
                    print("[DEBUG] 7. Recarregando lista de cadastrados...")
                    carregar_lista_cadastrados(
                        page=page, 
                        lista_cadastrados=lista_cadastrados, 
                        txt_nome_grupo=txt_nome_grupo, 
                        txt_portaria=txt_portaria, 
                        btn_cancelar=btn_cancelar, 
                        atualizar_lista_visual_fn=atualizar_lista_visual, 
                        excluir_grupo_fn=excluir_grupo, 
                        lista_view=lista_view
                    )
                    mostrar_snack(page, f"{nome_grupo} removido com sucesso!", "green")
                else:
                    raise Exception("salvar_dados_fluxoderotas retornou False")
            else:
                print(f"[DEBUG] ERRO: {nome_grupo} não existe no dicionário!")
                mostrar_snack(page, "Condomínio não encontrado.", "orange")
                dlg_confirma.open = False

        except Exception as ex:
            print(f"\n[!!! DEBUG CRÍTICO !!!] O ERRO É: {ex}")
            dlg_confirma.open = False # FECHA O DIÁLOGO NO ERRO para evitar tela branca
            mostrar_snack(page, f"Erro ao excluir: {ex}", "red")
        
        page.update()
        print("--- [DEBUG] FIM DO PROCESSO ---\n")

    # --- O RESTANTE DO DIÁLOGO FICA IGUAL ---
    dlg_confirma = ft.AlertDialog(
        title=ft.Text("Confirmar Exclusão"),
        content=ft.Text(f"Tem certeza que deseja apagar o {nome_grupo}?"),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: fechar_dialogo()),
            ft.ElevatedButton("Confirmar Exclusão", bgcolor="red", color="white", on_click=confirmar_exclusao),
        ],
    )

    def fechar_dialogo():        
        dlg_confirma.open = False
        page.update()

    page.overlay.append(dlg_confirma)
    dlg_confirma.open = True
    page.update()
    
# Funçao 45
def preparar_edicao_endereco(page, indice, dados):
    # Pega as referências dos campos que salvamos na interface
    # (Vou te mostrar como salvar essas referências no passo 3)
    txt_rua = page.session.get("ref_txt_rua")
    txt_num = page.session.get("ref_txt_num")
    txt_bairro = page.session.get("ref_txt_bairro")
    txt_cidade = page.session.get("ref_txt_cidade")
    btn_add = page.session.get("ref_btn_add")

    # 1. Preenche os campos
    txt_rua.value = dados['rua']
    txt_num.value = dados['numero']
    txt_bairro.value = dados['bairro']
    txt_cidade.value = dados['cidade']
    
    # 2. Salva o índice na sessão para saber que é uma edição
    page.session.set("index_editando", indice)
    
    # 3. Muda o visual do botão
    btn_add.text = "ATUALIZAR NA LISTA"
    btn_add.icon = ft.icons.REFRESH
    btn_add.bgcolor = "orange"
    
    page.update()

# Função 46
def obter_nome_logado(page: ft.Page):
    # 1. Pega o e-mail que a Função 29 salvou
    email_logado = page.session.get("usuario_email") 
    
    if not email_logado:
        return "Usuário Desconhecido"

    try:
        # 2. Consulta o documento no Firebase (Caminho extraído da Função 2)
        doc = db.collection("usuarios").document(email_logado).get()
        if doc.exists:
            dados = doc.to_dict()
            # 3. Pega o campo 'nome' definido no seu arquivo de criação de conta
            return dados.get("nome", "Motorista")
    except Exception as e:
        print(f"Erro ao buscar nome: {e}")
    
    return "Motorista"















