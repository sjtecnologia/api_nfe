"""
Migration: Criar tabela nfce_emitidas
Data: 2025-11-19
Descrição: Tabela para armazenar NFC-e (Nota Fiscal de Consumidor Eletrônica - Modelo 65)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.connection import engine

def upgrade():
    """Criar tabela nfce_emitidas"""
    
    with engine.connect() as conn:
        # Criar tabela nfce_emitidas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS nfce_emitidas (
                nfce_id SERIAL PRIMARY KEY,
                cliente_id INTEGER NOT NULL REFERENCES clientes(cliente_id) ON DELETE CASCADE,
                
                -- Identificação da NFC-e
                numero INTEGER NOT NULL,
                serie INTEGER NOT NULL DEFAULT 1,
                chave_acesso VARCHAR(44) UNIQUE,
                modelo VARCHAR(2) DEFAULT '65',
                
                -- Dados estruturados
                json_nfce JSONB NOT NULL,  -- Dados completos da NFC-e
                xml_content TEXT,           -- XML gerado
                xml_assinado TEXT,          -- XML após assinatura digital
                
                -- QR Code para consulta pelo consumidor
                qrcode_url TEXT,            -- URL do QR Code
                qrcode_imagem TEXT,         -- Base64 da imagem do QR Code
                url_consulta TEXT,          -- URL de consulta no portal da SEFAZ
                
                -- Status e controle
                status VARCHAR(50) NOT NULL DEFAULT 'em_processamento',
                ambiente VARCHAR(20) NOT NULL DEFAULT 'homologacao',  -- homologacao ou producao
                
                -- Datas
                data_emissao TIMESTAMP NOT NULL DEFAULT NOW(),
                data_autorizacao TIMESTAMP,
                data_cancelamento TIMESTAMP,
                
                -- Retorno SEFAZ
                protocolo_autorizacao VARCHAR(50),
                cstat VARCHAR(10),           -- Código de status da SEFAZ
                motivo VARCHAR(500),         -- Mensagem de retorno
                digest_value TEXT,           -- Hash do XML para validação
                
                -- Contingência
                em_contingencia BOOLEAN DEFAULT FALSE,
                tipo_contingencia VARCHAR(20),  -- EPEC, offline, etc
                motivo_contingencia TEXT,
                
                -- Valores para consultas rápidas
                valor_total DECIMAL(15,2),
                valor_produtos DECIMAL(15,2),
                valor_desconto DECIMAL(15,2),
                cpf_cnpj_consumidor VARCHAR(14),  -- Opcional
                
                -- Cancelamento
                motivo_cancelamento TEXT,
                protocolo_cancelamento VARCHAR(50),
                
                -- Auditoria
                data_criacao TIMESTAMP NOT NULL DEFAULT NOW(),
                data_atualizacao TIMESTAMP DEFAULT NOW(),
                
                -- Constraints
                CONSTRAINT uk_nfce_numero_serie UNIQUE (cliente_id, numero, serie, ambiente)
            );
        """))
        
        # Índices para performance
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_nfce_cliente 
                ON nfce_emitidas(cliente_id);
            
            CREATE INDEX IF NOT EXISTS idx_nfce_chave 
                ON nfce_emitidas(chave_acesso);
            
            CREATE INDEX IF NOT EXISTS idx_nfce_status 
                ON nfce_emitidas(status);
            
            CREATE INDEX IF NOT EXISTS idx_nfce_data_emissao 
                ON nfce_emitidas(data_emissao DESC);
            
            CREATE INDEX IF NOT EXISTS idx_nfce_cpf_cnpj 
                ON nfce_emitidas(cpf_cnpj_consumidor);
            
            -- Índice GIN para busca no JSONB
            CREATE INDEX IF NOT EXISTS idx_nfce_json 
                ON nfce_emitidas USING GIN (json_nfce);
        """))
        
        # Comentários nas colunas
        conn.execute(text("""
            COMMENT ON TABLE nfce_emitidas IS 
                'NFC-e (Nota Fiscal de Consumidor Eletrônica) - Modelo 65';
            
            COMMENT ON COLUMN nfce_emitidas.json_nfce IS 
                'Dados completos da NFC-e em formato JSON';
            
            COMMENT ON COLUMN nfce_emitidas.qrcode_url IS 
                'URL do QR Code para consulta pelo consumidor';
            
            COMMENT ON COLUMN nfce_emitidas.status IS 
                'Status: em_processamento, autorizada, rejeitada, cancelada, contingencia';
            
            COMMENT ON COLUMN nfce_emitidas.ambiente IS 
                'Ambiente de emissão: homologacao ou producao';
        """))
        
        conn.commit()
        print("✅ Tabela nfce_emitidas criada com sucesso!")

def downgrade():
    """Remover tabela nfce_emitidas"""
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS nfce_emitidas CASCADE;"))
        conn.commit()
        print("✅ Tabela nfce_emitidas removida!")

if __name__ == "__main__":
    print("🔄 Executando migration: create_nfce_table")
    upgrade()
    print("✅ Migration concluída!")
