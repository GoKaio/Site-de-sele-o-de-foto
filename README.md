# Casa da Foto Studio 📸

> Plataforma web full-stack para gestão de ensaios fotográficos, seleção de fotos por clientes e portfólio público — desenvolvida com Python, Bottle e SQLite.

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.9+
- pip

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/casa-da-foto.git
cd casa-da-foto

# 2. Crie e ative um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações

# 5. Inicialize o banco de dados
python db.py

# 6. Inicie o servidor
python server.py
```

Acesse: **http://127.0.0.1:8082**

---

## 👥 Perfis de Acesso

| Perfil | URL de Login | Credenciais | Acesso |
|--------|-------------|-------------|--------|
| **Administrador** | `/admin-login.html` | `GoAdm` / `Go06190608*` | Painel de gestão do site |
| **Fotógrafo** | `/login-fotografo.html` | `contato@casadafoto.com` / `123456` | Kanban + Galerias |
| **Cliente** | `/login-cliente.html` | `cliente@exemplo.com` / `123456` | Seleção de fotos |

> ⚠️ **Altere as senhas padrão imediatamente após o primeiro deploy!**

---

## 🏗️ Arquitetura

```
casa-da-foto/
├── server.py          # API REST + servidor estático (Bottle)
├── db.py              # Banco SQLite + seeding + bcrypt
├── app.js             # Lógica frontend (RBAC + API calls)
├── styles.css         # Design system completo
├── index.html         # Site público
├── projetos.html      # Kanban do fotógrafo
├── admin.html         # Painel administrativo
├── admin-login.html   # Login do administrador
├── login.html         # Seleção de perfil
├── login-fotografo.html
├── login-cliente.html
├── escolha-fotos.html # Seleção de fotos (cliente)
├── galeria-*.html     # Telas do fotógrafo
├── assets/
│   ├── logo/logo.png
│   └── images/
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🔒 Segurança

| Camada | Implementação |
|--------|--------------|
| **Senhas** | Hash bcrypt (rounds=12) |
| **Rate Limiting** | 60 req/min geral · 5 req/min auth · Bloqueio 15min |
| **Security Headers** | X-Frame-Options, CSP, HSTS, X-Content-Type-Options |
| **CORS** | Whitelist de origens permitidas |
| **Input Validation** | Sanitização HTML, validação de e-mail, comprimento máximo |
| **Path Traversal** | Whitelist de extensões + bloqueio de `..` |
| **SQL Injection** | Parameterized queries em 100% das consultas |
| **Audit Log** | Registro de todos os logins e ações críticas |
| **Dados Sensíveis** | Banco de dados e `.env` no `.gitignore` |

Ver [SECURITY.md](SECURITY.md) para detalhes completos.

---

## 📡 API Endpoints

### Autenticação
| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/auth/login-admin` | Login administrativo |
| `POST` | `/api/auth/login-fotografo` | Login do fotógrafo |
| `POST` | `/api/auth/login-cliente` | Login do cliente |

### Projetos (Kanban)
| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/projetos` | Lista projetos |
| `POST` | `/api/projetos` | Cria projeto |
| `PUT` | `/api/projetos/:id/status` | Atualiza status |
| `DELETE` | `/api/projetos/:id` | Remove projeto |

### Galeria / Fotos
| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/galeria/:id/fotos` | Lista fotos |
| `POST` | `/api/galeria/:id/fotos/:fid/toggle` | Alterna status |
| `POST` | `/api/galeria/:id/enviar-selecao` | Envia seleção |

### Site Público (Admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| `GET/POST` | `/api/site/categorias` | Categorias |
| `DELETE` | `/api/site/categorias/:id` | Remove categoria |
| `GET/POST` | `/api/site/fotos` | Fotos do carrossel |
| `DELETE` | `/api/site/fotos/:id` | Remove foto |

---

## 🛡️ Controle de Acesso (RBAC)

```
Cliente      → escolha-fotos.html apenas
Fotógrafo    → projetos.html + galeria-*.html
Administrador → admin.html + acesso total
```

Implementado no `app.js` com verificação de `sessionStorage` em cada carregamento de página.

---

## 📦 Tecnologias

- **Backend:** Python 3.9+ · Bottle 0.13 · SQLite3
- **Segurança:** bcrypt · python-dotenv
- **Frontend:** HTML5 · Vanilla CSS · Vanilla JavaScript
- **Tipografia:** Inter (Google Fonts)

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE) para detalhes.
