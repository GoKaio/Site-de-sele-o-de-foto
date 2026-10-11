"""
Módulo de Conectividade e Storage do Supabase - Casa da Foto Studio
Implementa padrões resilientes recomendados em GUIA_VERCEL_SERVERLESS_E_SUPABASE.md:
- Instanciação fora do handler para reaproveitamento em warm starts (Seção 3.4)
- Upload e CDN do Supabase Storage para evitar cotas de imagem da Vercel (Seção 4.1)
- Separação rígida de chaves (Seção 3.5)
"""

import os
import mimetypes
import requests

# ── 1. CONFIGURAÇÕES E CHAVES DO SUPABASE ─────────────────────────────────────
# URL pública do projeto Supabase (ex: https://xyzcompany.supabase.co)
SUPABASE_URL = os.environ.get('SUPABASE_URL') or os.environ.get('NEXT_PUBLIC_SUPABASE_URL', '')

# Chave anônima pública (usada para operações públicas com RLS)
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY') or os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY', '')

# Chave de serviço (EXCLUSIVA de backend serverless, NUNCA expor ao cliente!)
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

# Nome do bucket de uploads no Supabase Storage
STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'casadafoto-uploads')

def is_supabase_configured() -> bool:
    """Retorna True se as credenciais do Supabase estiverem configuradas."""
    return bool(SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY))

def get_auth_header() -> dict:
    """Retorna os headers de autorização para chamadas REST do Supabase."""
    token = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
    return {
        'apikey': token,
        'Authorization': f'Bearer {token}'
    }

# ── 2. SUPABASE STORAGE (UPLOADS VIA CDN GLOBAL) ──────────────────────────────
def upload_para_supabase_storage(file_bytes: bytes, filename: str, content_type: str = None) -> str:
    """
    Envia arquivo binário diretamente para o Supabase Storage.
    Retorna a URL pública da CDN do Supabase Storage se configurado, ou None em caso de falha/ausência de config.
    """
    if not is_supabase_configured():
        return None

    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = 'image/jpeg'

    # Endpoint do Supabase Storage API para upload de objeto
    # POST /storage/v1/object/<bucket>/<path>
    url_upload = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{STORAGE_BUCKET}/{filename}"

    headers = get_auth_header()
    headers['Content-Type'] = content_type
    headers['x-upsert'] = 'true'

    try:
        res = requests.post(url_upload, headers=headers, data=file_bytes, timeout=10)
        if res.status_code in (200, 201):
            # Retorna URL pública da CDN do Supabase
            url_publica = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"
            return url_publica
        else:
            print(f"[Supabase Storage] Erro {res.status_code}: {res.text}")
            return None
    except Exception as e:
        print(f"[Supabase Storage] Exceção ao enviar arquivo: {e}")
        return None
