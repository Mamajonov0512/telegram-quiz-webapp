from pathlib import Path
from parser import parse_file

def test_file_parsers():
    samples_dir = Path("samples")
    
    # 1. Excel
    xlsx_path = samples_dir / "test_shablon.xlsx"
    with open(xlsx_path, "rb") as f:
        q_excel, err_excel = parse_file("test_shablon.xlsx", f.read())
    assert len(q_excel) == 10, f"Expected 10 questions from Excel, got {len(q_excel)}"
    assert len(err_excel) == 0, f"Excel errors: {err_excel}"
    print(f"[+] Excel (.xlsx) muvaffaqiyatli tahlil qilindi: {len(q_excel)} ta savol")

    # 2. JSON
    json_path = samples_dir / "test_shablon.json"
    with open(json_path, "rb") as f:
        q_json, err_json = parse_file("test_shablon.json", f.read())
    assert len(q_json) == 10, f"Expected 10 questions from JSON, got {len(q_json)}"
    assert len(err_json) == 0, f"JSON errors: {err_json}"
    print(f"[+] JSON (.json) muvaffaqiyatli tahlil qilindi: {len(q_json)} ta savol")

    # 3. TXT
    txt_path = samples_dir / "test_shablon.txt"
    with open(txt_path, "rb") as f:
        q_txt, err_txt = parse_file("test_shablon.txt", f.read())
    assert len(q_txt) == 10, f"Expected 10 questions from TXT, got {len(q_txt)}"
    assert len(err_txt) == 0, f"TXT errors: {err_txt}"
    print(f"[+] Matn (.txt) muvaffaqiyatli tahlil qilindi: {len(q_txt)} ta savol")

    print("[OK] Barcha fayl formatlari to'liq ishlayapti!")

if __name__ == "__main__":
    test_file_parsers()
