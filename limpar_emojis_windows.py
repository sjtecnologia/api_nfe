#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para limpar TODOS os emojis dos arquivos Python no Windows
Execute no Windows: python limpar_emojis_windows.py
"""

import os
import glob
import shutil
from datetime import datetime

# Mapeamento de emojis para texto ASCII
EMOJI_MAP = {
    '👤': '[USER]',
    '🔐': '[LOCK]',
    '🔑': '[KEY]',
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARN]',
    '⚠': '[WARN]',
    '📧': '[EMAIL]',
    '🆔': '[ID]',
    '🔍': '[SEARCH]',
    '📋': '[DATA]',
    '🎉': '[SUCCESS]',
    '🔄': '[PROCESS]',
    '💡': '[INFO]',
    '🚀': '[START]',
    '📊': '[STATS]',
    '🆕': '[NEW]',
    '📦': '[PACKAGE]',
    '🔢': '[NUM]',
    '📅': '[DATE]',
    '✓': '[OK]',
    '➕': '[ADD]',
    '⭐': '[*]',
    '🧹': '[CLEAN]',
}

def has_emoji(text):
    """Verifica se o texto contém emojis problemáticos"""
    for char in text:
        code = ord(char)
        # Faixas de Unicode para emojis
        if (0x2600 <= code <= 0x26FF or  # Miscellaneous Symbols
            0x2700 <= code <= 0x27BF or  # Dingbats
            0x1F000 <= code <= 0x1FFFF):  # Emojis
            return True
    return False

def replace_emojis(text):
    """Substitui emojis conhecidos por texto ASCII"""
    result = text
    for emoji, replacement in EMOJI_MAP.items():
        result = result.replace(emoji, replacement)
    return result

def clean_file(filepath):
    """Limpa emojis de um arquivo"""
    try:
        # Ler arquivo
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se tem emojis
        if not has_emoji(content):
            return False, "Já limpo"
        
        # Backup
        backup_path = filepath + '.emoji_backup'
        shutil.copy2(filepath, backup_path)
        
        # Substituir emojis conhecidos
        new_content = replace_emojis(content)
        
        # Remover quaisquer outros emojis restantes (substituir por ?)
        clean_content = []
        for char in new_content:
            code = ord(char)
            if (0x2600 <= code <= 0x26FF or 
                0x2700 <= code <= 0x27BF or 
                0x1F000 <= code <= 0x1FFFF):
                clean_content.append('[?]')
            else:
                clean_content.append(char)
        
        final_content = ''.join(clean_content)
        
        # Salvar
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        return True, "Limpo"
        
    except Exception as e:
        return False, f"Erro: {e}"

def main():
    print("="*70)
    print("LIMPEZA DE EMOJIS - Windows cp1252 Compatibility")
    print("="*70)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Diretórios para limpar
    patterns = [
        'routes/*.py',
        'services/*.py',
        'auth/*.py',
        'utils/*.py',
        'config/*.py',
    ]
    
    cleaned_files = []
    already_clean = []
    errors = []
    
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            if 'venv' in filepath or '__pycache__' in filepath:
                continue
            
            print(f"Verificando: {filepath}...", end=' ')
            success, message = clean_file(filepath)
            
            if success:
                cleaned_files.append(filepath)
                print(f"[LIMPO]")
            elif message == "Já limpo":
                already_clean.append(filepath)
                print(f"[OK]")
            else:
                errors.append((filepath, message))
                print(f"[ERRO: {message}]")
    
    # Resumo
    print()
    print("="*70)
    print("RESUMO DA LIMPEZA")
    print("="*70)
    print(f"Arquivos limpos:       {len(cleaned_files)}")
    print(f"Arquivos já limpos:    {len(already_clean)}")
    print(f"Erros:                 {len(errors)}")
    
    if cleaned_files:
        print(f"\nArquivos que foram limpos:")
        for f in cleaned_files:
            print(f"  - {f} (backup em {f}.emoji_backup)")
    
    if errors:
        print(f"\nErros encontrados:")
        for f, msg in errors:
            print(f"  - {f}: {msg}")
    
    print()
    print("="*70)
    print("LIMPEZA CONCLUÍDA!")
    print("="*70)
    print()
    print("PRÓXIMOS PASSOS:")
    print("1. Reinicie o serviço: nssm restart NFe_Backend_v2")
    print("2. Teste o login novamente")
    print()

if __name__ == '__main__':
    main()
