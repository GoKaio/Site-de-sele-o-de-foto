import urllib.request
import urllib.parse
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8082"

def main():
    print("=== TESTE 1: Restaurar galerias de exemplo (forçar seed) ===")
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

    print("\n=== TESTE 2: Listar entregas de clientes (/api/entrega/lista) ===")
    with urllib.request.urlopen(f"{BASE_URL}/api/entrega/lista") as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("success") is True
        entregas = data.get("entregas", [])
        print(f"Total de entregas cadastradas: {len(entregas)}")
        assert len(entregas) >= 5
        for e in entregas:
            has_drive = "✓ DRIVE OK" if e.get("link_drive") else "⏳ PENDENTE"
            print(f"  - Galeria {e['galeria_id']} | Cliente: {e['nome_cliente']} ({e['tipo_ensaio']}) | {has_drive}")
            print(f"    Link Personalizado: {BASE_URL}/entrega.html?id={e['galeria_id']}")

    print("\n=== TESTE 3: Validar entrega personalizada do cliente Camila & Pedro ===")
    camila = next((e for e in entregas if "Camila" in e["nome_cliente"]), entregas[0])
    camila_id = camila["galeria_id"]
    with urllib.request.urlopen(f"{BASE_URL}/api/entrega/{camila_id}") as resp:
        detalhes = json.loads(resp.read().decode("utf-8"))
        assert detalhes.get("success") is True
        assert "Camila" in detalhes.get("nome_cliente", "")
        assert detalhes.get("link_drive", "").startswith("https://drive.google.com")
        assert "Camila" in detalhes.get("mensagem_personalizada", "")
        print(f"  [OK] Nome retornado: {detalhes['nome_cliente']}")
        print(f"  [OK] Ensaio: {detalhes['tipo_ensaio']}")
        print(f"  [OK] Link Google Drive: {detalhes['link_drive']}")
        print(f"  [OK] Mensagem: {detalhes['mensagem_personalizada'][:70]}...")

    print("\n=== TESTE 4: Validar entrega do cliente Helena (Primeiro Aninho) ===")
    helena = next((e for e in entregas if "Helena" in e["nome_cliente"]), None)
    if helena:
        with urllib.request.urlopen(f"{BASE_URL}/api/entrega/{helena['galeria_id']}") as resp:
            det_h = json.loads(resp.read().decode("utf-8"))
            assert det_h.get("success") is True
            assert "Helena" in det_h.get("nome_cliente", "")
            assert det_h.get("link_drive", "").startswith("https://drive.google.com")
            print(f"  [OK] Helena Link Drive: {det_h['link_drive']}")

    print("\n=== TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! ===")

if __name__ == "__main__":
    main()
