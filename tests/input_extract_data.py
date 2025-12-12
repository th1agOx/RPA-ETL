from robot.core.pdf_reader import pdf_path_to_text
from robot.core.parser import extract_from_text
import json

if __name__ == "__main__":
    pdf_path = r"C:/_repos_/saas/base-test/nacional_NFS_tests/NFS-E_amigao.pdf"

    text = pdf_path_to_text(pdf_path)
    result = extract_from_text(text)

    print(result)

    print("\n--- JSON payload ---\n")
    print(json.dumps(result.dict(), indent=2, ensure_ascii=False))