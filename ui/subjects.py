import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QLabel, QInputDialog, QMessageBox, QTreeWidget, 
                             QTreeWidgetItem, QFileDialog, QHeaderView, QFrame)
from PySide6.QtCore import Qt
import pymupdf as fitz
from database.connection import SessionLocal
from models.models import Subject, Topic, StudyBlock, BlockStatus, PdfDocument


class SubjectView(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_subject_id = None
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # --- COLUNA ESQUERDA: LISTA DE MATÉRIAS ---
        left_layout = QVBoxLayout()
        
        lbl_subj_title = QLabel("📚 Matérias")
        lbl_subj_title.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        left_layout.addWidget(lbl_subj_title)
        
        self.list_subjects = QListWidget()
        self.list_subjects.setStyleSheet("""
            QListWidget {
                background-color: #1E222A;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 8px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2C3E50;
            }
            QListWidget::item:hover {
                background-color: #2C3E50;
            }
            QListWidget::item:selected {
                background-color: #34495E;
                color: #3498DB;
                font-weight: bold;
            }
        """)
        self.list_subjects.itemClicked.connect(self.on_subject_selected)
        left_layout.addWidget(self.list_subjects)

        # Botões de Ação para Matérias
        btn_add_subject = QPushButton("➕ Nova Matéria")
        btn_add_subject.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        btn_add_subject.setCursor(Qt.PointingHandCursor)
        btn_add_subject.clicked.connect(self.add_subject)
        left_layout.addWidget(btn_add_subject)

        btn_delete_subject = QPushButton("❌ Apagar Matéria")
        btn_delete_subject.setStyleSheet("""
            QPushButton {
                background-color: #8E44AD;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #732D91; }
        """)
        btn_delete_subject.setCursor(Qt.PointingHandCursor)
        btn_delete_subject.clicked.connect(self.delete_selected_subject)
        left_layout.addWidget(btn_delete_subject)

        layout.addLayout(left_layout, stretch=1)

        # --- COLUNA DIREITA: TÓPICOS E PDFs DA MATÉRIA ---
        right_layout = QVBoxLayout()
        
        self.lbl_title = QLabel("<h3>Selecione uma matéria</h3>")
        self.lbl_title.setStyleSheet("color: #FFFFFF; font-size: 18px;")
        right_layout.addWidget(self.lbl_title)

        self.tree_topics = QTreeWidget()
        self.tree_topics.setHeaderLabels(["Tópico / Bloco", "Status / Páginas"])
        self.tree_topics.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_topics.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree_topics.setStyleSheet("""
            QTreeWidget {
                background-color: #1E222A;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 8px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px;
            }
            QTreeWidget::item:hover {
                background-color: #2C3E50;
            }
            QTreeWidget::item:selected {
                background-color: #34495E;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #2C3E50;
                color: #BDC3C7;
                font-weight: bold;
                padding: 6px;
                border: none;
            }
        """)
        right_layout.addWidget(self.tree_topics)

        # --- BARRA DE AÇÕES DA MATÉRIA / TÓPICOS ---
        action_layout = QHBoxLayout()

        btn_import_pdf = QPushButton("📄 Importar PDF e Gerar Blocos")
        btn_import_pdf.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71;
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #27AE60; }
        """)
        btn_import_pdf.setCursor(Qt.PointingHandCursor)
        btn_import_pdf.clicked.connect(self.import_pdf_and_generate_blocks)
        action_layout.addWidget(btn_import_pdf)

        btn_delete_topic = QPushButton("🗑️ Apagar Tópico")
        btn_delete_topic.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        btn_delete_topic.setCursor(Qt.PointingHandCursor)
        btn_delete_topic.clicked.connect(self.delete_selected_topic)
        action_layout.addWidget(btn_delete_topic)

        btn_reset_progress = QPushButton("🔄 Zerar Progresso")
        btn_reset_progress.setStyleSheet("""
            QPushButton {
                background-color: #E67E22;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #D35400; }
        """)
        btn_reset_progress.setCursor(Qt.PointingHandCursor)
        btn_reset_progress.clicked.connect(self.reset_subject_progress)
        action_layout.addWidget(btn_reset_progress)

        right_layout.addLayout(action_layout)
        layout.addLayout(right_layout, stretch=2.5)

        self.refresh()

    def refresh(self):
        self.list_subjects.clear()
        self.tree_topics.clear()
        self.lbl_title.setText("<b style='color: #BDC3C7;'>Selecione uma matéria na lista à esquerda</b>")
        self.selected_subject_id = None
        
        db = SessionLocal()
        subjects = db.query(Subject).all()
        for s in subjects:
            item = QListWidgetItem(f"{s.name}")
            item.setData(Qt.UserRole, s.id)
            self.list_subjects.addItem(item)
        db.close()

    def add_subject(self):
        text, ok = QInputDialog.getText(self, "Nova Matéria", "Nome da Matéria:")
        if ok and text.strip():
            db = SessionLocal()
            try:
                new_subj = Subject(name=text.strip())
                db.add(new_subj)
                db.commit()
                self.refresh()
            except Exception:
                QMessageBox.warning(self, "Erro", "A matéria já existe ou ocorreu um erro.")
            finally:
                db.close()

    def delete_selected_subject(self):
        if not self.selected_subject_id:
            QMessageBox.warning(self, "Aviso", "Selecione uma matéria na lista para apagar.")
            return

        db = SessionLocal()
        subj = db.query(Subject).filter(Subject.id == self.selected_subject_id).first()
        if not subj:
            db.close()
            return

        confirm = QMessageBox.question(
            self, "ATENÇÃO - Excluir Matéria", 
            f"Tem certeza que deseja apagar a matéria '{subj.name}'?\n\n"
            f"Isso apagará DEFINITIVAMENTE todos os tópicos, PDFs vinculados e o histórico de estudos desta matéria.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                all_topics = (
                    db.query(Topic)
                    .join(PdfDocument)
                    .filter(PdfDocument.subject_id == self.selected_subject_id)
                    .all()
                )
                topic_ids = [t.id for t in all_topics]

                if topic_ids:
                    db.query(StudyBlock).filter(StudyBlock.topic_id.in_(topic_ids)).delete(synchronize_session=False)
                    db.query(Topic).filter(Topic.id.in_(topic_ids)).delete(synchronize_session=False)

                db.query(PdfDocument).filter(PdfDocument.subject_id == self.selected_subject_id).delete(synchronize_session=False)
                db.query(Subject).filter(Subject.id == self.selected_subject_id).delete(synchronize_session=False)
                
                db.commit()
                QMessageBox.information(self, "Sucesso", "Matéria e todos os seus dados foram excluídos com sucesso.")
                self.refresh()
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Erro", f"Falha ao excluir matéria: {str(e)}")
            finally:
                db.close()

    def on_subject_selected(self, item):
        subj_id = item.data(Qt.UserRole)
        self.selected_subject_id = subj_id
        self.load_topics(subj_id)

    def load_topics(self, subject_id):
        self.tree_topics.clear()
        db = SessionLocal()
        subj = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subj:
            db.close()
            return

        self.lbl_title.setText(f"<b style='color: #3498DB;'>{subj.name}</b> <span style='color: #BDC3C7;'>- Tópicos e PDFs</span>")

        topics = (
            db.query(Topic)
            .join(PdfDocument)
            .filter(PdfDocument.subject_id == subject_id, Topic.parent_id.is_(None))
            .all()
        )
        
        def add_nodes(parent_item, topic_list):
            for t in topic_list:
                item = QTreeWidgetItem([f"🔖 {t.title}", ""])
                item.setData(0, Qt.UserRole, t.id)
                
                blocks = db.query(StudyBlock).filter(StudyBlock.topic_id == t.id).order_by(StudyBlock.page_start.asc()).all()
                if blocks:
                    for b in blocks:
                        page_start = getattr(b, 'page_start', getattr(b, 'start_page', 1))
                        page_end = getattr(b, 'page_end', getattr(b, 'end_page', 1))
                        
                        status_str = "⏳ Pendente"
                        if b.status == BlockStatus.EM_ANDAMENTO:
                            status_str = "▶️ Em Andamento"
                        elif b.status == BlockStatus.CONCLUIDO:
                            status_str = "✅ Concluído"

                        block_item = QTreeWidgetItem([f"   ↳ Bloco (Págs {page_start} - {page_end})", status_str])
                        item.addChild(block_item)

                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.tree_topics.addTopLevelItem(item)

                subtopics = db.query(Topic).filter(Topic.parent_id == t.id).all()
                if subtopics:
                    add_nodes(item, subtopics)

        add_nodes(None, topics)
        self.tree_topics.expandAll()
        db.close()

    def import_pdf_and_generate_blocks(self):
        """Permite importar um arquivo PDF e subdividi-lo automaticamente em blocos de estudo."""
        if not self.selected_subject_id:
            QMessageBox.warning(self, "Aviso", "Selecione uma matéria na lista para importar o PDF.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar PDF de Estudo", "", "Arquivos PDF (*.pdf)")
        if not file_path:
            return

        pages_per_block, ok = QInputDialog.getInt(self, "Divisão do Bloco", "Tamanho da meta em páginas (ex: 10 ou 15 págs por bloco):", 15, 1, 100)
        if not ok:
            return

        db = SessionLocal()
        try:
            filename = os.path.basename(file_path)
            topic_title = os.path.splitext(filename)[0]
            
            # 1. Obtém o tamanho do arquivo em bytes
            file_size_bytes = os.path.getsize(file_path)

            # 2. Abre o PDF para contar páginas reais
            doc = fitz.open(file_path)
            total_pages = len(doc)
            doc.close()

            # 3. Registra o Documento PDF
            pdf_doc = PdfDocument(
                subject_id=self.selected_subject_id,
                title=topic_title,
                file_path=file_path, 
                file_size_bytes=file_size_bytes,
                total_pages=total_pages
            )
            db.add(pdf_doc)
            db.flush()

            # 4. Cria o Tópico Principal vinculado ao PDF (com page_start e page_end)
            topic = Topic(
                pdf_id=pdf_doc.id, 
                title=topic_title,
                page_start=1,
                page_end=total_pages
            )
            db.add(topic)
            db.flush()

            # 5. Gera os blocos de estudo sequenciais
            start_p = 1
            while start_p <= total_pages:
                end_p = min(start_p + pages_per_block - 1, total_pages)
                block = StudyBlock(
                    topic_id=topic.id,
                    page_start=start_p,
                    page_end=end_p,
                    current_page=start_p,
                    status=BlockStatus.PENDENTE
                )
                db.add(block)
                start_p = end_p + 1

            db.commit()
            QMessageBox.information(
                self, 
                "PDF Importado", 
                f"PDF '{filename}' importado com sucesso!\n"
                f"• Total de páginas: {total_pages}\n"
                f"• Blocos gerados: {((total_pages - 1) // pages_per_block) + 1}"
            )
            self.load_topics(self.selected_subject_id)
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao importar PDF: {str(e)}")
        finally:
            db.close()

    def delete_selected_topic(self):
        current_item = self.tree_topics.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Aviso", "Selecione um tópico para apagar.")
            return

        topic_id = current_item.data(0, Qt.UserRole)
        if not topic_id:
            QMessageBox.warning(self, "Aviso", "Selecione um tópico principal para apagar (não um bloco).")
            return

        confirm = QMessageBox.question(
            self, "Confirmar Exclusão", 
            "Tem certeza que deseja apagar este tópico e todos os seus blocos associados?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                def recursive_delete(t_id):
                    subtopics = db.query(Topic).filter(Topic.parent_id == t_id).all()
                    for sub in subtopics:
                        recursive_delete(sub.id)
                    
                    db.query(StudyBlock).filter(StudyBlock.topic_id == t_id).delete()
                    db.query(Topic).filter(Topic.id == t_id).delete()

                recursive_delete(topic_id)
                db.commit()
                self.load_topics(self.selected_subject_id)
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Erro", f"Falha ao apagar tópico: {str(e)}")
            finally:
                db.close()

    def reset_subject_progress(self):
        if not self.selected_subject_id:
            QMessageBox.warning(self, "Aviso", "Selecione uma matéria primeiro.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar Reinício", 
            "Isso voltará todos os blocos desta matéria para o status 'PENDENTE' e resetará os tempos. Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            db = SessionLocal()
            try:
                blocks = (
                    db.query(StudyBlock)
                    .join(Topic)
                    .join(PdfDocument)
                    .filter(PdfDocument.subject_id == self.selected_subject_id)
                    .all()
                )
                for b in blocks:
                    b.status = BlockStatus.PENDENTE
                    start_p = getattr(b, 'page_start', getattr(b, 'start_page', 1))
                    b.current_page = start_p
                db.commit()
                QMessageBox.information(self, "Sucesso", "Progresso da matéria zerado com sucesso!")
                self.load_topics(self.selected_subject_id)
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Erro", f"Falha ao zerar progresso: {str(e)}")
            finally:
                db.close()