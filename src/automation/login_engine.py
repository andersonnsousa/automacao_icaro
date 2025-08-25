# autologin.py
import os
import json
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import logging

# --- CONFIGURAÇÃO DE LOGGING ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/analyzer.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- CARREGA CREDENCIAIS ---
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not EMAIL or not PASSWORD:
    raise Exception("EMAIL ou PASSWORD não definidos no arquivo .env")

EMAIL = str(EMAIL)
PASSWORD = str(PASSWORD)

def get_latest_analysis_path(base_dir="analyses"):
    if not os.path.exists(base_dir):
        logging.error(f"Pasta '{base_dir}' não encontrada.")
        return None, None

    all_paths = []
    for domain in os.listdir(base_dir):
        domain_path = os.path.join(base_dir, domain)
        if os.path.isdir(domain_path):
            for timestamp in os.listdir(domain_path):
                ts_path = os.path.join(domain_path, timestamp)
                if os.path.isdir(ts_path):
                    all_paths.append(ts_path)

    if not all_paths:
        logging.error("Nenhuma análise encontrada.")
        return None, None

    latest_analysis = max(all_paths, key=os.path.getctime)
    domain = os.path.basename(os.path.dirname(latest_analysis))
    url = f"https://{domain}"
    return latest_analysis, url

def find_login_form(structure):
    email_field = None
    password_field = None
    submit_button = None
    remember_checkbox = None

    email_keywords = ['email', 'usuario', 'user', 'login', 'nome de usuário']
    password_keywords = ['senha', 'password', 'pass']
    login_keywords = ['entrar', 'login', 'sign in', 'acessar']
    remember_keywords = ['lembrar', 'remember', 'manter conectado']

    for el in structure:
        tag = el['tag']
        text = (el['text'] or '').lower()
        value = (el['value'] or '').lower()
        attrs = el['attributes']
        full_text = f"{text} {value} {attrs.get('placeholder', '')} {attrs.get('name', '')} {attrs.get('id', '')}".lower()

        if tag == 'input' and not email_field:
            for kw in email_keywords:
                if kw in full_text:
                    email_field = el
                    break

        if tag == 'input' and not password_field:
            if attrs.get('type') == 'password':
                password_field = el
            else:
                for kw in password_keywords:
                    if kw in full_text:
                        password_field = el
                        break

        if (tag == 'input' or tag == 'button') and not submit_button:
            for kw in login_keywords:
                if kw in full_text:
                    submit_button = el
                    break

        if tag == 'input' and not remember_checkbox:
            if attrs.get('type') == 'checkbox':
                for kw in remember_keywords:
                    if kw in full_text:
                        remember_checkbox = el
                        break

    return {
        "email": email_field,
        "password": password_field,
        "submit": submit_button,
        "remember": remember_checkbox
    }

def perform_adaptive_login():
    logging.info("🔍 Procurando a análise mais recente...")
    analysis_path, base_url = get_latest_analysis_path()

    if not analysis_path or not base_url:
        return

    logging.info(f"📂 Análise encontrada: {analysis_path}")
    logging.info(f"🌐 URL alvo: {base_url}")

    json_path = os.path.join(analysis_path, "estrutura.json")
    if not os.path.exists(json_path):
        logging.error(f"❌ Arquivo estrutura.json não encontrado: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        structure = json.load(f)

    form = find_login_form(structure)

    if not form["email"]:
        logging.warning("⚠️ Campo de email não identificado no contexto.")
    if not form["password"]:
        logging.error("❌ Campo de senha não identificado. Login não pode continuar.")
        return
    if not form["submit"]:
        logging.warning("⚠️ Botão de login não identificado.")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(base_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        if form["email"]:
            try:
                field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, form["email"]["xpath"]))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", field)
                field.send_keys(EMAIL)
                logging.info("📧 Email preenchido.")
            except Exception as e:
                logging.warning(f"⚠️ Falha ao preencher email: {e}")

        try:
            field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, form["password"]["xpath"]))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", field)
            field.send_keys(PASSWORD)
            logging.info("🔒 Senha preenchida.")
        except Exception as e:
            logging.error(f"❌ Falha ao preencher senha: {e}")
            return

        if form["remember"]:
            try:
                checkbox = driver.find_element(By.XPATH, form["remember"]["xpath"])
                if not checkbox.is_selected():
                    checkbox.click()
                logging.info("✅ 'Lembre-se de mim' marcado.")
            except Exception as e:
                logging.warning(f"⚠️ Erro ao marcar checkbox: {e}")

        if form["submit"]:
            try:
                button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, form["submit"]["xpath"]))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                button.click()
                logging.info("🚀 Botão de login clicado.")
            except Exception as e:
                logging.warning(f"⚠️ Falha ao clicar no botão de login: {e}")
        else:
            try:
                field.send_keys("\n")
                logging.info("⌨️ Enviado com Enter.")
            except:
                logging.error("❌ Não foi possível enviar o formulário.")
                return

        logging.info("⏳ Aguardando login...")
        WebDriverWait(driver, 20).until(
            lambda d: d.current_url != base_url
        )
        logging.info(f"🎉 Login bem-sucedido! Nova URL: {driver.current_url}")

        input("\nPressione ENTER para fechar o navegador...")
    except Exception as e:
        logging.error(f"❌ Erro durante o login: {e}")
        driver.save_screenshot("erro_login.png")
        logging.info("📸 Screenshot salvo.")
    finally:
        driver.quit()

if __name__ == "__main__":
    perform_adaptive_login()