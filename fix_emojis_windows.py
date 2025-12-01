#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para remover emojis do código Python e substituir por texto ASCII
Necessário para compatibilidade com Windows (encoding cp1252)
"""

import os
import re

# Mapeamento de emojis para texto ASCII
EMOJI_MAP = {
    '✅': '[OK]',
    '❌': '[ERRO]',
    '⚠️': '[AVISO]',
    '🔄': '[PROC]',
    '⏳': '[AGUARDE]',
    '📊': '[STATS]',
    '📈': '[UP]',
    '📉': '[DOWN]',
    '🎯': '[FOCO]',
    '💡': '[INFO]',
    '🚀': '[INICIO]',
    '⭐': '[STAR]',
    '🔥': '[HOT]',
}

def fix_file(filepath):
    """Remove emojis de um arquivo Python"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Substituir cada emoji
        for emoji, replacement in EMOJI_MAP.items():
            content = content.replace(emoji, replacement)
        
        # Se houve mudanças, salvar
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
        
    except Exception as e:
        print(f"[ERRO] Erro ao processar {filepath}: {e}")
        return False

def main():
    """Processa todos os arquivos Python no diretório"""
    files_modified = 0
    
    # Listar arquivos Python a processar
    python_files = [
        'servico_sugestao_ia.py',
        'api_ia_unificada.py',
        'NCM_INTEGRATION_FINAL.py',
        'teste_busca_ncm.py',
        'teste_integracao_ia.py',
        'services/calculo_ibs_v2.py',
        'services/email_service.py',
    ]
    
    print("[INICIO] Iniciando remocao de emojis para compatibilidade Windows...")
    print(f"[INFO] {len(python_files)} arquivos serao processados\n")
    
    for filepath in python_files:
        if os.path.exists(filepath):
            if fix_file(filepath):
                print(f"[OK] {filepath}")
                files_modified += 1
            else:
                print(f"[INFO] {filepath} - sem emojis")
        else:
            print(f"[AVISO] {filepath} - nao encontrado")
    
    print(f"\n[CONCLUIDO] {files_modified} arquivos modificados")
    
    if files_modified > 0:
        print("\n[INFO] Execute os seguintes comandos para commitar:")
        print("git add .")
        print("git commit -m 'fix: Remover todos os emojis para compatibilidade Windows'")
        print("git push")

if __name__ == '__main__':
    main()
