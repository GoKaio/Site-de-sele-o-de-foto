/**
 * Processador de Fila em Lote com Concorrência Limitada
 * Previne estouro de memória (OOM) e saturação de CPU/Network no Sharp e R2
 * 
 * @param {Array<T>} items Lista de itens a serem processados
 * @param {number} concurrency Quantidade máxima de execuções simultâneas (ex: 3 a 5)
 * @param {Function} taskFn Função assíncrona que executa o processamento do item: (item, index) => Promise<R>
 * @returns {Promise<Array<{ item: T, success: boolean, result?: any, error?: Error }>>}
 */
async function processInBatches(items, concurrency = 4, taskFn) {
  const results = new Array(items.length);
  let currentIndex = 0;

  // Cria workers concorrentes
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (currentIndex < items.length) {
      const index = currentIndex++;
      const item = items[index];

      try {
        const result = await taskFn(item, index);
        results[index] = { item, success: true, result };
      } catch (error) {
        // Captura o erro individual sem derrubar o restante da fila
        results[index] = { item, success: false, error };
      }
    }
  });

  await Promise.all(workers);
  return results;
}

module.exports = {
  processInBatches
};
