const { processInBatches } = require('../src/services/batchQueue');

async function testQueue() {
  console.log('--- Testando Fila de Lotes com Concorrência Limitada ---');

  const items = [
    { name: 'foto1.jpg', fail: false },
    { name: 'foto2.jpg', fail: false },
    { name: 'foto3_corrompida.jpg', fail: true },
    { name: 'foto4.jpg', fail: false },
    { name: 'foto5.jpg', fail: false },
    { name: 'foto6.jpg', fail: false },
    { name: 'foto7.jpg', fail: false }
  ];

  let currentActive = 0;
  let maxActiveObserved = 0;
  const CONCURRENCY = 3;

  const results = await processInBatches(items, CONCURRENCY, async (item) => {
    currentActive++;
    if (currentActive > maxActiveObserved) maxActiveObserved = currentActive;

    // Simula tempo de processamento do Sharp + upload R2
    await new Promise(r => setTimeout(r, 60));

    currentActive--;

    if (item.fail) {
      throw new Error(`Arquivo corrompido ou erro de I/O: ${item.name}`);
    }

    return { processed: true, filename: item.name };
  });

  const succeeded = results.filter(r => r.success).map(r => r.result.filename);
  const failed = results.filter(r => !r.success).map(r => r.item.name);

  console.log('Máxima concorrência observada:', maxActiveObserved, `(Limite esperado <= ${CONCURRENCY})`);
  console.log('Sucesso:', succeeded);
  console.log('Falharam (capturados individualmente):', failed);

  if (maxActiveObserved <= CONCURRENCY && succeeded.length === 6 && failed.length === 1) {
    console.log('✅ TESTE DA FILA PASSOU COM SUCESSO!');
  } else {
    console.error('❌ TESTE FALHOU');
    process.exit(1);
  }
}

testQueue();
