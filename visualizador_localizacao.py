# visualizador_localizacao.py
import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import csv

ANALYSES_DIR = "analyses"


class LocalizacaoDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Dashboard de Análise Web - Localização de Elementos")
        self.root.geometry("1400x900")

        self.selected_analysis = None
        self.original_image = None
        self.image_tk = None
        self.current_elements = []

        self.setup_widgets()
        self.load_analyses()

    def setup_widgets(self):
        # === Painel Esquerdo: Navegação ===
        left_frame = ttk.Frame(self.root, width=300)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="📂 Análises", font=("Helvetica", 12, "bold")).pack(pady=5)

        # Treeview para domínios e timestamps
        self.tree = ttk.Treeview(left_frame, columns=("timestamp",), show="tree headings", height=20)
        self.tree.heading("#0", text="Domínio")
        self.tree.heading("timestamp", text="Execução")
        self.tree.column("timestamp", width=130)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_analysis)

        ttk.Button(left_frame, text="🔄 Recarregar", command=self.load_analyses).pack(pady=5)

        # === Painel Direito: Abas (Dashboard) ===
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.tab_control = ttk.Notebook(right_frame)
        self.tab_table = ttk.Frame(self.tab_control)
        self.tab_image = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_table, text="📋 Tabela de Elementos")
        self.tab_control.add(self.tab_image, text="🖼️ Visualização com Destaque")
        self.tab_control.pack(fill="both", expand=True)

        # --- Aba da Tabela ---
        table_top = ttk.Frame(self.tab_table)
        table_top.pack(fill="x", pady=5)
        ttk.Button(table_top, text="📤 Exportar Tabela para CSV", command=self.export_table).pack(side="left", padx=5)

        table_container = ttk.Frame(self.tab_table)
        table_container.pack(fill="both", expand=True)

        columns = ("index", "type", "text", "x", "y", "width", "height", "xpath")
        self.element_table = ttk.Treeview(table_container, columns=columns, show="headings", height=25)
        self.element_table.heading("index", text="ID")
        self.element_table.heading("type", text="Tipo")
        self.element_table.heading("text", text="Texto/Valor")
        self.element_table.heading("x", text="X")
        self.element_table.heading("y", text="Y")
        self.element_table.heading("width", text="Largura")
        self.element_table.heading("height", text="Altura")
        self.element_table.heading("xpath", text="XPath")

        for col, width in zip(columns, [50, 100, 180, 60, 60, 80, 80, 300]):
            self.element_table.column(col, width=width, anchor="center" if col in ["index", "x", "y", "width", "height"] else "w")

        v_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.element_table.yview)
        h_scroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.element_table.xview)
        self.element_table.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.element_table.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Destaque ao clicar
        self.element_table.bind("<ButtonRelease-1>", self.on_table_click)

        # --- Aba da Imagem ---
        self.canvas_frame = ttk.Frame(self.tab_image)
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="lightgray")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.resize_image)

    def load_analyses(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not os.path.exists(ANALYSES_DIR):
            messagebox.showwarning("Aviso", f"Pasta '{ANALYSES_DIR}' não encontrada.")
            return

        for domain in os.listdir(ANALYSES_DIR):
            domain_path = os.path.join(ANALYSES_DIR, domain)
            if os.path.isdir(domain_path):
                parent = self.tree.insert("", "end", text=domain, open=False)
                timestamps = sorted([t for t in os.listdir(domain_path) if os.path.isdir(os.path.join(domain_path, t))], reverse=True)
                for ts in timestamps:
                    ts_display = ts.replace("_", " ").replace("-", ":")
                    self.tree.insert(parent, "end", text="", values=(ts_display,), tags=(os.path.join(domain_path, ts),))

    def on_select_analysis(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            return
        analysis_path = tags[0]

        json_path = os.path.join(analysis_path, "estrutura.json")
        image_path = os.path.join(analysis_path, "pagina_anotada.png")

        if not os.path.exists(json_path):
            messagebox.showerror("Erro", "Arquivo estrutura.json não encontrado.")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                elements = json.load(f)
            self.current_elements = elements
            self.load_elements_to_table(elements)
            self.load_image(image_path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar análise: {e}")

    def load_elements_to_table(self, elements):
        for row in self.element_table.get_children():
            self.element_table.delete(row)
        for el in elements:
            self.element_table.insert("", "end", values=(
                el.get("index", ""),
                el.get("type", "unknown"),
                (el.get("text", "") or el.get("value", ""))[:50],
                el.get("x", ""),
                el.get("y", ""),
                el.get("width", ""),
                el.get("height", ""),
                el.get("xpath", "")
            ), tags=(el,))

    def load_image(self, image_path):
        self.canvas.delete("all")
        self.original_image = None
        self.image_tk = None

        if not image_path or not os.path.exists(image_path):
            self.canvas.create_text(100, 50, text="Imagem não disponível", fill="red", anchor="nw")
            return

        try:
            img_cv = cv2.imread(image_path)
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            self.original_image = Image.fromarray(img_rgb)
            self.display_image()
        except Exception as e:
            self.canvas.create_text(100, 50, text=f"Erro ao carregar imagem: {e}", fill="red", anchor="nw")

    def display_image(self):
        self.canvas.delete("all")
        if not self.original_image:
            return

        canvas_width = max(self.canvas.winfo_width(), 100)
        canvas_height = max(self.canvas.winfo_height(), 100)

        img = self.original_image.copy()
        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        self.image_tk = ImageTk.PhotoImage(img)

        self.canvas.create_image(canvas_width // 2, canvas_height // 2, anchor="center", image=self.image_tk)
        self._image_scale = (
            self.original_image.width / img.width,
            self.original_image.height / img.height
        )

    def resize_image(self, event):
        self.display_image()

    def on_table_click(self, event):
        """Destaca o elemento clicado na imagem"""
        selected_item = self.element_table.selection()
        if not selected_item:
            return
        item = self.element_table.item(selected_item[0])
        element_data = item['tags'][0]  # Dados completos do elemento

        x, y, w, h = element_data['x'], element_data['y'], element_data['width'], element_data['height']

        # Converter coordenadas para a imagem redimensionada
        scale_x, scale_y = self._image_scale
        x_img = x / scale_x
        y_img = y / scale_y
        w_img = w / scale_x
        h_img = h / scale_y

        # Redesenha a imagem e destaca o retângulo
        self.display_image()  # Redesenha imagem base
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width = self.original_image.width / scale_x
        img_height = self.original_image.height / scale_y

        # Posição central da imagem
        pad_x = (canvas_width - img_width) // 2
        pad_y = (canvas_height - img_height) // 2

        # Desenha o retângulo destacado
        self.canvas.create_rectangle(
            pad_x + x_img, pad_y + y_img,
            pad_x + x_img + w_img, pad_y + y_img + h_img,
            outline="red", width=3, dash=(4, 2)
        )
        self.canvas.create_text(
            pad_x + x_img, pad_y + y_img - 10,
            text=f"{element_data['type']}",
            fill="red", font=("Arial", 10, "bold"),
            anchor="nw"
        )

    def export_table(self):
        """Exporta a tabela atual para CSV"""
        if not self.current_elements:
            messagebox.showwarning("Aviso", "Nenhum dado para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Salvar tabela como CSV"
        )
        if not file_path:
            return

        try:
            with open(file_path, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Cabeçalho
                writer.writerow(["ID", "Tipo", "Texto/Valor", "X", "Y", "Largura", "Altura", "XPath"])
                # Dados
                for el in self.current_elements:
                    writer.writerow([
                        el.get("index", ""),
                        el.get("type", "unknown"),
                        (el.get("text", "") or el.get("value", "")),
                        el.get("x", ""),
                        el.get("y", ""),
                        el.get("width", ""),
                        el.get("height", ""),
                        el.get("xpath", "")
                    ])
            messagebox.showinfo("Sucesso", f"Tabela exportada com sucesso!\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar CSV:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LocalizacaoDashboard(root)
    root.mainloop()