import pymupdf as fitz

def extract_page_chars(page):
    """Extrai caracteres com bounding boxes preservando espaços naturais."""
    raw = page.get_text("rawdict")
    lines = []
    
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
            
        for line in block.get("lines", []):
            chars = []
            for span in line.get("spans", []):
                span_chars = span.get("chars", [])
                for i, ch in enumerate(span_chars):
                    chars.append({
                        "c": ch["c"],
                        "bbox": ch["bbox"]
                    })
                    if i < len(span_chars) - 1:
                        next_x0 = span_chars[i + 1]["bbox"][0]
                        curr_x1 = ch["bbox"][2]
                        if next_x0 - curr_x1 > (ch["bbox"][2] - ch["bbox"][0]) * 0.25:
                            space_bbox = (curr_x1, ch["bbox"][1], next_x0, ch["bbox"][3])
                            chars.append({"c": " ", "bbox": space_bbox})
            if chars:
                lines.append(chars)
    return lines

def flatten_chars(lines):
    flat = []
    for line_idx, chars in enumerate(lines):
        for ch in chars:
            flat.append({"line": line_idx, **ch})
    return flat

def nearest_char_flat_index(flat_chars, pdf_point):
    """Encontra o caractere mais próximo usando a menor distância euclidiana da bounding box."""
    if not flat_chars:
        return None
        
    px, py = pdf_point.x, pdf_point.y
    best_idx = 0
    min_dist_sq = float("inf")

    for idx, ch in enumerate(flat_chars):
        x0, y0, x1, y1 = ch["bbox"]
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        
        dy = max(0, y0 - py) if py < y0 else (max(0, py - y1) if py > y1 else 0)
        dx = max(0, x0 - px) if px < x0 else (max(0, px - x1) if px > x1 else 0)
        
        dist_sq = (dx * dx) + (dy * dy * 4.0)
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_idx = idx

    return best_idx

def build_selection_segments(flat_chars, anchor_idx, focus_idx):
    """Cria os retângulos de highlight ajustados por linha e consolida o texto de forma bidirecional."""
    if anchor_idx is None or focus_idx is None or not flat_chars:
        return [], ""

    lo, hi = sorted((anchor_idx, focus_idx))
    selected = flat_chars[lo:hi + 1]
    if not selected:
        return [], ""

    selected = sorted(selected, key=lambda c: (c["line"], c["bbox"][0]))

    segments = []
    text_parts = []
    current_line = selected[0]["line"]
    line_chars = []

    def flush():
        if not line_chars:
            return
        non_space = [c for c in line_chars if c["c"] != " "]
        if not non_space:
            return
            
        x0 = min(c["bbox"][0] for c in non_space)
        y0 = min(c["bbox"][1] for c in non_space)
        x1 = max(c["bbox"][2] for c in non_space)
        y1 = max(c["bbox"][3] for c in non_space)
        
        segments.append(fitz.Rect(x0, y0, x1, y1))
        line_text = "".join(c["c"] for c in line_chars)
        text_parts.append(line_text)

    for ch in selected:
        if ch["line"] != current_line:
            flush()
            line_chars = []
            current_line = ch["line"]
        line_chars.append(ch)
    flush()

    raw_text = "\n".join(text_parts)
    clean_text = "\n".join(" ".join(line.split()) for line in raw_text.splitlines() if line.strip())
    return segments, clean_text