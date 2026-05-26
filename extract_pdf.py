import sys
try:
    import pypdf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    import pypdf

import os

def extract_pdf(pdf_path, txt_path):
    print(f"Extracting {pdf_path} to {txt_path}...", flush=True)
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Done.", flush=True)

if __name__ == "__main__":
    extract_pdf("Enhancing Small Language Models for Co-Creative Mathematical Storytelling using RAG (1).pdf", "moto.txt")
    extract_pdf(os.path.join("backend", "Story-Based_Mathematics_Grades_1-6.pdf"), "backend_pdf.txt")
