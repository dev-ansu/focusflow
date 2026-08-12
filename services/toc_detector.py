from pathlib import Path
import re
from typing import List, Tuple, Union
import fitz  # PyMuPDF

from config.app import config


class TOCDetector:
    KEYWORDS = [
        "sumário",
        "sumario",
        "índice",
        "indice",
        "conteúdo",
        "conteudo",
        "tópicos",
        "topicos",
    ]

    @classmethod
    def detect_toc_pages(
        cls, file_path: Union[str, Path]
    ) -> Tuple[List[int], int]:
        """
        Detecta e calcula a pontuação de confiança das páginas do PDF que contêm o sumário/índice.
        Retorna uma tupla: (lista de índices de páginas 0-based, nível de confiança de 0 a 100).
        """
        path = Path(file_path)

        if not path.exists():
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] PDF não encontrado em: {path}"
                )
            return [], 0

        try:
            doc = fitz.open(path)
        except Exception as e:
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] Erro ao abrir PDF para detecção de sumário '{path.name}': {e}"
                )
            return [], 0

        try:
            max_search = min(20, len(doc))
            candidates = []

            for i in range(max_search):
                page_text = doc[i].get_text("text").lower()

                # Caso a página seja imagem escaneada sem OCR, pula a análise de texto
                if not page_text.strip():
                    continue

                score = 0

                # Pontuação por Palavras-Chave de Sumários
                for kw in cls.KEYWORDS:
                    if kw in page_text:
                        score += 40

                # Pontuação por linhas com pontilhados/traços terminadas em números
                lines_with_dots_and_nums = len(
                    re.findall(r"(\.\.\.|…|\-{3,})\s*\d+", page_text)
                )
                score += min(lines_with_dots_and_nums * 5, 40)

                # Pontuação por numeração de capítulos/tópicos (ex: "1.2 Título")
                numbered_patterns = len(
                    re.findall(
                        r"^\s*\d+(\.\d+)*\s+[a-zA-Z]", page_text, re.MULTILINE
                    )
                )
                score += min(numbered_patterns * 3, 20)

                if score > 20:
                    candidates.append((i, score))

            if not candidates:
                return [], 0

            # Ordena por pontuação e seleciona as 3 melhores páginas
            candidates.sort(key=lambda x: x[1], reverse=True)
            toc_pages = sorted([p[0] for p in candidates[:3]])
            confidence = min(100, max([p[1] for p in candidates]))

            return toc_pages, confidence

        finally:
            doc.close()