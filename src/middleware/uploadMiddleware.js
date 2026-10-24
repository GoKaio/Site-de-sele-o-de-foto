const multer = require('multer');

// Armazenamento em memória para envio direto de buffers ao Sharp e R2
const storage = multer.memoryStorage();

// Filtro de validação de formato de arquivo (apenas imagens fotográficas)
const fileFilter = (req, file, cb) => {
  const allowedMimes = [
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'image/tiff',
    'image/heic',
    'image/x-canon-cr2',
    'image/x-nikon-nef',
    'image/x-sony-arw'
  ];

  if (allowedMimes.includes(file.mimetype) || file.originalname.match(/\.(jpe?g|png|webp|tiff|cr2|nef|arw)$/i)) {
    cb(null, true);
  } else {
    cb(new Error(`Formato de arquivo não suportado: ${file.originalname}. Envie fotos JPEG, PNG, WebP ou RAW.`), false);
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: 60 * 1024 * 1024, // Limite de 60MB por foto
    files: 500 // Até 500 fotos por requisição multipart
  }
});

module.exports = upload;
