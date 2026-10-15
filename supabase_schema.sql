-- ==============================================================================
-- CASA DA FOTO STUDIO - SCHEMA DEFINITIVO PARA SUPABASE (POSTGRESQL)
-- Gerado de acordo com as diretrizes de GUIA_VERCEL_SERVERLESS_E_SUPABASE.md
-- 
-- Inclui:
-- 1. Criação de todas as tabelas relacionais do sistema
-- 2. Índices de alta performance
-- 3. Row Level Security (RLS) ativado em todas as tabelas com políticas estritas
-- 4. Criação do bucket público de imagens 'casadafoto-uploads' no Supabase Storage
-- 5. Carga inicial (seed) do Administrador, Fotógrafo, Textos e Galerias
-- ==============================================================================

-- ── 1. EXTENSÕES ÚTEIS ────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 2. TABELAS DO SISTEMA ─────────────────────────────────────────────────────

-- 2.1 Usuários (Admin, Fotógrafo, Cliente)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('admin', 'fotografo', 'cliente')),
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE,
    login VARCHAR(100) UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    avatar TEXT,
    ativo SMALLINT DEFAULT 1,
    tentativas_login INTEGER DEFAULT 0,
    bloqueado_ate TIMESTAMP WITH TIME ZONE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ultimo_login TIMESTAMP WITH TIME ZONE
);

-- 2.2 Projetos (Kanban)
CREATE TABLE IF NOT EXISTS projetos (
    id SERIAL PRIMARY KEY,
    nome_cliente VARCHAR(150) NOT NULL,
    tipo_ensaio VARCHAR(100) NOT NULL,
    categoria_tag VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'novos' CHECK (status IN ('novos', 'andamento', 'revisao', 'entrega', 'finalizados', 'prova')),
    sessoes INTEGER DEFAULT 1,
    prazo VARCHAR(50),
    avatar_img TEXT,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.3 Galerias
CREATE TABLE IF NOT EXISTS galerias (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER REFERENCES projetos(id) ON DELETE SET NULL,
    nome VARCHAR(200) NOT NULL,
    categoria VARCHAR(100) DEFAULT 'Galeria demonstrativa',
    data_trabalho VARCHAR(50) DEFAULT '08/10/2026',
    exibicao VARCHAR(100) DEFAULT 'Ultra HD - 4K (3840 pixels)',
    idioma VARCHAR(50) DEFAULT 'Português (Brasil)',
    mensagem_acesso TEXT,
    permitir_comentarios SMALLINT DEFAULT 1,
    permitir_compartilhar SMALLINT DEFAULT 0,
    prazo_selecao VARCHAR(50) DEFAULT '20/10/2026',
    horario_prazo VARCHAR(10) DEFAULT '23:59',
    limite_pacote INTEGER DEFAULT 10,
    valor_foto_extra NUMERIC(10,2) DEFAULT 25.00,
    permitir_extras SMALLINT DEFAULT 1,
    confirmar_extras SMALLINT DEFAULT 1,
    tipo_acesso VARCHAR(50) DEFAULT 'convite',
    senha_galeria VARCHAR(100) DEFAULT 'casadafoto2026',
    marca_dagua SMALLINT DEFAULT 1,
    bloquear_clique SMALLINT DEFAULT 1,
    permitir_download SMALLINT DEFAULT 0,
    quando_disponibilizar VARCHAR(150) DEFAULT 'Após revisão e aprovação do fotógrafo',
    fotos_liberadas VARCHAR(150) DEFAULT 'Somente seleção aprovada',
    formato_download VARCHAR(100) DEFAULT 'JPEG - qualidade máxima',
    perfil_cor VARCHAR(50) DEFAULT 'sRGB',
    resolucao_download VARCHAR(100) DEFAULT 'Alta resolução - tamanho original',
    versao_redes SMALLINT DEFAULT 1,
    agrupar_zip SMALLINT DEFAULT 1,
    prazo_download_dias INTEGER DEFAULT 30,
    avisar_expirar SMALLINT DEFAULT 1,
    organizacao_fotos VARCHAR(50) DEFAULT 'Grade regular',
    espacamento VARCHAR(50) DEFAULT 'Confortável',
    exibir_numero SMALLINT DEFAULT 1,
    mostrar_boas_vindas SMALLINT DEFAULT 1,
    foto_capa TEXT DEFAULT 'Foto 001',
    estilo_capa VARCHAR(100) DEFAULT 'Foto e título lado a lado',
    enquadramento VARCHAR(100) DEFAULT 'Preservar imagem original',
    tema_visual VARCHAR(100) DEFAULT 'Casa da Foto - creme e bronze',
    tipografia VARCHAR(100) DEFAULT 'Inter - clara e acolhedora',
    link_drive TEXT DEFAULT '',
    status_galeria VARCHAR(100) DEFAULT 'Aguardando seleção',
    selecao_bloqueada SMALLINT DEFAULT 0,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.4 Fotos da Galeria
CREATE TABLE IF NOT EXISTS fotos (
    id SERIAL PRIMARY KEY,
    galeria_id INTEGER NOT NULL REFERENCES galerias(id) ON DELETE CASCADE,
    numero VARCHAR(50) NOT NULL,
    titulo VARCHAR(150),
    arquivo TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'nao_selecionada' CHECK (status IN ('pacote', 'extra', 'nao_selecionada')),
    ordem INTEGER DEFAULT 0,
    comentarios_count INTEGER DEFAULT 0
);

-- 2.5 Destinatários / Convites de Clientes
CREATE TABLE IF NOT EXISTS destinatarios (
    id SERIAL PRIMARY KEY,
    galeria_id INTEGER NOT NULL REFERENCES galerias(id) ON DELETE CASCADE,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    permissao VARCHAR(100) DEFAULT 'Apenas visualizar',
    principal SMALLINT DEFAULT 0,
    status_convite VARCHAR(100) DEFAULT 'Convite preparado',
    data_convite VARCHAR(50),
    ultimo_acesso VARCHAR(100) DEFAULT 'Aguardando acesso',
    total_acessos INTEGER DEFAULT 0,
    fotos_pacote_count INTEGER DEFAULT 0,
    fotos_extras_count INTEGER DEFAULT 0
);

-- 2.6 Histórico de Atividades e Auditoria da Galeria
CREATE TABLE IF NOT EXISTS atividades (
    id SERIAL PRIMARY KEY,
    galeria_id INTEGER NOT NULL REFERENCES galerias(id) ON DELETE CASCADE,
    data_hora VARCHAR(50) NOT NULL,
    autor_tipo VARCHAR(50) NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    descricao TEXT,
    dispositivo VARCHAR(50) DEFAULT 'Computador',
    tipo_badge VARCHAR(50) DEFAULT 'Fotógrafo',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.7 Mensagens de Contato Enviadas pelo Site Público
CREATE TABLE IF NOT EXISTS contatos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(50),
    tipo_ensaio VARCHAR(100),
    mensagem TEXT NOT NULL,
    lido SMALLINT DEFAULT 0,
    data_envio TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.8 Categorias do Site Público (Filtros do Carrossel)
CREATE TABLE IF NOT EXISTS site_categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.9 Fotos do Carrossel do Site Público
CREATE TABLE IF NOT EXISTS site_fotos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    categoria_nome VARCHAR(100) NOT NULL,
    arquivo TEXT NOT NULL,
    descricao TEXT,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.10 Pacotes de Ensaio do Site Público (Gerenciados pelo Admin)
CREATE TABLE IF NOT EXISTS site_pacotes (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descricao TEXT,
    imagem TEXT,
    valor VARCHAR(100) DEFAULT 'Consultar valores',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.11 Log de Auditoria de Segurança
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(45),
    rota VARCHAR(255),
    metodo VARCHAR(10),
    usuario_id INTEGER,
    acao VARCHAR(100),
    detalhe TEXT,
    status INTEGER,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.12 Textos Customizáveis da Tela Inicial
CREATE TABLE IF NOT EXISTS site_textos (
    chave VARCHAR(100) PRIMARY KEY,
    valor TEXT NOT NULL,
    descricao TEXT
);

-- 2.13 Categorias de Ensaios / Galerias
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2.14 Log de Erros do Sistema (Frontend e Backend)
CREATE TABLE IF NOT EXISTS error_log (
    id SERIAL PRIMARY KEY,
    origem VARCHAR(20) DEFAULT 'frontend',
    mensagem VARCHAR(500) NOT NULL,
    detalhe TEXT,
    rota VARCHAR(255),
    ip VARCHAR(50),
    user_agent VARCHAR(255),
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ── 3. ÍNDICES DE PERFORMANCE ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_usuarios_login ON usuarios(login);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_projetos_status ON projetos(status);
CREATE INDEX IF NOT EXISTS idx_galerias_projeto ON galerias(projeto_id);
CREATE INDEX IF NOT EXISTS idx_fotos_galeria ON fotos(galeria_id);
CREATE INDEX IF NOT EXISTS idx_destinatarios_galeria ON destinatarios(galeria_id);
CREATE INDEX IF NOT EXISTS idx_atividades_galeria ON atividades(galeria_id);
CREATE INDEX IF NOT EXISTS idx_site_fotos_cat ON site_fotos(categoria_nome);
CREATE INDEX IF NOT EXISTS idx_audit_ip ON audit_log(ip);
CREATE INDEX IF NOT EXISTS idx_error_log_criado ON error_log(criado_em);

-- ── 4. SUPABASE STORAGE (BUCKET PÚBLICO DE FOTOS E UPLOADS) ───────────────────
-- Insere o bucket 'casadafoto-uploads' no storage do Supabase caso ainda não exista
INSERT INTO storage.buckets (id, name, public)
VALUES ('casadafoto-uploads', 'casadafoto-uploads', true)
ON CONFLICT (id) DO NOTHING;

-- Política de leitura pública para o bucket de fotos
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' AND policyname = 'Permitir visualização pública de fotos e uploads'
    ) THEN
        CREATE POLICY "Permitir visualização pública de fotos e uploads"
        ON storage.objects FOR SELECT
        USING (bucket_id = 'casadafoto-uploads');
    END IF;
END $$;

-- Política de upload autenticado / backend
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'objects' AND policyname = 'Permitir upload para backend serverless'
    ) THEN
        CREATE POLICY "Permitir upload para backend serverless"
        ON storage.objects FOR INSERT
        WITH CHECK (bucket_id = 'casadafoto-uploads');
    END IF;
END $$;

-- ── 5. ROW LEVEL SECURITY (RLS) - SEÇÃO 3.5 DO GUIA ───────────────────────────
-- Habilita RLS em todas as tabelas
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE projetos ENABLE ROW LEVEL SECURITY;
ALTER TABLE galerias ENABLE ROW LEVEL SECURITY;
ALTER TABLE fotos ENABLE ROW LEVEL SECURITY;
ALTER TABLE destinatarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE atividades ENABLE ROW LEVEL SECURITY;
ALTER TABLE contatos ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_fotos ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_pacotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_textos ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;

-- 5.1 Políticas Públicas de Leitura (Site Visitante)
CREATE POLICY "Leitura pública de categorias site" ON site_categorias FOR SELECT USING (true);
CREATE POLICY "Leitura pública de categorias" ON categorias FOR SELECT USING (true);
CREATE POLICY "Gerenciamento total de categorias" ON categorias FOR ALL USING (true);
CREATE POLICY "Leitura pública de fotos do site" ON site_fotos FOR SELECT USING (true);
CREATE POLICY "Leitura pública de pacotes" ON site_pacotes FOR SELECT USING (true);
CREATE POLICY "Leitura pública de textos da home" ON site_textos FOR SELECT USING (true);

-- 5.2 Política Pública de Inserção de Contato
CREATE POLICY "Público pode enviar mensagem de contato" ON contatos FOR INSERT WITH CHECK (true);

-- 5.3 Políticas para Service Role (O Backend Serverless na Vercel opera com privilégio total)
CREATE POLICY "Service Role total usuarios" ON usuarios FOR ALL USING (true);
CREATE POLICY "Service Role total projetos" ON projetos FOR ALL USING (true);
CREATE POLICY "Service Role total galerias" ON galerias FOR ALL USING (true);
CREATE POLICY "Service Role total fotos" ON fotos FOR ALL USING (true);
CREATE POLICY "Service Role total destinatarios" ON destinatarios FOR ALL USING (true);
CREATE POLICY "Service Role total atividades" ON atividades FOR ALL USING (true);
CREATE POLICY "Service Role total contatos" ON contatos FOR ALL USING (true);
CREATE POLICY "Service Role total site_categorias" ON site_categorias FOR ALL USING (true);
CREATE POLICY "Service Role total site_fotos" ON site_fotos FOR ALL USING (true);
CREATE POLICY "Service Role total site_pacotes" ON site_pacotes FOR ALL USING (true);
CREATE POLICY "Service Role total site_textos" ON site_textos FOR ALL USING (true);
CREATE POLICY "Service Role total audit_log" ON audit_log FOR ALL USING (true);

-- ── 6. CARGA INICIAL (SEEDS DO SISTEMA) ───────────────────────────────────────

-- 6.1 Usuários Iniciais
-- Admin: login 'GoAdm', senha 'Go06190608*'
-- Fotógrafo: email 'contato@casadafoto.com', senha '123456'
-- Cliente: login 'cliente@exemplo.com', senha '123456'
INSERT INTO usuarios (tipo, nome, email, login, senha_hash, ativo) VALUES
('admin', 'Administrador Principal', 'admin@casadafoto.com', 'GoAdm', '$2b$12$oKOqTD2ZwW2NjFThzDXCsOG4MwxIkPmLOM7FKkfYZHc7khcDfcVqC', 1),
('fotografo', 'Fotógrafo Pro', 'contato@casadafoto.com', 'fotografo', '$2b$12$NnkphOz5A/XgX86t1Nzw7uKTuj4LElrdqFduZhVdj0WsB5IEVCGcS', 1),
('cliente', 'Cliente de Exemplo', 'cliente@exemplo.com', 'cliente@exemplo.com', '$2b$12$NnkphOz5A/XgX86t1Nzw7uKTuj4LElrdqFduZhVdj0WsB5IEVCGcS', 1)
ON CONFLICT (login) DO NOTHING;

-- 6.2 Textos da Tela Inicial
INSERT INTO site_textos (chave, valor, descricao) VALUES
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
ON CONFLICT (chave) DO NOTHING;

-- 6.3 Projetos Iniciais do Kanban
INSERT INTO projetos (nome_cliente, tipo_ensaio, categoria_tag, status, sessoes, prazo, avatar_img) VALUES
('Camila & Pedro', 'Ensaio Gestante', 'Gestante', 'novos', 1, 'sem prazo', 'assets/logo/logo.png'),
('Lucas', 'Acompanhamento', 'Bebê', 'andamento', 1, 'sem prazo', 'assets/logo/logo.png'),
('Nicoly', '15 anos', 'Retrato', 'andamento', 1, 'sem prazo', 'assets/logo/logo.png'),
('Família Silva', 'Ensaio Família', 'Família', 'andamento', 2, '15 nov', 'assets/logo/logo.png'),
('Bruna', 'Grávida revelação', 'Gestante', 'revisao', 1, 'sem prazo', 'assets/logo/logo.png'),
('Manu', 'Newborn', 'Bebê', 'revisao', 1, 'sem prazo', 'assets/logo/logo.png'),
('Rafael & Julia', 'Ensaio Casal', 'Casal', 'revisao', 2, '22 nov', 'assets/logo/logo.png'),
('Helena', 'Primeiro aninho', 'Bebê', 'entrega', 1, '30 nov', 'assets/logo/logo.png'),
('Mariana & João', 'Bodas de Prata', 'Família', 'finalizados', 1, 'concluído', 'assets/logo/logo.png');

-- 6.4 Galeria Inicial de Demonstração
INSERT INTO galerias (
    projeto_id, nome, categoria, data_trabalho, exibicao, idioma, mensagem_acesso,
    permitir_comentarios, permitir_compartilhar, prazo_selecao, horario_prazo,
    limite_pacote, permitir_extras, confirmar_extras, tipo_acesso, senha_galeria
) VALUES (
    5, 'Exemplo de seleção', 'Galeria demonstrativa', '08/10/2026',
    'Ultra HD - 4K (3840 pixels)', 'Português (Brasil)',
    'Olá! Seus momentos estão aqui. Escolha suas favoritas para o pacote e, se desejar, marque fotos extras. Com carinho, Casa da Foto Studio.',
    1, 0, '20/10/2026', '23:59', 10, 1, 1, 'convite', 'casadafoto2026'
);

-- 6.5 Destinatário Inicial da Galeria
INSERT INTO destinatarios (
    galeria_id, nome, email, permissao, principal, status_convite,
    data_convite, ultimo_acesso, total_acessos, fotos_pacote_count, fotos_extras_count
) VALUES (
    1, 'Cliente de exemplo', 'cliente@exemplo.com',
    'Apenas visualizar - sem alterar a escolha principal', 1, 'Convite acessado',
    '09 out. 2026 - 10:50', '10 out. - 14:18', 3, 6, 2
);

-- 6.6 Atividades Iniciais da Galeria
INSERT INTO atividades (galeria_id, data_hora, autor_tipo, titulo, descricao, dispositivo, tipo_badge) VALUES
(1, '10 OUT 2026 14:20', 'Fotógrafo', 'Preferências da galeria salvas', 'Prazo em 20/10, acesso privado e download bloqueado.', 'Computador', 'Fotógrafo'),
(1, '10 OUT 2026 14:18', 'Cliente', 'Escolha parcial atualizada', 'Fotos do pacote: 001–003, 005, 006, 009 e extras 004 e 008.', 'Computador', 'Cliente'),
(1, '10 OUT 2026 09:42', 'Cliente', 'Galeria acessada para revisão', 'Cliente retornou e continuou pelo celular.', 'Computador', 'Cliente'),
(1, '09 OUT 2026 10:50', 'Cliente', 'Primeiro acesso à galeria', 'Convite acessado pelo destinatário principal.', 'Computador', 'Cliente'),
(1, '08 OUT 2026 15:00', 'Fotógrafo', 'Convite registrado', 'Convite no sistema para cliente@exemplo.com.', 'Computador', 'Fotógrafo');

-- 6.7 Categorias Padrão para Galerias e Ensaios
INSERT INTO categorias (nome) VALUES
('Galeria demonstrativa'),
('Ensaio Família'),
('Gestante'),
('Newborn'),
('Casamento'),
('Aniversário / 15 Anos'),
('Formatura'),
('Ensaio Casal'),
('Retrato Profissional'),
('Smash the Cake'),
('Batizado'),
('Eventos / Festas')
ON CONFLICT (nome) DO NOTHING;

-- ==============================================================================
-- FIM DO SCRIPT DE MIGRAÇÃO DO SUPABASE
-- Execute este script no SQL Editor do seu Dashboard Supabase
-- ==============================================================================
