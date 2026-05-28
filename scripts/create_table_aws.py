#!/usr/bin/env python3
import os
import sys
os.chdir('/home/ubuntu/api_nfe')
sys.path.insert(0, '/home/ubuntu/api_nfe')

from dotenv import load_dotenv
load_dotenv()
import psycopg2

db_config = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

conn = psycopg2.connect(**db_config)
cur = conn.cursor()

# Criar tabela
sql = '''
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
'''

cur.execute(sql)
conn.commit()
print('✅ Tabela password_reset_tokens criada com sucesso!')

# Verificar se existe
cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'password_reset_tokens')")
exists = cur.fetchone()[0]
print(f'✅ Tabela existe no banco: {exists}')

cur.close()
conn.close()
