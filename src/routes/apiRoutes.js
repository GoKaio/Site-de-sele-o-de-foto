const express = require('express');
const router = express.Router();

const upload = require('../middleware/uploadMiddleware');
const { uploadBatchPhotos } = require('../controllers/uploadController');
const { getAlbumPhotos, listAllAlbums } = require('../controllers/albumController');
const {
  getClientPortal,
  getClientAlbumPhotos,
  saveClientPhotoSelection
} = require('../controllers/portalController');

// ── MÓDULO 1: Upload em Lote e Gestão de Álbuns ──
// Upload com concorrência limitada (3 a 5 workers), Sharp, R2 e MySQL atômico
router.post('/albums/:albumId/photos/upload', upload.array('photos', 500), uploadBatchPhotos);

// Listagem completa de fotos de um álbum sem LIMIT
router.get('/albums/:albumId/photos', getAlbumPhotos);

// Listagem de todos os álbuns do estúdio
router.get('/albums', listAllAlbums);

// ── MÓDULO 2: Portal Multi-Galeria do Cliente ──
// 1. Dados do cliente e lista de ensaios com contadores
router.get('/portal/:token', getClientPortal);

// 2. Fotos do ensaio do cliente autenticado com lista para dropdown
router.get('/portal/:token/album/:albumId', getClientAlbumPhotos);

// 3. Salvar seleção/favoritação de fotos do ensaio
router.post('/portal/:token/album/:albumId/select', saveClientPhotoSelection);

module.exports = router;
