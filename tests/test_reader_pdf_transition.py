import os
import uuid
import pytest
from PySide6.QtCore import Qt

from database.connection import SessionLocal
from models.models import Subject, PdfDocument, Topic, StudyBlock
from services.study_manager import StudyManager
from ui.reader import StudyReaderView


def create_minimal_pdf(file_path):
    """Gera um arquivo PDF válido e minimalista de 30 páginas para o teste."""
    # Estrutura básica de um PDF sintaticamente válido de 30 páginas
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj <>/Pages 2 0 R>> endobj\n"
        b"2 0 obj <>/Count 30/Kids["
    )
    # Adiciona referências para 30 páginas falsas
    for i in range(3, 33):
        pdf_content += f"{i} 0 R ".encode()
    pdf_content += (
        b"]>> endobj\n"
    )
    for i in range(3, 33):
        pdf_content += f"{i} 0 obj <>/MediaBox[0 0 612 792]>> endobj\n".encode()
    
    pdf_content += (
        b"xref\n"
        b"0 33\n"
        b"0000000000 65535 f \n"
        b"trailer <>/Size 33>>\n"
        b"startxref\n"
        b"10\n"
        b"%%EOF"
    )

    with open(file_path, "wb") as f:
        f.write(pdf_content)


@pytest.fixture
def setup_database_with_two_pdfs(tmp_path):
    """Cria matéria, 2 PDFs válidos fictícios, tópicos e blocos no BD para o teste."""
    db = SessionLocal()
    
    # 1. Cria Matéria com nome único
    unique_name = f"Língua Portuguesa Teste {uuid.uuid4().hex[:6]}"
    subject = Subject(name=unique_name)
    db.add(subject)
    db.flush()

    # 2. Cria arquivos PDF válidos no diretório temporário do Pytest
    pdf1_path = str(tmp_path / "pdf1_morfologia.pdf")
    pdf2_path = str(tmp_path / "pdf2_sintaxe.pdf")
    
    create_minimal_pdf(pdf1_path)
    create_minimal_pdf(pdf2_path)

    # 3. PDF 1 - Morfologia
    doc1 = PdfDocument(
        subject_id=subject.id,
        title="Morfologia",
        file_path=pdf1_path,
        file_size_bytes=1024,
        total_pages=30
    )
    db.add(doc1)
    db.flush()

    topic1 = Topic(pdf_id=doc1.id, title="Morfologia Geral", page_start=1, page_end=30)
    db.add(topic1)
    db.flush()

    # Gera blocos para o PDF 1
    StudyManager.create_blocks_for_topic(db, topic1.id, mode="pages", pages_per_block=15)

    # 4. PDF 2 - Sintaxe
    doc2 = PdfDocument(
        subject_id=subject.id,
        title="Sintaxe",
        file_path=pdf2_path,
        file_size_bytes=1024,
        total_pages=30
    )
    db.add(doc2)
    db.flush()

    topic2 = Topic(pdf_id=doc2.id, title="Sintaxe Geral", page_start=1, page_end=30)
    db.add(topic2)
    db.flush()

    # Gera blocos para o PDF 2
    StudyManager.create_blocks_for_topic(db, topic2.id, mode="pages", pages_per_block=15)

    db.commit()

    # Recupera os blocos gerados para este teste
    blocks = (
        db.query(StudyBlock)
        .join(Topic, StudyBlock.topic_id == Topic.id)
        .filter(Topic.pdf_id.in_([doc1.id, doc2.id]))
        .order_by(StudyBlock.id)
        .all()
    )
    db.close()

    return {
        "pdf1_path": pdf1_path,
        "pdf2_path": pdf2_path,
        "blocks": blocks
    }


def test_transition_between_pdfs_on_block_completion(qtbot, setup_database_with_two_pdfs):
    """
    Testa se ao terminar o último bloco do PDF 1, o carregamento do próximo 
    bloco altera com sucesso o PDF aberto para o PDF 2.
    """
    data = setup_database_with_two_pdfs
    blocks = data["blocks"]

    # Instancia a tela do leitor
    reader = StudyReaderView()
    qtbot.addWidget(reader)

    # 1. Carrega o último bloco do PDF 1 (Bloco 2)
    last_block_pdf1 = blocks[1]
    reader.load_block(last_block_pdf1.id)

    # Verifica se o PDF carregado atualmente é o PDF 1 (Morfologia)
    assert reader.current_pdf_path == data["pdf1_path"]

    # 2. Simula a transição para o primeiro bloco do PDF 2 (Sintaxe)
    first_block_pdf2 = blocks[2]
    reader.load_block(first_block_pdf2.id)

    # 3. VALIDAÇÃO: O leitor DEVE ter trocado o arquivo aberto para o PDF 2
    assert reader.current_pdf_path == data["pdf2_path"]
    assert reader.current_pdf_path != data["pdf1_path"]