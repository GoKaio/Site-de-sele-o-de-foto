import urllib.request
import urllib.parse
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8082"

def main():
    print("=== TESTE 1: Restaurar galerias de exemplo ===")
    req = urllib.request.Request(
        f"{BASE_URL}/api/projetos/restaurar-exemplos",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("Restaurar:", res)
        assert res.get("success") is True

    print("\n=== TESTE 2: Listar projetos com link_drive e mensagem_acesso ===")
    with urllib.request.urlopen(f"{BASE_URL}/api/projetos") as resp:
        projs = json.loads(resp.read().decode("utf-8"))
        print(f"Total projetos no Kanban: {len(projs)}")
        assert len(projs) > 0
        for p in projs:
            print(f"  [{p['status'].upper()}] {p['nome_cliente']} ({p['tipo_ensaio']}) - Drive: {p.get('link_drive') or '(pendente)'}")

    print("\n=== TESTE 3: Salvar Link do Drive e Mensagem Personalizada ===")
    gal_id = projs[0]["galeria_id"]
    test_link = "https://drive.google.com/drive/folders/pastaOficialStudio2026?usp=sharing"
    test_msg = "Olá Camila & Pedro! ✨📸 Suas fotos do Ensaio Gestante estão prontas! Acesse o Drive oficial abaixo para baixar todos os arquivos em 300 DPI."
    
    payload = json.dumps({
        "link_drive": test_link,
        "mensagem_acesso": test_msg
    }).encode("utf-8")

    req_put = urllib.request.Request(
        f"{BASE_URL}/api/galeria/{gal_id}/link-drive",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT"
    )
    with urllib.request.urlopen(req_put) as resp:
        put_res = json.loads(resp.read().decode("utf-8"))
        print("Resposta PUT link-drive:", put_res)
        assert put_res.get("success") is True
        assert put_res.get("link_drive") == test_link
        assert put_res.get("mensagem_acesso") == test_msg

    print("\n=== TESTE 4: Obter dados públicos da entrega (/api/entrega/<id>) ===")
    with urllib.request.urlopen(f"{BASE_URL}/api/entrega/{gal_id}") as resp:
        entrega = json.loads(resp.read().decode("utf-8"))
        print("Entrega link_drive retornado:", entrega.get("link_drive"))
        print("Entrega mensagem_personalizada retornada:", entrega.get("mensagem_personalizada"))
        assert entrega.get("link_drive") == test_link
        assert entrega.get("mensagem_personalizada") == test_msg

    print("\n=== TODOS OS TESTES PASSARAM COM SUCESSO! ===")

if __name__ == "__main__":
    main()
