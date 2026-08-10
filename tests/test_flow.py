import pytest
import os
import fitz
from database.connection import Base, engine, SessionLocal
from models.models import Subject, PdfDocument, Topic, StudyBlock, BlockStatus
from services.study_manager import StudyManager

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_complete_flow(setup_db):
    db = setup_db
    
    # 1. Criar Matéria
    subject = Subject(name="Português Teste")
    db.add(subject)
    db.commit()
    assert subject.id is not None

    # 2. Criar PDF Simulado
    pdf = PdfDocument(
        subject_id=subject.id,
        title="Aula 01.pdf",
        file_path="/tmp/fake.pdf",
        file_size_bytes=1024,
        total_pages=50
    )
    db.add(pdf)
    db.commit()

    # 3. Criar Tópicos e Blocos
    topic = Topic(pdf_id=pdf.id, title="Sintaxe", page_start=1, page_end=30)
    db.add(topic)
    db.commit()

    StudyManager.create_blocks_for_topic(db, topic.id, mode="pages", pages_per_block=15)

    blocks = db.query(StudyBlock).filter(StudyBlock.topic_id == topic.id).all()
    assert len(blocks) == 2  # Págs 1-15 e 16-30

    # 4. Próximo Bloco ("Continuar onde parou")
    next_b = StudyManager.get_next_block_to_study(db)
    assert next_b.id == blocks[0].id

    # 5. Atualizar Progresso
    StudyManager.update_progress(db, next_b.id, current_page=10, seconds_added=120)
    assert next_b.current_page == 10
    assert next_b.status == BlockStatus.EM_ANDAMENTO

    # 6. Concluir Bloco
    StudyManager.update_progress(db, next_b.id, current_page=15, complete=True)
    assert next_b.status == BlockStatus.CONCLUIDO

    # 7. Avanço Automático
    next_b_2 = StudyManager.get_next_block_to_study(db)
    assert next_b_2.id == blocks[1].id
