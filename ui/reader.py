from datetime import datetime
import pymupdf as fitz
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QMessageBox, QFrame)
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QTimer, QTime, Signal, QRect
from database.connection import SessionLocal
from models.models import StudyBlock, BlockStatus, Topic, PdfDocument, Subject, Highlight
from services.study_manager import StudyManager

class StudyReaderView(QWidget):
    back_requested = Signal()

    def __init__(self, block_id=None):
        super().__init__()
        self.block_id = block_id
        self.doc = None
        self.current_pdf_id = None
        self.current_page = 0
        self.total_pages = 0
        
        # Meta do bloco em memória
        self.page_start = 1
        self.page_end = 1
        self.block_status = None
        
        # Timer de Estudo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_seconds = 0
        
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- PAINEL ESQUERDO: Visualizador do PDF ---
        pdf_container = QVBoxLayout()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("background-color: #34495e; border-radius: 6px;")

        self.lbl_pdf_page = PDFSelectableLabel("Nenhum PDF carregado.")
        self.lbl_pdf_page.setAlignment(Qt.AlignCenter)
        self.lbl_pdf_page.area_selected.connect(self.handle_area_selected)
        self.scroll_area.setWidget(self.lbl_pdf_page)
        
        pdf_container.addWidget(self.scroll_area)

        # Barra de Navegação de Páginas
        nav_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton("⬅️ Anterior")
        self.btn_prev_page.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.btn_prev_page)

        self.lbl_page_info = QLabel("Página: 0 / 0")
        self.lbl_page_info.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.lbl_page_info)

        self.btn_next_page = QPushButton("Próxima ➡️")
        self.btn_next_page.clicked.connect(self.next_page)
        nav_layout.addWidget(self.btn_next_page)

        pdf_container.addLayout(nav_layout)
        main_layout.addLayout(pdf_container, stretch=4)

        # --- PAINEL DIREITO: Acompanhamento e Ações ---
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        
        self.lbl_info = QLabel("<h3>Nenhum bloco selecionado</h3>")
        self.lbl_info.setWordWrap(True)
        sidebar_layout.addWidget(self.lbl_info)

        # Cronômetro
        timer_frame = QFrame()
        timer_frame.setStyleSheet("background-color: #2c3e50; border-radius: 8px; padding: 10px;")
        timer_layout = QVBoxLayout(timer_frame)
        
        lbl_timer_title = QLabel("Tempo de Estudo")
        lbl_timer_title.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        lbl_timer_title.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(lbl_timer_title)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setStyleSheet("font-size: 28px; font-weight: bold; color: #2ecc71;")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(self.lbl_timer)

        btn_timer_layout = QHBoxLayout()
        self.btn_start_timer = QPushButton("▶️ Iniciar")
        self.btn_start_timer.clicked.connect(self.start_timer)
        btn_timer_layout.addWidget(self.btn_start_timer)

        self.btn_pause_timer = QPushButton("⏸️ Pausar")
        self.btn_pause_timer.clicked.connect(self.pause_timer)
        btn_timer_layout.addWidget(self.btn_pause_timer)

        timer_layout.addLayout(btn_timer_layout)

        # Botão de Desfazer Grifo
        self.btn_undo_highlight = QPushButton("↩️ Desfazer Grifo")
        self.btn_undo_highlight.clicked.connect(self.undo_last_highlight)
        nav_layout.addWidget(self.btn_undo_highlight)

        self.btn_reset_timer = QPushButton("⏹️ Parar e Descartar")
        self.btn_reset_timer.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.btn_reset_timer.clicked.connect(self.reset_timer)
        timer_layout.addWidget(self.btn_reset_timer)

        sidebar_layout.addWidget(timer_frame)

        # --- AÇÕES DO BLOCO ---
        self.btn_save_pause = QPushButton("💾 Pausar e Salvar")
        self.btn_save_pause.setStyleSheet("""
            QPushButton {
                background-color: #f39c12; 
                color: white; 
                font-size: 13px; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 6px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        self.btn_save_pause.clicked.connect(self.save_and_pause)
        sidebar_layout.addWidget(self.btn_save_pause)

        self.btn_complete_block = QPushButton("✅ Concluir Bloco")
        self.btn_complete_block.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; 
                color: white; 
                font-size: 13px; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 6px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        self.btn_complete_block.clicked.connect(self.complete_block)
        sidebar_layout.addWidget(self.btn_complete_block)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar, stretch=0)

    def unload_pdf(self):
        """Fecha o documento atual, limpa a tela e reseta o estado interno do leitor."""
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None

        self.current_pdf_id = None
        self.block_id = None
        self.current_page = 0
        self.total_pages = 0
        self.lbl_pdf_page.setText("Nenhum PDF carregado.")
        self.lbl_page_info.setText("Página: 0 / 0")
        self.lbl_info.setText("<h3>Nenhum bloco selecionado</h3>")

    def closeEvent(self, event):
        """Garante a liberação de recursos ao fechar o widget."""
        self.unload_pdf()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.doc:
            self.render_page()

    def load_block(self, block_id):
        # Limpa o documento anterior antes de carregar o novo
        self.unload_pdf()
        self.block_id = block_id
        self.reset_timer(confirm=False)
        
        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == block_id).first()
            if not block:
                return

            topic = db.query(Topic).filter(Topic.id == block.topic_id).first()
            pdf_doc = db.query(PdfDocument).filter(PdfDocument.id == topic.pdf_id).first() if topic else None
            subject = db.query(Subject).filter(Subject.id == pdf_doc.subject_id).first() if pdf_doc else None

            subj_name = subject.name if subject else "Matéria"
            topic_title = topic.title if topic else "Tópico"
            
            self.page_start = getattr(block, 'page_start', 1)
            self.page_end = getattr(block, 'page_end', 1)
            self.block_status = block.status
            
            self.lbl_info.setText(
                f"<b>Matéria:</b> {subj_name}<br><br>"
                f"<b>Tópico:</b> {topic_title}<br><br>"
                f"<b>Meta:</b> Pág. {self.page_start} até {self.page_end}"
            )

            if pdf_doc and pdf_doc.file_path:
                self.current_pdf_id = pdf_doc.id
                self.doc = fitz.open(pdf_doc.file_path)
                self.total_pages = len(self.doc)
                
                saved_page = block.current_page if (block.current_page and block.current_page > 0) else self.page_start
                self.current_page = max(0, saved_page - 1)
                self.render_page()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir o PDF: {str(e)}")
        finally:
            db.close()

    def render_page(self, page_num: int = None):
        if page_num is not None:
            self.current_page = page_num - 1 if page_num > 0 else page_num

        if not self.doc or self.current_page < 0 or self.current_page >= self.total_pages:
            return

        page = self.doc[self.current_page]

        # Remove anotações no PyMuPDF para redesenhar com base no banco
        annot = page.first_annot
        while annot:
            next_annot = annot.next
            if annot.type[0] == 8:  # Type 8 = Highlight Annotation
                page.delete_annot(annot)
            annot = next_annot

        # Desenha os grifos persistidos no banco
        if self.current_pdf_id:
            db = SessionLocal()
            try:
                highlights = StudyManager.get_highlights_by_pdf(
                    db=db, 
                    pdf_id=self.current_pdf_id, 
                    page_number=self.current_page + 1
                )
                for hl in highlights:
                    if hl.selected_text:
                        matches = page.search_for(hl.selected_text)
                        for rect in matches:
                            annot = page.add_highlight_annot(rect)
                            annot.set_colors(stroke=(1, 1, 0))  # Amarelo
                            annot.update()
            except Exception as e:
                print(f"Erro ao carregar grifos: {e}")
            finally:
                db.close()

        target_width = max(400, self.scroll_area.viewport().width() - 30)
        zoom = target_width / page.rect.width
        matrix = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=matrix)
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.lbl_pdf_page.setPixmap(pixmap)
        self.lbl_page_info.setText(f"Página: {self.current_page + 1} / {self.total_pages}")

    def undo_last_highlight(self):
        if not self.current_pdf_id:
            return

        db = SessionLocal()
        try:
            last_hl = db.query(Highlight).filter(
                Highlight.pdf_id == self.current_pdf_id,
                Highlight.page_number == self.current_page + 1
            ).order_by(Highlight.id.desc()).first()

            if last_hl:
                db.delete(last_hl)
                db.commit()
                self.render_page()
        except Exception as e:
            print(f"Erro ao desfazer grifo: {e}")
        finally:
            db.close()

    def clear_all_page_highlights(self):
        if not self.current_pdf_id:
            return

        db = SessionLocal()
        try:
            db.query(Highlight).filter(
                Highlight.pdf_id == self.current_pdf_id,
                Highlight.page_number == self.current_page + 1
            ).delete()
            db.commit()
            self.render_page()
        except Exception as e:
            print(f"Erro ao limpar grifos: {e}")
        finally:
            db.close()

    def handle_area_selected(self, rect):
        if not self.doc or self.current_page < 0:
            return

        page = self.doc[self.current_page]
        target_width = max(400, self.scroll_area.viewport().width() - 30)
        zoom = target_width / page.rect.width

        pdf_rect = fitz.Rect(
            rect.x() / zoom,
            rect.y() / zoom,
            (rect.x() + rect.width()) / zoom,
            (rect.y() + rect.height()) / zoom
        )

        words = page.get_text("words", clip=pdf_rect)
        if not words:
            return

        selected_text = " ".join([w[4] for w in words]).strip()
        if selected_text:
            self.on_text_selected_to_highlight(selected_text, pdf_rect)

    def on_text_selected_to_highlight(self, selected_text: str, pdf_rect=None):
        """Salva o texto selecionado no banco e re-renderiza a página."""
        if not selected_text.strip() or not self.current_pdf_id:
            return

        db = SessionLocal()
        try:
            StudyManager.add_highlight(
                db=db,
                pdf_id=self.current_pdf_id,
                page_number=self.current_page + 1,
                selected_text=selected_text.strip(),
                color="#FFFF00"
            )
            self.render_page()
        except Exception as e:
            print(f"Erro ao salvar highlight: {e}")
        finally:
            db.close()

    def save_current_page(self):
        if not self.block_id:
            return
        
        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block:
                block.current_page = self.current_page + 1
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            self.save_current_page()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_page()
            self.save_current_page()
            self.check_block_completion()

    def check_block_completion(self):
        current_page_1based = self.current_page + 1
        
        if current_page_1based > self.page_end and self.block_status != BlockStatus.CONCLUIDO:
            db = SessionLocal()
            try:
                block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
                if block:
                    block.status = BlockStatus.CONCLUIDO
                    block.current_page = self.page_end
                    block.completed_at = datetime.utcnow()
                    block.time_spent_seconds = (block.time_spent_seconds or 0) + self.elapsed_seconds
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

            self.block_status = BlockStatus.CONCLUIDO
            self.pause_timer()

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Bloco Concluído! 🎉")
            msg.setText(
                "<b>Parabéns! Você concluiu este bloco de estudos.</b><br><br>"
                f"Faixa concluída: Páginas {self.page_start} até {self.page_end}.<br><br>"
                "Deseja continuar lendo o próximo bloco deste PDF ou voltar para o ciclo no Dashboard?"
            )
            
            btn_continue = msg.addButton("Continuar Lendo", QMessageBox.AcceptRole)
            msg.addButton("Voltar ao Dashboard", QMessageBox.RejectRole)
            msg.exec()
            
            if msg.clickedButton() == btn_continue:
                self.load_next_sequential_block()
            else:
                self.back_requested.emit()

    def load_next_sequential_block(self):
        db = SessionLocal()
        try:
            current_block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if not current_block:
                return

            next_block = db.query(StudyBlock)\
                .join(Topic, StudyBlock.topic_id == Topic.id)\
                .filter(
                    Topic.pdf_id == current_block.topic.pdf_id,
                    StudyBlock.status == BlockStatus.PENDENTE,
                    StudyBlock.page_start >= self.page_end
                )\
                .order_by(StudyBlock.page_start.asc())\
                .first()

            if next_block:
                next_id = next_block.id
                db.close()
                self.load_block(next_id)
                self.start_timer()
            else:
                db.close()
                QMessageBox.information(
                    self,
                    "Fim do Material",
                    "Você concluiu todos os blocos disponíveis para este PDF! Retornando ao Dashboard."
                )
                self.back_requested.emit()
        except Exception as e:
            db.close()
            QMessageBox.critical(self, "Erro", f"Erro ao avançar bloco: {str(e)}")

    def start_timer(self):
        self.timer.start(1000)
        if self.block_id:
            db = SessionLocal()
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block and block.status == BlockStatus.PENDENTE:
                block.status = BlockStatus.EM_ANDAMENTO
                self.block_status = BlockStatus.EM_ANDAMENTO
                if not block.started_at:
                    block.started_at = datetime.utcnow()
                db.commit()
            db.close()

    def pause_timer(self):
        self.timer.stop()

    def update_timer(self):
        self.elapsed_seconds += 1
        time_obj = QTime(0, 0, 0).addSecs(self.elapsed_seconds)
        self.lbl_timer.setText(time_obj.toString("hh:mm:ss"))

    def reset_timer(self, confirm=True):
        if confirm and self.elapsed_seconds > 0:
            reply = QMessageBox.question(
                self, "Descartar Progresso",
                "Deseja parar o cronômetro e descartar o tempo registrado nesta sessão?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.pause_timer()
        self.elapsed_seconds = 0
        self.lbl_timer.setText("00:00:00")

    def save_and_pause(self):
        if not self.block_id:
            return

        self.pause_timer()
        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block:
                block.current_page = self.current_page + 1
                block.status = BlockStatus.EM_ANDAMENTO
                self.block_status = BlockStatus.EM_ANDAMENTO
                if not block.started_at:
                    block.started_at = datetime.utcnow()
                
                block.time_spent_seconds = (block.time_spent_seconds or 0) + self.elapsed_seconds
                db.commit()

                QMessageBox.information(
                    self, 
                    "Progresso Salvo", 
                    f"Progresso salvo com sucesso!\n\n"
                    f"• Parou na página: {block.current_page}\n"
                    f"• Tempo registrado nesta sessão: {self.lbl_timer.text()}\n\n"
                    f"Você pode retomar de onde parou a qualquer momento."
                )
                
                self.elapsed_seconds = 0
                self.lbl_timer.setText("00:00:00")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao salvar progresso: {str(e)}")
        finally:
            db.close()

    def complete_block(self):
        if not self.block_id:
            return

        self.pause_timer()
        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block:
                block.status = BlockStatus.CONCLUIDO
                self.block_status = BlockStatus.CONCLUIDO
                block.current_page = self.page_end
                block.completed_at = datetime.utcnow()
                block.time_spent_seconds = (block.time_spent_seconds or 0) + self.elapsed_seconds
                
                db.commit()
                QMessageBox.information(
                    self, 
                    "Parabéns!", 
                    f"Bloco de estudo concluído com sucesso!\nTempo registrado: {self.lbl_timer.text()}"
                )
                
                self.elapsed_seconds = 0
                self.lbl_timer.setText("00:00:00")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao concluir o bloco: {str(e)}")
        finally:
            db.close()


class PDFSelectableLabel(QLabel):
    area_selected = Signal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.origin_point = None
        self.current_point = None
        self.is_selecting = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin_point = event.pos()
            self.current_point = event.pos()
            self.is_selecting = True
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_selecting and (event.buttons() & Qt.LeftButton):
            self.current_point = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            selection_rect = QRect(self.origin_point, self.current_point).normalized()
            self.origin_point = None
            self.current_point = None
            self.update()

            if selection_rect.width() > 10 and selection_rect.height() > 10:
                self.area_selected.emit(selection_rect)

        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_selecting and self.origin_point and self.current_point:
            painter = QPainter(self)
            rect = QRect(self.origin_point, self.current_point).normalized()
            
            painter.setPen(QPen(QColor(255, 215, 0, 200), 1, Qt.DashLine))
            painter.setBrush(QColor(255, 255, 0, 60))
            painter.drawRect(rect)