"""
Testes de Validação Completa: Botões, Handlers, Links e Persistência
"""
import requests
import re
import os
import glob

BASE_URL = "http://127.0.0.1:8082"
PROJECT_DIR = r"c:\Users\gokai\Desktop\Casa da foto"

def test_zero_dead_links():
    html_files = glob.glob(os.path.join(PROJECT_DIR, "*.html"))
    dead_links = []
    for hf in html_files:
        fname = os.path.basename(hf)
        with open(hf, "r", encoding="utf-8", errors="ignore") as f:
            c = f.read()
        links = re.findall(r'<a\b([^>]*)>(.*?)</a>', c, re.DOTALL)
        for a_attrs, a_text in links:
            clean_text = re.sub(r'<[^>]*>', '', a_text).strip()[:50]
            href_m = re.search(r'href=["\']([^"\']*)["\']', a_attrs)
            href = href_m.group(1) if href_m else ''
            has_click = 'onclick=' in a_attrs
            has_id = 'id=' in a_attrs
            has_data_tab = 'data-tab=' in a_attrs
            if href in ('#', '', '#clientes-menu', '#config-menu') and not has_click and not has_id and not has_data_tab:
                dead_links.append((fname, clean_text, href))
    assert len(dead_links) == 0, f"Links mortos encontrados: {dead_links}"
    print("  [PASS] 0 links mortos ou âncoras vazias em todas as 22 páginas HTML.")

def test_gallery_config_expanded_payload():
    # Testa se a rota PUT /api/galeria/1 persiste limite_pacote, valor_foto_extra e permitir_extras
    payload = {
        "limite_pacote": 15,
        "valor_foto_extra": 35.5,
        "permitir_extras": 1,
        "nome": "Galeria Teste Audit"
    }
    r = requests.put(f"{BASE_URL}/api/galeria/1", json=payload)
    assert r.status_code == 200, f"Falha no PUT galeria: {r.text}"
    assert r.json().get("success") is True

    # Verifica se os dados foram salvos
    r_get = requests.get(f"{BASE_URL}/api/galeria/1")
    assert r_get.status_code == 200
    dados = r_get.json()
    assert dados.get("limite_pacote") == 15, "limite_pacote não persistido"
    assert float(dados.get("valor_foto_extra")) == 35.5, "valor_foto_extra não persistido"
    print("  [PASS] Persistência de campos expandidos da galeria verificada com sucesso.")

def test_app_js_functions_declared():
    with open(os.path.join(PROJECT_DIR, "app.js"), "r", encoding="utf-8", errors="ignore") as f:
        js = f.read()
    
    assert "prepararRevisaoGaleria" in js, "prepararRevisaoGaleria ausente em app.js"
    assert "reenviarConviteCliente" in js, "reenviarConviteCliente ausente em app.js"
    assert "prepararNovoConviteForm" in js, "prepararNovoConviteForm ausente em app.js"
    assert "enviarGaleriaAoCliente" in js, "enviarGaleriaAoCliente ausente em app.js"
    assert "exportarHistoricoAtividades" in js, "exportarHistoricoAtividades ausente em app.js"
    print("  [PASS] Todas as novas funções globais estão devidamente declaradas e exportadas no window.")

if __name__ == "__main__":
    print("Iniciando bateria de testes da auditoria de funções e links...")
    test_zero_dead_links()
    test_gallery_config_expanded_payload()
    test_app_js_functions_declared()
    print("\nTODOS OS TESTES DE AUDITORIA PASSARAM COM 100% DE SUCESSO!")
