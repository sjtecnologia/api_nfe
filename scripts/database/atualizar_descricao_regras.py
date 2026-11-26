#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para atualizar descrições vazias de regras tributárias
Gera descrições automáticas baseadas nas características da regra
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.connection import get_db
from sqlalchemy import text

def atualizar_descricoes_regras():
    """Atualiza descrições vazias de regras tributárias"""
    
    print("=" * 80)
    print("ATUALIZAÇÃO DE DESCRIÇÕES DE REGRAS TRIBUTÁRIAS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Buscar regras sem descrição
        result = db.execute(text("""
            SELECT 
                rt.regra_tributacao_id,
                rt.regime_tributario_id,
                rt.cfop_id,
                rt.ncm_id,
                rt.uf_origem,
                rt.uf_destino,
                rt.tipo_item,
                rt.descricao_regra,
                reg.nome as regime_nome,
                c.cfop as cfop_codigo,
                n.codigo as ncm_codigo,
                cl.razao_social as cliente_nome
            FROM regras_tributacao rt
            LEFT JOIN regimes_tributarios reg ON rt.regime_tributario_id = reg.regime_tributario_id
            LEFT JOIN cfops c ON rt.cfop_id = c.cfop_id
            LEFT JOIN ncms n ON rt.ncm_id = n.ncm_id
            LEFT JOIN clientes cl ON rt.cliente_id = cl.cliente_id
            WHERE rt.descricao_regra IS NULL OR rt.descricao_regra = ''
            ORDER BY rt.regra_tributacao_id
        """))
        
        regras = result.fetchall()
        
        if not regras:
            print("\n✅ Todas as regras já possuem descrição!")
            return
        
        print(f"\n📋 Encontradas {len(regras)} regras sem descrição\n")
        print("-" * 80)
        
        atualizadas = 0
        
        for regra in regras:
            regra_id = regra.regra_tributacao_id
            regime_nome = regra.regime_nome or "Tributário"
            
            # Montar descrição automática
            descricao_parts = []
            
            # Regime
            descricao_parts.append(regime_nome)
            
            # Cliente específico
            if regra.cliente_nome:
                descricao_parts.append(f"- {regra.cliente_nome[:30]}")
            
            # CFOP específico
            if regra.cfop_codigo:
                descricao_parts.append(f"- CFOP {regra.cfop_codigo}")
            
            # NCM específico
            if regra.ncm_codigo:
                descricao_parts.append(f"- NCM {regra.ncm_codigo}")
            
            # UF Origem/Destino
            if regra.uf_origem and regra.uf_destino:
                if regra.uf_origem == regra.uf_destino:
                    descricao_parts.append(f"- Dentro de {regra.uf_origem}")
                else:
                    descricao_parts.append(f"- {regra.uf_origem} → {regra.uf_destino}")
            elif regra.uf_origem:
                descricao_parts.append(f"- Origem {regra.uf_origem}")
            elif regra.uf_destino:
                descricao_parts.append(f"- Destino {regra.uf_destino}")
            
            # Tipo de item
            if regra.tipo_item:
                descricao_parts.append(f"- {regra.tipo_item}")
            
            # Se não tem nada específico, é uma regra geral
            if len(descricao_parts) == 1:
                descricao_parts.append("- Regra Geral")
            
            descricao = " ".join(descricao_parts)
            
            # Limitar tamanho
            if len(descricao) > 200:
                descricao = descricao[:197] + "..."
            
            # Atualizar no banco
            db.execute(text("""
                UPDATE regras_tributacao 
                SET descricao_regra = :descricao 
                WHERE regra_tributacao_id = :regra_id
            """), {"descricao": descricao, "regra_id": regra_id})
            
            print(f"✅ Regra #{regra_id}: {descricao}")
            atualizadas += 1
        
        db.commit()
        
        print("-" * 80)
        print(f"\n✅ {atualizadas} regras atualizadas com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    atualizar_descricoes_regras()
