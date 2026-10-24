const config = require('./env');

// Criação do cliente AWS S3 configurado especificamente para a API S3 da Cloudflare R2
let s3Client = null;

try {
  const { S3Client } = require('@aws-sdk/client-s3');
  if (config.r2.accountId && config.r2.accessKeyId && config.r2.secretAccessKey) {
    s3Client = new S3Client({
      region: 'auto',
      endpoint: `https://${config.r2.accountId}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: config.r2.accessKeyId,
        secretAccessKey: config.r2.secretAccessKey
      }
    });
  }
} catch (err) {
  // Executa normalmente no modo local caso o SDK não esteja instalado
}

module.exports = {
  s3Client,
  bucketName: config.r2.bucketName,
  publicUrl: config.r2.publicUrl
};
