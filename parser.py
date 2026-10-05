import re
import json
import logging
from io import BytesIO
from typing import List, Dict, Any, Tuple, Optional
import openpyxl
from docx import Document

logger = logging.getLogger(__name__)

# Cyrillic lookalike letters to Latin mapping
CYRILLIC_OPT_MAP = {
    "А": "A", "а": "A",
    "В": "B", "в": "B",
    "С": "C", "с": "C",
    "D": "D", "d": "D",
    "Д": "D", "д": "D"
}

DIGIT_OPT_MAP = {
    "1": "A",
    "2": "B",
    "3": "C",
    "4": "D",
    "0": "A"
}

def normalize_correct_option(val: str) -> str:
    """Normalizes answer string to 'A', 'B', 'C', or 'D'."""
    val = (val or "").strip()
    if not val:
        return ""
    
    if val in DIGIT_OPT_MAP:
        return DIGIT_OPT_MAP[val]
    
    first_char = val[0]
    if first_char in CYRILLIC_OPT_MAP:
        first_char = CYRILLIC_OPT_MAP[first_char]
    else:
        first_char = first_char.upper()
        
    if first_char in ["A", "B", "C", "D"]:
        return first_char
        
    m = re.search(r"^[ABCDabcd1-4]", val)
    if m:
        c = m.group(0).upper()
        return DIGIT_OPT_MAP.get(c, c)
        
    return ""

def parse_excel(file_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses questions from an Excel file (.xlsx).
    Handles multi-line question texts (matching questions, poems, formulas) without collapsing lines.
    """
    questions = []
    errors = []
    
    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        
        header_row = None
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            row_str = [str(c).strip().lower() if c is not None else "" for c in row]
            if any("savol" in c or "question" in c for c in row_str):
                header_row = (row_idx, row_str)
                break
                
        if not header_row:
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

            if "question" not in col_map: col_map["question"] = 0
            if "a" not in col_map: col_map["a"] = 1
            if "b" not in col_map: col_map["b"] = 2
            if "c" not in col_map: col_map["c"] = 3
            if "d" not in col_map: col_map["d"] = 4
            if "correct" not in col_map: col_map["correct"] = 5

        for row_idx, row in enumerate(sheet.iter_rows(min_row=start_row, values_only=True), start=start_row):
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
                
            def get_val(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(row) and row[idx] is not None:
                    return str(row[idx]).strip()
                return ""

            q_raw = get_val("question")
            opt_a = get_val("a")
            opt_b = get_val("b")
            opt_c = get_val("c")
            opt_d = get_val("d")
            correct_raw = get_val("correct")
            explanation = get_val("explanation")
            category = get_val("category") or "Umumiy"

            if not q_raw:
                continue

            # Multi-line question processing: preserve newlines, clean tabs, strip leading question index only on line 1
            q_raw = q_raw.replace("\r\n", "\n").replace("\r", "\n").strip()
            q_lines = [re.sub(r"\t+", " ", l).strip() for l in q_raw.split("\n") if l.strip()]
            if q_lines:
                q_lines[0] = re.sub(r"^(?:Savol\s*\d*[\.\:\)]?\s*|\d+[\.\)]\s*)", "", q_lines[0])
                q_text = "\n".join(q_lines).strip()
            else:
                continue

            # Options cleaning
            opt_a = re.sub(r"\t+", " ", opt_a.replace("\r\n", " ").replace("\n", " ")).strip()
            opt_b = re.sub(r"\t+", " ", opt_b.replace("\r\n", " ").replace("\n", " ")).strip()
            opt_c = re.sub(r"\t+", " ", opt_c.replace("\r\n", " ").replace("\n", " ")).strip()
            opt_d = re.sub(r"\t+", " ", opt_d.replace("\r\n", " ").replace("\n", " ")).strip()

            correct = normalize_correct_option(correct_raw)
            if not correct:
                correct = "A"

            if not (opt_a and opt_b and opt_c and opt_d):
                errors.append(f"Qator {row_idx}: Variantlar to'liq emas ('{q_text[:30]}...')")
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

def split_into_question_blocks(text: str) -> List[List[str]]:
    """
    Intelligently splits text into individual question blocks.
    Respects:
    - Multi-line question texts (matching questions, poems, formulas, code snippets).
    - Sub-numbered items (1., 2., 3., 4.).
    - Sub-lettered definitions (a., b., c., d.).
    - Questions with or without empty lines between them.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = [l.strip() for l in text.split("\n")]
    
    # Check if the text contains uppercase options like A), B), C), D)
    has_any_upper_opts = bool(re.search(r"(?m)^[\+\*]?\s*[A-D][\)\.\:]\s+", text))
    
    blocks = []
    current = []
    has_opts = False
    has_ans = False

    for line in raw_lines:
        if not line:
            continue

        is_sep = bool(re.match(r"^(?:===+|---+|___+|###+)\s*$", line))
        is_explicit_q = bool(re.match(r"^(?:Savol|Question|Тест)\s*(?:\d+|№\d+|#\d+)?[\.\:\)]?\s*", line, re.IGNORECASE))
        is_q_num = bool(re.match(r"^\d+[\.\)]\s+", line))

        # A line marks the start of a NEW question if:
        # 1. It is an explicit delimiter (===, ---), OR
        # 2. An explicit "Savol N:" / "Question N:" marker, OR
        # 3. A numbered line (e.g. "32. "), BUT ONLY IF the current question already saw options or an answer!
        if current and (is_sep or ((has_opts or has_ans) and (is_q_num or is_explicit_q))):
            blocks.append(current)
            current = []
            has_opts = False
            has_ans = False
            if is_sep:
                continue

        # Check if line looks like an option:
        if has_any_upper_opts:
            if re.match(r"^[\+\*]?\s*[A-D][\)\.\:]\s+", line):
                has_opts = True
        else:
            if re.match(r"^[\+\*]?\s*[A-Da-d][\)\.\:]\s+", line):
                has_opts = True

        if re.match(r"^(?:Javob|To[\'’`]?g[\'’`]?ri\s*javob|Answer|Correct):", line, re.IGNORECASE):
            has_ans = True

        current.append(line)

    if current:
        blocks.append(current)

    return blocks

def parse_single_question_block(lines: List[str], block_idx: int) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Parses a single question block's lines into structured fields.
    Preserves multi-line questions, sub-numbered items, and lettered definitions intact.
    """
    if not lines:
        return None, []

    # Check if this block has uppercase options A), B), C), D)
    has_upper = any(re.match(r"^[\+\*]?\s*[A-D][\)\.\:]\s+", l) for l in lines)
    
    # If uppercase options exist, ONLY uppercase letters are options. Lowercase a), b), c), d) remain in question text!
    # If no uppercase options exist, lowercase a), b), c), d) can be options.
    if has_upper:
        opt_pattern = r"^([\+\*]?)\s*([A-D])[\)\.\:]\s*(.+)$"
    else:
        opt_pattern = r"^([\+\*]?)\s*([A-Da-d])[\)\.\:]\s*(.+)$"

    q_lines = []
    options = {}
    correct = ""
    explanation = ""
    category = "Umumiy"

    for line in lines:
        clean = line.strip()
        if not clean:
            continue

        # Category marker
        cat_m = re.match(r"^(?:Fan|Fan\s*nomi|Bo[\'’`]?lim|Kategoriya|Category|Mavzu|Subject):\s*(.+)$", clean, re.IGNORECASE)
        if cat_m:
            category = cat_m.group(1).strip()
            continue

        # Explanation marker
        exp_m = re.match(r"^(?:Izoh|Tushuntirish|Explanation):\s*(.+)$", clean, re.IGNORECASE)
        if exp_m:
            explanation = exp_m.group(1).strip()
            continue

        # Answer marker
        ans_m = re.match(r"^(?:Javob|To[\'’`]?g[\'’`]?ri\s*javob|Answer|Correct):\s*(.+)$", clean, re.IGNORECASE)
        if ans_m:
            correct = normalize_correct_option(ans_m.group(1))
            continue

        # Option marker
        opt_m = re.match(opt_pattern, clean)
        if opt_m:
            is_plus = bool(opt_m.group(1))
            raw_letter = opt_m.group(2)
            letter = CYRILLIC_OPT_MAP.get(raw_letter, raw_letter.upper())
            content = opt_m.group(3).strip()
            options[letter] = content
            if is_plus:
                correct = letter
            continue

        # Question text line:
        # If this is the very first line of the question, strip question number (e.g. '31. ')
        # For ALL subsequent lines, PRESERVE numbers and text (e.g. '1. Adaptatsiya', 'a) Ishdan keyingi...')!
        line_clean = re.sub(r"\t+", " ", clean).strip()
        if len(q_lines) == 0:
            line_clean = re.sub(r"^(?:Savol\s*\d*[\.\:\)]?\s*|\d+[\.\)]\s*)", "", line_clean)

        q_lines.append(line_clean)

    q_text = "\n".join(q_lines).strip()

    errors = []
    if not q_text:
        errors.append(f"Blok #{block_idx}: Savol matni topilmadi.")
        return None, errors

    opt_a = options.get("A", "")
    opt_b = options.get("B", "")
    opt_c = options.get("C", "")
    opt_d = options.get("D", "")

    if not (opt_a and opt_b and opt_c and opt_d):
        missing = [k for k in ["A", "B", "C", "D"] if not options.get(k)]
        errors.append(f"Blok #{block_idx}: Variantlar to'liq emas (Yetishmayapti: {', '.join(missing)}). Savol: '{q_text[:30]}...'")
        return None, errors

    if not correct or correct not in ["A", "B", "C", "D"]:
        # If not specified, default to A and log warning so valid question is not rejected
        correct = "A"

    return {
        "question_text": q_text,
        "option_a": opt_a,
        "option_b": opt_b,
        "option_c": opt_c,
        "option_d": opt_d,
        "correct_option": correct,
        "explanation": explanation,
        "category": category
    }, []

def parse_text(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses plain text formatted questions into structured list.
    Supports single questions, matching questions (moslashtirish), poems, multi-item lists, etc.
    """
    questions = []
    errors = []

    blocks = split_into_question_blocks(text)
    for block_idx, block in enumerate(blocks, start=1):
        q_data, block_errors = parse_single_question_block(block, block_idx)
        if q_data:
            questions.append(q_data)
        if block_errors:
            errors.extend(block_errors)

    return questions, errors

def parse_docx(file_bytes: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses questions from a Word document (.docx).
    Supports matching questions, multi-line questions, tables, and standard tests.
    """
    questions = []
    errors = []
    
    try:
        doc = Document(BytesIO(file_bytes))
        lines = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                lines.append(txt)
                
        # Also include table contents
        for table in doc.tables:
            for row in table.rows:
                cell_texts = [re.sub(r"\t+", " ", c.text).strip() for c in row.cells if c.text.strip()]
                unique_cells = []
                for ct in cell_texts:
                    if not unique_cells or ct != unique_cells[-1]:
                        unique_cells.append(ct)
                if unique_cells:
                    lines.append("   ".join(unique_cells))

        full_text = "\n".join(lines)
        return parse_text(full_text)
    except Exception as e:
        logger.error(f"Word docx parse error: {e}")
        errors.append(f"Word faylini o'qishda xatolik: {str(e)}")

    return questions, errors

def parse_json(content_str: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses questions from a JSON string.
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
            q_raw = item.get("question") or item.get("question_text") or item.get("savol") or ""
            q_raw = str(q_raw).replace("\r\n", "\n").replace("\r", "\n").strip()
            
            q_lines = [re.sub(r"\t+", " ", l).strip() for l in q_raw.split("\n") if l.strip()]
            if q_lines:
                q_lines[0] = re.sub(r"^(?:Savol\s*\d*[\.\:\)]?\s*|\d+[\.\)]\s*)", "", q_lines[0])
                q_text = "\n".join(q_lines).strip()
            else:
                continue
            
            options = item.get("options") or item.get("variantlar")
            if isinstance(options, list) and len(options) >= 4:
                opt_a = str(options[0]).strip()
                opt_b = str(options[1]).strip()
                opt_c = str(options[2]).strip()
                opt_d = str(options[3]).strip()
            elif isinstance(options, dict):
                opt_a = str(options.get("A", options.get("a", ""))).strip()
                opt_b = str(options.get("B", options.get("b", ""))).strip()
                opt_c = str(options.get("C", options.get("c", ""))).strip()
                opt_d = str(options.get("D", options.get("d", ""))).strip()
            else:
                opt_a = str(item.get("option_a") or item.get("a") or "").strip()
                opt_b = str(item.get("option_b") or item.get("b") or "").strip()
                opt_c = str(item.get("option_c") or item.get("c") or "").strip()
                opt_d = str(item.get("option_d") or item.get("d") or "").strip()

            correct_raw = str(item.get("correct") or item.get("correct_option") or item.get("javob") or item.get("answer") or "").strip()
            correct = normalize_correct_option(correct_raw)
            if not correct:
                correct = "A"

            explanation = str(item.get("explanation") or item.get("izoh") or "").strip()
            category = str(item.get("category") or item.get("kategoriya") or "Umumiy").strip()

            if not q_text:
                continue

            if not (opt_a and opt_b and opt_c and opt_d):
                errors.append(f"Element #{idx}: 4 ta variant to'liq emas.")
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
