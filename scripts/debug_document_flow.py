from robot.pdf_reader import pdf_bytes_to_text
from robot.core.text_normalizer import normalize_text
from robot.core.parser import extract_from_text
from pprint import pprint

PDF_PATH = "C:/_repos_/saas/base-test/nacional_NFS_tests/NFS-E_Quinta_do_Bosque.pdf"

with open(PDF_PATH, "rb") as f:
    pdf_bytes = f.read()

# 1. Extração literal
raw_result = pdf_bytes_to_text(pdf_bytes)

print("\n================ RAW TEXT ================\n")
print(raw_result[:3000])  # corta para não explodir o terminal

# 2. Normalização
normalized_text = normalize_text(raw_result.text) 

print("\n================ NORMALIZED TEXT ================\n")
print(normalized_text[:3000])

# 3. Parser completo
parsed = extract_from_text(normalized_text)

print("\n================ PARSER OUTPUT ================\n")
pprint(parsed)