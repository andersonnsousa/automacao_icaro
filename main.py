# main.py (versão atualizada com autenticação, exportação e detecção de mudanças)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import json
import cv2
import numpy as np
import os
import sys
from urllib.parse import urlparse
from datetime import datetime
import argparse
import time
import pandas as pd  # Para exportação CSV/Excel

# Argumentos
parser = argparse.ArgumentParser()
parser.add_argument("--url", type=str, required=True)
parser.add_argument("--output-dir", type=str, required=True)
parser.add_argument("--EMAIL", type=str, default=None)
parser.add_argument("--password", type=str, default=None)
args = parser.parse_args()

URL = args.url
OUTPUT_DIR = args.output_dir
EMAIL = args.EMAIL
PASSWORD = args.password
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mapeamento de tipos
ELEMENT_TYPES = {
    'h1': 'title', 'h2': 'subtitle', 'input': 'input', 'button': 'button',
    'a': 'link', 'label': 'label', 'p': 'paragraph', 'span': 'text', 'div': 'container'
}

KEYWORDS = {
    'bem-vindo': 'greeting',
    'email': 'email_input',
    'senha': 'password_input',
    'password': 'password_input',
    'lembrar': 'remember_checkbox',
    'cliente': 'user_role',
    'agente': 'user_role',
    'posto': 'user_role',
    'destinatário': 'user_role',
    'esqueceu': 'recovery_link',
    'entrar': 'login_button',
    'direitos': 'copyright',
    'login': 'login_page',
    'sign in': 'login_page'
}

def classify_element(element):
    tag = element.tag_name.lower()
    text = (element.text or '').strip().lower()
    value = (element.get_attribute("value") or '').lower()
    name = (element.get_attribute("name") or '').lower()
    type_attr = (element.get_attribute("type") or '').lower()
    id_attr = (element.get_attribute("id") or '').lower()
    placeholder = (element.get_attribute("placeholder") or '').lower()
    class_attr = (element.get_attribute("class") or '').lower()

    full_text = f"{text} {value} {name} {placeholder} {id_attr} {class_attr}"

    # Casos específicos
    if tag == 'input':
        if 'email' in full_text or 'usuario' in full_text or '@' in placeholder:
            return 'email_input'
        if type_attr == 'password':
            return 'password_input'
        if type_attr == 'checkbox' and ('lembrar' in full_text or 'remember' in full_text):
            return 'remember_checkbox'

    # Botões
    if tag == 'button' or 'submit' in type_attr:
        if 'entrar' in full_text or 'login' in full_text:
            return 'login_button'

    # Labels e opções de usuário
    if 'cliente' in full_text and 'role' in class_attr:
        return 'user_role'
    if 'agente' in full_text and 'role' in class_attr:
        return 'user_role'

    # Links
    if tag == 'a' and 'esqueceu' in full_text:
        return 'recovery_link'

    # Títulos
    if tag == 'h1' and 'bem-vindo' in full_text:
        return 'greeting'

    # Copyright
    if tag == 'p' and ('direitos' in full_text or 'rights' in full_text):
        return 'copyright'

    return 'unknown'
    tag = element.tag_name.lower()
    text = (element.text or '').strip().lower()
    value = (element.get_attribute("value") or '').lower()
    name = (element.get_attribute("name") or '').lower()
    type_attr = (element.get_attribute("type") or '').lower()
    full_text = f"{text} {value} {name} {type_attr}"

    if tag == 'input':
        if 'email' in full_text:
            return 'email_input'
        if type_attr == 'password':
            return 'password_input'
        if type_attr == 'checkbox':
            return 'remember_checkbox'

    for kw, typ in KEYWORDS.items():
        if kw in full_text:
            return typ

    return ELEMENT_TYPES.get(tag, 'unknown')

def scroll_to_bottom(driver, pause=1.5):
    """Rola até o fim da página para carregar conteúdo dinâmico"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def extract_structure(driver, url):
    print(f"[INFO] Carregando página: {url}")
    driver.get(url)

    try:
        # Espera explícita para garantir que a página carregou
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        print("[WARN] Página demorou para carregar, continuando mesmo assim.")

    # Rola para forçar carregamento de todos os elementos
    scroll_to_bottom(driver)

    # Força a aparição do formulário (se necessário)
    try:
        # Tenta clicar em um dos links de usuário (pode revelar o formulário)
        client_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Sou um cliente')]")
        driver.execute_script("arguments[0].click();", client_link)
        time.sleep(2)  # Aguarda o formulário aparecer
    except:
        print("[INFO] Não foi necessário interagir para revelar o formulário.")

    # Agora espera pelos campos de login
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "user[email]"))
        )
        print("[INFO] Campo de email detectado.")
    except:
        print("[WARN] Campo de email não encontrado após interação.")

    all_elements = driver.find_elements(By.XPATH, """
        //input[@type='email' or @type='password' or @name='user[email]' or @name='user[password]']
        | //input[@type='text' and contains(@name, 'email')]
        | //input[@type='checkbox']
        | //*[(text() != '') or @value or self::input or self::textarea]
    """)

    structure = []
    seen_texts = set()

    for idx, el in enumerate(all_elements):
        try:
            if not el.is_displayed():
                continue  # Ignora elementos ocultos

            text = el.text.strip()
            value = el.get_attribute("value") or ""
            name = el.get_attribute("name") or ""
            type_attr = el.get_attribute("type") or ""
            id_attr = el.get_attribute("id") or ""
            placeholder = el.get_attribute("placeholder") or ""
            full_text = f"{text} {value} {name} {type_attr} {id_attr} {placeholder}".lower()

            content = f"{text} {value}".strip()
            if not content and not name and not type_attr:
                continue
            if content in seen_texts:
                continue
            seen_texts.add(content)

            # Classificação melhorada
            if "email" in full_text or "usuario" in full_text:
                elem_type = "email_input"
            elif type_attr == "password":
                elem_type = "password_input"
            elif type_attr == "checkbox":
                elem_type = "remember_checkbox"
            elif type_attr == "submit" or (not type_attr and "entrar" in full_text):
                elem_type = "login_button"
            elif "cliente" in full_text and "role" in id_attr.lower():
                elem_type = "user_role"
            elif "agente" in full_text:
                elem_type = "user_role"
            elif "posto" in full_text:
                elem_type = "user_role"
            elif "destinatário" in full_text:
                elem_type = "user_role"
            elif "esqueceu" in full_text:
                elem_type = "recovery_link"
            elif "bem-vindo" in full_text:
                elem_type = "greeting"
            elif "direitos" in full_text:
                elem_type = "copyright"
            else:
                elem_type = "unknown"

            rect = el.rect
            item = {
                "index": idx,
                "type": elem_type,
                "tag": el.tag_name,
                "text": text,
                "value": value,
                "name": name,
                "type_attr": type_attr,
                "x": round(rect['x'], 2),
                "y": round(rect['y'], 2),
                "width": round(rect['width'], 2),
                "height": round(rect['height'], 2),
                "xpath": driver.execute_script("""
                    function getXPath(elt) {
                        if (elt.id) return '//*[@id="' + elt.id + '"]';
                        if (elt === document.body) return 'body';
                        let ix = 0;
                        for (let s = elt.parentNode?.firstChild; s; s = s.nextSibling)
                            if (s === elt) break;
                            else if (s.nodeType === 1 && s.tagName === elt.tagName) ix++;
                        return getXPath(elt.parentNode) + '/' + elt.tagName + '[' + (ix+1) + ']';
                    }
                    return getXPath(arguments[0]);
                """, el)
            }
            structure.append(item)
        except StaleElementReferenceException:
            continue
        except Exception as e:
            print(f"[WARN] Falha ao processar elemento {idx}: {e}")
            continue

    structure.sort(key=lambda x: (x['y'], x['x']))
    return structure, "Página de Login Icaro"
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        print(f"[INFO] Página carregou parcialmente: {url}")

    # Se credenciais forem fornecidas, tenta login básico (genérico)
    if EMAIL and PASSWORD:
        print("[INFO] Tentando login com credenciais fornecidas...")
        try:
            email_input = driver.find_element(By.XPATH, "//input[contains(@type,'email') or contains(@name,'user') or contains(@name,'email')]")
            password_input = driver.find_element(By.XPATH, "//input[@type='password']")
            login_button = driver.find_element(By.XPATH, "//input[@type='submit'] | //button[contains(text(),'Entrar')] | //button[contains(text(),'Login')]")

            email_input.send_keys(EMAIL)
            password_input.send_keys(PASSWORD)
            login_button.click()
            time.sleep(3)  # Aguarda redirecionamento
        except Exception as e:
            print(f"[WARN] Falha ao tentar login automático: {e}")

    # Rola para carregar todo o conteúdo
    scroll_to_bottom(driver)

    try:
        title = driver.title.strip() or "Página sem título"
    except:
        title = "Página não carregada"

    all_elements = driver.find_elements(By.XPATH, "//*[text() or @value]")
    structure = []
    seen_texts = set()

    for idx, el in enumerate(all_elements):
        try:
            if not el.is_displayed():
                continue
            text = el.text.strip()
            value = el.get_attribute("value") or ""
            content = f"{text} {value}".strip()
            if not content or content in seen_texts:
                continue
            seen_texts.add(content)

            rect = el.rect
            item = {
                "index": idx,
                "type": classify_element(el),
                "tag": el.tag_name,
                "text": text,
                "value": value,
                "x": round(rect['x'], 2),
                "y": round(rect['y'], 2),
                "width": round(rect['width'], 2),
                "height": round(rect['height'], 2),
                "xpath": driver.execute_script("""
                    function getXPath(elt) {
                        if (elt.id) return '//*[@id="' + elt.id + '"]';
                        if (elt === document.body) return 'body';
                        let ix = 0;
                        for (let s = elt.parentNode?.firstChild; s; s = s.nextSibling)
                            if (s === elt) break;
                            else if (s.nodeType === 1 && s.tagName === elt.tagName) ix++;
                        return getXPath(elt.parentNode) + '/' + elt.tagName + '[' + (ix+1) + ']';
                    }
                    return getXPath(arguments[0]);
                """, el)
            }
            structure.append(item)
        except StaleElementReferenceException:
            continue
        except Exception as e:
            print(f"[WARN] Ignorando elemento {idx}: {e}")
            continue

    structure.sort(key=lambda x: (x['y'], x['x']))
    return structure, title

def draw_bounding_boxes(structure, src_img, dst_img):
    if not os.path.exists(src_img): return
    img = cv2.imread(src_img)
    if img is None: return
    overlay = img.copy()

    colors = {
        'greeting': (255, 165, 0), 'email_input': (0, 128, 255),
        'password_input': (0, 100, 255), 'remember_checkbox': (147, 112, 219),
        'user_role': (255, 20, 147), 'recovery_link': (0, 255, 255),
        'login_button': (0, 255, 0), 'copyright': (128, 128, 128),
        'title': (255, 255, 0)
    }

    for item in structure:
        x, y, w, h = int(item['x']), int(item['y']), int(item['width']), int(item['height'])
        color = colors.get(item['type'], (200, 200, 200))
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        label = item['type']
        cv2.putText(overlay, label, (x + 3, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        cv2.putText(overlay, label, (x + 3, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    alpha = 0.7
    img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
    cv2.imwrite(dst_img, img)

def generate_web_viewer(structure, output_path, page_title, url):
    try:
        with open("templates/visualizador.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        html = """<html><head><title>Visualizador</title>
        <style>body{font-family:Arial;margin:20px}.element{border:1px solid #ddd;padding:10px;margin:10px 0;background:#fff}
        .type{font-weight:bold;color:#1a73e8}.pos{color:#666}.xpath{font-family:monospace;background:#eee;padding:3px}
        </style></head><body><h1>Elementos</h1><div id="elements-container"></div><script>const structure = {{json_data}};
        const c = document.getElementById('elements-container'); structure.forEach(i => {
        const d = document.createElement('div'); d.className='element';
        d.innerHTML = `<div class="type">${i.type}</div><div class="text">"${i.text}"</div>
        <div class="pos">(${i.x},${i.y})</div><div class="xpath">${i.xpath}</div>`; c.appendChild(d); });
        </script></body></html>"""

    json_data = json.dumps(structure, ensure_ascii=False, indent=2)
    html = html.replace("{{title}}", page_title)
    html = html.replace("{{url}}", url)
    html = html.replace("{{json_data}}", json_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

def export_to_excel(structure, excel_path):
    """Exporta a estrutura para Excel (com múltiplas abas)"""
    df = pd.DataFrame(structure)
    df_simple = df[["type", "text", "value", "tag", "x", "y", "width", "height"]]

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_simple.to_excel(writer, sheet_name="Resumo", index=False)
        df.to_excel(writer, sheet_name="Completo", index=False)
    print(f"[INFO] Exportado para Excel: {excel_path}")

def detect_changes(structure, base_dir):
    """Compara com a última análise e gera relatório de mudanças"""
    changes_log = os.path.join(base_dir, "mudancas.log")
    latest_json = os.path.join(base_dir, "latest.json")

    previous = None
    has_changed = False
    changes = []

    # Carrega análise anterior
    if os.path.exists(latest_json):
        try:
            with open(latest_json, "r", encoding="utf-8") as f:
                previous = json.load(f)
        except:
            print("[WARN] Falha ao ler análise anterior")

    current_texts = {f"{item['text']}_{item['value']}_{item['type']}": item for item in structure}
    prev_texts = {f"{item['text']}_{item['value']}_{item['type']}": item for item in previous} if previous else {}

    # Detecta novos elementos
    for key, item in current_texts.items():
        if key not in prev_texts:
            changes.append(f"➕ Novo elemento: {item['type']} | '{item['text']}'")
            has_changed = True

    # Detecta removidos
    for key, item in prev_texts.items():
        if key not in current_texts:
            changes.append(f"➖ Removido: {item['type']} | '{item['text']}'")
            has_changed = True

    # Salva mudanças
    mode = "a" if os.path.exists(changes_log) else "w"
    with open(changes_log, mode, encoding="utf-8") as f:
        f.write(f"\n--- Mudanças em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        if has_changed:
            f.write("\n".join(changes) + "\n")
        else:
            f.write("✅ Nenhuma mudança detectada.\n")

    # Atualiza latest.json
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    return has_changed, changes

def main():
    print(f"[INFO] Analisando: {URL}")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,800")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        structure, title = extract_structure(driver, URL)

        # Salva JSON
        json_path = os.path.join(OUTPUT_DIR, "estrutura.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

        # Captura de tela
        screenshot = os.path.join(OUTPUT_DIR, "pagina.png")
        annotated = os.path.join(OUTPUT_DIR, "pagina_anotada.png")
        driver.save_screenshot(screenshot)
        draw_bounding_boxes(structure, screenshot, annotated)

        # Visualizador
        viewer = os.path.join(OUTPUT_DIR, "visualizador.html")
        generate_web_viewer(structure, viewer, title, URL)

        # Exportação para Excel/CSV
        csv_path = os.path.join(OUTPUT_DIR, "elementos.csv")
        excel_path = os.path.join(OUTPUT_DIR, "elementos.xlsx")
        df = pd.DataFrame(structure)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        export_to_excel(structure, excel_path)

        # Detecção de mudanças
        parsed = urlparse(URL)
        base_domain_dir = os.path.join("analyses", parsed.netloc.replace("www.", ""))
        changed, changes = detect_changes(structure, base_domain_dir)
        print(f"[INFO] Detecção de mudanças: {'Alterações encontradas' if changed else 'Sem alterações'}")

        print(f"[OK] Análise concluída: {OUTPUT_DIR}")

    except Exception as e:
        print(f"[ERRO] {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()