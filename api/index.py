"""
Entrypoint Serverless Vercel - Casa da Foto Studio
Consolida todas as rotas da API em 1 ÚNICA Serverless Function (Técnica do API Gateway Único),
garantindo que o projeto nunca estoure o limite de 12 funções do plano Hobby da Vercel.
"""

import sys
import os

# Adiciona o diretório raiz do projeto ao path de busca do Python
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Importa a aplicação Bottle (WSGI compatível)
from server import app

# A Vercel detecta automaticamente a variável 'app' como uma aplicação WSGI padrão
handler = app
