import csv
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QSplitter, QFileDialog, QMenu,
    QSizePolicy, QListView
)
from PySide6.QtCore import Qt

from database.connection import SessionLocal
from models.models import Subject, Topic, PdfDocument, QuestionError, ErrorReason
from services.error_manager import ErrorManager


class ErrorNotebookView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_combos()
        self.load_errors()

    def _apply_combo_constraints(self, combo: QComboBox, max_width: int = 180):
        """Aplica restrições de largura e rolagem para evitar estouro de tela."""
        combo.setMaximumWidth(max_width)
        combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        combo.setMaxVisibleItems(8)
        
        view = QListView()
        view.setTextElideMode(Qt.ElideRight)
        combo.setView(view)

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QFrame.panel {
                background-color: #252637;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px 10px;
                color: #CDD6F4;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #89B4FA;
            }

            QComboBox QAbstractItemView {
                background-color: #181825;
                border: 1px solid #313244;
                color: #CDD6F4;
                selection-background-color: #F38BA8;
                selection-color: #11111B;
                outline: 0px;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background-color: #181825;
                width: 8px;
                height: 8px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background-color: #45475A;
                border-radius: 4px;
            }
            QScrollBar::handle:hover {
                background-color: #89B4FA;
            }

            QPushButton.primary-btn {
                background-color: #F38BA8;
                color: #11111B;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton.primary-btn:hover {
                background-color: #EBA0AC;
            }
            QPushButton.secondary-btn {
                background-color: #313244;
                color: #CDD6F4;
                font-weight: bold;
                border: 1px solid #45475A;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton.secondary-btn:hover {
                background-color: #45475A;
            }
            QTableWidget {
                background-color: #181825;
                border: 1px solid #313244;
                gridline-color: #313244;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #252637;
                color: #89B4FA;
                padding: 6px;
                font-weight: bold;
                border: 1px solid #313244;
            }
            QMenu {
                background-color: #252637;
                border: 1px solid #313244;
                color: #CDD6F4;
            }
            QMenu::item:selected {
                background-color: #F38BA8;
                color: #11111B;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        lbl_title = QLabel("🏷️ Caderno de Erros & Questões")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89B4FA;")
        main_layout.addWidget(lbl_title)

        splitter = QSplitter(Qt.Vertical)

        # ---------------- FORMULÁRIO DE CADASTRO ----------------
        form_frame = QFrame()
        form_frame.setProperty("class", "panel")
        form_layout = QVBoxLayout(form_frame)

        lbl_form_title = QLabel("<b>Cadastrar Nova Questão Incorreta</b>")
        lbl_form_title.setStyleSheet("color: #BAC2DE; font-size: 14px;")
        form_layout.addWidget(lbl_form_title)

        row1 = QHBoxLayout()
        
        self.cb_subject = QComboBox()
        self.cb_subject.setPlaceholderText("Selecione a Matéria")
        self._apply_combo_constraints(self.cb_subject, max_width=180)
        self.cb_subject.currentIndexChanged.connect(self.on_subject_changed)

        self.cb_topic = QComboBox()
        self.cb_topic.setPlaceholderText("Selecione o Tópico")
        self._apply_combo_constraints(self.cb_topic, max_width=200)

        self.txt_banca = QLineEdit()
        self.txt_banca.setPlaceholderText("Banca (ex: Cebraspe)")
        self.txt_banca.setMaximumWidth(140)

        self.cb_reason = QComboBox()
        self._apply_combo_constraints(self.cb_reason, max_width=160)
        for r in ErrorReason:
            self.cb_reason.addItem(getattr(r, "value", str(r)), r)

        row1.addWidget(QLabel("Matéria:"))
        row1.addWidget(self.cb_subject)
        row1.addWidget(QLabel("Tópico:"))
        row1.addWidget(self.cb_topic)
        row1.addWidget(self.txt_banca)
        row1.addWidget(QLabel("Motivo:"))
        row1.addWidget(self.cb_reason)
        row1.addStretch()

        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        
        self.txt_statement = QTextEdit()
        self.txt_statement.setPlaceholderText("Cole aqui o enunciado da questão ou um resumo do problema...")
        self.txt_statement.setMaximumHeight(80)

        self.txt_explanation = QTextEdit()
        self.txt_explanation.setPlaceholderText("Por que errou? O que precisa revisar? (Gabarito / Resolução)")
        self.txt_explanation.setMaximumHeight(80)

        row2.addWidget(self.txt_statement)
        row2.addWidget(self.txt_explanation)

        form_layout.addLayout(row2)

        btn_save = QPushButton("💾 Registrar Erro")
        btn_save.setProperty("class", "primary-btn")
        btn_save.clicked.connect(self.save_error)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        form_layout.addLayout(btn_layout)

        splitter.addWidget(form_frame)

        # ---------------- TABELA E FILTROS ----------------
        list_frame = QFrame()
        list_frame.setProperty("class", "panel")
        list_layout = QVBoxLayout(list_frame)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("🔍 <b>Filtrar:</b>"))

        self.cb_filter_subject = QComboBox()
        self.cb_filter_subject.addItem("Todas as Matérias", None)
        self._apply_combo_constraints(self.cb_filter_subject, max_width=160)
        self.cb_filter_subject.currentIndexChanged.connect(self.on_filter_subject_changed)

        self.cb_filter_topic = QComboBox()
        self.cb_filter_topic.addItem("Todos os Tópicos", None)
        self._apply_combo_constraints(self.cb_filter_topic, max_width=180)
        self.cb_filter_topic.currentIndexChanged.connect(self.load_errors)

        self.cb_filter_reason = QComboBox()
        self.cb_filter_reason.addItem("Todos os Motivos", None)
        self._apply_combo_constraints(self.cb_filter_reason, max_width=150)
        for r in ErrorReason:
            self.cb_filter_reason.addItem(getattr(r, "value", str(r)), r)
        self.cb_filter_reason.currentIndexChanged.connect(self.load_errors)

        # Filtro de Resolução / Status
        self.cb_filter_status = QComboBox()
        self.cb_filter_status.addItem("Todos os Status", None)
        self.cb_filter_status.addItem("Pendentes", False)
        self.cb_filter_status.addItem("Dominados", True)
        self._apply_combo_constraints(self.cb_filter_status, max_width=130)
        self.cb_filter_status.currentIndexChanged.connect(self.load_errors)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar no enunciado...")
        self.txt_search.textChanged.connect(self.filter_table_by_text)

        filter_layout.addWidget(self.cb_filter_subject)
        filter_layout.addWidget(self.cb_filter_topic)
        filter_layout.addWidget(self.cb_filter_reason)
        filter_layout.addWidget(self.cb_filter_status)
        filter_layout.addWidget(self.txt_search)

        self.cb_export_format = QComboBox()
        self.cb_export_format.addItems(["CSV (.csv)", "JSON (.json)", "Texto (.txt)"])
        self._apply_combo_constraints(self.cb_export_format, max_width=110)
        filter_layout.addWidget(self.cb_export_format)

        btn_export = QPushButton("📤 Exportar")
        btn_export.setProperty("class", "secondary-btn")
        btn_export.clicked.connect(self.export_errors)
        filter_layout.addWidget(btn_export)

        list_layout.addLayout(filter_layout)

        # Configuração da Tabela com 7 Colunas
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Status", "Matéria", "Tópico", "Motivo", "Enunciado/Resumo", "Explicação / Resolução"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        # Conecta sinal de edição de células (Inclui o Checkbox)
        self.table.itemChanged.connect(self.on_cell_edited)
        
        list_layout.addWidget(self.table)
        splitter.addWidget(list_frame)

        main_layout.addWidget(splitter)

    def load_combos(self):
        with SessionLocal() as db:
            try:
                subjects = db.query(Subject).order_by(Subject.order.asc(), Subject.name.asc()).all()
                
                self.cb_subject.blockSignals(True)
                self.cb_subject.clear()
                self.cb_subject.addItem("Selecione a Matéria...", None)
                
                self.cb_filter_subject.blockSignals(True)
                self.cb_filter_subject.clear()
                self.cb_filter_subject.addItem("Todas as Matérias", None)

                for s in subjects:
                    self.cb_subject.addItem(s.name, s.id)
                    self.cb_filter_subject.addItem(s.name, s.id)

            except Exception as e:
                print(f"Erro ao carregar matérias: {e}")
            finally:
                self.cb_subject.blockSignals(False)
                self.cb_filter_subject.blockSignals(False)

    def on_subject_changed(self):
        subject_id = self.cb_subject.currentData()

        self.cb_topic.blockSignals(True)
        self.cb_topic.clear()
        self.cb_topic.addItem("Selecione o Tópico (Opcional)...", None)

        if not subject_id:
            self.cb_topic.blockSignals(False)
            return

        with SessionLocal() as db:
            try:
                topics = (
                    db.query(Topic)
                    .join(PdfDocument, Topic.pdf_id == PdfDocument.id)
                    .filter(PdfDocument.subject_id == subject_id)
                    .order_by(Topic.order.asc(), Topic.id.asc())
                    .all()
                )

                for topic in topics:
                    self.cb_topic.addItem(topic.title, topic.id)
            except Exception as e:
                print(f"Erro ao carregar tópicos no cadastro: {e}")
            finally:
                self.cb_topic.blockSignals(False)

    def on_filter_subject_changed(self):
        subject_id = self.cb_filter_subject.currentData()

        self.cb_filter_topic.blockSignals(True)
        self.cb_filter_topic.clear()
        self.cb_filter_topic.addItem("Todos os Tópicos", None)

        if subject_id:
            with SessionLocal() as db:
                try:
                    topics = (
                        db.query(Topic)
                        .join(PdfDocument, Topic.pdf_id == PdfDocument.id)
                        .filter(PdfDocument.subject_id == subject_id)
                        .order_by(Topic.order.asc(), Topic.id.asc())
                        .all()
                    )
                    for topic in topics:
                        self.cb_filter_topic.addItem(topic.title, topic.id)
                except Exception as e:
                    print(f"Erro ao carregar tópicos no filtro: {e}")

        self.cb_filter_topic.blockSignals(False)
        self.load_errors()

    def save_error(self):
        subject_id = self.cb_subject.currentData()
        topic_id = self.cb_topic.currentData()
        statement = self.txt_statement.toPlainText().strip()
        explanation = self.txt_explanation.toPlainText().strip()
        reason = self.cb_reason.currentData()
        banca = self.txt_banca.text().strip()

        if not subject_id or not statement:
            QMessageBox.warning(self, "Campos Obrigatórios", "Por favor, selecione a Matéria e informe o Enunciado da questão.")
            return

        with SessionLocal() as db:
            try:
                ErrorManager.create_error(
                    db=db,
                    subject_id=subject_id,
                    topic_id=topic_id,
                    statement=statement,
                    correct_answer="N/A",
                    reason=reason,
                    banca=banca,
                    explanation=explanation
                )
                QMessageBox.information(self, "Sucesso", "Erro registrado com sucesso!")
                
                self.txt_statement.clear()
                self.txt_explanation.clear()
                self.txt_banca.clear()
                
                self.cb_subject.blockSignals(True)
                self.cb_subject.setCurrentIndex(0)
                self.cb_subject.blockSignals(False)

                self.cb_topic.blockSignals(True)
                self.cb_topic.clear()
                self.cb_topic.addItem("Selecione o Tópico (Opcional)...", None)
                self.cb_topic.blockSignals(False)
                
                self.load_errors()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao salvar erro: {e}")

    def load_errors(self):
        """Busca no banco aplicando os filtros de Matéria, Tópico, Motivo e Status de Resolução."""
        subject_id = self.cb_filter_subject.currentData()
        topic_id = self.cb_filter_topic.currentData()
        reason = self.cb_filter_reason.currentData()
        resolved_filter = self.cb_filter_status.currentData()

        # Bloqueia sinais para preenchimento seguro sem emitir eventos
        self.table.blockSignals(True)

        with SessionLocal() as db:
            try:
                query = db.query(QuestionError)
                if subject_id:
                    query = query.filter(QuestionError.subject_id == subject_id)
                if topic_id:
                    query = query.filter(QuestionError.topic_id == topic_id)
                if reason:
                    query = query.filter(QuestionError.reason == reason)
                if resolved_filter is not None:
                    query = query.filter(QuestionError.is_resolved == resolved_filter)

                errors = query.order_by(QuestionError.id.desc()).all()
                self.table.setRowCount(0)

                for row, err in enumerate(errors):
                    self.table.insertRow(row)
                    
                    # Coluna 0: ID (Não editável)
                    id_item = QTableWidgetItem(str(err.id))
                    id_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.table.setItem(row, 0, id_item)

                    # Coluna 1: Status (Checkbox interativo)
                    status_item = QTableWidgetItem(" Dominado" if err.is_resolved else " Pendente")
                    status_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    status_item.setCheckState(Qt.Checked if err.is_resolved else Qt.Unchecked)
                    self.table.setItem(row, 1, status_item)

                    # Colunas 2, 3 e 4: Metadados (Não editáveis na célula)
                    subject_name = err.subject.name if err.subject else "-"
                    topic_title = err.topic.title if err.topic else "-"
                    reason_val = getattr(err.reason, "value", str(err.reason))

                    for col_idx, val in [(2, subject_name), (3, topic_title), (4, reason_val)]:
                        item = QTableWidgetItem(val)
                        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        self.table.setItem(row, col_idx, item)

                    # Colunas 5 e 6: Textos editáveis
                    self.table.setItem(row, 5, QTableWidgetItem(err.statement))
                    self.table.setItem(row, 6, QTableWidgetItem(err.explanation or ""))
                
                self.filter_table_by_text()

            except Exception as e:
                print(f"Erro ao carregar erros: {e}")
            finally:
                self.table.blockSignals(False)

    def on_cell_edited(self, item: QTableWidgetItem):
        """Persiste em tempo real no banco quando o Checkbox, Enunciado ou Explicação for alterado."""
        row = item.row()
        col = item.column()

        id_item = self.table.item(row, 0)
        if not id_item:
            return

        try:
            error_id = int(id_item.text())

            with SessionLocal() as db:
                err = db.query(QuestionError).get(error_id)
                if not err:
                    return

                # Coluna 1: Checkbox (is_resolved)
                if col == 1:
                    is_checked = (item.checkState() == Qt.Checked)
                    err.is_resolved = is_checked
                    
                    self.table.blockSignals(True)
                    item.setText(" Dominado" if is_checked else " Pendente")
                    self.table.blockSignals(False)

                # Coluna 5: Enunciado
                elif col == 5:
                    err.statement = item.text().strip()

                # Coluna 6: Explicação
                elif col == 6:
                    err.explanation = item.text().strip()

                db.commit()
        except Exception as e:
            print(f"Erro ao atualizar registro #{error_id} no banco de dados: {e}")

    def filter_table_by_text(self):
        query = self.txt_search.text().lower().strip()
        for row in range(self.table.rowCount()):
            statement_item = self.table.item(row, 5)
            explanation_item = self.table.item(row, 6)
            
            statement_text = statement_item.text().lower() if statement_item else ""
            explanation_text = explanation_item.text().lower() if explanation_item else ""
            
            match = (query in statement_text) or (query in explanation_text)
            self.table.setRowHidden(row, not match)

    def show_table_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return

        row = item.row()
        error_id_item = self.table.item(row, 0)
        if not error_id_item:
            return

        error_id = int(error_id_item.text())

        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Excluir Registro")

        action = menu.exec(self.table.mapToGlobal(pos))
        if action == delete_action:
            self.delete_error(error_id)

    def delete_error(self, error_id):
        reply = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o registro de erro #{error_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with SessionLocal() as db:
                try:
                    err = db.query(QuestionError).get(error_id)
                    if err:
                        db.delete(err)
                        db.commit()
                        QMessageBox.information(self, "Sucesso", "Registro de erro excluído.")
                        self.load_errors()
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Erro", f"Falha ao excluir registro: {e}")

    def select_error_by_id(self, error_id: int):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == str(error_id):
                self.table.setRowHidden(row, False)
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                self.table.setFocus()
                break

    def export_errors(self):
        subject_id = self.cb_filter_subject.currentData()
        topic_id = self.cb_filter_topic.currentData()
        reason = self.cb_filter_reason.currentData()
        resolved_filter = self.cb_filter_status.currentData()

        with SessionLocal() as db:
            try:
                query = db.query(QuestionError)
                if subject_id:
                    query = query.filter(QuestionError.subject_id == subject_id)
                if topic_id:
                    query = query.filter(QuestionError.topic_id == topic_id)
                if reason:
                    query = query.filter(QuestionError.reason == reason)
                if resolved_filter is not None:
                    query = query.filter(QuestionError.is_resolved == resolved_filter)

                errors = query.all()
                if not errors:
                    QMessageBox.information(self, "Exportar Erros", "Nenhum erro encontrado para os filtros selecionados.")
                    return

                selected_fmt = self.cb_export_format.currentText()

                if "CSV" in selected_fmt:
                    default_filename = "caderno_de_erros.csv"
                    filter_str = "Arquivo CSV (*.csv)"
                elif "JSON" in selected_fmt:
                    default_filename = "caderno_de_erros.json"
                    filter_str = "Arquivo JSON (*.json)"
                else:
                    default_filename = "caderno_de_erros.txt"
                    filter_str = "Arquivo de Texto (*.txt)"

                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Exportar Caderno de Erros",
                    default_filename,
                    filter_str
                )

                if not file_path:
                    return

                if "JSON" in selected_fmt:
                    data = []
                    for err in errors:
                        reason_val = getattr(err.reason, "value", str(err.reason))
                        data.append({
                            "id": err.id,
                            "status": "Dominado" if err.is_resolved else "Pendente",
                            "materia": err.subject.name if err.subject else None,
                            "topico": err.topic.title if err.topic else None,
                            "banca": err.banca,
                            "motivo": reason_val,
                            "enunciado": err.statement,
                            "explicacao": err.explanation,
                            "criado_em": err.created_at.strftime("%Y-%m-%d %H:%M:%S") if err.created_at else None
                        })
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)

                elif "CSV" in selected_fmt:
                    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.writer(f, delimiter=";")
                        writer.writerow(["ID", "Status", "Matéria", "Tópico", "Banca", "Motivo", "Enunciado", "Explicação", "Data de Criação"])
                        for err in errors:
                            reason_val = getattr(err.reason, "value", str(err.reason))
                            writer.writerow([
                                err.id,
                                "Dominado" if err.is_resolved else "Pendente",
                                err.subject.name if err.subject else "",
                                err.topic.title if err.topic else "",
                                err.banca or "",
                                reason_val,
                                err.statement,
                                err.explanation or "",
                                err.created_at.strftime("%Y-%m-%d %H:%M:%S") if err.created_at else ""
                            ])

                else:  # TXT
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("=========================================\n")
                        f.write("        CADERNO DE ERROS & QUESTÕES      \n")
                        f.write("=========================================\n\n")
                        for err in errors:
                            reason_val = getattr(err.reason, "value", str(err.reason))
                            f.write(f"ID: {err.id}\n")
                            f.write(f"Status: {'Dominado' if err.is_resolved else 'Pendente'}\n")
                            f.write(f"Matéria: {err.subject.name if err.subject else '-'}\n")
                            f.write(f"Tópico: {err.topic.title if err.topic else '-'}\n")
                            f.write(f"Banca: {err.banca or '-'}\n")
                            f.write(f"Motivo: {reason_val}\n")
                            f.write(f"Enunciado:\n{err.statement}\n")
                            f.write(f"Explicação / Resolução:\n{err.explanation or '-'}\n")
                            f.write("-" * 41 + "\n\n")

                QMessageBox.information(self, "Sucesso", f"Erros exportados com sucesso para:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Exportar", f"Falha ao exportar o caderno de erros: {e}")