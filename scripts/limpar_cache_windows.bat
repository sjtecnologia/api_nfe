@echo off
REM Script para limpar cache Python no Windows Server
REM Execute este script no diretório raiz do projeto api_nfe

echo ========================================
echo Limpando cache Python...
echo ========================================

REM Limpar arquivos .pyc
echo.
echo [1/4] Removendo arquivos .pyc...
for /r %%i in (*.pyc) do (
    del /q "%%i" 2>nul
    if exist "%%i" (
        echo ERRO: Nao foi possivel remover %%i
    )
)
echo OK - Arquivos .pyc removidos

REM Limpar diretórios __pycache__
echo.
echo [2/4] Removendo diretorios __pycache__...
for /d /r %%i in (__pycache__) do (
    rd /s /q "%%i" 2>nul
    if exist "%%i" (
        echo AVISO: Nao foi possivel remover %%i
    )
)
echo OK - Diretorios __pycache__ removidos

REM Limpar cache de models (específico)
echo.
echo [3/4] Limpando cache de models...
if exist "models\__pycache__" (
    rd /s /q "models\__pycache__" 2>nul
    echo OK - Cache de models removido
) else (
    echo OK - Nenhum cache em models
)

REM Limpar cache de auth (específico)
echo.
echo [4/4] Limpando cache de auth...
if exist "auth\__pycache__" (
    rd /s /q "auth\__pycache__" 2>nul
    echo OK - Cache de auth removido
) else (
    echo OK - Nenhum cache em auth
)

echo.
echo ========================================
echo Cache limpo com sucesso!
echo ========================================
echo.
echo IMPORTANTE: Reinicie o servico Flask:
echo   net stop api_nfe_principal
echo   net start api_nfe_principal
echo.
echo Ou use o restart:
echo   net stop api_nfe_principal ^&^& net start api_nfe_principal
echo.
pause
