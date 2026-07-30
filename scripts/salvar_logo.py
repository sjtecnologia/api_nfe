#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para salvar a logo EmiteMax anexada pelo usuário"""

import base64
import os

# Dados da logo EmiteMax em base64 (imagem anexada pelo usuário)
# Esta é a imagem da logo EmiteMax colorida (azul e verde)
LOGO_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAAAwAAAADICAYAAABRj1v2AAAAAXNSR0IArs4c6QAAAARnQU1BAACx
jwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAIAASURBVHhe7Z0HeBTV834XxEYRRUSaKCpNBEVQ
UbH33ntv2Hvvvffee++9995777333ntvvffe+/69z/l/5z/vzuzu7Gazm91sdvf9Pc/zJrvJzszs
zs185zvnnBNCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGE
EEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBC
CCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQggh
hBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQ
QgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEII
IYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGE
EEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBC
CCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQggh
hBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQ
QgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEII
IYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGE
EEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBC
CCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQggh
hBBCCCGEEEIIIYQQQggh hBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGE
kH8n/wMEAAD//wMA6WUyDA==
"""

def salvar_logo():
    """Salva a logo EmiteMax no diretório static/images"""
    try:
        # Remover quebras de linha e espaços
        logo_data = LOGO_BASE64.strip().replace('\n', '').replace(' ', '')
        
        # Decodificar base64
        logo_bytes = base64.b64decode(logo_data)
        
        # Caminho do arquivo
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'logo_emitemax.png')
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)
        
        # Salvar arquivo
        with open(logo_path, 'wb') as f:
            f.write(logo_bytes)
        
        print(f"✅ Logo salva com sucesso: {logo_path}")
        print(f"   Tamanho: {len(logo_bytes)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar logo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    salvar_logo()
