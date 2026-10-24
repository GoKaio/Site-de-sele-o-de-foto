const express = require('express');
const cors = require('cors');
const path = require('path');
const config = require('./config/env');
const { testConnection } = require('./config/db');
const apiRoutes = require('./routes/apiRoutes');

const app = express();

// ── Middlewares Globais ──────────────────────────────────────────────────────
app.use(cors());
app.use(express.json({ limit: '15mb' }));
app.use(express.urlencoded({ extended: true, limit: '15mb' }));

// ── Arquivos Estáticos ────────────────────────────────────────────────────────
// Serve a pasta public (onde estão as interfaces do Portal e scripts anti-print)
app.use('/public', express.static(path.join(__dirname, '..', 'public')));
// Serve arquivos estáticos da raiz do estúdio (assets, logo, CSS, etc.)
app.use(express.static(path.join(__dirname, '..')));

// ── Rotas de API ─────────────────────────────────────────────────────────────
app.use('/api', apiRoutes);

// ── Rotas Amigáveis do Portal Multi-Galeria (Módulo 2) ────────────────────────
// 1. Dashboard inicial do cliente: /portal/:token
app.get('/portal/:token', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'portal.html'));
});

// 2. Galeria de seleção do ensaio: /portal/:token/album/:albumId
app.get('/portal/:token/album/:albumId', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'portal-album.html'));
});

// ── Tratamento Centralizado de Erros ──────────────────────────────────────────
app.use((err, req, res, next) => {
  console.error('[Express Error]', err);

  // Erros do Multer (limite de tamanho / quantidade de arquivos)
  if (err.name === 'MulterError') {
    return res.status(400).json({
      error: 'Erro no envio de arquivos.',
      code: err.code,
      message: err.message
    });
  }

  return res.status(500).json({
    error: 'Erro interno no servidor.',
    message: err.message || 'Erro inesperado'
  });
});

// ── Inicialização do Servidor ────────────────────────────────────────────────
async function startServer() {
  await testConnection();

  app.listen(config.port, config.host, () => {
    console.log(`
=============================================================
  📸 CASA DA FOTO STUDIO - SERVIDOR NODE.JS ATIVO
=============================================================
  Ambiente: ${config.nodeEnv}
  Endereço: http://${config.host}:${config.port}
  
  🔗 Rotas Principais:
  - Portal do Cliente: http://${config.host}:${config.port}/portal/a1b2c3d4e5f67890abcdef1234567890
  - API Base:          http://${config.host}:${config.port}/api
=============================================================
    `);
  });
}

startServer();

module.exports = app;
