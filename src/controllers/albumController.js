const { pool } = require('../config/db');

/**
 * MÓDULO 1 - Requisito 3: Listagem completa sem LIMIT que trunque o ensaio
 * Rota: GET /api/albums/:albumId/photos
 */
async function getAlbumPhotos(req, res) {
  const albumId = parseInt(req.params.albumId, 10);

  if (!albumId || isNaN(albumId)) {
    return res.status(400).json({ error: 'ID do álbum inválido.' });
  }

  try {
    // 1. Busca dados do álbum
    const [albumRows] = await pool.query(
      'SELECT id, client_id, title, cover_image_url, event_date, status, max_photos_included, created_at FROM albums WHERE id = ?',
      [albumId]
    );

    if (albumRows.length === 0) {
      return res.status(404).json({ error: 'Álbum não encontrado.' });
    }

    const album = albumRows[0];

    // 2. Busca TODAS as fotos sem cláusula LIMIT arbitrária, ordenadas por display_order ASC, id ASC
    const [photos] = await pool.query(
      `SELECT 
        id, 
        album_id, 
        original_name, 
        storage_key, 
        thumb_url, 
        preview_url, 
        is_selected, 
        display_order, 
        created_at
       FROM photos 
       WHERE album_id = ? 
       ORDER BY display_order ASC, id ASC`,
      [albumId]
    );

    // Contadores de integridade
    const totalCount = photos.length;
    const selectedCount = photos.filter(p => Boolean(p.is_selected)).length;

    return res.json({
      album,
      total_photos: totalCount,
      selected_photos: selectedCount,
      photos
    });

  } catch (error) {
    console.error(`[getAlbumPhotos Error] Álbum ${albumId}:`, error);
    return res.status(500).json({ error: 'Erro ao buscar fotos do álbum.', details: error.message });
  }
}

/**
 * Lista todos os álbuns cadastrados no estúdio (visão do fotógrafo / admin)
 * Rota: GET /api/albums
 */
async function listAllAlbums(req, res) {
  try {
    const [albums] = await pool.query(
      `SELECT 
        a.id, 
        a.client_id, 
        c.name AS client_name,
        c.access_token,
        a.title, 
        a.cover_image_url, 
        a.event_date, 
        a.status, 
        a.max_photos_included, 
        a.created_at,
        COUNT(p.id) AS total_photos,
        SUM(CASE WHEN p.is_selected = 1 THEN 1 ELSE 0 END) AS selected_photos
       FROM albums a
       JOIN clients c ON a.client_id = c.id
       LEFT JOIN photos p ON a.id = p.album_id
       GROUP BY a.id
       ORDER BY a.created_at DESC`
    );

    return res.json({ albums });
  } catch (error) {
    console.error('[listAllAlbums Error]:', error);
    return res.status(500).json({ error: 'Erro ao listar álbuns.', details: error.message });
  }
}

module.exports = {
  getAlbumPhotos,
  listAllAlbums
};
