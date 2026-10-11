# Guia Definitivo: Otimização de Serverless na Vercel & Conectividade com Supabase

> **Objetivo:** Estratégias arquiteturais completas para hospedar sites na Vercel sem estourar limites de Serverless Functions (especialmente no plano Hobby), além de padrões seguros e resilientes de conectividade com Supabase e boas práticas de produção.

---

## Sumário
1. [Limites da Vercel: Como Funcionam as Serverless Functions](#1-limites-da-vercel-como-funcionam-as-serverless-functions)
2. [Estratégias para NUNCA Estourar o Limite de Funções](#2-estratégias-para-nunca-estourar-o-limite-de-funções)
   - [2.1 SSG e ISR (Cache no Edge CDN)](#21-ssg-e-isr-cache-no-edge-cdn)
   - [2.2 Client-Side Rendering (CSR) com Dados Diretos](#22-client-side-rendering-csr-com-dados-diretos)
   - [2.3 Consolidação de Rotas API (A Técnica do API Gateway Único)](#23-consolidação-de-rotas-api-a-técnica-do-api-gateway-único)
   - [2.4 Edge Runtime vs Node.js Serverless](#24-edge-runtime-vs-nodejs-serverless)
   - [2.5 Otimização de Dependências e Bundle Size](#25-otimização-de-dependências-e-bundle-size)
3. [Conectividade Perfeita: Vercel + Supabase](#3-conectividade-perfeita-vercel--supabase)
   - [3.1 O Grande Vilão: Connection Pool Exhaustion](#31-o-grande-vilão-connection-pool-exhaustion)
   - [3.2 REST API vs Conexão Direta Postgres](#32-rest-api-vs-conexão-direta-postgres)
   - [3.3 Configurando o Supavisor / Pooler (Transaction Mode)](#33-configurando-o-supavisor--pooler-transaction-mode)
   - [3.4 Instanciação Correta do Supabase Client](#34-instanciação-correta-do-supabase-client)
   - [3.5 Separação Rígida de Chaves e Segurança (RLS)](#35-separação-rígida-de-chaves-e-segurança-rls)
4. [Dicas Gerais de Infraestrutura e Performance](#4-dicas-gerais-de-infraestrutura-e-performance)
   - [4.1 Evitando Limites de Otimização de Imagens](#41-evitando-limites-de-otimização-de-imagens)
   - [4.2 On-Demand Revalidation via Webhook do Supabase](#42-on-demand-revalidation-via-webhook-do-supabase)
   - [4.3 Headers de Cache e `vercel.json`](#43-headers-de-cache-e-verceljson)
5. [Checklist Pré-Deploy](#5-checklist-pré-deploy)

---

## 1. Limites da Vercel: Como Funcionam as Serverless Functions

Na Vercel, o código que roda no servidor é compilado como **AWS Lambda functions** gerenciadas. No plano **Hobby (Gratuito)**, as restrições são rígidas:

| Recurso | Plano Hobby (Gratuito) | Plano Pro |
| :--- | :--- | :--- |
| **Limite de Serverless Functions por Deploy** | **12 funções** (limite histórico estrito de rotas geradas) | Milhares (sem teto artificial rígido) |
| **Duração Máxima de Execução (Timeout)** | **10 segundos** (ou até 15s) | Até **300 segundos** (padrão 60s) |
| **Memória por Função** | 1024 MB | Até 3008 MB |
| **Invocação Mensal / GB-Hours** | 100 GB-horas / 100k requests | 1.000 GB-horas incluídas |
| **Tamanho Máximo do Pacote (Bundle)** | 50 MB comprimido / 250 MB descompactado | 50 MB comprimido / 250 MB descompactado |

### O que conta como uma Serverless Function?
Muitos desenvolvedores são pegos de surpresa porque **não são apenas arquivos em `/api`** que viram funções:
1. **Cada endpoint isolado em `/pages/api/*.ts` ou `/api/*.js`** = 1 Serverless Function.
2. **Cada rota dinâmica no App Router (`app/api/**/route.ts`)** = 1 Serverless Function.
3. **Cada página com SSR Dinâmico**:
   - No Pages Router: páginas com `getServerSideProps`.
   - No App Router: páginas que usam `cookies()`, `headers()`, `searchParams` dinâmicos ou `export const dynamic = 'force-dynamic'` sem revalidação estática.
4. Se você tiver 8 endpoints na API e 5 páginas dinâmicas, o total é **13 funções**. O deploy **vai falhar com erro**:
   ```text
   Error: You have reached the maximum number of Serverless Functions for your Plan (12).
   ```

---

## 2. Estratégias para NUNCA Estourar o Limite de Funções

### 2.1 SSG e ISR (Cache no Edge CDN)

A forma mais elegante e veloz de eliminar serverless functions das páginas é transformá-las em conteúdo pré-renderizado entregue pelo Edge CDN da Vercel.

- **Vantagem:** Custo de função = **0**. Tempo de resposta = **10ms a 30ms** globalmente.

#### Exemplo no Next.js (App Router):
```tsx
// app/produtos/[id]/page.tsx

// 1. Gera as páginas estaticamente no build
export async function generateStaticParams() {
  const res = await fetch('https://SEU-PROJETO.supabase.co/rest/v1/produtos?select=id', {
    headers: { apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY! }
  });
  const produtos = await res.json();
  return produtos.map((p: { id: string }) => ({ id: p.id }));
}

// 2. Define revalidação em segundo plano (ISR) a cada 60 segundos
export const revalidate = 60;

export default async function ProductPage({ params }: { params: { id: string } }) {
  const res = await fetch(`https://SEU-PROJETO.supabase.co/rest/v1/produtos?id=eq.${params.id}&select=*`, {
    headers: { apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY! },
    next: { revalidate: 60 } // Cache inteligente do Next.js
  });
  const produto = await res.json();

  return (
    <main>
      <h1>{produto[0]?.nome}</h1>
      <p>R$ {produto[0]?.preco}</p>
    </main>
  );
}
```

---

### 2.2 Client-Side Rendering (CSR) com Dados Diretos

Para áreas autenticadas (painel admin, perfil do cliente, carrinho), **não gaste SSR**:
1. Sirva a página como casca estática (`export const dynamic = 'force-static'`).
2. Busque os dados no navegador diretamente do Supabase usando `@supabase/supabase-js` com Row Level Security (RLS) habilitado.
3. Use bibliotecas de cache no cliente como **TanStack Query (React Query)** ou **SWR**.

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase-client';

export function UserDashboard() {
  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const { data, error } = await supabase.from('profiles').select('*').single();
      if (error) throw error;
      return data;
    }
  });

  if (isLoading) return <div>Carregando painel...</div>;
  return <div>Bem-vindo, {profile?.name}</div>;
}
```

---

### 2.3 Consolidação de Rotas API (A Técnica do API Gateway Único)

Se o seu site precisa de endpoints de backend (ex: checkout, webhooks, processamento seguro com `SUPABASE_SERVICE_ROLE_KEY`), **NÃO crie um arquivo para cada endpoint**.

Transforme todas as suas rotas em **1 ÚNICA Serverless Function** usando um roteador interno (como [Hono](https://hono.dev/) ou rota catch-all nativa).

#### Padrão Recomendado com Hono no Next.js (App Router):
Crie apenas o arquivo `app/api/[[...route]]/route.ts`:

```typescript
// app/api/[[...route]]/route.ts
import { Hono } from 'hono';
import { handle } from 'hono/vercel';

export const runtime = 'nodejs'; // ou 'edge'

const app = new Hono().basePath('/api');

// Rota 1: Status
app.get('/health', (c) => c.json({ status: 'ok', timestamp: Date.now() }));

// Rota 2: Produtos
app.get('/produtos', async (c) => {
  // Lógica de listagem
  return c.json({ items: [] });
});

// Rota 3: Checkout Seguro
app.post('/checkout', async (c) => {
  const body = await c.req.json();
  // Lógica transacional com chave de serviço
  return c.json({ success: true, orderId: '123' });
});

// Rota 4: Webhook
app.post('/webhooks/mercadopago', async (c) => {
  return c.text('OK', 200);
});

// Exporta os métodos suportados pela Vercel
export const GET = handle(app);
export const POST = handle(app);
export const PUT = handle(app);
export const DELETE = handle(app);
```

> **Resultado:** Você pode ter 50 endpoints REST no backend da sua aplicação gastando **EXATAMENTE 1 Serverless Function** do seu limite da Vercel!

---

### 2.4 Edge Runtime vs Node.js Serverless

A Vercel suporta duas tecnologias de execução no servidor:

| Característica | Node.js Serverless Function | Edge Function |
| :--- | :--- | :--- |
| **Runtime** | Node.js completo (AWS Lambda) | V8 Isolates (Edge Engine) |
| **Cold Start** | ~200ms a 1000ms | **Quase Zero (< 20ms)** |
| **Limite de Funções** | Conta no teto de 12 (Hobby) | **Limites muito mais flexíveis** |
| **APIs Disponíveis** | Todo o ecossistema Node (`fs`, `net`, `crypto`) | Web APIs padrão (`fetch`, `Request`, `Response`) |
| **Bibliotecas Suportadas** | Qualquer biblioteca npm | Bibliotecas sem dependências nativas C++ ou `eval` |

#### Quando ativar o Edge Runtime:
Em rotas leves de leitura, redirecionamentos, proxy ou verificação rápida de tokens:

```typescript
// app/api/proxy-rapido/route.ts
export const runtime = 'edge'; // Ativa Edge Runtime

export async function GET(request: Request) {
  return new Response(JSON.stringify({ status: 'rodando no edge global' }), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

---

### 2.5 Otimização de Dependências e Bundle Size

Se o pacote de uma Serverless Function passar de **50 MB compactado**, a Vercel recusará o deploy.

1. **Evite importar SDKs inteiros**:
   - ❌ `import AWS from 'aws-sdk';`
   - ✅ `import { S3Client } from '@aws-sdk/client-s3';`
2. **Exclua pacotes desnecessários do trace no `next.config.js`**:
   ```javascript
   // next.config.js
   module.exports = {
     outputFileTracingExcludes: {
       '*': [
         'node_modules/@swc/core-linux-x64-gnu',
         'node_modules/@swc/core-linux-x64-musl',
         'node_modules/terser'
       ],
     },
   };
   ```

---

## 3. Conectividade Perfeita: Vercel + Supabase

### 3.1 O Grande Vilão: Connection Pool Exhaustion

O modelo serverless e bancos relacionais tradicionais têm um conflito fundamental:
- **Serverless**: Cria dezenas ou centenas de instâncias efêmeras simultaneamente sob pico de tráfego.
- **Postgres**: Cada conexão consome memória RAM no servidor de banco de dados. O Supabase gratuito/básico suporta aproximadamente **60 a 90 conexões diretas**.

Se 70 instâncias de Serverless Functions acordarem na Vercel e cada uma abrir uma conexão direta via PostgreSQL, o banco trava e devolve:
```text
FATAL: remaining connection slots are reserved for non-replication superuser connections
# ou
Error: sorry, too many clients already
```

---

### 3.2 REST API vs Conexão Direta Postgres

O Supabase oferece duas formas principais de acesso:

```mermaid
flowchart TD
    Vercel[Vercel Serverless Function]
    
    subgraph Modo Recomendado (REST / HTTPS)
        Vercel -->|HTTPS Stateless Request| PostgREST[Supabase PostgREST API]
        PostgREST -->|Pool Interno Gerenciado| DB1[(PostgreSQL)]
    end
    
    subgraph Modo ORM (Prisma / Drizzle)
        Vercel -->|TCP Porta 6543| Supavisor[Supavisor Pooler Transaction Mode]
        Supavisor -->|Conexões Recicladas| DB2[(PostgreSQL)]
    end
```

1. **Supabase JS Client (`@supabase/supabase-js`) via PostgREST (Recomendado para 90% dos casos)**:
   - Funciona sobre **HTTPS**.
   - **É 100% Stateless**: ao final do `supabase.from('...').select()`, a requisição HTTP é fechada. **Nenhuma conexão TCP com o Postgres é deixada pendurada.**
   - Perfeito para serverless!

2. **Conexões TCP Diretas (Prisma, Drizzle, `pg`, TypeORM)**:
   - Exige cuidados rigorosos com pooling (leia abaixo).

---

### 3.3 Configurando o Supavisor / Pooler (Transaction Mode)

Se você utiliza **Prisma**, **Drizzle** ou driver SQL direto em suas Serverless Functions:

1. **NUNCA use a Direct Connection (Porta 5432)** em produção na Vercel:
   - `postgresql://postgres:[SENHA]@db.[REF].supabase.co:5432/postgres` ❌ (Trava o banco em picos).
   - A porta 5432 direta deve ser usada **apenas** na sua máquina local para rodar migrações (`prisma migrate dev` ou `supabase db push`).

2. **SEMPRE use a Pooler Connection (Porta 6543 - Transaction Mode)** na Vercel:
   - Obtenha no Dashboard do Supabase: **Project Settings > Database > Connection String > Transaction Mode**.
   - Formato:
     ```text
     DATABASE_URL="postgresql://postgres.[REF]:[SENHA]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=1"
     ```

#### Parâmetros Vitais para Prisma/Drizzle em Serverless:
- `?pgbouncer=true`: Informa ao Prisma para não usar *Prepared Statements* (incompatíveis com Transaction Pooling).
- `connection_limit=1`: Garante que cada Lambda abra no máximo **1 conexão** com o pooler.

---

### 3.4 Instanciação Correta do Supabase Client

#### Regra 1: Instanciar fora do Handler (Aproveitar Warm Starts)
Quando uma Serverless Function atende múltiplas requisições sequenciais, o runtime Node.js é reaproveitado (*warm start*). Instancie o client no escopo global do módulo:

```typescript
// lib/supabase-admin.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL!;
const supabaseServiceRole = process.env.SUPABASE_SERVICE_ROLE_KEY!;

// Criado UMA VEZ no escopo do módulo, reutilizado entre invocações
export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceRole, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
  },
  global: {
    fetch: fetch, // Usa o fetch nativo com keep-alive HTTP
  },
});
```

#### Regra 2: Para Aplicações com Sessão de Usuário (Next.js SSR)
Utilize o pacote oficial `@supabase/ssr` para sincronizar cookies com segurança:

```typescript
// lib/supabase-server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClientServer() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Chamado a partir de Server Component onde cookies são somente leitura
          }
        },
      },
    }
  );
}
```

---

### 3.5 Separação Rígida de Chaves e Segurança (RLS)

Nunca confunda as chaves:

| Variável | Onde Usar | Pode ir para o Navegador? | Ignora RLS? |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_SUPABASE_URL` | Cliente e Servidor | **SIM** (Pública) | Não |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Cliente e Servidor | **SIM** (Pública) | **NÃO** (Respeita RLS estritamente) |
| `SUPABASE_SERVICE_ROLE_KEY` | **Apenas Serverless Backend** | 🔴 **JAMAIS** | ⚠️ **SIM** (Acesso total de administrador) |

> ⚠️ **ATENÇÃO CRÍTICA:** Se você prefixar `SUPABASE_SERVICE_ROLE_KEY` com `NEXT_PUBLIC_`, ela será compilada no JavaScript do navegador e qualquer usuário poderá ler, modificar ou deletar todo o seu banco de dados.

---

## 4. Dicas Gerais de Infraestrutura e Performance

### 4.1 Evitando Limites de Otimização de Imagens

O componente `<Image />` do Next.js na Vercel utiliza uma Serverless Function interna para converter e redimensionar imagens sob demanda.
- No plano Hobby, você tem direito a **1.000 Source Images otimizadas por mês**. Se ultrapassar, a Vercel cobra ou bloqueia.

#### Solução: Usar a CDN do Supabase Storage
O Supabase Storage possui redimensionamento e conversão de imagem integrados na própria CDN:
```typescript
// Pede diretamente em formato WebP redimensionado ao Supabase
const urlOtimizada = `${supabaseUrl}/storage/v1/render/image/public/produtos/${fotoPath}?width=600&height=600&format=origin&quality=80`;
```

No `next.config.js`, caso queira desabilitar a otimização cara da Vercel e confiar na CDN de origem:
```javascript
// next.config.js
module.exports = {
  images: {
    unoptimized: true, // Não consome a cota de 1000 imagens da Vercel
  },
};
```

---

### 4.2 On-Demand Revalidation via Webhook do Supabase

Em vez de reconstruir o site ou usar SSR lento, combine **ISR** com **Webhooks**:

1. Crie uma rota API na Vercel:
```typescript
// app/api/revalidate/route.ts
import { revalidatePath } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const secret = req.headers.get('x-webhook-secret');
  if (secret !== process.env.REVALIDATION_SECRET) {
    return NextResponse.json({ message: 'Não autorizado' }, { status: 401 });
  }

  const payload = await req.json();
  const produtoId = payload.record?.id;

  if (produtoId) {
    revalidatePath(`/produtos/${produtoId}`);
  }
  revalidatePath('/catalogo');

  return NextResponse.json({ revalidated: true, now: Date.now() });
}
```

2. No painel do Supabase (**Database > Webhooks**), adicione um webhook na tabela `produtos` (para `INSERT`, `UPDATE`, `DELETE`) apontando para `https://seu-site.vercel.app/api/revalidate` enviando o header `x-webhook-secret`.

> **Resultado:** O site fica instantâneo como um arquivo estático e se atualiza sozinho em tempo real sempre que o estoque ou preço mudar!

---

### 4.3 Headers de Cache e `vercel.json`

Configure regras globais de cabeçalho no arquivo `vercel.json` na raiz do projeto para poupar tráfego e requisições repetidas:

```json
{
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    },
    {
      "source": "/api/produtos",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, s-maxage=60, stale-while-revalidate=300"
        }
      ]
    }
  ]
}
```

- `s-maxage=60`: O Edge CDN da Vercel guarda a resposta da API por 60 segundos antes de tocar no servidor.
- `stale-while-revalidate=300`: Se a resposta expirar, serve a versão antiga instantaneamente enquanto busca a nova em background.

---

## 5. Checklist Pré-Deploy

Antes de executar `git push` para publicar na Vercel, revise este checklist:

- [ ] **Contagem de Funções:** As rotas de API foram consolidadas (ex: via `[[...route]]` ou Hono) para não estourar o limite de 12 funções do plano Hobby?
- [ ] **Páginas Estáticas:** Páginas públicas estão usando SSG (`generateStaticParams`) ou ISR (`revalidate`) em vez de SSR puro a cada clique?
- [ ] **Conexão com Banco:**
  - Se usa Prisma/Drizzle: está apontando para o **Supavisor (porta 6543 / Transaction Mode)** com `?pgbouncer=true` e `connection_limit=1`?
  - A porta direta 5432 **NÃO** está configurada nas variáveis de ambiente da Vercel?
- [ ] **Segurança de Variáveis de Ambiente:**
  - `SUPABASE_SERVICE_ROLE_KEY` está sem o prefixo `NEXT_PUBLIC_`?
  - O RLS (*Row Level Security*) está ativo em **todas** as tabelas acessíveis pela chave anônima?
- [ ] **Timeouts:** Nenhuma rota de API realiza operações síncronas que demorem mais de 10 segundos (limite do Hobby). Processamentos longos foram migrados para filas ou Edge Functions com streaming?
- [ ] **Imagens:** O uso do `<Image />` não vai estourar a cota de 1.000 imagens ou está configurado para buscar versões otimizadas direto do Supabase Storage?

---

*Documento gerado como referência técnica de engenharia para projetos Vercel + Supabase.*
