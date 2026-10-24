const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const config = require('../src/config/env');

async function initializeDatabase() {
  console.log('[DB Init] Conectando ao MySQL para inicialização do banco...');

  // Conecta primeiro sem selecionar banco específico caso ele ainda não exista
  const connection = await mysql.createConnection({
    host: config.db.host,
    user: config.db.user,
    password: config.db.password,
    port: config.db.port,
    multipleStatements: true
  });

  try {
    const schemaSql = fs.readFileSync(path.join(__dirname, '..', 'schema.sql'), 'utf-8');
    console.log('[DB Init] Executando schema.sql...');

    await connection.query(schemaSql);
    console.log('✅ Banco de dados `casadafoto_db` e tabelas criados com sucesso!');
    console.log('✅ Dados de teste inseridos: Cliente token "a1b2c3d4e5f67890abcdef1234567890".');
  } catch (error) {
    console.error('❌ Erro ao inicializar banco de dados:', error.message);
  } finally {
    await connection.end();
  }
}

initializeDatabase();
