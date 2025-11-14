from fpdf import FPDF
import PyPDF2
import re

# === CONFIG ===
INPUT_PDF = "kanji_vocabulaire.pdf"
OUTPUT_PDF = "vocabulaire_organise.pdf"
DOCUMENT_TITLE = "📘 Vocabulaire Japonais Organisé"

# === 1. EXTRACTION TEXTE DU PDF ===
def extraire_texte_pdf(pdf_path):
    texte = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            texte += page.extract_text() + "\n"
    return texte

# === 2. EXTRACTION MOTS (kanji, lecture, fr) ===
def extraire_mots(texte):
    """
    Suppose que les mots suivent un format simple :
    漢字（かんじ）：traduction
    """
    pattern = r"(\S+)[（(](.+?)[)）][:：]\s*(.+)"
    mots = re.findall(pattern, texte)
    result = []
    seen = set()
    for k, l, f in mots:
        if k not in seen:
            result.append({"kanji": k, "lecture": l, "fr": f})
            seen.add(k)
    return result

# === 3. GENERATION PDF ORGANISE ===
def generer_pdf(mots, title=DOCUMENT_TITLE):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("NotoSansJP", "", r"C:\Windows\Fonts\NotoSansJP-VF.ttf", uni=True)
    pdf.set_font("NotoSansJP", "", 16)
    
    # Titre
    pdf.cell(0, 12, title, ln=True, align="C")
    pdf.ln(5)
    
    # Liste des mots
    pdf.set_font("NotoSansJP", "", 14)
    for i, mot in enumerate(mots, 1):
        ligne = f"{i}. {mot['kanji']}（{mot['lecture']}）：{mot['fr']}"
        pdf.multi_cell(0, 8, ligne)
        pdf.ln(1)
    
    pdf.output(OUTPUT_PDF)
    print(f"✅ PDF organisé généré : {OUTPUT_PDF}")

# === 4. PIPELINE ===
def main():
    texte = extraire_texte_pdf(INPUT_PDF)
    mots = extraire_mots(texte)
    generer_pdf(mots)

if __name__ == "__main__":
    main()
