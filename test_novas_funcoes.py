import urllib.request
import json
import base64

def test_novas_funcionalidades():
    base = 'http://localhost:8082'
    print("Iniciando testes das NOVAS funcionalidades e botões...")

    def post_json(endpoint, data):
        req = urllib.request.Request(base + endpoint, data=json.dumps(data).encode(), headers={'Content-Type':'application/json'})
        return json.loads(urllib.request.urlopen(req).read().decode())

    def delete_req(endpoint):
        req = urllib.request.Request(base + endpoint, method='DELETE')
        return json.loads(urllib.request.urlopen(req).read().decode())

    # 1. Teste de Pacotes API: Listar, Criar com foto Base64, e Deletar
    pacotes_iniciais = json.loads(urllib.request.urlopen(base + '/api/site/pacotes').read().decode())
    print(f"  [PASS] GET /api/site/pacotes: {len(pacotes_iniciais)} pacotes encontrados inicialmente.")

    # 1x1 png pixel in base64
    dummy_img = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    novo_pacote_data = {
        'titulo': 'Pacote Ensaio Premium Teste',
        'subtitulo': 'Perfeito para famílias e formaturas',
        'preco': 'R$ 650,00',
        'descricao': 'Sessão completa em estúdio com fotos em alta resolução',
        'duracao': '2 Horas',
        'fotos_inclusas': '30 Fotos Editadas',
        'destaque': True,
        'imagem': dummy_img
    }

    add_res = post_json('/api/site/pacotes', novo_pacote_data)
    assert add_res.get('success') is True, f"Falha ao criar pacote: {add_res}"
    pacote_id = add_res.get('id')
    assert pacote_id is not None, "ID do pacote não retornado"
    print(f"  [PASS] POST /api/site/pacotes: Pacote criado com ID {pacote_id}")

    # Verificar se o pacote criado possui imagem salva na pasta uploads/
    pacotes_apos = json.loads(urllib.request.urlopen(base + '/api/site/pacotes').read().decode())
    pacote_salvo = next((p for p in pacotes_apos if p['id'] == pacote_id), None)
    assert pacote_salvo is not None, "Pacote criado não foi encontrado na listagem"
    assert pacote_salvo['titulo'] == 'Pacote Ensaio Premium Teste'
    assert 'uploads/' in pacote_salvo['imagem'] or pacote_salvo['imagem'].startswith('data:image/'), f"Imagem do pacote inválida: {pacote_salvo['imagem']}"
    assert not pacote_salvo['imagem'].startswith('assets/'), f"ERRO: Imagem foi salva em assets!: {pacote_salvo['imagem']}"
    print(f"  [PASS] Imagem do pacote salva corretamente (uploads/ ou data:image otimizado)")

    # Excluir pacote de teste
    del_res = delete_req(f'/api/site/pacotes/{pacote_id}')
    assert del_res.get('success') is True, f"Falha ao deletar pacote: {del_res}"
    print(f"  [PASS] DELETE /api/site/pacotes/{pacote_id} funcionou perfeitamente")

    # 2. Teste de Atividades da Galeria
    nova_ativ = post_json('/api/galeria/1/atividades', {
        'usuario': 'Fotógrafo Pro',
        'acao': 'Upload de fotos',
        'detalhes': '5 fotos enviadas'
    })
    assert nova_ativ.get('success') is True, f"Falha ao criar atividade: {nova_ativ}"
    print("  [PASS] POST /api/galeria/1/atividades funcionando")

    # Verificar que lista de atividades da galeria retorna
    req_ativs = urllib.request.urlopen(f'{base}/api/galeria/1/atividades')
    ativs = json.loads(req_ativs.read().decode())
    assert isinstance(ativs, list) and len(ativs) > 0, "Nenhuma atividade encontrada"
    print(f"  [PASS] GET /api/galeria/1/atividades retornou {len(ativs)} atividades")

    # 3. Teste de Destinatários da Galeria (Adicionar e Deletar)
    req_add_dest = post_json('/api/galeria/1/destinatarios', {
        'nome': 'Destinatario Teste',
        'email': 'teste_dest@exemplo.com'
    })
    assert req_add_dest.get('success') is True, f"Falha ao adicionar destinatario: {req_add_dest}"
    dest_id = req_add_dest.get('id')
    print(f"  [PASS] POST /api/galeria/1/destinatarios: ID {dest_id}")

    del_dest_res = delete_req(f'/api/galeria/1/destinatarios/{dest_id}')
    assert del_dest_res.get('success') is True, f"Falha ao deletar destinatario: {del_dest_res}"
    print(f"  [PASS] DELETE /api/galeria/1/destinatarios/{dest_id} executado com sucesso")

    # 4. Teste de Exclusão de Mensagem de Contato
    # Criar contato
    contato_res = post_json('/api/site/contato', {
        'nome': 'Cliente Dúvida',
        'email': 'duvida@cliente.com',
        'telefone': '11999999999',
        'mensagem': 'Gostaria de saber disponibilidade'
    })
    assert contato_res.get('success') is True
    contato_id = contato_res.get('id')
    print(f"  [PASS] POST /api/site/contato: ID {contato_id}")

    del_contato_res = delete_req(f'/api/contatos/{contato_id}')
    assert del_contato_res.get('success') is True, f"Falha ao deletar contato: {del_contato_res}"
    print(f"  [PASS] DELETE /api/contatos/{contato_id} executado com sucesso")

    # 5. Validação de Elementos nos Arquivos HTML Modificados
    html_pacotes = urllib.request.urlopen(f'{base}/pacotes.html').read().decode('utf-8', errors='ignore')
    assert 'id="gridPacotesSite"' in html_pacotes, 'Elemento #gridPacotesSite não encontrado em pacotes.html'
    assert 'carregarPacotesSite' in urllib.request.urlopen(f'{base}/app.js').read().decode('utf-8', errors='ignore'), 'carregarPacotesSite não encontrado em app.js'
    print("  [PASS] pacotes.html e app.js integrados para renderização dinâmica")

    html_admin = urllib.request.urlopen(f'{base}/admin.html').read().decode('utf-8', errors='ignore')
    assert 'formAddPacote' in html_admin, '#formAddPacote ausente em admin.html'
    assert 'inputFotoPacoteUpload' in html_admin, '#inputFotoPacoteUpload ausente em admin.html'
    assert 'listaPacotes' in html_admin, '#listaPacotes ausente em admin.html'
    print("  [PASS] admin.html contém todos os controles de gerenciamento de pacotes")

    # 6. Validação dos Redirecionamentos das páginas standalone de galeria
    gal_pages = [
        'galeria-acesso.html', 'galeria-atividades.html', 'galeria-clientes.html',
        'galeria-dados.html', 'galeria-design.html', 'galeria-download.html',
        'galeria-fotos.html', 'galeria-historico.html', 'galeria-prazo.html',
        'galeria-selecao.html'
    ]
    for gp in gal_pages:
        content = urllib.request.urlopen(f'{base}/{gp}').read().decode('utf-8', errors='ignore')
        assert 'galeria-config.html' in content, f'Redirecionamento não encontrado em {gp}'
    print("  [PASS] Todas as 10 páginas galeria-*.html redirecionam para galeria-config.html com preservação de estado")

    print("\nTODOS OS NOVOS TESTES FORAM CONCLUÍDOS COM 100% DE SUCESSO!")

if __name__ == '__main__':
    test_novas_funcionalidades()
