import glob
import os
import re
import sqlite3

PROJECT_DIR = r"c:\Users\gokai\Desktop\Casa da foto"

def audit_html_links():
    print("--- 1. Auditando links nos arquivos HTML ---")
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
    if dead_links:
        print(f"  [AVISO] {len(dead_links)} links vazios ou sem handler encontrados:")
        for dl in dead_links:
            print(f"    - {dl[0]}: link '{dl[1]}' (href='{dl[2]}')")
    else:
        print("  [OK] Zero links mortos ou âncoras vazias.")

def audit_database():
    print("\n--- 2. Auditando integridade do banco SQLite (banco.db) ---")
    db_path = os.path.join(PROJECT_DIR, "banco.db")
    if not os.path.exists(db_path):
        print("  [ERRO] banco.db não encontrado!")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    res = cur.fetchall()
    print("  [INTEGRIDADE]:", res)

    # Verifica tabelas
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  [TABELAS]: {len(tables)} tabelas encontradas -> {tables}")

    # Verifica error_log
    if 'error_log' in tables:
        cur.execute("SELECT COUNT(*) FROM error_log")
        err_count = cur.fetchone()[0]
        print(f"  [ERROR_LOG]: {err_count} erros registrados.")
        if err_count > 0:
            cur.execute("SELECT * FROM error_log ORDER BY id DESC LIMIT 10")
            for row in cur.fetchall():
                print("    ->", row)
    conn.close()

def audit_js_syntax():
    print("\n--- 3. Verificando handlers globais em app.js ---")
    with open(os.path.join(PROJECT_DIR, "app.js"), "r", encoding="utf-8", errors="ignore") as f:
        js = f.read()
    
    needed_fns = [
        "prepararRevisaoGaleria",
        "reenviarConviteCliente",
        "prepararNovoConviteForm",
        "enviarGaleriaAoCliente",
        "exportarHistoricoAtividades",
        "salvarConfiguracaoGaleriaCompleta"
    ]
    for fn in needed_fns:
        if fn in js:
            print(f"  [OK] Função '{fn}' declarada em app.js.")
        else:
            print(f"  [ALERTA] Função '{fn}' NÃO encontrada em app.js!")

def audit_html_handlers():
    print("\n--- 4. Auditando todos os onclick/onchange/onsubmit do HTML ---")
    with open(os.path.join(PROJECT_DIR, "app.js"), "r", encoding="utf-8", errors="ignore") as f:
        js_content = f.read()

    html_files = glob.glob(os.path.join(PROJECT_DIR, "*.html"))
    missing = []
    total = 0

    builtins = {'alert', 'confirm', 'prompt', 'preventDefault', 'stopPropagation',
                'togglePhotoSelect', 'finalizarSelecao', 'openZoomModal', 'closeZoomModal',
                'verificarIntegridade', 'selecionarTodasFotos', 'closeModal', 'openModal',
                'parseInt', 'parseFloat', 'Boolean', 'String', 'Number', 'console'}

    for hf in html_files:
        fname = os.path.basename(hf)
        with open(hf, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        inline = "\n".join(re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL))
        code = js_content + "\n" + inline

        handlers = re.findall(r'on(?:click|change|submit)=["\']([^"\']+)["\']', html)
        for h in handlers:
            total += 1
            m = re.search(r'(?:return\s+)?([a-zA-Z0-9_$]+)\s*\(', h)
            if m:
                fn = m.group(1)
                if fn in builtins:
                    continue
                patterns = [f'function {fn}', f'{fn} =', f'{fn}=', f'window.{fn}', f'const {fn}', f'let {fn}', f'var {fn}']
                if not any(p in code for p in patterns):
                    missing.append((fname, fn, h))

    print(f"  Total de handlers analisados: {total}")
    if missing:
        unique_missing = sorted(set(missing))
        print(f"  [ALERTA] {len(unique_missing)} funções chamadas no HTML mas não encontradas:")
        for m in unique_missing:
            print(f"    - Em {m[0]}: {m[1]} (chamada: '{m[2]}')")
    else:
        print("  [OK] 100% dos handlers chamados em tags HTML estão declarados.")

if __name__ == "__main__":
    audit_html_links()
    audit_database()
    audit_js_syntax()
    audit_html_handlers()

