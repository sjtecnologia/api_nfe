#!/bin/bash
# Upload rápido do nfe_service.py para AWS

echo "📤 Enviando nfe_service.py para servidor AWS..."

# Copia o arquivo
scp services/nfe_service.py ubuntu@3.87.73.106:/home/ubuntu/api_nfe/services/

# Reinicia o serviço
ssh ubuntu@3.87.73.106 "sudo systemctl restart api-nfe-principal"

echo "✅ Arquivo enviado e serviço reiniciado!"
