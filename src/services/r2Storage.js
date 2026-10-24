let PutObjectCommand = null;
try {
  PutObjectCommand = require('@aws-sdk/client-s3').PutObjectCommand;
} catch (e) {}

const path = require('path');
const fs = require('fs');
const { s3Client, bucketName, publicUrl } = require('../config/r2');

// Garante existência de pasta de upload local caso R2 não esteja configurado
const uploadsBaseDir = path.join(process.cwd(), 'uploads', 'photos');
if (!fs.existsSync(uploadsBaseDir)) {
  fs.mkdirSync(uploadsBaseDir, { recursive: true });
}

/**
 * Realiza o upload de fotos:
 * - Se as credenciais do Cloudflare R2 estiverem presentes, envia para a nuvem R2.
 * - Caso contrário, armazena no disco local do servidor em `uploads/photos/` (100% gratuito e definitivo).
 * 
 * @param {string} storageKey Caminho / Chave do objeto (ex: albums/1/abc_thumb.webp)
 * @param {Buffer} buffer Conteúdo binário otimizado da foto
 * @param {string} contentType Tipo MIME (ex: 'image/webp')
 * @returns {Promise<{ storageKey: string, url: string }>}
 */
async function uploadToR2(storageKey, buffer, contentType = 'image/webp') {
  // MODO NUVEM: se as chaves S3/R2 estiverem configuradas
  if (s3Client) {
    try {
      const command = new PutObjectCommand({
        Bucket: bucketName,
        Key: storageKey,
        Body: buffer,
        ContentType: contentType,
        CacheControl: 'public, max-age=31536000, immutable'
      });

      await s3Client.send(command);

      const fullUrl = publicUrl 
        ? `${publicUrl}/${storageKey}`
        : `https://${bucketName}.r2.cloudflarestorage.com/${storageKey}`;

      return {
        storageKey,
        url: fullUrl
      };
    } catch (r2Error) {
      console.warn(`[Storage] Falha no envio para Cloudflare R2 (${r2Error.message}). Alternando automaticamente para armazenamento local.`);
    }
  }

  // MODO LOCAL GRATUITO (Zero Custo): salva no disco local com pastas organizadas
  const targetPath = path.join(uploadsBaseDir, storageKey);
  const targetFolder = path.dirname(targetPath);

  if (!fs.existsSync(targetFolder)) {
    fs.mkdirSync(targetFolder, { recursive: true });
  }

  await fs.promises.writeFile(targetPath, buffer);

  // Retorna a URL pública local relativa servida pelo Express
  const localUrl = `/uploads/photos/${storageKey.replace(/\\/g, '/')}`;

  return {
    storageKey,
    url: localUrl
  };
}

module.exports = {
  uploadToR2
};
