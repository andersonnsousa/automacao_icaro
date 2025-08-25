# main.py
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

parser = argparse.ArgumentParser()
parser.add_argument("--url", type=str, required=True)
parser.add_argument("--output-dir", type=str, required=True)
args = parser.parse_args()

URL = args.url
OUTPUT_DIR = args.output_dir
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_structure(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        print(f"[INFO] Página carregou parcialmente: {url}")

    # Rola até o fim para carregar conteúdo dinâmico
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    try:
        title = driver.title.strip() or "Página sem título"
    except:
        title = "Página não carregada"

    all_elements = driver.find_elements(By.XPATH, """
        //*[
            (text() != '' and not(self::script or self::style))
            or @value
            or @type
            or @href
            or @onclick
            or @class
            or @id
        ]
    """)

    structure = []
    seen_xpaths = set()

    for idx, el in enumerate(all_elements):
        try:
            if not el.is_displayed():
                continue

            attributes = {}
            for attr in ['name', 'id', 'class', 'type', 'placeholder', 'href', 'title', 'alt', 'value', 'src']:
                val = el.get_attribute(attr)
                if val:
                    attributes[attr] = val

            rect = el.rect
            tag = el.tag_name.lower()
            text = el.text.strip()
            value = el.get_attribute("value") or ""

            xpath = driver.execute_script("""
                function getXPath(elt) {
                    if (elt.id) return '//*[@id="' + elt.id + '"]';
                    if (elt === document.body) return 'body';
                    let ix = 0;
                    for (let s = elt.parentNode?.firstChild; s; s = s.nextSibling) {
                        if (s === elt) break;
                        if (s.nodeType === 1 && s.tagName === elt.tagName) ix++;
                    }
                    return getXPath(elt.parentNode) + '/' + elt.tagName + '[' + (ix+1) + ']';
                }
                return getXPath(arguments[0]);
            """, el)

            if xpath in seen_xpaths:
                continue
            seen_xpaths.add(xpath)

            item = {
                "index": idx,
                "tag": tag,
                "text": text,
                "value": value,
                "attributes": attributes,
                "x": round(rect['x'], 2),
                "y": round(rect['y'], 2),
                "width": round(rect['width'], 2),
                "height": round(rect['height'], 2),
                "xpath": xpath
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
    if not os.path.exists(src_img):
        return
    img = cv2.imread(src_img)
    if img is None:
        return
    overlay = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

    for item in structure:
        x, y, w, h = int(item['x']), int(item['y']), int(item['width']), int(item['height'])
        cv2.rectangle(img, (x, y), (x + w, y + h), (100, 100, 255), 1)
        label = f"{item['tag']}"
        cv2.putText(overlay, label, (x + 2, y - 2), font, font_scale, (0, 0, 0), 2)
        cv2.putText(overlay, label, (x + 2, y - 2), font, font_scale, (255, 255, 255), 1)

    alpha = 0.6
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
        d.innerHTML = `<div class="tag"><${i.tag}></div><div class="text">"${i.text || i.value}"</div>
        <div class="pos">(${i.x},${i.y})</div><div class="xpath">${i.xpath}</div>`; c.appendChild(d); });
        </script></body></html>"""

    json_data = json.dumps(structure, ensure_ascii=False, indent=2)
    html = html.replace("{{title}}", page_title)
    html = html.replace("{{url}}", url)
    html = html.replace("{{json_data}}", json_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

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

        with open(os.path.join(OUTPUT_DIR, "estrutura.json"), "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

        screenshot = os.path.join(OUTPUT_DIR, "pagina.png")
        annotated = os.path.join(OUTPUT_DIR, "pagina_anotada.png")
        driver.save_screenshot(screenshot)
        draw_bounding_boxes(structure, screenshot, annotated)

        generate_web_viewer(structure, os.path.join(OUTPUT_DIR, "visualizador.html"), title, URL)

        print(f"[OK] Análise concluída: {OUTPUT_DIR}")

    except Exception as e:
        print(f"[ERRO] Falha na análise: {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()