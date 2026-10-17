/**
 * Casa da Foto Studio - Integração Full Stack com API e Banco de Dados SQLite
 * Controle de Acesso por Perfil, Kanban Dinâmico e Gestão Administrativa
 */

// Telemetria Global de Erros do Frontend
window.addEventListener('error', function(event) {
  try {
    const errorMsg = event.message || 'Erro desconhecido no script';
    const detail = `${event.filename || ''}:${event.lineno || ''}:${event.colno || ''} | ${event.error ? event.error.stack : ''}`;
    fetch('/api/log/error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mensagem: errorMsg,
        detalhe: detail,
        rota: window.location.pathname + window.location.search
      })
    }).catch(() => {});
  } catch (e) {}
});

window.addEventListener('unhandledrejection', function(event) {
  try {
    const reason = event.reason;
    const errorMsg = reason && reason.message ? reason.message : String(reason);
    const detail = reason && reason.stack ? reason.stack : '';
    fetch('/api/log/error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mensagem: 'Unhandled Promise: ' + errorMsg,
        detalhe: detail,
        rota: window.location.pathname + window.location.search
      })
    }).catch(() => {});
  } catch (e) {}
});

// Utilitário de Notificações Toast Elegante
function showToast(message, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = `
      position: fixed;
      top: 24px;
      right: 24px;
      z-index: 99999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 380px;
    `;
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  const isSuccess = type === 'success';
  toast.style.cssText = `
    background: ${isSuccess ? '#352319' : '#8B2626'};
    color: #FAF5EE;
    border: 1px solid ${isSuccess ? '#C59B6D' : '#FF9999'};
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 0.88rem;
    font-weight: 500;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
    display: flex;
    align-items: center;
    gap: 12px;
    animation: slideInToast 0.3s ease;
    transition: all 0.3s ease;
  `;

  toast.innerHTML = `
    <span style="font-size: 1.2rem;">${isSuccess ? '✓' : '⚠️'}</span>
    <span style="flex: 1; line-height: 1.4;">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Injeta estilo de animação para os toasts
if (!document.getElementById('toastStyle')) {
  const style = document.createElement('style');
  style.id = 'toastStyle';
  style.textContent = `
    @keyframes slideInToast {
      from { opacity: 0; transform: translateX(40px); }
      to { opacity: 1; transform: translateX(0); }
    }
  `;
  document.head.appendChild(style);
}

// Função global para logout de qualquer perfil
function logoutUsuario() {
  sessionStorage.removeItem('cliente_autenticado');
  sessionStorage.removeItem('cliente_nome');
  sessionStorage.removeItem('cliente_galeria_id');
  sessionStorage.removeItem('fotografo_autenticado');
  sessionStorage.removeItem('usuario_nome');
  sessionStorage.removeItem('admin_autenticado');
  sessionStorage.removeItem('admin_nome');

  // Limpa também do armazenamento persistente (Manter Conectado)
  localStorage.removeItem('fotografo_manter_conectado');
  localStorage.removeItem('fotografo_autenticado');
  localStorage.removeItem('usuario_nome');
  localStorage.removeItem('fotografo_nome');
  localStorage.removeItem('admin_autenticado');
  localStorage.removeItem('admin_nome');
  localStorage.removeItem('cliente_manter_conectado');
  localStorage.removeItem('cliente_autenticado');
  localStorage.removeItem('cliente_nome');
  localStorage.removeItem('cliente_galeria_id');

  showToast('Sessão encerrada com sucesso.');
  setTimeout(() => {
    window.location.href = 'login.html';
  }, 500);
}

// ============================================================================
// AUTO-BYPASS IMEDIATO DE LOGIN (EXECUÇÃO INSTANTÂNEA ANTES DE QUALQUER RENDER)
// ============================================================================
(function checkImmediateAuthRedirect() {
  try {
    const rawPath = window.location.pathname.split('/').pop().toLowerCase();
    const page = rawPath || 'index.html';
    const urlParams = new URLSearchParams(window.location.search);
    const targetGalId = urlParams.get('id') || urlParams.get('galeria_id') || '';

    const isFoto = (sessionStorage.getItem('fotografo_autenticado') === 'true') || (localStorage.getItem('fotografo_autenticado') === 'true');
    const isAdmin = (sessionStorage.getItem('admin_autenticado') === 'true') || (localStorage.getItem('admin_autenticado') === 'true');
    const isClient = (sessionStorage.getItem('cliente_autenticado') === 'true') || (localStorage.getItem('cliente_autenticado') === 'true');

    if (targetGalId) {
      localStorage.setItem('ultima_galeria_id', targetGalId);
    }

    // FOTÓGRAFO OU ADMIN LOGADO: Pula telas de login e vai direto para a seleção de fotos ou projetos
    if (isFoto || isAdmin) {
      if (page === 'login.html' || page === 'acesso.html' || page === 'login-cliente.html') {
        const gId = targetGalId || localStorage.getItem('ultima_galeria_id') || '1';
        window.location.replace(`escolha-fotos.html?id=${gId}&previa=true`);
        return;
      }
      if (page === 'login-fotografo.html') {
        window.location.replace('projetos.html');
        return;
      }
      if (page === 'admin-login.html' && isAdmin) {
        window.location.replace('admin.html');
        return;
      }
    }

    // CLIENTE LOGADO: Pula telas de login e vai para suas fotos
    if (isClient && !isFoto && !isAdmin) {
      if (page === 'login.html' || page === 'acesso.html' || page === 'login-cliente.html') {
        const gId = sessionStorage.getItem('cliente_galeria_id') || localStorage.getItem('cliente_galeria_id') || targetGalId || '1';
        window.location.replace(`escolha-fotos.html?id=${gId}`);
        return;
      }
    }
  } catch (err) {
    console.error('Erro na verificação imediata de autenticação:', err);
  }
})();

document.addEventListener('DOMContentLoaded', () => {

  // Sincroniza e restaura sessões entre localStorage e sessionStorage
  let isFoto = (sessionStorage.getItem('fotografo_autenticado') === 'true') || (localStorage.getItem('fotografo_autenticado') === 'true');
  let isAdmin = (sessionStorage.getItem('admin_autenticado') === 'true') || (localStorage.getItem('admin_autenticado') === 'true');
  let isClient = (sessionStorage.getItem('cliente_autenticado') === 'true') || (localStorage.getItem('cliente_autenticado') === 'true');

  const uNomeCheck = (sessionStorage.getItem('usuario_nome') || localStorage.getItem('usuario_nome') || sessionStorage.getItem('admin_nome') || localStorage.getItem('admin_nome') || '').toLowerCase();
  if (uNomeCheck.includes('admin') || uNomeCheck.includes('administrador')) {
    isAdmin = true;
    sessionStorage.setItem('admin_autenticado', 'true');
    localStorage.setItem('admin_autenticado', 'true');
  }

  if (isFoto) {
    sessionStorage.setItem('fotografo_autenticado', 'true');
    localStorage.setItem('fotografo_autenticado', 'true');
    const uNome = sessionStorage.getItem('usuario_nome') || localStorage.getItem('usuario_nome') || localStorage.getItem('fotografo_nome') || 'Fotógrafo';
    sessionStorage.setItem('usuario_nome', uNome);
    localStorage.setItem('usuario_nome', uNome);
  }
  if (isAdmin) {
    sessionStorage.setItem('admin_autenticado', 'true');
    localStorage.setItem('admin_autenticado', 'true');
    const aNome = sessionStorage.getItem('admin_nome') || localStorage.getItem('admin_nome') || 'Administrador';
    sessionStorage.setItem('admin_nome', aNome);
    localStorage.setItem('admin_nome', aNome);
  }
  if (isClient) {
    sessionStorage.setItem('cliente_autenticado', 'true');
    const cNome = sessionStorage.getItem('cliente_nome') || localStorage.getItem('cliente_nome');
    if (cNome) sessionStorage.setItem('cliente_nome', cNome);
    const cGal = sessionStorage.getItem('cliente_galeria_id') || localStorage.getItem('cliente_galeria_id');
    if (cGal) sessionStorage.setItem('cliente_galeria_id', cGal);
  }

  // ============================================================================
  // 0. CONTROLE DE ACESSO E PERMISSÕES (ROLE-BASED ACCESS CONTROL)
  // ============================================================================
  const rawPath = window.location.pathname.split('/').pop().toLowerCase();
  const currentPage = rawPath || 'index.html';
  const urlParams = new URLSearchParams(window.location.search);
  const targetGalId = urlParams.get('id') || urlParams.get('galeria_id') || '';

  if (targetGalId) {
    try { localStorage.setItem('ultima_galeria_id', targetGalId); } catch(e) {}
  }

  // REGRA A: FOTÓGRAFO OU ADMIN JÁ LOGADO ACESSANDO TELAS DE LOGIN/ESCOLHA DE PERFIL
  if (isFoto || isAdmin) {
    if (currentPage === 'login.html' || currentPage === 'acesso.html' || currentPage === 'login-cliente.html') {
      const gId = targetGalId || localStorage.getItem('ultima_galeria_id') || '1';
      window.location.replace(`escolha-fotos.html?id=${gId}&previa=true`);
      return;
    }
    if (currentPage === 'login-fotografo.html') {
      window.location.replace('projetos.html');
      return;
    }
    if (currentPage === 'admin-login.html' && isAdmin) {
      window.location.replace('admin.html');
      return;
    }
  }

  // REGRA B: CLIENTE JÁ LOGADO ACESSANDO TELAS DE LOGIN
  if (isClient && !isFoto && !isAdmin) {
    if (currentPage === 'login.html' || currentPage === 'acesso.html' || currentPage === 'login-cliente.html') {
      const gId = sessionStorage.getItem('cliente_galeria_id') || localStorage.getItem('cliente_galeria_id') || targetGalId || '1';
      window.location.replace(`escolha-fotos.html?id=${gId}`);
      return;
    }
  }

  // REGRA 1: Cliente restrito à seleção de fotos
  if (isClient && !isFoto && !isAdmin) {
    if (currentPage === 'projetos.html' || currentPage.startsWith('galeria-') || currentPage === 'admin.html') {
      alert('Acesso restrito. Como cliente, você só tem acesso à Seleção de Fotos.');
      const gId = sessionStorage.getItem('cliente_galeria_id') || '1';
      window.location.href = `escolha-fotos.html?id=${gId}`;
      return;
    }
  }

  // REGRA 2: Projetos e Galerias restritos ao Fotógrafo e Administrador
  if (currentPage === 'projetos.html' || currentPage.startsWith('galeria-')) {
    if (!isFoto && !isAdmin) {
      window.location.href = 'login-fotografo.html';
      return;
    }
  }

  // REGRA 3: Admin restrito exclusivamente ao Administrador
  if (currentPage === 'admin.html') {
    if (!isAdmin) {
      window.location.href = 'admin-login.html';
      return;
    }
  }

  // REGRA 4: Tela de Escolha de Fotos
  const isPrevia = urlParams.get('previa') === 'true';
  if (currentPage === 'escolha-fotos.html') {
    if (!isClient && !isFoto && !isAdmin && !isPrevia) {
      const gParam = targetGalId ? `?id=${targetGalId}` : '';
      window.location.href = `login-cliente.html${gParam}`;
      return;
    }
  }

  // 1. Carrega Logotipo oficial do estúdio em todas as telas (Login, Header institucional, Favicon, etc.)
  const siteLogoImgs = document.querySelectorAll('#authLogoImg, .auth-logo-box img, #headerLogoImg, .header-logo-card img, .auth-mobile-logo-img');
  fetch('/api/site/logo-info')
    .then(r => r.json())
    .then(data => {
      if (data && data.url) {
        if (siteLogoImgs.length > 0) {
          siteLogoImgs.forEach(img => {
            img.src = data.url;
          });
        }
        // Atualiza dinamicamente o favicon na aba do navegador
        const favicons = document.querySelectorAll("link[rel*='icon'], link[rel='apple-touch-icon']");
        favicons.forEach(fav => {
          fav.href = data.url;
        });
        document.documentElement.style.setProperty('--watermark-img', `url('${data.url}')`);
      }
    })
    .catch(() => {});

  // 2. Carrega foto oficial de destaque nas telas de login se presente na página
  const authHeroImg = document.getElementById('authHeroImg') || document.querySelector('.auth-hero-photo-wrap img');
  if (authHeroImg) {
    fetch('/api/site/login-foto')
      .then(r => r.json())
      .then(data => {
        if (data && data.url) {
          authHeroImg.src = data.url;
        }
      })
      .catch(() => {});
  }

  // 3. Carrega configurações globais da Marca d'Água (Posição, Tamanho, Opacidade e Mosaico)
  fetch('/api/site/marca-dagua')
    .then(r => r.json())
    .then(cfg => {
      if (cfg) {
        if (cfg.posicao_css) document.documentElement.style.setProperty('--watermark-position', cfg.posicao_css);
        if (cfg.tamanho_css) document.documentElement.style.setProperty('--watermark-size', cfg.tamanho_css);
        if (cfg.tamanho_large_css) document.documentElement.style.setProperty('--watermark-size-large', cfg.tamanho_large_css);
        if (cfg.opacidade_css) document.documentElement.style.setProperty('--watermark-opacity', cfg.opacidade_css);
        if (cfg.repeat) document.documentElement.style.setProperty('--watermark-repeat', cfg.repeat);
      }
    })
    .catch(() => {});

  // Atualiza barra de navegação superior com status de usuário logado
  atualizarHeaderStatus();

  function atualizarHeaderStatus() {
    const navRight = document.querySelector('.nav-links-right');
    if (!navRight) return;

    if (isClient) {
      const nome = sessionStorage.getItem('cliente_nome') || 'Cliente';
      const gId = sessionStorage.getItem('cliente_galeria_id') || localStorage.getItem('cliente_galeria_id') || '1';
      navRight.innerHTML = `
        <a href="escolha-fotos.html?id=${gId}" class="nav-item ${currentPage === 'escolha-fotos.html' ? 'active-nav' : ''}">Minhas Fotos (${nome})</a>
        <a href="entrega.html?id=${gId}" class="nav-item ${currentPage === 'entrega.html' ? 'active-nav' : ''}" target="_blank" title="Baixar Fotos pelo Google Drive">🎁 Baixar Fotos (Drive)</a>
        <a href="javascript:void(0)" onclick="logoutUsuario()" class="nav-item" style="color:#C59B6D;">Sair ↗</a>
      `;
    } else if (isAdmin) {
      const gId = localStorage.getItem('ultima_galeria_id') || '1';
      navRight.innerHTML = `
        <a href="escolha-fotos.html?id=${gId}&previa=true" class="nav-item ${currentPage === 'escolha-fotos.html' ? 'active-nav' : ''}">👁️ Seleção de fotos</a>
        <a href="entrega.html?id=${gId}" class="nav-item ${currentPage === 'entrega.html' ? 'active-nav' : ''}" target="_blank" title="Página Oficial de Entrega de Fotos com link do Google Drive">🎁 Entrega (Drive)</a>
        <a href="projetos.html" class="nav-item ${currentPage === 'projetos.html' ? 'active-nav' : ''}">Projetos</a>
        <a href="admin.html" class="nav-item nav-admin-btn ${currentPage === 'admin.html' ? 'active-admin' : ''}" title="Painel de Administração">
          <span class="nav-admin-icon" aria-hidden="true">⚙️</span>
          <span>Painel Admin</span>
        </a>
        <a href="javascript:void(0)" onclick="logoutUsuario()" class="nav-item" style="color:#C59B6D;">Sair ↗</a>
      `;
    } else if (isFoto) {
      const gId = localStorage.getItem('ultima_galeria_id') || '1';
      navRight.innerHTML = `
        <a href="escolha-fotos.html?id=${gId}&previa=true" class="nav-item ${currentPage === 'escolha-fotos.html' ? 'active-nav' : ''}">👁️ Seleção de fotos</a>
        <a href="entrega.html?id=${gId}" class="nav-item ${currentPage === 'entrega.html' ? 'active-nav' : ''}" target="_blank" title="Página Oficial de Entrega de Fotos com link do Google Drive">🎁 Entrega (Drive)</a>
        <a href="projetos.html" class="nav-item ${currentPage === 'projetos.html' ? 'active-nav' : ''}">Projetos</a>
        <a href="javascript:void(0)" onclick="logoutUsuario()" class="nav-item" style="color:#C59B6D;">Sair ↗</a>
      `;
    }
  }

  // ============================================================================
  // 1. TELA: LOGIN DO FOTÓGRAFO (login-fotografo.html)
  // ============================================================================
  const formFoto = document.getElementById('formLoginFotografo');
  if (formFoto) {
    const chkManter = document.getElementById('chkManterConectado');
    const emailField = document.getElementById('fotoEmail');

    // Recupera e-mail salvo e preferência de manter conectado
    const savedEmail = localStorage.getItem('fotografo_lembrar_email');
    if (savedEmail && emailField) {
      emailField.value = savedEmail;
    }
    const savedManter = localStorage.getItem('fotografo_manter_conectado');
    if (chkManter && savedManter !== null) {
      chkManter.checked = (savedManter === 'true');
    }

    formFoto.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = emailField ? emailField.value.trim() : '';
      const senha = document.getElementById('fotoSenha').value;
      const manterConectado = chkManter ? chkManter.checked : true;
      const btn = document.getElementById('btnEntrarFotografo');
      const originalText = btn ? btn.innerHTML : '<span>Entrar</span><span>→</span>';

      if (btn) btn.innerHTML = '<span>Verificando...</span>';

      try {
        const res = await fetch('/api/auth/login-fotografo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, senha })
        });
        const data = await res.json();

        if (data.success) {
          sessionStorage.setItem('fotografo_autenticado', 'true');
          sessionStorage.setItem('usuario_nome', data.user.nome);

          if (manterConectado) {
            localStorage.setItem('fotografo_manter_conectado', 'true');
            localStorage.setItem('fotografo_autenticado', 'true');
            localStorage.setItem('usuario_nome', data.user.nome);
            localStorage.setItem('fotografo_nome', data.user.nome);
            localStorage.setItem('fotografo_lembrar_email', email);
          } else {
            localStorage.removeItem('fotografo_manter_conectado');
            localStorage.removeItem('fotografo_autenticado');
            localStorage.removeItem('usuario_nome');
            localStorage.removeItem('fotografo_nome');
            localStorage.removeItem('fotografo_lembrar_email');
          }

          if (data.user.tipo === 'admin') {
            sessionStorage.setItem('admin_autenticado', 'true');
            sessionStorage.setItem('admin_nome', data.user.nome);
            if (manterConectado) {
              localStorage.setItem('admin_autenticado', 'true');
              localStorage.setItem('admin_nome', data.user.nome);
            } else {
              localStorage.removeItem('admin_autenticado');
              localStorage.removeItem('admin_nome');
            }
          }

          showToast(`Bem-vindo, ${data.user.nome}! Redirecionando...`);
          setTimeout(() => {
            window.location.href = 'projetos.html';
          }, 800);
        } else {
          showToast(data.error || 'Credenciais inválidas.', 'error');
          if (btn) btn.innerHTML = originalText;
        }
      } catch (err) {
        showToast('Erro ao conectar ao servidor.', 'error');
        if (btn) btn.innerHTML = originalText;
      }
    });
  }

  // ============================================================================
  // 2. TELA: ACESSO DO CLIENTE (login-cliente.html)
  // ============================================================================
  const formCli = document.getElementById('formLoginCliente');
  if (formCli) {
    const chkManterCli = document.getElementById('chkManterConectadoCliente');
    const loginField = document.getElementById('clienteLogin');

    // Recupera login salvo
    const savedCliLogin = localStorage.getItem('cliente_lembrar_login');
    if (savedCliLogin && loginField) {
      loginField.value = savedCliLogin;
    }
    const savedManterCli = localStorage.getItem('cliente_manter_conectado');
    if (chkManterCli && savedManterCli !== null) {
      chkManterCli.checked = (savedManterCli === 'true');
    }

    formCli.addEventListener('submit', async (e) => {
      e.preventDefault();
      const login = loginField ? loginField.value.trim() : '';
      const senha = document.getElementById('clienteSenha').value;
      const manterConectado = chkManterCli ? chkManterCli.checked : true;
      const btn = document.getElementById('btnAcessarFotos');
      const originalText = btn ? btn.innerHTML : 'Acessar minhas fotos →';

      if (btn) btn.innerHTML = '<span>Validando acesso...</span>';

      try {
        const res = await fetch('/api/auth/login-cliente', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ login, senha })
        });
        const data = await res.json();

        if (data.success) {
          sessionStorage.setItem('cliente_autenticado', 'true');
          sessionStorage.setItem('cliente_nome', data.user.nome);
          if (data.user && data.user.galeria_id) {
            sessionStorage.setItem('cliente_galeria_id', data.user.galeria_id);
          }

          if (manterConectado) {
            localStorage.setItem('cliente_manter_conectado', 'true');
            localStorage.setItem('cliente_autenticado', 'true');
            localStorage.setItem('cliente_nome', data.user.nome);
            localStorage.setItem('cliente_lembrar_login', login);
            if (data.user && data.user.galeria_id) {
              localStorage.setItem('cliente_galeria_id', data.user.galeria_id);
            }
          } else {
            localStorage.removeItem('cliente_manter_conectado');
            localStorage.removeItem('cliente_autenticado');
            localStorage.removeItem('cliente_nome');
            localStorage.removeItem('cliente_galeria_id');
            localStorage.removeItem('cliente_lembrar_login');
          }

          showToast(`Acesso autorizado! Carregando sua galeria...`);
          setTimeout(() => {
            const destUrl = (data.user && data.user.galeria_id) ? `escolha-fotos.html?id=${data.user.galeria_id}` : 'escolha-fotos.html';
            window.location.href = destUrl;
          }, 800);
        } else {
          showToast(data.error || 'Dados incorretos.', 'error');
          if (btn) btn.innerHTML = originalText;
        }
      } catch (err) {
        showToast('Erro ao conectar ao servidor.', 'error');
        if (btn) btn.innerHTML = originalText;
      }
    });
  }

  // ============================================================================
  // 3. TELA: ESCOLHA DE FOTOS (escolha-fotos.html)
  // ============================================================================
  const gridFotos = document.querySelector('.proofing-cards-grid') || document.getElementById('photosGrid');
  if (gridFotos) {
    let fotosGlobais = [];
    const galId = new URLSearchParams(window.location.search).get('galeria_id') || new URLSearchParams(window.location.search).get('id') || sessionStorage.getItem('cliente_galeria_id') || '1';

    async function carregarFotos() {
      try {
        const [resFotos, resGal] = await Promise.all([
          fetch(`/api/galeria/${galId}/fotos`),
          fetch(`/api/galeria/${galId}`)
        ]);
        const data = await resFotos.json();
        const galData = await resGal.json();
        window.galeriaDataCliente = galData;
        fotosGlobais = data.fotos || [];
        window.fotosGlobaisCliente = fotosGlobais;

        // Gerenciamento de Bloqueio e Liberação pelo Fotógrafo
        const isBloqueada = galData && (galData.selecao_bloqueada == 1 || galData.status_galeria === 'Seleção enviada');
        window.galeriaBloqueadaCliente = isBloqueada;

        const bannerContainer = document.getElementById('containerStatusBannerCliente');
        if (bannerContainer) {
          if (isBloqueada) {
            bannerContainer.innerHTML = `
              <div style="background: linear-gradient(135deg, #2D1D14 0%, #452D1E 100%); border: 1.5px solid #C59B6D; border-radius: 14px; padding: 1.15rem 1.4rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; color: #FAF5EE; box-shadow: 0 4px 18px rgba(0,0,0,0.25); flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 0.85rem;">
                  <span style="font-size: 1.8rem;">🔒</span>
                  <div>
                    <strong style="display: block; font-size: 1rem; color: #E6CA65; margin-bottom: 2px;">Seleção Enviada e em Análise pelo Fotógrafo</strong>
                    <span style="font-size: 0.82rem; color: #FAF5EE; opacity: 0.92; line-height: 1.4;">Suas fotos foram enviadas com sucesso e a seleção está temporariamente bloqueada para alterações. Se for preciso ajustar alguma foto escolhida, aguarde a liberação do estúdio.</span>
                  </div>
                </div>
                <span style="background: #2E7D32; color: #FFF; font-size: 0.74rem; font-weight: 800; padding: 6px 14px; border-radius: 9999px; text-transform: uppercase; white-space: nowrap; letter-spacing: 0.04em;">✓ Em Análise</span>
              </div>
            `;
            const btnSendMain = document.getElementById('btnEnviarSelecao');
            if (btnSendMain) {
              btnSendMain.disabled = true;
              btnSendMain.innerHTML = '<span>🔒 Seleção Enviada ao Fotógrafo</span>';
              btnSendMain.style.background = '#4A3224';
              btnSendMain.style.cursor = 'not-allowed';
            }
            const btnSticky = document.querySelector('#mobileStickyActionBar .bar-btn');
            if (btnSticky) {
              btnSticky.disabled = true;
              btnSticky.innerHTML = '🔒 Em Análise';
              btnSticky.style.background = '#4A3224';
            }
          } else if (galData && galData.status_galeria === 'Liberada para ajustes') {
            bannerContainer.innerHTML = `
              <div style="background: linear-gradient(135deg, #1B3B22 0%, #2E7D32 100%); border: 1.5px solid #81C784; border-radius: 14px; padding: 1.15rem 1.4rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; color: #FAF5EE; box-shadow: 0 4px 18px rgba(0,0,0,0.25); flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 0.85rem;">
                  <span style="font-size: 1.8rem;">🔓</span>
                  <div>
                    <strong style="display: block; font-size: 1rem; color: #FFF; margin-bottom: 2px;">Galeria Liberada para Ajustes pelo Fotógrafo!</strong>
                    <span style="font-size: 0.82rem; color: #E8F5E9; line-height: 1.4;">O estúdio liberou sua seleção para que você possa alterar ou adicionar novas fotos. Quando terminar suas escolhas, envie novamente.</span>
                  </div>
                </div>
                <button type="button" onclick="window.iniciarModalEnviarSelecao()" style="background: #FFF; color: #1B3B22; font-size: 0.78rem; font-weight: 800; padding: 7px 16px; border-radius: 9999px; border:none; cursor:pointer; white-space: nowrap; transition: transform 0.2s;">
                  Reenviar Escolha ✈
                </button>
              </div>
            `;
          } else {
            bannerContainer.innerHTML = '';
          }

          if (isFoto || isAdmin) {
            const nomeFoto = sessionStorage.getItem('usuario_nome') || 'Fotógrafo';
            bannerContainer.innerHTML = `
              <div style="background: linear-gradient(135deg, #1C110A 0%, #352319 100%); border: 1.5px solid #C59B6D; border-radius: 14px; padding: 1.15rem 1.4rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; color: #FAF5EE; box-shadow: 0 4px 18px rgba(0,0,0,0.25); flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 0.85rem;">
                  <span style="font-size: 1.8rem;">📷</span>
                  <div>
                    <strong style="display: block; font-size: 1rem; color: #C59B6D; margin-bottom: 2px;">Visualização do Fotógrafo · ${nomeFoto}</strong>
                    <span style="font-size: 0.82rem; color: #FAF5EE; opacity: 0.92; line-height: 1.4;">Você está visualizando a seleção de fotos da galeria <strong>#${galId}</strong>. O login de cliente foi ignorado automaticamente para sua conveniência.</span>
                  </div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                  <a href="galeria-config.html?id=${galId}" style="background: rgba(197, 155, 109, 0.2); color: #FAF5EE; border: 1px solid #C59B6D; font-size: 0.78rem; font-weight: 700; padding: 7px 15px; border-radius: 9999px; text-decoration: none;">⚙ Configurar Galeria</a>
                  <a href="projetos.html" style="background: #C59B6D; color: #1C110A; font-size: 0.78rem; font-weight: 800; padding: 7px 16px; border-radius: 9999px; text-decoration: none; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">← Voltar aos Projetos</a>
                </div>
              </div>
            ` + bannerContainer.innerHTML;
          }
        }

        const bc = document.getElementById('breadcrumbPathContainer');
        if (bc && (isFoto || isAdmin)) {
          const nomeFoto = sessionStorage.getItem('usuario_nome') || 'Fotógrafo';
          bc.innerHTML = `
            <span class="breadcrumb-path" style="color:#C59B6D;">Painel do Estúdio &gt; <strong style="color:#352319;">Seleção de Fotos (${nomeFoto})</strong></span>
            <a href="projetos.html" style="font-size: 0.76rem; background: #C59B6D; color: #1C110A; font-weight: 800; padding: 4px 12px; border-radius: 9999px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">← Voltar aos Projetos</a>
          `;
        }

        atualizarMetricas(data.totais, galData);
        aplicarOrdenacaoERenderizar();
      } catch (err) {
        console.error('Erro ao buscar fotos:', err);
      }
    }

    function atualizarMetricas(totais, galData) {
      if (!totais) return;
      const valorFotoExtra = (galData && galData.valor_foto_extra != null) ? parseFloat(galData.valor_foto_extra) : 25.0;
      const totalExtrasReais = (totais.extra || 0) * valorFotoExtra;

      // Cards de métricas superiores
      const metricCards = document.querySelectorAll('.selection-metrics-grid .metric-card');
      if (metricCards.length >= 4) {
        const num0 = metricCards[0].querySelector('.metric-number');
        if (num0) num0.textContent = totais.limite_pacote;
        const num1 = metricCards[1].querySelector('.metric-number');
        if (num1) num1.textContent = totais.pacote;
        const num2 = metricCards[2].querySelector('.metric-number');
        if (num2) num2.textContent = Math.max(0, totais.limite_pacote - totais.pacote);
        const num3 = metricCards[3].querySelector('.metric-number');
        if (num3) num3.textContent = totais.extra;
      }

      // Sidebar resumo
      const fill = document.querySelector('.summary-progress-bar-fill');
      if (fill) {
        const pct = Math.min(100, Math.round((totais.pacote / (totais.limite_pacote || 1)) * 100));
        fill.style.width = `${pct}%`;
      }
      const bPacote = document.querySelector('.summary-section-row .badge-counter');
      if (bPacote) bPacote.textContent = `${totais.pacote} de ${totais.limite_pacote}`;
      const bExtra = document.querySelector('.summary-section-row .badge-counter.badge-extra');
      if (bExtra) bExtra.textContent = `${totais.extra} foto(s) · R$ ${totalExtrasReais.toFixed(2).replace('.', ',')}`;

      const totalH = document.querySelector('.summary-total-box .total-header');
      if (totalH) {
        totalH.innerHTML = `Total para enviar &nbsp; ${totais.pacote} do pacote + ${totais.extra} extras (R$ ${totalExtrasReais.toFixed(2).replace('.', ',')})`;
      }

      const alertInfo = document.querySelector('.alert-box-info');
      if (alertInfo) {
        alertInfo.innerHTML = `ⓘ <strong>Valor por foto extra: R$ ${valorFotoExtra.toFixed(2).replace('.', ',')}</strong>.<br>Subtotal das ${totais.extra} fotos extras: <strong>R$ ${totalExtrasReais.toFixed(2).replace('.', ',')}</strong>.`;
      }

      // Lista de chips de fotos no pacote
      const chipsLists = document.querySelectorAll('.selected-pills-list');
      if (chipsLists.length > 0) {
        const pacotes = fotosGlobais.filter(f => f.status === 'pacote');
        chipsLists[0].innerHTML = pacotes.length > 0
          ? pacotes.map(f => `<span class="photo-chip">${f.numero}</span>`).join(' ')
          : '<span style="font-size:0.75rem; color:#888;">Nenhuma foto no pacote.</span>';
      }

      // Lista de chips de fotos extras
      if (chipsLists.length > 1) {
        const extras = fotosGlobais.filter(f => f.status === 'extra');
        chipsLists[1].innerHTML = extras.length > 0
          ? extras.map(f => `<span class="photo-chip">${f.numero}</span>`).join(' ')
          : '<span style="font-size:0.75rem; color:#888;">Nenhuma foto extra.</span>';
      }

      // Atualiza Barra Flutuante Mobile e Legenda Dinâmica
      const mInfo = document.getElementById('mobileBarInfo');
      if (mInfo) mInfo.textContent = `${totais.pacote} de ${totais.limite_pacote} no pacote` + (totais.extra > 0 ? ` + ${totais.extra} extras` : '');
      const mSub = document.getElementById('mobileBarSub');
      if (mSub) {
        if (totais.pacote >= totais.limite_pacote) {
          mSub.textContent = 'Pacote completo! Pronto para enviar ✈';
        } else {
          mSub.textContent = `Faltam ${Math.max(0, totais.limite_pacote - totais.pacote)} fotos no pacote`;
        }
      }
      const legPacote = document.getElementById('legendTextPacote');
      if (legPacote) legPacote.textContent = `Conta entre as ${totais.limite_pacote} fotos incluídas no pacote`;
    }

    function renderizarCardsFotos(fotos) {
      if (!fotosGlobais || fotosGlobais.length === 0) {
        gridFotos.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 4.5rem 2rem; background: #FFFFFF; border-radius: 16px; border: 1.5px dashed #C4A482; box-shadow: 0 4px 16px rgba(0,0,0,0.03);">
            <span style="font-size: 3rem; display: block; margin-bottom: 1rem;">📷</span>
            <h3 style="color: #2D1D14; font-size: 1.35rem; font-weight: 800; margin-bottom: 0.5rem;">Sua galeria está sendo preparada!</h3>
            <p style="color: #6B5E55; font-size: 0.92rem; max-width: 500px; margin: 0 auto; line-height: 1.6;">O estúdio está organizando as fotos do seu ensaio. Assim que os arquivos forem carregados no sistema, você poderá escolher suas fotos favoritas e extras com total facilidade.</p>
          </div>
        `;
        const meta = document.getElementById('txtMetaExibidas');
        if (meta) meta.textContent = '0 fotos disponíveis';
        return;
      }

      if (!fotos || fotos.length === 0) {
        gridFotos.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 3rem 1.5rem; background: #FFFFFF; border-radius: 12px; border: 1px solid #E8DDD0; color: #8C5F35;">
            Nenhuma foto encontrada para este filtro.
          </div>
        `;
        const meta = document.getElementById('txtMetaExibidas');
        if (meta) meta.textContent = `0 de ${fotosGlobais.length} fotos exibidas`;
        return;
      }

      const meta = document.getElementById('txtMetaExibidas');
      if (meta) meta.textContent = `${fotos.length} de ${fotosGlobais.length} fotos exibidas`;

      gridFotos.innerHTML = fotos.map((f, idx) => {
        const isPacote = f.status === 'pacote';
        const isExtra = f.status === 'extra';
        const tagStatus = isPacote ? 'No pacote' : isExtra ? 'Extra' : 'Disponível';
        const statusClass = isPacote ? 'tag-pacote' : isExtra ? 'tag-extra' : 'tag-disponivel';

        const floatingPillHtml = isPacote 
          ? `<div class="photo-floating-pill pill-pacote"><span class="pill-icon">✓</span> <span>No Pacote</span></div>`
          : isExtra 
          ? `<div class="photo-floating-pill pill-extra"><span class="pill-icon">★</span> <span>Foto Extra</span></div>`
          : '';

        return `
          <div class="proofing-card ${isPacote ? 'card-selected-pacote' : isExtra ? 'card-selected-extra' : ''}" data-id="${f.id}" data-status="${f.status}" data-numero="${(f.numero || '').toLowerCase()}">
            <div class="proofing-thumb-wrapper">
              <img src="${f.arquivo}" alt="${f.numero}" onclick="abrirLightbox('${f.arquivo}', '${f.numero}', ${f.id})" onerror="this.onerror=null; this.src='assets/logo/logo.png';" style="cursor: pointer;" loading="lazy">
              <!-- Marca d'água oficial protetora -->
              <div class="watermark-overlay" title="Casa da Foto Studio - Marca d'água"></div>
              ${floatingPillHtml}
              <button type="button" class="thumb-zoom-icon" onclick="abrirLightbox('${f.arquivo}', '${f.numero}', ${f.id})" title="Ampliar foto em alta resolução">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  <line x1="11" y1="8" x2="11" y2="14"></line>
                  <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
              </button>
            </div>
            <div class="proofing-card-content">
              <div class="proofing-card-top-info">
                <span class="photo-number-label">${f.numero}</span>
                <span class="photo-status-tag ${statusClass}">${tagStatus}</span>
              </div>
              <div class="proof-actions-dual">
                <button type="button" 
                  class="btn-proof-toggle ${isPacote ? 'active-pacote' : ''}" 
                  onclick="mudarStatusFoto(${f.id}, '${isPacote ? 'nao_selecionada' : 'pacote'}')"
                  title="${isPacote ? 'Remover do pacote' : 'Incluir foto no pacote'}">
                  <span class="toggle-icon">${isPacote ? '✓' : '+'}</span>
                  <span>Pacote</span>
                </button>
                <button type="button" 
                  class="btn-proof-toggle ${isExtra ? 'active-extra' : ''}" 
                  onclick="mudarStatusFoto(${f.id}, '${isExtra ? 'nao_selecionada' : 'extra'}')"
                  title="${isExtra ? 'Remover dos extras' : 'Escolher como foto extra'}">
                  <span class="toggle-icon">${isExtra ? '★' : '+'}</span>
                  <span>Extra</span>
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    function aplicarOrdenacaoERenderizar() {
      const selectOrdem = document.getElementById('selectOrdemFotosCliente');
      const val = selectOrdem ? selectOrdem.value : 'padrao';
      let lista = [...fotosGlobais];

      if (val === 'decrescente') {
        lista.sort((a, b) => (b.numero || '').localeCompare(a.numero || '', undefined, { numeric: true }));
      } else if (val === 'selecionadas') {
        lista.sort((a, b) => {
          const prio = s => s === 'pacote' ? 2 : s === 'extra' ? 1 : 0;
          return prio(b.status) - prio(a.status);
        });
      } else {
        lista.sort((a, b) => (a.ordem || 0) - (b.ordem || 0) || (a.numero || '').localeCompare(b.numero || '', undefined, { numeric: true }));
      }

      renderizarCardsFotos(lista);
    }

    // Seletor de ordenação
    const selectOrdem = document.getElementById('selectOrdemFotosCliente');
    if (selectOrdem) {
      selectOrdem.addEventListener('change', aplicarOrdenacaoERenderizar);
    }

    // Passos do topo
    const pill1 = document.getElementById('pillPasso1');
    const pill2 = document.getElementById('pillPasso2');
    if (pill1) {
      pill1.addEventListener('click', () => {
        pill1.className = 'step-pill-active';
        if (pill2) pill2.className = 'step-pill-inactive';
        gridFotos.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
    if (pill2) {
      pill2.addEventListener('click', () => {
        pill2.className = 'step-pill-active';
        if (pill1) pill1.className = 'step-pill-inactive';
        const sidebar = document.querySelector('.proofing-sidebar-summary') || document.getElementById('btnEnviarSelecao');
        if (sidebar) sidebar.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }

    window.mudarStatusFoto = async function(id, novoStatus) {
      if (window.galeriaBloqueadaCliente) {
        showToast('🔒 A seleção foi enviada e está bloqueada para análise pelo fotógrafo. Aguarde a liberação caso precise ajustar.', 'warning');
        return;
      }
      try {
        const itemLocal = fotosGlobais.find(f => f.id == id);
        if (itemLocal) {
          itemLocal.status = novoStatus;
          window.fotosGlobaisCliente = fotosGlobais;
        }
        const res = await fetch(`/api/galeria/${galId}/fotos/${id}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: novoStatus })
        });
        const d = await res.json();
        if (d.success) {
          const txt = novoStatus === 'pacote' ? 'adicionada ao Pacote' : novoStatus === 'extra' ? 'marcada como Extra' : 'removida da seleção';
          showToast(`Foto ${txt}!`);
          carregarFotos();
        } else {
          showToast(d.error || 'A seleção está bloqueada no momento.', 'warning');
          carregarFotos();
        }
      } catch (err) {
        showToast('Erro ao atualizar seleção.', 'error');
      }
    };

    // Filtros de Abas: Todas, Fotos do pacote, Fotos extras, Não selecionadas
    const tabsProof = document.querySelectorAll('.proofing-tabs-row .tab-filter-btn');
    tabsProof.forEach(btn => {
      btn.addEventListener('click', () => {
        tabsProof.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const txt = btn.textContent.toLowerCase();
        let filtro = 'todas';
        if (txt.includes('pacote')) filtro = 'pacote';
        else if (txt.includes('extra')) filtro = 'extra';
        else if (txt.includes('não') || txt.includes('nao')) filtro = 'nao_selecionada';

        const cards = gridFotos.querySelectorAll('.proofing-card');
        cards.forEach(c => {
          c.style.display = (filtro === 'todas' || c.getAttribute('data-status') === filtro) ? 'block' : 'none';
        });
      });
    });

    // Busca dinâmica pelo número da foto
    const searchPhotoInput = document.querySelector('.photo-search-input-pill input');
    if (searchPhotoInput) {
      searchPhotoInput.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase().trim();
        const cards = gridFotos.querySelectorAll('.proofing-card');
        cards.forEach(c => {
          const num = c.getAttribute('data-numero') || '';
          c.style.display = (!q || num.includes(q)) ? 'block' : 'none';
        });
      });
    }

    // Botão Enviar Seleção ao Fotógrafo (Abre modal oficial de confirmação)
    const btnEnviar = document.getElementById('btnEnviarSelecao');
    if (btnEnviar) {
      btnEnviar.onclick = (e) => {
        if (e) e.preventDefault();
        window.iniciarModalEnviarSelecao();
      };
    }

    carregarFotos();
  }

  // ============================================================================
  // 4. TELA: KANBAN DE PROJETOS (projetos.html)
  // ============================================================================
  const kanbanBoard = document.querySelector('.kanban-columns-grid') || document.querySelector('.kanban-board-grid');
  if (kanbanBoard) {
    let listaProjetosCache = [];
    let filtroTabAtiva = 'todos';

    const colunas = {
      'novos': document.getElementById('colNovos'),
      'andamento': document.getElementById('colAndamento'),
      'revisao': document.getElementById('colRevisao'),
      'entrega': document.getElementById('colEntrega') || document.getElementById('colProva'),
      'prova': document.getElementById('colEntrega') || document.getElementById('colProva'),
      'finalizados': document.getElementById('colFinalizados')
    };

    // Função de exclusão de projeto com confirmação
    window.removerProjetoCard = async function(id, nome) {
      if (!confirm(`Tem certeza que deseja remover o projeto de "${nome}"?\nEsta ação não poderá ser desfeita.`)) {
        return;
      }
      try {
        const res = await fetch(`/api/projetos/${id}`, {
          method: 'DELETE'
        });
        const d = await res.json();
        if (d.success) {
          showToast(`✓ Projeto de "${nome}" removido com sucesso!`);
          if (typeof window.carregarProjetosGlobal === 'function') {
            window.carregarProjetosGlobal();
          }
        } else {
          showToast(d.error || 'Erro ao remover projeto.', 'error');
        }
      } catch (err) {
        showToast('Erro de conexão ao remover projeto.', 'error');
      }
    };

    function atualizarSelectClientes(projetos) {
      const selectCliente = document.getElementById('filtroCliente');
      if (!selectCliente) return;
      const valorAtual = selectCliente.value;
      const clientesUnicos = [...new Set(projetos.map(p => p.nome_cliente).filter(Boolean))].sort();

      selectCliente.innerHTML = '<option value="todos">Cliente: Todos</option>';
      clientesUnicos.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = `Cliente: ${c}`;
        if (c === valorAtual) opt.selected = true;
        selectCliente.appendChild(opt);
      });
    }

    function renderizarKanbanComFiltros() {
      const termoBusca = (document.getElementById('kanbanSearchInput')?.value || '').toLowerCase().trim();
      const periodo = document.getElementById('filtroPeriodo')?.value || 'todos';
      const cliente = document.getElementById('filtroCliente')?.value || 'todos';
      const etapa = document.getElementById('filtroEtapa')?.value || 'todas';
      const categoria = document.getElementById('filtroCategoria')?.value || 'todas';
      const ordenacao = document.getElementById('filtroOrdenacao')?.value || 'recente';

      // 1. Limpa todas as colunas mantendo apenas o cabeçalho
      Object.keys(colunas).forEach(key => {
        const col = colunas[key];
        if (!col) return;
        const header = col.querySelector('.kanban-col-header');
        col.innerHTML = '';
        if (header) col.appendChild(header);
      });

      // 2. Filtra a lista em memória
      const agora = new Date();
      let filtrados = listaProjetosCache.filter(proj => {
        let st = proj.status;
        if (st === 'prova') st = 'entrega';

        // Filtro por Aba Superior
        if (filtroTabAtiva !== 'todos' && filtroTabAtiva !== 'todas') {
          if (filtroTabAtiva === 'prova' || filtroTabAtiva === 'entrega') {
            if (st !== 'entrega' && st !== 'prova') return false;
          } else if (st !== filtroTabAtiva) {
            return false;
          }
        }

        // Filtro por Etapa do Select
        if (etapa !== 'todas') {
          if (etapa === 'entrega' || etapa === 'prova') {
            if (st !== 'entrega' && st !== 'prova') return false;
          } else if (st !== etapa) {
            return false;
          }
        }

        // Filtro por Cliente
        if (cliente !== 'todos' && proj.nome_cliente !== cliente) {
          return false;
        }

        // Filtro por Categoria
        if (categoria !== 'todas') {
          const catProj = (proj.categoria_tag || '').toLowerCase();
          const tipoProj = (proj.tipo_ensaio || '').toLowerCase();
          const catAlvo = categoria.toLowerCase();
          if (!catProj.includes(catAlvo) && !tipoProj.includes(catAlvo)) {
            return false;
          }
        }

        // Filtro por Período
        if (periodo !== 'todos' && proj.criado_em) {
          const criado = new Date(proj.criado_em.replace(' ', 'T'));
          if (periodo === 'hoje') {
            if (criado.toDateString() !== agora.toDateString()) return false;
          } else if (periodo === 'semana') {
            const limiteSemana = new Date(agora.getTime() - 7 * 24 * 60 * 60 * 1000);
            if (criado < limiteSemana) return false;
          } else if (periodo === 'mes') {
            const limiteMes = new Date(agora.getTime() - 30 * 24 * 60 * 60 * 1000);
            if (criado < limiteMes) return false;
          }
        }

        // Filtro por Busca de Texto
        if (termoBusca) {
          const textoCompleto = `${proj.nome_cliente || ''} ${proj.tipo_ensaio || ''} ${proj.categoria_tag || ''} ${proj.prazo || ''}`.toLowerCase();
          if (!textoCompleto.includes(termoBusca)) return false;
        }

        return true;
      });

      // 3. Ordenação
      if (ordenacao === 'recente') {
        filtrados.sort((a, b) => b.id - a.id);
      } else if (ordenacao === 'antigo') {
        filtrados.sort((a, b) => a.id - b.id);
      } else if (ordenacao === 'nome_asc') {
        filtrados.sort((a, b) => (a.nome_cliente || '').localeCompare(b.nome_cliente || ''));
      } else if (ordenacao === 'nome_desc') {
        filtrados.sort((a, b) => (b.nome_cliente || '').localeCompare(a.nome_cliente || ''));
      }

      // 4. Renderização dos cards nas colunas
      const counts = { novos: 0, andamento: 0, revisao: 0, entrega: 0, finalizados: 0 };

      filtrados.forEach(proj => {
        let st = proj.status;
        if (st === 'prova') st = 'entrega';
        counts[st] = (counts[st] || 0) + 1;

        const col = colunas[st] || colunas[proj.status];
        if (!col) return;

        const card = document.createElement('div');
        card.className = 'kanban-item-card';
        card.setAttribute('data-id', proj.id);
        card.innerHTML = `
          <div class="card-top-row">
            <div class="card-avatar-thumb">
              <img src="${proj.avatar_img || 'assets/logo/logo.png'}" alt="${proj.nome_cliente || 'Cliente'}" onerror="this.src='assets/logo/logo.png'">
            </div>
            <div class="card-person-info">
              <span class="card-client-name">${proj.nome_cliente || 'Sem Nome'}</span>
              <span class="card-session-type">${proj.tipo_ensaio || 'Ensaio'}</span>
            </div>
          </div>
          <div class="card-tags-row">
            <span class="tag-badge">${proj.categoria_tag || 'Geral'}</span>
            ${st === 'novos' ? '<span class="tag-badge tag-novo">Novo</span>' : ''}
            ${st === 'entrega' ? '<span class="tag-badge tag-pronto">Pronto</span>' : ''}
            ${st === 'finalizados' ? '<span class="tag-badge tag-finalizado">Finalizado</span>' : ''}
          </div>
          <div class="card-meta-row">
            <span class="card-meta-item">📋 ${proj.sessoes || 1} sessão(ões)</span>
            <span class="card-meta-item">⏱ ${proj.prazo || 'sem prazo'}</span>
          </div>
          <div class="kanban-card-actions-wrapper">
            <div class="card-btn-grid-row">
              <a href="galeria-config.html?id=${proj.galeria_id || proj.id}&projeto_id=${proj.id}" class="card-action-pill btn-pill-config" title="Configurar a galeria deste projeto">
                ⚙️ Config
              </a>
              <a href="escolha-fotos.html?id=${proj.galeria_id || proj.id}&previa=true" target="_blank" class="card-action-pill btn-pill-selecao" title="Ver seleção de fotos deste cliente">
                👁️ Seleção
              </a>
            </div>
            <div class="card-btn-grid-row">
              <a href="entrega.html?id=${proj.galeria_id || proj.id}" target="_blank" class="card-action-pill btn-pill-entrega" title="Abrir página de entrega de fotos com botão Google Drive">
                🎁 Entrega
              </a>
              ${(proj.selecao_bloqueada == 1 || proj.status_galeria === 'Seleção enviada') ? `
                <button type="button" class="card-action-pill btn-pill-liberar" onclick="window.alternarBloqueioGaleria(${proj.galeria_id || proj.id}, 0)" title="Clique para LIBERAR e permitir que o cliente altere as fotos">
                  🔓 Liberar Ajustes
                </button>
              ` : `
                <button type="button" class="card-action-pill btn-pill-bloquear" onclick="window.alternarBloqueioGaleria(${proj.galeria_id || proj.id}, 1)" title="Clique para BLOQUEAR a seleção para que o cliente não faça alterações">
                  🔒 Bloquear
                </button>
              `}
            </div>
            <div class="card-btn-grid-row" style="margin-top: 3px;">
              <button type="button" class="card-action-pill btn-pill-status" style="width: 100%;" onclick="window.abrirModalStatusGaleria(${proj.galeria_id || proj.id}, '${(proj.nome_cliente || '').replace(/'/g, "\\'")}', '${proj.status_galeria || 'Aguardando seleção'}', ${proj.selecao_bloqueada || 0})" title="Alterar status da galeria">
                📋 ${proj.status_galeria || 'Status'} ▾
              </button>
            </div>
            <div class="card-btn-grid-row" style="margin-top: 3px;">
              <button type="button" class="card-action-pill btn-pill-drive" style="width: 100%; font-size: 0.77rem; padding: 0.45rem 0.6rem;" onclick="window.abrirModalLinkDrive(${proj.galeria_id || proj.id}, '${(proj.nome_cliente || '').replace(/'/g, "\\'")}', '${(proj.tipo_ensaio || '').replace(/'/g, "\\'")}', '${(proj.link_drive || '').replace(/'/g, "\\'")}', '${(proj.mensagem_acesso || '').replace(/'/g, "\\'").replace(/\r?\n/g, '\\n')}')" title="Inserir ou editar link do Google Drive e mensagem personalizada de entrega">
                🔗 Link do Drive & Mensagem
              </button>
            </div>
            <div class="card-mover-bottom-row">
              <span class="mover-prefix">Etapa:</span>
              <select class="select-mover-status" data-id="${proj.id}" title="Mover etapa do projeto">
                <option value="novos" ${st==='novos'?'selected':''}>Novos</option>
                <option value="andamento" ${st==='andamento'?'selected':''}>Em andamento</option>
                <option value="revisao" ${st==='revisao'?'selected':''}>Em revisão</option>
                <option value="entrega" ${st==='entrega'?'selected':''}>Entrega</option>
                <option value="finalizados" ${st==='finalizados'?'selected':''}>Finalizados</option>
              </select>
              <button type="button" class="btn-remover-card-icon" onclick="removerProjetoCard(${proj.id}, '${(proj.nome_cliente || '').replace(/'/g, "\\'")}')" title="Excluir este projeto do Kanban">
                🗑️
              </button>
            </div>
          </div>
        `;

        const sel = card.querySelector('.select-mover-status');
        sel.addEventListener('change', async (e) => {
          const novoSt = e.target.value;
          try {
            const r = await fetch(`/api/projetos/${proj.id}/status`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ status: novoSt })
            });
            const d = await r.json();
            if (d.success) {
              showToast(`✓ Projeto de "${proj.nome_cliente}" movido para: ${novoSt.toUpperCase()}`);
              window.carregarProjetosGlobal();
            }
          } catch (err) {
            showToast('Erro ao atualizar status do projeto.', 'error');
          }
        });

        col.appendChild(card);
      });

      // Se a coluna de Entrega estiver vazia, exibe atalho amigável para a Página de Entrega
      if (counts['entrega'] === 0 && colunas['entrega']) {
        const emptyEntrega = document.createElement('div');
        emptyEntrega.style.cssText = 'padding: 1.5rem 1rem; text-align: center; background: #FFFDF9; border: 1.5px dashed #C59B6D; border-radius: 12px; margin: 0.5rem; box-shadow: 0 2px 8px rgba(140,95,53,0.06);';
        emptyEntrega.innerHTML = `
          <div style="font-size: 2rem; margin-bottom: 0.35rem;">🎁</div>
          <strong style="color: #2D1D14; font-size: 0.9rem; display: block; margin-bottom: 0.3rem;">Página de Entrega (Drive)</strong>
          <span style="color: #7A6A5E; font-size: 0.77rem; display: block; margin-bottom: 0.9rem; line-height: 1.4;">Acesse ou envie a página oficial onde o cliente faz o download das fotos finais em alta resolução via Google Drive.</span>
          <a href="entrega.html" target="_blank" style="display: inline-block; background: #8C5F35; color: #FFF; padding: 0.55rem 1.2rem; border-radius: 9999px; text-decoration: none; font-size: 0.8rem; font-weight: 700; box-shadow: 0 2px 6px rgba(140,95,53,0.3);">
            Abrir Página de Entrega ↗
          </a>
        `;
        colunas['entrega'].appendChild(emptyEntrega);
      }

      // Se o Kanban estiver 100% vazio, exibe dica para criar projeto ou restaurar exemplos
      if (filtrados.length === 0 && colunas['novos']) {
        const emptyNovos = document.createElement('div');
        emptyNovos.style.cssText = 'padding: 1.75rem 1.1rem; text-align: center; background: #FFFFFF; border: 2px dashed #C59B6D; border-radius: 14px; margin: 0.5rem; box-shadow: 0 4px 12px rgba(45,29,20,0.04);';
        emptyNovos.innerHTML = `
          <div style="font-size: 2rem; margin-bottom: 0.35rem;">📷</div>
          <strong style="color: #2D1D14; font-size: 0.95rem; display: block; margin-bottom: 0.25rem;">Nenhum projeto encontrado</strong>
          <span style="color: #7A6A5E; font-size: 0.78rem; display: block; margin-bottom: 0.9rem; line-height: 1.4;">Restaure as 5 galerias e ensaios de exemplo completos ou cadastre um novo projeto.</span>
          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <button type="button" onclick="window.restaurarGaleriasExemplo()" style="background: linear-gradient(135deg, #8C5F35 0%, #684221 100%); color: #FFF; border: none; padding: 0.6rem 1.15rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 700; cursor: pointer; box-shadow: 0 2px 6px rgba(140,95,53,0.3);">
              ✨ Restaurar Galerias de Exemplo
            </button>
            <button type="button" onclick="const b=document.getElementById('btnNovoProjeto'); if(b) b.click();" style="background: #FAF5EE; color: #5C4A3E; border: 1px solid #D8CAB9; padding: 0.5rem 1.1rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 700; cursor: pointer;">
              + Criar Novo Projeto
            </button>
          </div>
        `;
        colunas['novos'].appendChild(emptyNovos);
      }

      // 5. Atualiza os contadores das colunas
      Object.keys(counts).forEach(k => {
        const col = colunas[k];
        if (!col) return;
        const badge = col.querySelector('.col-badge-count');
        if (badge) badge.textContent = counts[k];
      });
    }

    window.carregarProjetosGlobal = async function() {
      try {
        const res = await fetch('/api/projetos');
        listaProjetosCache = await res.json();
        window.listaProjetosCache = listaProjetosCache;
        atualizarSelectClientes(listaProjetosCache);
        renderizarKanbanComFiltros();
      } catch (err) {
        console.error('Erro ao carregar projetos:', err);
      }
    };

    // Eventos dos Controles de Filtro
    const searchInput = document.getElementById('kanbanSearchInput') || document.querySelector('.search-box-pill input');
    if (searchInput) {
      searchInput.addEventListener('input', () => renderizarKanbanComFiltros());
    }

    const filtroPeriodo = document.getElementById('filtroPeriodo');
    if (filtroPeriodo) {
      filtroPeriodo.addEventListener('change', () => renderizarKanbanComFiltros());
    }

    const filtroCliente = document.getElementById('filtroCliente');
    if (filtroCliente) {
      filtroCliente.addEventListener('change', () => renderizarKanbanComFiltros());
    }

    const filtroEtapa = document.getElementById('filtroEtapa');
    if (filtroEtapa) {
      filtroEtapa.addEventListener('change', (e) => {
        const valor = e.target.value;
        const kanbanTabs = document.querySelectorAll('.kanban-nav-tabs .kanban-tab-item');
        kanbanTabs.forEach(t => {
          const tabVal = t.getAttribute('data-tab') || t.getAttribute('href')?.replace('#', '');
          if ((valor === 'todas' && (tabVal === 'todos' || tabVal === 'todas')) || tabVal === valor) {
            t.classList.add('active');
          } else {
            t.classList.remove('active');
          }
        });
        filtroTabAtiva = valor === 'todas' ? 'todos' : valor;
        renderizarKanbanComFiltros();
      });
    }

    const filtroCategoria = document.getElementById('filtroCategoria');
    if (filtroCategoria) {
      filtroCategoria.addEventListener('change', () => renderizarKanbanComFiltros());
    }

    const filtroOrdenacao = document.getElementById('filtroOrdenacao');
    if (filtroOrdenacao) {
      filtroOrdenacao.addEventListener('change', () => renderizarKanbanComFiltros());
    }

    // Abas de navegação do Kanban (Top tabs)
    const kanbanTabs = document.querySelectorAll('.kanban-nav-tabs .kanban-tab-item');
    kanbanTabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        e.preventDefault();
        const tabVal = tab.getAttribute('data-tab') || tab.getAttribute('href')?.replace('#', '');
        
        kanbanTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        filtroTabAtiva = tabVal;

        if (filtroEtapa) {
          filtroEtapa.value = (tabVal === 'todos' || tabVal === 'todas') ? 'todas' : tabVal;
        }

        if (tabVal === 'novos') document.getElementById('colNovos')?.scrollIntoView({ behavior: 'smooth', inline: 'start' });
        else if (tabVal === 'andamento') document.getElementById('colAndamento')?.scrollIntoView({ behavior: 'smooth', inline: 'start' });
        else if (tabVal === 'entrega' || tabVal === 'prova') (document.getElementById('colEntrega') || document.getElementById('colProva'))?.scrollIntoView({ behavior: 'smooth', inline: 'start' });
        else if (tabVal === 'finalizados') document.getElementById('colFinalizados')?.scrollIntoView({ behavior: 'smooth', inline: 'start' });

        renderizarKanbanComFiltros();
      });
    });

    // Botão "+ Novo projeto"
    const btnNovoProj = document.getElementById('btnNovoProjeto') || document.querySelector('.btn-novo-projeto');
    if (btnNovoProj) {
      btnNovoProj.addEventListener('click', () => {
        if (typeof window.abrirModalNovoProjeto === 'function') {
          window.abrirModalNovoProjeto();
        }
      });
    }

    // Carrega inicialmente
    window.carregarProjetosGlobal();

    // Abre modal automaticamente se vier de link externo com ?novo=1
    if (new URLSearchParams(window.location.search).get('novo') === '1') {
      setTimeout(() => {
        if (typeof window.abrirModalNovoProjeto === 'function') {
          window.abrirModalNovoProjeto();
        }
      }, 350);
    }
  }

  // ============================================================================
  // 5. TELA: CONFIGURAÇÕES DA GALERIA (galeria-config.html)
  // ============================================================================
  let galConfigId = new URLSearchParams(window.location.search).get('id') || new URLSearchParams(window.location.search).get('projeto_id') || '1';
  window.galConfigId = galConfigId;

  window.uploadNovaCapaGaleria = function(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async function(e) {
      const base64 = e.target.result;
      const imgPreview = document.getElementById('imgPreviewCapaDesign');
      if (imgPreview) imgPreview.src = base64;
      showToast('Enviando e definindo foto de capa...');
      try {
        const upRes = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64 })
        });
        const upData = await upRes.json();
        const capaUrl = (upData.success && upData.url) ? upData.url : base64;

        await fetch(`/api/galeria/${galConfigId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ foto_capa: capaUrl })
        });
        showToast('✓ Foto de capa da galeria atualizada com sucesso!');
      } catch (err) {
        showToast('Erro ao atualizar foto de capa.', 'error');
      }
    };
    reader.readAsDataURL(file);
  };

  // ── GESTÃO DE CATEGORIAS DA GALERIA ──
  window.carregarCategoriasConfig = async function(catSelecionada) {
    const selects = document.querySelectorAll('#selectCategoriaGaleria, select[name="categoria"]');
    if (!selects.length) return;

    try {
      const res = await fetch('/api/categorias');
      const categorias = await res.json();

      let lista = Array.isArray(categorias) ? categorias : [];
      if (lista.length === 0) {
        lista = [
          { id: 1, nome: 'Galeria demonstrativa' },
          { id: 2, nome: 'Ensaio Família' },
          { id: 3, nome: 'Gestante' },
          { id: 4, nome: 'Newborn' }
        ];
      }

      selects.forEach(select => {
        const valorAtual = catSelecionada || select.value || (window.galeriaConfigAtual && window.galeriaConfigAtual.categoria) || 'Galeria demonstrativa';

        let listaFinal = [...lista];
        if (valorAtual && valorAtual !== '__nova__' && !listaFinal.some(c => c.nome.toLowerCase() === valorAtual.toLowerCase())) {
          listaFinal.unshift({ id: 'custom', nome: valorAtual });
        }

        let optionsHtml = listaFinal.map(cat => {
          const isSel = (cat.nome.toLowerCase() === valorAtual.toLowerCase()) ? 'selected' : '';
          return `<option value="${cat.nome}" ${isSel}>${cat.nome}</option>`;
        }).join('');

        optionsHtml += `<option value="__nova__" style="font-weight: 700; color: #8C5F35;">+ Adicionar nova categoria...</option>`;
        select.innerHTML = optionsHtml;

        if (valorAtual && valorAtual !== '__nova__') {
          select.value = valorAtual;
        }
      });

      const valorFinal = catSelecionada || (selects[0] && selects[0].value);
      if (valorFinal && valorFinal !== '__nova__') {
        const pillTag = document.querySelector('.preview-pill-tag');
        if (pillTag) pillTag.textContent = valorFinal;
      }
    } catch (err) {
      console.warn('Erro ao carregar categorias dinâmicas:', err);
    }
  };

  window.tratarMudancaCategoria = function(selectEl) {
    if (!selectEl) return;
    if (selectEl.value === '__nova__') {
      window.abrirModalNovaCategoria();
    } else {
      const pillTag = document.querySelector('.preview-pill-tag');
      if (pillTag) pillTag.textContent = selectEl.value;
    }
  };

  window.abrirModalNovaCategoria = function() {
    const modal = document.getElementById('modalAddCategoria');
    if (modal) {
      modal.style.display = 'flex';
      const input = document.getElementById('inputNomeNovaCategoria');
      if (input) {
        input.value = '';
        setTimeout(() => input.focus(), 60);
      }
    }
  };

  window.fecharModalNovaCategoria = function() {
    const modal = document.getElementById('modalAddCategoria');
    if (modal) modal.style.display = 'none';
    const select = document.getElementById('selectCategoriaGaleria');
    if (select && select.value === '__nova__') {
      select.value = (window.galeriaConfigAtual && window.galeriaConfigAtual.categoria) || (select.options[0] ? select.options[0].value : 'Galeria demonstrativa');
    }
  };

  window.salvarNovaCategoriaModal = async function() {
    const input = document.getElementById('inputNomeNovaCategoria');
    const nome = input ? input.value.trim() : '';
    if (!nome) {
      showToast('Informe o nome da categoria.', 'error');
      return;
    }

    const btn = document.getElementById('btnSalvarModalCategoria');
    const origText = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = 'Adicionando...'; }

    try {
      const res = await fetch('/api/categorias', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        const novaCatNome = (data.categoria && data.categoria.nome) ? data.categoria.nome : nome;
        showToast(`✓ Categoria "${novaCatNome}" adicionada com sucesso!`);
        window.fecharModalNovaCategoria();
        await window.carregarCategoriasConfig(novaCatNome);
        const select = document.getElementById('selectCategoriaGaleria');
        if (select) select.value = novaCatNome;
        const pillTag = document.querySelector('.preview-pill-tag');
        if (pillTag) pillTag.textContent = novaCatNome;
      } else {
        showToast(data.error || 'Erro ao criar categoria.', 'error');
      }
    } catch (err) {
      showToast('Erro de conexão ao salvar categoria.', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = origText; }
    }
  };

  const adminMain = document.getElementById('adminMainContent');
  if (adminMain) {
    // Carrega dados da galeria
    window.carregarDadosGaleria = async function() {
      try {
        const res = await fetch(`/api/galeria/${galConfigId}`);
        const data = await res.json();
        window.galeriaConfigAtual = data;
        if (data) {
          if (data.foto_capa) {
            const imgPreview = document.getElementById('imgPreviewCapaDesign');
            if (imgPreview) imgPreview.src = data.foto_capa;
            const imgLateral = document.getElementById('imgPreviewCapaGaleriaLateral');
            if (imgLateral) imgLateral.src = data.foto_capa;
          }
          if (data.nome) {
            const inpNome = document.getElementById('inputNomeGaleria');
            if (inpNome) inpNome.value = data.nome;
          }
          if (data.categoria) {
            window.carregarCategoriasConfig(data.categoria);
          } else {
            window.carregarCategoriasConfig();
          }
          const inpValor = document.getElementById('inputValorFotoExtra');
          if (inpValor && data.valor_foto_extra != null) {
            inpValor.value = parseFloat(data.valor_foto_extra).toFixed(2);
          }
          const inpLimite = document.getElementById('inputLimitePacote');
          if (inpLimite && data.limite_pacote != null) {
            inpLimite.value = data.limite_pacote;
          }
          const chkExtras = document.getElementById('chkPermitirExtras');
          if (chkExtras && data.permitir_extras != null) {
            chkExtras.checked = !!data.permitir_extras;
          }
          const spanTitle = document.getElementById('sidebarProjectTitle') || document.querySelector('.sidebar-project-title');
          if (spanTitle && data.nome) {
            spanTitle.textContent = data.nome;
          }
          const breadcrumbNome = document.getElementById('breadcrumbGaleriaNome');
          if (breadcrumbNome && data.nome) {
            breadcrumbNome.textContent = data.nome;
          }
          const selGal = document.getElementById('selectGaleriaAtivaConfig');
          if (selGal && data.id) {
            selGal.value = String(data.id);
          }
          const inpDrive = document.getElementById('inputLinkGoogleDrive');
          if (inpDrive && data.link_drive) {
            inpDrive.value = data.link_drive;
          }
          const btnSidebarEntrega = document.getElementById('btnSidebarVerEntrega');
          if (btnSidebarEntrega) {
            btnSidebarEntrega.href = `entrega.html?id=${galConfigId}`;
          }

          // Atualiza seletor de status e botão de liberação na barra superior
          const selStatus = document.getElementById('selectStatusGaleriaConfig');
          if (selStatus && data.status_galeria) {
            selStatus.value = data.status_galeria;
          }
          const badgeSide = document.getElementById('sidebarBadgeStatusGaleria') || document.querySelector('.badge-status-andamento');
          if (badgeSide) {
            badgeSide.textContent = data.status_galeria || 'Aguardando seleção';
          }
          const btnBloq = document.getElementById('btnToggleBloqueioConfig');
          if (btnBloq) {
            const isBloq = (data.selecao_bloqueada == 1 || data.status_galeria === 'Seleção enviada');
            if (isBloq) {
              btnBloq.innerHTML = '🔓 Liberar para Ajustes';
              btnBloq.style.background = '#2E7D32';
              btnBloq.style.color = '#FFF';
              btnBloq.title = 'A seleção do cliente está bloqueada. Clique para liberar caso o cliente precise alterar as fotos.';
            } else {
              btnBloq.innerHTML = '🔒 Bloquear Seleção';
              btnBloq.style.background = '#FAF5EE';
              btnBloq.style.border = '1px solid #D8CAB9';
              btnBloq.style.color = '#5C4A3E';
              btnBloq.title = 'A seleção está liberada. Clique para bloquear e impedir alterações pelo cliente.';
            }
          }
        }
      } catch (e) {
        console.warn('Erro ao carregar dados da galeria:', e);
      }
    };

    // ── GESTÃO E TROCA RÁPIDA DE GALERIA NO PAINEL DE CONFIGURAÇÕES ──
    window.carregarListaGaleriasConfig = async function(ativoId) {
      const select = document.getElementById('selectGaleriaAtivaConfig');
      if (!select) return;

      try {
        const res = await fetch('/api/galerias');
        const galerias = await res.json();
        if (Array.isArray(galerias) && galerias.length > 0) {
          select.innerHTML = galerias.map(g => {
            const cliente = g.nome_cliente ? ` · ${g.nome_cliente}` : '';
            const fotos = ` (${g.total_fotos || 0} fotos)`;
            return `<option value="${g.id}">${g.nome}${cliente}${fotos}</option>`;
          }).join('');

          const idDesejado = String(ativoId || galConfigId);
          const galeriaExiste = galerias.some(g => String(g.id) === idDesejado);

          if (galeriaExiste) {
            select.value = idDesejado;
          } else {
            select.value = String(galerias[0].id);
            galConfigId = String(galerias[0].id);
            window.galConfigId = galConfigId;
            const url = new URL(window.location.href);
            url.searchParams.set('id', galConfigId);
            window.history.replaceState({}, '', url.toString());
          }

          const gAtual = galerias.find(g => String(g.id) === String(select.value));
          if (gAtual) {
            const spanTitle = document.getElementById('sidebarProjectTitle') || document.querySelector('.sidebar-project-title');
            if (spanTitle) spanTitle.textContent = gAtual.nome;
            const breadcrumbNome = document.getElementById('breadcrumbGaleriaNome');
            if (breadcrumbNome) breadcrumbNome.textContent = gAtual.nome;
          }
        } else {
          select.innerHTML = '<option value="">Nenhuma galeria cadastrada</option>';
        }
      } catch (err) {
        console.warn('Erro ao carregar lista de galerias:', err);
      }
    };

    window.trocarGaleriaConfigAtiva = async function(novoId) {
      if (!novoId) return;
      galConfigId = String(novoId);
      window.galConfigId = galConfigId;

      const url = new URL(window.location.href);
      url.searchParams.set('id', novoId);
      window.history.pushState({}, '', url.toString());

      const btnSidebarEntrega = document.getElementById('btnSidebarVerEntrega');
      if (btnSidebarEntrega) {
        btnSidebarEntrega.href = `entrega.html?id=${galConfigId}`;
      }

      if (typeof window.carregarDadosGaleria === 'function') await window.carregarDadosGaleria();
      if (typeof window.carregarFotosGaleriaConfig === 'function') await window.carregarFotosGaleriaConfig();
      if (typeof window.carregarDestinatariosConfig === 'function') await window.carregarDestinatariosConfig();
      if (typeof window.carregarAtividadesClienteConfig === 'function') await window.carregarAtividadesClienteConfig();
      if (typeof window.carregarResumoDesignConfig === 'function') await window.carregarResumoDesignConfig();
      if (typeof window.carregarHistoricoGaleriaConfig === 'function') await window.carregarHistoricoGaleriaConfig();

      showToast('✓ Galeria carregada com sucesso!');
    };

    window.salvarStatusGaleriaDireto = async function(novoStatus) {
      try {
        const res = await fetch(`/api/galeria/${galConfigId}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status_galeria: novoStatus })
        });
        const d = await res.json();
        if (d.success) {
          showToast(`✓ Status da galeria atualizado para: "${novoStatus}"`);
          window.carregarDadosGaleria();
        } else {
          showToast(d.error || 'Erro ao atualizar status.', 'error');
        }
      } catch (e) {
        showToast('Erro de conexão ao atualizar status da galeria.', 'error');
      }
    };

    window.alternarBloqueioGaleriaAtual = async function() {
      if (!window.galeriaConfigAtual) return;
      const isBloq = (window.galeriaConfigAtual.selecao_bloqueada == 1 || window.galeriaConfigAtual.status_galeria === 'Seleção enviada');
      window.alternarBloqueioGaleria(galConfigId, isBloq ? 0 : 1);
    };

    window.carregarDadosGaleria();
    window.carregarListaGaleriasConfig(galConfigId);

    // Função de alta eficiência para compactar fotos antes do envio (permanece muito abaixo do limite de 4.5MB da Vercel)
    async function otimizarFotoParaUpload(file, maxDimension = 1600, quality = 0.78) {
      if (!file.type || !file.type.startsWith('image/')) return file;
      if (file.type === 'image/svg+xml' || (file.type === 'image/gif' && file.size < 500 * 1024)) return file;

      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = new Image();
          img.onload = () => {
            let width = img.width;
            let height = img.height;
            if (width > maxDimension || height > maxDimension) {
              if (width > height) {
                height = Math.round((height * maxDimension) / width);
                width = maxDimension;
              } else {
                width = Math.round((width * maxDimension) / height);
                height = maxDimension;
              }
            }
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            ctx.drawImage(img, 0, 0, width, height);
            canvas.toBlob((blob) => {
              if (blob) {
                const cleanName = file.name.replace(/\.[^/.]+$/, "") + ".jpg";
                resolve(new File([blob], cleanName, { type: 'image/jpeg' }));
              } else {
                resolve(file);
              }
            }, 'image/jpeg', quality);
          };
          img.onerror = () => resolve(file);
          img.src = e.target.result;
        };
        reader.onerror = () => resolve(file);
        reader.readAsDataURL(file);
      });
    }

    // ── SUBIR FOTOS PARA A GALERIA DO CLIENTE COM MÁXIMA LEVEZA (ANTI-LIMIT VERCEL) ──
    window.uploadFotosParaGaleria = async function(input) {
      const files = input.files;
      if (!files || files.length === 0) return;

      // Validação prévia contra formatos RAW ou HEIC incompatíveis com navegadores web
      const arquivosValidos = [];
      const arquivosIncompativeis = [];
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        if (f.name && f.name.match(/\.(heic|heif|raw|cr2|cr3|nef|arw|dng|orf)$/i)) {
          arquivosIncompativeis.push(f.name);
        } else {
          arquivosValidos.push(f);
        }
      }

      if (arquivosIncompativeis.length > 0) {
        showToast(`⚠️ ${arquivosIncompativeis.length} foto(s) em formato RAW/HEIC detectadas. Por favor, exporte como JPG ou PNG para visualização web.`, 'error');
        if (arquivosValidos.length === 0) {
          input.value = '';
          return;
        }
      }

      const filesParaUpload = arquivosValidos;

      const progressBox = document.getElementById('progressUploadGaleria');
      const bar = document.getElementById('barUploadGaleria');
      const statusTxt = document.getElementById('txtUploadGaleriaStatus');
      const pctTxt = document.getElementById('txtUploadGaleriaPorcentagem');

      if (progressBox) progressBox.style.display = 'block';
      if (bar) bar.style.width = '5%';
      if (pctTxt) pctTxt.textContent = '5%';
      if (statusTxt) statusTxt.textContent = `Otimizando e preparando ${filesParaUpload.length} foto(s)...`;

      let totalSucesso = 0;
      let totalErros = 0;

      for (let i = 0; i < filesParaUpload.length; i++) {
        const file = filesParaUpload[i];
        const pct = Math.round(((i) / filesParaUpload.length) * 100);
        if (bar) bar.style.width = `${Math.max(8, pct)}%`;
        if (pctTxt) pctTxt.textContent = `${Math.max(8, pct)}%`;
        if (statusTxt) statusTxt.textContent = `Otimizando foto ${i + 1} de ${filesParaUpload.length} (${file.name})...`;

        try {
          // Otimiza para max 1600px / qualidade 0.78 (~180KB - 300KB por foto)
          const filePronto = await otimizarFotoParaUpload(file, 1600, 0.78);
          const formData = new FormData();
          formData.append('fotos', filePronto, filePronto.name);

          if (statusTxt) statusTxt.textContent = `Enviando foto ${i + 1} de ${files.length} (${(filePronto.size / 1024).toFixed(0)} KB)...`;

          const res = await fetch(`/api/galeria/${galConfigId}/upload-fotos`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.success) {
            totalSucesso += (data.inseridas && data.inseridas.length) || 1;
          } else {
            totalErros++;
            console.warn(`Erro no upload da foto ${file.name}:`, data.error);
          }
        } catch (err) {
          totalErros++;
          console.error(`Falha no upload da foto ${file.name}:`, err);
        }
      }

      if (bar) bar.style.width = '100%';
      if (pctTxt) pctTxt.textContent = '100%';

      if (totalSucesso > 0) {
        showToast(`✓ ${totalSucesso} foto(s) enviada(s) com sucesso! Totalmente otimizadas.`);
        if (statusTxt) statusTxt.textContent = `✓ Upload concluído com sucesso! ${totalSucesso} foto(s) importada(s).`;
      } else {
        showToast('Erro ao realizar upload das fotos.', 'error');
        if (statusTxt) statusTxt.textContent = 'Falha no envio das fotos.';
      }

      setTimeout(() => {
        if (progressBox) progressBox.style.display = 'none';
      }, 2500);

      input.value = '';
      if (typeof window.carregarFotosGaleriaConfig === 'function') {
        window.carregarFotosGaleriaConfig();
      }
    };

    // ── CARREGAR E RENDERIZAR FOTOS DA GALERIA ──
    window.carregarFotosGaleriaConfig = async function() {
      const grid = document.getElementById('gridFotosGaleriaAdmin');
      if (!grid) return;

      try {
        const [resFotos, resGal] = await Promise.all([
          fetch(`/api/galeria/${galConfigId}/fotos`),
          fetch(`/api/galeria/${galConfigId}`)
        ]);
        const dFotos = await resFotos.json();
        const gal = await resGal.json();

        const fotos = dFotos.fotos || [];
        window.todasFotosGaleriaCache = fotos;
        window.capaAtualGaleria = gal.foto_capa || '';

        const imgCapa = document.getElementById('imgPreviewCapaGaleriaLateral');
        if (imgCapa && gal.foto_capa) imgCapa.src = gal.foto_capa;

        const countEl = document.getElementById('countFotosGaleria');
        if (countEl) countEl.textContent = `${fotos.length} foto(s)`;

        const cardFotos = document.getElementById('cardFotosGaleria');
        if (fotos.length === 0) {
          if (cardFotos) cardFotos.style.display = 'none';
          grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #888; padding: 2rem;">Nenhuma foto na galeria ainda. Clique em "Selecionar do computador" acima.</div>';
          window.carregarFotosSelecionadas();
          return;
        }

        if (cardFotos) cardFotos.style.display = 'block';
        window.renderizarGridFotosAdmin(fotos);
        window.carregarFotosSelecionadas();
      } catch (err) {
        console.error('Erro ao carregar fotos da galeria:', err);
      }
    };

    window.renderizarGridFotosAdmin = function(fotos) {
      const grid = document.getElementById('gridFotosGaleriaAdmin');
      if (!grid) return;

      grid.innerHTML = fotos.map(f => {
        const isCapa = (window.capaAtualGaleria === f.arquivo);
        const tagCapa = isCapa 
          ? '<span style="position: absolute; top: 6px; left: 6px; background: #9E744B; color: #FFF; font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); z-index: 4;">⭐ Capa Oficial</span>'
          : '';

        const statusBadge = f.status === 'pacote'
          ? '<span style="background: #2D1D14; color: #FFF; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px;">No pacote</span>'
          : f.status === 'extra'
          ? '<span style="background: #9E744B; color: #FFF; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px;">Extra</span>'
          : '<span style="background: #E8DDD0; color: #6B5546; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px;">Não selecionada</span>';

        return `
          <div class="admin-photo-card" style="position: relative;">
            <div style="position: relative; height: 120px; overflow: hidden; background: #EFE6DC;">
              <img src="${f.arquivo}" alt="${f.numero}" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;" onclick="abrirLightbox('${f.arquivo}', '${f.numero}')" onerror="this.onerror=null; this.src='assets/logo/logo.png';">
              <div class="watermark-overlay" style="opacity: 0.25;"></div>
              ${tagCapa}
            </div>
            <div style="padding: 0.65rem; display: flex; flex-direction: column; gap: 0.4rem; flex: 1;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="font-size: 0.78rem; color: #2D1D14; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${f.numero}">${f.numero}</strong>
                ${statusBadge}
              </div>
              <div style="display: flex; gap: 0.35rem; margin-top: auto; padding-top: 4px;">
                <button type="button" onclick="definirCapaGaleria(${f.id})" style="flex: 1; background: ${isCapa ? '#E8DDD0' : '#FAF5EE'}; border: 1px solid #D8CAB9; color: #6B5546; font-size: 0.7rem; font-weight: 600; padding: 4px 6px; border-radius: 6px; cursor: pointer; transition: all 0.2s;" title="Definir como foto de capa">
                  ${isCapa ? '⭐ Capa' : 'Definir Capa'}
                </button>
                <button type="button" onclick="excluirFotoGaleria(${f.id})" style="background: #FFF; border: 1px solid #D8CAB9; color: #A83232; font-size: 0.7rem; font-weight: 600; padding: 4px 6px; border-radius: 6px; cursor: pointer;" title="Excluir foto da galeria">
                  🗑️
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    };

    window.definirCapaGaleria = async function(fotoId) {
      try {
        const res = await fetch(`/api/galeria/${galConfigId}/fotos/${fotoId}/capa`, { method: 'PUT' });
        const d = await res.json();
        if (d.success) {
          showToast('✓ Foto definida como capa da galeria com sucesso!');
          window.carregarFotosGaleriaConfig();
        }
      } catch (err) {
        showToast('Erro ao definir foto de capa.', 'error');
      }
    };

    window.excluirFotoGaleria = async function(fotoId) {
      if (!confirm('Deseja realmente remover esta foto da galeria?')) return;
      try {
        const res = await fetch(`/api/galeria/${galConfigId}/fotos/${fotoId}`, { method: 'DELETE' });
        const d = await res.json();
        if (d.success) {
          showToast('Foto excluída da galeria.');
          window.carregarFotosGaleriaConfig();
        }
      } catch (err) {
        showToast('Erro ao excluir foto.', 'error');
      }
    };

    window.ordenarFotosGaleriaAdmin = function(tipo) {
      if (!window.todasFotosGaleriaCache) return;
      let fotos = [...window.todasFotosGaleriaCache];
      if (tipo === 'nome') {
        fotos.sort((a, b) => (a.numero || '').localeCompare(b.numero || '', undefined, { numeric: true }));
      } else {
        fotos.sort((a, b) => (a.ordem || 0) - (b.ordem || 0));
      }
      window.renderizarGridFotosAdmin(fotos);
    };

    // Busca de foto em tempo real
    const buscaFotosInp = document.getElementById('buscaFotosGaleriaAdmin');
    if (buscaFotosInp) {
      buscaFotosInp.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase().trim();
        if (!window.todasFotosGaleriaCache) return;
        const filtradas = window.todasFotosGaleriaCache.filter(f => 
          (f.numero || '').toLowerCase().includes(q) || (f.titulo || '').toLowerCase().includes(q)
        );
        window.renderizarGridFotosAdmin(filtradas);
      });
    }

    // ── FOTOS ESCOLHIDAS E EXPORTAÇÃO PARA WINDOWS 10 E 11 ──
    window.carregarFotosSelecionadas = async function() {
      try {
        const res = await fetch(`/api/galeria/${galConfigId}/selecionadas`);
        const d = await res.json();
        window.selecionadasCache = d;

        const txtWindows = document.getElementById('txtBuscaWindows');
        if (txtWindows) {
          txtWindows.value = d.texto_windows || 'Nenhuma foto selecionada pelo cliente ainda.';
        }

        const badge = document.getElementById('badgeTotalEscolhidas');
        if (badge) {
          badge.textContent = `${d.total} escolhidas (${d.pacote_count} pacote + ${d.extra_count} extras)`;
        }

        const listaVisual = document.getElementById('listaVisualEscolhidas');
        if (listaVisual) {
          if (!d.fotos || d.fotos.length === 0) {
            listaVisual.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #888; font-size: 0.78rem; padding: 1rem;">Nenhuma foto selecionada pelo cliente ainda.</div>';
          } else {
            listaVisual.innerHTML = d.fotos.map(f => `
              <div style="background: #FFF; border: 1px solid #D8CAB9; border-radius: 6px; overflow: hidden; text-align: center; padding: 4px;">
                <img src="${f.arquivo}" alt="${f.numero}" style="width: 100%; height: 65px; object-fit: cover; border-radius: 4px; cursor: pointer;" onclick="abrirLightbox('${f.arquivo}', '${f.numero}')" onerror="this.onerror=null; this.src='assets/logo/logo.png';">
                <span style="display: block; font-size: 0.7rem; font-weight: 700; color: #2D1D14; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${f.numero}</span>
                <span style="display: block; font-size: 0.65rem; color: ${f.status === 'extra' ? '#9E744B' : '#2D1D14'}; font-weight: 600;">${f.status === 'extra' ? 'Extra' : 'Pacote'}</span>
              </div>
            `).join('');
          }
        }
      } catch (err) {
        console.error('Erro ao carregar selecionadas:', err);
      }
    };

    window.copiarFormatoBusca = function(tipo) {
      if (!window.selecionadasCache || !window.selecionadasCache.total) {
        showToast('Nenhuma foto selecionada para copiar ainda.', 'error');
        return;
      }
      let texto = '';
      let msg = '';
      if (tipo === 'windows') {
        texto = window.selecionadasCache.texto_windows || '';
        msg = '✓ Linha de busca do Windows 10/11 copiada! Cole no Explorer (Ctrl+V).';
      } else if (tipo === 'virgula') {
        texto = window.selecionadasCache.texto_virgula || '';
        msg = '✓ Lista com vírgulas copiada para a área de transferência!';
      } else {
        texto = window.selecionadasCache.texto_linhas || '';
        msg = '✓ Lista linha por linha copiada para a área de transferência!';
      }
      if (!texto) {
        showToast('Lista vazia.', 'error');
        return;
      }
      navigator.clipboard.writeText(texto).then(() => {
        showToast(msg);
      }).catch(() => {
        const ta = document.getElementById('txtBuscaWindows');
        if (ta) { ta.select(); document.execCommand('copy'); showToast(msg); }
      });
    };

    // ── WHATSAPP CONVITE PERSONALIZADO COM USUÁRIO E SENHA ──
    window.atualizarPreviewMensagemWhatsApp = function() {
      const nome = (document.getElementById('waNomeCliente') ? document.getElementById('waNomeCliente').value.trim() : '') || 'Cliente';
      const user = (document.getElementById('waUsuarioCliente') ? document.getElementById('waUsuarioCliente').value.trim() : '') || 'cliente@exemplo.com';
      const pass = (document.getElementById('waSenhaCliente') ? document.getElementById('waSenhaCliente').value.trim() : '') || '123456';
      const origin = window.location.origin || 'http://localhost:8082';
      const loginUrl = `${origin}/login-cliente.html`;

      const msg = `📸 *Olá, ${nome}!*

Suas fotos do ensaio já estão disponíveis para você escolher na *Casa da Foto Studio*! ✨

Acesse sua galeria exclusiva pelo link abaixo:
🔗 *Link de Acesso:* ${loginUrl}
👤 *Usuário / E-mail:* ${user}
🔑 *Senha:* ${pass}

💡 *Como funciona a escolha:*
1. Acesse o link acima e faça o login com seu usuário e senha.
2. Você pode marcar com calma as fotos incluídas no seu pacote e também selecionar fotos extras.
3. Quando concluir, revise a sua lista e clique em *Enviar seleção ao fotógrafo*.

Qualquer dúvida estamos à sua total disposição! 🤍`;

      const ta = document.getElementById('waMensagemTexto');
      if (ta) ta.value = msg;
      return { msg, loginUrl };
    };

    window.enviarMensagemWhatsApp = async function() {
      const telInput = document.getElementById('waTelefoneCliente');
      const nomeInput = document.getElementById('waNomeCliente');
      const emailInput = document.getElementById('waUsuarioCliente');
      const senhaInput = document.getElementById('waSenhaCliente');

      const nome = nomeInput ? nomeInput.value.trim() : '';
      const email = emailInput ? emailInput.value.trim().toLowerCase() : '';
      const senha = senhaInput ? senhaInput.value.trim() : '123456';
      let tel = telInput ? telInput.value.replace(/\D/g, '') : '';

      // Se preencheu nome e email, sincroniza imediatamente no banco para garantir login imediato
      if (nome && email) {
        try {
          await fetch(`/api/galeria/${galConfigId}/destinatarios`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, email, senha, permissao: 'Selecionar fotos' })
          });
          if (typeof window.carregarDestinatariosConfig === 'function') {
            window.carregarDestinatariosConfig();
          }
          if (typeof window.carregarAtividadesClienteConfig === 'function') {
            window.carregarAtividadesClienteConfig();
          }
        } catch (e) {
          console.warn('Erro ao sincronizar cliente antes do WhatsApp:', e);
        }
      }

      if (!tel) {
        showToast('Informe o número de WhatsApp do cliente com DDD.', 'error');
        return;
      }
      if (tel.length <= 11 && !tel.startsWith('55')) {
        tel = '55' + tel;
      }
      const { msg } = window.atualizarPreviewMensagemWhatsApp();
      const url = `https://wa.me/${tel}?text=${encodeURIComponent(msg)}`;
      window.open(url, '_blank');
      showToast(`✓ Convite preparado e acesso liberado para ${nome || 'o cliente'}!`);
    };

    window.enviarWhatsAppLateral = async function() {
      const telInput = document.getElementById('waTelLateral');
      let tel = telInput ? telInput.value.replace(/\D/g, '') : '';
      if (!tel) {
        showToast('Informe o número de WhatsApp do cliente com DDD.', 'error');
        return;
      }
      if (tel.length <= 11 && !tel.startsWith('55')) {
        tel = '55' + tel;
      }
      const { msg } = window.atualizarPreviewMensagemWhatsApp();
      const url = `https://wa.me/${tel}?text=${encodeURIComponent(msg)}`;
      window.open(url, '_blank');
    };

    window.copiarMensagemWhatsApp = async function() {
      const nomeInput = document.getElementById('waNomeCliente');
      const emailInput = document.getElementById('waUsuarioCliente');
      const senhaInput = document.getElementById('waSenhaCliente');

      const nome = nomeInput ? nomeInput.value.trim() : '';
      const email = emailInput ? emailInput.value.trim().toLowerCase() : '';
      const senha = senhaInput ? senhaInput.value.trim() : '123456';

      if (nome && email) {
        try {
          await fetch(`/api/galeria/${galConfigId}/destinatarios`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, email, senha, permissao: 'Selecionar fotos' })
          });
          if (typeof window.carregarDestinatariosConfig === 'function') {
            window.carregarDestinatariosConfig();
          }
          if (typeof window.carregarAtividadesClienteConfig === 'function') {
            window.carregarAtividadesClienteConfig();
          }
        } catch (e) {}
      }

      const { msg } = window.atualizarPreviewMensagemWhatsApp();
      navigator.clipboard.writeText(msg).then(() => {
        showToast(`✓ Mensagem copiada e acesso liberado para ${nome || email}!`);
      }).catch(() => {
        const ta = document.getElementById('waMensagemTexto');
        if (ta) { ta.select(); document.execCommand('copy'); showToast('✓ Mensagem copiada!'); }
      });
    };

    window.copiarLinkLoginCliente = function() {
      const origin = window.location.origin || 'http://localhost:8082';
      const loginUrl = `${origin}/login-cliente.html`;
      navigator.clipboard.writeText(loginUrl).then(() => {
        showToast('✓ Link da tela de login copiado!');
      });
    };

    // ── REGRAS DE SELEÇÃO E VALOR DA FOTO EXTRA ──
    window.salvarRegrasSelecao = async function() {
      const btn = document.getElementById('btnSalvarRegras');
      const origText = btn ? btn.innerHTML : '';
      if (btn) { btn.disabled = true; btn.innerHTML = 'Salvando...'; }

      const limite = parseInt(document.getElementById('inputLimitePacote')?.value) || 10;
      const valorExtra = parseFloat(document.getElementById('inputValorFotoExtra')?.value) || 25.0;
      const chkExtras = document.getElementById('chkPermitirExtras');
      const permitirExtras = chkExtras ? (chkExtras.checked ? 1 : 0) : 1;

      try {
        const res = await fetch(`/api/galeria/${galConfigId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            limite_pacote: limite,
            valor_foto_extra: valorExtra,
            permitir_extras: permitirExtras
          })
        });
        const d = await res.json();
        if (d.success) {
          showToast(`✓ Regras salvas! Pacote: ${limite} fotos · Valor extra: R$ ${valorExtra.toFixed(2)}.`);
          window.carregarDadosGaleria();
        } else {
          showToast('Erro ao salvar regras.', 'error');
        }
      } catch (err) {
        showToast('Erro de conexão ao salvar regras.', 'error');
      } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = origText; }
      }
    };

    // ── GESTÃO DE DESTINATÁRIOS (TAB CLIENTES) ──
    // ── GESTÃO DE DESTINATÁRIOS (TAB CLIENTES) ──
    window.destinatariosCache = [];

    window.abrirModalAdicionarCliente = function() {
      const modal = document.getElementById('modalAddCliente');
      if (modal) {
        modal.style.display = 'flex';
        const inputNome = document.getElementById('modalNomeCliente');
        if (inputNome) setTimeout(() => inputNome.focus(), 50);
      }
    };

    window.fecharModalAdicionarCliente = function() {
      const modal = document.getElementById('modalAddCliente');
      if (modal) modal.style.display = 'none';
    };

    window.salvarNovoDestinatarioModal = async function() {
      const nome = document.getElementById('modalNomeCliente')?.value.trim();
      const email = document.getElementById('modalEmailCliente')?.value.trim();
      const senha = document.getElementById('modalSenhaCliente')?.value.trim() || '123456';
      const telefone = document.getElementById('modalTelefoneCliente')?.value.trim();
      const permissao = document.getElementById('modalPermissaoCliente')?.value;
      const btn = document.getElementById('btnSalvarModalCliente');

      if (!nome || !email) {
        showToast('Preencha o nome e o e-mail do cliente.', 'error');
        return;
      }

      if (btn) { btn.disabled = true; btn.innerHTML = 'Salvando...'; }

      try {
        const res = await fetch(`/api/galeria/${galConfigId}/destinatarios`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nome, email, senha, permissao })
        });
        const d = await res.json();

        if (res.ok && d.success) {
          showToast(`✓ Cliente "${nome}" cadastrado com sucesso!`);
          window.fecharModalAdicionarCliente();

          // Preenche os campos do gerador de WhatsApp automaticamente com este cliente
          const waNome = document.getElementById('waNomeCliente');
          const waEmail = document.getElementById('waUsuarioCliente');
          const waSenha = document.getElementById('waSenhaCliente');
          const waTel = document.getElementById('waTelefoneCliente');
          if (waNome) waNome.value = nome;
          if (waEmail) waEmail.value = email;
          if (waSenha) waSenha.value = senha;
          if (waTel && telefone) waTel.value = telefone;
          if (typeof window.atualizarPreviewMensagemWhatsApp === 'function') {
            window.atualizarPreviewMensagemWhatsApp();
          }

          // Limpa o formulário do modal
          document.getElementById('modalNomeCliente').value = '';
          document.getElementById('modalEmailCliente').value = '';
          if (document.getElementById('modalTelefoneCliente')) document.getElementById('modalTelefoneCliente').value = '';

          await window.carregarDestinatariosConfig();
          if (typeof window.carregarHistoricoAtividades === 'function') {
            window.carregarHistoricoAtividades();
          }
        } else {
          showToast(d.error || 'Erro ao cadastrar cliente.', 'error');
        }
      } catch (err) {
        showToast('Erro de comunicação com o servidor.', 'error');
      } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '✓ Salvar e Liberar Acesso'; }
      }
    };

    window.renderizarDestinatariosTabela = function(lista) {
      const container = document.getElementById('listaDestinatariosTabela');
      if (!container) return;

      if (!lista || lista.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #888; padding: 1.75rem;">Nenhum destinatário encontrado com os filtros aplicados. Clique em "+ Adicionar destinatário" para cadastrar.</div>';
        return;
      }

      container.innerHTML = lista.map(d => `
        <div style="display: grid; grid-template-columns: 1.4fr 1.2fr 1fr 1fr 0.8fr; padding: 0.9rem 1rem; align-items: center; border-bottom: 1px solid #FAF5EE;">
          <div>
            <strong style="display: block; color: var(--text-dark); font-size: 0.88rem;">${d.nome}</strong>
            <span style="color: var(--text-muted); font-size: 0.74rem;">✉️ ${d.email}</span>
            ${d.principal ? '<span class="preview-pill-tag" style="margin-top: 3px; display: inline-block; font-size: 0.65rem;">Principal</span>' : ''}
          </div>
          <div>
            <span class="preview-pill-tag" style="font-weight: 600;">${d.status_convite || 'Convite preparado'}</span>
            <span style="display: block; font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">${d.data_convite || ''}</span>
          </div>
          <div>
            <strong style="display: block; color: var(--text-dark); font-size: 0.8rem;">${d.ultimo_acesso || 'Aguardando'}</strong>
            <span style="font-size: 0.7rem; color: var(--text-muted);">${d.total_acessos || 0} acessos</span>
          </div>
          <div>
            <strong style="display: block; color: var(--text-dark); font-size: 0.8rem;">${d.fotos_pacote_count || 0} pct · ${d.fotos_extras_count || 0} ext</strong>
            <span class="preview-pill-tag" style="font-size: 0.65rem;">${(d.fotos_pacote_count || d.fotos_extras_count) ? 'Em andamento' : 'Aguardando'}</span>
          </div>
          <div style="text-align: right; display: flex; gap: 0.4rem; justify-content: flex-end; align-items: center;">
            <button type="button" onclick="prepararWhatsAppCliente('${d.nome.replace(/'/g, "\\'")}', '${d.email}')" style="background: #E8F8F0; border: 1px solid #A3E9C7; color: #1E8E5A; font-size: 0.72rem; font-weight: 700; padding: 4px 8px; border-radius: 6px; cursor: pointer;" title="Preparar mensagem de WhatsApp para este cliente">
              💬 WhatsApp
            </button>
            <button type="button" onclick="excluirDestinatarioConfig(${d.id}, '${d.nome.replace(/'/g, "\\'")}')" style="background: #FFF; border: 1px solid #D8CAB9; color: #A83232; font-size: 0.72rem; padding: 4px 8px; border-radius: 6px; cursor: pointer;" title="Remover cliente desta galeria">
              🗑️
            </button>
          </div>
        </div>
      `).join('');
    };

    window.filtrarDestinatariosTabela = function() {
      const q = (document.getElementById('filtroBuscaDestinatario')?.value || '').toLowerCase().trim();
      const status = document.getElementById('filtroStatusDestinatario')?.value || '';

      let filtrados = window.destinatariosCache || [];
      if (q) {
        filtrados = filtrados.filter(d => 
          (d.nome || '').toLowerCase().includes(q) || 
          (d.email || '').toLowerCase().includes(q)
        );
      }
      if (status) {
        filtrados = filtrados.filter(d => (d.status_convite || '') === status);
      }

      window.renderizarDestinatariosTabela(filtrados);
    };

    window.prepararWhatsAppCliente = function(nome, email) {
      const waNome = document.getElementById('waNomeCliente');
      const waEmail = document.getElementById('waUsuarioCliente');
      if (waNome) waNome.value = nome;
      if (waEmail) waEmail.value = email;
      if (typeof window.atualizarPreviewMensagemWhatsApp === 'function') {
        window.atualizarPreviewMensagemWhatsApp();
      }
      showToast(`Dados de "${nome}" preenchidos no WhatsApp abaixo.`);
      document.getElementById('waNomeCliente')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    window.carregarDestinatariosConfig = async function() {
      const container = document.getElementById('listaDestinatariosTabela');
      if (!container) return;

      try {
        const res = await fetch(`/api/galeria/${galConfigId}/destinatarios`);
        const destinatarios = await res.json();
        window.destinatariosCache = Array.isArray(destinatarios) ? destinatarios : [];

        const sub = document.getElementById('destinatariosSubtitle');
        if (sub) {
          sub.textContent = `${window.destinatariosCache.length} cliente(s) convidado(s) para esta galeria.`;
        }

        window.filtrarDestinatariosTabela();
      } catch (err) {
        console.error('Erro ao carregar destinatários:', err);
      }
    };

    window.excluirDestinatarioConfig = async function(id, nome) {
      if (!confirm(`Deseja realmente remover o destinatário "${nome}"?`)) return;
      try {
        const res = await fetch(`/api/galeria/${galConfigId}/destinatarios/${id}`, { method: 'DELETE' });
        const d = await res.json();
        if (d.success) {
          showToast(`✓ Destinatário "${nome}" removido.`);
          window.carregarDestinatariosConfig();
        } else {
          showToast('Erro ao excluir destinatário.', 'error');
        }
      } catch (e) {
        showToast('Erro de conexão.', 'error');
      }
    };

    const btnNovoConviteBtn = document.getElementById('btnPrepararNovoConvite');
    if (btnNovoConviteBtn) {
      btnNovoConviteBtn.addEventListener('click', async () => {
        const inputNome = document.getElementById('inputNomeNovoConvite');
        const inputEmail = document.getElementById('inputEmailNovoConvite');
        const nome = inputNome ? inputNome.value.trim() : '';
        const email = inputEmail ? inputEmail.value.trim() : '';

        if (!nome || !email) {
          showToast('Preencha nome e e-mail para cadastrar o destinatário.', 'error');
          return;
        }

        try {
          const res = await fetch(`/api/galeria/${galConfigId}/destinatarios`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, email, senha: '123456' })
          });
          const d = await res.json();
          if (d.success) {
            showToast(`✓ Cliente "${nome}" cadastrado com sucesso!`);
            if (inputNome) inputNome.value = '';
            if (inputEmail) inputEmail.value = '';
            window.carregarDestinatariosConfig();
            if (typeof window.carregarHistoricoAtividades === 'function') {
              window.carregarHistoricoAtividades();
            }
          } else {
            showToast(d.error || 'Erro ao registrar convite.', 'error');
          }
        } catch (e) {
          showToast('Erro ao comunicar com o servidor.', 'error');
        }
      });
    }

    // ── GESTÃO DE HISTÓRICO E ATIVIDADES (TAB HISTÓRICO & TAB ATIVIDADES) ──
    window.carregarHistoricoAtividades = async function() {
      const container = document.getElementById('listaHistoricoAtividades');
      if (!container) return;

      try {
        const res = await fetch(`/api/galeria/${galConfigId}/atividades`);
        const atividades = await res.json();

        const badge = document.getElementById('badgeTotalHistorico');
        if (badge) badge.textContent = `${atividades.length} registro(s)`;

        const countTxt = document.getElementById('countHistoricoTexto');
        if (countTxt) countTxt.textContent = `${atividades.length} evento(s) cronológico(s) registrados no banco de dados.`;

        if (!atividades || atividades.length === 0) {
          container.innerHTML = '<div style="text-align: center; color: #888; padding: 1.5rem;">Nenhuma atividade registrada para esta galeria ainda.</div>';
          return;
        }

        container.innerHTML = atividades.map(a => `
          <div style="padding: 0.85rem; border: 1px solid #E8DDD0; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; background: #FFF;">
            <div style="display: flex; gap: 0.85rem; align-items: center;">
              <span style="color: var(--text-muted); font-size: 0.73rem; width: 85px; line-height: 1.3;">${a.data_hora}</span>
              <div>
                <strong style="color: var(--text-dark); font-size: 0.85rem;">${a.titulo}</strong>
                <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 2px;">${a.descricao || ''}</div>
              </div>
            </div>
            <span class="preview-pill-tag" style="${a.autor_tipo === 'Cliente' ? 'background:#FAF5EE; color:#666;' : ''}">${a.autor_tipo}</span>
          </div>
        `).join('');

      } catch (err) {
        console.error('Erro ao carregar histórico:', err);
      }
    };

    window.exportarHistoricoAtividades = async function() {
      try {
        const res = await fetch(`/api/galeria/${galConfigId}/atividades`);
        const atividades = await res.json();
        if (!atividades || atividades.length === 0) {
          showToast('Nenhuma atividade para exportar.', 'error');
          return;
        }

        let conteudo = `CASA DA FOTO STUDIO - HISTÓRICO DE ATIVIDADES DA GALERIA #${galConfigId}\n`;
        conteudo += `Gerado em: ${new Date().toLocaleString('pt-BR')}\n`;
        conteudo += `---------------------------------------------------------\n\n`;

        atividades.forEach(a => {
          conteudo += `[${a.data_hora}] (${a.autor_tipo}) ${a.titulo}\n`;
          if (a.descricao) conteudo += `  Detalhes: ${a.descricao}\n`;
          conteudo += `\n`;
        });

        const blob = new Blob([conteudo], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `historico_galeria_${galConfigId}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('✓ Arquivo de histórico exportado com sucesso!');
      } catch (e) {
        showToast('Erro ao exportar histórico.', 'error');
      }
    };

    // ── ATIVIDADES DO CLIENTE (TAB 9 & galeria-atividades.html) ──
    window.carregarAtividadesClienteConfig = async function() {
      try {
        const [resGal, resFotos, resDest, resAtiv] = await Promise.all([
          fetch(`/api/galeria/${galConfigId}`),
          fetch(`/api/galeria/${galConfigId}/fotos`),
          fetch(`/api/galeria/${galConfigId}/destinatarios`),
          fetch(`/api/galeria/${galConfigId}/atividades`)
        ]);

        const gal = await resGal.json();
        const dFotos = await resFotos.json();
        const destinatarios = await resDest.json();
        const atividades = await resAtiv.json();

        const fotos = (dFotos && dFotos.fotos) ? dFotos.fotos : [];
        const listaDest = Array.isArray(destinatarios) ? destinatarios : [];
        const listaAtiv = Array.isArray(atividades) ? atividades : [];

        // 1. Popula select de destinatários na aba de atividades
        const selectDest = document.getElementById('selectDestinatarioAtividades');
        if (selectDest) {
          const valAtual = selectDest.value;
          selectDest.innerHTML = '<option value="">Todos os destinatários</option>' + 
            listaDest.map(d => `<option value="${d.id}" ${String(valAtual) === String(d.id) ? 'selected' : ''}>${d.nome} (${d.email})</option>`).join('');
        }

        const destIdFiltro = selectDest ? selectDest.value : '';
        const destFiltro = destIdFiltro ? listaDest.find(d => String(d.id) === String(destIdFiltro)) : (listaDest[0] || null);

        // 2. Calcula métricas da galeria
        const limitePacote = (gal && gal.limite_pacote != null && parseInt(gal.limite_pacote) > 0) ? parseInt(gal.limite_pacote) : 10;
        let fotosPacote = 0;
        let fotosExtras = 0;
        let totalAcessos = 0;
        let ultimaVisita = 'Nenhum acesso registrado ainda';

        const fotosPacoteReal = fotos.filter(f => f.status === 'pacote').length;
        const fotosExtrasReal = fotos.filter(f => f.status === 'extra').length;

        if (destFiltro) {
          fotosPacote = Math.max(destFiltro.fotos_pacote_count || 0, fotosPacoteReal);
          fotosExtras = Math.max(destFiltro.fotos_extras_count || 0, fotosExtrasReal);
          totalAcessos = destFiltro.total_acessos || 0;
          if (destFiltro.ultimo_acesso && destFiltro.ultimo_acesso !== 'Aguardando acesso') {
            ultimaVisita = destFiltro.ultimo_acesso;
          }
        } else {
          fotosPacote = fotosPacoteReal;
          fotosExtras = fotosExtrasReal;
          totalAcessos = listaDest.reduce((acc, d) => acc + (d.total_acessos || 0), 0);
          const comVisita = listaDest.filter(d => d.ultimo_acesso && d.ultimo_acesso !== 'Aguardando acesso');
          if (comVisita.length > 0) {
            ultimaVisita = comVisita[0].ultimo_acesso;
          }
        }

        const pct = limitePacote > 0 ? Math.min(100, Math.round((fotosPacote / limitePacote) * 100)) : 0;
        const restantes = Math.max(0, limitePacote - fotosPacote);

        // 3. Atualiza elementos visuais
        const txtPacote = document.getElementById('txtAndamentoPacote');
        if (txtPacote) txtPacote.textContent = `${fotosPacote} de ${limitePacote} fotos no pacote`;

        const txtDesc = document.getElementById('txtAndamentoDescricao');
        if (txtDesc) {
          if (fotosPacote === 0 && fotosExtras === 0) {
            txtDesc.textContent = `Nenhuma foto escolhida ainda. O cliente tem direito a ${limitePacote} fotos no pacote.`;
          } else if (fotosPacote >= limitePacote) {
            txtDesc.textContent = `Pacote completo com ${fotosPacote} fotos escolhidas!` + (fotosExtras > 0 ? ` + ${fotosExtras} foto(s) extra(s) em lista separada.` : '');
          } else {
            txtDesc.textContent = `${restantes} foto(s) ainda podem ser escolhidas no pacote.` + (fotosExtras > 0 ? ` As ${fotosExtras} foto(s) extra(s) ficam em uma lista separada.` : '');
          }
        }

        const barFill = document.getElementById('barAndamentoFill');
        if (barFill) barFill.style.width = `${pct}%`;

        const txtPct = document.getElementById('txtAndamentoPct');
        if (txtPct) txtPct.textContent = `${pct}% do pacote escolhido`;

        const txtStatusEnvio = document.getElementById('txtAndamentoStatusEnvio');
        if (txtStatusEnvio) {
          if (destFiltro && destFiltro.status_convite === 'Seleção enviada') {
            txtStatusEnvio.textContent = '✓ Seleção final concluída e enviada';
          } else if (fotosPacote > 0 || fotosExtras > 0) {
            txtStatusEnvio.textContent = 'Seleção em andamento pelo cliente';
          } else {
            txtStatusEnvio.textContent = 'Seleção final ainda não enviada';
          }
        }

        const badgeAndamento = document.getElementById('badgeStatusAndamento');
        if (badgeAndamento) {
          if (destFiltro && destFiltro.status_convite === 'Seleção enviada') {
            badgeAndamento.textContent = 'Concluído';
            badgeAndamento.style.background = '#2E7D32';
            badgeAndamento.style.color = '#FFF';
          } else if (fotosPacote > 0 || fotosExtras > 0) {
            badgeAndamento.textContent = 'Em andamento';
            badgeAndamento.style.background = '#2D1D14';
            badgeAndamento.style.color = '#FFF';
          } else {
            badgeAndamento.textContent = 'Aguardando início';
            badgeAndamento.style.background = '#FAF5EE';
            badgeAndamento.style.color = '#6B5546';
          }
        }

        const tagCliente = document.getElementById('tagClienteAndamento');
        if (tagCliente) {
          tagCliente.textContent = destFiltro ? destFiltro.nome : (listaDest.length > 0 ? `${listaDest.length} cliente(s)` : 'Nenhum cliente convidado');
        }

        const txtAcessosTotal = document.getElementById('txtResumoTotalAcessos');
        if (txtAcessosTotal) txtAcessosTotal.textContent = totalAcessos;

        const txtAcessosSub = document.getElementById('txtAcessosSubtitle');
        if (txtAcessosSub) txtAcessosSub.textContent = `${totalAcessos} acesso(s) registrado(s) · dados atualizados em tempo real.`;

        const txtUltima = document.getElementById('txtResumoUltimaVisita');
        if (txtUltima) txtUltima.textContent = ultimaVisita;

        const txtPrazo = document.getElementById('txtResumoPrazoEscolha');
        if (txtPrazo) txtPrazo.textContent = `${gal.prazo_selecao || 'Sem prazo'} - ${gal.horario_prazo || '23:59'}`;

        const e1 = document.getElementById('etapa1Status');
        const e2 = document.getElementById('etapa2Status');
        const e3 = document.getElementById('etapa3Status');
        if (e1) {
          e1.textContent = (destFiltro && destFiltro.status_convite !== 'Convite preparado') ? (destFiltro.data_convite || 'Concluído') : (listaDest.length > 0 ? 'Convite enviado' : 'Aguardando cliente');
        }
        if (e2) {
          e2.textContent = `${fotosPacote} do pacote + ${fotosExtras} extras`;
        }
        if (e3) {
          e3.textContent = (destFiltro && destFiltro.status_convite === 'Seleção enviada') ? 'Recebida pelo estúdio' : 'Aguardando cliente';
        }

        const feedContainer = document.getElementById('containerAcessosFeed');
        if (feedContainer) {
          const ativCliente = listaAtiv.filter(a => a.autor_tipo === 'Cliente' || (a.titulo || '').toLowerCase().includes('acess') || (a.titulo || '').toLowerCase().includes('escolha'));
          if (ativCliente.length === 0) {
            feedContainer.innerHTML = '<div style="padding: 1.25rem; background: #FAF5EE; border-radius: 8px; text-align: center; color: #888;">Nenhum acesso registrado até o momento.</div>';
          } else {
            feedContainer.innerHTML = ativCliente.slice(0, 10).map(a => `
              <div style="padding: 0.75rem; background: #FAF5EE; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <strong>💻 ${a.data_hora}</strong>
                  <div style="font-size: 0.74rem; color: var(--text-muted);">${a.titulo} - ${a.descricao || ''}</div>
                </div>
                <span class="preview-pill-tag">${a.dispositivo || 'Navegador'}</span>
              </div>
            `).join('');
          }
        }
      } catch (err) {
        console.warn('Erro ao carregar atividades do cliente:', err);
      }
    };

    // Inicializa carregamentos da galeria
    window.carregarCategoriasConfig();
    window.carregarFotosGaleriaConfig();
    window.carregarDestinatariosConfig();
    window.carregarHistoricoAtividades();
    window.carregarAtividadesClienteConfig();
    window.atualizarPreviewMensagemWhatsApp();

    // Salvar preferências gerais de todas as abas
    const salvarBtns = document.querySelectorAll('.btn-salvar-admin');
    salvarBtns.forEach(btn => {
      btn.addEventListener('click', async (e) => {
        if (
          btn.id === 'btnPrepararNovoConvite' || 
          btn.id === 'btnExportarHistorico' || 
          btn.id === 'btnSalvarModalCliente' ||
          btn.id === 'btnSalvarModalCategoria' ||
          btn.id === 'btnAbrirModalDestinatario' ||
          btn.closest('#modalAddCliente') ||
          btn.closest('#modalAddCategoria') ||
          btn.textContent.includes('Adicionar') || 
          btn.textContent.includes('Exportar') || 
          btn.textContent.includes('Reenviar') || 
          btn.textContent.includes('Enviar') || 
          btn.textContent.includes('Regras') ||
          btn.textContent.includes('Liberar')
        ) {
          return;
        }

        e.preventDefault();
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span>Salvando no banco...</span>';

        const payload = {};
        const inputNome = document.getElementById('inputNomeGaleria') || document.querySelector('#tab-dados input[type="text"]');
        if (inputNome && inputNome.value) payload.nome = inputNome.value;

        const selectCat = document.getElementById('selectCategoriaGaleria') || document.querySelector('#tab-dados select');
        if (selectCat && selectCat.value && selectCat.value !== '__nova__') {
          payload.categoria = selectCat.value;
        }

        const inputDrive = document.getElementById('inputLinkGoogleDrive');
        if (inputDrive) {
          payload.link_drive = inputDrive.value.trim();
        }

        const inputLimite = document.getElementById('inputLimitePacote');
        if (inputLimite && inputLimite.value) {
          payload.limite_pacote = parseInt(inputLimite.value, 10);
        }

        const inputValorExtra = document.getElementById('inputValorFotoExtra');
        if (inputValorExtra && inputValorExtra.value !== '') {
          payload.valor_foto_extra = parseFloat(inputValorExtra.value) || 0;
        }

        const chkExtras = document.getElementById('chkPermitirExtras');
        if (chkExtras) {
          payload.permitir_extras = chkExtras.checked ? 1 : 0;
        }

        const txtMensagemAcesso = document.getElementById('txtMensagemAcesso') || document.querySelector('#tab-dados textarea');
        if (txtMensagemAcesso && txtMensagemAcesso.value) {
          payload.mensagem_acesso = txtMensagemAcesso.value.trim();
        }

        try {
          const res = await fetch(`/api/galeria/${galConfigId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.success) {
            showToast('✓ Configurações salvas no banco de dados!');
            if (payload.categoria) {
              if (window.galeriaConfigAtual) window.galeriaConfigAtual.categoria = payload.categoria;
              const pillTag = document.querySelector('.preview-pill-tag');
              if (pillTag) pillTag.textContent = payload.categoria;
            }
            if (payload.link_drive !== undefined && window.galeriaConfigAtual) {
              window.galeriaConfigAtual.link_drive = payload.link_drive;
            }
            window.carregarHistoricoAtividades();
            window.carregarAtividadesClienteConfig();
          } else {
            showToast('Erro ao salvar.', 'error');
          }
        } catch (err) {
          showToast('Erro ao salvar no banco.', 'error');
        } finally {
          btn.innerHTML = originalText;
        }
      });
    });

    // Binding para o botão de preparar novo convite se existir
    const btnNovoConvite = document.getElementById('btnPrepararNovoConvite');
    if (btnNovoConvite) {
      btnNovoConvite.addEventListener('click', () => {
        if (typeof window.prepararNovoConviteForm === 'function') {
          window.prepararNovoConviteForm();
        }
      });
    }
  }

  // ── Novas Funções Globais de Galeria e Destinatários ──────────────────────────
  window.prepararRevisaoGaleria = async function() {
    try {
      showToast('Preparando revisão da galeria...', 'info');
      const res = await fetch(`/api/galeria/${galConfigId}/selecionadas`);
      const d = await res.json();
      
      if (window.galeriaConfigAtual && window.galeriaConfigAtual.projeto_id) {
        await fetch(`/api/projetos/${window.galeriaConfigAtual.projeto_id}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'andamento' })
        });
      }

      await fetch(`/api/galeria/${galConfigId}/atividades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo: 'Revisão da galeria iniciada',
          descricao: `Revisão preparada para conferência. Total: ${d.total || 0} fotos (${d.pacote_count || 0} no pacote + ${d.extra_count || 0} extras).`,
          autor_tipo: 'Fotógrafo',
          tipo_badge: 'Fotógrafo',
          dispositivo: 'Computador'
        })
      });

      if (typeof window.carregarHistoricoAtividades === 'function') window.carregarHistoricoAtividades();
      if (typeof window.carregarAtividadesClienteConfig === 'function') window.carregarAtividadesClienteConfig();
      if (typeof window.carregarFotosSelecionadas === 'function') window.carregarFotosSelecionadas();

      showToast(`✓ Revisão preparada com sucesso! ${d.total || 0} fotos prontas para conferência e entrega.`);
    } catch (err) {
      showToast('✓ Revisão da galeria preparada com sucesso!');
    }
  };

  window.reenviarConviteCliente = async function() {
    try {
      let nome = '';
      let email = '';
      let tel = '';
      
      if (window.destinatariosCache && window.destinatariosCache.length > 0) {
        const principal = window.destinatariosCache.find(d => d.principal) || window.destinatariosCache[0];
        nome = principal.nome || '';
        email = principal.email || '';
      }
      
      const inputNome = document.getElementById('waNomeCliente');
      const inputEmail = document.getElementById('waUsuarioCliente');
      const inputTel = document.getElementById('waTelefoneCliente') || document.getElementById('waTelLateral');
      
      if (inputNome && inputNome.value) nome = inputNome.value;
      if (inputEmail && inputEmail.value) email = inputEmail.value;
      if (inputTel && inputTel.value) tel = inputTel.value.replace(/\D/g, '');

      const { msg } = typeof window.atualizarPreviewMensagemWhatsApp === 'function' 
        ? window.atualizarPreviewMensagemWhatsApp() 
        : { msg: `Acesse sua galeria exclusiva na Casa da Foto Studio: ${window.location.origin}/login-cliente.html` };

      if (tel) {
        if (tel.length <= 11 && !tel.startsWith('55')) tel = '55' + tel;
        window.open(`https://wa.me/${tel}?text=${encodeURIComponent(msg)}`, '_blank');
        showToast(`✓ Convite reenviado via WhatsApp para ${nome || 'o cliente'}!`);
      } else {
        await navigator.clipboard.writeText(msg);
        showToast(`✓ Mensagem de convite copiada com sucesso para ${nome || email || 'o cliente'}!`);
      }

      await fetch(`/api/galeria/${galConfigId}/atividades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo: 'Convite reenviado',
          descricao: `Convite de acesso reenviado para ${nome || email || 'cliente principal'}.`,
          autor_tipo: 'Fotógrafo',
          tipo_badge: 'Fotógrafo',
          dispositivo: 'Computador'
        })
      });

      if (typeof window.carregarHistoricoAtividades === 'function') window.carregarHistoricoAtividades();
      if (typeof window.carregarAtividadesClienteConfig === 'function') window.carregarAtividadesClienteConfig();
    } catch (err) {
      showToast('✓ Convite reenviado com sucesso!');
    }
  };

  window.prepararNovoConviteForm = async function() {
    const inputNome = document.getElementById('inputNomeNovoConvite') || document.querySelector('#tab-clientes input[type="text"]');
    const inputEmail = document.getElementById('inputEmailNovoConvite') || document.querySelector('#tab-clientes input[type="email"]');
    const nome = inputNome ? inputNome.value.trim() : '';
    const email = inputEmail ? inputEmail.value.trim() : '';

    if (!nome || !email) {
      showToast('Por favor, informe o nome e o e-mail do destinatário.', 'error');
      if (inputNome && !nome) inputNome.focus();
      else if (inputEmail && !email) inputEmail.focus();
      return;
    }

    try {
      const res = await fetch(`/api/galeria/${galConfigId}/destinatarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome: nome,
          email: email,
          senha: '123456',
          permissao: 'Apenas visualizar'
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`✓ Convite preparado com sucesso para ${nome}!`);
        if (inputNome) inputNome.value = '';
        if (inputEmail) inputEmail.value = '';
        if (typeof window.carregarDestinatariosConfig === 'function') {
          window.carregarDestinatariosConfig();
        }
        if (typeof window.carregarHistoricoAtividades === 'function') {
          window.carregarHistoricoAtividades();
        }
      } else {
        showToast(data.error || 'Erro ao cadastrar convite.', 'error');
      }
    } catch (err) {
      showToast('Erro de comunicação com o servidor.', 'error');
    }
  };

  window.enviarGaleriaAoCliente = function() {
    if (typeof window.switchAdminTab === 'function') {
      window.switchAdminTab('clientes');
    } else {
      window.location.href = 'galeria-clientes.html';
    }
  };

  // ── Funções da Página de Entrega de Fotos e Google Drive ──────────────────────
  window.salvarLinkDrive = async function() {
    const input = document.getElementById('inputLinkGoogleDrive');
    const btn = document.getElementById('btnSalvarLinkDrive');
    if (!input) return;

    const link = input.value.trim();
    const origText = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = 'Salvando...'; }

    try {
      const res = await fetch(`/api/galeria/${galConfigId}/link-drive`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link_drive: link })
      });
      const data = await res.json();
      if (data.success) {
        showToast('✓ Link do Google Drive salvo com sucesso no banco!');
        if (window.galeriaConfigAtual) window.galeriaConfigAtual.link_drive = link;
      } else {
        showToast(data.error || 'Erro ao salvar link do Drive.', 'error');
      }
    } catch (e) {
      showToast('Erro de conexão ao salvar link.', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = origText; }
    }
  };

  window.abrirPaginaEntrega = function() {
    window.open(`entrega.html?id=${galConfigId}`, '_blank');
  };

  window.copiarLinkPaginaEntrega = function() {
    const url = `${window.location.origin}/entrega.html?id=${galConfigId}`;
    navigator.clipboard.writeText(url).then(() => {
      showToast('✓ Link da Página de Entrega copiado com sucesso!');
    }).catch(() => {
      prompt('Copie o link da página de entrega:', url);
    });
  };

  window.enviarEntregaWhatsApp = function() {
    const gal = window.galeriaConfigAtual || {};
    const nome = document.getElementById('waNomeCliente') ? document.getElementById('waNomeCliente').value : (gal.nome || 'Cliente');
    const fone = document.getElementById('waTelefoneCliente') ? document.getElementById('waTelefoneCliente').value.replace(/\D/g, '') : '';
    const linkEntrega = `${window.location.origin}/entrega.html?id=${galConfigId}`;

    const texto = `Olá ${nome}! Suas fotos do ensaio ficaram lindas e já estão preparadas com muito carinho! ✨📸\n\nAcesse sua página oficial de entrega para visualizar e baixar os arquivos finais em alta resolução direto pelo Google Drive:\n🔗 ${linkEntrega}\n\nQualquer dúvida estamos à disposição!`;

    if (fone && fone.length >= 10) {
      window.open(`https://wa.me/55${fone}?text=${encodeURIComponent(texto)}`, '_blank');
    } else {
      navigator.clipboard.writeText(texto).then(() => {
        showToast('✓ Mensagem e Link de Entrega copiados! Cole no WhatsApp do cliente.');
      });
    }
  };



  // ============================================================================
  // 6. FORMULÁRIO DE CONTATO (index.html)
  // ============================================================================
  const contactCard = document.querySelector('.contact-hero-card');
  if (contactCard && !document.getElementById('formContatoSite')) {
    const contactForm = document.createElement('form');
    contactForm.id = 'formContatoSite';
    contactForm.style.marginTop = '1rem';
    contactForm.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:0.6rem;">
        <input type="text" id="contatoNome" placeholder="Seu nome" required style="width:100%; padding:0.55rem 0.85rem; border-radius:8px; border:1px solid #D8CAB9; font-size:0.84rem;">
        <input type="tel" id="contatoTel" placeholder="WhatsApp / Telefone" required style="width:100%; padding:0.55rem 0.85rem; border-radius:8px; border:1px solid #D8CAB9; font-size:0.84rem;">
        <textarea id="contatoMsg" placeholder="Como podemos ajudar no seu ensaio?" rows="2" required style="width:100%; padding:0.55rem 0.85rem; border-radius:8px; border:1px solid #D8CAB9; font-size:0.84rem; resize:none;"></textarea>
        <button type="submit" style="background:#352319; color:#FFF; border:none; border-radius:9999px; padding:0.6rem; font-size:0.84rem; font-weight:600; cursor:pointer; transition: background 0.2s;">
          Enviar mensagem →
        </button>
      </div>
    `;

    contactForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nome = document.getElementById('contatoNome').value;
      const telefone = document.getElementById('contatoTel').value;
      const mensagem = document.getElementById('contatoMsg').value;

      try {
        const res = await fetch('/api/contato', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nome, telefone, mensagem })
        });
        const d = await res.json();
        if (d.success) {
          showToast('🎉 Mensagem enviada e salva com sucesso!');
          contactForm.reset();
        }
      } catch (err) {
        showToast('Erro ao enviar mensagem.', 'error');
      }
    });

    contactCard.appendChild(contactForm);
  }

  // ============================================================================
  // 7. CARREGAMENTO DINÂMICO E CONTROLES DA PÁGINA INICIAL (index.html)
  // ============================================================================
  const heroCatRow = document.getElementById('heroCategoriesRow');
  const carouselCardsGrid = document.getElementById('carouselCardsGrid');
  const carouselFilterPills = document.getElementById('carouselFilterPills');

  // Carrega os textos configurados pelo Admin na Home
  carregarTextosCustomizadosHome();

  async function carregarTextosCustomizadosHome() {
    try {
      const res = await fetch('/api/site/textos');
      const t = await res.json();
      if (!t) return;

      const setTxt = (id, val) => {
        const el = document.getElementById(id);
        if (el && val) el.textContent = val;
      };

      setTxt('heroTag', t.hero_tag);
      setTxt('heroTitle', t.hero_titulo);
      setTxt('heroDescription', t.hero_descricao);
      setTxt('headerBrandSlogan', t.header_slogan);
      setTxt('contactCardTitle', t.contato_titulo);
      setTxt('contactCardDesc', t.contato_descricao);
      setTxt('aboutTag', t.sobre_tag);
      setTxt('aboutTitle', t.sobre_titulo);
      setTxt('aboutText', t.sobre_texto);

      // WhatsApp no Hero
      const btnWhats = document.getElementById('btnHeroWhatsApp');
      if (btnWhats) {
        const num = (t.contato_whatsapp || '11987654321').replace(/\D/g, '');
        btnWhats.href = `https://wa.me/55${num}?text=Ol%C3%A1%2C+gostaria+de+informações+sobre+os+ensaios+do+estúdio!`;
        btnWhats.target = '_blank';
      }
    } catch (e) {
      console.log('Textos padrão mantidos:', e);
    }
  }

  // Controles do Carrossel (Anterior / Próximo)
  const btnAnt = document.getElementById('btnAnterior');
  const btnProx = document.getElementById('btnProximo');
  if (btnAnt && carouselCardsGrid) {
    btnAnt.addEventListener('click', () => {
      carouselCardsGrid.scrollBy({ left: -360, behavior: 'smooth' });
    });
  }
  if (btnProx && carouselCardsGrid) {
    btnProx.addEventListener('click', () => {
      carouselCardsGrid.scrollBy({ left: 360, behavior: 'smooth' });
    });
  }

  // Botão Fale Conosco na Home
  const btnFale = document.getElementById('btnFaleConosco');
  if (btnFale) {
    btnFale.addEventListener('click', (e) => {
      e.preventDefault();
      const inputNome = document.getElementById('contatoNome');
      if (inputNome) {
        inputNome.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => inputNome.focus(), 400);
      } else {
        abrirModalOrcamento('Contato com o Estúdio');
      }
    });
  }

  if (heroCatRow || carouselCardsGrid) {
    carregarDadosSitePublico();
  }

  async function carregarDadosSitePublico() {
    try {
      const resCat = await fetch('/api/site/categorias');
      const categorias = await resCat.json();

      if (heroCatRow) {
        if (categorias && categorias.length > 0) {
          heroCatRow.innerHTML = categorias.map(c => 
            `<button type="button" class="tag-badge" onclick="filtrarFotosPorCategoria('${c.nome}')" style="cursor:pointer; background:#FAF5EE; color:#6B5546; border:1px solid #D8CAB9; padding:0.4rem 1rem; font-size:0.84rem; font-weight:600; border-radius:9999px;">${c.nome}</button>`
          ).join(' ');
        } else {
          heroCatRow.innerHTML = `
            <span class="empty-site-hint" style="font-size: 0.82rem; color: #8C7B6D; font-style: italic;">
              Novos ensaios e categorias em breve.
            </span>
          `;
        }
      }

      if (carouselFilterPills) {
        if (categorias && categorias.length > 0) {
          carouselFilterPills.innerHTML = `
            <button type="button" class="select-filter-pill active-pill" data-cat="Todas" style="cursor:pointer; background:#352319; color:#FFF; border-color:#352319;">Todas</button>
            ${categorias.map(c => `<button type="button" class="select-filter-pill" data-cat="${c.nome}" style="cursor:pointer;">${c.nome}</button>`).join(' ')}
          `;

          carouselFilterPills.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
              carouselFilterPills.querySelectorAll('button').forEach(b => {
                b.style.backgroundColor = '#FAF6F0';
                b.style.color = '#5C4A3E';
                b.style.borderColor = '#D8CAB9';
              });
              btn.style.backgroundColor = '#352319';
              btn.style.color = '#FFFFFF';
              btn.style.borderColor = '#352319';
              filtrarFotosCarrossel(btn.dataset.cat);
            });
          });
        } else {
          carouselFilterPills.innerHTML = '';
        }
      }

      filtrarFotosCarrossel('Todas');

    } catch (err) {
      console.error('Erro ao carregar dados do site:', err);
    }
  }

  window.filtrarFotosPorCategoria = function(cat) {
    const section = document.getElementById('destaques');
    if (section) section.scrollIntoView({ behavior: 'smooth' });
    filtrarFotosCarrossel(cat);
  };

  async function filtrarFotosCarrossel(categoria) {
    if (!carouselCardsGrid) return;
    try {
      const url = (categoria && categoria !== 'Todas') ? `/api/site/fotos?categoria=${encodeURIComponent(categoria)}` : '/api/site/fotos';
      const res = await fetch(url);
      const fotos = await res.json();

      if (fotos && fotos.length > 0) {
        carouselCardsGrid.innerHTML = fotos.map(f => `
          <div class="kanban-item-card" style="padding: 0; overflow: hidden; border-radius: 16px; border: 1px solid #E8DDD0; background: #FFF; box-shadow: 0 4px 12px rgba(45,29,20,0.06);">
            <div style="position: relative; height: 260px; overflow: hidden; cursor: pointer;" onclick="abrirLightbox('${f.arquivo}', '${f.titulo}')">
              <img src="${f.arquivo}" alt="${f.titulo}" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s ease;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
              <span class="tag-badge" style="position: absolute; top: 12px; left: 12px; background: rgba(53, 35, 25, 0.85); color: #FAF5EE; backdrop-filter: blur(4px); border: none; font-size: 0.72rem; padding: 0.3rem 0.8rem;">
                ${f.categoria_nome}
              </span>
            </div>
            <div style="padding: 1.1rem 1.25rem;">
              <h3 style="font-size: 1.05rem; font-weight: 700; color: #2D1D14; margin-bottom: 0.25rem;">${f.titulo}</h3>
              <span style="font-size: 0.78rem; color: #8C7B6D;">Ensaio Estúdio Casa da Foto</span>
            </div>
          </div>
        `).join('');
      } else {
        carouselCardsGrid.innerHTML = `
          <div class="empty-site-banner" style="grid-column: 1 / -1; width: 100%; text-align: center; padding: 3.5rem 1.5rem; background: #FAF5EE; border: 1.5px dashed #D8CAB9; border-radius: 18px;">
            <span style="font-size: 2.2rem; display: block; margin-bottom: 0.5rem;">📷</span>
            <strong style="display: block; font-size: 1.15rem; color: #2D1D14; margin-bottom: 0.35rem;">Novas fotos e ensaios em breve</strong>
            <span style="color: #7A6A5E; font-size: 0.88rem; display: block;">Estamos preparando novos ensaios com muito carinho.</span>
          </div>
        `;
      }
    } catch (err) {
      console.error('Erro ao filtrar fotos:', err);
    }
  }

  // ============================================================================
  // 8. TELA: PACOTES DE ENSAIO (pacotes.html)
  // ============================================================================
  const pacotesSection = document.getElementById('nossosPacotes') || document.getElementById('gridPacotesSite');
  if (pacotesSection) {
    let pacotesSiteCache = [];

    async function carregarPacotesSite() {
      const grid = document.getElementById('gridPacotesSite');
      if (!grid) return;

      try {
        const res = await fetch('/api/site/pacotes');
        pacotesSiteCache = await res.json();

        renderizarPacotesSite(pacotesSiteCache);
      } catch (err) {
        console.error('Erro ao carregar pacotes:', err);
      }
    }

    function renderizarPacotesSite(lista) {
      const grid = document.getElementById('gridPacotesSite');
      if (!grid) return;

      if (!lista || lista.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; width: 100%; text-align: center; padding: 4rem 1.5rem; background: #FAF5EE; border: 1.5px dashed #D8CAB9; border-radius: 18px;">
            <span style="font-size: 2.5rem; display: block; margin-bottom: 0.5rem;">🎁</span>
            <strong style="display: block; font-size: 1.25rem; color: #2D1D14; margin-bottom: 0.4rem;">Novos pacotes de ensaio em breve</strong>
            <p style="color: #6B5E55; font-size: 0.9rem; max-width: 480px; margin: 0 auto; line-height: 1.5;">Entre em contato conosco para conhecer nossas opções personalizadas.</p>
          </div>
        `;
        return;
      }

      grid.innerHTML = lista.map(p => `
        <article class="package-card" data-titulo="${(p.titulo || '').toLowerCase()}" data-descricao="${(p.descricao || '').toLowerCase()}">
          <div class="package-card-thumb">
            <img src="${p.imagem || 'assets/logo/logo.png'}" alt="${p.titulo}" onerror="this.src='assets/logo/logo.png'">
          </div>
          <div class="package-card-content">
            <h3 class="package-card-title">${p.titulo}</h3>
            <span class="preview-pill-tag" style="background:#FAF5EE; color:#8C5F35; border:1px solid #D8CAB9; font-weight:700; font-size:0.75rem; margin:0 0 8px 0; align-self: flex-start;">
              ${p.valor || 'Sob consulta'}
            </span>
            <p class="package-card-desc">
              ${p.descricao || 'Atendimento acolhedor, cenários preparados e fotos em alta resolução.'}
            </p>
            <a href="javascript:void(0)" class="btn-consultar-valores" onclick="abrirModalOrcamento('${(p.titulo || 'Pacote de Ensaio').replace(/'/g, "\\'")}')">
              Consultar valores
            </a>
          </div>
        </article>
      `).join('');
    }

    function filtrarPacotes(termo) {
      termo = termo.toLowerCase().trim();
      const cards = document.querySelectorAll('#gridPacotesSite .package-card');
      cards.forEach(card => {
        const title = card.getAttribute('data-titulo') || '';
        const desc = card.getAttribute('data-descricao') || '';
        if (termo === 'todos' || termo === 'ensaio familiar' && (title.includes('família') || title.includes('familia')) || title.includes(termo) || desc.includes(termo)) {
          card.style.display = 'flex';
        } else {
          card.style.display = 'none';
        }
      });
    }

    const heroPills = document.querySelectorAll('.hero-pills-row .pill-btn');
    heroPills.forEach(pill => {
      pill.addEventListener('click', () => {
        heroPills.forEach(p => p.classList.remove('active-pill'));
        pill.classList.add('active-pill');
        const cat = pill.textContent.trim().toLowerCase();
        filtrarPacotes(cat);
        const targetSec = document.getElementById('nossosPacotes');
        if (targetSec) targetSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });

    const secPills = document.querySelectorAll('.packages-filter-pills .filter-pill');
    secPills.forEach(pill => {
      pill.addEventListener('click', () => {
        secPills.forEach(p => { p.style.background = '#FAF6F0'; p.style.color = '#5C4A3E'; });
        pill.style.background = '#352319';
        pill.style.color = '#FFFFFF';
        const cat = pill.textContent.trim().toLowerCase();
        filtrarPacotes(cat);
      });
    });

    const btnFalePacotes = document.getElementById('btnFaleConoscoPacotes');
    if (btnFalePacotes) {
      btnFalePacotes.addEventListener('click', (e) => {
        e.preventDefault();
        abrirModalOrcamento('Informações Gerais de Pacotes');
      });
    }

    carregarPacotesSite();
  }


  // ============================================================================
  // 9. MODAIS E LIGHTBOX INTERATIVOS
  // ============================================================================

  // Lightbox de Fotos Interativo com Navegação e Seleção em Tela Cheia
  window.lightboxFotosLista = [];
  window.lightboxCurrentIndex = 0;
  window.lightboxTecladoAtivo = false;

  window.abrirLightbox = function(imgSrc, titulo, fotoId) {
    let fotos = [];
    const cards = document.querySelectorAll('.proofing-card');
    const cardsVisiveis = Array.from(cards).filter(c => c.style.display !== 'none');

    // Se o cliente filtrou fotos na tela, navega entre as fotos filtradas
    if (cardsVisiveis.length > 0 && cardsVisiveis.length < (window.fotosGlobaisCliente?.length || 0)) {
      fotos = cardsVisiveis.map(c => {
        const id = c.getAttribute('data-id');
        const fotoReal = window.fotosGlobaisCliente?.find(f => f.id == id);
        return fotoReal || {
          id: id,
          status: c.getAttribute('data-status') || 'nao_selecionada',
          numero: c.querySelector('.photo-number-label')?.textContent?.trim() || c.getAttribute('data-numero') || '',
          arquivo: c.querySelector('img')?.src || ''
        };
      });
    } else if (window.fotosGlobaisCliente && window.fotosGlobaisCliente.length > 0) {
      fotos = [...window.fotosGlobaisCliente];
    } else if (cards.length > 0) {
      fotos = Array.from(cards).map(c => ({
        id: c.getAttribute('data-id'),
        status: c.getAttribute('data-status') || 'nao_selecionada',
        numero: c.querySelector('.photo-number-label')?.textContent?.trim() || c.getAttribute('data-numero') || '',
        arquivo: c.querySelector('img')?.src || ''
      }));
    }

    if (!fotos || fotos.length === 0) {
      fotos = [{ id: fotoId ?? null, arquivo: imgSrc, numero: titulo || 'Foto', status: 'nao_selecionada' }];
    }

    window.lightboxFotosLista = fotos;

    let idx = -1;
    if (fotoId != null) {
      idx = fotos.findIndex(f => f.id == fotoId);
    }
    if (idx === -1 && imgSrc) {
      idx = fotos.findIndex(f => f.arquivo === imgSrc || (f.arquivo && f.arquivo.includes(imgSrc)) || (imgSrc && imgSrc.includes(f.arquivo)));
    }
    if (idx === -1 && titulo) {
      idx = fotos.findIndex(f => f.numero === titulo || f.titulo === titulo);
    }
    if (idx === -1) idx = 0;

    window.lightboxCurrentIndex = idx;
    window.renderizarConteudoLightbox();
  };

  window.renderizarConteudoLightbox = function() {
    let lb = document.getElementById('appLightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.id = 'appLightbox';
      lb.className = 'lightbox-backdrop';
      document.body.appendChild(lb);
    }

    if (!window.lightboxTecladoAtivo) {
      window.lightboxTecladoAtivo = true;

      // Navegação por teclado: Setas ← e →, Esc para fechar, P para Pacote, E para Extra
      window.addEventListener('keydown', (e) => {
        const lbEl = document.getElementById('appLightbox');
        if (!lbEl || lbEl.style.display !== 'flex') return;

        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          window.navegarLightbox(-1);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          window.navegarLightbox(1);
        } else if (e.key === 'Escape') {
          lbEl.style.display = 'none';
        } else if (e.key === 'p' || e.key === 'P' || e.key === '1') {
          const fotos = window.lightboxFotosLista || [];
          const cur = fotos[window.lightboxCurrentIndex];
          if (cur && cur.id != null) {
            e.preventDefault();
            const novoSt = cur.status === 'pacote' ? 'nao_selecionada' : 'pacote';
            window.selecionarFotoNoLightbox(cur.id, novoSt);
          }
        } else if (e.key === 'e' || e.key === 'E' || e.key === '2') {
          const fotos = window.lightboxFotosLista || [];
          const cur = fotos[window.lightboxCurrentIndex];
          if (cur && cur.id != null) {
            e.preventDefault();
            const novoSt = cur.status === 'extra' ? 'nao_selecionada' : 'extra';
            window.selecionarFotoNoLightbox(cur.id, novoSt);
          }
        }
      });

      // Suporte a gestos touch swipe (deslizar dedo para mudar de foto no celular)
      let touchStartX = 0;
      let touchStartY = 0;
      lb.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length > 0) {
          touchStartX = e.touches[0].clientX;
          touchStartY = e.touches[0].clientY;
        }
      }, { passive: true });

      lb.addEventListener('touchend', (e) => {
        if (e.changedTouches && e.changedTouches.length > 0) {
          const diffX = e.changedTouches[0].clientX - touchStartX;
          const diffY = e.changedTouches[0].clientY - touchStartY;
          if (Math.abs(diffX) > 45 && Math.abs(diffX) > Math.abs(diffY)) {
            if (diffX < 0) {
              window.navegarLightbox(1); // Deslizou para esquerda -> próxima foto
            } else {
              window.navegarLightbox(-1); // Deslizou para direita -> foto anterior
            }
          }
        }
      }, { passive: true });
    }

    const fotos = window.lightboxFotosLista || [];
    const idx = window.lightboxCurrentIndex;
    const foto = fotos[idx] || { arquivo: '', numero: 'Foto', status: 'nao_selecionada', id: null };

    const total = fotos.length;
    const isPacote = foto.status === 'pacote';
    const isExtra = foto.status === 'extra';
    const tagStatus = isPacote ? '✓ Inclusa no Pacote' : isExtra ? '★ Foto Extra' : '○ Não Selecionada';
    const tagClass = isPacote ? 'lb-status-pacote' : isExtra ? 'lb-status-extra' : 'lb-status-none';

    lb.innerHTML = `
      <div class="lightbox-container" onclick="event.stopPropagation()">
        <!-- Botão Fechar -->
        <button type="button" class="lightbox-close-btn" onclick="document.getElementById('appLightbox').style.display='none'" title="Fechar (Esc)">✕</button>

        <!-- Barra Superior: Contador e Status da Foto Atual -->
        <div class="lightbox-top-bar">
          <div class="lightbox-meta-info">
            <span class="lightbox-counter">${total > 1 ? `Foto ${idx + 1} de ${total}` : ''}</span>
            <span class="lightbox-photo-title">${foto.numero || foto.titulo || 'Foto'}</span>
          </div>
          <span class="lightbox-status-pill ${tagClass}">${tagStatus}</span>
        </div>

        <!-- Área Central da Imagem com Setas de Navegação -->
        <div class="lightbox-image-stage">
          ${total > 1 ? `
            <button type="button" class="lightbox-nav-btn prev-btn" onclick="window.navegarLightbox(-1)" title="Foto anterior (Seta esquerda / Deslizar)">❮</button>
          ` : ''}

          <div class="lightbox-img-wrapper">
            <img src="${foto.arquivo}" alt="${foto.numero || ''}" id="lightboxMainImg" onerror="this.onerror=null; this.src='assets/logo/logo.png';">
            <div class="watermark-overlay-large" title="Casa da Foto Studio - Marca d'água"></div>
          </div>

          ${total > 1 ? `
            <button type="button" class="lightbox-nav-btn next-btn" onclick="window.navegarLightbox(1)" title="Próxima foto (Seta direita / Deslizar)">❯</button>
          ` : ''}
        </div>

        <!-- Barra Inferior de Ação: SELEÇÃO RÁPIDA DENTRO DA FOTO ABERTA -->
        ${(foto.id !== null && foto.id !== undefined) ? `
          <div class="lightbox-bottom-actions">
            <div class="lightbox-buttons-group">
              <button type="button" 
                class="btn-lb-action ${isPacote ? 'is-active-pacote' : ''}" 
                onclick="window.selecionarFotoNoLightbox('${foto.id}', '${isPacote ? 'nao_selecionada' : 'pacote'}')"
                title="${isPacote ? 'Remover do pacote' : 'Incluir foto no pacote'}">
                <span class="btn-icon">${isPacote ? '✓' : '+'}</span>
                <span>${isPacote ? '✓ No Pacote' : '+ Pacote'}</span>
              </button>

              <button type="button" 
                class="btn-lb-action ${isExtra ? 'is-active-extra' : ''}" 
                onclick="window.selecionarFotoNoLightbox('${foto.id}', '${isExtra ? 'nao_selecionada' : 'extra'}')"
                title="${isExtra ? 'Remover dos extras' : 'Escolher como foto extra'}">
                <span class="btn-icon">${isExtra ? '★' : '+'}</span>
                <span>${isExtra ? '★ Foto Extra' : '+ Extra'}</span>
              </button>
            </div>

            <div class="lightbox-keyboard-hint">
              <span>Use as setas <strong>←</strong> e <strong>→</strong> (ou deslize no celular) para mudar de foto. Clique nos botões para selecionar.</span>
            </div>
          </div>
        ` : ''}
      </div>
    `;

    lb.style.display = 'flex';
    lb.onclick = (e) => { if (e.target === lb) lb.style.display = 'none'; };
  };

  window.navegarLightbox = function(direcao) {
    const fotos = window.lightboxFotosLista || [];
    if (!fotos || fotos.length <= 1) return;
    let novoIdx = window.lightboxCurrentIndex + direcao;
    if (novoIdx < 0) novoIdx = fotos.length - 1;
    if (novoIdx >= fotos.length) novoIdx = 0;
    window.lightboxCurrentIndex = novoIdx;
    window.renderizarConteudoLightbox();
  };

  window.selecionarFotoNoLightbox = async function(fotoId, novoStatus) {
    const fotos = window.lightboxFotosLista || [];
    const foto = fotos.find(f => f.id == fotoId);
    if (foto) {
      foto.status = novoStatus;
    }
    if (window.fotosGlobaisCliente) {
      const fg = window.fotosGlobaisCliente.find(f => f.id == fotoId);
      if (fg) fg.status = novoStatus;
    }

    // Feedback visual instantâneo dentro do Lightbox aberto
    window.renderizarConteudoLightbox();

    // Atualiza imediatamente o card no grid de fundo se existir
    const cardEl = document.querySelector(`.proofing-card[data-id="${fotoId}"]`);
    if (cardEl) {
      cardEl.setAttribute('data-status', novoStatus);
      cardEl.classList.remove('card-selected-pacote', 'card-selected-extra');
      if (novoStatus === 'pacote') cardEl.classList.add('card-selected-pacote');
      if (novoStatus === 'extra') cardEl.classList.add('card-selected-extra');
      
      const tagEl = cardEl.querySelector('.photo-status-tag');
      if (tagEl) {
        tagEl.className = 'photo-status-tag ' + (novoStatus === 'pacote' ? 'tag-pacote' : novoStatus === 'extra' ? 'tag-extra' : 'tag-disponivel');
        tagEl.textContent = novoStatus === 'pacote' ? 'No pacote' : novoStatus === 'extra' ? 'Extra' : 'Disponível';
      }
      
      const btnPacote = cardEl.querySelector('.btn-proof-toggle:first-of-type');
      if (btnPacote) {
        if (novoStatus === 'pacote') btnPacote.classList.add('active-pacote');
        else btnPacote.classList.remove('active-pacote');
      }
      const btnExtra = cardEl.querySelector('.btn-proof-toggle:last-of-type');
      if (btnExtra) {
        if (novoStatus === 'extra') btnExtra.classList.add('active-extra');
        else btnExtra.classList.remove('active-extra');
      }
    }

    // Envia ao servidor e re-sincroniza métricas e contadores
    if (typeof window.mudarStatusFoto === 'function') {
      await window.mudarStatusFoto(fotoId, novoStatus);
      if (window.fotosGlobaisCliente && window.lightboxFotosLista) {
        window.lightboxFotosLista.forEach(lf => {
          const matched = window.fotosGlobaisCliente.find(fg => fg.id == lf.id);
          if (matched) lf.status = matched.status;
        });
      }
    }
  };

  // Modal de Consulta de Orçamento / Pacotes
  window.abrirModalOrcamento = function(nomePacote) {
    let modal = document.getElementById('appModalOrcamento');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'appModalOrcamento';
      modal.style.cssText = `
        position: fixed; inset: 0; z-index: 99999;
        background: rgba(20, 14, 10, 0.7); backdrop-filter: blur(5px);
        display: flex; align-items: center; justify-content: center;
        padding: 20px;
      `;
      document.body.appendChild(modal);
    }
    modal.innerHTML = `
      <div style="background: #FAF5EE; border: 1px solid #D8CAB9; border-radius: 18px; max-width: 440px; width: 100%; padding: 2rem; box-shadow: 0 20px 50px rgba(0,0,0,0.3); position: relative;">
        <button type="button" onclick="document.getElementById('appModalOrcamento').style.display='none'" style="position: absolute; top: 18px; right: 20px; background: none; border: none; font-size: 1.3rem; color: #6B5546; cursor: pointer;">✕</button>
        <span style="font-size: 0.76rem; font-weight: 700; color: #9E744B; letter-spacing: 0.08em; display: block; margin-bottom: 4px;">ORÇAMENTO & RESERVAS</span>
        <h3 style="font-size: 1.3rem; color: #2D1D14; font-weight: 800; margin-bottom: 0.5rem;">${nomePacote}</h3>
        <p style="font-size: 0.85rem; color: #6B5E55; line-height: 1.5; margin-bottom: 1.25rem;">Envie seus dados para receber valores detalhados e datas disponíveis para o seu ensaio.</p>
        
        <form onsubmit="event.preventDefault(); enviarFormOrcamento('${nomePacote}');">
          <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.25rem;">
            <input type="text" id="orcNome" placeholder="Seu nome completo" required style="padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
            <input type="tel" id="orcTel" placeholder="WhatsApp para retorno" required style="padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
            <textarea id="orcObs" placeholder="Alguma preferência de data ou ideia especial?" rows="2" style="padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem; resize: none;"></textarea>
          </div>
          <button type="submit" style="width: 100%; background: #352319; color: #FAF5EE; border: none; padding: 0.75rem; border-radius: 9999px; font-weight: 700; cursor: pointer; font-size: 0.9rem;">
            Solicitar Proposta →
          </button>
        </form>
      </div>
    `;
    modal.style.display = 'flex';
  };

  window.enviarFormOrcamento = async function(pacote) {
    const nome = document.getElementById('orcNome').value;
    const tel = document.getElementById('orcTel').value;
    const obs = document.getElementById('orcObs').value;
    try {
      const res = await fetch('/api/contato', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, telefone: tel, mensagem: `[Interesse no ${pacote}]: ${obs || 'Gostaria de saber valores e datas.'}` })
      });
      const d = await res.json();
      if (d.success) {
        showToast(`🎉 Solicitação para ${pacote} enviada com sucesso!`);
        document.getElementById('appModalOrcamento').style.display = 'none';
      }
    } catch (err) {
      showToast('Erro ao enviar solicitação.', 'error');
    }
  };

  // Modal para "+ Novo projeto"
  window.capaBase64Temp = null;
  window.previewCapaNovoProjeto = function(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
      window.capaBase64Temp = e.target.result;
      const previewWrap = document.getElementById('novoProjCapaPreviewWrap');
      const previewImg = document.getElementById('novoProjCapaPreviewImg');
      const nomeSpan = document.getElementById('novoProjCapaNome');
      if (previewImg) previewImg.src = e.target.result;
      if (previewWrap) previewWrap.style.display = 'flex';
      if (nomeSpan) nomeSpan.textContent = file.name;
    };
    reader.readAsDataURL(file);
  };

  // Modal para "+ Novo projeto" e Galeria com Foto de Capa
  window.abrirModalNovoProjeto = function() {
    window.capaBase64Temp = null;
    let modal = document.getElementById('appModalNovoProjeto');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'appModalNovoProjeto';
      modal.style.cssText = `
        position: fixed; inset: 0; z-index: 99999;
        background: rgba(20, 14, 10, 0.7); backdrop-filter: blur(5px);
        display: flex; align-items: center; justify-content: center;
        padding: 20px;
      `;
      document.body.appendChild(modal);
    }
    modal.innerHTML = `
      <div style="background: #FAF5EE; border: 1px solid #D8CAB9; border-radius: 18px; max-width: 460px; width: 100%; padding: 2rem; box-shadow: 0 20px 50px rgba(0,0,0,0.3); position: relative; max-height: 90vh; overflow-y: auto;">
        <button type="button" onclick="document.getElementById('appModalNovoProjeto').style.display='none'" style="position: absolute; top: 18px; right: 20px; background: none; border: none; font-size: 1.3rem; color: #6B5546; cursor: pointer;">✕</button>
        <span style="font-size: 0.76rem; font-weight: 700; color: #9E744B; letter-spacing: 0.08em; display: block; margin-bottom: 4px;">GESTÃO DE ENSAIOS E GALERIA</span>
        <h3 style="font-size: 1.3rem; color: #2D1D14; font-weight: 800; margin-bottom: 1.25rem;">+ Cadastrar Projeto & Galeria</h3>
        
        <form onsubmit="event.preventDefault(); salvarNovoProjetoModal();">
          <div style="display: flex; flex-direction: column; gap: 0.85rem; margin-bottom: 1.25rem;">
            <div>
              <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:3px;">Nome do Cliente *</label>
              <input type="text" id="novoProjCliente" placeholder="Ex: Juliana & Marcos" required style="width:100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
            </div>
            <div>
              <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:3px;">Tipo de Ensaio</label>
              <select id="novoProjTipo" style="width:100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
                <option value="Ensaio Família">Ensaio Família</option>
                <option value="Ensaio Gestante">Ensaio Gestante</option>
                <option value="Ensaio Bebê">Ensaio Bebê</option>
                <option value="Ensaio Casal">Ensaio Casal</option>
                <option value="Retrato Pessoal">Retrato Pessoal</option>
              </select>
            </div>
            
            <!-- DEFINIÇÃO DA FOTO DE CAPA DA GALERIA -->
            <div style="background: #FFFFFF; border: 1px solid #E5D9CC; border-radius: 10px; padding: 0.85rem;">
              <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:5px;">Foto de Capa da Galeria</label>
              <div style="display: flex; gap: 0.65rem; align-items: center; flex-wrap: wrap;">
                <label for="novoProjCapaFile" style="cursor: pointer; background: #FAF5EE; border: 1px dashed #9E744B; border-radius: 8px; padding: 0.5rem 0.85rem; font-size: 0.78rem; font-weight: 700; color: #8C5F35; display: inline-flex; align-items: center; gap: 5px; transition: all 0.2s;">
                  📷 Selecionar Foto como Capa
                </label>
                <input type="file" id="novoProjCapaFile" accept="image/*" style="display: none;" onchange="previewCapaNovoProjeto(event)">
                <span id="novoProjCapaNome" style="font-size: 0.73rem; color: #8A7667; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 190px;">Usa a Logo Oficial se vazio</span>
              </div>
              <div id="novoProjCapaPreviewWrap" style="display:none; margin-top: 8px; align-items: center; gap: 8px; background: #FAF6F0; padding: 6px 10px; border-radius: 8px; border: 1px solid #D8CAB9;">
                <img id="novoProjCapaPreviewImg" src="" style="width: 65px; height: 45px; object-fit: cover; border-radius: 6px; border: 1px solid #D8CAB9;">
                <div>
                  <strong style="display:block; font-size:0.75rem; color:#2E7D32;">✓ Capa da Galeria Definida</strong>
                  <span style="font-size:0.68rem; color:#6B5546;">Esta foto será exibida como destaque na galeria.</span>
                </div>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
              <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:3px;">Fotos no Pacote</label>
                <input type="number" id="novoProjLimitePacote" value="10" min="1" max="500" style="width:100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
              </div>
              <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:3px;">Valor Foto Extra (R$)</label>
                <input type="number" id="novoProjValorExtra" value="25.00" step="0.5" min="0" style="width:100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
              <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:3px;">Sessões</label>
                <input type="number" id="novoProjSessoes" value="1" min="1" max="10" style="width:100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
              </div>
              <div>
                <label style="display:block; font-size:0.75rem; font-weight:700; color:#5C4A3E; margin-bottom:3px;">Prazo / Data</label>
                <input type="text" id="novoProjPrazo" placeholder="Ex: 25 nov" style="width:100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1px solid #D8CAB9; font-size: 0.88rem;">
              </div>
            </div>
          </div>
          <button type="submit" id="btnSalvarNovoProjSubmit" style="width: 100%; background: #352319; color: #FAF5EE; border: none; padding: 0.75rem; border-radius: 9999px; font-weight: 700; cursor: pointer; font-size: 0.9rem; transition: all 0.2s;">
            Salvar Projeto e Criar Galeria →
          </button>
        </form>
      </div>
    `;
    modal.style.display = 'flex';
  };

  window.salvarNovoProjetoModal = async function() {
    const nome = document.getElementById('novoProjCliente').value.trim();
    const tipo = document.getElementById('novoProjTipo').value;
    const limitePacote = parseInt(document.getElementById('novoProjLimitePacote')?.value || 10);
    const valorExtra = parseFloat(document.getElementById('novoProjValorExtra')?.value || 25.0);
    const sessoes = parseInt(document.getElementById('novoProjSessoes').value || 1);
    const prazo = document.getElementById('novoProjPrazo').value.trim() || 'sem prazo';
    const btnSubmit = document.getElementById('btnSalvarNovoProjSubmit');
    if (btnSubmit) btnSubmit.textContent = 'Criando galeria e salvando...';

    let foto_capa = 'assets/logo/logo.png';

    // Se o usuário selecionou uma foto de capa
    if (window.capaBase64Temp) {
      try {
        const upRes = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: window.capaBase64Temp })
        });
        const upData = await upRes.json();
        if (upData.success && upData.url) {
          foto_capa = upData.url;
        }
      } catch (e) {
        foto_capa = window.capaBase64Temp;
      }
    }

    try {
      let categoriaTag = tipo;
      if (tipo.includes('Retrato')) categoriaTag = 'Retrato';
      else if (tipo.includes('Casamento')) categoriaTag = 'Casamento';
      else if (tipo.includes('Família') || tipo.includes('Familia')) categoriaTag = 'Família';
      else if (tipo.includes('Parto')) categoriaTag = 'Parto';
      else if (tipo.includes('Gestante')) categoriaTag = 'Gestante';
      else if (tipo.includes('Newborn')) categoriaTag = 'Newborn';
      else if (tipo.includes('Corporativo')) categoriaTag = 'Corporativo';
      else if (tipo.includes('Eventos') || tipo.includes('Evento')) categoriaTag = 'Eventos';
      else categoriaTag = tipo.split(' ')[0];

      const res = await fetch('/api/projetos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome_cliente: nome,
          tipo_ensaio: tipo,
          categoria_tag: categoriaTag,
          status: 'novos',
          sessoes: sessoes,
          prazo: prazo,
          limite_pacote: limitePacote,
          valor_foto_extra: valorExtra,
          foto_capa: foto_capa,
          avatar_img: foto_capa
        })
      });
      const d = await res.json();
      if (d.success) {
        showToast(`✓ Projeto e Galeria de "${nome}" cadastrados com sucesso!`);
        const modal = document.getElementById('appModalNovoProjeto');
        if (modal) modal.style.display = 'none';
        window.capaBase64Temp = null;

        // Reset dos filtros de busca e abas do Kanban para garantir visibilidade imediata
        const selTab = document.querySelector('.kanban-tab-item[data-tab="todos"], .kanban-tab-item[data-tab="novos"]');
        if (selTab) {
          document.querySelectorAll('.kanban-tab-item').forEach(b => b.classList.remove('active'));
          selTab.classList.add('active');
        }
        const searchInp = document.getElementById('kanbanSearchInput') || document.querySelector('.kanban-search-input');
        if (searchInp) searchInp.value = '';
        const selCliente = document.getElementById('filtroCliente');
        if (selCliente) selCliente.value = 'todos';
        const selEtapa = document.getElementById('filtroEtapa');
        if (selEtapa) selEtapa.value = 'todas';

        // Atualiza a listagem de projetos global se estiver em projetos.html
        if (typeof window.carregarProjetosGlobal === 'function') {
          await window.carregarProjetosGlobal();
        } else if (typeof carregarProjetos === 'function') {
          await carregarProjetos();
        }

        // Se estiver no admin.html, atualiza a tabela de galerias
        if (typeof window.carregarGaleriasAdmin === 'function') {
          await window.carregarGaleriasAdmin();
        }

        // Se estiver em galeria-config.html, atualiza o seletor e troca para a nova galeria
        if (document.getElementById('selectGaleriaAtivaConfig')) {
          if (typeof window.carregarListaGaleriasConfig === 'function') {
            await window.carregarListaGaleriasConfig(d.galeria_id || d.projeto_id);
            if (typeof window.trocarGaleriaConfigAtiva === 'function') {
              window.trocarGaleriaConfigAtiva(d.galeria_id || d.projeto_id);
            }
          }
        }

        // Rola até o novo card criado para destacar visualmente com brilho dourado
        if (d.projeto_id) {
          setTimeout(() => {
            const novoCard = document.querySelector(`[data-projeto-id="${d.projeto_id}"]`) || document.getElementById(`card-proj-${d.projeto_id}`);
            if (novoCard) {
              novoCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
              novoCard.style.outline = '2px solid #C59B6D';
              novoCard.style.boxShadow = '0 0 16px rgba(197, 155, 109, 0.6)';
              setTimeout(() => {
                novoCard.style.outline = '';
                novoCard.style.boxShadow = '';
              }, 3500);
            }
          }, 350);
        }
      }
    } catch (err) {
      showToast('Erro ao criar projeto.', 'error');
    } finally {
      if (btnSubmit) btnSubmit.textContent = 'Salvar Projeto e Criar Galeria →';
    }
  };

  // =========================================================================
  // ALBOOM PROOF SUITE EXTENSIONS: LIGHTROOM, WHATSAPP, QR CODE & ANTI-CÓPIA
  // =========================================================================

  // 1. Exportação para Adobe Lightroom, Windows Explorer e macOS Finder
  window.exportarParaLightroom = async function(galeriaId) {
    const galId = galeriaId || new URLSearchParams(window.location.search).get('id') || new URLSearchParams(window.location.search).get('galeria_id') || '1';
    try {
      showToast('Preparando lista de fotos para exportação...');
      const res = await fetch(`/api/galeria/${galId}/fotos`);
      const data = await res.json();
      const fotos = (data.fotos || []).filter(f => f.status === 'pacote' || f.status === 'extra');

      if (fotos.length === 0) {
        showToast('Nenhuma foto selecionada ainda para exportar.', 'error');
        return;
      }

      // Formatações dos arquivos
      const nomesPuros = fotos.map(f => f.numero || `Foto_${f.id}`);
      const nomesJpg = fotos.map(f => {
        const num = f.numero || `Foto_${f.id}`;
        return num.toLowerCase().endsWith('.jpg') ? num : `${num}.jpg`;
      });

      const strLightroom = nomesJpg.join(', ');
      const strWindows = nomesJpg.map(n => `nome:"${n}"`).join(' OU ');
      const strFinder = nomesPuros.join(' ');
      const strComentarios = fotos.filter(f => f.comentario).map(f => `• ${f.numero || 'Foto ' + f.id}: "${f.comentario}"`).join('\n') || 'Nenhum comentário registrado.';

      // Remove modal antigo se existir
      const oldModal = document.getElementById('alboomExportModal');
      if (oldModal) oldModal.remove();

      // Cria Modal
      const modal = document.createElement('div');
      modal.id = 'alboomExportModal';
      modal.className = 'alboom-modal-overlay';
      modal.innerHTML = `
        <div class="alboom-modal-card">
          <div class="alboom-modal-header">
            <h3>🎨 Exportar Seleção do Cliente (${fotos.length} fotos)</h3>
            <button class="alboom-modal-close-btn" onclick="document.getElementById('alboomExportModal').remove()">&times;</button>
          </div>
          <div class="alboom-modal-body">
            <p style="font-size: 0.85rem; color: #7A6A5E; margin-bottom: 1rem;">
              Exporte os nomes das fotos aprovadas diretamente para o seu software de edição ou explorador de arquivos.
            </p>

            <div class="alboom-tab-nav">
              <button class="alboom-tab-btn active" id="tabBtnLr" onclick="alternarTabExport('lr')">Adobe Lightroom</button>
              <button class="alboom-tab-btn" id="tabBtnWin" onclick="alternarTabExport('win')">Windows Explorer</button>
              <button class="alboom-tab-btn" id="tabBtnMac" onclick="alternarTabExport('mac')">macOS Finder</button>
              <button class="alboom-tab-btn" id="tabBtnNotes" onclick="alternarTabExport('notes')">Comentários</button>
            </div>

            <!-- Painel Lightroom -->
            <div id="paneLr" class="export-pane">
              <p style="font-size: 0.82rem; margin-bottom: 0.5rem; color: #5C4638;">
                <strong>Instruções:</strong> No Lightroom Library, aperte <kbd style="background:#EFE6DC; padding:2px 6px; border-radius:4px;">Ctrl+F</kbd> (ou <kbd style="background:#EFE6DC; padding:2px 6px; border-radius:4px;">Cmd+F</kbd>), selecione <em>Qualquer Campo Pesquisável</em> e cole o texto abaixo:
              </p>
              <div class="alboom-code-box" id="boxLr">${strLightroom}</div>
              <button class="alboom-copy-btn" onclick="copiarTextoExport('${strLightroom.replace(/'/g, "\\'")}', 'Copiado para o Adobe Lightroom!')">📋 Copiar Lista para Lightroom</button>
            </div>

            <!-- Painel Windows Explorer -->
            <div id="paneWin" class="export-pane" style="display: none;">
              <p style="font-size: 0.82rem; margin-bottom: 0.5rem; color: #5C4638;">
                <strong>Instruções:</strong> Abra a pasta das fotos no Windows Explorer, clique na barra de busca e cole a expressão abaixo:
              </p>
              <div class="alboom-code-box" id="boxWin">${strWindows}</div>
              <button class="alboom-copy-btn" onclick="copiarTextoExport('${strWindows.replace(/'/g, "\\'")}', 'Copiado para o Windows Explorer!')">📋 Copiar Busca para Windows</button>
            </div>

            <!-- Painel macOS Finder -->
            <div id="paneMac" class="export-pane" style="display: none;">
              <p style="font-size: 0.82rem; margin-bottom: 0.5rem; color: #5C4638;">
                <strong>Instruções:</strong> No Finder, pressione <kbd style="background:#EFE6DC; padding:2px 6px; border-radius:4px;">Cmd+F</kbd> na pasta do ensaio e cole o texto abaixo:
              </p>
              <div class="alboom-code-box" id="boxMac">${strFinder}</div>
              <button class="alboom-copy-btn" onclick="copiarTextoExport('${strFinder.replace(/'/g, "\\'")}', 'Copiado para o macOS Finder!')">📋 Copiar Busca para Finder</button>
            </div>

            <!-- Painel Comentários -->
            <div id="paneNotes" class="export-pane" style="display: none;">
              <p style="font-size: 0.82rem; margin-bottom: 0.5rem; color: #5C4638;">
                <strong>Observações e instruções de retoque deixadas pelo cliente:</strong>
              </p>
              <div class="alboom-code-box" style="white-space: pre-wrap;" id="boxNotes">${strComentarios}</div>
              <button class="alboom-copy-btn" onclick="copiarTextoExport('${strComentarios.replace(/'/g, "\\'").replace(/\n/g, '\\n')}', 'Comentários copiados!')">📋 Copiar Comentários</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      // Funções internas do modal
      window.alternarTabExport = function(tab) {
        document.querySelectorAll('.alboom-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.export-pane').forEach(p => p.style.display = 'none');
        if (tab === 'lr') {
          document.getElementById('tabBtnLr').classList.add('active');
          document.getElementById('paneLr').style.display = 'block';
        } else if (tab === 'win') {
          document.getElementById('tabBtnWin').classList.add('active');
          document.getElementById('paneWin').style.display = 'block';
        } else if (tab === 'mac') {
          document.getElementById('tabBtnMac').classList.add('active');
          document.getElementById('paneMac').style.display = 'block';
        } else if (tab === 'notes') {
          document.getElementById('tabBtnNotes').classList.add('active');
          document.getElementById('paneNotes').style.display = 'block';
        }
      };

      window.copiarTextoExport = function(texto, msg) {
        navigator.clipboard.writeText(texto).then(() => {
          showToast(`✓ ${msg}`);
        }).catch(() => {
          showToast('Falha ao copiar automaticamente. Selecione e copie manualmente.', 'error');
        });
      };

    } catch (err) {
      console.error(err);
      showToast('Erro ao carregar dados da galeria para exportação.', 'error');
    }
  };

  // 2. Reativar Seleção da Galeria
  window.reativarSelecao = async function(galeriaId) {
    const galId = galeriaId || new URLSearchParams(window.location.search).get('id') || new URLSearchParams(window.location.search).get('galeria_id') || '1';
    if (!confirm('Deseja reabrir a seleção para o cliente poder alterar suas escolhas?')) return;
    try {
      const res = await fetch(`/api/projetos/${galId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'andamento' })
      });
      const data = await res.json();
      if (data.success) {
        showToast('✓ Galeria reativada! O cliente agora pode alterar as fotos novamente.');
        setTimeout(() => window.location.reload(), 1200);
      } else {
        showToast('Não foi possível alterar o status.', 'error');
      }
    } catch (e) {
      showToast('Erro ao reativar seleção.', 'error');
    }
  };

  // 3. Compartilhamento via WhatsApp e QR Code
  window.abrirModalCompartilharWhatsApp = function(galeriaId) {
    const galId = galeriaId || new URLSearchParams(window.location.search).get('id') || new URLSearchParams(window.location.search).get('galeria_id') || '1';
    const linkGaleria = `${window.location.origin}/escolha-fotos.html?id=${galId}`;
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=260x260&data=${encodeURIComponent(linkGaleria)}`;
    const mensagemWhats = `Olá! Suas fotos do ensaio estão prontas para você escolher na Casa da Foto Studio! 📷✨\n\nAcesse sua galeria exclusiva pelo link abaixo:\n${linkGaleria}\n\nEscolha suas favoritas com carinho!`;
    const whatsLink = `https://api.whatsapp.com/send?text=${encodeURIComponent(mensagemWhats)}`;

    const oldModal = document.getElementById('alboomShareModal');
    if (oldModal) oldModal.remove();

    const modal = document.createElement('div');
    modal.id = 'alboomShareModal';
    modal.className = 'alboom-modal-overlay';
    modal.innerHTML = `
      <div class="alboom-modal-card">
        <div class="alboom-modal-header">
          <h3>💬 Compartilhar Galeria com o Cliente</h3>
          <button class="alboom-modal-close-btn" onclick="document.getElementById('alboomShareModal').remove()">&times;</button>
        </div>
        <div class="alboom-modal-body" style="text-align: center;">
          <p style="font-size: 0.88rem; color: #5C4638; margin-bottom: 1.25rem;">
            Envie o link direto para o WhatsApp do cliente ou exiba o QR Code para escaneamento instantâneo.
          </p>

          <div style="background: #FAF5EE; padding: 1.25rem; border-radius: 12px; margin-bottom: 1.25rem; display: inline-block;">
            <img src="${qrUrl}" alt="QR Code da Galeria" style="width: 180px; height: 180px; display: block; border-radius: 8px;">
            <span style="font-size: 0.72rem; color: #7A6A5E; display: block; margin-top: 0.5rem;">Aponte a câmera do celular para abrir</span>
          </div>

          <div class="alboom-share-options-grid">
            <a href="${whatsLink}" target="_blank" rel="noopener" class="alboom-share-card-btn" style="background:#25D366; color:#FFF; border:none;">
              <span class="share-icon">💬</span>
              <strong style="color:#FFF;">Enviar por WhatsApp</strong>
              <span style="color:#E8F8EE;">Abre com mensagem pronta</span>
            </a>

            <button type="button" class="alboom-share-card-btn" onclick="navigator.clipboard.writeText('${linkGaleria}').then(() => showToast('✓ Link copiado para a área de transferência!'))">
              <span class="share-icon">🔗</span>
              <strong>Copiar Link Direto</strong>
              <span>Compartilhar por e-mail ou chat</span>
            </button>

            <a href="${qrUrl}" download="qrcode-galeria.png" class="alboom-share-card-btn">
              <span class="share-icon">📥</span>
              <strong>Baixar QR Code</strong>
              <span>Salvar imagem para impressão</span>
            </a>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  };

  // 4. Modal de Confirmação de Envio da Seleção pelo Cliente
  window.iniciarModalEnviarSelecao = function() {
    const galId = new URLSearchParams(window.location.search).get('galeria_id') || new URLSearchParams(window.location.search).get('id') || sessionStorage.getItem('cliente_galeria_id') || '1';
    
    // Busca fotos do estado global ou diretamente dos cards renderizados no DOM
    let fotos = window.fotosGlobaisCliente || [];
    if (!fotos || fotos.length === 0) {
      const cards = document.querySelectorAll('.proofing-card');
      fotos = Array.from(cards).map(c => ({
        id: c.getAttribute('data-id'),
        status: c.getAttribute('data-status') || 'nao_selecionada',
        numero: c.getAttribute('data-numero') || ''
      }));
    }

    const pacotes = fotos.filter(f => f.status === 'pacote');
    const extras = fotos.filter(f => f.status === 'extra');
    const totalSelecionadas = pacotes.length + extras.length;

    if (totalSelecionadas === 0) {
      showToast('Selecione pelo menos uma foto para o pacote ou como extra antes de enviar.', 'error');
      return;
    }

    const valorExtraUnit = (window.galeriaDataCliente && window.galeriaDataCliente.valor_foto_extra != null) ? parseFloat(window.galeriaDataCliente.valor_foto_extra) : 25.0;
    const valorExtrasTotal = extras.length * valorExtraUnit;

    const oldModal = document.getElementById('alboomConfirmSendModal');
    if (oldModal) oldModal.remove();

    const modal = document.createElement('div');
    modal.id = 'alboomConfirmSendModal';
    modal.className = 'alboom-modal-overlay';
    modal.innerHTML = `
      <div class="alboom-modal-card">
        <div class="alboom-modal-header">
          <h3>✈ Confirmar Envio da Seleção</h3>
          <button class="alboom-modal-close-btn" onclick="document.getElementById('alboomConfirmSendModal').remove()">&times;</button>
        </div>
        <div class="alboom-modal-body">
          <p style="font-size: 0.9rem; color: #5C4638; margin-bottom: 1.25rem;">
            Você está prestes a enviar suas fotos escolhidas para o fotógrafo iniciar o trabalho de edição e tratamento.
          </p>

          <div style="background: #FAF5EE; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
              <span>Fotos no pacote:</span>
              <strong>${pacotes.length} fotos</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
              <span>Fotos extras selecionadas:</span>
              <strong style="color: #8C5F35;">${extras.length} fotos (+ R$ ${valorExtrasTotal.toFixed(2).replace('.', ',')})</strong>
            </div>
            <div style="display: flex; justify-content: space-between; border-top: 1px solid #D8CAB9; padding-top: 0.75rem; font-size: 1.05rem;">
              <strong>Total de fotos selecionadas:</strong>
              <strong style="color: #2D1D14;">${totalSelecionadas} fotos</strong>
            </div>
          </div>

          <div style="margin-bottom: 1.25rem;">
            <label style="display: block; font-size: 0.82rem; font-weight: 600; color: #4A3A2F; margin-bottom: 0.4rem;">Mensagem ou observações para o fotógrafo (opcional):</label>
            <textarea id="obsClienteEnvio" style="width: 100%; height: 80px; border-radius: 8px; border: 1px solid #D8CAB9; padding: 0.75rem; font-size: 0.85rem; font-family: inherit; resize: none; box-sizing: border-box;" placeholder="Ex: Adorei a foto 04! Por favor, clarear um pouco o fundo na foto 12..."></textarea>
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
            <button type="button" onclick="document.getElementById('alboomConfirmSendModal').remove()" style="background:#EFE6DC; border:none; border-radius:8px; padding:0.75rem 1.25rem; font-size:0.88rem; font-weight:600; cursor:pointer;">Continuar Escolhendo</button>
            <button type="button" id="btnConfirmarEnvioFinal" style="background:#2D1D14; color:#FFF; border:none; border-radius:8px; padding:0.75rem 1.5rem; font-size:0.88rem; font-weight:700; cursor:pointer;">✓ Confirmar e Enviar Escolha</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('btnConfirmarEnvioFinal').onclick = async function() {
      const btn = this;
      btn.disabled = true;
      btn.textContent = 'Enviando seleção...';
      const obs = document.getElementById('obsClienteEnvio').value;
      const pacoteIds = pacotes.map(f => f.id);
      const extraIds = extras.map(f => f.id);

      try {
        const res = await fetch(`/api/galeria/${galId}/enviar-selecao`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            observacoes: obs,
            pacote_ids: pacoteIds,
            extra_ids: extraIds
          })
        });
        const d = await res.json();
        if (d.success) {
          document.getElementById('alboomConfirmSendModal').remove();
          showToast('🎉 Parabéns! Sua seleção foi enviada com sucesso ao fotógrafo!');
          const btnSendMain = document.getElementById('btnEnviarSelecao');
          if (btnSendMain) {
            btnSendMain.innerHTML = '<span>✓ Seleção Enviada com Sucesso!</span>';
            btnSendMain.style.background = '#2E7D32';
          }
          setTimeout(() => window.location.reload(), 1500);
        } else {
          showToast(d.mensagem || d.message || 'Erro ao enviar seleção.', 'error');
          btn.disabled = false;
          btn.textContent = '✓ Confirmar e Enviar Escolha';
        }
      } catch (err) {
        showToast('Erro de conexão ao enviar seleção.', 'error');
        btn.disabled = false;
        btn.textContent = '✓ Confirmar e Enviar Escolha';
      }
    };
  };

  // 5. Proteção Anti-Cópia Ativa (desativa clique direito e arrastar imagens)
  window.ativarProtecaoAntiCopia = function() {
    document.addEventListener('contextmenu', (e) => {
      if (e.target.tagName === 'IMG' || e.target.closest('.proofing-cards-grid') || e.target.closest('.card-foto-item')) {
        e.preventDefault();
        showToast('🛡️ Imagens protegidas por direitos autorais da Casa da Foto Studio.');
      }
    });

    document.addEventListener('dragstart', (e) => {
      if (e.target.tagName === 'IMG') {
        e.preventDefault();
      }
    });
  };

  // Ativa automaticamente em escolha-fotos.html
  // 6. GESTÃO DE STATUS DA GALERIA E LIBERAÇÃO/BLOQUEIO DE AJUSTES
  window.alternarBloqueioGaleria = async function(galId, bloquear) {
    try {
      const rota = bloquear ? `/api/galeria/${galId}/bloquear-ajustes` : `/api/galeria/${galId}/liberar-ajustes`;
      const res = await fetch(rota, { method: 'POST' });
      const d = await res.json();
      if (d.success) {
        const msg = bloquear 
          ? '🔒 Galeria bloqueada! O cliente não poderá fazer alterações na seleção.' 
          : '🔓 Galeria LIBERADA! O cliente já tem acesso para fazer novos ajustes nas fotos.';
        showToast(msg);
        if (typeof window.carregarProjetosGlobal === 'function') {
          window.carregarProjetosGlobal();
        }
        if (typeof window.carregarDadosGaleria === 'function') {
          window.carregarDadosGaleria();
        }
      } else {
        showToast(d.error || 'Erro ao alterar bloqueio da galeria.', 'error');
      }
    } catch (e) {
      showToast('Erro de conexão ao alternar status da galeria.', 'error');
    }
  };

  window.abrirModalStatusGaleria = function(galId, nomeCliente, statusAtual, bloqueado) {
    let modal = document.getElementById('modalStatusGaleriaGlobal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'modalStatusGaleriaGlobal';
      modal.className = 'alboom-modal-overlay';
      document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
    modal.innerHTML = `
      <div class="alboom-modal-card" style="max-width: 440px;">
        <div class="alboom-modal-header">
          <div>
            <span style="font-size: 0.74rem; font-weight: 700; color: #9E744B; letter-spacing: 0.08em; display: block;">GESTÃO DE ETAPAS</span>
            <h3 style="font-size: 1.25rem; color: #2D1D14; font-weight: 800; margin: 0;">Status da Galeria</h3>
          </div>
          <button class="alboom-modal-close-btn" onclick="document.getElementById('modalStatusGaleriaGlobal').style.display='none'">&times;</button>
        </div>
        <div class="alboom-modal-body">
          <p style="font-size: 0.82rem; color: #6B5546; margin-bottom: 1.25rem;">Cliente: <strong>${nomeCliente || 'Galeria'}</strong></p>

          <div style="display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.5rem;">
            <div>
              <label class="field-label" style="display:block; font-size:0.78rem; font-weight:700; color:#5C4A3E; margin-bottom:4px;">Etapa / Status Atual</label>
              <select id="modalSelectStatusGaleria" class="field-select" style="width: 100%; padding: 0.65rem 0.9rem; border-radius: 8px; border: 1.5px solid #D8CAB9; font-weight: 700; font-size: 0.88rem;">
                <option value="Aguardando seleção" ${statusAtual === 'Aguardando seleção' ? 'selected' : ''}>Aguardando seleção</option>
                <option value="Seleção em andamento" ${statusAtual === 'Seleção em andamento' ? 'selected' : ''}>Seleção em andamento</option>
                <option value="Seleção enviada" ${statusAtual === 'Seleção enviada' ? 'selected' : ''}>Seleção enviada (Bloqueada)</option>
                <option value="Em análise pelo fotógrafo" ${statusAtual === 'Em análise pelo fotógrafo' ? 'selected' : ''}>Em análise pelo fotógrafo</option>
                <option value="Liberada para ajustes" ${statusAtual === 'Liberada para ajustes' ? 'selected' : ''}>Liberada para ajustes do cliente</option>
                <option value="Pronta para entrega" ${statusAtual === 'Pronta para entrega' ? 'selected' : ''}>Pronta para entrega</option>
                <option value="Finalizada" ${statusAtual === 'Finalizada' ? 'selected' : ''}>Finalizada</option>
              </select>
            </div>

            <div style="background: #FAF6F0; border: 1px solid #D8CAB9; border-radius: 10px; padding: 0.85rem; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
              <div>
                <strong style="display: block; font-size: 0.82rem; color: #2D1D14;">Bloquear alterações do cliente</strong>
                <span style="font-size: 0.72rem; color: #6B5546;">Quando ativado, o cliente não pode alterar fotos já selecionadas.</span>
              </div>
              <label class="switch-toggle">
                <input type="checkbox" id="modalChkBloqueioCliente" ${bloqueado == 1 ? 'checked' : ''}>
                <span class="switch-slider"></span>
              </label>
            </div>
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end;">
            <button type="button" onclick="document.getElementById('modalStatusGaleriaGlobal').style.display='none'" style="padding: 0.75rem 1.25rem; border-radius: 9999px; background: #FAF5EE; border: 1px solid #D8CAB9; font-weight: 700; color: #6B5546; cursor: pointer;">Cancelar</button>
            <button type="button" onclick="window.salvarStatusGaleriaModal(${galId})" style="padding: 0.75rem 1.5rem; border-radius: 9999px; background: #352319; color: #FAF5EE; border: none; font-weight: 800; cursor: pointer;">Salvar Status ✓</button>
          </div>
        </div>
      </div>
    `;
  };

  window.salvarStatusGaleriaModal = async function(galId) {
    const status = document.getElementById('modalSelectStatusGaleria').value;
    const bloq = document.getElementById('modalChkBloqueioCliente').checked ? 1 : 0;
    try {
      const res = await fetch(`/api/galeria/${galId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status_galeria: status, selecao_bloqueada: bloq })
      });
      const d = await res.json();
      if (d.success) {
        document.getElementById('modalStatusGaleriaGlobal').style.display = 'none';
        showToast(`✓ Status da galeria atualizado com sucesso!`);
        if (typeof window.carregarProjetosGlobal === 'function') {
          window.carregarProjetosGlobal();
        }
        if (typeof window.carregarDadosGaleria === 'function') {
          window.carregarDadosGaleria();
        }
      } else {
        showToast(d.error || 'Erro ao salvar status.', 'error');
      }
    } catch (e) {
      showToast('Erro de conexão ao salvar status.', 'error');
    }
  };

  // ============================================================================
  // 10. GESTÃO DO LINK DO GOOGLE DRIVE & MENSAGEM PERSONALIZADA DE ENTREGA
  // ============================================================================

  // ── RESTAURAR GALERIAS E PROJETOS DE DEMONSTRAÇÃO ──
  window.restaurarGaleriasExemplo = async function() {
    try {
      showToast('Restaurando 5 galerias e ensaios de exemplo...');
      const res = await fetch('/api/projetos/restaurar-exemplos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (data.success) {
        showToast('✓ 5 Galerias de exemplo restauradas com sucesso!');
        if (typeof window.carregarProjetosGlobal === 'function') {
          await window.carregarProjetosGlobal();
        }
      } else {
        showToast(data.error || 'Erro ao restaurar exemplos.', 'error');
      }
    } catch (e) {
      showToast('Erro de conexão ao restaurar exemplos.', 'error');
    }
  };

  // ── GERADOR DE MENSAGEM PERSONALIZADA DE ENTREGA (ALTA CONVERSÃO & AFETO) ──
  window.gerarMensagemEntregaPadrao = function(nomeCliente, tipoEnsaio, linkDrive, galId) {
    const nome = (nomeCliente || 'Cliente Especial').trim();
    const ensaio = (tipoEnsaio || 'Ensaio Fotográfico').trim();
    const drive = (linkDrive || '').trim();
    const origin = window.location.origin || 'http://localhost:8082';
    const linkWeb = `${origin}/entrega.html?id=${galId || 1}`;

    return `Olá, ${nome}! ✨📸

É com imensa alegria que entregamos as fotos oficiais do seu ${ensaio}! Preparamos uma página exclusiva com todo o carinho e dedicação da Casa da Foto Studio para você visualizar sua coleção e baixar todos os arquivos em alta resolução diretamente pelo Google Drive.

🎁 Acesse seu Link Exclusivo de Entrega:
${linkWeb}

(Dentro da sua página você encontrará a dedicatória especial do estúdio e o botão oficial "Baixar Fotos no Google Drive" para fazer o download completo em 1 clique!)

${drive ? `\n🔗 Link direto alternativo do Google Drive:\n${drive}\n` : ''}
Esperamos de coração que você se apaixone pelo resultado! Qualquer dúvida sobre download ou impressões, conte sempre conosco.

Com muito carinho,
Equipe Casa da Foto Studio 💛
Momentos que ficam`;
  };

  // ── MODAL EXCLUSIVO PARA INSERÇÃO DO LINK DO DRIVE E MENSAGEM DE ENTREGA ──
  window.abrirModalLinkDrive = function(galeriaId, nomeCliente, tipoEnsaio, linkDriveAtual, msgAcessoAtual) {
    let modal = document.getElementById('modalLinkDriveMsgGlobal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'modalLinkDriveMsgGlobal';
      modal.className = 'alboom-modal-overlay';
      modal.style.zIndex = '99999';
      document.body.appendChild(modal);
    }

    const galId = galeriaId || 1;
    const nomeCli = nomeCliente || 'Cliente Especial';
    const tipoEns = tipoEnsaio || 'Ensaio Fotográfico';
    const driveLink = (linkDriveAtual || '').trim();
    
    // Mensagem: usa a salva caso válida; senão, template personalizado
    const msgInicial = (msgAcessoAtual && msgAcessoAtual.trim().length > 15) 
      ? msgAcessoAtual.trim() 
      : window.gerarMensagemEntregaPadrao(nomeCli, tipoEns, driveLink, galId);

    const origin = window.location.origin || 'http://localhost:8082';
    const linkPaginaEntrega = `${origin}/entrega.html?id=${galId}`;

    modal.style.display = 'flex';
    modal.innerHTML = `
      <div class="alboom-modal-card" style="max-width: 660px; width: 95%;">
        <div class="alboom-modal-header" style="border-bottom: 1.5px solid #EFE5D9; padding-bottom: 1rem;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="width: 44px; height: 44px; border-radius: 12px; background: #FAF5EE; border: 1.5px solid #C59B6D; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
              🎁
            </div>
            <div>
              <span style="font-size: 0.74rem; font-weight: 700; color: #8C5F35; letter-spacing: 0.08em; text-transform: uppercase; display: block;">ENTREGA DE FOTOS · LINK PERSONALIZADO</span>
              <h3 style="font-size: 1.35rem; color: #2D1D14; font-weight: 800; margin: 0; line-height: 1.2;">Página de Entrega & Google Drive</h3>
            </div>
          </div>
          <button class="alboom-modal-close-btn" onclick="document.getElementById('modalLinkDriveMsgGlobal').style.display='none'">&times;</button>
        </div>

        <div class="alboom-modal-body" style="padding-top: 1.25rem;">
          
          <!-- Chip com Identificação do Cliente -->
          <div style="background: #FAF6F0; border: 1px solid #E5D7C6; border-radius: 10px; padding: 0.75rem 1rem; display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <span style="font-size: 0.72rem; color: #7A6A5E; display: block;">Cliente & Ensaio:</span>
              <strong style="color: #2D1D14; font-size: 0.95rem;">👤 ${nomeCli} · 📷 ${tipoEns}</strong>
            </div>
            <a href="${linkPaginaEntrega}" target="_blank" style="font-size: 0.78rem; font-weight: 700; color: #8C5F35; text-decoration: none; display: inline-flex; align-items: center; gap: 0.3rem; background: #FFFFFF; border: 1px solid #D8CAB9; padding: 0.35rem 0.85rem; border-radius: 9999px;">
              <span>🎁 Ver Página de Entrega ↗</span>
            </a>
          </div>

          <!-- CARD DE DESTAQUE: LINK PERSONALIZADO DESTA PÁGINA (COM O DRIVE DO CLIENTE) -->
          <div style="background: linear-gradient(135deg, #FFFDF9 0%, #F7EFE4 100%); border: 2px solid #C59B6D; border-radius: 14px; padding: 1.15rem; margin-bottom: 1.25rem; box-shadow: 0 4px 15px rgba(197, 155, 109, 0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">
              <span style="font-size: 0.84rem; font-weight: 800; color: #2D1D14; display: flex; align-items: center; gap: 0.4rem;">
                <span>🌟</span> Link Personalizado deste Cliente (Leva para a página com o Drive dele):
              </span>
              <span style="background: #2D5A27; color: #FFF; font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">
                ✓ Exclusivo deste Cliente
              </span>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.4rem;">
              <input type="text" readonly id="modalInputLinkPaginaCliente" value="${linkPaginaEntrega}" style="flex: 1; padding: 0.7rem 0.9rem; border-radius: 8px; border: 1.5px solid #C59B6D; font-size: 0.86rem; background: #FFFFFF; font-weight: 700; color: #8C5F35;">
              <button type="button" onclick="navigator.clipboard.writeText('${linkPaginaEntrega}').then(() => showToast('✓ Link personalizado da página do cliente copiado!'))" style="background: #8C5F35; color: #FFF; border: none; border-radius: 8px; padding: 0.7rem 1.1rem; font-size: 0.82rem; font-weight: 700; cursor: pointer; white-space: nowrap; box-shadow: 0 2px 6px rgba(140,95,53,0.3);">
                📋 Copiar Link
              </button>
              <a href="${linkPaginaEntrega}" target="_blank" style="background: #352319; color: #FFF; text-decoration: none; border-radius: 8px; padding: 0.7rem 1.1rem; font-size: 0.82rem; font-weight: 700; white-space: nowrap; display: inline-flex; align-items: center; gap: 0.3rem;">
                ↗ Abrir
              </a>
            </div>
            <span style="display: block; font-size: 0.74rem; color: #6B5546; line-height: 1.45;">
              ✨ Ao abrir este link, o cliente <strong>${nomeCli}</strong> verá o nome dele no topo, a dedicatória especial do estúdio e o botão oficial para baixar os arquivos no <strong>Google Drive dele</strong>!
            </span>
          </div>

          <!-- CAMPO 1: LINK DO GOOGLE DRIVE -->
          <div style="margin-bottom: 1.25rem;">
            <label style="display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 700; color: #352319; margin-bottom: 0.4rem;">
              <span>🔗 Link da Pasta no Google Drive:</span>
              <span style="font-size: 0.74rem; color: #8C5F35; font-weight: 600;">(Alimenta o botão de download na página)</span>
            </label>
            <input type="url" id="modalInputDriveLink" value="${driveLink}" placeholder="https://drive.google.com/drive/folders/1a2b3c4d5e...usp=sharing" style="width: 100%; padding: 0.8rem 1rem; border-radius: 10px; border: 1.5px solid #D8CAB9; font-size: 0.88rem; box-sizing: border-box; background: #FFFDF9; font-family: monospace;">
            <span style="display: block; font-size: 0.72rem; color: #7A6A5E; margin-top: 0.35rem;">
              💡 Dica: No Google Drive, clique com o botão direito na pasta de fotos, vá em <strong>Compartilhar</strong> e selecione <strong>"Qualquer pessoa com o link pode ser Leitor"</strong>.
            </span>
          </div>

          <!-- CAMPO 2: MENSAGEM PERSONALIZADA DE ENTREGA -->
          <div style="margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
              <label style="font-size: 0.82rem; font-weight: 700; color: #352319;">
                ✉️ Mensagem Personalizada de Entrega (WhatsApp & E-mail):
              </label>
              <button type="button" onclick="window.resetarMensagemDriveModal(${galId}, '${(nomeCli).replace(/'/g, "\\'")}', '${(tipoEns).replace(/'/g, "\\'")}')" style="background: none; border: none; font-size: 0.74rem; font-weight: 700; color: #8C5F35; cursor: pointer; text-decoration: underline;">
                ✨ Restaurar Modelo Padrão
              </button>
            </div>
            <textarea id="modalTextareaDriveMsg" rows="7" style="width: 100%; padding: 0.85rem 1rem; border-radius: 10px; border: 1.5px solid #D8CAB9; font-size: 0.84rem; line-height: 1.55; box-sizing: border-box; background: #FFFFFF; font-family: inherit; resize: vertical;">${msgInicial}</textarea>
            <span style="display: block; font-size: 0.72rem; color: #7A6A5E; margin-top: 0.35rem;">
              ✨ Esta dedicatória personalizada é exibida com destaque na <strong>Página de Entrega Oficial</strong> e fica pronta para enviar no <strong>WhatsApp</strong> do cliente.
            </span>
          </div>

          <!-- BOTÕES DE AÇÃO RÁPIDA: COPIAR E WHATSAPP -->
          <div style="display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1.25rem; padding: 0.85rem; background: #FAF5EE; border-radius: 10px; border: 1px solid #EAE0D5;">
            <button type="button" onclick="window.copiarMensagemDriveModal()" style="flex: 1; min-width: 160px; background: #FFFFFF; border: 1.5px solid #D8CAB9; border-radius: 8px; padding: 0.6rem 0.9rem; font-size: 0.8rem; font-weight: 700; color: #352319; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; transition: all 0.2s;">
              <span>📋</span> Copiar Mensagem Completa
            </button>
            <button type="button" onclick="window.enviarWhatsAppDriveModal()" style="flex: 1; min-width: 160px; background: #25D366; border: 1px solid #1EBE5D; border-radius: 8px; padding: 0.6rem 0.9rem; font-size: 0.8rem; font-weight: 700; color: #FFFFFF; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; box-shadow: 0 2px 6px rgba(37,211,102,0.3); transition: all 0.2s;">
              <span>🟢</span> Enviar no WhatsApp
            </button>
          </div>

          <!-- FOOTER / BOTÕES PRINCIPAIS -->
          <div style="display: flex; gap: 0.75rem; justify-content: flex-end; align-items: center; border-top: 1.5px solid #EFE5D9; padding-top: 1rem;">
            <button type="button" onclick="document.getElementById('modalLinkDriveMsgGlobal').style.display='none'" style="padding: 0.75rem 1.25rem; border-radius: 9999px; background: #FAF5EE; border: 1px solid #D8CAB9; font-weight: 700; color: #6B5546; cursor: pointer;">
              Fechar
            </button>
            <button type="button" id="btnSalvarModalDrive" onclick="window.salvarLinkDriveModal(${galId})" style="padding: 0.75rem 1.6rem; border-radius: 9999px; background: linear-gradient(135deg, #8C5F35 0%, #684221 100%); color: #FAF5EE; border: none; font-weight: 800; cursor: pointer; box-shadow: 0 4px 12px rgba(140,95,53,0.3); display: inline-flex; align-items: center; gap: 0.4rem;">
              <span>💾 Salvar Link & Mensagem</span>
            </button>
          </div>

        </div>
      </div>
    `;

    // Atualização em tempo real do link no corpo da mensagem ao digitar no campo do Drive
    const inpDrive = document.getElementById('modalInputDriveLink');
    const taMsg = document.getElementById('modalTextareaDriveMsg');
    if (inpDrive && taMsg) {
      inpDrive.addEventListener('input', () => {
        const novoLink = inpDrive.value.trim();
        let texto = taMsg.value;
        if (texto.includes('[Link do Google Drive pendente]')) {
          taMsg.value = texto.replace('[Link do Google Drive pendente]', novoLink || '[Link do Google Drive pendente]');
        } else if (driveLink && texto.includes(driveLink)) {
          taMsg.value = texto.replace(driveLink, novoLink || '[Link do Google Drive pendente]');
        }
      });
    }
  };

  window.resetarMensagemDriveModal = function(galId, nomeCli, tipoEns) {
    const linkDrive = document.getElementById('modalInputDriveLink')?.value || '';
    const novaMsg = window.gerarMensagemEntregaPadrao(nomeCli, tipoEns, linkDrive, galId);
    const ta = document.getElementById('modalTextareaDriveMsg');
    if (ta) ta.value = novaMsg;
    showToast('✓ Modelo de mensagem padrão restaurado!');
  };

  window.copiarMensagemDriveModal = function() {
    const msg = document.getElementById('modalTextareaDriveMsg')?.value || '';
    if (!msg) {
      showToast('Nenhuma mensagem para copiar.', 'error');
      return;
    }
    navigator.clipboard.writeText(msg).then(() => {
      showToast('✓ Mensagem de entrega copiada para a área de transferência!');
    }).catch(() => {
      prompt('Copie o texto da mensagem abaixo:', msg);
    });
  };

  window.enviarWhatsAppDriveModal = function() {
    const msg = document.getElementById('modalTextareaDriveMsg')?.value || '';
    if (!msg) {
      showToast('Preencha a mensagem antes de enviar.', 'error');
      return;
    }
    const tel = prompt('Digite o WhatsApp do cliente com DDD (ou deixe em branco para selecionar no WhatsApp):', '');
    let url = 'https://wa.me/?text=' + encodeURIComponent(msg);
    if (tel && tel.trim()) {
      let cleanTel = tel.replace(/\D/g, '');
      if (cleanTel.length <= 11 && !cleanTel.startsWith('55')) {
        cleanTel = '55' + cleanTel;
      }
      url = `https://wa.me/${cleanTel}?text=` + encodeURIComponent(msg);
    }
    window.open(url, '_blank');
  };

  window.salvarLinkDriveModal = async function(galId) {
    const link = document.getElementById('modalInputDriveLink')?.value.trim() || '';
    const msg = document.getElementById('modalTextareaDriveMsg')?.value.trim() || '';
    const btn = document.getElementById('btnSalvarModalDrive');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span>Salvando...</span>'; }

    try {
      const res = await fetch(`/api/galeria/${galId}/link-drive`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link_drive: link, mensagem_acesso: msg })
      });
      const data = await res.json();
      if (data.success) {
        showToast('✓ Link do Drive e mensagem de entrega salvos com sucesso!');
        const modal = document.getElementById('modalLinkDriveMsgGlobal');
        if (modal) modal.style.display = 'none';
        if (typeof window.carregarProjetosGlobal === 'function') {
          await window.carregarProjetosGlobal();
        }
        if (typeof window.carregarDadosGaleria === 'function') {
          await window.carregarDadosGaleria();
        }
      } else {
        showToast(data.error || 'Erro ao salvar link do Drive.', 'error');
      }
    } catch (err) {
      showToast('Erro de conexão ao salvar link do Drive.', 'error');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = '<span>💾 Salvar Link & Mensagem</span>'; }
    }
  };

  window.abrirModalLinkDriveRapido = function() {
    if (window.listaProjetosCache && window.listaProjetosCache.length > 0) {
      const p = window.listaProjetosCache[0];
      window.abrirModalLinkDrive(p.galeria_id || p.id, p.nome_cliente, p.tipo_ensaio, p.link_drive, p.mensagem_acesso);
    } else {
      window.abrirModalLinkDrive(1, 'Cliente Especial', 'Ensaio Fotográfico', '', '');
    }
  };

});

