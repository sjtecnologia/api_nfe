@echo off
REM ============================================================================
REM SCRIPT DE ATUALIZAÇÃO DO BANCO DE DADOS - Windows Server
REM Sistema: EmiteMax v2.0 - Implementação CRT=3 (Lucro Real/Presumido)
REM Data: 11/12/2025
REM ============================================================================

echo.
echo ============================================================
echo   ATUALIZACAO BANCO DE DADOS - CRT=3
echo   EmiteMax v2.0
echo ============================================================
echo.

REM Configurações do PostgreSQL
set PGHOST=localhost
set PGPORT=5432
set PGDATABASE=sjtnfe
set PGUSER=postgres

REM Solicitar senha do PostgreSQL
set /p PGPASSWORD="Digite a senha do PostgreSQL: "

echo.
echo [INFO] Conectando ao banco de dados %PGDATABASE%...
echo.

REM Verificar se o arquivo SQL existe
if not exist "atualizacao_crt3.sql" (
    echo [ERRO] Arquivo atualizacao_crt3.sql nao encontrado!
    echo [INFO] Certifique-se de que o arquivo esta na mesma pasta deste script.
    pause
    exit /b 1
)

REM Fazer backup do banco ANTES da atualização
echo [INFO] Criando backup de segurança...
set BACKUP_FILE=backup_sjtnfe_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%.sql
set BACKUP_FILE=%BACKUP_FILE: =0%

"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U %PGUSER% -h %PGHOST% -p %PGPORT% %PGDATABASE% > %BACKUP_FILE% 2>nul

if errorlevel 1 (
    echo [AVISO] Nao foi possivel criar backup automatico.
    echo [INFO] Continuando mesmo assim...
) else (
    echo [OK] Backup criado: %BACKUP_FILE%
)

echo.
echo [INFO] Executando script de atualizacao...
echo.

REM Executar o script SQL
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d %PGDATABASE% -f atualizacao_crt3.sql

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao executar o script de atualizacao!
    echo [INFO] Verifique as mensagens de erro acima.
    echo [INFO] Se necessario, restaure o backup: %BACKUP_FILE%
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   ATUALIZACAO CONCLUIDA COM SUCESSO!
echo ============================================================
echo.
echo [OK] Banco de dados atualizado
echo [OK] Backup salvo em: %BACKUP_FILE%
echo.
echo PROXIMOS PASSOS:
echo 1. Atualizar arquivos do sistema (ver arquivo ARQUIVOS_PARA_ATUALIZAR.txt)
echo 2. Reiniciar o serviço EmiteMax
echo 3. Testar emissao com cliente Lucro Real/Presumido
echo.

pause
