# Estrutura do Projeto API NFe

## Arquivos Principais (Raiz)
- `app.py` - Aplicação principal Flask
- `run_app_utf8.py` - Script para executar a aplicação com encoding UTF-8
- `requirements.txt` - Dependências Python
- `Procfile` - Configuração para deploy (Heroku/similar)
- `pyrightconfig.json` - Configuração do Pylance/Pyright

## Diretórios Principais

### `/auth/` - Autenticação e Permissões
- Sistema de login e controle de permissões

### `/config/` - Configurações
- Configurações da aplicação (settings, CEP, etc)

### `/database/` - Banco de Dados
- Modelos e conexões com PostgreSQL

### `/routes/` - Rotas da Aplicação
- `admin_routes.py` - Rotas administrativas (clientes, produtos, certificados, etc)
- `nfe_routes.py` - Rotas de NFe (emissão, consulta, DANFE, etc)

### `/services/` - Serviços
- Lógica de negócio e integrações

### `/templates/` - Templates Jinja2
- Interface web da aplicação

### `/static/` - Arquivos Estáticos
- CSS, JavaScript, imagens, logos

### `/ai_ncm/` - Sistema de IA para NCM
- Módulos de IA para sugestão de NCM

### `/ia_service/` - Serviço de IA
- APIs e serviços de inteligência artificial

### `/models/` - Modelos de Dados
- Classes e estruturas de dados

### `/utils/` - Utilitários
- Funções auxiliares e helpers

## Diretórios Organizados

### `/docs/` - Documentação
- `/analises/` - Análises técnicas e relatórios
- `/guias/` - Guias de uso e deployment
- `/checklists/` - Checklists de desenvolvimento
- `/correcoes/` - Documentação de correções aplicadas
- `/manuais/` - Manuais de usuário e sistema
- Demais documentos de projeto (implantação, fases, etc)

### `/scripts/` - Scripts Auxiliares
- `/database/` - Scripts SQL, backup e restore
- `/migrations/` - Scripts de migração de dados
- `/testes/` - Scripts de teste e verificação
- `/utilitarios/` - Scripts utilitários diversos
- Scripts shell (.sh) para automação

### `/datasets/` - Conjuntos de Dados
- Datasets de treinamento
- Arquivos JSON de dados (NCM, Lei 214, etc)
- CSVs de importação
- Notebooks Jupyter

### `/examples/` - Exemplos
- Exemplos de uso e integração
- Scripts de demonstração

### `/logs/` - Logs
- Arquivos de log da aplicação (.log)
- Arquivos PID de processos

### `/backups/` - Backups
- Backups de dados

### `/deployment/` - Deployment
- Arquivos de configuração para deploy
- Services e configurações de servidor

### `/comunicados/` - Comunicados
- Comunicados para clientes

### `/migrations/` - Migrações Flask
- Migrações de banco de dados (Alembic/Flask-Migrate)

### `/tests/` - Testes Automatizados
- Testes unitários e de integração

## Estrutura Criada
Organização realizada em 3 de dezembro de 2025 para melhor manutenibilidade do projeto.
