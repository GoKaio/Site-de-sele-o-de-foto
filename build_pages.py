import re
import os

base_dir = r"C:\Users\gokai\.gemini\antigravity-ide\scratch\casa da foto"
source_file = os.path.join(base_dir, "galeria-config.html")

with open(source_file, "r", encoding="utf-8") as f:
    html = f.read()

tabs_meta = [
    {
        'key': 'dados',
        'file': 'galeria-dados.html',
        'title': 'Dados da galeria',
        'subtitle': 'Organize as informações e a mensagem que acolhe o cliente na galeria.',
        'breadcrumb': 'Configurações',
        'icon': '📁'
    },
    {
        'key': 'fotos',
        'file': 'galeria-fotos.html',
        'title': 'Fotos',
        'subtitle': 'Adicione, organize e revise as fotos antes de convidar o cliente para escolher.',
        'breadcrumb': 'Fotos',
        'icon': '🖼️'
    },
    {
        'key': 'selecao',
        'file': 'galeria-selecao.html',
        'title': 'Seleção e venda',
        'subtitle': 'Configure o pacote e acompanhe as favoritas, mantendo as fotos extras em uma lista separada.',
        'breadcrumb': 'Seleção e venda',
        'icon': '🛒'
    },
    {
        'key': 'prazo',
        'file': 'galeria-prazo.html',
        'title': 'Prazo e lembrete',
        'subtitle': 'Dê ao cliente tempo para escolher e prepare lembretes com a voz do estúdio.',
        'breadcrumb': 'Prazo e lembrete',
        'icon': '📅'
    },
    {
        'key': 'acesso',
        'file': 'galeria-acesso.html',
        'title': 'Acesso e privacidade',
        'subtitle': 'Cuide da privacidade das fotos e defina quem pode acompanhar a escolha.',
        'breadcrumb': 'Acesso e privacidade',
        'icon': '🔒'
    },
    {
        'key': 'clientes',
        'file': 'galeria-clientes.html',
        'title': 'Clientes',
        'subtitle': 'Gerencie destinatários, acompanhe os convites e mantenha a escolha em um só lugar.',
        'breadcrumb': 'Clientes',
        'icon': '👥'
    },
    {
        'key': 'download',
        'file': 'galeria-download.html',
        'title': 'Download',
        'subtitle': 'Defina a disponibilidade dos arquivos e os formatos da futura entrega ao cliente.',
        'breadcrumb': 'Download',
        'icon': '📥'
    },
    {
        'key': 'design',
        'file': 'galeria-design.html',
        'title': 'Design',
        'subtitle': 'Apresente a galeria com a identidade acolhedora da Casa da Foto Studio.',
        'breadcrumb': 'Design',
        'icon': '🎨'
    },
    {
        'key': 'atividades',
        'file': 'galeria-atividades.html',
        'title': 'Atividades do cliente',
        'subtitle': 'Acompanhe os acessos e o andamento da escolha, sem perder de vista o próximo passo.',
        'breadcrumb': 'Atividades',
        'icon': '📊'
    },
    {
        'key': 'historico',
        'file': 'galeria-historico.html',
        'title': 'Histórico de atividades',
        'subtitle': 'Consulte a linha do tempo da galeria e os registros de cada etapa do trabalho.',
        'breadcrumb': 'Histórico',
        'icon': '🕒'
    }
]

# Extract each tab-pane content
tab_contents = {}
for i, tab in enumerate(tabs_meta):
    key = tab['key']
    pattern = rf'(<div class="tab-pane[^"]*" id="tab-{key}"[^>]*>[\s\S]*?</div>\s*</div>\s*</div>\s*</div>)'
    # Find matching pane
    start_str = f'id="tab-{key}"'
    start_pos = html.find(start_str)
    if start_pos != -1:
        # Find start of <div
        div_start = html.rfind('<div class="tab-pane', 0, start_pos)
        # Find next tab-pane or </main>
        next_pos = len(html)
        if i < len(tabs_meta) - 1:
            next_key = tabs_meta[i+1]['key']
            next_div = html.find(f'id="tab-{next_key}"')
            if next_div != -1:
                next_pos = html.rfind('<!-- ====', 0, next_div)
        else:
            next_pos = html.find('</main>')
        
        tab_html = html[div_start:next_pos].strip()
        # Clean up display none / active
        tab_html = re.sub(r'style="display:\s*none;?"', '', tab_html)
        tab_html = re.sub(r'class="tab-pane[^"]*"', 'class="tab-pane active"', tab_html)
        tab_contents[key] = tab_html
        print(f"Extracted tab: {key}, length: {len(tab_html)}")
    else:
        print(f"FAILED to find tab: {key}")

# Get the common header up to <ul class="sidebar-menu-list" id="sidebarMenu">
sidebar_menu_start = html.find('<ul class="sidebar-menu-list" id="sidebarMenu">')
header_part = html[:sidebar_menu_start]

# Get the footer part from </main> onwards
main_end_pos = html.find('</main>')
# Everything from footer to </html>, excluding the script
footer_and_end = html[main_end_pos:]
script_pos = footer_and_end.find('<script>')
if script_pos != -1:
    footer_clean = footer_and_end[:script_pos] + "</body>\n</html>"
else:
    footer_clean = footer_and_end

# Generate the 10 files
for tab in tabs_meta:
    cur_key = tab['key']
    cur_file = tab['file']
    cur_title = tab['title']
    cur_sub = tab['subtitle']
    cur_bread = tab['breadcrumb']
    
    # Build sidebar menu for this tab
    menu_html = '<ul class="sidebar-menu-list" id="sidebarMenu">\n'
    for item in tabs_meta:
        active_cls = ' active' if item['key'] == cur_key else ''
        menu_html += f'''          <li>
            <a href="{item['file']}" class="sidebar-nav-btn{active_cls}">
              <span class="sidebar-btn-content">{item['icon']} {item['title']}</span>
            </a>
          </li>\n'''
    menu_html += '        </ul>'

    # Build the main section top bar
    main_header_html = f'''      <!-- ÁREA DE CONTEÚDO PRINCIPAL (DIREITA) -->
      <main class="admin-main-content" id="adminMainContent">
        
        <!-- Barra Superior: Breadcrumbs, Badge e Botão Prévia -->
        <div class="admin-top-meta-row">
          <div class="admin-breadcrumb">
            Projetos &nbsp;/&nbsp; Exemplo de seleção &nbsp;/&nbsp; <strong id="breadcrumbTabName">{cur_bread}</strong>
          </div>
          <span class="admin-badge-demo">Demonstração · sem valores comerciais</span>
        </div>

        <div class="admin-header-action-row">
          <div>
            <h1 class="admin-page-title" id="pageTitle">{cur_title}</h1>
            <p class="admin-page-subtitle" id="pageSubtitle">{cur_sub}</p>
          </div>
          <a href="escolha-fotos.html" class="btn-previa-cliente">
            <span>👁 Prévia do cliente</span>
          </a>
        </div>

        <!-- CONTEÚDO DA TELA: {cur_title.upper()} -->
        {tab_contents[cur_key]}
'''

    # Help card in sidebar
    help_card = '''
        <!-- Card de Ajuda no Rodapé da Sidebar -->
        <div class="sidebar-help-card">
          <strong>Cada detalhe, com cuidado.</strong>
          <p>Organize a escolha e prepare uma entrega tranquila para seu cliente.</p>
          <a href="#">Central de ajuda ↗</a>
        </div>

      </aside>
'''

    full_page_html = header_part + menu_html + help_card + main_header_html + "\n      " + footer_clean

    # Update page <title>
    full_page_html = re.sub(
        r'<title>.*?</title>',
        f'<title>{cur_title} | Configurações da Galeria | Casa da Foto Studio</title>',
        full_page_html
    )

    out_path = os.path.join(base_dir, cur_file)
    with open(out_path, "w", encoding="utf-8") as out_f:
        out_f.write(full_page_html)
    print(f"Wrote {cur_file} ({len(full_page_html)} bytes)")

print("All 10 dedicated pages generated successfully!")
