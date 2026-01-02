@echo off
REM ============================================================
REM Script de Atualizacao do Banco de Dados - Certificado A3
REM Data: 18/12/2024
REM Descricao: Adiciona suporte para certificados A3 (tokens)
REM ============================================================

echo.
echo ============================================================
echo ATUALIZACAO DO BANCO DE DADOS - SUPORTE CERTIFICADO A3
echo ============================================================
echo.

REM Definir variaveis do banco de dados
REM IMPORTANTE: Ajuste estas variaveis conforme sua configuracao
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=nfesjt
set DB_USER=postgres
set DB_PASSWORD=sua_senha_aqui

echo Configuracao do Banco de Dados:
echo   Host: %DB_HOST%
echo   Porta: %DB_PORT%
echo   Database: %DB_NAME%
echo   Usuario: %DB_USER%
echo.

REM Verificar se o psql existe
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] PostgreSQL cliente (psql) nao encontrado!
    echo Por favor, instale o PostgreSQL ou adicione ao PATH
    echo Download: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
)

echo [INFO] PostgreSQL cliente encontrado.
echo.

REM Criar backup antes da migracao
echo ============================================================
echo CRIANDO BACKUP DO BANCO DE DADOS
echo ============================================================
echo.

set BACKUP_DIR=%~dp0backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

set BACKUP_FILE=%BACKUP_DIR%\backup_pre_a3_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
set BACKUP_FILE=%BACKUP_FILE: =0%

echo Criando backup em: %BACKUP_FILE%
echo.

set PGPASSWORD=%DB_PASSWORD%
pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -F p -f "%BACKUP_FILE%"

if %errorlevel% neq 0 (
    echo [ERRO] Falha ao criar backup!
    echo Abortando atualizacao por seguranca.
    pause
    exit /b 1
)

echo [OK] Backup criado com sucesso!
echo.

REM Executar migracao
echo ============================================================
echo EXECUTANDO MIGRACAO DO BANCO DE DADOS
echo ============================================================
echo.

set MIGRATION_FILE=%~dp0..\database\migrations\add_tipo_certificado.sql

if not exist "%MIGRATION_FILE%" (
    echo [ERRO] Arquivo de migracao nao encontrado!
    echo Procurado em: %MIGRATION_FILE%
    echo.
    echo Certifique-se de que o arquivo existe no caminho correto.
    pause
    exit /b 1
)

echo Aplicando migracao: %MIGRATION_FILE%
echo.

psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f "%MIGRATION_FILE%"

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao executar migracao!
    echo.
    echo O backup foi salvo em: %BACKUP_FILE%
    echo Voce pode restaura-lo com:
    echo   psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f "%BACKUP_FILE%"
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Migracao aplicada com sucesso!
echo.

REM Verificar se as colunas foram criadas
echo ============================================================
echo VERIFICANDO ESTRUTURA DO BANCO
echo ============================================================
echo.

echo Verificando colunas adicionadas...
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'certificados_digitais' AND column_name IN ('tipo_certificado', 'token_slot_id', 'token_label', 'pkcs11_library') ORDER BY column_name;"

if %errorlevel% neq 0 (
    echo [AVISO] Nao foi possivel verificar as colunas
) else (
    echo.
    echo [OK] Colunas verificadas!
)

echo.
echo ============================================================
echo ATUALIZACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo Proximos passos:
echo   1. Instalar PyKCS11: pip install PyKCS11
echo   2. Instalar drivers dos tokens (SafeNet, Certisign, etc)
echo   3. Reiniciar o servico da API
echo.
echo Backup salvo em: %BACKUP_FILE%
echo.
echo Documentacao: docs\SUPORTE_CERTIFICADOS_A3.md
echo.

pause
