import re
import json
import logging
from io import BytesIO
from typing import List, Dict, Any, Tuple
import openpyxl
from docx import Document

logger = logging.getLogger(__name__)

def parse_excel(file_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses questions from an Excel file (.xlsx).
    Expected columns (case-insensitive, flexible):
    - Savol / Question / Savol matni
    - Variant A / A / A varianti
    - Variant B / B / B varianti
    - Variant C / C / C varianti
    - Variant D / D / D varianti
    - To'g'ri javob / Javob / Correct / To'g'ri (A, B, C, D or 1, 2, 3, 4)
    - Izoh / Explanation (optional)
    - Kategoriya / Category (optional)
    """
    questions = []
    errors = []
    
    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        
        # Determine header indices
        header_row = None
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            row_str = [str(c).strip().lower() if c is not None else "" for c in row]
            # Check if this row looks like a header
            if any("savol" in c or "question" in c for c in row_str):
                header_row = (row_idx, row_str)
                break
                
        if not header_row:
            # If no obvious header, assume standard column order:
            # Col 0: Savol, Col 1: A, Col 2: B, Col 3: C, Col 4: D, Col 5: Javob, Col 6: Izoh
            start_row = 1
            col_map = {"question": 0, "a": 1, "b": 2, "c": 3, "d": 4, "correct": 5, "explanation": 6, "category": 7}
        else:
            start_row = header_row[0] + 1
            row_str = header_row[1]
            col_map = {}
            for idx, val in enumerate(row_str):
                if "savol" in val or "question" in val:
                    col_map["question"] = idx
                elif val in ["a", "variant a", "var a", "a varianti"]:
                    col_map["a"] = idx
                elif val in ["b", "variant b", "var b", "b varianti"]:
                    col_map["b"] = idx
                elif val in ["c", "variant c", "var c", "c varianti"]:
                    col_map["c"] = idx
                elif val in ["d", "variant d", "var d", "d varianti"]:
                    col_map["d"] = idx
                elif "javob" in val or "correct" in val or "to'g'ri" in val or "togri" in val:
                    col_map["correct"] = idx
                elif "izoh" in val or "explanation" in val:
                    col_map["explanation"] = idx
                elif "kategoriya" in val or "category" in val or "bo'lim" in val or "bolim" in val or "fan" in val or "mavzu" in val or "subject" in val:
                    col_map["category"] = idx

            # Fallbacks if columns missing
            if "question" not in col_map: col_map["question"] = 0
            if "a" not in col_map: col_map["a"] = 1
            if "b" not in col_map: col_map["b"] = 2
            if "c" not in col_map: col_map["c"] = 3
            if "d" not in col_map: col_map["d"] = 4
            if "correct" not in col_map: col_map["correct"] = 5

        # Read rows
        for row_idx, row in enumerate(sheet.iter_rows(min_row=start_row, values_only=True), start=start_row):
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
                
            def get_val(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(row) and row[idx] is not None:
                    return str(row[idx]).strip()
                return ""

            q_text = get_val("question")
            opt_a = get_val("a")
            opt_b = get_val("b")
            opt_c = get_val("c")
            opt_d = get_val("d")
            correct = get_val("correct").upper()
            explanation = get_val("explanation")
            category = get_val("category") or "Umumiy"

            # Normalize correct option (e.g. 1 -> A, 2 -> B, 3 -> C, 4 -> D)
            digit_map = {"1": "A", "2": "B", "3": "C", "4": "D"}
            if correct in digit_map:
                correct = digit_map[correct]
            
            # If formatted like "A)" or "A." or "B) Variant", extract first letter
            if len(correct) > 1:
                match = re.search(r"^[ABCD]", correct)
                if match:
                    correct = match.group(0)

            if not q_text:
                continue

            if not (opt_a and opt_b and opt_c and opt_d):
                errors.append(f"Qator {row_idx}: Variantlar to'liq emas ('{q_text[:30]}...')")
                continue

            if correct not in ["A", "B", "C", "D"]:
                errors.append(f"Qator {row_idx}: To'g'ri javob noaniq ('{correct}'). A, B, C yoki D bo'lishi kerak.")
                continue

            questions.append({
                "question_text": q_text,
                "option_a": opt_a,
                "option_b": opt_b,
                "option_c": opt_c,
                "option_d": opt_d,
                "correct_option": correct,
                "explanation": explanation,
                "category": category
            })
            
    except Exception as e:
        logger.error(f"Excel parse error: {e}")
        errors.append(f"Excel faylini o'qishda xatolik: {str(e)}")

    return questions, errors

def parse_docx(file_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses questions from a Word document (.docx).
    Supports format:
    1. Savol matni
    A) Variant 1
    B) Variant 2
    C) Variant 3
    D) Variant 4
    Javob: B
    Izoh: Izoh matni (ixtiyoriy)
    """
    questions = []
    errors = []
    
    try:
        doc = Document(BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # Also include any table rows if present
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        full_text = "\n".join(paragraphs)
        parsed_q, p_errors = parse_text(full_text)
        questions.extend(parsed_q)
        errors.extend(p_errors)
    except Exception as e:
        logger.error(f"Word docx parse error: {e}")
        errors.append(f"Word faylini o'qishda xatolik: {str(e)}")

    return questions, errors

def parse_json(content_str: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses questions from a JSON string.
    Expected formats:
    [
      {
        "question": "...",
        "option_a": "...",
        "option_b": "...",
        "option_c": "...",
        "option_d": "...",
        "correct": "A" or 0,
        "explanation": "..."
      },
      ...
    ]
    or with "options": ["A", "B", "C", "D"]
    """
    questions = []
    errors = []
    
    try:
        data = json.loads(content_str)
        if isinstance(data, dict):
            if "questions" in data and isinstance(data["questions"], list):
                data = data["questions"]
            elif "tests" in data and isinstance(data["tests"], list):
                data = data["tests"]
            else:
                data = [data]
                
        if not isinstance(data, list):
            errors.append("JSON formati massiv (array) bo'lishi kerak.")
            return questions, errors

        for idx, item in enumerate(data, start=1):
            q_text = item.get("question") or item.get("question_text") or item.get("savol") or ""
            q_text = str(q_text).strip()
            
            # Check options
            options = item.get("options") or item.get("variantlar")
            if isinstance(options, list) and len(options) >= 4:
                opt_a = str(options[0]).strip()
                opt_b = str(options[1]).strip()
                opt_c = str(options[2]).strip()
                opt_d = str(options[3]).strip()
            else:
                opt_a = str(item.get("option_a") or item.get("a") or "").strip()
                opt_b = str(item.get("option_b") or item.get("b") or "").strip()
                opt_c = str(item.get("option_c") or item.get("c") or "").strip()
                opt_d = str(item.get("option_d") or item.get("d") or "").strip()

            correct = str(item.get("correct") or item.get("correct_option") or item.get("javob") or item.get("answer") or "").strip().upper()
            digit_map = {"0": "A", "1": "B", "2": "C", "3": "D", "1": "A", "2": "B", "3": "C", "4": "D"}
            if correct in digit_map:
                correct = digit_map[correct]

            if len(correct) > 1:
                m = re.search(r"^[ABCD]", correct)
                if m:
                    correct = m.group(0)

            explanation = str(item.get("explanation") or item.get("izoh") or "").strip()
            category = str(item.get("category") or item.get("kategoriya") or "Umumiy").strip()

            if not q_text:
                continue

            if not (opt_a and opt_b and opt_c and opt_d):
                errors.append(f"Element #{idx}: 4 ta variant to'liq emas.")
                continue

            if correct not in ["A", "B", "C", "D"]:
                errors.append(f"Element #{idx}: To'g'ri javob 'A', 'B', 'C' yoki 'D' bo'lishi kerak.")
                continue

            questions.append({
                "question_text": q_text,
                "option_a": opt_a,
                "option_b": opt_b,
                "option_c": opt_c,
                "option_d": opt_d,
                "correct_option": correct,
                "explanation": explanation,
                "category": category
            })
    except Exception as e:
        logger.error(f"JSON parse error: {e}")
        errors.append(f"JSON faylini tahlil qilishda xatolik: {str(e)}")

    return questions, errors

def parse_text(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses plain text formatted questions.
    Example:
    1. O'zbekiston poytaxti qaysi shahar?
    A) Samarqand
    B) Toshkent
    C) Buxoro
    D) Xiva
    Javob: B
    Izoh: Toshkent O'zbekistonning poytaxti.
    
    Also supports '+' marking correct option:
    A) Samarqand
    +B) Toshkent
    C) Buxoro
    D) Xiva
    """
    questions = []
    errors = []
    
    # Split text into question blocks based on empty lines or question numbers
    raw_blocks = re.split(r"\n\s*\n+", text.strip())
    
    # If blocks were not separated by double newline, try regex split on question numbers
    if len(raw_blocks) <= 1 and "\n" in text:
        # Check if lines start with numbers like "1.", "2."
        splits = re.split(r"(?m)^(?=\d+[\.\)])", text)
        if len(splits) > 1:
            raw_blocks = [s.strip() for s in splits if s.strip()]

    for block_idx, block in enumerate(raw_blocks, start=1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        q_text = ""
        opt_a = ""
        opt_b = ""
        opt_c = ""
        opt_d = ""
        correct = ""
        explanation = ""
        category = "Umumiy"

        # Check lines
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            
            # Check for question start
            if idx == 0 or (not q_text and not re.match(r"^[\+\*\-]?[A-Da-d][\)\.]", line)):
                # Strip leading numbers e.g. "1. " or "1) "
                cleaned_q = re.sub(r"^\d+[\.\)]\s*", "", line)
                if q_text:
                    q_text += " " + cleaned_q
                else:
                    q_text = cleaned_q
                idx += 1
                continue

            # Check for answer marker e.g. "Javob: B" or "To'g'ri javob: C"
            ans_match = re.match(r"^(?:Javob|To'?g'?ri\s*javob|Answer|Correct):\s*([A-Da-d1-4])", line, re.IGNORECASE)
            if ans_match:
                correct = ans_match.group(1).upper()
                idx += 1
                continue

            # Check for explanation
            exp_match = re.match(r"^(?:Izoh|Tushuntirish|Explanation):\s*(.+)$", line, re.IGNORECASE)
            if exp_match:
                explanation = exp_match.group(1).strip()
                idx += 1
                continue

            # Check for category / fan
            cat_match = re.match(r"^(?:Fan|Fan\s*nomi|Kategoriya|Category|Mavzu|Subject):\s*(.+)$", line, re.IGNORECASE)
            if cat_match:
                category = cat_match.group(1).strip()
                idx += 1
                continue

            # Check for options A), B), C), D) or +A), +B) etc.
            opt_match = re.match(r"^([\+\*]?)\s*([A-Da-d])[\)\.]\s*(.+)$", line)
            if opt_match:
                is_marked_correct = bool(opt_match.group(1))
                letter = opt_match.group(2).upper()
                content = opt_match.group(3).strip()

                if letter == "A":
                    opt_a = content
                    if is_marked_correct: correct = "A"
                elif letter == "B":
                    opt_b = content
                    if is_marked_correct: correct = "B"
                elif letter == "C":
                    opt_c = content
                    if is_marked_correct: correct = "C"
                elif letter == "D":
                    opt_d = content
                    if is_marked_correct: correct = "D"
                idx += 1
                continue

            # If inside question or explanation
            if opt_d and not correct:
                # Could be answer or explanation continuation
                pass
            elif not opt_a:
                q_text += " " + line

            idx += 1

        # Normalize correct
        digit_map = {"1": "A", "2": "B", "3": "C", "4": "D"}
        if correct in digit_map:
            correct = digit_map[correct]

        if not q_text:
            continue

        if not (opt_a and opt_b and opt_c and opt_d):
            errors.append(f"Blok #{block_idx}: Savol yoki variantlar to'liq emas ('{q_text[:25]}...').")
            continue

        if correct not in ["A", "B", "C", "D"]:
            errors.append(f"Blok #{block_idx}: To'g'ri javob topilmadi ('{q_text[:25]}...'). 'Javob: A' deb ko'rsating.")
            continue

        questions.append({
            "question_text": q_text,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
            "option_d": opt_d,
            "correct_option": correct,
            "explanation": explanation,
            "category": category
        })

    return questions, errors

def parse_file(filename: str, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Auto-detects file type by extension and parses questions.
    """
    ext = filename.lower().split(".")[-1]
    if ext in ["xlsx", "xls"]:
        return parse_excel(file_bytes)
    elif ext in ["docx"]:
        return parse_docx(file_bytes)
    elif ext in ["json"]:
        try:
            content_str = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_str = file_bytes.decode("latin-1")
        return parse_json(content_str)
    elif ext in ["txt", "text"]:
        try:
            content_str = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_str = file_bytes.decode("latin-1")
        return parse_text(content_str)
    else:
        return [], [f"Qo'llab-quvvatlanmaydigan fayl formati: .{ext}. (.xlsx, .docx, .json, .txt fayllardan foydalaning)"]
