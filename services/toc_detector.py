import pymupdf as fitz
import re

class TOCDetector:
    KEYWORDS = ["sumário", "sumario", "índice", "indice", "conteúdo", "conteudo", "tópicos", "topicos"]

    @classmethod
    def detect_toc_pages(cls, file_path: str):
        doc = fitz.open(file_path)
        max_search = min(20, len(doc))
        candidates = []

        for i in range(max_search):
            page_text = doc[i].get_text("text").lower()
            score = 0

            for kw in cls.KEYWORDS:
                if kw in page_text:
                    score += 40
            
            # Conta correspondências de padrões como "1.1 Titulo ... 12" ou "Sintaxe 15"
            lines_with_dots_and_nums = len(re.findall(r'(\.\.\.|…|\-{3,})\s*\d+', page_text))
            score += min(lines_with_dots_and_nums * 5, 40)

            numbered_patterns = len(re.findall(r'^\s*\d+(\.\d+)*\s+[a-zA-z]', page_text, re.MULTILINE))
            score += min(numbered_patterns * 3, 20)

            if score > 20:
                candidates.append((i, score))

        doc.close()

        if not candidates:
            return [], 0

        candidates.sort(key=lambda x: x[1], reverse=True)
        toc_pages = sorted([p[0] for p in candidates[:3]])
        confidence = min(100, max([p[1] for p in candidates]))
        return toc_pages, confidence