@echo off
REM ============================================================================
REM SCRIPT DE BACKUP DO BANCO DE DADOS - Windows Server
REM Sistema: EmiteMax v2.0
REM Servidor: 192.168.0.52:8080
REM ============================================================================

echo.
echo ============================================================
echo   BACKUP BANCO DE DADOS PostgreSQL
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

REM Criar pasta de backups se não existir
if not exist "C:\backups\" mkdir C:\backups\

REM Gerar nome do arquivo com data e hora
set DATA=%date:~-4%%date:~3,2%%date:~0,2%
set HORA=%time:~0,2%%time:~3,2%%time:~6,2%
set HORA=%HORA: =0%
set BACKUP_FILE=C:\backups\sjtnfe_backup_%DATA%_%HORA%.sql

echo.
echo [INFO] Conectando ao banco de dados %PGDATABASE%...
echo [INFO] Criando backup em: %BACKUP_FILE%
echo.

REM Executar backup
"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d %PGDATABASE% --no-owner --no-privileges > "%BACKUP_FILE%" 2>backup_error.log

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao criar backup!
    echo [INFO] Verifique o arquivo backup_error.log para detalhes.
    type backup_error.log
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   BACKUP CONCLUIDO COM SUCESSO!
echo ============================================================
echo.
echo [OK] Arquivo criado: %BACKUP_FILE%
echo.

REM Calcular tamanho do arquivo
for %%A in ("%BACKUP_FILE%") do set TAMANHO=%%~zA
set /a TAMANHO_MB=%TAMANHO% / 1048576

echo [INFO] Tamanho do backup: %TAMANHO_MB% MB
echo.

REM Gerar arquivo de informações
echo Backup do Banco de Dados EmiteMax > "%BACKUP_FILE%.info"
echo ========================================== >> "%BACKUP_FILE%.info"
echo Data/Hora: %date% %time% >> "%BACKUP_FILE%.info"
echo Servidor: %PGHOST%:%PGPORT% >> "%BACKUP_FILE%.info"
echo Banco: %PGDATABASE% >> "%BACKUP_FILE%.info"
echo Usuario: %PGUSER% >> "%BACKUP_FILE%.info"
echo Tamanho: %TAMANHO_MB% MB >> "%BACKUP_FILE%.info"
echo ========================================== >> "%BACKUP_FILE%.info"

echo [OK] Arquivo de informacoes: %BACKUP_FILE%.info
echo.

REM Listar backups existentes
echo BACKUPS EXISTENTES:
echo ----------------------------------------------------------
dir C:\backups\sjtnfe_backup_*.sql /o-d /b | findstr /n "^"
echo ----------------------------------------------------------
echo.

REM Instruções para transferência
echo PROXIMOS PASSOS:
echo.
echo 1. Copie o arquivo para o seu computador local:
echo    %BACKUP_FILE%
echo.
echo 2. Metodos de transferencia:
echo    - WinSCP / FileZilla (FTP)
echo    - Copiar via Remote Desktop
echo    - Pendrive / Pasta compartilhada
echo.
echo 3. No Mac, execute: restaurar_banco_mac.sh
echo.

pause
