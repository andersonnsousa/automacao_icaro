# autologin.py
import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not EMAIL or not PASSWORD:
    raise Exception("EMAIL ou PASSWORD não definidos no arquivo .env")

EMAIL = str(EMAIL)
PASSWORD = str(PASSWORD)

COOKIES_FILE = "session_cookies_icaro.json"
TARGET_URL = "https://icaro.eslcloud.com.br/users/sign_in"
DASHBOARD_INDICATOR = "dashboard"  # Parte da URL que indica login bem-sucedido

def save_cookies(driver):
    """Salva os cookies da sessão autenticada."""
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)
    print(f"🍪 Cookies salvos em: {COOKIES_FILE}")

def load_cookies(driver):
    """Carrega cookies salvos e os adiciona à sessão."""
    if not os.path.exists(COOKIES_FILE):
        return False
    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        for cookie in cookies:
            # Remove 'sameSite' se causar erro
            cookie.pop('sameSite', None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print(f"⚠️ Erro ao adicionar cookie: {e}")
        print("🍪 Cookies carregados com sucesso.")
        return True
    except Exception as e:
        print(f"❌ Falha ao carregar cookies: {e}")
        return False

def is_logged_in(driver):
    """Verifica se já está logado com base na URL ou em um elemento."""
    current_url = driver.current_url.lower()
    if DASHBOARD_INDICATOR in current_url:
        return True
    try:
        # Verifica se o campo de email não está visível (indicando login)
        WebDriverWait(driver, 3).until_not(
            EC.presence_of_element_located((By.NAME, "user[email]"))
        )
        return True
    except:
        return False

def safe_send_keys(driver, xpath, value, timeout=10):
    try:
        field = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
        field.clear()
        field.send_keys(str(value))
        return True
    except TimeoutException:
        print(f"❌ Timeout: Campo não encontrado (XPath: {xpath})")
        return False
    except Exception as e:
        print(f"❌ Erro ao preencher campo: {e}")
        return False

def perform_login():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless=new")  # Remova para ver o login

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(TARGET_URL)
        print("🌐 Acessando página de login...")

        # Verifica se já está logado
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        if is_logged_in(driver):
            print("✅ Você já está logado!")
            input("Pressione ENTER para continuar...")
            return

        # Tenta carregar cookies
        if load_cookies(driver):
            driver.refresh()
            time.sleep(2)
            if is_logged_in(driver):
                print("✅ Login restaurado com cookies!")
                input("Pressione ENTER para continuar...")
                return

        # Se não funcionou, faz login manual
        print("🔐 Iniciando login com credenciais...")

        # Preenche email
        if not safe_send_keys(driver, "//input[@name='user[email]']", EMAIL):
            raise Exception("Campo de email não encontrado")

        # Preenche senha
        if not safe_send_keys(driver, "//input[@name='user[password]']", PASSWORD):
            raise Exception("Campo de senha não encontrado")

        # Marca "Lembre-se de mim"
        try:
            checkbox = driver.find_element(By.XPATH, "//input[@name='user[remember_me]']")
            if not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)
        except:
            pass

        # Clica em "Entrar"
        login_xpaths = [
            "//input[@type='submit' and @value='Entrar']",
            "//input[@type='submit']"
        ]
        login_clicado = False
        for xpath in login_xpaths:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                button.click()
                login_clicado = True
                break
            except:
                continue
        if not login_clicado:
            raise Exception("Botão de login não encontrado")

        # Aguarda redirecionamento
        WebDriverWait(driver, 20).until(
            lambda d: DASHBOARD_INDICATOR in d.current_url.lower()
        )
        print("🎉 Login bem-sucedido!")

        # Salva cookies para uso futuro
        save_cookies(driver)

        input("\nPressione ENTER para fechar o navegador...")
    except Exception as e:
        print(f"❌ Erro: {e}")
        driver.save_screenshot("erro_login.png")
        print("📸 Screenshot salvo.")
    finally:
        driver.quit()

if __name__ == "__main__":
    perform_login()