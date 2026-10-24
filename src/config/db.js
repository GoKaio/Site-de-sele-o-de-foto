const mysql = require('mysql2/promise');
const config = require('./env');

// Criação do Pool de Conexões MySQL para alta concorrência e reaproveitamento de conexões
const pool = mysql.createPool({
  host: config.db.host,
  user: config.db.user,
  password: config.db.password,
  database: config.db.database,
  port: config.db.port,
  waitForConnections: config.db.waitForConnections,
  connectionLimit: config.db.connectionLimit,
  queueLimit: config.db.queueLimit,
  timezone: '-03:00',
  dateStrings: true
});

/**
 * Testa a conexão com o banco MySQL
 */
async function testConnection() {
  try {
    const connection = await pool.getConnection();
    console.log(`[MySQL] Conectado com sucesso ao banco '${config.db.database}' em ${config.db.host}:${config.db.port}`);
    connection.release();
    return true;
  } catch (error) {
    console.error(`[MySQL] Falha ao conectar ao banco de dados: ${error.message}`);
    return false;
  }
}

module.exports = {
  pool,
  testConnection
};
