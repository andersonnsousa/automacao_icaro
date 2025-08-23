@echo off
:: install.bat
:: Script de Instalação Automática para o Analizador Web Icaro

echo.
echo ============================================================
echo  Analizador Web Icaro - Instalação Automática
echo ============================================================
echo.

:: Verifica se o Python está instalado
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado. Por favor, instale o Python 3.8+ e adicione ao PATH.
    echo    Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Cria o ambiente virtual
echo ✅ Criando ambiente virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Falha ao criar o ambiente virtual.
    pause
    exit /b 1
)

:: Ativa o ambiente virtual e instala as dependências
echo ✅ Instalando dependências...
call venv\Scripts\activate.bat
pip install selenium webdriver-manager opencv-python pandas openpyxl python-dotenv fpdf2
if %errorlevel% neq 0 (
    echo ❌ Falha ao instalar as dependências.
    pause
    exit /b 1
)

:: Cria o arquivo .env se não existir
if not exist ".env" (
    echo EMAIL=seu_usuario@empresa.com > .env
    echo PASSWORD=sua_senha_segura >> .env
    echo ✅ Arquivo .env criado. Por favor, edite com suas credenciais.
) else (
    echo ℹ️ Arquivo .env já existe. Preservando configurações existentes.
)

:: Cria as pastas necessárias
mkdir analyses >nul 2>&1
echo ✅ Estrutura de pastas criada.

:: Cria um atalho para a GUI
echo @echo off > start_gui.bat
echo call venv\Scripts\activate.bat >> start_gui.bat
echo python gui.py >> start_gui.bat
echo pause >> start_gui.bat
echo ✅ Atalho 'start_gui.bat' criado.

echo.
echo ============================================================
echo  ✅ Instalação concluída com sucesso!
echo ============================================================
echo.
echo 1. Edite o arquivo '.env' com seu EMAIL e PASSWORD.
echo 2. Execute 'start_gui.bat' para iniciar a interface.
echo.
pause