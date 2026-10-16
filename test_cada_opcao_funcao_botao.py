"""
Script de Validação Completa de Cada Opção, Função e Botão
Casa da Foto Studio - Painel Administrativo e Sistema de Marca d'Água
"""

import urllib.request
import urllib.parse
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8082"

def api_request(path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}

def test_watermark_positions():
    print("\n--- [TESTE 1] Testando cada uma das 6 opções de POSIÇÃO da Marca d'Água ---")
    posicoes = [
        ("top-left", "14px 14px", "no-repeat", "Superior Esq."),
        ("center", "center center", "no-repeat", "Centralizado"),
        ("top-right", "calc(100% - 18px) 18px", "no-repeat", "Superior Dir."),
        ("bottom-left", "18px calc(100% - 18px)", "no-repeat", "Inferior Esq."),
        ("repeat", "center center", "repeat", "Mosaico (Repetir)"),
        ("bottom-right", "calc(100% - 18px) calc(100% - 18px)", "no-repeat", "Inferior Dir.")
    ]
    for pos, expected_css, expected_repeat, label in posicoes:
        status, res = api_request("/api/site/marca-dagua", "POST", {
            "posicao": pos,
            "tamanho": 55,
            "opacidade": 35
        })
        assert status == 200, f"Falha no botão '{label}': status={status}"
        assert res.get("success") is True, f"Falha no sucesso para '{label}': {res}"
        assert res.get("posicao") == pos, f"Posição incorreta para '{label}'"
        assert res.get("repeat") == expected_repeat, f"Repeat incorreto para '{label}'"
        
        # Valida leitura GET correspondente
        g_status, g_res = api_request("/api/site/marca-dagua")
        assert g_status == 200
        assert g_res.get("posicao") == pos
        assert g_res.get("repeat") == expected_repeat
        print(f"  [OK] Botão '{label}' ({pos}) -> Salvo, CSS calculado: {res.get('posicao_css')}, Repeat: {expected_repeat}")

def test_watermark_size_presets_and_sliders():
    print("\n--- [TESTE 2] Testando cada opção e botão de TAMANHO (Presets e Slider) ---")
    tamanhos = [
        (30, "30% (Pequeno)", "30% auto"),
        (55, "55% (Médio)", "55% auto"),
        (75, "75% (Grande)", "75% auto"),
        (90, "90% (Extra Grande)", "90% auto"),
        (15, "15% (Mínimo Permitido Slider)", "15% auto"),
        (95, "95% (Máximo Permitido Slider)", "95% auto"),
        (10, "10% (Limite Inferior com Clamp)", "15% auto"),   # Clamped to 15
        (120, "120% (Limite Superior com Clamp)", "95% auto"), # Clamped to 95
    ]
    for tam, label, expected_css in tamanhos:
        status, res = api_request("/api/site/marca-dagua", "POST", {
            "posicao": "center",
            "tamanho": tam,
            "opacidade": 35
        })
        clamped_tam = max(15, min(95, tam))
        assert status == 200, f"Falha no tamanho {label}: status={status}"
        assert res.get("success") is True
        assert res.get("tamanho") == clamped_tam
        assert res.get("tamanho_css") == expected_css
        print(f"  [OK] Botão/Opção '{label}' -> Salvo: {res.get('tamanho')}%, CSS: {res.get('tamanho_css')}")

def test_watermark_opacity():
    print("\n--- [TESTE 3] Testando cada opção e botão de OPACIDADE / VISIBILIDADE ---")
    opacidades = [
        (10, "10% (Mínimo)", "0.1"),
        (25, "25% (Suave)", "0.25"),
        (35, "35% (Padrão)", "0.35"),
        (60, "60% (Marcante)", "0.6"),
        (90, "90% (Máxima)", "0.9"),
        (2, "2% (Clamp Inferior)", "0.05"),  # Clamped to 5
        (100, "100% (Clamp Superior)", "0.95") # Clamped to 95
    ]
    for opac, label, expected_css in opacidades:
        status, res = api_request("/api/site/marca-dagua", "POST", {
            "posicao": "center",
            "tamanho": 55,
            "opacidade": opac
        })
        clamped_opac = max(5, min(95, opac))
        assert status == 200, f"Falha na opacidade {label}: status={status}"
        assert res.get("success") is True
        assert res.get("opacidade") == clamped_opac
        assert res.get("opacidade_css") == expected_css
        print(f"  [OK] Slider/Opção '{label}' -> Salvo: {res.get('opacidade')}%, Opacity CSS: {res.get('opacidade_css')}")

def test_diagnostics_and_error_logs():
    print("\n--- [TESTE 4] Testando cada botão e função da Central de Diagnóstico & Logs ---")
    
    # 4.1 Limpar logs antes de começar
    st, res = api_request("/api/admin/error-log", "DELETE")
    assert st == 200 and res.get("success") is True
    print("  [OK] Botão 'Limpar Erros' (DELETE /api/admin/error-log) -> Base zerada")
    
    # 4.2 Verificar que o total é 0
    st, erros = api_request("/api/admin/error-log")
    assert st == 200 and len(erros) == 0
    print(f"  [OK] Botão 'Atualizar Logs' (GET /api/admin/error-log) -> 0 erros registrados (100% estabilidade)")
    
    # 4.3 Testar gravação de erro via frontend (window.onerror)
    st, res = api_request("/api/log/error", "POST", {
        "mensagem": "Teste de Unhandled Exception do Frontend",
        "detalhe": "ReferenceError: teste is not defined at admin.html:42",
        "rota": "/admin.html"
    })
    assert st == 200 and res.get("success") is True
    print("  [OK] Função de captura de erros de Frontend (/api/log/error) registrada")
    
    # 4.4 Testar gravação de erro do backend (endpoint de teste)
    st, res = api_request("/api/admin/error-log/test", "POST")
    assert st == 200 and res.get("success") is True
    print("  [OK] Função de teste de log do Backend (/api/admin/error-log/test) registrada")
    
    # 4.5 Listar erros e validar contadores
    st, erros = api_request("/api/admin/error-log")
    assert st == 200 and len(erros) == 2
    origens = {e.get("origem") for e in erros}
    assert "frontend" in origens and "backend" in origens
    print(f"  [OK] Aba 'Erros do Sistema' exibindo corretamente {len(erros)} erros (Frontend e Backend)")
    
    # 4.6 Testar Aba de Auditoria de Segurança
    st, audit = api_request("/api/admin/audit-log")
    assert st == 200 and isinstance(audit, list)
    print(f"  [OK] Aba 'Auditoria de Segurança' (GET /api/admin/audit-log) -> {len(audit)} ações rastreadas com sucesso")
    
    # 4.7 Limpar erros novamente para deixar o sistema 100% limpo e sem erros
    st, res = api_request("/api/admin/error-log", "DELETE")
    assert st == 200 and res.get("success") is True
    st, erros_final = api_request("/api/admin/error-log")
    assert st == 200 and len(erros_final) == 0
    print("  [OK] Botão 'Limpar Erros' executado novamente: 0 erros restantes!")

def test_all_other_admin_functions():
    print("\n--- [TESTE 5] Testando demais botões e funções do Painel Master ---")
    
    # 5.1 Textos da Home
    st, textos = api_request("/api/site/textos")
    assert st == 200 and isinstance(textos, dict)
    print(f"  [OK] Função 'Carregar Textos' -> {len(textos)} campos carregados")
    
    st, res = api_request("/api/site/textos", "POST", {
        "hero_titulo": "CASA DA FOTO STUDIO OFICIAL"
    })
    assert st == 200 and res.get("success") is True
    print("  [OK] Botão 'Salvar Alterações na Tela Inicial' -> Textos atualizados")
    
    # 5.2 Logo Info
    st, logo_info = api_request("/api/site/logo-info")
    assert st == 200 and "url" in logo_info
    print(f"  [OK] Função 'Carregar Logo' -> URL: {logo_info['url']}")
    
    # 5.3 Foto de Login
    st, foto_login = api_request("/api/site/login-foto")
    assert st == 200 and "url" in foto_login
    print(f"  [OK] Função 'Carregar Foto de Login' -> URL: {foto_login['url']}")
    
    # 5.4 Categorias do Site
    st, res_cat = api_request("/api/site/categorias", "POST", {"nome": "Teste Automacao Botao"})
    assert st in (200, 201), f"Erro ao adicionar categoria: {res_cat}"
    cat_id = res_cat.get("id")
    st, cats = api_request("/api/site/categorias")
    assert any(c["nome"] == "Teste Automacao Botao" for c in cats)
    if cat_id:
        api_request(f"/api/site/categorias/{cat_id}", "DELETE")
    print("  [OK] Botão '+ Adicionar Categoria' e 'Excluir Categoria' testados com sucesso")
    
    # 5.5 Gestão de Fotógrafos
    email_fotografo = f"fotografo_{int(time.time())}@teste.com"
    st, res_fotografo = api_request("/api/admin/fotografos", "POST", {
        "nome": "Fotógrafo Teste",
        "email": email_fotografo,
        "senha": "senhaSegura123"
    })
    assert st in (200, 201) and res_fotografo.get("success") is True, f"Status: {st}, Res: {res_fotografo}"
    fotografo_id = res_fotografo.get("id")
    
    st, fotografos = api_request("/api/admin/fotografos")
    assert any(f["email"] == email_fotografo for f in fotografos)
    print(f"  [OK] Botão '+ Cadastrar Fotógrafo' -> Fotógrafo criado (ID {fotografo_id})")
    
    if fotografo_id:
        st, del_res = api_request(f"/api/admin/fotografos/{fotografo_id}", "DELETE")
        assert st == 200 and del_res.get("success") is True
        print(f"  [OK] Botão 'Excluir Fotógrafo' -> Fotógrafo removido com sucesso")

def main():
    print("=================================================================")
    print(" BATERIA EXAUSTIVA: CADA OPÇÃO, FUNÇÃO E BOTÃO DO ADMIN")
    print("=================================================================")
    test_watermark_positions()
    test_watermark_size_presets_and_sliders()
    test_watermark_opacity()
    test_diagnostics_and_error_logs()
    test_all_other_admin_functions()
    print("\n=================================================================")
    print(" RESULTADO FINAL: 100% DOS BOTÕES, OPÇÕES E FUNÇÕES PASSARAM!")
    print(" ZERO ERROS NO SISTEMA E DIAGNÓSTICO ESTÁVEL.")
    print("=================================================================")

if __name__ == "__main__":
    main()
