# generate_pdf.py
from fpdf import FPDF
import os

def create_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Configurações de fonte
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Documentação Completa do Projeto: Analizador Web Icaro", ln=True, align='C')
    pdf.ln(10)

    # Visão Geral
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Visão Geral", ln=True)
    pdf.set_font("Arial", '', 12)
    overview = (
        "Este projeto é uma solução completa de análise, automação e visualização de páginas web, projetada para:\n"
        "- Realizar web scraping generalista em qualquer página.\n"
        "- Automatizar o login em sistemas como o Icaro (icaro.eslcloud.com.br).\n"
        "- Salvar análises com timeline por domínio e data.\n"
        "- Visualizar a localização dos elementos (posição e XPath).\n"
        "- Oferecer uma interface gráfica (GUI) para uso intuitivo."
    )
    pdf.multi_cell(0, 7, overview)
    pdf.ln(5)

    # Adicione as demais seções da documentação aqui...
    # (Para brevidade, o código completo com todas as seções está no arquivo final)

    # Salva o PDF
    pdf.output("Documentacao_Analizador_Web_Icaro.pdf")
    print("✅ PDF gerado com sucesso: Documentacao_Analizador_Web_Icaro.pdf")

if __name__ == "__main__":
    create_pdf()