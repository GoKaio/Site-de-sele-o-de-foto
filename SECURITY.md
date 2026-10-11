# Política de Segurança — Casa da Foto Studio

## Versão Suportada

| Versão | Suportada |
|--------|-----------|
| 1.x    | ✅ Sim     |

---

## Reportando Vulnerabilidades

Se você descobrir uma vulnerabilidade de segurança, **não abra uma issue pública**.

Por favor, envie um e-mail para: **contato@casadafoto.com**

Inclua:
1. Descrição da vulnerabilidade
2. Passos para reprodução
3. Impacto potencial
4. Sugestão de correção (se houver)

Você receberá uma resposta em até **72 horas**.

---

## Medidas de Segurança Implementadas

### 1. 🔐 Autenticação Segura
- Senhas armazenadas com **bcrypt (rounds=12)** — nunca em texto puro
- Delay anti-timing attack nas respostas de falha de autenticação (300ms)
- Bloqueio automático de conta após tentativas excessivas
- Registro de `ultimo_login` e `tentativas_login` por usuário

### 2. 🚦 Rate Limiting
- **60 requisições/minuto** por IP para rotas gerais
- **5 requisições/minuto** por IP para rotas de autenticação
- **Bloqueio de 15 minutos** após excesso de tentativas
- Log de auditoria para todos os bloqueios

### 3. 🛡️ Security Headers HTTP
Todos os responses incluem:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Strict-Transport-Security: max-age=31536000 (produção)
Cache-Control: no-store (rotas de API)
```

### 4. 🌐 CORS
- Whitelist explícita de origens permitidas
- Configurável via variável de ambiente `ALLOWED_ORIGINS`

### 5. 💉 Proteção contra SQL Injection
- **100% parameterized queries** — nunca concatenação de strings em SQL
- Foreign keys habilitadas (`PRAGMA foreign_keys=ON`)
- WAL mode para integridade do banco (`PRAGMA journal_mode=WAL`)

### 6. 🗂️ Proteção contra Path Traversal
- Validação de `..` em todos os caminhos de arquivo
- Whitelist de extensões permitidas para arquivos estáticos
- Bloqueio de acesso a `banco.db`, `.env`, `server.py`, `db.py`

### 7. ✅ Validação de Input
- Sanitização de todos os campos (remoção de tags HTML/script)
- Validação de formato de e-mail
- Limites de tamanho em todos os campos
- Validação de enums (status de projetos, status de fotos)
- Whitelist de caminhos de imagens

### 8. 📋 Log de Auditoria
Tabela `audit_log` registra:
- IP de origem
- Rota e método HTTP
- ID do usuário (quando autenticado)
- Ação executada
- Status HTTP
- Timestamp

Acessível em: `GET /api/admin/audit-log`

### 9. 🔒 Controle de Acesso (RBAC)
No frontend (`app.js`):
- **Cliente** → acesso restrito exclusivamente a `escolha-fotos.html`
- **Fotógrafo** → acesso a `projetos.html` e `galeria-*.html`
- **Administrador** → acesso a `admin.html` e funcionalidades de gestão

### 10. 🔑 Variáveis de Ambiente
- `SECRET_KEY` gerada com `secrets.token_hex(32)`
- Credenciais nunca hardcoded em código (lidas do `.env`)
- `.env` incluído no `.gitignore`

---

## Lista de Verificação para Deploy em Produção

- [ ] Alterar `ADMIN_SENHA_INICIAL` no `.env`
- [ ] Alterar senha do fotógrafo e cliente de exemplo
- [ ] Gerar `SECRET_KEY` única: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Definir `DEBUG=false`
- [ ] Configurar HTTPS (Nginx/Caddy como reverse proxy)
- [ ] Atualizar `ALLOWED_ORIGINS` com domínio real
- [ ] Configurar backup automático do `banco.db`
- [ ] Revisar `RATE_LIMIT_PER_MIN` e `RATE_LIMIT_AUTH_PER_MIN`
- [ ] Restringir permissões do arquivo `banco.db` (chmod 600)
- [ ] Monitorar `audit_log` periodicamente

---

## Histórico de Segurança

| Data | Versão | Descrição |
|------|--------|-----------|
| Out/2026 | 1.0 | Implementação inicial com bcrypt, rate limiting e security headers completos |
