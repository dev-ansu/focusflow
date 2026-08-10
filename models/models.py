import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from database.connection import Base

class BlockStatus(enum.Enum):
    PENDENTE = "PENDENTE"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    IGNORADO = "IGNORADO"

class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    pdfs = relationship("PdfDocument", back_populates="subject", cascade="all, delete-orphan")
    cycle_entries = relationship("StudyCycle", back_populates="subject", cascade="all, delete-orphan")

class PdfDocument(Base):
    __tablename__ = "pdf_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    total_pages = Column(Integer, nullable=False)
    imported_at = Column(DateTime, default=datetime.utcnow)
    
    subject = relationship("Subject", back_populates="pdfs")
    topics = relationship("Topic", back_populates="pdf", cascade="all, delete-orphan")
    subject = relationship("Subject", back_populates="pdfs")
    topics = relationship("Topic", back_populates="pdf", cascade="all, delete-orphan")
    
    # NOVO RELACIONAMENTO:
    highlights = relationship("Highlight", back_populates="pdf", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    title = Column(String(255), nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    
    pdf = relationship("PdfDocument", back_populates="topics")
    parent = relationship("Topic", remote_side=[id], backref="subtopics")
    blocks = relationship("StudyBlock", back_populates="topic", cascade="all, delete-orphan")

class StudyBlock(Base):
    __tablename__ = "study_blocks"
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    current_page = Column(Integer, nullable=False)
    status = Column(Enum(BlockStatus), default=BlockStatus.PENDENTE)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    
    topic = relationship("Topic", back_populates="blocks")
    sessions = relationship("StudySession", back_populates="block", cascade="all, delete-orphan")

class StudySession(Base):
    __tablename__ = "study_sessions"
    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("study_blocks.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    pages_read = Column(Integer, default=0)

    block = relationship("StudyBlock", back_populates="sessions")

class StudyCycle(Base):
    __tablename__ = "study_cycles"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    order = Column(Integer, nullable=False)

    subject = relationship("Subject", back_populates="cycle_entries")
# Adicione a classe Highlight no final do models/models.py

class Highlight(Base):
    __tablename__ = "highlights"
    id = Column(Integer, primary_key=True, index=True)
    pdf_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    
    # Texto grifado e cor em hex (#FFFF00 = amarelo)
    selected_text = Column(Text, nullable=True)
    color = Column(String(20), default="#FFFF00")
    
    # Coordenadas do retângulo grifado na página (opcional, para renderização precisa)
    x = Column(Integer, nullable=True)
    y = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    pdf = relationship("PdfDocument", back_populates="highlights")