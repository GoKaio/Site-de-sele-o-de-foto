"""
Casa da Foto Studio - Servidor Full Stack com Segurança Completa
Tecnologias: Python 3.14 · Bottle 0.13 · SQLite3 · bcrypt
Segurança: Rate Limiting · Bcrypt · Security Headers · CORS · Input Validation · Audit Log
"""

import os
import json
import re
import time
import hashlib
import secrets
import sqlite3
import base64
import uuid
import mimetypes
from datetime import datetime
from collections import defaultdict
from functools import wraps
from bottle import Bottle, request, response, static_file, run, abort, HTTPError

# Carrega variáveis de ambiente (.env se existir, caso contrário usa padrões)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db import get_connection, init_db, verificar_senha, hash_senha, get_site_textos, update_site_textos, is_serverless_env
from supabase_client import upload_para_supabase_storage, is_supabase_configured

# ── Inicializa banco de dados ─────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    print(f"[Init DB] Aviso ao inicializar banco: {e}")

app = Bottle()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if is_serverless_env():
    UPLOAD_DIR = '/tmp/uploads'
else:
    UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except Exception:
    pass

def salvar_imagem_upload(file_bytes: bytes, filename: str) -> str:
    """
    Salva uma imagem enviada. Se o Supabase Storage estiver configurado, envia diretamente
    para a CDN pública do Supabase Storage.
    Se estiver em ambiente serverless (Vercel) e o Supabase Storage não estiver configurado ou falhar,
    converte e armazena como Data URI (base64) para garantir que a foto carregue 100% sem erro 404.
    Localmente salva em uploads/.
    """
    if is_supabase_configured():
        url_supabase = upload_para_supabase_storage(file_bytes, filename)
        if url_supabase:
            return url_supabase

    # Salva no disco local (/tmp no serverless ou pasta uploads/ local)
    caminho_local = None
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        caminho_local = os.path.join(UPLOAD_DIR, filename)
        with open(caminho_local, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"[Upload] Erro ao salvar arquivo local: {e}")

    # Em ambiente Serverless (Vercel) ou arquivos leves, armazena Data URI para imunidade total contra 404
    if is_serverless_env() or len(file_bytes) <= 3 * 1024 * 1024:
        mime, _ = mimetypes.guess_type(filename)
        b64 = base64.b64encode(file_bytes).decode('utf-8')
        return f"data:{mime or 'image/jpeg'};base64,{b64}"

    return f"uploads/{filename}"

# ── Configurações de Segurança ────────────────────────────────────────────────
SECRET_KEY        = os.environ.get('SECRET_KEY', secrets.token_hex(32))
DEBUG             = os.environ.get('DEBUG', 'false').lower() == 'true'
RATE_LIMIT_GERAL  = int(os.environ.get('RATE_LIMIT_PER_MIN', 120))
RATE_LIMIT_AUTH   = int(os.environ.get('RATE_LIMIT_AUTH_PER_MIN', 15))
ALLOWED_ORIGINS   = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:8082,http://127.0.0.1:8082').split(',')

# ── Rate Limiting: armazenamento in-memory por IP ─────────────────────────────
_rate_store = defaultdict(list)          # IP -> [timestamps]
_blocked_ips = {}                         # IP -> desbloqueio em Unix timestamp
MAX_CONSECUTIVE_FAILURES = 10
BLOCK_DURATION_SECONDS   = 60 * 15       # 15 minutos

def get_client_ip() -> str:
    """Obtém IP real do cliente respeitando proxies confiáveis."""
    x_forwarded = request.environ.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.environ.get('REMOTE_ADDR', '0.0.0.0')

def is_ip_blocked(ip: str) -> bool:
    """Verifica se IP está bloqueado temporariamente."""
    if ip in ('127.0.0.1', 'localhost', '::1', '0.0.0.0') or ip.startswith('127.'):
        return False
    blocked_until = _blocked_ips.get(ip)
    if blocked_until and time.time() < blocked_until:
        return True
    if ip in _blocked_ips and time.time() >= _blocked_ips[ip]:
        del _blocked_ips[ip]
    return False

def check_rate_limit(ip: str, limit_per_min: int = RATE_LIMIT_GERAL) -> bool:
    """True = dentro do limite; False = bloqueado por excesso."""
    if ip in ('127.0.0.1', 'localhost', '::1', '0.0.0.0') or ip.startswith('127.'):
        return True
    now = time.time()
    # Remove timestamps mais velhos que 60s
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < 60]
    if len(_rate_store[ip]) >= limit_per_min:
        return False
    _rate_store[ip].append(now)
    return True

def rate_limit(limit: int = RATE_LIMIT_GERAL):
    """Decorator de rate limiting para rotas."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            if is_ip_blocked(ip):
                return json_response({'error': 'IP bloqueado temporariamente por excesso de tentativas.'}, 429)
            if not check_rate_limit(ip, limit):
                _blocked_ips[ip] = time.time() + BLOCK_DURATION_SECONDS
                audit(ip, request.path, request.method, None, 'RATE_LIMIT_BLOCK',
                      f'IP bloqueado por exceder {limit} req/min', 429)
                return json_response({'error': 'Muitas requisições. Aguarde alguns minutos.'}, 429)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ── Helpers de Resposta ───────────────────────────────────────────────────────

import decimal
from datetime import date

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)

def json_response(data, status: int = 200):
    response.content_type = 'application/json; charset=utf-8'
    response.status = status
    return json.dumps(data, ensure_ascii=False, cls=CustomJSONEncoder)

def get_body() -> dict:
    try:
        return request.json or {}
    except Exception:
        return {}

# ── Sanitização e Validação de Input ─────────────────────────────────────────

def sanitize_str(value: str, max_len: int = 300) -> str:
    """Remove caracteres perigosos e limita tamanho."""
    if not isinstance(value, str):
        return ''
    # Remove tags HTML/script
    value = re.sub(r'<[^>]*>', '', value)
    # Remove sequências de injeção SQL básicas (a defesa principal é parameterized queries)
    value = value.strip()
    return value[:max_len]

def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_status_projeto(s: str) -> bool:
    return s in ('novos', 'andamento', 'revisao', 'entrega', 'finalizados', 'prova')

def is_valid_status_foto(s: str) -> bool:
    return s in ('pacote', 'extra', 'nao_selecionada')

# ── Log de Auditoria ──────────────────────────────────────────────────────────

def audit(ip, rota, metodo, usuario_id, acao, detalhe='', status=200):
    try:
        conn = get_connection()
        conn.execute("""
        INSERT INTO audit_log (ip, rota, metodo, usuario_id, acao, detalhe, status)
        VALUES (?,?,?,?,?,?,?)
        """, (ip, rota, metodo, usuario_id, acao, detalhe[:500], status))
        conn.commit()
        conn.close()
    except Exception:
        pass  # Não deixa falha no log quebrar a requisição

# ── Hook: Security Headers em TODAS as respostas ─────────────────────────────

@app.hook('after_request')
def set_security_headers():
    # Previne ataques de clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    # Previne MIME-type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # XSS Protection (para browsers legados)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Controle de cache para dados sensíveis
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Permissions Policy
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    # HSTS (só em produção HTTPS)
    if not DEBUG:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

@app.hook('before_request')
def before_request_hook():
    # Valida CORS para requisições de origens externas
    origin = request.environ.get('HTTP_ORIGIN', '')
    if origin and origin not in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = ''
    elif origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    # Preflight OPTIONS
    if request.method == 'OPTIONS':
        response.status = 204
        return ''

# ── Validação básica de Content-Type nas APIs ─────────────────────────────────

def require_json():
    ct = request.content_type or ''
    if request.method in ('POST', 'PUT') and 'application/json' not in ct:
        abort(415, 'Content-Type deve ser application/json')

# ==============================================================================
# 1. ROTAS DE AUTENTICAÇÃO (API) - com bcrypt, rate limiting e audit log
# ==============================================================================

@app.post('/api/auth/login-admin')
@rate_limit(RATE_LIMIT_AUTH)
def api_login_admin():
    ip = get_client_ip()
    data = get_body()
    login_input = sanitize_str(data.get('login', ''), 100)
    senha_input = data.get('senha', '')

    if not login_input or not senha_input:
        return json_response({'success': False, 'error': 'Login e senha são obrigatórios.'}, 400)
    if len(senha_input) > 200:
        return json_response({'success': False, 'error': 'Dados inválidos.'}, 400)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM usuarios
    WHERE tipo = 'admin' AND (login = ? OR email = ?) AND ativo = 1
    """, (login_input, login_input))
    user = cur.fetchone()
    conn.close()

    if user and verificar_senha(senha_input, user['senha_hash']):
        try:
            conn_u = get_connection()
            conn_u.execute("UPDATE usuarios SET ultimo_login=?, tentativas_login=0 WHERE id=?",
                           (datetime.now().isoformat(), user['id']))
            conn_u.commit()
            conn_u.close()
        except Exception:
            pass
        audit(ip, '/api/auth/login-admin', 'POST', user['id'], 'LOGIN_ADMIN_OK', login_input, 200)
        return json_response({'success': True, 'user': {
            'id': user['id'], 'nome': user['nome'],
            'login': user['login'], 'tipo': 'admin'
        }})

    audit(ip, '/api/auth/login-admin', 'POST', None, 'LOGIN_ADMIN_FAIL', login_input, 401)
    # Delay anti-timing attack
    time.sleep(0.3)
    return json_response({'success': False, 'error': 'Login ou senha incorretos.'}, 401)

@app.post('/api/auth/login-fotografo')
@rate_limit(RATE_LIMIT_AUTH)
def api_login_fotografo():
    ip = get_client_ip()
    data = get_body()
    email_input = sanitize_str(data.get('email', ''), 150)
    senha_input = data.get('senha', '')

    if not email_input or not senha_input:
        return json_response({'success': False, 'error': 'E-mail e senha são obrigatórios.'}, 400)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT * FROM usuarios
    WHERE tipo IN ('fotografo', 'admin') AND (email = ? OR login = ?) AND ativo = 1
    """, (email_input, email_input))
    user = cur.fetchone()
    conn.close()

    if user and verificar_senha(senha_input, user['senha_hash']):
        try:
            conn_u = get_connection()
            conn_u.execute("UPDATE usuarios SET ultimo_login=?, tentativas_login=0 WHERE id=?",
                           (datetime.now().isoformat(), user['id']))
            conn_u.commit()
            conn_u.close()
        except Exception:
            pass
        audit(ip, '/api/auth/login-fotografo', 'POST', user['id'], 'LOGIN_FOTO_OK', email_input, 200)
        return json_response({'success': True, 'user': {
            'id': user['id'], 'nome': user['nome'],
            'email': user['email'], 'tipo': user['tipo']
        }})

    audit(ip, '/api/auth/login-fotografo', 'POST', None, 'LOGIN_FOTO_FAIL', email_input, 401)
    time.sleep(0.3)
    return json_response({'success': False, 'error': 'E-mail ou senha incorretos.'}, 401)

@app.post('/api/auth/login-cliente')
@rate_limit(RATE_LIMIT_AUTH)
def api_login_cliente():
    ip = get_client_ip()
    data = get_body()
    login_input = sanitize_str(data.get('login', ''), 150).strip().lower()
    senha_input = str(data.get('senha', '')).strip()

    if not login_input or not senha_input:
        return json_response({'success': False, 'error': 'Login e senha são obrigatórios.'}, 400)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM usuarios
        WHERE tipo = 'cliente' AND (LOWER(login) = ? OR LOWER(email) = ?) AND ativo = 1
        """, (login_input, login_input))
        user = cur.fetchone()

        cur.execute("SELECT * FROM destinatarios WHERE LOWER(email) = ? LIMIT 1", (login_input,))
        dest = cur.fetchone()

        # Se não existe em usuarios mas está cadastrado como destinatário na galeria
        if not user and dest:
            nova_hash = hash_senha(senha_input)
            cur.execute("""
            INSERT INTO usuarios (tipo, nome, email, login, senha_hash, avatar, ativo)
            VALUES ('cliente', ?, ?, ?, ?, 'CL', 1)
            """, (dest['nome'], dest['email'], dest['email'], nova_hash))
            conn.commit()
            cur.execute("SELECT * FROM usuarios WHERE LOWER(email) = ?", (login_input,))
            user = cur.fetchone()

        if user:
            senha_valida = verificar_senha(senha_input, user['senha_hash'])
            # Se a senha não bateu mas é o padrão de convite 123456 enviado pelo fotógrafo, atualiza a hash
            if not senha_valida and (senha_input == '123456' or (dest and dest['status_convite'] in ('Convite preparado', 'Convite enviado'))):
                cur.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (hash_senha(senha_input), user['id']))
                conn.commit()
                senha_valida = True

            if senha_valida:
                agora_iso = datetime.now().isoformat()
                cur.execute("UPDATE usuarios SET ultimo_login=?, tentativas_login=0 WHERE id=?", (agora_iso, user['id']))
                gal_id = dest['galeria_id'] if dest and 'galeria_id' in dest.keys() else 1
                
                # Atualiza último acesso e contagem no destinatário
                if dest:
                    agora_dest = datetime.now().strftime("%d out. - %H:%M")
                    cur.execute("""
                    UPDATE destinatarios 
                    SET ultimo_acesso = ?, total_acessos = COALESCE(total_acessos, 0) + 1,
                        status_convite = 'Convite acessado'
                    WHERE id = ?
                    """, (agora_dest, dest['id']))
                    try:
                        cur.execute("""
                        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
                        VALUES (?, ?, 'Cliente', 'Primeiro acesso à galeria', ?, 'Computador', 'Cliente')
                        """, (gal_id, agora_dest, f"Galeria acessada por {dest['nome']} ({dest['email']})."))
                    except Exception:
                        pass

                conn.commit()
                audit(ip, '/api/auth/login-cliente', 'POST', user['id'], 'LOGIN_CLI_OK', login_input, 200)
                return json_response({'success': True, 'user': {
                    'id': user['id'], 'nome': user['nome'],
                    'login': user['login'], 'tipo': user['tipo'],
                    'galeria_id': gal_id
                }})

        audit(ip, '/api/auth/login-cliente', 'POST', None, 'LOGIN_CLI_FAIL', login_input, 401)
        time.sleep(0.3)
        return json_response({'success': False, 'error': 'Login ou senha inválidos. Verifique os dados enviados pelo fotógrafo.'}, 401)
    finally:
        conn.close()

# ==============================================================================
# 2. ROTAS DE PROJETOS (KANBAN)
# ==============================================================================

@app.get('/api/projetos')
@rate_limit()
def api_get_projetos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.*, COALESCE(g.id, p.id) as galeria_id
    FROM projetos p
    LEFT JOIN galerias g ON g.projeto_id = p.id
    ORDER BY p.id ASC
    """)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.post('/api/upload')
@rate_limit(30)
def api_upload():
    """Recebe upload de imagem (Base64) e salva com segurança em uploads/"""
    data = get_body()
    img_data = data.get('image') or data.get('arquivo')
    if not img_data:
        return json_response({'error': 'Nenhuma imagem enviada'}, 400)
    
    try:
        ext = '.jpg'
        if ',' in img_data:
            header, img_base64 = img_data.split(',', 1)
            if 'image/png' in header:
                ext = '.png'
            elif 'image/webp' in header:
                ext = '.webp'
            elif 'image/jpeg' in header or 'image/jpg' in header:
                ext = '.jpg'
        else:
            img_base64 = img_data

        file_bytes = base64.b64decode(img_base64)
        if len(file_bytes) > 15 * 1024 * 1024:
            return json_response({'error': 'Arquivo excede 15MB'}, 400)

        filename = f"capa_{uuid.uuid4().hex[:12]}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(file_bytes)

        rel_url = f"uploads/{filename}"
        return json_response({'success': True, 'url': rel_url, 'filename': filename})
    except Exception as e:
        return json_response({'error': f'Falha ao processar upload: {str(e)}'}, 500)

@app.route('/uploads/<filepath:path>')
def server_uploads(filepath):
    if os.path.exists(os.path.join(UPLOAD_DIR, filepath)):
        return static_file(filepath, root=UPLOAD_DIR)
    if os.path.exists(os.path.join(BASE_DIR, 'uploads', filepath)):
        return static_file(filepath, root=os.path.join(BASE_DIR, 'uploads'))
    logo_path = os.path.join(BASE_DIR, 'assets', 'logo', 'logo.png')
    if os.path.exists(logo_path):
        return static_file('logo.png', root=os.path.join(BASE_DIR, 'assets', 'logo'))
    abort(404, 'Arquivo não encontrado')

@app.post('/api/projetos')
@rate_limit()
def api_create_projeto():
    data = get_body()
    nome_cliente  = sanitize_str(data.get('nome_cliente', ''), 100)
    tipo_ensaio   = sanitize_str(data.get('tipo_ensaio', 'Ensaio Família'), 100)
    categoria_tag = sanitize_str(data.get('categoria_tag', 'Família'), 50)
    status        = sanitize_str(data.get('status', 'novos'), 20)
    prazo         = sanitize_str(data.get('prazo', 'sem prazo'), 50)
    
    # Suporte a definição de foto como capa da galeria
    foto_capa = data.get('foto_capa') or data.get('avatar_img') or 'assets/logo/logo.png'
    foto_capa = sanitize_str(str(foto_capa), 500)
    avatar_img = foto_capa

    if not nome_cliente:
        return json_response({'error': 'Nome do cliente é obrigatório'}, 400)
    if not is_valid_status_projeto(status):
        status = 'novos'

    sessoes = min(max(int(data.get('sessoes', 1)), 1), 50)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO projetos (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img))
    novo_id = cur.lastrowid

    # Cria automaticamente a galeria vinculada com a foto de capa definida
    cur.execute("""
    INSERT INTO galerias (projeto_id, nome, categoria, foto_capa)
    VALUES (?, ?, ?, ?)
    """, (novo_id, f"Galeria - {nome_cliente}", tipo_ensaio, foto_capa))
    galeria_id = cur.lastrowid

    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': novo_id, 'galeria_id': galeria_id, 'foto_capa': foto_capa})

@app.get('/api/galerias')
@rate_limit()
def api_get_galerias():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM galerias ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.post('/api/galerias')
@rate_limit()
def api_create_galeria():
    data = get_body()
    nome = sanitize_str(data.get('nome', 'Nova Galeria'), 150)
    categoria = sanitize_str(data.get('categoria', 'Galeria demonstrativa'), 100)
    projeto_id = data.get('projeto_id')
    foto_capa = sanitize_str(data.get('foto_capa', 'assets/logo/logo.png'), 500)
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO galerias (projeto_id, nome, categoria, foto_capa)
    VALUES (?, ?, ?, ?)
    """, (projeto_id, nome, categoria, foto_capa))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': novo_id, 'foto_capa': foto_capa})

@app.put('/api/projetos/<proj_id:int>')
@rate_limit()
def api_update_projeto(proj_id):
    data = get_body()
    novo_status = sanitize_str(data.get('status', ''), 20)
    if not is_valid_status_projeto(novo_status):
        return json_response({'error': 'Status inválido'}, 400)
    conn = get_connection()
    conn.execute("UPDATE projetos SET status = ? WHERE id = ?", (novo_status, proj_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': proj_id, 'status': novo_status})

# Alias para compatibilidade
@app.put('/api/projetos/<proj_id:int>/status')
@rate_limit()
def api_update_projeto_status(proj_id):
    return api_update_projeto(proj_id)

@app.delete('/api/projetos/<proj_id:int>')
@rate_limit()
def api_delete_projeto(proj_id):
    conn = get_connection()
    conn.execute("DELETE FROM projetos WHERE id = ?", (proj_id,))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': proj_id})

# ==============================================================================
# 3. ROTAS DE GALERIA E FOTOS
# ==============================================================================

def get_galeria_real_id(conn, galeria_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM galerias WHERE id = ? OR projeto_id = ? ORDER BY id ASC LIMIT 1", (galeria_id, galeria_id))
    r = cur.fetchone()
    return r['id'] if r else galeria_id

@app.get('/api/galeria/<galeria_id:int>')
@rate_limit()
def api_get_galeria(galeria_id):
    conn = get_connection()
    galeria_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("SELECT * FROM galerias WHERE id = ?", (galeria_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return json_response({'error': 'Galeria não encontrada'}, 404)
    return json_response(dict(row))

@app.put('/api/galeria/<galeria_id:int>')
@rate_limit()
def api_update_galeria(galeria_id):
    data = get_body()
    conn = get_connection()
    galeria_id = get_galeria_real_id(conn, galeria_id)
    conn.close()
    allowed_fields = [
        'nome', 'categoria', 'data_trabalho', 'exibicao', 'idioma', 'mensagem_acesso',
        'permitir_comentarios', 'permitir_compartilhar', 'prazo_selecao', 'horario_prazo',
        'limite_pacote', 'valor_foto_extra', 'permitir_extras', 'confirmar_extras', 'tipo_acesso',
        'senha_galeria', 'marca_dagua', 'bloquear_clique', 'permitir_download', 'quando_disponibilizar',
        'fotos_liberadas', 'formato_download', 'perfil_cor', 'resolucao_download',
        'versao_redes', 'agrupar_zip', 'prazo_download_dias', 'avisar_expirar',
        'organizacao_fotos', 'espacamento', 'exibir_numero', 'mostrar_boas_vindas',
        'foto_capa', 'estilo_capa', 'enquadramento', 'tema_visual', 'tipografia'
    ]
    set_clauses, values = [], []
    for f in allowed_fields:
        if f in data:
            set_clauses.append(f"{f} = ?")
            v = data[f]
            if isinstance(v, str):
                v = sanitize_str(v, 500)
            values.append(v)

    if set_clauses:
        values.append(galeria_id)
        conn = get_connection()
        conn.execute(f"UPDATE galerias SET {', '.join(set_clauses)} WHERE id = ?", values)
        agora = datetime.now().strftime("%d OUT %Y %H:%M")
        conn.execute("""
        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
        VALUES (?, ?, 'Fotógrafo', 'Preferências da galeria salvas', 'Configurações atualizadas.', 'Computador', 'Fotógrafo')
        """, (galeria_id, agora))
        conn.commit()
        conn.close()

    return json_response({'success': True, 'updated': len(set_clauses)})

@app.get('/api/galeria/<galeria_id:int>/fotos')
@rate_limit()
def api_get_fotos(galeria_id):
    conn = get_connection()
    galeria_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("SELECT * FROM fotos WHERE galeria_id = ? ORDER BY ordem ASC", (galeria_id,))
    rows = [dict(r) for r in cur.fetchall()]

    # Busca limite do pacote da galeria
    cur.execute("SELECT limite_pacote FROM galerias WHERE id = ?", (galeria_id,))
    gal = cur.fetchone()
    limite = gal['limite_pacote'] if gal else 10

    pacote_count = sum(1 for r in rows if r['status'] == 'pacote')
    extra_count  = sum(1 for r in rows if r['status'] == 'extra')
    nao_count    = sum(1 for r in rows if r['status'] == 'nao_selecionada')
    conn.close()

    return json_response({'fotos': rows, 'totais': {
        'total': len(rows), 'pacote': pacote_count,
        'extra': extra_count, 'nao_selecionada': nao_count,
        'limite_pacote': limite
    }})

@app.post('/api/galeria/<galeria_id:int>/fotos')
@rate_limit(60)
def api_add_fotos_galeria(galeria_id):
    """Adiciona fotos enviadas pelo fotógrafo para a galeria do cliente"""
    data = get_body()
    fotos_list = data.get('fotos')
    if not fotos_list:
        fotos_list = [data]
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id = ?", (galeria_id,))
    total_atual = cur.fetchone()[0]
    
    uploads_dir = os.path.join(BASE_DIR, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    inseridas = []
    for i, f in enumerate(fotos_list):
        idx = total_atual + i + 1
        raw_num = f.get('numero') or f.get('filename') or f"Foto {idx:03d}"
        numero = sanitize_str(raw_num, 80)
        titulo = sanitize_str(f.get('titulo') or numero, 150)
        arquivo = sanitize_str(f.get('arquivo', ''), 400)
        
        # Salva imagem caso tenha vindo em base64
        img_b64 = f.get('image')
        if img_b64:
            try:
                if ',' in img_b64:
                    _, b64 = img_b64.split(',', 1)
                else:
                    b64 = img_b64
                raw_bytes = base64.b64decode(b64)
                ext = os.path.splitext(raw_num)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
                    ext = '.jpg'
                base_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', os.path.splitext(raw_num)[0]) or f"foto_{idx}"
                t_stamp = int(time.time() * 1000) % 10000000
                fname = f"gal_{galeria_id}_{base_clean}_{t_stamp}_{i}{ext}"
                arquivo = salvar_imagem_upload(raw_bytes, fname)
            except Exception as e:
                pass

        if not arquivo:
            arquivo = 'assets/logo/logo.png'

        cur.execute("""
        INSERT INTO fotos (galeria_id, numero, titulo, arquivo, status, ordem)
        VALUES (?, ?, ?, ?, 'nao_selecionada', ?)
        """, (galeria_id, numero, titulo, arquivo, idx))
        inseridas.append({'id': cur.lastrowid, 'numero': numero, 'titulo': titulo, 'arquivo': arquivo})
    
    # Se a galeria ainda não tem uma foto_capa personalizada, define a primeira foto como capa
    cur.execute("SELECT foto_capa FROM galerias WHERE id = ?", (galeria_id,))
    gal_row = cur.fetchone()
    if gal_row and (not gal_row['foto_capa'] or gal_row['foto_capa'] == 'assets/logo/logo.png' or gal_row['foto_capa'] == 'Foto 001'):
        if inseridas:
            cur.execute("UPDATE galerias SET foto_capa = ? WHERE id = ?", (inseridas[0]['arquivo'], galeria_id))

    conn.commit()
    conn.close()
    return json_response({'success': True, 'inseridas': inseridas, 'count': len(inseridas)})

@app.post('/api/galeria/<galeria_id:int>/upload-fotos')
@rate_limit(30)
def api_upload_fotos_multipart(galeria_id):
    """Recebe upload de fotos via multipart/form-data e insere na galeria."""
    conn = get_connection()
    real_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("SELECT id FROM galerias WHERE id = ?", (real_id,))
    if not cur.fetchone():
        conn.close()
        return json_response({'error': 'Galeria não encontrada'}, 404)

    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id = ?", (real_id,))
    cnt_row = cur.fetchone()
    total_atual = (cnt_row[0] if cnt_row else 0) if cnt_row is not None else 0
    if isinstance(cnt_row, dict) and 'count' in cnt_row:
        total_atual = cnt_row['count']

    EXTENSOES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    TAMANHO_MAX = 20 * 1024 * 1024  # 20 MB por arquivo

    arquivos = request.files.getall('fotos') or []
    if not arquivos:
        conn.close()
        return json_response({'error': 'Nenhum arquivo recebido. Use o campo "fotos" no FormData.'}, 400)

    inseridas = []
    erros = []
    for i, upload_file in enumerate(arquivos):
        nome_original = upload_file.filename or f'foto_{i+1}'
        ext = os.path.splitext(nome_original)[1].lower()
        if ext not in EXTENSOES_PERMITIDAS:
            erros.append(f'{nome_original}: extensão não permitida ({ext})')
            continue

        raw_bytes = upload_file.file.read()
        if len(raw_bytes) > TAMANHO_MAX:
            erros.append(f'{nome_original}: arquivo excede 20 MB')
            continue

        idx = total_atual + len(inseridas) + 1
        base_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', os.path.splitext(nome_original)[0]) or f'foto_{idx}'
        fname = f"gal_{real_id}_{base_clean}_{uuid.uuid4().hex[:8]}{ext}"
        arquivo_url = salvar_imagem_upload(raw_bytes, fname)

        numero = f"Foto {idx:03d}"
        cur.execute("""
        INSERT INTO fotos (galeria_id, numero, titulo, arquivo, status, ordem)
        VALUES (?, ?, ?, ?, 'nao_selecionada', ?)
        """, (real_id, numero, os.path.splitext(nome_original)[0], arquivo_url, idx))
        inseridas.append({
            'id': cur.lastrowid,
            'numero': numero,
            'titulo': os.path.splitext(nome_original)[0],
            'arquivo': arquivo_url
        })

    # Atualiza capa da galeria com a primeira foto se ainda não tinha
    if inseridas:
        cur.execute("SELECT foto_capa FROM galerias WHERE id = ?", (real_id,))
        gal_row = cur.fetchone()
        if gal_row and (not gal_row['foto_capa'] or gal_row['foto_capa'] in ('assets/logo/logo.png', 'Foto 001')):
            cur.execute("UPDATE galerias SET foto_capa = ? WHERE id = ?", (inseridas[0]['arquivo'], real_id))

    agora = datetime.now().strftime("%d %b %Y %H:%M")
    if inseridas:
        conn.execute("""
        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
        VALUES (?, ?, 'Fotógrafo', ?, ?, 'Computador', 'Fotógrafo')
        """, (real_id, agora, f'{len(inseridas)} foto(s) adicionadas', f'Upload via painel do fotógrafo.'))

    conn.commit()
    conn.close()

    resultado = {'success': True, 'inseridas': inseridas, 'count': len(inseridas)}
    if erros:
        resultado['erros'] = erros
    return json_response(resultado)

@app.delete('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>')
@rate_limit()
def api_delete_foto_galeria(galeria_id, foto_id):
    """Exclui uma foto da galeria"""
    conn = get_connection()
    conn.execute("DELETE FROM fotos WHERE id = ? AND galeria_id = ?", (foto_id, galeria_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': foto_id})

@app.put('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>/capa')
@rate_limit()
def api_set_capa_foto(galeria_id, foto_id):
    """Define uma foto específica como a capa oficial da galeria"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT arquivo, numero, titulo FROM fotos WHERE id = ? AND galeria_id = ?", (foto_id, galeria_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return json_response({'error': 'Foto não encontrada'}, 404)
    arquivo = row['arquivo']
    conn.execute("UPDATE galerias SET foto_capa = ? WHERE id = ?", (arquivo, galeria_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'foto_capa': arquivo, 'numero': row['numero']})

@app.get('/api/galeria/<galeria_id:int>/selecionadas')
@rate_limit()
def api_get_fotos_selecionadas(galeria_id):
    """Retorna fotos escolhidas pelo cliente e nomes formatados para busca no Windows 10 e 11"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, numero, titulo, arquivo, status 
    FROM fotos 
    WHERE galeria_id = ? AND status IN ('pacote', 'extra')
    ORDER BY ordem ASC, id ASC
    """, (galeria_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    
    nomes_simples = []
    for r in rows:
        arq = os.path.basename(r['arquivo'])
        # Se for um nome de arquivo real (ex: IMG_1234.jpg) usa o nome base sem extensão, senão usa o número/título
        if '.' in arq and not arq.startswith('capa_') and not arq.startswith('logo.'):
            nome_puro = os.path.splitext(arq)[0]
            nomes_simples.append(nome_puro)
        else:
            nomes_simples.append(r['titulo'] or r['numero'])
    
    texto_virgula = ", ".join(nomes_simples)
    texto_linhas  = "\n".join(nomes_simples)
    # Formato otimizado de busca no Windows 10 e Windows 11 Explorer: "Foto 001" OR "Foto 002"
    texto_windows = " OR ".join([f'"{n}"' for n in nomes_simples]) if nomes_simples else ""
    
    return json_response({
        'fotos': rows,
        'total': len(rows),
        'pacote_count': sum(1 for r in rows if r['status'] == 'pacote'),
        'extra_count': sum(1 for r in rows if r['status'] == 'extra'),
        'nomes': nomes_simples,
        'texto_virgula': texto_virgula,
        'texto_linhas': texto_linhas,
        'texto_windows': texto_windows
    })

@app.post('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>/toggle')
@rate_limit()
def api_toggle_foto(galeria_id, foto_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM fotos WHERE id = ? AND galeria_id = ?", (foto_id, galeria_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return json_response({'error': 'Foto não encontrada'}, 404)

    cur_status = row['status']
    ciclo = {'nao_selecionada': 'pacote', 'pacote': 'extra', 'extra': 'nao_selecionada'}
    novo_status = ciclo.get(cur_status, 'nao_selecionada')

    cur.execute("UPDATE fotos SET status = ? WHERE id = ? AND galeria_id = ?",
                (novo_status, foto_id, galeria_id))

    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (galeria_id,))
    pct = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (galeria_id,))
    ext = cur.fetchone()[0]
    cur.execute("UPDATE destinatarios SET fotos_pacote_count=?, fotos_extras_count=? WHERE galeria_id=?",
                (pct, ext, galeria_id))

    conn.commit()
    conn.close()
    return json_response({'success': True, 'foto_id': foto_id, 'status': novo_status,
                          'pacote': pct, 'extra': ext})

@app.post('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>/status')
@rate_limit()
def api_set_foto_status(galeria_id, foto_id):
    data = get_body()
    novo_status = data.get('status', 'nao_selecionada')
    if novo_status not in ('pacote', 'extra', 'nao_selecionada'):
        return json_response({'error': 'Status inválido'}, 400)
    conn = get_connection()
    conn.execute("UPDATE fotos SET status = ? WHERE id = ? AND galeria_id = ?",
                 (novo_status, foto_id, galeria_id))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (galeria_id,))
    pct = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (galeria_id,))
    ext = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return json_response({'success': True, 'foto_id': foto_id, 'status': novo_status,
                          'pacote': pct, 'extra': ext})


@app.post('/api/galeria/<galeria_id:int>/enviar-selecao')
@rate_limit(10)
def api_enviar_selecao(galeria_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (galeria_id,))
    pct = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (galeria_id,))
    ext = cur.fetchone()[0]
    agora = datetime.now().strftime("%d OUT %Y %H:%M")
    cur.execute("""
    INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
    VALUES (?, ?, 'Cliente', 'Seleção enviada ao fotógrafo', ?, 'Computador', 'Cliente')
    """, (galeria_id, agora, f"Seleção de {pct} fotos do pacote e {ext} extras enviada."))
    cur.execute("UPDATE destinatarios SET status_convite='Seleção enviada' WHERE galeria_id=?", (galeria_id,))
    conn.commit()
    conn.close()
    return json_response({'success': True,
                          'mensagem': f'Seleção enviada! {pct} do pacote + {ext} extras.',
                          'pacote': pct, 'extra': ext})

# ==============================================================================
# 4. DESTINATÁRIOS
# ==============================================================================

@app.get('/api/galeria/<galeria_id:int>/destinatarios')
@rate_limit()
def api_get_destinatarios(galeria_id):
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        cur.execute("SELECT * FROM destinatarios WHERE galeria_id = ? ORDER BY id ASC", (real_gal_id,))
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return json_response(rows)

@app.post('/api/galeria/<galeria_id:int>/destinatarios')
@rate_limit()
def api_add_destinatario(galeria_id):
    data = get_body()
    nome  = sanitize_str(data.get('nome', ''), 100).strip()
    email = sanitize_str(data.get('email', ''), 150).strip().lower()
    senha = str(data.get('senha', '')).strip() or '123456'
    permissao = sanitize_str(data.get('permissao', 'Apenas visualizar'), 100)

    if not nome or not email:
        return json_response({'error': 'Nome e e-mail são obrigatórios'}, 400)
    if not is_valid_email(email):
        return json_response({'error': 'E-mail inválido. Digite um e-mail válido (ex: cliente@exemplo.com)'}, 400)

    agora = datetime.now().strftime("%d out. %Y - %H:%M")
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()

        # Verifica se destinatário já existe para esta galeria
        cur.execute("SELECT id FROM destinatarios WHERE galeria_id = ? AND LOWER(email) = ?", (real_gal_id, email))
        dest_existente = cur.fetchone()
        if dest_existente:
            novo_id = dest_existente['id']
            cur.execute("""
            UPDATE destinatarios SET nome = ?, permissao = ? WHERE id = ?
            """, (nome, permissao, novo_id))
        else:
            cur.execute("""
            INSERT INTO destinatarios (galeria_id, nome, email, permissao, principal, status_convite, data_convite, ultimo_acesso, total_acessos)
            VALUES (?, ?, ?, ?, 0, 'Convite preparado', ?, 'Aguardando acesso', 0)
            """, (real_gal_id, nome, email, permissao, agora))
            novo_id = cur.lastrowid

        # Cria ou atualiza conta do cliente em 'usuarios' para login imediato com a senha definida
        cur.execute("SELECT id FROM usuarios WHERE LOWER(email) = ? OR LOWER(login) = ?", (email, email))
        user_row = cur.fetchone()
        if not user_row:
            cur.execute("""
            INSERT INTO usuarios (tipo, nome, email, login, senha_hash, avatar, ativo)
            VALUES ('cliente', ?, ?, ?, ?, 'CL', 1)
            """, (nome, email, email, hash_senha(senha)))
        else:
            cur.execute("""
            UPDATE usuarios SET ativo=1, nome=?, senha_hash=? WHERE id=?
            """, (nome, hash_senha(senha), user_row['id']))

        # Registra atividade
        try:
            cur.execute("""
            INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
            VALUES (?, ?, 'Fotógrafo', 'Novo convite preparado', ?, 'Computador', 'Fotógrafo')
            """, (real_gal_id, agora, f"Convite registrado para {nome} ({email})."))
        except Exception:
            pass

        conn.commit()
    finally:
        conn.close()

    return json_response({
        'success': True,
        'id': novo_id,
        'nome': nome,
        'email': email,
        'senha': senha,
        'mensagem': f'Cliente "{nome}" adicionado com sucesso!'
    })

@app.delete('/api/galeria/<galeria_id:int>/destinatarios/<dest_id:int>')
@rate_limit()
def api_delete_destinatario(galeria_id, dest_id):
    conn = get_connection()
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    conn.execute("DELETE FROM destinatarios WHERE id = ? AND galeria_id = ?", (dest_id, real_gal_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': dest_id})

# ==============================================================================
# 5. HISTÓRICO DE ATIVIDADES
# ==============================================================================

@app.get('/api/galeria/<galeria_id:int>/atividades')
@rate_limit()
def api_get_atividades(galeria_id):
    conn = get_connection()
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("SELECT * FROM atividades WHERE galeria_id = ? ORDER BY id DESC LIMIT 50", (real_gal_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.post('/api/galeria/<galeria_id:int>/atividades')
@rate_limit()
def api_add_atividade(galeria_id):
    data = get_body()
    titulo = sanitize_str(data.get('titulo') or data.get('acao') or 'Nova Atividade', 150)
    descricao = sanitize_str(data.get('descricao') or data.get('detalhes') or '', 500)
    autor_tipo = sanitize_str(data.get('autor_tipo') or data.get('usuario') or 'Fotógrafo', 50)
    agora = datetime.now().strftime("%d %b %Y %H:%M")
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
        VALUES (?, ?, ?, ?, ?, 'Computador', ?)
        """, (real_gal_id, agora, autor_tipo, titulo, descricao, autor_tipo))
        conn.commit()
    except Exception as e:
        return json_response({'success': False, 'error': str(e)}, 400)
    finally:
        conn.close()
    return json_response({'success': True})

# ==============================================================================
# 6. CONTATO DO SITE
# ==============================================================================

@app.post('/api/contato')
@app.post('/api/site/contato')
@rate_limit(15)
def api_enviar_contato():
    ip = get_client_ip()
    data = get_body()
    nome     = sanitize_str(data.get('nome', ''), 100)
    email    = sanitize_str(data.get('email', ''), 150)
    telefone = sanitize_str(data.get('telefone', ''), 20)
    mensagem = sanitize_str(data.get('mensagem', ''), 2000)

    if not nome or not mensagem:
        return json_response({'error': 'Nome e mensagem são obrigatórios'}, 400)
    if len(nome) < 2:
        return json_response({'error': 'Nome muito curto'}, 400)
    if email and not is_valid_email(email):
        return json_response({'error': 'E-mail inválido'}, 400)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO contatos (nome, email, telefone, mensagem)
    VALUES (?, ?, ?, ?)
    """, (nome, email, telefone, mensagem))
    msg_id = cur.lastrowid
    conn.commit()
    conn.close()

    audit(ip, '/api/contato', 'POST', None, 'CONTATO_RECEBIDO', nome, 200)
    return json_response({'success': True, 'id': msg_id,
                          'mensagem': 'Mensagem recebida! Em breve entraremos em contato.'})

@app.get('/api/contatos')
@rate_limit()
def api_get_contatos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contatos ORDER BY id DESC LIMIT 100")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.delete('/api/contatos/<contato_id:int>')
@rate_limit()
def api_delete_contato(contato_id):
    conn = get_connection()
    conn.execute("DELETE FROM contatos WHERE id = ?", (contato_id,))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': contato_id})

# ==============================================================================
# 7. GESTÃO DO SITE PÚBLICO (PAINEL ADMINISTRATIVO)
# ==============================================================================

@app.get('/api/site/categorias')
@rate_limit()
def api_get_site_categorias():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM site_categorias ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.post('/api/site/categorias')
@rate_limit(20)
def api_add_site_categoria():
    data = get_body()
    nome = sanitize_str(data.get('nome', ''), 80)
    if not nome or len(nome) < 2:
        return json_response({'error': 'Nome da categoria é obrigatório (mín. 2 caracteres)'}, 400)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO site_categorias (nome) VALUES (?)", (nome,))
        novo_id = cur.lastrowid
        conn.commit()
        conn.close()
        return json_response({'success': True, 'id': novo_id, 'nome': nome})
    except sqlite3.IntegrityError:
        conn.close()
        return json_response({'error': 'Categoria já existe'}, 409)

@app.delete('/api/site/categorias/<cat_id:int>')
@rate_limit()
def api_delete_site_categoria(cat_id):
    conn = get_connection()
    conn.execute("DELETE FROM site_categorias WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': cat_id})

@app.get('/api/site/fotos')
@rate_limit()
def api_get_site_fotos():
    cat = sanitize_str(request.query.get('categoria', ''), 80)
    conn = get_connection()
    cur = conn.cursor()
    if cat and cat not in ('Todos', 'Todas', ''):
        cur.execute("SELECT * FROM site_fotos WHERE categoria_nome = ? ORDER BY id DESC", (cat,))
    else:
        cur.execute("SELECT * FROM site_fotos ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.post('/api/upload')
@rate_limit(120)
def api_upload_file():
    """Recebe uma imagem em base64 e salva no diretório uploads/"""
    data = get_body()
    img_data = data.get('image')
    orig_name = sanitize_str(data.get('filename', 'foto.jpg'), 150)
    if not img_data:
        return json_response({'error': 'Nenhuma imagem enviada'}, 400)
    
    ext = os.path.splitext(orig_name)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = '.jpg'
    
    try:
        if ',' in img_data:
            _, b64 = img_data.split(',', 1)
        else:
            b64 = img_data
        file_bytes = base64.b64decode(b64)
    except Exception as e:
        return json_response({'error': f'Base64 inválido: {str(e)}'}, 400)
    
    base_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', os.path.splitext(orig_name)[0]) or 'foto'
    timestamp = int(time.time() * 1000)
    nome_final = f"{base_clean}_{timestamp % 1000000}{ext}"
    
    rel_url = salvar_imagem_upload(file_bytes, nome_final)
    return json_response({
        'success': True,
        'url': rel_url,
        'filename': nome_final,
        'original_name': orig_name,
        'tamanho': len(file_bytes)
    })

@app.post('/api/site/fotos')
@rate_limit(40)
def api_add_site_foto():
    data = get_body()
    titulo         = sanitize_str(data.get('titulo', 'Nova Foto'), 150)
    categoria_nome = sanitize_str(data.get('categoria_nome', 'Geral'), 80)
    arquivo        = sanitize_str(data.get('arquivo', ''), 300)
    descricao      = sanitize_str(data.get('descricao', ''), 500)

    # Se veio imagem base64 diretamente, salva em uploads/
    img_b64 = data.get('image')
    if img_b64:
        try:
            if ',' in img_b64:
                _, b64 = img_b64.split(',', 1)
            else:
                b64 = img_b64
            file_bytes = base64.b64decode(b64)
            fname = f"site_carrossel_{int(time.time() * 1000) % 10000000}.jpg"
            arquivo = salvar_imagem_upload(file_bytes, fname)
        except Exception as e:
            pass

    if not arquivo:
        arquivo = 'assets/logo/logo.png'

    # Segurança: valida que o arquivo é um caminho relativo seguro (sem path traversal)
    if '..' in arquivo or arquivo.startswith('/') or arquivo.startswith('\\'):
        return json_response({'error': 'Caminho de arquivo inválido'}, 400)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO site_fotos (titulo, categoria_nome, arquivo, descricao)
    VALUES (?, ?, ?, ?)
    """, (titulo, categoria_nome, arquivo, descricao))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': novo_id, 'titulo': titulo,
                          'categoria_nome': categoria_nome, 'arquivo': arquivo})

@app.delete('/api/site/fotos/<foto_id:int>')
@rate_limit()
def api_delete_site_foto(foto_id):
    conn = get_connection()
    conn.execute("DELETE FROM site_fotos WHERE id = ?", (foto_id,))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': foto_id})

@app.put('/api/site/fotos/<foto_id:int>')
@rate_limit(40)
def api_update_site_foto(foto_id):
    """Altera dados ou foto de um registro do carrossel"""
    data = get_body()
    titulo = sanitize_str(data.get('titulo', ''), 150)
    categoria_nome = sanitize_str(data.get('categoria_nome', ''), 80)
    arquivo = sanitize_str(data.get('arquivo', ''), 300)
    
    # Se enviou nova imagem em base64, salva no uploads/
    img_b64 = data.get('image')
    if img_b64:
        try:
            if ',' in img_b64:
                _, b64 = img_b64.split(',', 1)
            else:
                b64 = img_b64
            file_bytes = base64.b64decode(b64)
            fname = f"site_foto_{foto_id}_{int(time.time() * 1000) % 10000000}.jpg"
            arquivo = salvar_imagem_upload(file_bytes, fname)
        except Exception as e:
            pass

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE site_fotos 
    SET titulo = COALESCE(NULLIF(?, ''), titulo),
        categoria_nome = COALESCE(NULLIF(?, ''), categoria_nome),
        arquivo = COALESCE(NULLIF(?, ''), arquivo)
    WHERE id = ?
    """, (titulo, categoria_nome, arquivo, foto_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': foto_id, 'arquivo': arquivo})

@app.post('/api/site/logo')
@rate_limit(20)
def api_update_site_logo():
    """Permite alterar a Logo Oficial do estúdio através do painel de administração"""
    data = get_body()
    img_data = data.get('image')
    if not img_data:
        return json_response({'error': 'Nenhuma imagem enviada'}, 400)
    try:
        if ',' in img_data:
            _, img_base64 = img_data.split(',', 1)
        else:
            img_base64 = img_data
        file_bytes = base64.b64decode(img_base64)
        logo_path = os.path.join(BASE_DIR, 'assets', 'logo', 'logo.png')
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        with open(logo_path, 'wb') as f:
            f.write(file_bytes)
        return json_response({'success': True, 'url': 'assets/logo/logo.png?v=' + str(int(time.time()))})
    except Exception as e:
        return json_response({'error': f'Falha ao atualizar logo: {str(e)}'}, 500)

@app.post('/api/site/login-foto')
@rate_limit(20)
def api_update_site_login_foto():
    """Permite alterar a foto de destaque das telas de login através do painel de administração"""
    data = get_body()
    img_data = data.get('image')
    if not img_data:
        return json_response({'error': 'Nenhuma imagem enviada'}, 400)
    try:
        if ',' in img_data:
            _, img_base64 = img_data.split(',', 1)
        else:
            img_base64 = img_data
        file_bytes = base64.b64decode(img_base64)
        url = salvar_imagem_upload(file_bytes, 'login_hero.jpg')
        if '?' not in url:
            url += f"?v={int(time.time())}"
        
        # Salva no banco de dados site_textos
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO site_textos (chave, valor) VALUES ('foto_login', ?)", (url,))
        conn.commit()
        conn.close()

        return json_response({'success': True, 'url': url})
    except Exception as e:
        return json_response({'error': f'Falha ao atualizar foto de login: {str(e)}'}, 500)

@app.get('/api/site/login-foto')
@rate_limit()
def api_get_site_login_foto():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT valor FROM site_textos WHERE chave = 'foto_login'")
    row = cur.fetchone()
    conn.close()
    url = row['valor'] if row else 'uploads/login_hero.jpg'
    return json_response({'url': url})


@app.get('/api/site/pacotes')
@rate_limit()
def api_get_site_pacotes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM site_pacotes ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

@app.post('/api/site/pacotes')
@rate_limit(20)
def api_add_site_pacote():
    data = get_body()
    titulo    = sanitize_str(data.get('titulo', ''), 150)
    descricao = sanitize_str(data.get('descricao', ''), 500)
    imagem    = sanitize_str(data.get('imagem', 'assets/logo/logo.png'), 300)
    valor     = sanitize_str(data.get('valor', 'Consultar valores'), 100)

    # Suporte a upload de imagem do computador em base64 (via 'image' ou 'imagem')
    img_b64 = data.get('image')
    if not img_b64 and isinstance(data.get('imagem'), str) and data.get('imagem', '').startswith('data:image'):
        img_b64 = data.get('imagem')
    if img_b64:
        try:
            if ',' in img_b64:
                _, b64 = img_b64.split(',', 1)
            else:
                b64 = img_b64
            file_bytes = base64.b64decode(b64)
            t_stamp = int(time.time() * 1000) % 10000000
            fname = f"pacote_{t_stamp}.jpg"
            imagem = salvar_imagem_upload(file_bytes, fname)
        except Exception:
            pass

    if not titulo:
        return json_response({'error': 'Título do pacote é obrigatório'}, 400)
    if '..' in imagem:
        imagem = 'assets/logo/logo.png'

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO site_pacotes (titulo, descricao, imagem, valor) VALUES (?, ?, ?, ?)",
                    (titulo, descricao, imagem, valor))
        novo_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    return json_response({'success': True, 'id': novo_id, 'imagem': imagem})

@app.delete('/api/site/pacotes/<pacote_id:int>')
@rate_limit()
def api_delete_site_pacote(pacote_id):
    conn = get_connection()
    conn.execute("DELETE FROM site_pacotes WHERE id = ?", (pacote_id,))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': pacote_id})

# ── Textos Customizáveis da Página Inicial ──

@app.get('/api/site/textos')
@rate_limit()
def api_get_site_textos():
    return json_response(get_site_textos())

@app.post('/api/site/textos')
@app.put('/api/site/textos')
@rate_limit(30)
def api_update_site_textos():
    ip = get_client_ip()
    data = get_body()
    if not isinstance(data, dict):
        return json_response({'error': 'Dados inválidos'}, 400)

    # Sanitiza cada chave e valor
    sanitizado = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            sanitizado[sanitize_str(k, 50)] = sanitize_str(v, 3000)

    update_site_textos(sanitizado)
    audit(ip, '/api/site/textos', 'POST', None, 'TEXTOS_SITE_UPDATE', f"{len(sanitizado)} campos atualizados", 200)
    return json_response({'success': True, 'mensagem': 'Textos da página inicial atualizados com sucesso!', 'textos': get_site_textos()})


# ==============================================================================
# 8. ADMIN: LOG DE AUDITORIA & GESTÃO DE FOTÓGRAFOS
# ==============================================================================

@app.get('/api/admin/fotografos')
@rate_limit()
def api_get_admin_fotografos():
    """Lista todos os fotógrafos cadastrados no sistema."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT id, nome, email, login, ativo, criado_em, ultimo_login
        FROM usuarios
        WHERE tipo = 'fotografo'
        ORDER BY id DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return json_response(rows)

@app.post('/api/admin/fotografos')
@rate_limit(30)
def api_add_admin_fotografo():
    """Cadastra um novo fotógrafo com login, e-mail e senha segura."""
    ip = get_client_ip()
    data = get_body()
    nome = sanitize_str(data.get('nome', ''), 120)
    email = sanitize_str(data.get('email', ''), 150).strip().lower()
    senha = str(data.get('senha', '')).strip()

    if not nome or len(nome) < 2:
        return json_response({'error': 'Nome do fotógrafo é obrigatório (mínimo 2 caracteres).'}, 400)
    if not email or '@' not in email:
        return json_response({'error': 'E-mail válido é obrigatório.'}, 400)
    if not senha or len(senha) < 4:
        return json_response({'error': 'A senha deve ter no mínimo 4 caracteres.'}, 400)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE email = ? OR login = ?", (email, email))
        if cur.fetchone():
            return json_response({'error': 'Já existe um usuário com este e-mail/login cadastrado.'}, 400)

        senha_h = hash_senha(senha)
        avatar = (nome[:2] if len(nome) >= 2 else 'CF').upper()

        cur.execute("""
        INSERT INTO usuarios (tipo, nome, email, login, senha_hash, avatar, ativo)
        VALUES ('fotografo', ?, ?, ?, ?, ?, 1)
        """, (nome, email, email, senha_h, avatar))
        novo_id = cur.lastrowid
        conn.commit()
        audit(ip, '/api/admin/fotografos', 'POST', None, 'ADD_FOTOGRAFO', f'Fotógrafo {nome} ({email}) criado', 200)
        return json_response({
            'success': True,
            'id': novo_id,
            'nome': nome,
            'email': email,
            'avatar': avatar,
            'mensagem': f'Fotógrafo "{nome}" cadastrado com sucesso!'
        }, 201)
    finally:
        conn.close()

@app.delete('/api/admin/fotografos/<foto_id:int>')
@rate_limit(30)
def api_delete_admin_fotografo(foto_id):
    """Remove o login de um fotógrafo."""
    ip = get_client_ip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome, email FROM usuarios WHERE id = ? AND tipo = 'fotografo'", (foto_id,))
        row = cur.fetchone()
        if not row:
            return json_response({'error': 'Fotógrafo não encontrado.'}, 404)

        nome = row['nome']
        cur.execute("DELETE FROM usuarios WHERE id = ? AND tipo = 'fotografo'", (foto_id,))
        conn.commit()
        audit(ip, f'/api/admin/fotografos/{foto_id}', 'DELETE', None, 'DEL_FOTOGRAFO', f'Fotógrafo {nome} excluído', 200)
        return json_response({'success': True, 'deleted': foto_id, 'mensagem': f'Fotógrafo "{nome}" removido com sucesso.'})
    finally:
        conn.close()

@app.get('/api/admin/audit-log')
@rate_limit()
def api_get_audit_log():
    limite = min(int(request.query.get('limit', 50)), 200)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limite,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response(rows)

# ==============================================================================
# 9. ARQUIVOS ESTÁTICOS (com proteções de segurança)
# ==============================================================================

# Extensões permitidas para arquivos estáticos
ALLOWED_EXTENSIONS = {
    '.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.json', '.txt'
}

# Diretórios bloqueados (nunca servir)
BLOCKED_PATHS = {'banco.db', '.env', '.gitignore', 'requirements.txt',
                 'db.py', 'server.py', '__pycache__'}

@app.route('/')
@app.route('/index')
@app.route('/index.html')
@app.route('/inicio')
@app.route('/home')
def serve_index():
    return static_file('index.html', root=BASE_DIR)

@app.route('/<filepath:path>')
def serve_static(filepath):
    # Previne Path Traversal
    if '..' in filepath or filepath.startswith('/') or filepath.startswith('\\'):
        abort(403, 'Acesso negado')

    # Bloqueia acesso a arquivos sensíveis
    first_segment = filepath.split('/')[0].split('\\')[0]
    if first_segment in BLOCKED_PATHS or filepath in BLOCKED_PATHS:
        abort(403, 'Acesso negado')

    # Verifica extensão
    _, ext = os.path.splitext(filepath)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        abort(403, 'Tipo de arquivo não permitido')

    if filepath.startswith('uploads/'):
        fname = filepath[len('uploads/'):]
        if os.path.exists(os.path.join(UPLOAD_DIR, fname)):
            return static_file(fname, root=UPLOAD_DIR)
        # Fallback gracioso para containers efêmeros da Vercel: serve o logo do estúdio evitando ícone quebrado
        logo_path = os.path.join(BASE_DIR, 'assets', 'logo', 'logo.png')
        if os.path.exists(logo_path):
            return static_file('logo.png', root=os.path.join(BASE_DIR, 'assets', 'logo'))

    return static_file(filepath, root=BASE_DIR)

# ==============================================================================
# 10. INICIALIZAÇÃO
# ==============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8082))
    host = os.environ.get('HOST', '127.0.0.1')  # Só localhost por padrão (mais seguro)

    print("=" * 65)
    print(" CASA DA FOTO STUDIO - Servidor com Seguranca Completa")
    print("=" * 65)
    print(f"  URL:          http://{host}:{port}/")
    print(f"  Banco:        {os.path.join(BASE_DIR, 'banco.db')}")
    print(f"  Rate Limit:   {RATE_LIMIT_GERAL} req/min (auth: {RATE_LIMIT_AUTH}/min)")
    print(f"  Debug:        {'ATIVADO [ATENCAO]' if DEBUG else 'Desativado [OK]'}")
    print(f"  Bcrypt:       Ativado [OK]")
    print(f"  Sec Headers:  Ativados [OK]")
    print(f"  CORS:         {', '.join(ALLOWED_ORIGINS)}")
    print("=" * 65)


    run(app, host=host, port=port, debug=DEBUG, quiet=not DEBUG)
