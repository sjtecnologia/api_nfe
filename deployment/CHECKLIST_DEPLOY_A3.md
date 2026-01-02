# Checklist de Deploy - Certificado A3

Data: 18/12/2024

## 📋 Pré-Deploy

- [ ] Ler documentação completa em `docs/SUPORTE_CERTIFICADOS_A3.md`
- [ ] Verificar lista de arquivos em `deployment/ARQUIVOS_ATUALIZACAO_A3.txt`
- [ ] Fazer backup completo do banco de dados atual
- [ ] Fazer backup completo dos arquivos da aplicação
- [ ] Testar em ambiente de homologação primeiro

## 📁 1. Upload dos Arquivos

### Arquivos Novos (criar)

- [ ] `database/migrations/add_tipo_certificado.sql`
- [ ] `services/pkcs11_service.py`
- [ ] `routes/a3_routes.py`
- [ ] `templates/a3/select_certificate.html`
- [ ] `docs/SUPORTE_CERTIFICADOS_A3.md`

### Arquivos Modificados (substituir)

- [ ] `database/models.py`
- [ ] `services/certificate_service.py`
- [ ] `services/xml_signature_service.py`
- [ ] `templates/admin/certificados/list.html`
- [ ] `app.py`
- [ ] `requirements.txt`

### Scripts de Deploy (criar)

- [ ] `deployment/atualizar_banco_a3_windows.bat`
- [ ] `deployment/atualizar_banco_a3_linux.sh`
- [ ] `deployment/ARQUIVOS_ATUALIZACAO_A3.txt`
- [ ] `deployment/CHECKLIST_DEPLOY_A3.md` (este arquivo)

## 🔧 2. Configuração do Ambiente

### Windows

- [ ] Verificar se PostgreSQL cliente está instalado
- [ ] Abrir `deployment/atualizar_banco_a3_windows.bat` em um editor
- [ ] Ajustar variáveis do banco de dados:
  ```batch
  set DB_HOST=localhost
  set DB_PORT=5432
  set DB_NAME=nfesjt
  set DB_USER=postgres
  set DB_PASSWORD=sua_senha_aqui
  ```
- [ ] Salvar o arquivo

### Linux/macOS

- [ ] Verificar se PostgreSQL cliente está instalado
- [ ] Tornar script executável: `chmod +x deployment/atualizar_banco_a3_linux.sh`
- [ ] Configurar variáveis de ambiente ou editar o script:
  ```bash
  export DB_HOST=localhost
  export DB_PORT=5432
  export DB_NAME=nfesjt
  export DB_USER=postgres
  ```

## 🗄️ 3. Atualização do Banco de Dados

### Windows

- [ ] Abrir CMD como Administrador
- [ ] Navegar até o diretório: `cd C:\caminho\api_nfe\deployment`
- [ ] Executar: `atualizar_banco_a3_windows.bat`
- [ ] Verificar mensagem de sucesso
- [ ] Conferir se backup foi criado em `deployment/backups/`

### Linux/macOS

- [ ] Abrir terminal
- [ ] Navegar até o diretório: `cd /caminho/api_nfe/deployment`
- [ ] Executar: `./atualizar_banco_a3_linux.sh`
- [ ] Verificar mensagem de sucesso
- [ ] Conferir se backup foi criado em `deployment/backups/`

### Verificação Manual (opcional)

```sql
-- Conectar ao banco e verificar:
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'certificados_digitais' 
  AND column_name IN ('tipo_certificado', 'token_slot_id', 'token_label', 'pkcs11_library');
```

## 📦 4. Instalação de Dependências

### PyKCS11

#### Windows
```cmd
pip install PyKCS11
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install swig libpcsclite-dev pcscd
pip install PyKCS11
sudo systemctl start pcscd
sudo systemctl enable pcscd
```

#### Linux (CentOS/RHEL)
```bash
sudo yum install swig pcsc-lite pcsc-lite-libs pcsc-lite-devel
pip install PyKCS11
sudo systemctl start pcscd
sudo systemctl enable pcscd
```

#### macOS
```bash
brew install swig pcsc-lite
pip install PyKCS11
```

- [ ] PyKCS11 instalado com sucesso
- [ ] Testar importação: `python -c "import PyKCS11; print('OK')"`

### Drivers dos Tokens

#### SafeNet eToken
- [ ] Baixar de: https://support.globalsign.com/ca-certificates/local-registration-authorities-lras/safenet-drivers
- [ ] Instalar driver
- [ ] Reiniciar sistema (se necessário)

#### Certisign
- [ ] Baixar de: https://www.certisign.com.br/downloads
- [ ] Instalar driver
- [ ] Reiniciar sistema (se necessário)

#### Gemalto/Thales
- [ ] Baixar de: https://www.thalesgroup.com/en/markets/digital-identity-and-security/government/customer-services/software-downloads
- [ ] Instalar driver
- [ ] Reiniciar sistema (se necessário)

#### Watchdata
- [ ] Baixar do site do fabricante
- [ ] Instalar driver
- [ ] Reiniciar sistema (se necessário)

## 🔄 5. Reiniciar Serviços

### Windows (Serviço)
```cmd
net stop api_nfe_principal
net start api_nfe_principal
```

- [ ] Serviço parado com sucesso
- [ ] Serviço iniciado com sucesso
- [ ] Verificar logs: `logs/app.log`

### Linux (Systemd)
```bash
sudo systemctl restart api_nfe_principal
sudo systemctl status api_nfe_principal
```

- [ ] Serviço reiniciado com sucesso
- [ ] Status mostra "active (running)"
- [ ] Verificar logs: `sudo journalctl -u api_nfe_principal -f`

### Manual
```bash
# Parar processo existente
pkill -f 'python.*app.py'

# Iniciar novo processo
cd /caminho/api_nfe
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate.bat  # Windows
python app.py
```

- [ ] Processo parado
- [ ] Processo iniciado
- [ ] API respondendo na porta configurada

## ✅ 6. Testes de Funcionamento

### Teste 1: Verificar Interface

- [ ] Acessar: `http://servidor/admin/certificados?cliente_id=1`
- [ ] Verificar se aparecem **dois botões**:
  - 🔵 "Certificado A1" (azul)
  - 🟢 "Certificado A3" (verde)
- [ ] Verificar se tabela tem coluna "Tipo"

### Teste 2: Acessar Wizard A3

- [ ] Clicar no botão "Certificado A3"
- [ ] Verificar se abre página de seleção
- [ ] Verificar se aparecem 3 passos:
  1. Detectar Tokens
  2. Inserir PIN
  3. Selecionar Certificado

### Teste 3: Detecção de Tokens (com token conectado)

- [ ] Conectar token USB
- [ ] Clicar em "Detectar Tokens Conectados"
- [ ] Verificar se token é detectado
- [ ] Verificar informações: fabricante, modelo, serial

### Teste 4: Listar Certificados (com token conectado)

- [ ] Selecionar token detectado
- [ ] Inserir PIN do token
- [ ] Clicar em "Listar Certificados"
- [ ] Verificar se certificados são listados
- [ ] Verificar informações: nome, validade, status

### Teste 5: Registrar Certificado A3

- [ ] Selecionar um certificado válido
- [ ] Clicar em "Registrar Certificado"
- [ ] Verificar mensagem de sucesso
- [ ] Voltar para lista de certificados
- [ ] Verificar se certificado aparece com badge verde "A3"

### Teste 6: Assinar XML com A3

- [ ] Emitir uma NFe de teste usando cliente com certificado A3
- [ ] Verificar se XML é assinado com sucesso
- [ ] Validar assinatura no portal da SEFAZ

### Teste 7: Certificados A1 Continuam Funcionando

- [ ] Acessar lista de certificados
- [ ] Verificar se certificados A1 existentes aparecem com badge azul "A1"
- [ ] Testar upload de novo certificado A1
- [ ] Testar assinatura com certificado A1

## 🐛 7. Troubleshooting

### Erro: "PyKCS11 não encontrado"

- [ ] Verificar instalação: `pip list | grep PyKCS11`
- [ ] Reinstalar: `pip install --force-reinstall PyKCS11`

### Erro: "Nenhuma biblioteca PKCS#11 encontrada"

- [ ] Verificar se driver do token está instalado
- [ ] Windows: Procurar em `C:\Windows\System32\` por arquivos `.dll`
- [ ] Linux: Procurar em `/usr/lib/` por arquivos `.so`
- [ ] macOS: Procurar em `/Library/` e `/usr/local/lib/`

### Erro: "Token não detectado"

- [ ] Verificar se token está conectado via USB
- [ ] Verificar se LED do token está aceso
- [ ] Windows: Verificar no Gerenciador de Dispositivos
- [ ] Linux: Executar `pcsc_scan` para testar comunicação
- [ ] Verificar se serviço pcscd está rodando (Linux)

### Erro: "PIN incorreto" / Token bloqueado

- [ ] Verificar PIN correto com proprietário do token
- [ ] Tokens geralmente bloqueiam após 3 tentativas incorretas
- [ ] Entrar em contato com Autoridade Certificadora para desbloqueio
- [ ] Procedimento de desbloqueio geralmente requer PUK

### Erro: Certificado não assina XML

- [ ] Verificar logs em `logs/app.log`
- [ ] Verificar se token está conectado durante assinatura
- [ ] Verificar se PIN está correto no banco de dados
- [ ] Testar assinatura manualmente via Python:
  ```python
  from services.pkcs11_service import get_pkcs11_service
  pkcs11 = get_pkcs11_service()
  tokens = pkcs11.list_tokens('caminho/biblioteca.so')
  print(tokens)
  ```

## 📊 8. Monitoramento Pós-Deploy

### Primeiras 24 horas

- [ ] Monitorar logs de erro
- [ ] Verificar performance da API
- [ ] Coletar feedback dos usuários
- [ ] Documentar problemas encontrados

### Primeira semana

- [ ] Analisar métricas de uso (A1 vs A3)
- [ ] Verificar taxa de sucesso de assinaturas
- [ ] Identificar tokens mais utilizados
- [ ] Ajustar documentação conforme necessário

## 📝 9. Documentação

- [ ] Atualizar documentação interna com peculiaridades do servidor
- [ ] Criar guia de uso para clientes
- [ ] Documentar procedimentos de suporte
- [ ] Registrar configurações específicas do ambiente

## 🎯 10. Rollback (se necessário)

### Se houver problemas críticos:

1. **Parar serviço**
   ```bash
   # Windows
   net stop api_nfe_principal
   
   # Linux
   sudo systemctl stop api_nfe_principal
   ```

2. **Restaurar backup do banco**
   ```bash
   # Windows
   psql -h localhost -U postgres -d nfesjt -f deployment\backups\backup_pre_a3_YYYYMMDD_HHMMSS.sql
   
   # Linux
   psql -h localhost -U postgres -d nfesjt -f deployment/backups/backup_pre_a3_YYYYMMDD_HHMMSS.sql
   ```

3. **Restaurar arquivos anteriores**
   - Substituir arquivos modificados pelas versões antigas

4. **Reiniciar serviço**
   ```bash
   # Windows
   net start api_nfe_principal
   
   # Linux
   sudo systemctl start api_nfe_principal
   ```

5. **Verificar funcionamento**
   - Testar funcionalidades básicas
   - Confirmar que certificados A1 funcionam

- [ ] Procedimento de rollback documentado
- [ ] Backups testados e acessíveis

---

## ✅ Conclusão

- [ ] Todos os testes passaram
- [ ] Documentação atualizada
- [ ] Equipe treinada
- [ ] Clientes notificados da nova funcionalidade
- [ ] Suporte preparado para atender dúvidas

**Data de conclusão do deploy:** ____/____/________

**Responsável:** _________________________________

**Observações:**
