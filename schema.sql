-- ==============================================================================
-- CASA DA FOTO STUDIO - SCHEMA MYSQL
-- Módulo 1 & 2: Gestão de Clientes, Álbuns (Multi-Galeria) e Fotos
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS casadafoto_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE casadafoto_db;

-- 1. TABELA DE CLIENTES
CREATE TABLE IF NOT EXISTS clients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  phone VARCHAR(50),
  email VARCHAR(255),
  access_token VARCHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_clients_access_token (access_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. TABELA DE ÁLBUNS / ENSAIOS (MULTI-GALERIA)
CREATE TABLE IF NOT EXISTS albums (
  id INT AUTO_INCREMENT PRIMARY KEY,
  client_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  cover_image_url TEXT,
  event_date DATE,
  status ENUM('em_selecao', 'concluido') NOT NULL DEFAULT 'em_selecao',
  max_photos_included INT NOT NULL DEFAULT 20,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
  INDEX idx_albums_client_id (client_id),
  INDEX idx_albums_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. TABELA DE FOTOS
CREATE TABLE IF NOT EXISTS photos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  album_id INT NOT NULL,
  original_name VARCHAR(255) NOT NULL,
  storage_key VARCHAR(255) NOT NULL,
  thumb_url TEXT NOT NULL,
  preview_url TEXT NOT NULL,
  is_selected BOOLEAN NOT NULL DEFAULT FALSE,
  display_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
  INDEX idx_photos_album_order (album_id, display_order, id),
  INDEX idx_photos_album_selected (album_id, is_selected)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==============================================================================
-- DADOS INICIAIS DE TESTE / DEMONSTRAÇÃO (SEED)
-- ==============================================================================
-- Inserir cliente de demonstração
INSERT INTO clients (id, name, phone, email, access_token)
VALUES 
  (1, 'Mariana e Arthur Silveira', '(11) 98765-4321', 'mariana.silveira@exemplo.com', 'a1b2c3d4e5f67890abcdef1234567890')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- Inserir ensaios / álbuns do mesmo cliente (Multi-Galeria)
INSERT INTO albums (id, client_id, title, cover_image_url, event_date, status, max_photos_included)
VALUES
  (1, 1, 'Ensaio Acompanhamento - 10 Meses', 'https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=800&q=80', '2026-08-15', 'concluido', 15),
  (2, 1, 'Ensaio Acompanhamento - 11 Meses', 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=800&q=80', '2026-09-20', 'em_selecao', 20),
  (3, 1, 'Ensaio Família Especial 1 Ano', 'https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&w=800&q=80', '2026-10-18', 'em_selecao', 25)
ON DUPLICATE KEY UPDATE title=VALUES(title);

-- Inserir fotos de exemplo para o álbum 2 (11 meses)
INSERT INTO photos (id, album_id, original_name, storage_key, thumb_url, preview_url, is_selected, display_order)
VALUES
  (1, 2, 'IMG_1001.JPG', 'albums/2/IMG_1001_thumb.webp', 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=600&q=80', 'https://images.unsplash.com/photo-1519741497674-611481863552?auto=format&fit=crop&w=1920&q=85', 1, 1),
  (2, 2, 'IMG_1002.JPG', 'albums/2/IMG_1002_thumb.webp', 'https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=600&q=80', 'https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=1920&q=85', 1, 2),
  (3, 2, 'IMG_1003.JPG', 'albums/2/IMG_1003_thumb.webp', 'https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&w=600&q=80', 'https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&w=1920&q=85', 0, 3),
  (4, 2, 'IMG_1004.JPG', 'albums/2/IMG_1004_thumb.webp', 'https://images.unsplash.com/photo-1471286174890-9c112ffca56a?auto=format&fit=crop&w=600&q=80', 'https://images.unsplash.com/photo-1471286174890-9c112ffca56a?auto=format&fit=crop&w=1920&q=85', 0, 4),
  (5, 2, 'IMG_1005.JPG', 'albums/2/IMG_1005_thumb.webp', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=1920&q=85', 0, 5)
ON DUPLICATE KEY UPDATE original_name=VALUES(original_name);
