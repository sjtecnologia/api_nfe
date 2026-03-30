#!/usr/bin/env python3
"""
Script para corrigir status da NFe 3 que foi autorizada pela SEFAZ 
mas gravada incorretamente como REJEITADA devido a bug no sefaz_service.py
"""

import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Configuração do banco
DB_HOST = "nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "sjtnfe"
DB_USER = "postgres"
DB_PASSWORD = "gMGM!#)NW$nH1w(wrVIdcmn5"

# Dados da NFe autorizada pela SEFAZ
NFE_NUMERO = 3
NFE_SERIE = 1
CLIENTE_ID = 29
CHAVE_ACESSO = "35260257308098000166550010000000031802393378"
PROTOCOLO = "135260574058064"
DATA_AUTORIZACAO = "2026-02-12 14:28:05"
MENSAGEM = "Autorizado o uso da NF-e"

def main():
    print("=" * 80)
    print("CORREÇÃO DE STATUS DA NFE 3 - AUTORIZADA PELA SEFAZ")
    print("=" * 80)
    
    # Criar conexão
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)
    
    with engine.connect() as conn:
        # 1. Verificar estado atual
        print("\n1️⃣ VERIFICANDO ESTADO ATUAL...")
        query_select = text("""
            SELECT nfe_emitida_id, numero, serie, status, chave_acesso, 
                   protocolo_sefaz, data_autorizacao, mensagem_sefaz,
                   valor_total, destinatario_razao_social
            FROM nfe_emitidas
            WHERE numero = :numero 
              AND serie = :serie 
              AND cliente_id = :cliente_id
        """)
        
        result = conn.execute(query_select, {
            'numero': NFE_NUMERO,
            'serie': NFE_SERIE,
            'cliente_id': CLIENTE_ID
        })
        
        nfe_atual = result.fetchone()
        
        if not nfe_atual:
            print(f"❌ NFe não encontrada: Número {NFE_NUMERO}, Série {NFE_SERIE}, Cliente {CLIENTE_ID}")
            return
        
        print(f"\n📋 NFe encontrada:")
        print(f"   ID: {nfe_atual[0]}")
        print(f"   Número: {nfe_atual[1]}")
        print(f"   Série: {nfe_atual[2]}")
        print(f"   Status ATUAL: {nfe_atual[3]} ⚠️")
        print(f"   Chave Atual: {nfe_atual[4] or 'NULL'}")
        print(f"   Protocolo Atual: {nfe_atual[5] or 'NULL'}")
        print(f"   Data Autorização Atual: {nfe_atual[6] or 'NULL'}")
        print(f"   Mensagem Atual: {nfe_atual[7] or 'NULL'}")
        print(f"   Valor Total: R$ {nfe_atual[8]}")
        print(f"   Destinatário: {nfe_atual[9]}")
        
        # 2. Atualizar para status correto
        print(f"\n2️⃣ ATUALIZANDO PARA STATUS CORRETO...")
        query_update = text("""
            UPDATE nfe_emitidas 
            SET status = 'AUTORIZADA',
                chave_acesso = :chave_acesso,
                protocolo_sefaz = :protocolo,
                data_autorizacao = :data_autorizacao,
                mensagem_sefaz = :mensagem
            WHERE nfe_emitida_id = :nfe_id
        """)
        
        conn.execute(query_update, {
            'nfe_id': nfe_atual[0],
            'chave_acesso': CHAVE_ACESSO,
            'protocolo': PROTOCOLO,
            'data_autorizacao': DATA_AUTORIZACAO,
            'mensagem': MENSAGEM
        })
        
        conn.commit()
        print("✅ UPDATE executado com sucesso!")
        
        # 3. Verificar resultado
        print("\n3️⃣ VERIFICANDO RESULTADO...")
        result_after = conn.execute(query_select, {
            'numero': NFE_NUMERO,
            'serie': NFE_SERIE,
            'cliente_id': CLIENTE_ID
        })
        
        nfe_atualizada = result_after.fetchone()
        
        print(f"\n✅ NFe atualizada com sucesso:")
        print(f"   ID: {nfe_atualizada[0]}")
        print(f"   Status: {nfe_atualizada[3]} ✅")
        print(f"   Chave: {nfe_atualizada[4]}")
        print(f"   Protocolo: {nfe_atualizada[5]}")
        print(f"   Data Autorização: {nfe_atualizada[6]}")
        print(f"   Mensagem: {nfe_atualizada[7]}")
        
        print("\n" + "=" * 80)
        print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print(f"\n📋 DADOS DA NFE AUTORIZADA:")
        print(f"   Chave de Acesso: {CHAVE_ACESSO}")
        print(f"   Protocolo SEFAZ: {PROTOCOLO}")
        print(f"   Status: AUTORIZADA")
        print(f"   Data/Hora: {DATA_AUTORIZACAO}")
        print("\n💡 A NFe agora está corretamente registrada como AUTORIZADA no sistema!")

if __name__ == '__main__':
    main()
