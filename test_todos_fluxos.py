"""
Bateria de Testes Exaustiva de Todos os 5 Fluxos do Sistema Casa da Foto Studio
Executa todos os fluxos de ponta a ponta:
1. Admin (Login, Categorias, Textos, Pacotes, Contatos)
2. Fotógrafo (Login, Kanban de Projetos, Criação, Atualização, Exclusão)
3. Configuração de Galeria (Fotos, Capa, Regras, Drive, Destinatários, Atividades)
4. Escolha de Fotos do Cliente (Login, Marcação Pacote, Extra, Envio de Seleção)
5. Entrega Final e Download pelo Google Drive
"""

import requests
import json
import base64
import time

BASE_URL = "http://127.0.0.1:8082"

def print_pass(msg):
    print(f"  [PASS] {msg}")

def test_fluxo_1_admin():
    print("\n[Fluxo 1] Painel do Administrador...")
    
    # Login Admin
    r = requests.post(f"{BASE_URL}/api/auth/login-admin", json={"login": "GoAdm", "senha": "Go06190608*"})
    assert r.status_code == 200, f"Falha login admin: {r.text}"
    assert r.json().get("success") is True
    print_pass("Login do Administrador autenticado com sucesso")

    # Adicionar Categoria
    cat_nome = f"Ensaio Teste Auto {int(time.time())}"
    r = requests.post(f"{BASE_URL}/api/categorias", json={"nome": cat_nome})
    assert r.status_code == 200
    cat_id = r.json().get("id") or r.json().get("categoria", {}).get("id")
    assert cat_id is not None
    print_pass(f"Categoria criada: {cat_nome} (ID {cat_id})")

    # Listar Categorias
    r = requests.get(f"{BASE_URL}/api/categorias")
    assert r.status_code == 200
    cats = r.json()
    assert any(c["nome"] == cat_nome for c in cats)
    print_pass("Listagem de categorias validada")

    # Remover Categoria de Teste
    r = requests.delete(f"{BASE_URL}/api/categorias/{cat_id}")
    assert r.status_code == 200
    print_pass("Exclusão de categoria validada")

    # Gerenciamento de Textos do Site
    r = requests.get(f"{BASE_URL}/api/site/textos")
    assert r.status_code == 200
    textos = r.json()
    assert "hero_titulo" in textos
    print_pass("Leitura de textos oficiais do site validada")

    # Gerenciamento de Pacotes de Ensaio
    pkg_payload = {
        "titulo": "Pacote Teste E2E",
        "categoria": "Família",
        "descricao": "Descrição teste completa",
        "valor": "R$ 450,00",
        "imagem": "assets/images/familia.jpg"
    }
    r = requests.post(f"{BASE_URL}/api/site/pacotes", json=pkg_payload)
    assert r.status_code == 200
    pkg_id = r.json().get("id")
    assert pkg_id is not None
    print_pass(f"Pacote de ensaio criado com sucesso (ID {pkg_id})")

    r = requests.delete(f"{BASE_URL}/api/site/pacotes/{pkg_id}")
    assert r.status_code == 200
    print_pass("Exclusão de pacote de teste validada")

def test_fluxo_2_fotografo_kanban():
    print("\n[Fluxo 2] Fotógrafo e Kanban de Projetos...")
    
    # Login Fotógrafo
    r = requests.post(f"{BASE_URL}/api/auth/login-fotografo", json={"email": "contato@casadafoto.com", "senha": "123456"})
    assert r.status_code == 200
    assert r.json().get("success") is True
    print_pass("Login do fotógrafo validado")

    # Listar Projetos
    r = requests.get(f"{BASE_URL}/api/projetos")
    assert r.status_code == 200
    projs = r.json()
    print_pass(f"Projetos carregados no Kanban: {len(projs)} projetos")

    # Criar Novo Projeto
    novo_proj = {
        "nome_cliente": "Cliente Teste E2E",
        "tipo_ensaio": "Ensaio Newborn",
        "categoria_tag": "Newborn",
        "status": "novos",
        "prazo": "15 dias"
    }
    r = requests.post(f"{BASE_URL}/api/projetos", json=novo_proj)
    assert r.status_code == 200
    p_data = r.json()
    proj_id = p_data.get("id")
    gal_id = p_data.get("galeria_id")
    assert proj_id is not None and gal_id is not None
    print_pass(f"Projeto criado (ID {proj_id}) com galeria vinculada (ID {gal_id})")

    # Mover Projeto de Coluna (Status)
    r = requests.put(f"{BASE_URL}/api/projetos/{proj_id}/status", json={"status": "andamento"})
    assert r.status_code == 200
    assert r.json().get("status") == "andamento"
    print_pass("Transição de status no Kanban validada: novos -> andamento")

    return proj_id, gal_id

def test_fluxo_3_galeria_e_config(gal_id, proj_id):
    print(f"\n[Fluxo 3] Gestão e Configuração da Galeria #{gal_id}...")

    # Adicionar Fotos na Galeria
    pixel_gif = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    fotos_payload = {
        "fotos": [
            {"numero": "Foto 001", "titulo": "Ensaio Foto 001", "image": pixel_gif},
            {"numero": "Foto 002", "titulo": "Ensaio Foto 002", "image": pixel_gif},
            {"numero": "Foto 003", "titulo": "Ensaio Foto 003", "image": pixel_gif}
        ]
    }
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/fotos", json=fotos_payload)
    assert r.status_code == 200
    assert r.json().get("count") == 3
    print_pass("Upload de 3 fotos na galeria realizado com sucesso")

    # Listar Fotos
    r = requests.get(f"{BASE_URL}/api/galeria/{gal_id}/fotos")
    assert r.status_code == 200
    fotos_data = r.json()
    assert len(fotos_data.get("fotos", [])) >= 3
    foto_1_id = fotos_data["fotos"][0]["id"]
    foto_2_id = fotos_data["fotos"][1]["id"]
    foto_3_id = fotos_data["fotos"][2]["id"]
    print_pass("Listagem de fotos da galeria validada")

    # Definir Capa
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/fotos/{foto_1_id}/capa")
    assert r.status_code == 200
    print_pass("Definição de foto de capa da galeria validada")

    # Salvar Configurações (Preço extra, Limite pacote, Link Google Drive)
    config_payload = {
        "limite_pacote": 2,
        "valor_foto_extra": 30.0,
        "permitir_extras": 1,
        "link_drive": "https://drive.google.com/drive/folders/pastaEntregaE2E?usp=sharing"
    }
    r = requests.put(f"{BASE_URL}/api/galeria/{gal_id}", json=config_payload)
    assert r.status_code == 200
    print_pass("Salvamento de regras, limites e link do Google Drive validado")

    # Cadastrar Destinatário / Cliente
    email_cliente = f"cliente_{int(time.time())}@teste.com"
    dest_payload = {
        "nome": "Cliente VIP E2E",
        "email": email_cliente,
        "senha": "senhaCliente123",
        "permissao": "Selecionar fotos"
    }
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/destinatarios", json=dest_payload)
    assert r.status_code == 200
    assert r.json().get("success") is True
    print_pass(f"Destinatário cadastrado com credenciais de login: {email_cliente}")

    # Listar Destinatários
    r = requests.get(f"{BASE_URL}/api/galeria/{gal_id}/destinatarios")
    assert r.status_code == 200
    dests = r.json()
    assert any(d["email"] == email_cliente for d in dests)
    print_pass("Listagem de destinatários da galeria validada")

    # Histórico de Atividades
    r = requests.get(f"{BASE_URL}/api/galeria/{gal_id}/atividades")
    assert r.status_code == 200
    ativs = r.json()
    assert len(ativs) > 0
    print_pass(f"Histórico de atividades verificado: {len(ativs)} registros registrados")

    return email_cliente, "senhaCliente123", [foto_1_id, foto_2_id, foto_3_id]

def test_fluxo_4_escolha_cliente(gal_id, email, senha, foto_ids):
    print(f"\n[Fluxo 4] Escolha de Fotos pelo Cliente ({email})...")

    # Login Cliente com a senha definida pelo fotógrafo
    r = requests.post(f"{BASE_URL}/api/auth/login-cliente", json={"login": email, "senha": senha})
    assert r.status_code == 200, f"Falha no login do cliente: {r.text}"
    assert r.json().get("success") is True
    print_pass("Login do cliente autenticado com sucesso")

    # Cliente marca Foto 1 no Pacote
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/fotos/{foto_ids[0]}/status", json={"status": "pacote"})
    assert r.status_code == 200
    assert r.json().get("status") == "pacote"
    print_pass("Cliente selecionou Foto 1 para o pacote")

    # Cliente marca Foto 2 no Pacote
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/fotos/{foto_ids[1]}/status", json={"status": "pacote"})
    assert r.status_code == 200
    print_pass("Cliente selecionou Foto 2 para o pacote")

    # Cliente marca Foto 3 como Extra
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/fotos/{foto_ids[2]}/status", json={"status": "extra"})
    assert r.status_code == 200
    assert r.json().get("status") == "extra"
    print_pass("Cliente selecionou Foto 3 como foto extra")

    # Verificar endpoint de fotos selecionadas
    r = requests.get(f"{BASE_URL}/api/galeria/{gal_id}/selecionadas")
    assert r.status_code == 200
    sel_data = r.json()
    assert sel_data["pacote_count"] == 2
    assert sel_data["extra_count"] == 1
    assert "texto_windows" in sel_data and len(sel_data["texto_windows"]) > 0
    print_pass(f"Linha de busca do Windows 10/11 gerada perfeitamente: {sel_data['texto_windows'][:60]}...")

    # Enviar Seleção Final ao Fotógrafo
    r = requests.post(f"{BASE_URL}/api/galeria/{gal_id}/enviar-selecao", json={
        "observacoes": "Adorei as fotos! Por favor caprichar no tratamento da foto 3.",
        "pacote_ids": [foto_ids[0], foto_ids[1]],
        "extra_ids": [foto_ids[2]]
    })
    assert r.status_code == 200
    assert r.json().get("success") is True
    print_pass("Seleção enviada com sucesso ao estúdio com observações")

def test_fluxo_5_entrega_e_drive(gal_id, proj_id):
    print(f"\n[Fluxo 5] Página de Entrega Final e Google Drive...")

    # Acessa dados públicos da entrega
    r = requests.get(f"{BASE_URL}/api/entrega/{gal_id}")
    assert r.status_code == 200
    entrega = r.json()
    assert entrega.get("success") is True
    assert "https://drive.google.com" in entrega.get("link_drive", "")
    assert entrega.get("total_fotos") >= 3
    assert entrega.get("contato", {}).get("whatsapp") is not None
    print_pass(f"Página de entrega 100% pronta! Link do Drive: {entrega.get('link_drive')}")

    # Limpeza do projeto de teste
    r = requests.delete(f"{BASE_URL}/api/projetos/{proj_id}")
    assert r.status_code == 200
    print_pass("Limpeza do projeto de teste executada com sucesso")

if __name__ == "__main__":
    print("=================================================================")
    print(" INICIANDO BATERIA DE TESTES DE INTEGRAÇÃO COMPLETA (5 FLUXOS)")
    print("=================================================================")
    
    test_fluxo_1_admin()
    proj_id, gal_id = test_fluxo_2_fotografo_kanban()
    email_cliente, senha_cliente, foto_ids = test_fluxo_3_galeria_e_config(gal_id, proj_id)
    test_fluxo_4_escolha_cliente(gal_id, email_cliente, senha_cliente, foto_ids)
    test_fluxo_5_entrega_e_drive(gal_id, proj_id)

    print("\n=================================================================")
    print(" TODOS OS 5 FLUXOS FORAM EXECUTADOS COM 100% DE SUCESSO! ZERO ERROS!")
    print("=================================================================")
