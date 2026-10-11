import sqlite3
import os
import json
import bcrypt
from datetime import datetime

import shutil

# Carrega .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')

# No Vercel (onde o filesystem é read-only), se não houver DATABASE_URL, utiliza /tmp/banco.db
if os.environ.get('VERCEL') == '1' and not DATABASE_URL:
    tmp_db = '/tmp/banco.db'
    orig_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco.db')
    if not os.path.exists(tmp_db) and os.path.exists(orig_db):
        try:
            shutil.copy2(orig_db, tmp_db)
        except Exception:
            pass
    DB_FILE = tmp_db
else:
    DB_FILE = os.environ.get('DB_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco.db'))

def is_postgres() -> bool:
    """Retorna True se configurado para banco PostgreSQL / Supabase."""
    return bool(DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')))

# ── ADAPTADOR POSTGRESQL / SUPABASE (SUPAVISOR TRANSACTION MODE) ──────────────
class PostgresCursorWrapper:
    def __init__(self, raw_cur):
        self._cur = raw_cur
        self.lastrowid = None

    def execute(self, sql, params=None):
        # 1. Substitui placeholders SQLite '?' por PostgreSQL '%s'
        converted_sql = sql.replace('?', '%s')
        
        # 2. Converte 'INSERT OR IGNORE INTO' para 'INSERT INTO ... ON CONFLICT DO NOTHING'
        if 'INSERT OR IGNORE INTO' in converted_sql.upper():
            converted_sql = converted_sql.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
            if 'ON CONFLICT' not in converted_sql.upper():
                converted_sql = converted_sql.rstrip('; ') + ' ON CONFLICT DO NOTHING'

        # 3. Tratamento para cur.lastrowid em comandos INSERT
        is_insert = converted_sql.strip().upper().startswith('INSERT INTO')
        if is_insert and 'RETURNING' not in converted_sql.upper() and 'DO NOTHING' not in converted_sql.upper():
            converted_sql = converted_sql.rstrip('; ') + ' RETURNING id;'
            self._cur.execute(converted_sql, params or ())
            try:
                row = self._cur.fetchone()
                if row:
                    self.lastrowid = row['id'] if isinstance(row, dict) else row[0]
            except Exception:
                pass
        else:
            self._cur.execute(converted_sql, params or ())
        return self

    def executemany(self, sql, seq_of_params):
        converted_sql = sql.replace('?', '%s')
        if 'INSERT OR IGNORE INTO' in converted_sql.upper():
            converted_sql = converted_sql.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
            if 'ON CONFLICT' not in converted_sql.upper():
                converted_sql = converted_sql.rstrip('; ') + ' ON CONFLICT DO NOTHING'
        self._cur.executemany(converted_sql, seq_of_params)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows] if rows else []

    @property
    def rowcount(self):
        return self._cur.rowcount

class PostgresConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        import psycopg2.extras
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

def get_connection():
    if is_postgres():
        try:
            import psycopg2
            # Supavisor pooler (porta 6543) com timeout de conexão
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print(f"[Supabase Postgres] Erro ao conectar ao Postgres: {e}. Usando fallback SQLite.")
    
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass
    return conn

def hash_senha(senha_plain: str) -> str:
    """Gera hash bcrypt seguro da senha."""
    return bcrypt.hashpw(senha_plain.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def verificar_senha(senha_plain: str, senha_hash: str) -> bool:
    """Verifica senha contra hash bcrypt."""
    try:
        return bcrypt.checkpw(senha_plain.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception:
        return False

def init_db():
    if is_postgres():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'usuarios'")
            row = cur.fetchone()
            conn.close()
            if row:
                print("[Supabase Postgres] Banco Supabase conectado e tabelas verificadas.")
            else:
                print("[Supabase Postgres] Conectado! Execute supabase_schema.sql no SQL Editor do Supabase.")
        except Exception as e:
            print(f"[Supabase Postgres] Verificação de tabelas: {e}")
        return

    conn = get_connection()
    cur = conn.cursor()

    # ── 1. Usuários (Fotógrafo, Clientes e Admin) ──────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo        TEXT NOT NULL CHECK(tipo IN ('admin','fotografo','cliente')),
        nome        TEXT NOT NULL,
        email       TEXT UNIQUE,
        login       TEXT UNIQUE,
        senha_hash  TEXT NOT NULL,
        avatar      TEXT,
        ativo       INTEGER DEFAULT 1,
        tentativas_login INTEGER DEFAULT 0,
        bloqueado_ate    TEXT,
        criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
        ultimo_login DATETIME
    )
    """)

    # ── 2. Projetos (Kanban) ───────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projetos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_cliente    TEXT NOT NULL,
        tipo_ensaio     TEXT NOT NULL,
        categoria_tag   TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'novos'
                        CHECK(status IN ('novos','andamento','revisao','entrega','finalizados','prova')),
        sessoes         INTEGER DEFAULT 1,
        prazo           TEXT,
        avatar_img      TEXT,
        criado_em       DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── 3. Galerias ────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS galerias (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        projeto_id            INTEGER,
        nome                  TEXT NOT NULL,
        categoria             TEXT DEFAULT 'Galeria demonstrativa',
        data_trabalho         TEXT DEFAULT '08/10/2026',
        exibicao              TEXT DEFAULT 'Ultra HD - 4K (3840 pixels)',
        idioma                TEXT DEFAULT 'Português (Brasil)',
        mensagem_acesso       TEXT,
        permitir_comentarios  INTEGER DEFAULT 1,
        permitir_compartilhar INTEGER DEFAULT 0,
        prazo_selecao         TEXT DEFAULT '20/10/2026',
        horario_prazo         TEXT DEFAULT '23:59',
        limite_pacote         INTEGER DEFAULT 10,
        valor_foto_extra      REAL DEFAULT 25.00,
        permitir_extras       INTEGER DEFAULT 1,
        confirmar_extras      INTEGER DEFAULT 1,
        tipo_acesso           TEXT DEFAULT 'convite',
        senha_galeria         TEXT DEFAULT 'casadafoto2026',
        marca_dagua           INTEGER DEFAULT 1,
        bloquear_clique       INTEGER DEFAULT 1,
        permitir_download     INTEGER DEFAULT 0,
        quando_disponibilizar TEXT DEFAULT 'Após revisão e aprovação do fotógrafo',
        fotos_liberadas       TEXT DEFAULT 'Somente seleção aprovada',
        formato_download      TEXT DEFAULT 'JPEG - qualidade máxima',
        perfil_cor            TEXT DEFAULT 'sRGB',
        resolucao_download    TEXT DEFAULT 'Alta resolução - tamanho original',
        versao_redes          INTEGER DEFAULT 1,
        agrupar_zip           INTEGER DEFAULT 1,
        prazo_download_dias   INTEGER DEFAULT 30,
        avisar_expirar        INTEGER DEFAULT 1,
        organizacao_fotos     TEXT DEFAULT 'Grade regular',
        espacamento           TEXT DEFAULT 'Confortável',
        exibir_numero         INTEGER DEFAULT 1,
        mostrar_boas_vindas   INTEGER DEFAULT 1,
        foto_capa             TEXT DEFAULT 'Foto 001',
        estilo_capa           TEXT DEFAULT 'Foto e título lado a lado',
        enquadramento         TEXT DEFAULT 'Preservar imagem original',
        tema_visual           TEXT DEFAULT 'Casa da Foto - creme e bronze',
        tipografia            TEXT DEFAULT 'Inter - clara e acolhedora',
        criado_em             DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE SET NULL
    )
    """)

    # ── 4. Fotos da Galeria ────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fotos (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        galeria_id         INTEGER NOT NULL,
        numero             TEXT NOT NULL,
        titulo             TEXT,
        arquivo            TEXT NOT NULL,
        status             TEXT NOT NULL DEFAULT 'nao_selecionada'
                           CHECK(status IN ('pacote','extra','nao_selecionada')),
        ordem              INTEGER DEFAULT 0,
        comentarios_count  INTEGER DEFAULT 0,
        FOREIGN KEY (galeria_id) REFERENCES galerias(id) ON DELETE CASCADE
    )
    """)

    # ── 5. Destinatários / Convites ────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS destinatarios (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        galeria_id          INTEGER NOT NULL,
        nome                TEXT NOT NULL,
        email               TEXT NOT NULL,
        permissao           TEXT DEFAULT 'Apenas visualizar',
        principal           INTEGER DEFAULT 0,
        status_convite      TEXT DEFAULT 'Convite preparado',
        data_convite        TEXT,
        ultimo_acesso       TEXT DEFAULT 'Aguardando acesso',
        total_acessos       INTEGER DEFAULT 0,
        fotos_pacote_count  INTEGER DEFAULT 0,
        fotos_extras_count  INTEGER DEFAULT 0,
        FOREIGN KEY (galeria_id) REFERENCES galerias(id) ON DELETE CASCADE
    )
    """)

    # ── 6. Histórico de Atividades ─────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS atividades (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        galeria_id  INTEGER NOT NULL,
        data_hora   TEXT NOT NULL,
        autor_tipo  TEXT NOT NULL,
        titulo      TEXT NOT NULL,
        descricao   TEXT,
        dispositivo TEXT DEFAULT 'Computador',
        tipo_badge  TEXT DEFAULT 'Fotógrafo',
        criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (galeria_id) REFERENCES galerias(id) ON DELETE CASCADE
    )
    """)

    # ── 7. Mensagens de Contato ────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS contatos (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        nome         TEXT NOT NULL,
        email        TEXT,
        telefone     TEXT,
        tipo_ensaio  TEXT,
        mensagem     TEXT NOT NULL,
        lido         INTEGER DEFAULT 0,
        data_envio   DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── 8. Categorias do Site Público (zerado por padrão) ─────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS site_categorias (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        nome      TEXT NOT NULL UNIQUE COLLATE NOCASE,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── 9. Fotos do Carrossel do Site (zerado por padrão) ─────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS site_fotos (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo         TEXT NOT NULL,
        categoria_nome TEXT NOT NULL,
        arquivo        TEXT NOT NULL,
        descricao      TEXT,
        criado_em      DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── 10. Pacotes do Site Público ────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS site_pacotes (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo    TEXT NOT NULL,
        descricao TEXT,
        imagem    TEXT,
        valor     TEXT DEFAULT 'Consultar valores',
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── 11. Log de Auditoria de Segurança ─────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        ip         TEXT,
        rota       TEXT,
        metodo     TEXT,
        usuario_id INTEGER,
        acao       TEXT,
        detalhe    TEXT,
        status     INTEGER,
        criado_em  DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── 12. Textos Customizáveis da Tela Inicial ──────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS site_textos (
        chave      TEXT PRIMARY KEY,
        valor      TEXT NOT NULL,
        descricao  TEXT
    )
    """)

    # ── 13. Índices para Performance ──────────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_login ON usuarios(login)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fotos_galeria ON fotos(galeria_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_atividades_galeria ON atividades(galeria_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_site_fotos_cat ON site_fotos(categoria_nome)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_ip ON audit_log(ip)")

    conn.commit()

    # Migração suave para coluna de valor de foto extra
    try:
        cur.execute("ALTER TABLE galerias ADD COLUMN valor_foto_extra REAL DEFAULT 25.00")
        conn.commit()
    except Exception:
        pass

    # ── SEEDING: Apenas dados essenciais (admin garantido; fotógrafo cria o restante via painel) ──

    # Garante que o usuário admin sempre existe com credenciais do .env ou padrão
    admin_login = os.environ.get('ADMIN_LOGIN', 'GoAdm')
    admin_senha = os.environ.get('ADMIN_SENHA_INICIAL', 'Go06190608*')

    cur.execute("SELECT id FROM usuarios WHERE tipo='admin'")
    row = cur.fetchone()
    if not row:
        cur.execute("""
        INSERT OR IGNORE INTO usuarios (tipo, nome, email, login, senha_hash, avatar)
        VALUES ('admin','Administrador do Estúdio','admin@casadafoto.com',?,?,'AD')
        """, (admin_login, hash_senha(admin_senha)))
    else:
        cur.execute("""
        UPDATE usuarios
        SET login=?, senha_hash=?, ativo=1, tentativas_login=0, bloqueado_ate=NULL
        WHERE tipo='admin'
        """, (admin_login, hash_senha(admin_senha)))

    # Garante usuário fotógrafo funcional (contato@casadafoto.com / 123456)
    cur.execute("SELECT id FROM usuarios WHERE tipo='fotografo'")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO usuarios (tipo, nome, email, login, senha_hash, avatar, ativo)
        VALUES ('fotografo', 'Fotógrafo Casa da Foto', 'contato@casadafoto.com', 'contato@casadafoto.com', ?, 'CF', 1)
        """, (hash_senha('123456'),))

    # Garante usuário cliente funcional (cliente@exemplo.com / 123456)
    cur.execute("SELECT id FROM usuarios WHERE tipo='cliente'")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO usuarios (tipo, nome, email, login, senha_hash, avatar, ativo)
        VALUES ('cliente', 'Cliente Exemplo', 'cliente@exemplo.com', 'cliente@exemplo.com', ?, 'CL', 1)
        """, (hash_senha('123456'),))

    # Garante Projeto 1 e Galeria 1 para testes e navegação completa
    cur.execute("SELECT id FROM projetos WHERE id=1")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO projetos (id, nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img)
        VALUES (1, 'Família Silva (Exemplo)', 'Ensaio Família', 'Família', 'novos', 1, '30/10/2026', 'assets/logo/logo.png')
        """)

    cur.execute("SELECT id FROM galerias WHERE id=1")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO galerias (id, projeto_id, nome, categoria, data_trabalho, prazo_selecao, limite_pacote, valor_foto_extra, foto_capa)
        VALUES (1, 1, 'Galeria Principal - Família Silva', 'Ensaio Família', '11/10/2026', '30/10/2026', 15, 25.00, 'assets/logo/logo.png')
        """)

    cur.execute("SELECT id FROM destinatarios WHERE galeria_id=1")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO destinatarios (galeria_id, nome, email, permissao, principal, status_convite)
        VALUES (1, 'Cliente Exemplo', 'cliente@exemplo.com', 'Selecionar fotos', 1, 'Convite enviado')
        """)

    # Pacotes de Ensaio do Site Público
    cur.execute("SELECT COUNT(*) FROM site_pacotes")
    if cur.fetchone()[0] == 0:
        pacotes_iniciais = [
            ('Pacote Ensaio Família', 'Sessão completa em estúdio com cenários temáticos e iluminação acolhedora.', 'assets/logo/logo.png', 'R$ 450,00'),
            ('Pacote Gestante Prime', 'Registro afetivo da gestação com figurinos inclusos e produção cuidadosa.', 'assets/logo/logo.png', 'R$ 550,00'),
            ('Pacote Retrato Pessoal & Profissional', 'Fotos elegantes para perfil profissional, redes sociais e marca pessoal.', 'assets/logo/logo.png', 'R$ 380,00')
        ]
        cur.executemany("""
        INSERT INTO site_pacotes (titulo, descricao, imagem, valor) VALUES (?, ?, ?, ?)
        """, pacotes_iniciais)

    # Textos da Tela Inicial (seeding inicial)
    cur.execute("SELECT COUNT(*) FROM site_textos")
    if cur.fetchone()[0] == 0:
        textos_iniciais = [
            ('hero_tag', 'ESTÚDIO FOTOGRÁFICO', 'Tag acima do título no Hero'),
            ('hero_titulo', 'Casa da Foto Studio', 'Título principal no Hero'),
            ('hero_descricao', 'Espaço acolhedor para ensaios, registros familiares e momentos especiais. Trabalhamos com iluminação natural, cenários personalizados e um atendimento que torna cada sessão tranquila e autêntica.', 'Descrição principal do estúdio'),
            ('header_slogan', 'Momentos que ficam', 'Slogan no cabeçalho do site'),
            ('contato_titulo', 'Vamos conversar sobre o seu ensaio', 'Título do card de contato'),
            ('contato_descricao', 'Reservamos horários para família, gestantes, bebês, casais e retratos pessoais.', 'Subtítulo do card de contato'),
            ('contato_whatsapp', '(11) 98765-4321', 'WhatsApp para agendamentos'),
            ('contato_email', 'contato@casadafoto.com', 'E-mail oficial do estúdio'),
            ('sobre_tag', 'SOBRE O ESTÚDIO', 'Tag da seção Sobre'),
            ('sobre_titulo', 'Sobre a Casa da foto studio', 'Título da seção Sobre'),
            ('sobre_texto', 'Trabalhamos com ensaios pensados para capturar momentos reais, com um ambiente acolhedor e uma equipe preparada para tornar cada sessão tranquila e autêntica. Oferecemos opções para família, gestantes, bebês, casais e retratos pessoais, sempre com foco em luz natural, cenários personalizados e um atendimento atencioso.', 'Texto descritivo sobre o estúdio')
        ]
        cur.executemany("""
        INSERT OR IGNORE INTO site_textos (chave, valor, descricao) VALUES (?, ?, ?)
        """, textos_iniciais)

    conn.commit()
    conn.close()

def get_site_textos() -> dict:
    """Retorna todos os textos configuráveis do site como um dicionário chave -> valor."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chave, valor FROM site_textos")
    rows = cur.fetchall()
    conn.close()
    return {r['chave']: r['valor'] for r in rows}

def update_site_textos(novos_textos: dict) -> bool:
    """Atualiza ou insere textos no banco de dados com segurança."""
    conn = get_connection()
    cur = conn.cursor()
    for chave, valor in novos_textos.items():
        if isinstance(chave, str) and isinstance(valor, str):
            cur.execute("""
            INSERT INTO site_textos (chave, valor)
            VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
            """, (chave.strip(), valor.strip()))
    conn.commit()
    conn.close()
    return True

    print("Banco de dados SQLite inicializado com sucesso em:", DB_FILE)

if __name__ == "__main__":
    init_db()
