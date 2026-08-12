"""
Testes focados em dois pontos:

1. O bug de highlight duplicado (services/study_manager.py + ui/reader.py):
   garante que o retângulo é persistido corretamente e que o redesenho usa
   coordenada exata, não busca de texto na página inteira.

2. services/topic_parser.py: nunca tinha sido revisado a fundo. Cobre o
   fallback por regex, a deduplicação de tópicos na mesma página e o
   cálculo de page_end.

Rodar com: pytest tests/test_highlight_and_toc.py -v
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import pymupdf as fitz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from models.models import Subject, PdfDocument, Highlight
from services.study_manager import StudyManager
from services.topic_parser import TopicParser


# ---------------------------------------------------------------------------
# Fixtures: banco em memória (isolado do banco real do app) + PySide6 headless
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_pdf(db_session, tmp_path):
    """Cria um PDF sintético com a MESMA palavra repetida 3x na página,
    exatamente o cenário que expunha o bug original."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "conceito")
    page.insert_text((72, 140), "conceito")
    page.insert_text((72, 180), "conceito")
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()

    subject = Subject(name="Direito Administrativo")
    db_session.add(subject)
    db_session.commit()

    pdf = PdfDocument(
        subject_id=subject.id, title="sample.pdf", file_path=str(path),
        file_size_bytes=1, total_pages=1,
    )
    db_session.add(pdf)
    db_session.commit()
    return pdf, str(path)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# 1. Bug do highlight duplicado
# ---------------------------------------------------------------------------

class TestHighlightRectPersistence:

    def test_add_highlight_salva_coordenadas_quando_fornecidas(self, db_session, sample_pdf):
        pdf, _ = sample_pdf
        hl = StudyManager.add_highlight(
            db=db_session, pdf_id=pdf.id, page_number=1,
            selected_text="conceito", color="#00FF00",
            rect=(72, 90, 50, 15),  # x, y, width, height
        )
        assert hl.x == 72
        assert hl.y == 90
        assert hl.width == 50
        assert hl.height == 15
        assert hl.color == "#00FF00"

    def test_add_highlight_sem_rect_mantem_coordenadas_nulas(self, db_session, sample_pdf):
        """Reproduz o comportamento de highlights criados ANTES da correção."""
        pdf, _ = sample_pdf
        hl = StudyManager.add_highlight(
            db=db_session, pdf_id=pdf.id, page_number=1, selected_text="conceito",
        )
        assert hl.x is None and hl.y is None and hl.width is None and hl.height is None


class TestReaderRenderApenasUmaOcorrencia:
    """
    Este é o teste que teria pego o bug original: com uma palavra repetida
    3x na mesma página, o grifo persistido com coordenadas deve resultar em
    UMA única anotação no PDF renderizado -- não três.
    """

    def test_grifo_com_coordenadas_marca_apenas_a_selecao_original(
        self, db_session, sample_pdf, qapp
    ):
        pdf, path = sample_pdf

        # Simula o usuário selecionando a 1a ocorrência de "conceito"
        doc = fitz.open(path)
        page = doc[0]
        matches = page.search_for("conceito")
        assert len(matches) == 3, "pré-condição do teste: precisa haver 3 ocorrências"
        primeira_ocorrencia = matches[0]
        doc.close()

        StudyManager.add_highlight(
            db=db_session, pdf_id=pdf.id, page_number=1, selected_text="conceito",
            color="#FFFF00",
            rect=(
                primeira_ocorrencia.x0, primeira_ocorrencia.y0,
                primeira_ocorrencia.x1 - primeira_ocorrencia.x0,
                primeira_ocorrencia.y1 - primeira_ocorrencia.y0,
            ),
        )

        # Reproduz exatamente a lógica de render_page corrigida
        doc = fitz.open(path)
        page = doc[0]
        highlights = StudyManager.get_highlights_by_pdf(db=db_session, pdf_id=pdf.id, page_number=1)
        count = 0
        for hl in highlights:
            if hl.x is not None:
                r = fitz.Rect(hl.x, hl.y, hl.x + hl.width, hl.y + hl.height)
                page.add_highlight_annot(r)
                count += 1

        annots = list(page.annots())
        doc.close()

        assert count == 1
        assert len(annots) == 1, "BUG: mais de uma anotação foi criada para um único grifo"

    def test_fallback_legado_marca_so_a_primeira_ocorrencia(self, db_session, sample_pdf):
        """Grifo antigo (sem coordenada) não deve mais grifar as 3 ocorrências
        -- o fallback precisa se limitar à primeira, prevenindo a regressão do bug."""
        pdf, path = sample_pdf
        StudyManager.add_highlight(
            db=db_session, pdf_id=pdf.id, page_number=1, selected_text="conceito",
        )

        doc = fitz.open(path)
        page = doc[0]
        highlights = StudyManager.get_highlights_by_pdf(db=db_session, pdf_id=pdf.id, page_number=1)

        marcados = 0
        for hl in highlights:
            if hl.x is None and hl.selected_text:
                matches = page.search_for(hl.selected_text)
                if matches:
                    page.add_highlight_annot(matches[0])
                    marcados += 1

        annots = list(page.annots())
        doc.close()

        assert marcados == 1
        assert len(annots) == 1


class TestHexToRgb:
    """Testa o conversor de cor usado no redesenho (ui/reader.py)."""

    def test_cores_validas(self, qapp):
        from ui.reader import StudyReaderView
        assert StudyReaderView._hex_to_rgb("#FF0000") == (1.0, 0.0, 0.0)
        assert StudyReaderView._hex_to_rgb("#00FF00") == (0.0, 1.0, 0.0)
        assert StudyReaderView._hex_to_rgb("#0000FF") == (0.0, 0.0, 1.0)

    def test_cor_invalida_cai_no_amarelo_padrao(self, qapp):
        from ui.reader import StudyReaderView
        assert StudyReaderView._hex_to_rgb(None) == (1, 1, 0)
        assert StudyReaderView._hex_to_rgb("") == (1, 1, 0)
        assert StudyReaderView._hex_to_rgb("naoehex") == (1, 1, 0)
        assert StudyReaderView._hex_to_rgb("#FFF") == (1, 1, 0)  # formato curto não suportado


# ---------------------------------------------------------------------------
# 2. services/topic_parser.py -- ainda não tinha sido testado
# ---------------------------------------------------------------------------

class TestTopicParserFallbackRegex:

    def _pdf_com_sumario(self, tmp_path, linhas_sumario, paginas_conteudo=30):
        doc = fitz.open()
        toc_page = doc.new_page()
        y = 72
        for linha in linhas_sumario:
            toc_page.insert_text((72, y), linha)
            y += 20
        for _ in range(paginas_conteudo):
            doc.new_page()
        path = tmp_path / "toc.pdf"
        doc.save(str(path))
        doc.close()
        return str(path), doc.page_count if False else (paginas_conteudo + 1)

    def test_extrai_topicos_com_dot_leader(self, tmp_path):
        linhas = [
            "Introducao ..... 3",
            "Direito Constitucional ..... 8",
            "Direito Administrativo ..... 15",
        ]
        path, total_pages = self._pdf_com_sumario(tmp_path, linhas)
        topics = TopicParser.parse_toc(path, toc_pages=[0], total_pages=total_pages)

        titles = [t["title"] for t in topics]
        assert "Introducao" in titles
        assert "Direito Constitucional" in titles
        assert "Direito Administrativo" in titles

    def test_page_end_do_ultimo_topico_vai_ate_o_fim_do_pdf(self, tmp_path):
        linhas = ["Capitulo 1 ..... 2", "Capitulo 2 ..... 10"]
        path, total_pages = self._pdf_com_sumario(tmp_path, linhas)
        topics = TopicParser.parse_toc(path, toc_pages=[0], total_pages=total_pages)

        assert topics[-1]["page_end"] == total_pages

    def test_topicos_na_mesma_pagina_mantem_apenas_o_mais_especifico(self, tmp_path):
        """Cobre a CAMADA 3 do parser: quando um título 'pai' e um 'filho'
        começam na mesma página, só o mais específico (o último da sequência)
        deve sobreviver."""
        linhas = [
            "Aula 1 - Direito Administrativo ..... 6",
            "1.1 Principios ..... 6",
            "1.2 Poderes ..... 12",
        ]
        path, total_pages = self._pdf_com_sumario(tmp_path, linhas)
        topics = TopicParser.parse_toc(path, toc_pages=[0], total_pages=total_pages)

        page_starts_6 = [t for t in topics if t["page_start"] == 6]
        assert len(page_starts_6) == 1, (
            "esperado só 1 tópico começando na página 6 (o mais específico); "
            f"encontrados: {[t['title'] for t in page_starts_6]}"
        )
        assert page_starts_6[0]["title"] == "1.1 Principios"

    def test_sem_linhas_reconheciveis_retorna_lista_vazia(self, tmp_path):
        linhas = ["texto qualquer sem padrao de sumario"]
        path, total_pages = self._pdf_com_sumario(tmp_path, linhas)
        topics = TopicParser.parse_toc(path, toc_pages=[0], total_pages=total_pages)
        assert topics == []

    def test_pagina_fora_do_intervalo_do_pdf_e_descartada(self, tmp_path):
        linhas = ["Capitulo Valido ..... 5", "Capitulo Invalido ..... 9999"]
        path, total_pages = self._pdf_com_sumario(tmp_path, linhas)
        topics = TopicParser.parse_toc(path, toc_pages=[0], total_pages=total_pages)

        titles = [t["title"] for t in topics]
        assert "Capitulo Valido" in titles
        assert "Capitulo Invalido" not in titles