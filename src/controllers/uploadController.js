const crypto = require('crypto');
const path = require('path');
const { pool } = require('../config/db');
const { processThumbnail, processPreview } = require('../services/imageProcessor');
const { uploadToR2 } = require('../services/r2Storage');
const { processInBatches } = require('../services/batchQueue');
const config = require('../config/env');

/**
 * MÓDULO 1: Upload em lote com concorrência limitada e confirmação atômica no MySQL
 * Rota: POST /api/albums/:albumId/photos/upload
 */
async function uploadBatchPhotos(req, res) {
  const albumId = parseInt(req.params.albumId || req.body.album_id, 10);

  if (!albumId || isNaN(albumId)) {
    return res.status(400).json({ error: 'ID do álbum inválido ou não informado.' });
  }

  const files = req.files;
  if (!files || files.length === 0) {
    return res.status(400).json({ error: 'Nenhum arquivo enviado para upload.' });
  }

  try {
    // 1. Valida se o álbum existe no banco
    const [albumRows] = await pool.query('SELECT id, title FROM albums WHERE id = ?', [albumId]);
    if (albumRows.length === 0) {
      return res.status(404).json({ error: `Álbum com ID ${albumId} não encontrado.` });
    }

    // 2. Busca a ordem máxima atual para ordenar sequencialmente
    const [orderRows] = await pool.query(
      'SELECT COALESCE(MAX(display_order), 0) AS max_order FROM photos WHERE album_id = ?',
      [albumId]
    );
    let baseOrder = orderRows[0].max_order;

    console.log(`[Upload] Iniciando processamento de ${files.length} fotos para o álbum ${albumId} com concorrência = ${config.processing.concurrency}`);

    // 3. Processamento em Lote com Concorrência Limitada (ex: 4 fotos simultâneas)
    const batchResults = await processInBatches(files, config.processing.concurrency, async (file, index) => {
      const originalName = file.originalname;
      const fileId = crypto.randomBytes(8).toString('hex');
      const sanitizedBase = path.parse(originalName).name.replace(/[^a-zA-Z0-9_\-]/g, '_');

      // Chaves de armazenamento no Bucket R2
      const thumbStorageKey = `albums/${albumId}/${sanitizedBase}_${fileId}_thumb.webp`;
      const previewStorageKey = `albums/${albumId}/${sanitizedBase}_${fileId}_preview.webp`;

      // ETAPA A: Otimização e geração de Thumbnail e Preview com Sharp
      const thumbBuffer = await processThumbnail(file.buffer);
      const previewBuffer = await processPreview(file.buffer, true);

      // ETAPA B: Envio para Cloudflare R2
      const [thumbResult, previewResult] = await Promise.all([
        uploadToR2(thumbStorageKey, thumbBuffer, 'image/webp'),
        uploadToR2(previewStorageKey, previewBuffer, 'image/webp')
      ]);

      if (!thumbResult?.url || !previewResult?.url) {
        throw new Error(`Falha no upload para o Cloudflare R2 para o arquivo ${originalName}`);
      }

      // ETAPA C: Confirmação Atômica - Apenas insere no MySQL após sucesso comprovado no R2
      const currentOrder = baseOrder + index + 1;
      const [insertResult] = await pool.query(
        `INSERT INTO photos (album_id, original_name, storage_key, thumb_url, preview_url, is_selected, display_order)
         VALUES (?, ?, ?, ?, ?, 0, ?)`,
        [albumId, originalName, previewStorageKey, thumbResult.url, previewResult.url, currentOrder]
      );

      return {
        id: insertResult.insertId,
        original_name: originalName,
        thumb_url: thumbResult.url,
        preview_url: previewResult.url,
        display_order: currentOrder
      };
    });

    // 4. Compilação do Relatório Consolidado de Upload
    const uploaded = [];
    const failed = [];
    const failedDetails = [];

    batchResults.forEach((resItem) => {
      if (resItem.success) {
        uploaded.push(resItem.result);
      } else {
        const fname = resItem.item.originalname;
        failed.push(fname);
        failedDetails.push({
          filename: fname,
          error: resItem.error?.message || 'Erro desconhecido'
        });
        console.error(`[Upload Falhou] Arquivo '${fname}':`, resItem.error?.message);
      }
    });

    const responsePayload = {
      total: files.length,
      uploaded: uploaded.length,
      failed: failed, // Formato exigido: array de nomes de arquivos que falharam
      failed_details: failedDetails,
      photos: uploaded
    };

    console.log(`[Upload Concluído] Total: ${files.length} | Gravadas com sucesso: ${uploaded.length} | Falhas: ${failed.length}`);

    // Se nenhuma salvou, retorna erro 500
    if (uploaded.length === 0 && files.length > 0) {
      return res.status(500).json(responsePayload);
    }

    // Retorna HTTP 200 (ou 207 Multi-Status caso parcial)
    return res.status(failed.length > 0 ? 207 : 200).json(responsePayload);

  } catch (error) {
    console.error('[Upload Fatal]', error);
    return res.status(500).json({
      error: 'Erro interno ao processar lote de imagens.',
      details: error.message
    });
  }
}

module.exports = {
  uploadBatchPhotos
};
