@echo off
REM Script para verificar erros recentes no log do Windows

echo ========================================
echo ULTIMOS ERROS NO LOG
echo ========================================
echo.

REM Ver últimas 100 linhas do log
powershell -Command "Get-Content C:\nfe_app\logs\service.log -Tail 100 | Select-String -Pattern 'ERROR|Exception|Traceback|Failed|cliente_id|logo_path|DANFE' -Context 2,2"

echo.
echo ========================================
echo ERROS RECENTES (ULTIMA HORA)
echo ========================================
echo.

REM Ver erros das últimas linhas
powershell -Command "Get-Content C:\nfe_app\logs\service.log -Tail 200 | Out-File -FilePath C:\nfe_app\logs\ultimos_erros.txt"

echo Log gravado em: C:\nfe_app\logs\ultimos_erros.txt
echo.
echo Procurando por padroes especificos...
echo.

REM Procurar por erros específicos
powershell -Command "Get-Content C:\nfe_app\logs\service.log -Tail 200 | Select-String -Pattern 'NameError|AttributeError|KeyError|TypeError|ImportError'"

echo.
pause
