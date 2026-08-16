from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, Signal

class PDFOutlineTreeWidget(QTreeWidget):
    page_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover { background-color: #313244; }
            QTreeWidget::item:selected {
                background-color: #45475A;
                color: #89B4FA;
            }
        """)
        self.itemClicked.connect(self.on_item_clicked)

    def load_db_topics(self, topics_list):
        self.clear()

        if not topics_list:
            item = QTreeWidgetItem(self, ["Nenhum tópico cadastrado"])
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            return

        for t in topics_list:
            title = getattr(t, 'title', t.get('title', 'Tópico sem título') if isinstance(t, dict) else 'Tópico sem título')
            page = getattr(t, 'page_start', t.get('page_start', 1) if isinstance(t, dict) else 1)

            tree_item = QTreeWidgetItem(self, [f"📌 {title} (p. {page})"])
            tree_item.setData(0, Qt.UserRole, page)

        self.expandToDepth(0)

    def load_toc(self, toc_list):
        self.clear()
        
        valid_toc = []
        if toc_list:
            for item in toc_list:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    level = item[0]
                    title = item[1]
                    page = item[2] if len(item) > 2 and item[2] is not None else 1
                    valid_toc.append([level, title, page])

        if not valid_toc:
            item = QTreeWidgetItem(self, ["Nenhum sumário disponível"])
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            return

        parents = {0: self}

        for item_data in valid_toc:
            try:
                level = int(item_data[0])
                title = str(item_data[1]).strip() or "Tópico sem título"
                raw_page = item_data[2]
                page = 1 if raw_page is None else int(raw_page)
            except (ValueError, TypeError, IndexError):
                continue

            page = max(1, page)
            target_level = level - 1
            while target_level > 0 and target_level not in parents:
                target_level -= 1

            parent = parents.get(target_level, self)
            tree_item = QTreeWidgetItem(parent, [f"{title} (p. {page})"])
            tree_item.setData(0, Qt.UserRole, page)
            parents[level] = tree_item

        self.expandToDepth(0)

    def on_item_clicked(self, item, column):
        page = item.data(0, Qt.UserRole)
        if page is not None and isinstance(page, int):
            self.page_requested.emit(page)