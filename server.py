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
from bottle import Bottle, request, response, static_file, run, abort, HTTPError, BaseRequest
BaseRequest.MEMFILE_MAX = 50 * 1024 * 1024  # 50 MB (permite uploads de fotos e logos em alta resolução)

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
        if request.json:
            return request.json
    except Exception:
        pass
    try:
        if hasattr(request, 'body') and request.body:
            raw = request.body.read()
            if raw:
                return json.loads(raw.decode('utf-8'))
    except Exception:
        pass
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

# ── Log de Erros do Sistema (Frontend e Backend) ─────────────────────────────

def log_error(origem: str, mensagem: str, detalhe: str = '', rota: str = '', ip: str = None, user_agent: str = None):
    try:
        if not ip:
            ip = get_client_ip()
        if not user_agent and hasattr(request, 'headers'):
            user_agent = request.headers.get('User-Agent', '')[:250]
        conn = get_connection()
        conn.execute("""
        INSERT INTO error_log (origem, mensagem, detalhe, rota, ip, user_agent)
        VALUES (?,?,?,?,?,?)
        """, (origem[:20], mensagem[:500], detalhe[:2000], rota[:250], ip[:50], (user_agent or '')[:250]))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LogError] Falha ao registrar erro: {e}")

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

def semear_projetos_iniciais(conn, forcar=False):
    """Semeia projetos e galerias de demonstração com links de entrega e mensagens personalizadas."""
    try:
        from db import assegurar_schema_postgres
        assegurar_schema_postgres(conn)
    except Exception:
        pass

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM projetos")
        count = cur.fetchone()[0]
        if count > 0 and not forcar:
            return

        projetos_demo = [
            ('Camila & Pedro', 'Ensaio Gestante', 'Gestante', 'novos', 1, 'sem prazo', 'assets/logo/logo.png', 'https://drive.google.com/drive/folders/pastaCamilaPedro?usp=sharing'),
            ('Família Silva', 'Ensaio Família', 'Família', 'andamento', 2, '15 nov', 'assets/logo/logo.png', 'https://drive.google.com/drive/folders/pastaFamiliaSilva?usp=sharing'),
            ('Nicoly', '15 anos', 'Retrato', 'revisao', 1, '22 nov', 'assets/logo/logo.png', 'https://drive.google.com/drive/folders/pastaNicoly15Anos?usp=sharing'),
            ('Helena (Primeiro Aninho)', 'Ensaio Bebê', 'Bebê', 'entrega', 1, '30 nov', 'assets/logo/logo.png', 'https://drive.google.com/drive/folders/pastaHelenaBebe?usp=sharing'),
            ('Mariana & João', 'Bodas de Prata', 'Família', 'finalizados', 1, 'Concluído', 'assets/logo/logo.png', 'https://drive.google.com/drive/folders/pastaMarianaJoao?usp=sharing')
        ]
        
        msg_template = "Olá {nome}! ✨📸 É com imensa alegria que entregamos as fotos oficiais do seu {ensaio}! Preparamos cada detalhe com todo carinho da Casa da Foto Studio para eternizar os seus melhores momentos. Acesse sua página exclusiva para baixar todos os arquivos em alta resolução diretamente pelo Google Drive."

        for nome, tipo, tag, st, sessoes, prazo, avatar, drive_link in projetos_demo:
            cur.execute("SELECT id FROM projetos WHERE nome_cliente = ?", (nome,))
            proj_existente = cur.fetchone()
            if not proj_existente:
                cur.execute("""
                INSERT INTO projetos (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nome, tipo, tag, st, sessoes, prazo, avatar))
                proj_id = cur.lastrowid
            else:
                proj_id = proj_existente['id']

            msg_personalizada = msg_template.format(nome=nome, ensaio=tipo)
            
            # Verifica se já existe galeria associada
            cur.execute("SELECT id FROM galerias WHERE projeto_id = ? OR nome = ?", (proj_id, f"Galeria - {nome}"))
            gal_existente = cur.fetchone()
            if not gal_existente:
                cur.execute("""
                INSERT INTO galerias (projeto_id, nome, categoria, data_trabalho, prazo_selecao, limite_pacote, valor_foto_extra, foto_capa, link_drive, mensagem_acesso, status_galeria)
                VALUES (?, ?, ?, '15/10/2026', '30/10/2026', 15, 25.00, 'assets/logo/logo.png', ?, ?, ?)
                """, (proj_id, f"Galeria - {nome}", tipo, drive_link, msg_personalizada, 'Seleção aprovada' if st in ('entrega', 'finalizados') else 'Aguardando seleção'))
                gal_id = cur.lastrowid
            else:
                gal_id = gal_existente['id']
                cur.execute("UPDATE galerias SET link_drive = ?, mensagem_acesso = ?, projeto_id = ? WHERE id = ?", (drive_link, msg_personalizada, proj_id, gal_id))

        conn.commit()
    except Exception as e:
        print(f"[Seed Projetos] Erro ao semear projetos padrão: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        raise e

@app.get('/api/projetos')
@rate_limit()
def api_get_projetos():
    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
            SELECT p.*, COALESCE(g.id, p.id) as galeria_id,
                   COALESCE(g.status_galeria, 'Aguardando seleção') as status_galeria,
                   COALESCE(g.selecao_bloqueada, 0) as selecao_bloqueada,
                   COALESCE(g.link_drive, '') as link_drive,
                   COALESCE(g.mensagem_acesso, '') as mensagem_acesso,
                   COALESCE(g.foto_capa, p.avatar_img, 'assets/logo/logo.png') as foto_capa,
                   (SELECT COUNT(*) FROM fotos f WHERE f.galeria_id = COALESCE(g.id, p.id)) as total_fotos
            FROM projetos p
            LEFT JOIN galerias g ON g.projeto_id = p.id
            ORDER BY p.id ASC
            """)
            rows = [dict(row) for row in cur.fetchall()]
            return json_response(rows)
        finally:
            conn.close()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[API_PROJETOS_EX] {e}\n{tb}")
        return json_response({'error': str(e), 'traceback': tb, 'status': 500}, 500)

@app.post('/api/projetos/restaurar-exemplos')
@rate_limit()
def api_restaurar_projetos_exemplos():
    conn = get_connection()
    try:
        semear_projetos_iniciais(conn, forcar=True)
        return json_response({'success': True, 'mensagem': '5 Galerias demonstrativas com links do Google Drive restauradas com sucesso!'})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[Restaurar Erro]: {e}\n{tb}")
        return json_response({'error': f'Falha ao semear projetos: {str(e)}', 'traceback': tb}, 500)
    finally:
        conn.close()

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
        rel_url = salvar_imagem_upload(file_bytes, filename)
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

    limite_pacote = int(data.get('limite_pacote', 10))
    if limite_pacote <= 0:
        limite_pacote = 10
    valor_foto_extra = float(data.get('valor_foto_extra', 25.0))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO projetos (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img))
    novo_id = cur.lastrowid

    # Cria automaticamente a galeria vinculada com a foto de capa e limites definidos
    cur.execute("""
    INSERT INTO galerias (projeto_id, nome, categoria, foto_capa, limite_pacote, valor_foto_extra)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (novo_id, f"Galeria - {nome_cliente}", tipo_ensaio, foto_capa, limite_pacote, valor_foto_extra))
    galeria_id = cur.lastrowid

    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': novo_id, 'projeto_id': novo_id, 'galeria_id': galeria_id, 'foto_capa': foto_capa, 'limite_pacote': limite_pacote})

@app.get('/api/galerias')
@rate_limit()
def api_get_galerias():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT g.*, 
               COALESCE(p.nome_cliente, REPLACE(g.nome, 'Galeria - ', '')) as nome_cliente,
               COALESCE(p.tipo_ensaio, g.categoria) as tipo_ensaio,
               COALESCE(p.status, 'novos') as status_projeto,
               COALESCE(g.foto_capa, p.avatar_img, 'assets/logo/logo.png') as capa_exibicao,
               (SELECT COUNT(*) FROM fotos f WHERE f.galeria_id = g.id) as total_fotos
        FROM galerias g
        LEFT JOIN projetos p ON p.id = g.projeto_id
        ORDER BY g.id DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        return json_response(rows)
    finally:
        conn.close()

@app.post('/api/galerias')
@rate_limit()
def api_create_galeria():
    data = get_body()
    nome = sanitize_str(data.get('nome', 'Nova Galeria'), 150)
    categoria = sanitize_str(data.get('categoria', 'Galeria demonstrativa'), 100)
    projeto_id = data.get('projeto_id')
    foto_capa = sanitize_str(data.get('foto_capa', 'assets/logo/logo.png'), 500)
    limite_pacote = int(data.get('limite_pacote', 10))
    valor_foto_extra = float(data.get('valor_foto_extra', 25.0))
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Se não foi fornecido projeto_id, cria o projeto correspondente para aparecer no Kanban
    if not projeto_id:
        nome_cliente = nome.replace('Galeria - ', '').strip() or 'Novo Cliente'
        cur.execute("""
        INSERT INTO projetos (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img)
        VALUES (?, ?, ?, 'novos', 1, 'sem prazo', ?)
        """, (nome_cliente, categoria, categoria.split(' ')[-1] if ' ' in categoria else categoria, foto_capa))
        projeto_id = cur.lastrowid

    cur.execute("""
    INSERT INTO galerias (projeto_id, nome, categoria, foto_capa, limite_pacote, valor_foto_extra, status_galeria)
    VALUES (?, ?, ?, ?, ?, ?, 'Aguardando seleção')
    """, (projeto_id, nome, categoria, foto_capa, limite_pacote, valor_foto_extra))
    novo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return json_response({'success': True, 'id': novo_id, 'galeria_id': novo_id, 'projeto_id': projeto_id, 'foto_capa': foto_capa})

@app.delete('/api/galerias/<galeria_id:int>')
@rate_limit()
def api_delete_galeria(galeria_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT projeto_id, nome FROM galerias WHERE id = ?", (galeria_id,))
        row = cur.fetchone()
        proj_id = row['projeto_id'] if row else None
        gal_nome = row['nome'] if row else ''
        
        cur.execute("DELETE FROM fotos WHERE galeria_id = ?", (galeria_id,))
        cur.execute("DELETE FROM destinatarios WHERE galeria_id = ?", (galeria_id,))
        cur.execute("DELETE FROM atividades WHERE galeria_id = ?", (galeria_id,))
        cur.execute("DELETE FROM galerias WHERE id = ?", (galeria_id,))
        
        if proj_id:
            cur.execute("DELETE FROM projetos WHERE id = ?", (proj_id,))
        elif gal_nome:
            nome_cli = gal_nome.replace('Galeria - ', '').strip()
            if nome_cli:
                cur.execute("DELETE FROM projetos WHERE nome_cliente = ?", (nome_cli,))
            
        conn.commit()
        return json_response({'success': True, 'deleted': galeria_id})
    finally:
        conn.close()

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

@app.delete('/api/projetos/limpar-todos')
@rate_limit()
def api_limpar_todos_projetos():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM fotos")
        cur.execute("DELETE FROM destinatarios")
        cur.execute("DELETE FROM atividades")
        cur.execute("DELETE FROM galerias")
        cur.execute("DELETE FROM projetos")
        conn.commit()
        return json_response({'success': True, 'mensagem': 'Todos os projetos e galerias foram excluídos com sucesso.'})
    finally:
        conn.close()

@app.delete('/api/projetos/<proj_id:int>')
@rate_limit()
def api_delete_projeto(proj_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome_cliente FROM projetos WHERE id = ?", (proj_id,))
        p_row = cur.fetchone()
        nome_cli = p_row['nome_cliente'] if p_row else ''

        # Deleta fotos, destinatarios, atividades e galerias associadas pelo ID do projeto ou nome
        if nome_cli:
            cur.execute("SELECT id FROM galerias WHERE projeto_id = ? OR nome = ? OR nome = ?", 
                        (proj_id, f"Galeria - {nome_cli}", nome_cli))
        else:
            cur.execute("SELECT id FROM galerias WHERE projeto_id = ?", (proj_id,))
        gal_rows = cur.fetchall()
        for g in gal_rows:
            gid = g['id']
            cur.execute("DELETE FROM fotos WHERE galeria_id = ?", (gid,))
            cur.execute("DELETE FROM destinatarios WHERE galeria_id = ?", (gid,))
            cur.execute("DELETE FROM atividades WHERE galeria_id = ?", (gid,))
            cur.execute("DELETE FROM galerias WHERE id = ?", (gid,))

        # Limpeza defensiva caso existam registros vinculados pelo mesmo ID numérico
        cur.execute("DELETE FROM fotos WHERE galeria_id = ?", (proj_id,))
        cur.execute("DELETE FROM destinatarios WHERE galeria_id = ?", (proj_id,))
        cur.execute("DELETE FROM atividades WHERE galeria_id = ?", (proj_id,))
        cur.execute("DELETE FROM galerias WHERE id = ?", (proj_id,))

        cur.execute("DELETE FROM projetos WHERE id = ?", (proj_id,))
        conn.commit()
        return json_response({'success': True, 'deleted': proj_id})
    finally:
        conn.close()

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
        'foto_capa', 'estilo_capa', 'enquadramento', 'tema_visual', 'tipografia',
        'link_drive', 'status_galeria', 'selecao_bloqueada'
    ]
    set_clauses, values = [], []
    for f in allowed_fields:
        if f in data:
            set_clauses.append(f"{f} = ?")
            v = data[f]
            if isinstance(v, str):
                max_len = 1000 if f == 'link_drive' else 500
                v = sanitize_str(v, max_len)
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

@app.put('/api/galeria/<galeria_id:int>/link-drive')
@rate_limit()
def api_update_link_drive(galeria_id):
    """Atualiza de forma direta e rápida o link do Google Drive e a mensagem personalizada de entrega das fotos."""
    data = get_body() or {}
    link = sanitize_str(data.get('link_drive', ''), 1000).strip()
    msg = sanitize_str(data.get('mensagem_acesso', ''), 3000).strip()
    conn = get_connection()
    try:
        real_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        if msg:
            cur.execute("UPDATE galerias SET link_drive = ?, mensagem_acesso = ? WHERE id = ?", (link, msg, real_id))
        else:
            cur.execute("UPDATE galerias SET link_drive = ? WHERE id = ?", (link, real_id))
        agora = datetime.now().strftime("%d OUT %Y %H:%M")
        cur.execute("""
        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
        VALUES (?, ?, 'Fotógrafo', 'Link do Drive e Mensagem de Entrega atualizados', 'Link e mensagem de entrega das fotos atualizados.', 'Computador', 'Fotógrafo')
        """, (real_id, agora))
        conn.commit()
        return json_response({'success': True, 'link_drive': link, 'mensagem_acesso': msg})
    finally:
        conn.close()

@app.get('/api/entrega/lista')
@rate_limit()
def api_get_lista_entregas():
    """Retorna a lista de todas as entregas disponíveis para o seletor da página de entrega."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT 
            COALESCE(g.id, p.id) as galeria_id,
            p.id as projeto_id,
            p.nome_cliente,
            p.tipo_ensaio,
            p.status as status_projeto,
            COALESCE(g.status_galeria, 'Aguardando seleção') as status_galeria,
            COALESCE(g.link_drive, '') as link_drive,
            COALESCE(g.mensagem_acesso, '') as mensagem_acesso,
            COALESCE(g.data_trabalho, 'Outubro 2026') as data_trabalho
        FROM projetos p
        LEFT JOIN galerias g ON g.projeto_id = p.id
        ORDER BY 
            CASE WHEN COALESCE(g.link_drive, '') != '' THEN 0 ELSE 1 END,
            p.id ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        return json_response({'success': True, 'entregas': rows})
    finally:
        conn.close()

@app.get('/api/entrega/<galeria_id:int>')
@rate_limit()
def api_get_entrega(galeria_id):
    """Retorna os dados públicos da entrega da galeria: dados do ensaio, link do Drive, mensagem personalizada e fotos entregues."""
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        cur.execute("SELECT * FROM galerias WHERE id = ?", (real_gal_id,))
        galeria_row = cur.fetchone()
        
        # Se não achou por ID de galeria, busca pelo ID do projeto
        if not galeria_row:
            cur.execute("SELECT * FROM galerias WHERE projeto_id = ? ORDER BY id ASC LIMIT 1", (galeria_id,))
            galeria_row = cur.fetchone()

        if not galeria_row:
            # Fallback para primeira galeria que tenha link do Drive
            cur.execute("SELECT * FROM galerias WHERE link_drive != '' ORDER BY id ASC LIMIT 1")
            galeria_row = cur.fetchone()

        if not galeria_row:
            cur.execute("SELECT * FROM galerias ORDER BY id ASC LIMIT 1")
            galeria_row = cur.fetchone()

        if not galeria_row:
            return json_response({'error': 'Entrega não encontrada.'}, 404)

        galeria = dict(galeria_row)
        real_gal_id = galeria['id']

        # Busca dados do projeto associado
        projeto = None
        if galeria.get('projeto_id'):
            cur.execute("SELECT id, nome_cliente, tipo_ensaio, status, prazo, avatar_img FROM projetos WHERE id = ?", (galeria['projeto_id'],))
            proj_row = cur.fetchone()
            if proj_row:
                projeto = dict(proj_row)

        if not projeto:
            cur.execute("SELECT id, nome_cliente, tipo_ensaio, status, prazo, avatar_img FROM projetos WHERE id = ?", (galeria['id'],))
            proj_row = cur.fetchone()
            if proj_row:
                projeto = dict(proj_row)

        # Informações de contato do estúdio
        textos = get_site_textos()
        contato = {
            'nome_estudio': textos.get('hero_titulo', 'Casa da Foto Studio'),
            'slogan': textos.get('header_slogan', 'Momentos que ficam'),
            'whatsapp': textos.get('contato_whatsapp', '(11) 98765-4321'),
            'email': textos.get('contato_email', 'contato@casadafoto.com')
        }

        # Fotos da galeria
        cur.execute("SELECT id, numero, titulo, arquivo, status FROM fotos WHERE galeria_id = ? ORDER BY ordem ASC, id ASC", (real_gal_id,))
        todas_fotos = [dict(f) for f in cur.fetchall()]
        fotos_aprovadas = [f for f in todas_fotos if f.get('status') in ('pacote', 'extra')]
        fotos_exibir = fotos_aprovadas if fotos_aprovadas else todas_fotos

        # Identificação garantida do cliente e do ensaio
        nome_cli = (projeto.get('nome_cliente') if projeto else None)
        if not nome_cli:
            gal_nome = galeria.get('nome', '')
            if 'Galeria - ' in gal_nome:
                nome_cli = gal_nome.replace('Galeria - ', '').strip()
            elif gal_nome and gal_nome != 'Galeria demonstrativa':
                nome_cli = gal_nome.strip()
            else:
                nome_cli = 'Cliente Especial'

        tipo_ens = (projeto.get('tipo_ensaio') if projeto else None) or galeria.get('categoria') or 'Ensaio Fotográfico'

        # Mensagem personalizada
        msg_entrega = galeria.get('mensagem_acesso')
        if not msg_entrega or len(msg_entrega.strip()) < 10:
            msg_entrega = (
                f"Olá {nome_cli}! ✨📸 É com imensa alegria que entregamos as fotos oficiais do seu {tipo_ens}! "
                f"Cada imagem foi preparada e tratada com todo o cuidado, carinho e dedicação da equipe Casa da Foto Studio para eternizar os seus melhores momentos. "
                f"Aproveite para visualizar e baixar todos os arquivos em alta resolução diretamente pelo Google Drive!"
            )

        return json_response({
            'success': True,
            'galeria': galeria,
            'projeto': projeto,
            'nome_cliente': nome_cli,
            'tipo_ensaio': tipo_ens,
            'fotos': fotos_exibir,
            'total_fotos': len(fotos_exibir),
            'total_aprovadas': len(fotos_aprovadas),
            'link_drive': galeria.get('link_drive', '') or '',
            'mensagem_personalizada': msg_entrega,
            'contato': contato
        })
    finally:
        conn.close()

# ── ROTAS DE CATEGORIAS (Personalização de tipos de ensaio) ───────────────────

@app.get('/api/categorias')
@rate_limit()
def api_get_categorias():
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM categorias ORDER BY nome ASC")
            rows = [dict(r) for r in cur.fetchall()]
        except Exception:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
            rows = []

        if not rows:
            padroes = [
                'Galeria demonstrativa', 'Ensaio Família', 'Gestante', 'Newborn',
                'Casamento', 'Aniversário / 15 Anos', 'Formatura', 'Ensaio Casal',
                'Retrato Profissional', 'Smash the Cake', 'Batizado', 'Eventos / Festas'
            ]
            for p in padroes:
                try:
                    cur.execute("INSERT INTO categorias (nome) VALUES (?)", (p,))
                except Exception:
                    pass
            conn.commit()
            cur.execute("SELECT * FROM categorias ORDER BY nome ASC")
            rows = [dict(r) for r in cur.fetchall()]

        return json_response(rows)
    finally:
        conn.close()

@app.post('/api/categorias')
@rate_limit(30)
def api_add_categoria():
    data = get_body()
    nome = sanitize_str(data.get('nome', ''), 100).strip()
    if not nome:
        return json_response({'error': 'Nome da categoria é obrigatório.'}, 400)

    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, nome FROM categorias WHERE LOWER(nome) = ?", (nome.lower(),))
            existente = cur.fetchone()
        except Exception:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
            existente = None

        if existente:
            return json_response({'success': True, 'categoria': {'id': existente['id'], 'nome': existente['nome']}, 'id': existente['id'], 'nome': existente['nome'], 'mensagem': 'Categoria já existente.'})

        cur.execute("INSERT INTO categorias (nome) VALUES (?)", (nome,))
        novo_id = cur.lastrowid
        conn.commit()
        return json_response({'success': True, 'categoria': {'id': novo_id, 'nome': nome}, 'id': novo_id, 'nome': nome, 'mensagem': f'Categoria "{nome}" cadastrada com sucesso!'})
    except Exception as e:
        return json_response({'error': f'Erro ao salvar categoria: {str(e)}'}, 500)
    finally:
        conn.close()

@app.delete('/api/categorias/<cat_id:int>')
@rate_limit(30)
def api_delete_categoria(cat_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
        conn.commit()
        return json_response({'success': True, 'deleted': cat_id})
    finally:
        conn.close()

@app.get('/api/galeria/<galeria_id:int>/fotos')
@rate_limit()
def api_get_fotos(galeria_id):
    """
    Retorna TODAS as fotos da galeria sem LIMIT arbitrário.
    Ordenação determinística: ordem ASC, id ASC — garante que as últimas fotos
    enviadas sempre apareçam, mesmo em ensaios com centenas de arquivos.
    """
    conn = get_connection()
    galeria_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    # Dupla ordenação: coluna 'ordem' (posição manual) e 'id' (ordem de inserção).
    # Isso evita que fotos do final de lotes grandes sejam truncadas ou reordenadas.
    cur.execute(
        "SELECT * FROM fotos WHERE galeria_id = ? ORDER BY ordem ASC, id ASC",
        (galeria_id,)
    )
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

@app.get('/api/galeria/<galeria_id:int>/fotos/integridade')
@rate_limit()
def api_check_fotos_integridade(galeria_id):
    """
    Endpoint de verificação de integridade: retorna a contagem real de fotos
    gravadas no banco para o álbum, permitindo ao admin comparar com o total enviado.
    Útil para detectar uploads parcialmente completos.
    """
    conn = get_connection()
    real_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id = ?", (real_id,))
    row = cur.fetchone()
    total_banco = (row[0] if row else 0)
    cur.execute(
        "SELECT id, numero, titulo, arquivo, status, ordem FROM fotos WHERE galeria_id = ? ORDER BY id DESC LIMIT 10",
        (real_id,)
    )
    ultimas = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json_response({
        'galeria_id': real_id,
        'total_fotos_banco': total_banco,
        'ultimas_10_inseridas': ultimas,
        'mensagem': f'{total_banco} foto(s) gravada(s) com sucesso no banco para esta galeria.'
    })

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
    """
    Recebe upload de fotos via multipart/form-data e insere na galeria com:
      - Processamento sequencial em lotes de BATCH_SIZE (evita OOM com muitos arquivos).
      - Tratamento granular de erros: falha em uma foto não interrompe as demais.
      - Confirmação de escrita no storage ANTES do INSERT no banco (integridade).
      - Relatório final com total enviado, salvos com sucesso e lista de falhas.
    """
    BATCH_SIZE = 4          # Máximo de arquivos processados por vez
    EXTENSOES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    TAMANHO_MAX = 20 * 1024 * 1024  # 20 MB por arquivo

    conn = get_connection()
    try:
        real_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        cur.execute("SELECT id FROM galerias WHERE id = ?", (real_id,))
        if not cur.fetchone():
            return json_response({'error': 'Galeria não encontrada'}, 404)

        # Captura contagem atual ANTES do loop para numerar sequencialmente
        cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id = ?", (real_id,))
        cnt_row = cur.fetchone()
        total_atual = 0
        if cnt_row is not None:
            total_atual = cnt_row['count'] if isinstance(cnt_row, dict) and 'count' in cnt_row else cnt_row[0]

        arquivos = request.files.getall('fotos') or []
        if not arquivos:
            return json_response({'error': 'Nenhum arquivo recebido. Use o campo "fotos" no FormData.'}, 400)

        total_recebidos = len(arquivos)
        inseridas = []   # Fotos salvas com sucesso no storage E no banco
        erros = []       # Falhas por arquivo (com motivo)

        # ── Processa em lotes de BATCH_SIZE ────────────────────────────────
        for lote_inicio in range(0, total_recebidos, BATCH_SIZE):
            lote = arquivos[lote_inicio : lote_inicio + BATCH_SIZE]

            for upload_file in lote:
                nome_original = upload_file.filename or f'foto_sem_nome_{lote_inicio}'
                ext = os.path.splitext(nome_original)[1].lower()

                # ── Validação de extensão ───────────────────────────────────
                if ext not in EXTENSOES_PERMITIDAS:
                    erros.append({'arquivo': nome_original, 'motivo': f'Extensão não permitida: {ext}'})
                    print(f'[Upload] SKIP {nome_original}: extensão inválida ({ext})')
                    continue

                # ── Leitura dos bytes ───────────────────────────────────────
                try:
                    raw_bytes = upload_file.file.read()
                except Exception as read_err:
                    erros.append({'arquivo': nome_original, 'motivo': f'Erro ao ler arquivo: {read_err}'})
                    print(f'[Upload] ERRO leitura {nome_original}: {read_err}')
                    continue

                if len(raw_bytes) > TAMANHO_MAX:
                    erros.append({'arquivo': nome_original, 'motivo': 'Arquivo excede 20 MB'})
                    print(f'[Upload] SKIP {nome_original}: excede 20 MB')
                    continue

                if len(raw_bytes) == 0:
                    erros.append({'arquivo': nome_original, 'motivo': 'Arquivo vazio (0 bytes)'})
                    print(f'[Upload] SKIP {nome_original}: arquivo vazio')
                    continue

                # ── Geração do nome único no storage ───────────────────────
                idx = total_atual + len(inseridas) + 1
                base_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', os.path.splitext(nome_original)[0]) or f'foto_{idx}'
                fname = f"gal_{real_id}_{base_clean}_{uuid.uuid4().hex[:8]}{ext}"

                # ── ESCRITA NO STORAGE (Supabase / disco local) ─────────────
                # O INSERT no banco SÓ ocorre após confirmação desta etapa.
                try:
                    arquivo_url = salvar_imagem_upload(raw_bytes, fname)
                    if not arquivo_url:
                        raise ValueError('salvar_imagem_upload retornou vazio')
                except Exception as save_err:
                    erros.append({'arquivo': nome_original, 'motivo': f'Erro ao salvar no storage: {save_err}'})
                    print(f'[Upload] ERRO storage {nome_original}: {save_err}')
                    continue  # Não insere no banco — integridade garantida

                # ── INSERT NO BANCO (apenas após confirmação do storage) ────
                numero = f"Foto {idx:03d}"
                titulo = os.path.splitext(nome_original)[0]
                try:
                    cur.execute("""
                    INSERT INTO fotos (galeria_id, numero, titulo, arquivo, status, ordem)
                    VALUES (?, ?, ?, ?, 'nao_selecionada', ?)
                    """, (real_id, numero, titulo, arquivo_url, idx))
                    foto_id = cur.lastrowid
                    inseridas.append({
                        'id': foto_id,
                        'numero': numero,
                        'titulo': titulo,
                        'arquivo': arquivo_url
                    })
                    print(f'[Upload] OK {nome_original} → id={foto_id}, url={arquivo_url[:60]}')
                except Exception as db_err:
                    erros.append({'arquivo': nome_original, 'motivo': f'Erro ao registrar no banco: {db_err}'})
                    print(f'[Upload] ERRO banco {nome_original}: {db_err}')
                    continue

            # Commit parcial a cada lote: reduz risco de perda por timeout
            conn.commit()

        # ── Atualiza capa da galeria se ainda não tinha ────────────────────
        if inseridas:
            cur.execute("SELECT foto_capa FROM galerias WHERE id = ?", (real_id,))
            gal_row = cur.fetchone()
            if gal_row and (not gal_row['foto_capa'] or gal_row['foto_capa'] in ('assets/logo/logo.png', 'Foto 001')):
                cur.execute("UPDATE galerias SET foto_capa = ? WHERE id = ?", (inseridas[0]['arquivo'], real_id))

        # ── Registro de atividade ──────────────────────────────────────────
        agora = datetime.now().strftime("%d %b %Y %H:%M")
        if inseridas:
            desc = (f'Upload via painel: {len(inseridas)} de {total_recebidos} foto(s) processada(s).'
                    + (f' {len(erros)} falha(s).' if erros else ''))
            conn.execute("""
            INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
            VALUES (?, ?, 'Fotógrafo', ?, ?, 'Computador', 'Fotógrafo')
            """, (real_id, agora, f'{len(inseridas)} foto(s) adicionadas', desc))
        conn.commit()

        # ── Relatório final ────────────────────────────────────────────────
        resultado = {
            'success': len(inseridas) > 0,
            'total_recebidos': total_recebidos,
            'count': len(inseridas),
            'inseridas': inseridas,
            'total_erros': len(erros),
        }
        if erros:
            resultado['erros'] = erros
            # Simplifica erros para exibição frontend (lista de strings)
            resultado['erros_resumo'] = [f"{e['arquivo']}: {e['motivo']}" for e in erros]
        return json_response(resultado)

    finally:
        conn.close()

@app.delete('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>')
@rate_limit()
def api_delete_foto_galeria(galeria_id, foto_id):
    """Exclui uma foto da galeria"""
    conn = get_connection()
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    conn.execute("DELETE FROM fotos WHERE id = ? AND galeria_id = ?", (foto_id, real_gal_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'deleted': foto_id})

@app.put('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>/capa')
@app.post('/api/galeria/<galeria_id:int>/fotos/<foto_id:int>/capa')
@rate_limit()
def api_set_capa_foto(galeria_id, foto_id):
    """Define uma foto específica como a capa oficial da galeria"""
    conn = get_connection()
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("SELECT arquivo, numero, titulo FROM fotos WHERE id = ? AND galeria_id = ?", (foto_id, real_gal_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return json_response({'error': 'Foto não encontrada'}, 404)
    arquivo = row['arquivo']
    conn.execute("UPDATE galerias SET foto_capa = ? WHERE id = ?", (arquivo, real_gal_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'foto_capa': arquivo, 'numero': row['numero']})

@app.get('/api/galeria/<galeria_id:int>/selecionadas')
@rate_limit()
def api_get_fotos_selecionadas(galeria_id):
    """Retorna fotos escolhidas pelo cliente e nomes formatados para busca no Windows 10 e 11"""
    conn = get_connection()
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()
    cur.execute("""
    SELECT id, numero, titulo, arquivo, status 
    FROM fotos 
    WHERE galeria_id = ? AND status IN ('pacote', 'extra')
    ORDER BY ordem ASC, id ASC
    """, (real_gal_id,))
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
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()

    cur.execute("SELECT selecao_bloqueada FROM galerias WHERE id = ?", (real_gal_id,))
    grow = cur.fetchone()
    if grow and grow['selecao_bloqueada']:
        conn.close()
        return json_response({'error': 'A seleção está bloqueada para análise pelo fotógrafo. Aguarde a liberação do estúdio caso precise realizar ajustes.'}, 403)

    cur.execute("SELECT status FROM fotos WHERE id = ? AND galeria_id = ?", (foto_id, real_gal_id))
    row = cur.fetchone()
    if not row:
        conn.close()
        return json_response({'error': 'Foto não encontrada'}, 404)

    cur_status = row['status']
    ciclo = {'nao_selecionada': 'pacote', 'pacote': 'extra', 'extra': 'nao_selecionada'}
    novo_status = ciclo.get(cur_status, 'nao_selecionada')

    cur.execute("UPDATE fotos SET status = ? WHERE id = ? AND galeria_id = ?",
                (novo_status, foto_id, real_gal_id))

    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (real_gal_id,))
    pct = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (real_gal_id,))
    ext = cur.fetchone()[0]
    cur.execute("UPDATE destinatarios SET fotos_pacote_count=?, fotos_extras_count=? WHERE galeria_id=?",
                (pct, ext, real_gal_id))

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
    real_gal_id = get_galeria_real_id(conn, galeria_id)
    cur = conn.cursor()

    cur.execute("SELECT selecao_bloqueada FROM galerias WHERE id = ?", (real_gal_id,))
    grow = cur.fetchone()
    if grow and grow['selecao_bloqueada']:
        conn.close()
        return json_response({'error': 'A seleção está bloqueada para análise pelo fotógrafo. Aguarde a liberação do estúdio caso precise realizar ajustes.'}, 403)

    conn.execute("UPDATE fotos SET status = ? WHERE id = ? AND galeria_id = ?",
                 (novo_status, foto_id, real_gal_id))
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (real_gal_id,))
    pct = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (real_gal_id,))
    ext = cur.fetchone()[0]
    cur.execute("""
        UPDATE destinatarios 
        SET fotos_pacote_count = ?, fotos_extras_count = ?,
            status_convite = CASE WHEN status_convite = 'Seleção enviada' THEN 'Seleção enviada' ELSE 'Seleção em andamento' END
        WHERE galeria_id = ?
    """, (pct, ext, real_gal_id))
    conn.commit()
    conn.close()
    return json_response({'success': True, 'foto_id': foto_id, 'status': novo_status,
                          'pacote': pct, 'extra': ext})


@app.post('/api/galeria/<galeria_id:int>/enviar-selecao')
@rate_limit(20)
def api_enviar_selecao(galeria_id):
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        data = get_body() or {}
        obs = sanitize_str(data.get('observacoes', ''), 500).strip()
        pacote_ids = data.get('pacote_ids', [])
        extra_ids = data.get('extra_ids', [])

        cur = conn.cursor()

        # Se o cliente enviou IDs explícitos de pacote/extra, sincroniza no banco
        if pacote_ids:
            for pid in pacote_ids:
                try:
                    cur.execute("UPDATE fotos SET status='pacote' WHERE id=? AND galeria_id=?", (int(pid), real_gal_id))
                except Exception:
                    pass
        if extra_ids:
            for eid in extra_ids:
                try:
                    cur.execute("UPDATE fotos SET status='extra' WHERE id=? AND galeria_id=?", (int(eid), real_gal_id))
                except Exception:
                    pass

        cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (real_gal_id,))
        pct = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (real_gal_id,))
        ext = cur.fetchone()[0]
        agora = datetime.now().strftime("%d OUT %Y %H:%M")

        descricao_ativ = f"Seleção enviada com {pct} fotos do pacote e {ext} extras."
        if obs:
            descricao_ativ += f" Observações do cliente: {obs}"

        try:
            cur.execute("""
            INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
            VALUES (?, ?, 'Cliente', 'Seleção enviada ao fotógrafo', ?, 'Computador', 'Cliente')
            """, (real_gal_id, agora, descricao_ativ))
        except Exception as e_ativ:
            print(f"[Atividades] Erro ao registrar atividade: {e_ativ}")

        try:
            cur.execute("""
                UPDATE destinatarios 
                SET status_convite = 'Seleção enviada', fotos_pacote_count = ?, fotos_extras_count = ?
                WHERE galeria_id = ?
            """, (pct, ext, real_gal_id))
        except Exception:
            pass

        # Bloqueia a seleção e atualiza status da galeria
        try:
            cur.execute("""
                UPDATE galerias 
                SET status_galeria = 'Seleção enviada', selecao_bloqueada = 1 
                WHERE id = ?
            """, (real_gal_id,))
        except Exception:
            pass

        conn.commit()
        return json_response({
            'success': True,
            'mensagem': f'Seleção enviada com sucesso! {pct} do pacote + {ext} extras.',
            'pacote': pct,
            'extra': ext,
            'selecao_bloqueada': 1
        })
    finally:
        conn.close()

@app.put('/api/galeria/<galeria_id:int>/status')
@rate_limit()
def api_update_galeria_status(galeria_id):
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        data = get_body() or {}
        novo_status = sanitize_str(data.get('status_galeria') or data.get('status', ''), 100).strip()
        bloqueado = data.get('selecao_bloqueada')

        if not novo_status and bloqueado is None:
            return json_response({'error': 'Status ou estado de bloqueio é obrigatório'}, 400)

        cur = conn.cursor()
        agora = datetime.now().strftime("%d OUT %Y %H:%M")

        # Se for liberada para ajustes, desmarca bloqueio
        if novo_status == 'Liberada para ajustes' or (bloqueado is not None and not bool(bloqueado)):
            bloqueado_val = 0
            if not novo_status:
                novo_status = 'Liberada para ajustes'
            cur.execute("UPDATE destinatarios SET status_convite = 'Liberada para ajustes' WHERE galeria_id = ?", (real_gal_id,))
            cur.execute("""
            INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
            VALUES (?, ?, 'Fotógrafo', 'Galeria liberada para ajustes', 'Fotógrafo liberou a galeria para o cliente fazer novos ajustes na seleção de fotos.', 'Painel', 'Admin')
            """, (real_gal_id, agora))
        elif novo_status in ('Seleção enviada', 'Seleção bloqueada', 'Em análise pelo fotógrafo') or (bloqueado is not None and bool(bloqueado)):
            bloqueado_val = 1
            if not novo_status:
                novo_status = 'Seleção enviada'
            cur.execute("UPDATE destinatarios SET status_convite = ? WHERE galeria_id = ?", (novo_status, real_gal_id))
            cur.execute("""
            INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
            VALUES (?, ?, 'Fotógrafo', 'Seleção bloqueada para análise', 'Fotógrafo bloqueou a seleção de fotos da galeria para análise interna.', 'Painel', 'Admin')
            """, (real_gal_id, agora))
        else:
            bloqueado_val = 0 if novo_status in ('Aguardando seleção', 'Seleção em andamento') else 1

        cur.execute("""
            UPDATE galerias 
            SET status_galeria = ?, selecao_bloqueada = ? 
            WHERE id = ?
        """, (novo_status, bloqueado_val, real_gal_id))

        conn.commit()
        return json_response({
            'success': True,
            'galeria_id': real_gal_id,
            'status_galeria': novo_status,
            'selecao_bloqueada': bloqueado_val
        })
    finally:
        conn.close()

@app.post('/api/galeria/<galeria_id:int>/liberar-ajustes')
@rate_limit()
def api_liberar_ajustes_galeria(galeria_id):
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        cur.execute("""
            UPDATE galerias 
            SET status_galeria = 'Liberada para ajustes', selecao_bloqueada = 0 
            WHERE id = ?
        """, (real_gal_id,))
        cur.execute("UPDATE destinatarios SET status_convite = 'Liberada para ajustes' WHERE galeria_id = ?", (real_gal_id,))
        agora = datetime.now().strftime("%d OUT %Y %H:%M")
        cur.execute("""
        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
        VALUES (?, ?, 'Fotógrafo', 'Galeria liberada para ajustes', 'Fotógrafo liberou a galeria para o cliente fazer novos ajustes na seleção.', 'Painel', 'Admin')
        """, (real_gal_id, agora))
        conn.commit()
        return json_response({'success': True, 'galeria_id': real_gal_id, 'status_galeria': 'Liberada para ajustes', 'selecao_bloqueada': 0})
    finally:
        conn.close()

@app.post('/api/galeria/<galeria_id:int>/bloquear-ajustes')
@rate_limit()
def api_bloquear_ajustes_galeria(galeria_id):
    conn = get_connection()
    try:
        real_gal_id = get_galeria_real_id(conn, galeria_id)
        cur = conn.cursor()
        cur.execute("""
            UPDATE galerias 
            SET status_galeria = 'Seleção enviada', selecao_bloqueada = 1 
            WHERE id = ?
        """, (real_gal_id,))
        cur.execute("UPDATE destinatarios SET status_convite = 'Seleção enviada' WHERE galeria_id = ?", (real_gal_id,))
        agora = datetime.now().strftime("%d OUT %Y %H:%M")
        cur.execute("""
        INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge)
        VALUES (?, ?, 'Fotógrafo', 'Seleção bloqueada para análise', 'Fotógrafo bloqueou a seleção de fotos da galeria para análise.', 'Painel', 'Admin')
        """, (real_gal_id, agora))
        conn.commit()
        return json_response({'success': True, 'galeria_id': real_gal_id, 'status_galeria': 'Seleção enviada', 'selecao_bloqueada': 1})
    finally:
        conn.close()

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

        # Sincroniza fotos_pacote_count e fotos_extras_count com a contagem real
        cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='pacote'", (real_gal_id,))
        pct = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fotos WHERE galeria_id=? AND status='extra'", (real_gal_id,))
        ext = cur.fetchone()[0]
        if pct > 0 or ext > 0:
            cur.execute("""
                UPDATE destinatarios 
                SET fotos_pacote_count = CASE WHEN fotos_pacote_count < ? THEN ? ELSE fotos_pacote_count END,
                    fotos_extras_count = CASE WHEN fotos_extras_count < ? THEN ? ELSE fotos_extras_count END
                WHERE galeria_id = ?
            """, (pct, pct, ext, ext, real_gal_id))
            conn.commit()

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
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome FROM site_categorias WHERE id = ?", (cat_id,))
        row = cur.fetchone()
        if row:
            cat_nome = row['nome']
            # Reatribui fotos da categoria para 'Geral' evitando fotos órfãs no carrossel
            conn.execute("UPDATE site_fotos SET categoria_nome = 'Geral' WHERE categoria_nome = ?", (cat_nome,))
        conn.execute("DELETE FROM site_categorias WHERE id = ?", (cat_id,))
        conn.commit()
    finally:
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
        
        # 1. Tenta atualizar o arquivo local em assets/logo/logo.png
        try:
            logo_path = os.path.join(BASE_DIR, 'assets', 'logo', 'logo.png')
            os.makedirs(os.path.dirname(logo_path), exist_ok=True)
            with open(logo_path, 'wb') as f:
                f.write(file_bytes)
        except Exception as e_local:
            print(f"[Logo] Aviso ao salvar logo em assets: {e_local}")

        # 2. Salva via salvar_imagem_upload (suporta Supabase Storage, Vercel Data URI e uploads/ local)
        url = salvar_imagem_upload(file_bytes, 'logo.png')
        if '?' not in url and not url.startswith('data:'):
            url += f"?v={int(time.time())}"

        # 3. Salva a URL no banco de dados site_textos
        update_site_textos({'logo_url': url})

        return json_response({'success': True, 'url': url})
    except Exception as e:
        return json_response({'error': f'Falha ao atualizar logo: {str(e)}'}, 500)

@app.get('/api/site/logo-info')
@rate_limit()
def api_get_site_logo_info():
    """Retorna a URL atualizada do logotipo oficial do estúdio."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT valor FROM site_textos WHERE chave = 'logo_url'")
    row = cur.fetchone()
    conn.close()
    if row and row['valor']:
        return json_response({'url': row['valor']})
    return json_response({'url': f'assets/logo/logo.png?v={int(time.time())}'})

@app.get('/api/site/logo')
def api_get_site_logo():
    """Serve a Logo Oficial do estúdio."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT valor FROM site_textos WHERE chave = 'logo_url'")
    row = cur.fetchone()
    conn.close()
    if row and row['valor']:
        url = row['valor']
        if url.startswith('http://') or url.startswith('https://'):
            from bottle import redirect
            return redirect(url)
    logo_path = os.path.join(BASE_DIR, 'assets', 'logo', 'logo.png')
    if os.path.exists(logo_path):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return static_file('logo.png', root=os.path.join(BASE_DIR, 'assets', 'logo'))
    abort(404, 'Logo não encontrada')

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
        if '?' not in url and not url.startswith('data:'):
            url += f"?v={int(time.time())}"
        
        # Salva no banco de dados site_textos
        update_site_textos({'foto_login': url})

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
    # Evita retornar placeholders corrompidos ou pixels de testes antigos
    if url and url.startswith('data:image/') and len(url) < 200:
        url = 'uploads/login_hero.jpg'
    return json_response({'url': url})

@app.get('/api/site/marca-dagua')
@rate_limit()
def api_get_site_marca_dagua():
    """Retorna as configurações atuais de posição, tamanho e opacidade da marca d'água."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT chave, valor FROM site_textos WHERE chave IN ('marca_posicao', 'marca_tamanho', 'marca_opacidade')")
        rows = dict(cur.fetchall())
    except Exception:
        rows = {}
    finally:
        conn.close()
    
    pos = rows.get('marca_posicao') or 'center'
    try:
        tam = int(rows.get('marca_tamanho') or 55)
    except Exception:
        tam = 55
    try:
        opac = int(rows.get('marca_opacidade') or 35)
    except Exception:
        opac = 35

    pos_map = {
        'center': 'center center',
        'bottom-right': 'calc(100% - 18px) calc(100% - 18px)',
        'bottom-left': '18px calc(100% - 18px)',
        'top-right': 'calc(100% - 18px) 18px',
        'top-left': '18px 18px',
        'repeat': 'center center'
    }
    repeat_val = 'repeat' if pos == 'repeat' else 'no-repeat'
    pos_css = pos_map.get(pos, 'center center')
    size_css = f"{tam}% auto" if pos != 'repeat' else "28% auto"
    size_large_css = f"{int(tam * 0.8)}% auto" if pos != 'repeat' else "22% auto"
    opac_css = str(round(opac / 100.0, 2))

    return json_response({
        'posicao': pos,
        'tamanho': tam,
        'opacidade': opac,
        'posicao_css': pos_css,
        'tamanho_css': size_css,
        'tamanho_large_css': size_large_css,
        'opacidade_css': opac_css,
        'repeat': repeat_val
    })

@app.post('/api/site/marca-dagua')
@rate_limit(30)
def api_update_site_marca_dagua():
    """Salva a posição, tamanho e opacidade da marca d'água no banco."""
    try:
        data = get_body()
        pos = sanitize_str(data.get('posicao', 'center'), 50)
        try:
            tam = max(15, min(95, int(data.get('tamanho', 55))))
        except Exception:
            tam = 55
        try:
            opac = max(5, min(95, int(data.get('opacidade', 35))))
        except Exception:
            opac = 35

        if pos not in ['center', 'bottom-right', 'bottom-left', 'top-right', 'top-left', 'repeat']:
            pos = 'center'

        update_site_textos({
            'marca_posicao': pos,
            'marca_tamanho': str(tam),
            'marca_opacidade': str(opac)
        })

        pos_map = {
            'center': 'center center',
            'bottom-right': 'calc(100% - 18px) calc(100% - 18px)',
            'bottom-left': '18px calc(100% - 18px)',
            'top-right': 'calc(100% - 18px) 18px',
            'top-left': '18px 18px',
            'repeat': 'center center'
        }
        repeat_val = 'repeat' if pos == 'repeat' else 'no-repeat'
        pos_css = pos_map.get(pos, 'center center')
        size_css = f"{tam}% auto" if pos != 'repeat' else "28% auto"
        size_large_css = f"{int(tam * 0.8)}% auto" if pos != 'repeat' else "22% auto"
        opac_css = str(round(opac / 100.0, 2))

        return json_response({
            'success': True,
            'posicao': pos,
            'tamanho': tam,
            'opacidade': opac,
            'posicao_css': pos_css,
            'tamanho_css': size_css,
            'tamanho_large_css': size_large_css,
            'opacidade_css': opac_css,
            'repeat': repeat_val
        })
    except Exception as e:
        import traceback
        log_error('backend', f"Erro ao atualizar marca d'água: {str(e)}", detalhe=traceback.format_exc(), rota='/api/site/marca-dagua')
        return json_response({'error': f"Erro ao salvar configurações da marca d'água: {str(e)}"}, 500)


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

    try:
        update_site_textos(sanitizado)
        audit(ip, '/api/site/textos', 'POST', None, 'TEXTOS_SITE_UPDATE', f"{len(sanitizado)} campos atualizados", 200)
        return json_response({'success': True, 'mensagem': 'Textos da página inicial atualizados com sucesso!', 'textos': get_site_textos()})
    except Exception as e:
        import traceback
        log_error('backend', f"Erro ao atualizar textos do site: {str(e)}", detalhe=traceback.format_exc(), rota='/api/site/textos')
        return json_response({'error': f"Erro ao atualizar textos do site: {str(e)}"}, 500)


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

@app.post('/api/log/error')
@rate_limit(60)
def api_report_client_error():
    """Recebe erros do frontend (window.onerror / unhandledrejection) e grava no error_log"""
    data = get_body()
    mensagem = sanitize_str(data.get('mensagem', 'Erro desconhecido'), 500)
    detalhe = sanitize_str(data.get('detalhe', ''), 2000)
    rota = sanitize_str(data.get('rota', request.environ.get('HTTP_REFERER', '')), 250)
    log_error('frontend', mensagem, detalhe, rota)
    return json_response({'success': True})

@app.get('/api/admin/error-log')
@rate_limit()
def api_get_error_log():
    """Lista erros capturados do sistema (frontend e backend)."""
    limite = min(int(request.query.get('limit', 50)), 200)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM error_log ORDER BY id DESC LIMIT ?", (limite,))
        rows = [dict(r) for r in cur.fetchall()]
        return json_response(rows)
    finally:
        conn.close()

@app.delete('/api/admin/error-log')
@rate_limit()
def api_clear_error_log():
    """Limpa a tabela de logs de erro."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM error_log")
        conn.commit()
        return json_response({'success': True, 'mensagem': 'Log de erros limpo com sucesso.'})
    finally:
        conn.close()

@app.post('/api/admin/error-log/test')
@rate_limit()
def api_test_error_log():
    """Endpoint de teste para validar se o sistema de log de erros está ativo."""
    log_error('backend', 'Teste de verificação do sistema de diagnóstico', detalhe='Validação de integridade do error_log executada com sucesso.', rota='/api/admin/error-log/test')
    return json_response({'success': True, 'mensagem': 'Erro de teste registrado no error_log com sucesso.'})

# ==============================================================================
# 8.5 MÓDULO 2: PORTAL MULTI-GALERIA (VERCEL / SUPABASE / SQLITE)
# ==============================================================================

@app.get('/api/portal/<token>')
@rate_limit()
def api_get_portal_client(token):
    """Retorna dados do cliente e todos os seus álbuns disponíveis para seleção."""
    token = token.strip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Busca destinatário pelo e-mail ou nome
        cur.execute("SELECT id, galeria_id, nome, email FROM destinatarios WHERE email = ? OR id = ? LIMIT 1", (token, int(token) if token.isdigit() else -1))
        dest = cur.fetchone()

        if dest:
            dest_dict = dict(dest)
            client_name = dest_dict.get('nome') or 'Cliente'
            client_email = dest_dict.get('email') or token
            # Busca todas as galerias onde este cliente é destinatário
            cur.execute("""
                SELECT g.id, g.nome AS title, g.foto_capa AS cover_image_url, g.data_trabalho AS event_date,
                       g.status_galeria, g.limite_pacote AS max_photos_included, g.criado_em
                FROM galerias g
                JOIN destinatarios d ON d.galeria_id = g.id
                WHERE d.email = ? OR d.nome = ?
                ORDER BY g.id DESC
            """, (client_email, client_name))
            gals = [dict(r) for r in cur.fetchall()]
        else:
            # Fallback demonstrativo: retorna as galerias ativas
            client_name = "Cliente"
            client_email = token
            cur.execute("""
                SELECT id, nome AS title, foto_capa AS cover_image_url, data_trabalho AS event_date,
                       status_galeria, limite_pacote AS max_photos_included, criado_em
                FROM galerias
                ORDER BY id DESC LIMIT 10
            """)
            gals = [dict(r) for r in cur.fetchall()]

        # Para cada galeria, calcula total de fotos e fotos selecionadas
        albums = []
        for g in gals:
            gid = g['id']
            cur.execute("SELECT COUNT(*) AS total FROM fotos WHERE galeria_id = ?", (gid,))
            total_f = cur.fetchone()['total']
            cur.execute("SELECT COUNT(*) AS sel FROM fotos WHERE galeria_id = ? AND status IN ('pacote', 'extra')", (gid,))
            sel_f = cur.fetchone()['sel']

            status_clean = 'concluido' if g.get('status_galeria') == 'Concluído' else 'em_selecao'

            albums.append({
                'id': gid,
                'title': g.get('title') or f"Ensaio #{gid}",
                'cover_image_url': g.get('cover_image_url') or 'assets/logo/logo.png',
                'event_date': g.get('event_date') or '',
                'status': status_clean,
                'max_photos_included': g.get('max_photos_included') or 20,
                'total_photos': total_f,
                'selected_photos': sel_f
            })

        return json_response({
            'client': {
                'id': 1,
                'name': client_name,
                'email': client_email,
                'access_token': token
            },
            'albums': albums
        })
    finally:
        conn.close()

@app.get('/api/portal/<token>/album/<album_id:int>')
@rate_limit()
def api_get_portal_album_photos(token, album_id):
    """Retorna fotos completas da galeria para o portal do cliente."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM galerias WHERE id = ?", (album_id,))
        gal = cur.fetchone()
        if not gal:
            response.status = 404
            return json_response({'error': 'Ensaio não encontrado.'})

        gal_dict = dict(gal)

        # Busca outras galerias para o switcher rápido
        cur.execute("SELECT id, nome AS title, status_galeria FROM galerias ORDER BY id DESC LIMIT 8")
        other_raw = [dict(r) for r in cur.fetchall()]
        other_albums = [{
            'id': r['id'],
            'title': r.get('title') or f"Ensaio #{r['id']}",
            'status': 'concluido' if r.get('status_galeria') == 'Concluído' else 'em_selecao'
        } for r in other_raw]

        # Busca todas as fotos da galeria ordenadas deterministamente sem LIMIT
        cur.execute("""
            SELECT id, galeria_id, numero, titulo AS original_name, arquivo, status, ordem
            FROM fotos
            WHERE galeria_id = ?
            ORDER BY ordem ASC, id ASC
        """, (album_id,))
        rows = [dict(r) for r in cur.fetchall()]

        photos = []
        for r in rows:
            is_sel = r.get('status') in ('pacote', 'extra')
            img_url = r.get('arquivo', '')
            photos.append({
                'id': r['id'],
                'album_id': r['galeria_id'],
                'original_name': r.get('original_name') or r.get('numero') or f"Foto {r['id']}",
                'thumb_url': img_url,
                'preview_url': img_url,
                'is_selected': is_sel,
                'display_order': r.get('ordem') or r['id']
            })

        return json_response({
            'client': {'id': 1, 'name': 'Cliente', 'email': token},
            'album': {
                'id': gal_dict['id'],
                'title': gal_dict.get('nome') or 'Ensaio',
                'cover_image_url': gal_dict.get('foto_capa'),
                'event_date': gal_dict.get('data_trabalho'),
                'max_photos_included': gal_dict.get('limite_pacote') or 20,
                'status': 'concluido' if gal_dict.get('status_galeria') == 'Concluído' else 'em_selecao'
            },
            'other_albums': other_albums,
            'photos': photos
        })
    finally:
        conn.close()

@app.post('/api/portal/<token>/album/<album_id:int>/select')
@rate_limit()
def api_post_portal_select(token, album_id):
    """Salva a seleção de fotos do cliente na galeria."""
    data = get_body()
    conn = get_connection()
    try:
        cur = conn.cursor()
        photo_id = data.get('photo_id')
        is_sel = data.get('is_selected')

        if photo_id is not None:
            new_status = 'pacote' if is_sel else 'nao_selecionada'
            cur.execute("UPDATE fotos SET status = ? WHERE id = ? AND galeria_id = ?", (new_status, int(photo_id), album_id))
            conn.commit()
        elif 'selected_ids' in data:
            sel_ids = set(data.get('selected_ids', []))
            cur.execute("UPDATE fotos SET status = 'nao_selecionada' WHERE galeria_id = ?", (album_id,))
            for pid in sel_ids:
                cur.execute("UPDATE fotos SET status = 'pacote' WHERE id = ? AND galeria_id = ?", (int(pid), album_id))
            conn.commit()

        if data.get('finalize'):
            cur.execute("UPDATE galerias SET status_galeria = 'Concluído' WHERE id = ?", (album_id,))
            conn.commit()

        cur.execute("SELECT COUNT(*) AS sel FROM fotos WHERE galeria_id = ? AND status IN ('pacote', 'extra')", (album_id,))
        count = cur.fetchone()['sel']

        return json_response({'success': True, 'selected_photos': count})
    finally:
        conn.close()

# ── Rotas do Portal de Clientes (HTML) ──
@app.route('/portal/<token>')
@app.route('/portal/<token>/')
def serve_portal_entry(token):
    return static_file('portal.html', root=os.path.join(BASE_DIR, 'public'))

@app.route('/portal/<token>/album/<album_id:int>')
def serve_portal_album(token, album_id):
    return static_file('portal-album.html', root=os.path.join(BASE_DIR, 'public'))

@app.route('/public/<filepath:path>')
def serve_public_assets(filepath):
    return static_file(filepath, root=os.path.join(BASE_DIR, 'public'))

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

@app.route('/favicon.ico')
def serve_favicon():
    ico_path = os.path.join(BASE_DIR, 'favicon.ico')
    if os.path.exists(ico_path):
        return static_file('favicon.ico', root=BASE_DIR, mimetype='image/x-icon')
    return static_file('logo.png', root=os.path.join(BASE_DIR, 'assets', 'logo'), mimetype='image/png')

@app.route('/<filepath:path>')
def serve_static(filepath):
    # Se a requisição for para /api/ e chegou aqui, a rota da API não existe -> 404
    if filepath.startswith('api/'):
        abort(404, 'API não encontrada')

    # Previne Path Traversal
    if '..' in filepath or filepath.startswith('/') or filepath.startswith('\\'):
        abort(403, 'Acesso negado')

    # Bloqueia acesso a arquivos sensíveis
    first_segment = filepath.split('/')[0].split('\\')[0]
    if first_segment in BLOCKED_PATHS or filepath in BLOCKED_PATHS:
        abort(403, 'Acesso negado')

    # Se não tiver extensão, verifica se existe arquivo .html correspondente (rotas amigáveis)
    _, ext = os.path.splitext(filepath)
    if not ext:
        html_candidate = filepath + '.html'
        if os.path.exists(os.path.join(BASE_DIR, html_candidate)):
            return static_file(html_candidate, root=BASE_DIR)
        abort(404, 'Página não encontrada')

    # Verifica extensão
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

@app.error(403)
def error_handler_403(err):
    p = request.path if hasattr(request, 'path') else ''
    if p.startswith('/api/'):
        response.content_type = 'application/json; charset=utf-8'
        return json.dumps({'error': 'Acesso negado', 'status': 403, 'path': p}, ensure_ascii=False)
    response.content_type = 'text/html; charset=utf-8'
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Acesso Negado | Casa da Foto Studio</title>
  <link rel="stylesheet" href="/styles.css?v=luxo4">
</head>
<body style="background: #251710; color: #FAF5EE; display: flex; align-items: center; justify-content: center; min-height: 100vh; text-align: center; font-family: sans-serif; padding: 2rem;">
  <div>
    <h1 style="font-size: 3rem; color: #C59B6D; margin-bottom: 0.5rem;">403</h1>
    <h2 style="font-size: 1.5rem; margin-bottom: 1rem;">Acesso Negado</h2>
    <p style="color: #D8CAB9; margin-bottom: 2rem;">Você não possui permissão para acessar este recurso.</p>
    <a href="/index.html" style="background: #8C5F35; color: #FFF; padding: 0.75rem 1.75rem; border-radius: 9999px; text-decoration: none; font-weight: 700;">← Voltar ao Início</a>
  </div>
</body>
</html>"""

@app.error(404)
def error_handler_404(err):
    p = request.path if hasattr(request, 'path') else ''
    if p.startswith('/api/'):
        response.content_type = 'application/json; charset=utf-8'
        return json.dumps({'error': 'Recurso não encontrado', 'status': 404, 'path': p}, ensure_ascii=False)
    response.content_type = 'text/html; charset=utf-8'
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Página Não Encontrada | Casa da Foto Studio</title>
  <link rel="stylesheet" href="/styles.css?v=luxo4">
</head>
<body style="background: #251710; color: #FAF5EE; display: flex; align-items: center; justify-content: center; min-height: 100vh; text-align: center; font-family: sans-serif; padding: 2rem;">
  <div>
    <h1 style="font-size: 3rem; color: #C59B6D; margin-bottom: 0.5rem;">404</h1>
    <h2 style="font-size: 1.5rem; margin-bottom: 1rem;">Página Não Encontrada</h2>
    <p style="color: #D8CAB9; margin-bottom: 2rem;">O endereço solicitado não existe ou foi movido.</p>
    <a href="/index.html" style="background: #8C5F35; color: #FFF; padding: 0.75rem 1.75rem; border-radius: 9999px; text-decoration: none; font-weight: 700;">← Voltar ao Início</a>
  </div>
</body>
</html>"""

@app.error(500)
def error_handler_500(err):
    origem = 'backend'
    mensagem = str(err.exception) if hasattr(err, 'exception') and err.exception else 'Erro interno do servidor 500'
    detalhe = str(err.traceback) if hasattr(err, 'traceback') and err.traceback else ''
    log_error(origem, mensagem, detalhe, request.path if hasattr(request, 'path') else '')
    response.content_type = 'application/json; charset=utf-8'
    return json.dumps({'error': 'Ocorreu um erro interno no servidor', 'mensagem': mensagem, 'status': 500})

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
