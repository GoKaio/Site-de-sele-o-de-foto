try {
  if (typeof process.loadEnvFile === 'function') {
    process.loadEnvFile('.env');
  } else {
    require('dotenv').config();
  }
} catch (e) {}

module.exports = {
  port: parseInt(process.env.NODE_PORT, 10) || 3000,
  host: process.env.HOST || '127.0.0.1',
  nodeEnv: process.env.NODE_ENV || 'development',

  db: {
    host: process.env.DB_HOST || '127.0.0.1',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'casadafoto_db',
    port: parseInt(process.env.DB_PORT, 10) || 3306,
    connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT, 10) || 10,
    waitForConnections: true,
    queueLimit: 0
  },

  r2: {
    accountId: process.env.R2_ACCOUNT_ID || '',
    accessKeyId: process.env.R2_ACCESS_KEY_ID || '',
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY || '',
    bucketName: process.env.R2_BUCKET_NAME || 'casadafoto-uploads',
    publicUrl: (process.env.R2_PUBLIC_URL || '').replace(/\/$/, '')
  },

  processing: {
    concurrency: parseInt(process.env.BATCH_CONCURRENCY, 10) || 4,
    thumbWidth: parseInt(process.env.THUMB_WIDTH, 10) || 400,
    thumbQuality: parseInt(process.env.THUMB_QUALITY, 10) || 80,
    previewWidth: parseInt(process.env.PREVIEW_WIDTH, 10) || 1920,
    previewQuality: parseInt(process.env.PREVIEW_QUALITY, 10) || 85
  }
};
