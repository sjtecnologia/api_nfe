#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para remover emojis de arquivos Python para compatibilidade com Windows
"""

import re

def remove_emojis_from_file(filepath):
    """Remove emojis de um arquivo Python"""
    
    # Mapeamento de emojis para texto
    emoji_map = {
        '[OK]': 'OK:',
        '[!]': 'AVISO:',
        '[X]': 'ERRO:',
        '[?]': 'IMPORTANTE:',
        '[LOG]': 'NOTA:',
        '[START]': '',
        '[SAVE]': '',
        '[?]️': '',
        '[?]': '',
        '[?]': '',
        '⚡': '',
    }
    
    try:
        # Ler arquivo
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fazer backup
        backup_path = filepath + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Backup criado: {backup_path}")
        
        # Substituir emojis
        original_content = content
        for emoji, replacement in emoji_map.items():
            content = content.replace(emoji, replacement)
        
        # Remover qualquer emoji restante (caracteres Unicode > U+1F600)
        content = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]', '', content)
        
        if content != original_content:
            # Salvar arquivo modificado
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Arquivo modificado: {filepath}")
            print(f"  Emojis removidos com sucesso!")
            return True
        else:
            print(f"- Nenhum emoji encontrado em: {filepath}")
            return False
            
    except Exception as e:
        print(f"✗ Erro ao processar {filepath}: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    # Arquivos para processar
    files_to_clean = [
        'services/nfe_service.py',
        'app.py',
        'routes/nfe_routes.py',
    ]
    
    print("=" * 60)
    print("Removendo emojis para compatibilidade com Windows")
    print("=" * 60)
    
    for filepath in files_to_clean:
        print(f"\nProcessando: {filepath}")
        remove_emojis_from_file(filepath)
    
    print("\n" + "=" * 60)
    print("Concluído!")
    print("=" * 60)
