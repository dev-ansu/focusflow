import pymupdf as fitz
import re

class TopicParser:
    @staticmethod
    def parse_toc(file_path: str, toc_pages: list[int], total_pages: int):
        doc = fitz.open(file_path)
        raw_topics = []

        # -------------------------------------------------------------
        # CAMADA 1: Tenta ler o índice NATIVO (Bookmarks do PDF)
        # -------------------------------------------------------------
        native_toc = doc.get_toc(simple=True)  # Retorna [level, title, page]
        if native_toc:
            for item in native_toc:
                title = item[1].strip()
                page_start = item[2]
                if 1 <= page_start <= total_pages and len(title) > 2:
                    raw_topics.append({
                        "title": title,
                        "page_start": page_start
                    })

        # -------------------------------------------------------------
        # CAMADA 2: Fallback por Regex (se não houver bookmarks nativos)
        # -------------------------------------------------------------
        if not raw_topics:
            raw_lines = []
            for p in toc_pages:
                if p < len(doc):
                    text = doc[p].get_text("text")
                    raw_lines.extend(text.splitlines())

            # Regex universal: Captura "Título ..... Páginas" ou "Título 15"
            pattern = re.compile(r'^\s*(.*?)\s*[\.\s…\-]+\s*(\d+)\s*$')

            for line in raw_lines:
                line = line.strip()
                if not line:
                    continue
                match = pattern.match(line)
                if match:
                    title = match.group(1).strip()
                    page_start = int(match.group(2))
                    
                    # Descarta linhas do tipo "Página" isolada ou fora do limite do PDF
                    if len(title) > 2 and 1 <= page_start <= total_pages:
                        raw_topics.append({
                            "title": title,
                            "page_start": page_start
                        })

        doc.close()

        if not raw_topics:
            return []

        # -------------------------------------------------------------
        # CAMADA 3: Tratamento de Hierarquia e Sobreposição de Páginas
        # -------------------------------------------------------------
        # Remove redundâncias de tópicos "pai" que começam exatamente na mesma página
        # que um tópico "filho" (Ex: Aula na pág 6 e Subtópico 1 na pág 6).
        cleaned_topics = []
        for i in range(len(raw_topics)):
            curr = raw_topics[i]
            
            # Se não for o último, verifica se o próximo começa na MESMA página
            if i < len(raw_topics) - 1:
                nxt = raw_topics[i + 1]
                # Se o próximo tem o mesmo page_start, o atual é apenas um Título de Capítulo
                # Mantemos o próximo por ser o subtópico específico
                if curr["page_start"] == nxt["page_start"]:
                    continue

            cleaned_topics.append(curr)

        # -------------------------------------------------------------
        # CAMADA 4: Cálculo do page_end Dinâmico
        # -------------------------------------------------------------
        final_topics = []
        for i in range(len(cleaned_topics)):
            curr_title = cleaned_topics[i]["title"]
            curr_start = cleaned_topics[i]["page_start"]

            if i < len(cleaned_topics) - 1:
                next_start = cleaned_topics[i + 1]["page_start"]
                # Garante que page_end seja ao menos igual ao page_start
                curr_end = max(curr_start, next_start - 1)
            else:
                # O último tópico vai até o final do PDF
                curr_end = total_pages

            final_topics.append({
                "title": curr_title,
                "page_start": curr_start,
                "page_end": curr_end
            })

        return final_topics