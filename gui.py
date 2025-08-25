# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import sys
from urllib.parse import urlparse
from datetime import datetime
import json

# --- CONFIGURAÇÃO DE LOGGING ---
os.makedirs("logs", exist_ok=True)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/analyzer.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class WebAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🌐 Analisador Web Adaptativo")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.setup_styles()
        self.create_widgets()
        self.load_analyses()
        logging.info("GUI iniciada.")

    def setup_styles(self):
        style = ttk.Style()
        # style.theme_use('clam')  # Pode causar problemas no Python 3.13
        style.configure("TButton", padding=8, font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 11))
        style.configure("Header.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Treeview", rowheight=28, font=("Helvetica", 9))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        # ❌ Removido: style.map("TNotebook.Tab", padding=...) → causa erro no Python 3.13

    def create_widgets(self):
        # === Painel Superior: Entrada e Ações ===
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(top_frame, text="URL:", font=("Helvetica", 11)).pack(side="left", padx=(0, 5))
        self.url_var = tk.StringVar(value="https://")
        ttk.Entry(top_frame, textvariable=self.url_var, width=60).pack(side="left", padx=(0, 10))

        ttk.Button(top_frame, text="▶ Analisar", command=self.start_analysis, width=12).pack(side="left", padx=2)
        ttk.Button(top_frame, text="⚡ Login Rápido", command=self.quick_login, width=15).pack(side="left", padx=2)

        # === Painel Principal: Abas ===
        self.tab_control = ttk.Notebook(self.root)
        self.tab_control.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- Aba: Análises ---
        self.tab_analyses = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_analyses, text="📊 Análises", padding=10)

        # Treeview para análises
        self.tree = ttk.Treeview(self.tab_analyses, columns=("timestamp", "url"), show="tree headings", height=15)
        self.tree.heading("#0", text="Domínio")
        self.tree.heading("timestamp", text="Data e Hora")
        self.tree.heading("url", text="URL Analisada")
        self.tree.column("timestamp", width=150)
        self.tree.column("url", width=300)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Botões de ação
        btn_frame = ttk.Frame(self.tab_analyses)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="🔄 Recarregar", command=self.load_analyses).pack(side="left")
        self.open_btn = ttk.Button(btn_frame, text="📁 Abrir Pasta", state="disabled", command=self.open_selected_results)
        self.open_btn.pack(side="left", padx=5)
        self.view_btn = ttk.Button(btn_frame, text="🔍 Visualizar", state="disabled", command=self.view_selected_analysis)
        self.view_btn.pack(side="left", padx=5)

        # --- Aba: Resultados Atuais ---
        self.tab_current = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_current, text="📋 Resultado Atual", padding=10)

        self.progress = ttk.Progressbar(self.tab_current, length=500, mode="determinate")
        self.progress.pack(pady=20)
        self.progress_label = ttk.Label(self.tab_current, text="Pronto para análise.", font=("Helvetica", 10))
        self.progress_label.pack()

        # === Status Bar ===
        self.status_var = tk.StringVar(value="Pronto.")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", font=("Helvetica", 9), foreground="gray")
        self.status_bar.pack(side="bottom", fill="x")

        # === Variáveis de Estado ===
        self.current_output_dir = None
        self.selected_analysis_path = None
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def load_analyses(self):
        """Carrega todas as análises do diretório analyses/"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not os.path.exists("analyses"):
            return

        for domain in os.listdir("analyses"):
            domain_path = os.path.join("analyses", domain)
            if os.path.isdir(domain_path):
                parent = self.tree.insert("", "end", text=domain, open=False)
                timestamps = sorted([t for t in os.listdir(domain_path) if os.path.isdir(os.path.join(domain_path, t))], reverse=True)
                for ts in timestamps:
                    json_path = os.path.join(domain_path, ts, "estrutura.json")
                    url = "Desconhecida"
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                if data:
                                    # Tenta extrair a URL da análise (opcional)
                                    pass
                        except:
                            pass
                    ts_display = ts.replace("_", " ").replace("-", ":")
                    self.tree.insert(parent, "end", text="", values=(ts_display, url), tags=(os.path.join(domain_path, ts),))

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, "tags")
        if tags:
            self.selected_analysis_path = tags[0]
            self.open_btn.config(state="normal")
            self.view_btn.config(state="normal")
        else:
            self.open_btn.config(state="disabled")
            self.view_btn.config(state="disabled")

    def open_selected_results(self):
        if hasattr(self, 'selected_analysis_path') and os.path.exists(self.selected_analysis_path):
            os.startfile(self.selected_analysis_path)
        else:
            messagebox.showwarning("Aviso", "Pasta não encontrada.")

    def view_selected_analysis(self):
        if hasattr(self, 'selected_analysis_path') and os.path.exists(self.selected_analysis_path):
            html_path = os.path.join(self.selected_analysis_path, "visualizador.html")
            if os.path.exists(html_path):
                os.startfile(html_path)
            else:
                messagebox.showwarning("Aviso", "visualizador.html não encontrado.")
        else:
            messagebox.showwarning("Aviso", "Análise não encontrada.")

    def start_analysis(self):
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror("Erro", "URL inválida.")
            return

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_dir = os.path.join("analyses", domain)
        output_dir = os.path.join(base_dir, timestamp)

        self.current_output_dir = output_dir
        self.open_btn.config(state="disabled")
        self.view_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label.config(text="Iniciando análise...")
        self.status_var.set(f"Analisando: {url}")

        thread = threading.Thread(target=self.run_analysis_in_thread, args=(url, output_dir), daemon=True)
        thread.start()

    def run_analysis_in_thread(self, url, output_dir):
        def update_progress(value):
            self.progress["value"] = value
            self.progress_label.config(text=f"Progresso: {int(value)}%")

        def finish(success, message):
            self.progress_label.config(text="✅ Concluído!" if success else "❌ Falha")
            self.status_var.set("Análise finalizada." if success else "Falha na análise.")
            messagebox.showinfo("Resultado", message) if success else messagebox.showerror("Erro", message)
            self.load_analyses()  # Atualiza a lista

        try:
            update_progress(20)
            cmd = [sys.executable, "main.py", "--url", url, "--output-dir", output_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.stderr:
                logging.error("STDERR:\n" + result.stderr)
            if result.returncode != 0:
                raise Exception(result.stderr or "Erro desconhecido")

            update_progress(100)
            logging.info(f"Sucesso: {output_dir}")
            finish(True, f"✅ Sucesso!\n{output_dir}")

        except Exception as e:
            error_msg = str(e).split('\n')[0]
            logging.error(f"Falha: {error_msg}")
            finish(False, f"❌ Erro:\n{error_msg}")

    def quick_login(self):
        def run():
            try:
                import autologin
                autologin.perform_adaptive_login()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Falha no login:\n{e}"))
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

if __name__ == "__main__":
    logging.info("="*60)
    logging.info("Iniciando Analisador Web Adaptativo")
    logging.info(f"Diretório: {os.getcwd()}")
    try:
        root = tk.Tk()
        app = WebAnalyzerGUI(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Falha crítica: {e}", exc_info=True)
        messagebox.showerror("Erro", f"Erro ao iniciar GUI:\n{e}")