from pathlib import Path
from typing import Any, Dict, Union
import fitz  # PyMuPDF

from config.app import config


class PDFParser:

    @staticmethod
    def get_info(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Retorna metadados básicos do arquivo PDF (título, caminho, tamanho e número de páginas)."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        try:
            doc = fitz.open(path)
            size = path.stat().st_size
            pages = len(doc)
            doc.close()

            return {
                "title": path.name,
                "file_path": str(path.resolve()),
                "size_bytes": size,
                "pages": pages,
            }
        except Exception as e:
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] Erro ao ler informações do PDF '{path.name}': {e}"
                )
            raise e

    @staticmethod
    def extract_text_from_page(
        file_path: Union[str, Path], page_num: int
    ) -> str:
        """Extrai o texto contido em uma página específica do PDF (índice 0-based)."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        try:
            doc = fitz.open(path)
            text = (
                doc[page_num].get_text("text") if page_num < len(doc) else ""
            )
            doc.close()
            return text
        except Exception as e:
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] Erro ao extrair texto da página {page_num}: {e}"
                )
            return ""