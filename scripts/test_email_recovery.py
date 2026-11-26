#!/usr/bin/env python3
"""
Script para testar envio de email de recuperação de senha
"""
import os
import sys
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.email_sender import enviar_email_recuperacao_senha

def teste_email():
    """Testar envio de email de recuperação"""
    
    print("=" * 60)
    print("TESTE DE EMAIL DE RECUPERAÇÃO DE SENHA")
    print("=" * 60)
    print()
    
    # Verificar variáveis de ambiente
    print("📋 Verificando configurações:")
    print(f"   SMTP_SERVER: {os.getenv('SMTP_SERVER')}")
    print(f"   SMTP_PORT: {os.getenv('SMTP_PORT')}")
    print(f"   SMTP_USER: {os.getenv('SMTP_USER')}")
    print(f"   SMTP_PASSWORD definida: {'Sim' if os.getenv('SMTP_PASSWORD') else 'Não'}")
    print()
    
    # Pedir email de teste
    email_teste = input("Digite o email para teste (ou Enter para usar o do .env): ").strip()
    if not email_teste:
        email_teste = os.getenv('SMTP_USER')
    
    print()
    print(f"📧 Enviando email de teste para: {email_teste}")
    print()
    
    # URL de teste
    reset_url = "http://localhost:5000/auth/reset-password/TOKEN_DE_TESTE_123456"
    
    try:
        resultado = enviar_email_recuperacao_senha(
            destinatario=email_teste,
            usuario="Usuário Teste",
            reset_url=reset_url
        )
        
        print()
        print("=" * 60)
        if resultado and resultado.get('success'):
            print("✅ EMAIL ENVIADO COM SUCESSO!")
            print(f"   Mensagem: {resultado.get('message')}")
        else:
            print("❌ FALHA AO ENVIAR EMAIL")
            print(f"   Erro: {resultado.get('message') if resultado else 'Sem resposta'}")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERRO NA EXECUÇÃO:")
        print(f"   {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    teste_email()
