const sharp = require('sharp');
const config = require('../config/env');

/**
 * Cria a marca d'água semi-transparente como buffer SVG para ser aplicada pelo Sharp
 * @param {number} width Largura da imagem
 * @param {number} height Altura da imagem
 * @returns {Buffer} Buffer do SVG da marca d'água
 */
function generateWatermarkSvg(width, height) {
  const text = 'CASA DA FOTO • PROVA';
  const fontSize = Math.max(24, Math.floor(width / 35));
  
  // Padrão diagonal repetido
  const svg = `
    <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="wmPattern" width="${fontSize * 14}" height="${fontSize * 8}" patternTransform="rotate(-30 0 0)" patternUnits="userSpaceOnUse">
          <text x="20" y="${fontSize * 3}" 
                font-family="Arial, sans-serif" 
                font-weight="bold" 
                font-size="${fontSize}" 
                fill="rgba(255, 255, 255, 0.22)"
                stroke="rgba(0, 0, 0, 0.18)"
                stroke-width="1">
            ${text}
          </text>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#wmPattern)" />
    </svg>
  `;
  return Buffer.from(svg);
}

/**
 * Redimensiona e otimiza uma imagem para visualização em miniatura (Thumbnail)
 * @param {Buffer} inputBuffer Buffer da foto original
 * @returns {Promise<Buffer>} Buffer WebP da miniatura
 */
async function processThumbnail(inputBuffer) {
  return await sharp(inputBuffer)
    .rotate() // Auto-rotaciona de acordo com a orientação EXIF da câmera
    .resize({
      width: config.processing.thumbWidth,
      withoutEnlargement: true,
      fit: 'inside'
    })
    .webp({ quality: config.processing.thumbQuality, effort: 4 })
    .toBuffer();
}

/**
 * Redimensiona e otimiza uma imagem para Preview em alta definição com marca d'água
 * @param {Buffer} inputBuffer Buffer da foto original
 * @param {boolean} applyWatermark Se deve sobrepor a marca d'água de prova
 * @returns {Promise<Buffer>} Buffer WebP otimizado da pré-visualização
 */
async function processPreview(inputBuffer, applyWatermark = true) {
  let pipeline = sharp(inputBuffer)
    .rotate()
    .resize({
      width: config.processing.previewWidth,
      withoutEnlargement: true,
      fit: 'inside'
    });

  if (applyWatermark) {
    const metadata = await pipeline.metadata();
    const w = metadata.width || config.processing.previewWidth;
    const h = metadata.height || 1080;
    const wmBuffer = generateWatermarkSvg(w, h);

    pipeline = pipeline.composite([
      {
        input: wmBuffer,
        top: 0,
        left: 0,
        blend: 'over'
      }
    ]);
  }

  return await pipeline
    .webp({ quality: config.processing.previewQuality, effort: 4 })
    .toBuffer();
}

module.exports = {
  processThumbnail,
  processPreview
};
