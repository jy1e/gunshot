import os
import docx
import pdfplumber

def parse_docx(filepath):
    doc = docx.Document(filepath)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def parse_pdf(filepath):
    with pdfplumber.open(filepath) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        return text

def parse_txt(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return text

def parse_file(filepath):
    _, ext = os.path.splitext(filepath)
    if ext == ".docx":
        return parse_docx(filepath)
    elif ext == ".pdf":
        return parse_pdf(filepath)
    elif ext == ".txt":
        return parse_txt(filepath)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {ext}")