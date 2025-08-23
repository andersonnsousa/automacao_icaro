# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import sys
from urllib.parse import urlparse
from datetime import datetime

# --- CONFIGURAÇÃO DE LOGGING (Atualizada) ---
import logging

# Cria a pasta 'logs' se não existir
os.makedirs("logs", exist_ok=True)

# Configura o logging para salvar no arquivo dentro da pasta 'logs'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/analyzer.log', encoding='utf-8'),  # ✅ Caminho corrigido
        logging.StreamHandler(sys.stdout)
    ]
)
# --- FIM DA CONFIGURAÇÃO DE LOGGING ---

class WebAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔍 Analisador Web Generalista")
        self.root.geometry("800x600")
        self.setup_styles()
        self.create_widgets()
        logging.info("GUI iniciada.")

    def setup_styles(self):
        style = ttk.Style()
        style.configure("TButton", padding=6, font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 11))
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))

    def create_widgets(self):
        ttk.Label(self.root, text="Analisador Web Generalista", style="Header.TLabel").pack(pady=10)
        ttk.Label(self.root, text="Insira qualquer URL:").pack(pady=(10, 0))
        self.url_var = tk.StringVar(value="https://")
        ttk.Entry(self.root, textvariable=self.url_var, width=80).pack(pady=5)

        self.analyze_btn = ttk.Button(self.root, text="▶ Analisar Página", command=self.start_analysis)
        self.analyze_btn.pack(pady=10)

        self.login_btn = ttk.Button(self.root, text="⚡ Login Rápido", command=self.quick_login)
        self.login_btn.pack(pady=10)

        self.progress = ttk.Progressbar(self.root, length=500, mode="determinate")
        self.progress.pack(pady=10)
        self.progress_label = ttk.Label(self.root, text="Pronto.")
        self.progress_label.pack()

        self.open_btn = ttk.Button(self.root, text="📁 Abrir Resultados", state="disabled", command=self.open_results)
        self.open_btn.pack(pady=10)

        ttk.Label(self.root, text="© 2025 - Análise Automatizada de Interfaces", foreground="gray").pack(side="bottom", pady=20)

        self.current_output_dir = None

    def start_analysis(self):
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror("Erro", "Por favor, insira uma URL válida (com http:// ou https://)")
            return

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_dir = os.path.join("analyses", domain)
        output_dir = os.path.join(base_dir, timestamp)

        # Garante que a pasta existe
        os.makedirs(output_dir, exist_ok=True)

        self.current_output_dir = output_dir
        self.open_btn.config(state="disabled")
        self.analyze_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label.config(text="Iniciando análise...")

        # Executa em thread separada
        thread = threading.Thread(target=self.run_analysis_in_thread, args=(url, output_dir), daemon=True)
        thread.start()

    def run_analysis_in_thread(self, url, output_dir):
        def update_progress(value):
            self.progress["value"] = value
            self.progress_label.config(text=f"Progresso: {int(value)}%")

        def finish(success, message):
            self.analyze_btn.config(state="normal")
            if success:
                self.progress_label.config(text="✅ Concluído!")
                self.open_btn.config(state="normal")
            else:
                self.progress_label.config(text="❌ Falha")
            messagebox.showinfo("Resultado", message) if success else messagebox.showerror("Erro", message)

        try:
            update_progress(20)

            # Comando para executar main.py
            cmd = [
                sys.executable, "main.py",
                "--url", url,
                "--output-dir", output_dir
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # Log de saída
            if result.stdout:
                logging.info("STDOUT:\n" + result.stdout)
            if result.stderr:
                logging.error("STDERR:\n" + result.stderr)

            if result.returncode != 0:
                raise Exception(result.stderr or "Erro desconhecido")

            update_progress(100)
            logging.info(f"Sucesso: {output_dir}")
            finish(True, f"✅ Sucesso!\n{output_dir}")

        except Exception as e:
            error_msg = str(e)
            logging.error(f"Falha: {error_msg}")
            finish(False, f"❌ Erro:\n{error_msg}")

    def open_results(self):
        if self.current_output_dir and os.path.exists(self.current_output_dir):
            os.startfile(self.current_output_dir)  # Windows
        else:
            messagebox.showwarning("Aviso", "Pasta não encontrada.")

    def quick_login(self):
        """Executa o login rápido em uma thread separada"""
        def run():
            try:
                # Importa o módulo de login
                import autologin
                # Executa na mesma thread do Selenium
                autologin.perform_login()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Falha no login:\n{e}"))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()


if __name__ == "__main__":
    # Cria a pasta logs no início, antes de qualquer log
    os.makedirs("logs", exist_ok=True)

    logging.info("="*60)
    logging.info("Iniciando Analisador Web Generalista")
    logging.info(f"Diretório: {os.getcwd()}")
    try:
        root = tk.Tk()
        app = WebAnalyzerGUI(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Falha crítica: {e}", exc_info=True)
        messagebox.showerror("Erro", f"Erro ao iniciar GUI:\n{e}")