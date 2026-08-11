import csv
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QComboBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QSplitter, QFileDialog, QMenu
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

        # Header Title
        lbl_title = QLabel("🏷️ Caderno de Erros & Questões")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89B4FA;")
        main_layout.addWidget(lbl_title)

        # Splitter dividindo Formulário de Cadastro / Lista de Erros
        splitter = QSplitter(Qt.Vertical)

        # ---------------- FORMULÁRIO DE CADASTRO ----------------
        form_frame = QFrame()
        form_frame.setProperty("class", "panel")
        form_layout = QVBoxLayout(form_frame)

        lbl_form_title = QLabel("<b>Cadastrar Nova Questão Incorreta</b>")
        lbl_form_title.setStyleSheet("color: #BAC2DE; font-size: 14px;")
        form_layout.addWidget(lbl_form_title)

        # Linha 1: Matéria, Tópico, Banca e Motivo
        row1 = QHBoxLayout()
        
        self.cb_subject = QComboBox()
        self.cb_subject.setPlaceholderText("Selecione a Matéria")
        self.cb_subject.currentIndexChanged.connect(self.on_subject_changed)

        self.cb_topic = QComboBox()
        self.cb_topic.setPlaceholderText("Selecione o Tópico")

        self.txt_banca = QLineEdit()
        self.txt_banca.setPlaceholderText("Banca (ex: Cebraspe)")

        self.cb_reason = QComboBox()
        for r in ErrorReason:
            self.cb_reason.addItem(r.value, r)

        row1.addWidget(QLabel("Matéria:"))
        row1.addWidget(self.cb_subject, stretch=2)
        row1.addWidget(QLabel("Tópico:"))
        row1.addWidget(self.cb_topic, stretch=2)
        row1.addWidget(self.txt_banca, stretch=1)
        row1.addWidget(QLabel("Motivo:"))
        row1.addWidget(self.cb_reason, stretch=2)

        form_layout.addLayout(row1)

        # Linha 2: Enunciado e Explicação
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

        # Botão Salvar
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

        # Barra de Filtros + Seleção de Formato e Botão Exportar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("🔍 <b>Filtrar Erros:</b>"))

        self.cb_filter_subject = QComboBox()
        self.cb_filter_subject.addItem("Todas as Matérias", None)
        self.cb_filter_subject.currentIndexChanged.connect(self.load_errors)

        self.cb_filter_reason = QComboBox()
        self.cb_filter_reason.addItem("Todos os Motivos", None)
        for r in ErrorReason:
            self.cb_filter_reason.addItem(r.value, r)
        self.cb_filter_reason.currentIndexChanged.connect(self.load_errors)

        filter_layout.addWidget(self.cb_filter_subject, stretch=2)
        filter_layout.addWidget(self.cb_filter_reason, stretch=2)
        filter_layout.addStretch()

        # ComboBox para escolher a extensão de exportação
        self.cb_export_format = QComboBox()
        self.cb_export_format.addItems(["CSV (.csv)", "JSON (.json)", "Texto (.txt)"])
        filter_layout.addWidget(self.cb_export_format)

        btn_export = QPushButton("📤 Exportar")
        btn_export.setProperty("class", "secondary-btn")
        btn_export.clicked.connect(self.export_errors)
        filter_layout.addWidget(btn_export)

        list_layout.addLayout(filter_layout)

        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Matéria", "Motivo do Erro", "Enunciado/Resumo", "Explicação / Resolução"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        
        # Menu de contexto (botão direito) na tabela
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        list_layout.addWidget(self.table)
        splitter.addWidget(list_frame)

        main_layout.addWidget(splitter)

    def load_combos(self):
        """Carrega as matérias nos ComboBoxes (do formulário e do filtro)."""
        with SessionLocal() as db:
            try:
                subjects = db.query(Subject).all()
                
                # 1. Atualiza formulário de cadastro
                self.cb_subject.blockSignals(True)
                self.cb_subject.clear()
                self.cb_subject.addItem("Selecione a Matéria...", None)
                
                # 2. Atualiza filtro da tabela
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
        """Atualiza os tópicos de acordo com a matéria selecionada no formulário."""
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
                    .all()
                )

                for topic in topics:
                    self.cb_topic.addItem(topic.title, topic.id)
            except Exception as e:
                print(f"Erro ao carregar tópicos: {e}")
            finally:
                self.cb_topic.blockSignals(False)

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
                
                # Limpa formulário e reseta comboboxes
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
        subject_id = self.cb_filter_subject.currentData()
        reason = self.cb_filter_reason.currentData()

        with SessionLocal() as db:
            try:
                errors = ErrorManager.get_errors_filtered(db, subject_id=subject_id, reason=reason)
                self.table.setRowCount(0)

                for row, err in enumerate(errors):
                    self.table.insertRow(row)
                    
                    subject_name = err.subject.name if err.subject else "-"
                    
                    self.table.setItem(row, 0, QTableWidgetItem(str(err.id)))
                    self.table.setItem(row, 1, QTableWidgetItem(subject_name))
                    self.table.setItem(row, 2, QTableWidgetItem(err.reason.value if hasattr(err.reason, 'value') else str(err.reason)))
                    self.table.setItem(row, 3, QTableWidgetItem(err.statement))
                    self.table.setItem(row, 4, QTableWidgetItem(err.explanation or ""))
            except Exception as e:
                print(f"Erro ao carregar erros: {e}")

    def show_table_context_menu(self, pos):
        """Menu acionado pelo botão direito para excluir o erro selecionado."""
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
        """Confirma e remove o registro de erro do banco de dados."""
        reply = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Tem certeza que deseja excluir o registro de erro #{error_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            with SessionLocal() as db:
                try:
                    # Caso exista um método delete no ErrorManager ou deletando via ORM:
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
        """Busca o ID do erro na tabela, seleciona a linha e rola até ela."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)  # Coluna 0 é o ID
            if item and item.text() == str(error_id):
                self.table.selectRow(row)
                self.table.scrollToItem(item)
                break

    def export_errors(self):
        """Exporta os erros atualmente filtrados conforme o formato selecionado no ComboBox."""
        subject_id = self.cb_filter_subject.currentData()
        reason = self.cb_filter_reason.currentData()

        with SessionLocal() as db:
            try:
                errors = ErrorManager.get_errors_filtered(db, subject_id=subject_id, reason=reason)
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
                        data.append({
                            "id": err.id,
                            "materia": err.subject.name if err.subject else None,
                            "topico": err.topic.title if err.topic else None,
                            "banca": err.banca,
                            "motivo": err.reason.value if hasattr(err.reason, 'value') else str(err.reason),
                            "enunciado": err.statement,
                            "explicacao": err.explanation,
                            "criado_em": err.created_at.strftime("%Y-%m-%d %H:%M:%S") if err.created_at else None
                        })
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)

                elif "CSV" in selected_fmt:
                    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.writer(f, delimiter=";")
                        writer.writerow(["ID", "Matéria", "Tópico", "Banca", "Motivo", "Enunciado", "Explicação", "Data de Criação"])
                        for err in errors:
                            writer.writerow([
                                err.id,
                                err.subject.name if err.subject else "",
                                err.topic.title if err.topic else "",
                                err.banca or "",
                                err.reason.value if hasattr(err.reason, 'value') else str(err.reason),
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
                            f.write(f"ID: {err.id}\n")
                            f.write(f"Matéria: {err.subject.name if err.subject else '-'}\n")
                            f.write(f"Tópico: {err.topic.title if err.topic else '-'}\n")
                            f.write(f"Banca: {err.banca or '-'}\n")
                            f.write(f"Motivo: {err.reason.value if hasattr(err.reason, 'value') else str(err.reason)}\n")
                            f.write(f"Enunciado:\n{err.statement}\n")
                            f.write(f"Explicação / Resolução:\n{err.explanation or '-'}\n")
                            f.write("-" * 41 + "\n\n")

                QMessageBox.information(self, "Sucesso", f"Erros exportados com sucesso para:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Exportar", f"Falha ao exportar o caderno de erros: {e}")
        