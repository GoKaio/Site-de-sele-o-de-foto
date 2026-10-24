const { pool } = require('../config/db');

/**
 * MÓDULO 2 - Requisito 2: GET /api/portal/:token
 * Retorna os dados do cliente e a lista consolidada de todos os seus álbuns com contagens
 */
async function getClientPortal(req, res) {
  const { token } = req.params;

  if (!token || typeof token !== 'string' || token.trim().length === 0) {
    return res.status(400).json({ error: 'Token de acesso não informado.' });
  }

  try {
    // 1. Localiza o cliente pelo access_token
    const [clients] = await pool.query(
      'SELECT id, name, phone, email, access_token, created_at FROM clients WHERE access_token = ?',
      [token.trim()]
    );

    if (clients.length === 0) {
      return res.status(404).json({ error: 'Portal não encontrado. Verifique o link de acesso exclusivo.' });
    }

    const client = clients[0];

    // 2. Busca todos os álbuns vinculados a este cliente, calculando fotos totais e selecionadas
    const [albums] = await pool.query(
      `SELECT 
        a.id, 
        a.title, 
        a.cover_image_url, 
        a.event_date, 
        a.status, 
        a.max_photos_included, 
        a.created_at,
        COUNT(p.id) AS total_photos,
        CAST(COALESCE(SUM(CASE WHEN p.is_selected = 1 THEN 1 ELSE 0 END), 0) AS UNSIGNED) AS selected_photos
       FROM albums a
       LEFT JOIN photos p ON a.id = p.album_id
       WHERE a.client_id = ?
       GROUP BY a.id
       ORDER BY a.event_date DESC, a.id DESC`,
      [client.id]
    );

    return res.json({
      client: {
        id: client.id,
        name: client.name,
        email: client.email,
        phone: client.phone,
        access_token: client.access_token
      },
      albums
    });

  } catch (error) {
    console.error(`[Portal Error] Token ${token}:`, error);
    return res.status(500).json({ error: 'Erro ao carregar portal do cliente.', details: error.message });
  }
}

/**
 * MÓDULO 2 - Requisito 2: GET /api/portal/:token/album/:albumId
 * Valida se o álbum pertence àquele cliente e retorna as fotos completas
 */
async function getClientAlbumPhotos(req, res) {
  const { token, albumId } = req.params;
  const parsedAlbumId = parseInt(albumId, 10);

  if (!token || !parsedAlbumId || isNaN(parsedAlbumId)) {
    return res.status(400).json({ error: 'Parâmetros inválidos (token ou albumId ausente).' });
  }

  try {
    // 1. Valida existência do cliente com o token
    const [clients] = await pool.query(
      'SELECT id, name, email FROM clients WHERE access_token = ?',
      [token.trim()]
    );

    if (clients.length === 0) {
      return res.status(404).json({ error: 'Token de acesso inválido.' });
    }

    const client = clients[0];

    // 2. Valida se o álbum pertence a este cliente
    const [albums] = await pool.query(
      `SELECT id, client_id, title, cover_image_url, event_date, status, max_photos_included, created_at 
       FROM albums 
       WHERE id = ? AND client_id = ?`,
      [parsedAlbumId, client.id]
    );

    if (albums.length === 0) {
      return res.status(403).json({ error: 'Acesso negado: este ensaio não pertence ao cliente informado.' });
    }

    const album = albums[0];

    // 3. Busca a lista de outros álbuns do mesmo cliente para o switcher/dropdown de navegação
    const [otherAlbums] = await pool.query(
      'SELECT id, title, event_date, status FROM albums WHERE client_id = ? ORDER BY event_date DESC, id DESC',
      [client.id]
    );

    // 4. Busca as fotos do álbum sem LIMIT arbitrário, ordenadas por display_order ASC, id ASC
    const [photos] = await pool.query(
      `SELECT 
        id, 
        album_id, 
        original_name, 
        thumb_url, 
        preview_url, 
        is_selected, 
        display_order
       FROM photos 
       WHERE album_id = ? 
       ORDER BY display_order ASC, id ASC`,
      [parsedAlbumId]
    );

    const totalPhotos = photos.length;
    const selectedPhotos = photos.filter(p => Boolean(p.is_selected)).length;

    return res.json({
      client,
      album,
      other_albums: otherAlbums,
      stats: {
        total_photos: totalPhotos,
        selected_photos: selectedPhotos,
        max_photos_included: album.max_photos_included
      },
      photos
    });

  } catch (error) {
    console.error(`[Portal Album Error] Token ${token}, Album ${albumId}:`, error);
    return res.status(500).json({ error: 'Erro ao carregar fotos do ensaio.', details: error.message });
  }
}

/**
 * MÓDULO 2 - Requisito 2: POST /api/portal/:token/album/:albumId/select
 * Salva a seleção/favoritação de fotos do álbum pelo cliente
 */
async function saveClientPhotoSelection(req, res) {
  const { token, albumId } = req.params;
  const parsedAlbumId = parseInt(albumId, 10);
  const { selected_ids, photo_id, is_selected, finalize } = req.body;

  if (!token || !parsedAlbumId || isNaN(parsedAlbumId)) {
    return res.status(400).json({ error: 'Parâmetros inválidos.' });
  }

  const connection = await pool.getConnection();

  try {
    // 1. Valida cliente
    const [clients] = await connection.query(
      'SELECT id, name FROM clients WHERE access_token = ?',
      [token.trim()]
    );

    if (clients.length === 0) {
      connection.release();
      return res.status(404).json({ error: 'Cliente não autenticado.' });
    }

    const client = clients[0];

    // 2. Valida posse do álbum
    const [albums] = await connection.query(
      'SELECT id, title, status, max_photos_included FROM albums WHERE id = ? AND client_id = ?',
      [parsedAlbumId, client.id]
    );

    if (albums.length === 0) {
      connection.release();
      return res.status(403).json({ error: 'Álbum não pertence a este cliente.' });
    }

    const album = albums[0];

    await connection.beginTransaction();

    // MODO A: Atualização em lote (array com todos os IDs selecionados)
    if (Array.isArray(selected_ids)) {
      // Desmarca todas as fotos deste álbum
      await connection.query('UPDATE photos SET is_selected = 0 WHERE album_id = ?', [parsedAlbumId]);

      // Marca apenas as selecionadas
      if (selected_ids.length > 0) {
        const sanitizedIds = selected_ids.map(id => parseInt(id, 10)).filter(id => !isNaN(id));
        if (sanitizedIds.length > 0) {
          await connection.query(
            `UPDATE photos SET is_selected = 1 WHERE album_id = ? AND id IN (${sanitizedIds.map(() => '?').join(',')})`,
            [parsedAlbumId, ...sanitizedIds]
          );
        }
      }
    } 
    // MODO B: Toggle unitário de uma foto específica
    else if (photo_id !== undefined) {
      const parsedPhotoId = parseInt(photo_id, 10);
      const newStatus = is_selected ? 1 : 0;

      await connection.query(
        'UPDATE photos SET is_selected = ? WHERE album_id = ? AND id = ?',
        [newStatus, parsedAlbumId, parsedPhotoId]
      );
    } else {
      await connection.rollback();
      connection.release();
      return res.status(400).json({ error: 'Informe `selected_ids` (array) ou `photo_id` + `is_selected`.' });
    }

    // Se o cliente marcou para finalizar o ensaio
    if (finalize === true) {
      await connection.query(
        "UPDATE albums SET status = 'concluido' WHERE id = ?",
        [parsedAlbumId]
      );
    }

    // Busca contagem atualizada
    const [countRows] = await connection.query(
      'SELECT COUNT(*) AS count FROM photos WHERE album_id = ? AND is_selected = 1',
      [parsedAlbumId]
    );

    await connection.commit();
    connection.release();

    const currentSelected = countRows[0].count;

    return res.json({
      success: true,
      message: 'Seleção salva com sucesso!',
      selected_photos: currentSelected,
      max_photos_included: album.max_photos_included,
      extra_photos: Math.max(0, currentSelected - album.max_photos_included)
    });

  } catch (error) {
    await connection.rollback();
    connection.release();
    console.error(`[Select Error] Album ${albumId}:`, error);
    return res.status(500).json({ error: 'Erro ao salvar seleção de fotos.', details: error.message });
  }
}

module.exports = {
  getClientPortal,
  getClientAlbumPhotos,
  saveClientPhotoSelection
};
