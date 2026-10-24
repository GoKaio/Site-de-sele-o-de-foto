/**
 * ==============================================================================
 * CASA DA FOTO STUDIO - MÓDULO 3: SISTEMA ANTI-PRINT E PROTEÇÃO DE IMAGEM
 * ==============================================================================
 * Camadas de dissuasão e proteção para a galeria de prova e modal de zoom:
 * 1. Bloqueio de eventos (contextmenu, dragstart) e atalhos (Ctrl+S, Ctrl+P, F12, etc.)
 * 2. Escudo Transparente (Shield Layer) com pointer-events: none na tag <img>
 * 3. Dissuasão de Captura: Limpeza do clipboard no PrintScreen + blur(25px) por 2s
 * 4. Blur imediato ao perder o foco (window.onblur / visibilitychange)
 * 5. Marca d'água semi-transparente sobreposta
 * ==============================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.AntiPrintProtection = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const defaultOptions = {
    gallerySelector: '#galleryContainer, .proofing-cards-grid, .photo-grid',
    modalSelector: '#zoomModal, .zoom-modal-container',
    blurDurationMs: 2000,
    blurAmount: '25px',
    toastMessages: {
      blockedMenu: '🔒 Imagem protegida — Direitos autorais reservados à Casa da Foto.',
      blockedShortcut: '🔒 Ação desabilitada nesta galeria de seleção.',
      printScreen: '⚠️ Captura de tela não permitida — Área de transferência limpa.'
    }
  };

  let isInitialized = false;
  let activeBlurTimeout = null;

  function showToastNotice(message) {
    let toast = document.getElementById('antiPrintToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'antiPrintToast';
      toast.className = 'anti-print-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('visible');

    if (toast._timer) clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.remove('visible');
    }, 2800);
  }

  function applyGalleryBlur(container, durationMs = 2000) {
    if (!container) return;
    container.classList.add('protection-blur-active');

    if (activeBlurTimeout) clearTimeout(activeBlurTimeout);
    activeBlurTimeout = setTimeout(() => {
      container.classList.remove('protection-blur-active');
    }, durationMs);
  }

  function clearGalleryBlur(container) {
    if (!container) return;
    if (activeBlurTimeout) clearTimeout(activeBlurTimeout);
    container.classList.remove('protection-blur-active');
    container.classList.remove('window-unfocused-blur');
  }

  function init(options = {}) {
    if (isInitialized) return;
    isInitialized = true;

    const opts = Object.assign({}, defaultOptions, options);

    // ── REQUISITO 1: Bloqueio de Menu de Contexto (Botão Direito) ─────────────
    document.addEventListener('contextmenu', function (e) {
      const target = e.target;
      const isGalleryOrModal = target.closest(opts.gallerySelector) || 
                               target.closest(opts.modalSelector) ||
                               target.tagName === 'IMG' ||
                               target.classList.contains('photo-shield');

      if (isGalleryOrModal) {
        e.preventDefault();
        e.stopPropagation();
        showToastNotice(opts.toastMessages.blockedMenu);
        return false;
      }
    }, true);

    // ── REQUISITO 1: Bloqueio de Dragstart (Arrastar imagens) ─────────────────
    document.addEventListener('dragstart', function (e) {
      if (e.target && e.target.tagName === 'IMG') {
        e.preventDefault();
        return false;
      }
    }, true);

    // ── REQUISITO 1: Bloqueio de Atalhos (Ctrl+S, Ctrl+P, Ctrl+U, F12, Ctrl+Shift+I)
    document.addEventListener('keydown', function (e) {
      const key = (e.key || '').toLowerCase();
      const ctrlOrCmd = e.ctrlKey || e.metaKey;

      // F12 (DevTools)
      if (e.key === 'F12') {
        e.preventDefault();
        showToastNotice(opts.toastMessages.blockedShortcut);
        return false;
      }

      // Ctrl + S / Cmd + S (Salvar Página)
      if (ctrlOrCmd && key === 's') {
        e.preventDefault();
        showToastNotice(opts.toastMessages.blockedShortcut);
        return false;
      }

      // Ctrl + P / Cmd + P (Impressão / PDF)
      if (ctrlOrCmd && key === 'p') {
        e.preventDefault();
        showToastNotice(opts.toastMessages.blockedShortcut);
        return false;
      }

      // Ctrl + U / Cmd + U (Ver Código Fonte)
      if (ctrlOrCmd && key === 'u') {
        e.preventDefault();
        showToastNotice(opts.toastMessages.blockedShortcut);
        return false;
      }

      // Ctrl + Shift + I / Cmd + Opt + I (Inspecionar Elemento)
      // Ctrl + Shift + J (Console) ou Ctrl + Shift + C
      if (ctrlOrCmd && e.shiftKey && (key === 'i' || key === 'j' || key === 'c')) {
        e.preventDefault();
        showToastNotice(opts.toastMessages.blockedShortcut);
        return false;
      }
    }, true);

    // ── REQUISITO 3: Dissuasão de Captura de Tela (PrintScreen) ────────────────
    // No evento keyup da tecla PrintScreen: limpa clipboard e aplica blur(25px) por 2s
    window.addEventListener('keyup', function (e) {
      if (e.key === 'PrintScreen' || e.code === 'PrintScreen' || e.keyCode === 44) {
        // 1. Limpa a área de transferência
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText('').catch(() => {
            // Falha silenciosa caso permissão não concedida
          });
        }

        // 2. Aplica classe com blur(25px) no container por 2 segundos
        const targetContainer = document.querySelector(opts.gallerySelector) || document.body;
        applyGalleryBlur(targetContainer, opts.blurDurationMs);

        showToastNotice(opts.toastMessages.printScreen);
      }
    });

    // ── REQUISITO 3: Blur imediato caso a janela perca o foco ────────────────
    window.addEventListener('blur', function () {
      const targetContainer = document.querySelector(opts.gallerySelector) || document.body;
      targetContainer.classList.add('window-unfocused-blur');
    });

    window.addEventListener('focus', function () {
      const targetContainer = document.querySelector(opts.gallerySelector) || document.body;
      targetContainer.classList.remove('window-unfocused-blur');
    });

    document.addEventListener('visibilitychange', function () {
      const targetContainer = document.querySelector(opts.gallerySelector) || document.body;
      if (document.hidden) {
        targetContainer.classList.add('window-unfocused-blur');
      } else {
        targetContainer.classList.remove('window-unfocused-blur');
      }
    });

    console.log('[AntiPrintProtection] Camadas de proteção e dissuasão ativadas com sucesso.');
  }

  return {
    init,
    showToastNotice,
    applyGalleryBlur
  };
});
