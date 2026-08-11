import pymupdf as fitz
import re

class TopicParser:
    @classmethod
    def parse_toc(cls, file_path: str, toc_pages: list[int], total_pages: int):
        try:
            doc = fitz.open(file_path)
        except Exception:
            return cls._generate_fallback_topics(total_pages)

        raw_topics = []

        # --- CAMADA 1: Bookmarks Nativos ---
        try:
            native_toc = doc.get_toc(simple=True)
            if native_toc:
                for item in native_toc:
                    title = item[1].strip()
                    page_start = item[2]
                    if 1 <= page_start <= total_pages and len(title) > 2:
                        raw_topics.append({
                            "title": title,
                            "page_start": page_start
                        })
        except Exception:
            pass

        # --- CAMADA 2: Regex nas Páginas do Sumário Detectado ---
        if not raw_topics and toc_pages:
            raw_lines = []
            for p in toc_pages:
                if p < len(doc):
                    text = doc[p].get_text("text")
                    raw_lines.extend(text.splitlines())

            pattern = re.compile(r'^\s*(.*?)\s*[\.\s…\-]+\s*(\d+)\s*$')

            for line in raw_lines:
                line = line.strip()
                if not line:
                    continue
                match = pattern.match(line)
                if match:
                    title = match.group(1).strip()
                    page_start = int(match.group(2))
                    
                    if len(title) > 2 and 1 <= page_start <= total_pages:
                        raw_topics.append({
                            "title": title,
                            "page_start": page_start
                        })

        doc.close()

        # --- CAMADA 3: Fallback Inteligente caso falhem as camadas 1 e 2 ---
        if not raw_topics:
            return cls._generate_fallback_topics(total_pages)

        # --- Processamento Normal de Sobreposição e Cálculo de page_end ---
        cleaned_topics = []
        for i in range(len(raw_topics)):
            curr = raw_topics[i]
            if i < len(raw_topics) - 1:
                nxt = raw_topics[i + 1]
                if curr["page_start"] == nxt["page_start"]:
                    continue
            cleaned_topics.append(curr)

        final_topics = []
        for i in range(len(cleaned_topics)):
            curr_title = cleaned_topics[i]["title"]
            curr_start = cleaned_topics[i]["page_start"]

            if i < len(cleaned_topics) - 1:
                next_start = cleaned_topics[i + 1]["page_start"]
                curr_end = max(curr_start, next_start - 1)
            else:
                curr_end = total_pages

            final_topics.append({
                "title": curr_title,
                "page_start": curr_start,
                "page_end": curr_end
            })

        return final_topics

    @staticmethod
    def _generate_fallback_topics(total_pages: int, chunk_size: int = 15) -> list[dict]:
        """
        Gera tópicos genéricos baseados em blocos de páginas caso o PDF seja escaneado
        ou não tenha estrutura de sumário extraível.
        """
        if total_pages <= 0:
            return [{"title": "Leitura Completa", "page_start": 1, "page_end": 1}]

        topics = []
        part = 1
        
        for start in range(1, total_pages + 1, chunk_size):
            end = min(start + chunk_size - 1, total_pages)
            topics.append({
                "title": f"Parte {part} (Págs. {start}-{end})",
                "page_start": start,
                "page_end": end
            })
            part += 1

        return topics