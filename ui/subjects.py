import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QTreeWidget, 
    QTreeWidgetItem, QFileDialog, QHeaderView, QAbstractItemView,
    QDialog, QTextEdit, QComboBox, QFrame
)
from PySide6.QtCore import Qt, Signal
import pymupdf as fitz
from sqlalchemy.orm import joinedload, subqueryload

from database.connection import SessionLocal
from models.models import Subject, Topic, StudyBlock, BlockStatus, PdfDocument
from services.pdf_parser import PDFParser


class NotesPreviewDialog(QDialog):
    """Janela Modal para preview e exportação das anotações em Markdown ou TXT."""
    def __init__(self, subject_name, content_md, content_txt, parent=None):
        super().__init__(parent)
        self.subject_name = subject_name
        self.content_md = content_md
        self.content_txt = content_txt

        self.setWindowTitle(f"Preview das Anotações - {subject_name}")
        self.resize(750, 550)
        self.setStyleSheet("""
            QDialog { background-color: #1E1E2E; color: #CDD6F4; }
            QLabel { color: #CDD6F4; font-size: 13px; }
            QComboBox { 
                background-color: #181825; 
                color: #CDD6F4; 
                border: 1px solid #313244; 
                border-radius: 6px; 
                padding: 6px 10px; 
            }
            QTextEdit { 
                background-color: #181825; 
                color: #CDD6F4; 
                border: 1px solid #313244; 
                border-radius: 8px; 
                font-family: 'Cascadia Code', 'Consolas', monospace; 
                font-size: 13px; 
            }
        """)

        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        lbl_info = QLabel("<b>Visualização Prévia das Anotações:</b>")
        lbl_info.setStyleSheet("font-size: 14px; color: #89B4FA;")
        top_layout.addWidget(lbl_info)
        top_layout.addStretch()

        lbl_format = QLabel("Formato:")
        top_layout.addWidget(lbl_format)

        self.combo_format = QComboBox()
        self.combo_format.addItems(["Markdown (.md)", "Texto Puro (.txt)"])
        self.combo_format.currentIndexChanged.connect(self.update_preview_content)
        top_layout.addWidget(self.combo_format)

        layout.addLayout(top_layout)

        self.txt_preview = QTextEdit()
        layout.addWidget(self.txt_preview)

        bottom_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton { background-color: #313244; color: #CDD6F4; padding: 8px 16px; border-radius: 6px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #45475A; }
        """)
        btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(btn_cancel)

        bottom_layout.addStretch()

        btn_save = QPushButton("💾 Salvar em Disco")
        btn_save.setStyleSheet("""
            QPushButton { background-color: #A6E3A1; color: #11111B; padding: 8px 16px; border-radius: 6px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #94E2D5; }
        """)
        btn_save.clicked.connect(self.save_file)
        bottom_layout.addWidget(btn_save)

        layout.addLayout(bottom_layout)
        self.update_preview_content()

    def update_preview_content(self):
        if self.combo_format.currentIndex() == 0:
            self.txt_preview.setPlainText(self.content_md)
        else:
            self.txt_preview.setPlainText(self.content_txt)

    def save_file(self):
        is_md = self.combo_format.currentIndex() == 0
        ext_filter = "Markdown (*.md)" if is_md else "Arquivo de Texto (*.txt)"
        default_ext = ".md" if is_md else ".txt"
        default_name = f"Anotacoes_{self.subject_name.replace(' ', '_')}{default_ext}"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Anotações", default_name, f"{ext_filter};;Todos os Arquivos (*.*)"
        )

        if not file_path:
            return

        content_to_save = self.content_md if is_md else self.content_txt

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content_to_save)
            QMessageBox.information(self, "Sucesso", f"Anotações salvas em:\n{file_path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{str(e)}")


class OrderableTreeWidget(QTreeWidget):
    """QTreeWidget customizado que detecta a soltura de itens para salvar a nova ordem no DB."""
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent_view.save_topics_order()


class SubjectView(QWidget):
    # 📡 Sinal enviado para abrir a sessão de estudo no leitor
    start_study_signal = Signal(int)

    def __init__(self):
        super().__init__()
        self.selected_subject_id = None
        self.init_ui()

    def init_ui(self):
        # Estilo Global da View de Matérias
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            /* Lista de Matérias */
            QListWidget {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 8px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #2A2B3D;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #313244;
            }
            QListWidget::item:selected {
                background-color: #45475A;
                color: #89B4FA;
                font-weight: bold;
            }
            /* Árvore de Tópicos */
            QTreeWidget {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 8px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #313244;
            }
            QTreeWidget::item:selected {
                background-color: #45475A;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #1E1E2E;
                color: #A6ADC8;
                font-weight: bold;
                padding: 6px 10px;
                border: none;
                border-bottom: 1px solid #313244;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # --- COLUNA ESQUERDA: LISTA DE MATÉRIAS ---
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        lbl_subj_title = QLabel("📚 Matérias")
        lbl_subj_title.setStyleSheet("color: #89B4FA; font-size: 18px; font-weight: bold;")
        left_layout.addWidget(lbl_subj_title)
        
        self.list_subjects = QListWidget()
        self.list_subjects.itemClicked.connect(self.on_subject_selected)
        left_layout.addWidget(self.list_subjects)

        left_btn_layout = QHBoxLayout()
        left_btn_layout.setSpacing(8)

        btn_add_subject = QPushButton("➕ Nova")
        btn_add_subject.setStyleSheet("""
            QPushButton { background-color: #313244; color: #89B4FA; font-weight: bold; padding: 8px; border-radius: 6px; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; color: #B4BEFE; }
        """)
        btn_add_subject.setCursor(Qt.PointingHandCursor)
        btn_add_subject.clicked.connect(self.add_subject)
        left_btn_layout.addWidget(btn_add_subject)

        btn_delete_subject = QPushButton("❌ Excluir")
        btn_delete_subject.setStyleSheet("""
            QPushButton { background-color: #313244; color: #F38BA8; font-weight: bold; padding: 8px; border-radius: 6px; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; }
        """)
        btn_delete_subject.setCursor(Qt.PointingHandCursor)
        btn_delete_subject.clicked.connect(self.delete_selected_subject)
        left_btn_layout.addWidget(btn_delete_subject)

        left_layout.addLayout(left_btn_layout)
        layout.addLayout(left_layout, stretch=1)

        # --- COLUNA DIREITA: TÓPICOS E PDFs DA MATÉRIA ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        
        self.lbl_title = QLabel("Selecione uma matéria")
        self.lbl_title.setStyleSheet("color: #CDD6F4; font-size: 18px; font-weight: bold;")
        right_layout.addWidget(self.lbl_title)

        self.tree_topics = OrderableTreeWidget(self)
        self.tree_topics.setHeaderLabels(["Tópico / Bloco", "Status / Páginas"])
        self.tree_topics.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_topics.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        self.tree_topics.setDragEnabled(True)
        self.tree_topics.setAcceptDrops(True)
        self.tree_topics.setDropIndicatorShown(True)
        self.tree_topics.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree_topics.itemDoubleClicked.connect(self.on_item_double_clicked)

        right_layout.addWidget(self.tree_topics)

        # --- BARRA INFERIOR DE AÇÕES UNIFICADA ---
        action_frame = QFrame()
        action_frame.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px;
            }
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                font-weight: 500;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #45475A;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45475A;
            }
        """)
        
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(8, 6, 8, 6)
        action_layout.setSpacing(8)

        # 1. Ação Principal (Destaque)
        btn_start_study = QPushButton("▶️ Estudar Bloco")
        btn_start_study.setStyleSheet("""
            QPushButton {
                background-color: #A6E3A1;
                color: #11111B;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #94E2D5; }
        """)
        btn_start_study.setCursor(Qt.PointingHandCursor)
        btn_start_study.clicked.connect(self.start_study_selected)
        action_layout.addWidget(btn_start_study)

        action_layout.addSpacing(6)

        # 2. Reordenação e Edição
        btn_move_up = QPushButton("⬆️")
        btn_move_up.setToolTip("Mover Tópico para Cima")
        btn_move_up.setFixedWidth(36)
        btn_move_up.setCursor(Qt.PointingHandCursor)
        btn_move_up.clicked.connect(lambda: self.move_topic(-1))
        action_layout.addWidget(btn_move_up)

        btn_move_down = QPushButton("⬇️")
        btn_move_down.setToolTip("Mover Tópico para Baixo")
        btn_move_down.setFixedWidth(36)
        btn_move_down.setCursor(Qt.PointingHandCursor)
        btn_move_down.clicked.connect(lambda: self.move_topic(1))
        action_layout.addWidget(btn_move_down)

        btn_import_pdf = QPushButton("📄 Importar PDF")
        btn_import_pdf.setCursor(Qt.PointingHandCursor)
        btn_import_pdf.clicked.connect(self.import_pdf_and_generate_blocks)
        action_layout.addWidget(btn_import_pdf)

        btn_delete_topic = QPushButton("🗑️ Apagar")
        btn_delete_topic.setToolTip("Apagar Tópico Selecionado")
        btn_delete_topic.setStyleSheet("""
            QPushButton { background-color: #313244; color: #F38BA8; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; }
        """)
        btn_delete_topic.setCursor(Qt.PointingHandCursor)
        btn_delete_topic.clicked.connect(self.delete_selected_topic)
        action_layout.addWidget(btn_delete_topic)

        action_layout.addStretch()

        # 3. Ferramentas Adicionais
        btn_export_notes = QPushButton("📝 Resumo / Anotações")
        btn_export_notes.setStyleSheet("""
            QPushButton { background-color: #313244; color: #CBA6F7; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; }
        """)
        btn_export_notes.setCursor(Qt.PointingHandCursor)
        btn_export_notes.clicked.connect(self.export_notes)
        action_layout.addWidget(btn_export_notes)

        btn_reset_progress = QPushButton("🔄 Zerar")
        btn_reset_progress.setToolTip("Zerar todo o progresso desta matéria")
        btn_reset_progress.setStyleSheet("""
            QPushButton { background-color: #313244; color: #FAB387; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; }
        """)
        btn_reset_progress.setCursor(Qt.PointingHandCursor)
        btn_reset_progress.clicked.connect(self.reset_subject_progress)
        action_layout.addWidget(btn_reset_progress)

        right_layout.addWidget(action_frame)
        layout.addLayout(right_layout, stretch=2.5)

        self.refresh()

    def start_study_selected(self):
        """Inicia a sessão de estudo para o bloco selecionado ou o primeiro bloco do tópico."""
        current_item = self.tree_topics.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Aviso", "Selecione um tópico ou bloco para iniciar o estudo.")
            return

        item_type = current_item.data(0, Qt.UserRole + 1)
        
        if item_type == "BLOCK":
            block_id = current_item.data(0, Qt.UserRole)
            if block_id:
                self.start_study_signal.emit(block_id)
        elif item_type == "TOPIC":
            topic_id = current_item.data(0, Qt.UserRole)
            db = SessionLocal()
            block = db.query(StudyBlock).filter(
                StudyBlock.topic_id == topic_id,
                StudyBlock.status != BlockStatus.IGNORADO
            ).order_by(StudyBlock.page_start.asc()).first()
            db.close()

            if block:
                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(self, "Aviso", "Não há blocos de estudo disponíveis para este tópico.")

    def on_item_double_clicked(self, item, column):
        """Ação ao dar dois cliques em um item da árvore."""
        self.start_study_selected()

    def load_topics(self, subject_id):
        """Carrega todos os tópicos e subtópicos em uma única consulta otimizada."""
        self.tree_topics.clear()
        db = SessionLocal()
        subj = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subj:
            db.close()
            return

        self.lbl_title.setText(f"<span style='color: #89B4FA;'>{subj.name}</span> <span style='color: #A6ADC8; font-size: 14px;'>(Tópicos e Materiais)</span>")

        all_topics = (
            db.query(Topic)
            .join(PdfDocument)
            .options(joinedload(Topic.blocks))
            .filter(PdfDocument.subject_id == subject_id)
            .order_by(Topic.order.asc(), Topic.id.asc())
            .all()
        )

        topics_by_parent = {}
        for t in all_topics:
            topics_by_parent.setdefault(t.parent_id, []).append(t)

        def add_nodes(parent_item, parent_id):
            for t in topics_by_parent.get(parent_id, []):
                item = QTreeWidgetItem([f"🔖 {t.title}", ""])
                item.setData(0, Qt.UserRole, t.id)
                item.setData(0, Qt.UserRole + 1, "TOPIC")
                
                if t.blocks:
                    sorted_blocks = sorted(t.blocks, key=lambda b: b.page_start)
                    for b in sorted_blocks:
                        status_str = "⏳ Pendente"
                        if b.status == BlockStatus.EM_ANDAMENTO:
                            status_str = "▶️ Em Andamento"
                        elif b.status == BlockStatus.CONCLUIDO:
                            status_str = "✅ Concluído"
                        elif b.status == BlockStatus.IGNORADO:
                            status_str = "🚫 Ignorado"

                        block_item = QTreeWidgetItem([f"   ↳ Bloco (Págs {b.page_start} - {b.page_end})", status_str])
                        block_item.setData(0, Qt.UserRole, b.id)
                        block_item.setData(0, Qt.UserRole + 1, "BLOCK")
                        item.addChild(block_item)

                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.tree_topics.addTopLevelItem(item)

                add_nodes(item, t.id)

        add_nodes(None, None)
        self.tree_topics.expandAll()
        db.close()

    def export_notes(self):
        if not self.selected_subject_id:
            QMessageBox.warning(self, "Aviso", "Selecione uma matéria para visualizar o resumo.")
            return

        db = SessionLocal()
        try:
            current_item = self.tree_topics.currentItem()
            selected_topic_id = None
            
            if current_item and current_item.data(0, Qt.UserRole + 1) == "TOPIC":
                selected_topic_id = current_item.data(0, Qt.UserRole)

            subj = db.query(Subject).filter(Subject.id == self.selected_subject_id).first()
            if not subj:
                return

            query = (
                db.query(Topic)
                .join(PdfDocument)
                .options(
                    subqueryload(Topic.blocks).subqueryload(StudyBlock.notes),
                    joinedload(Topic.pdf).subqueryload(PdfDocument.highlights)
                )
                .filter(PdfDocument.subject_id == self.selected_subject_id)
            )

            if selected_topic_id:
                topics = query.filter(Topic.id == selected_topic_id).all()
            else:
                topics = query.order_by(Topic.order.asc(), Topic.id.asc()).all()

            lines_md = [f"# Resumo de Estudos: {subj.name}\n\n"]
            lines_txt = [f"# RESUMO DE ESTUDOS: {subj.name.upper()}\n", "=" * 60 + "\n\n"]

            total_items_count = 0

            for topic in topics:
                has_topic_header = False

                def ensure_topic_header():
                    nonlocal has_topic_header
                    if not has_topic_header:
                        lines_md.append(f"## 📌 Tópico: {topic.title}\n\n")
                        lines_txt.append(f"📌 TÓPICO: {topic.title}\n" + "-" * 40 + "\n")
                        has_topic_header = True

                for block in topic.blocks:
                    if block.notes:
                        ensure_topic_header()
                        lines_md.append(f"### 📄 Bloco (Págs. {block.page_start} - {block.page_end}) - Anotações\n")
                        lines_txt.append(f"  • Bloco (Págs {block.page_start} - {block.page_end}) - Anotações:\n")

                        for note in block.notes:
                            note_text = note.content.strip()
                            lines_md.append(f"- **[Pág. {note.page_number}]**: {note_text}\n")
                            lines_txt.append(f"    - [Pág. {note.page_number}]: {note_text}\n")
                            total_items_count += 1

                        lines_md.append("\n")
                        lines_txt.append("\n")

                if topic.pdf and topic.pdf.highlights:
                    topic_highlights = [
                        h for h in topic.pdf.highlights 
                        if topic.page_start <= h.page_number <= topic.page_end and h.selected_text
                    ]

                    if topic_highlights:
                        ensure_topic_header()
                        lines_md.append("### 🖍️ Trechos Grifados\n")
                        lines_txt.append("  • Trechos Grifados:\n")

                        topic_highlights.sort(key=lambda h: h.page_number)

                        for hl in topic_highlights:
                            highlight_text = hl.selected_text.strip().replace("\n", " ")
                            lines_md.append(f"> **[Pág. {hl.page_number}]** _{highlight_text}_\n\n")
                            lines_txt.append(f'    - [Pág. {hl.page_number}]: "{highlight_text}"\n')
                            total_items_count += 1

                        lines_md.append("\n")
                        lines_txt.append("\n")

            if total_items_count == 0:
                QMessageBox.information(self, "Exportação", "Nenhuma anotação ou grifo foi encontrado para este escopo.")
                return

            preview_dialog = NotesPreviewDialog(
                subject_name=subj.name,
                content_md="".join(lines_md),
                content_txt="".join(lines_txt),
                parent=self
            )
            preview_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao carregar anotações e grifos: {str(e)}")
        finally:
            db.close()

    def refresh(self):
        self.list_subjects.clear()
        self.tree_topics.clear()
        self.lbl_title.setText("<span style='color: #A6ADC8;'>Selecione uma matéria na lista à esquerda</span>")
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

    def move_topic(self, direction):
        current_item = self.tree_topics.currentItem()
        if not current_item or current_item.data(0, Qt.UserRole + 1) != "TOPIC":
            return

        parent = current_item.parent()
        if parent:
            index = parent.indexOfChild(current_item)
            new_index = index + direction
            if 0 <= new_index < parent.childCount():
                taken = parent.takeChild(index)
                parent.insertChild(new_index, taken)
                self.tree_topics.setCurrentItem(taken)
                self.save_topics_order()
        else:
            index = self.tree_topics.indexOfTopLevelItem(current_item)
            new_index = index + direction
            if 0 <= new_index < self.tree_topics.topLevelItemCount():
                taken = self.tree_topics.takeTopLevelItem(index)
                self.tree_topics.insertTopLevelItem(new_index, taken)
                self.tree_topics.setCurrentItem(taken)
                self.save_topics_order()

    def save_topics_order(self):
        """Salva a nova sequência de exibição dos tópicos no banco de dados."""
        db = SessionLocal()
        try:
            def sync_item_order(parent_item=None):
                count = parent_item.childCount() if parent_item else self.tree_topics.topLevelItemCount()
                for i in range(count):
                    item = parent_item.child(i) if parent_item else self.tree_topics.topLevelItem(i)
                    topic_id = item.data(0, Qt.UserRole)
                    item_type = item.data(0, Qt.UserRole + 1)
                    
                    if topic_id and item_type == "TOPIC":
                        t = db.query(Topic).filter(Topic.id == topic_id).first()
                        if t:
                            t.order = i
                            parent_topic_id = parent_item.data(0, Qt.UserRole) if parent_item else None
                            t.parent_id = parent_topic_id
                        
                        sync_item_order(item)

            sync_item_order(None)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def import_pdf_and_generate_blocks(self):
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
            
            file_size_bytes = os.path.getsize(file_path)
            doc = fitz.open(file_path)
            total_pages = len(doc)
            doc.close()

            pdf_doc = PdfDocument(
                subject_id=self.selected_subject_id,
                title=topic_title,
                file_path=file_path, 
                file_size_bytes=file_size_bytes,
                total_pages=total_pages
            )
            db.add(pdf_doc)
            db.flush()

            last_t = db.query(Topic).order_by(Topic.order.desc()).first()
            max_order = (last_t.order + 1) if (last_t and last_t.order is not None) else 0

            topic = Topic(
                pdf_id=pdf_doc.id,
                title=topic_title,
                page_start=1,
                page_end=total_pages,
                order=max_order
            )
            db.add(topic)
            db.flush()

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
        if not topic_id or current_item.data(0, Qt.UserRole + 1) != "TOPIC":
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
                    
                    topic = db.query(Topic).filter(Topic.id == t_id).first()
                    pdf_id = topic.pdf_id if topic else None
                    
                    db.query(Topic).filter(Topic.id == t_id).delete()
                    
                    if pdf_id:
                        other_topics = db.query(Topic).filter(Topic.pdf_id == pdf_id).count()
                        if other_topics == 0:
                            db.query(PdfDocument).filter(PdfDocument.id == pdf_id).delete()

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
                    b.current_page = b.page_start
                db.commit()
                QMessageBox.information(self, "Sucesso", "Progresso da matéria zerado com sucesso!")
                self.load_topics(self.selected_subject_id)
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Erro", f"Falha ao zerar progresso: {str(e)}")
            finally:
                db.close()