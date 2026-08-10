from datetime import datetime
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from models.models import Subject, PdfDocument, Topic, StudyBlock, BlockStatus, Highlight

class StudyManager:

    @staticmethod
    def get_next_block_to_study(db: Session, last_subject_id: int = None):
        """
        Retorna o próximo bloco de estudo seguindo o Ciclo Inteligente:
        1. Prioriza blocos que já estão EM_ANDAMENTO (respeitando Topic.order).
        2. Aplica Rotação de Matérias: busca o próximo bloco PENDENTE da matéria 
           com MENOS blocos concluídos.
        3. Desempata alternando a matéria em relação à última estudada.
        4. Garante a sequência lógica através do campo Topic.order.
        """
        # 1. Prioridade Máxima: Bloco em andamento (ordenado pelo sumário)
        block = db.query(StudyBlock)\
            .join(Topic, StudyBlock.topic_id == Topic.id)\
            .filter(StudyBlock.status == BlockStatus.EM_ANDAMENTO)\
            .order_by(Topic.order.asc(), StudyBlock.started_at.asc(), StudyBlock.id.asc())\
            .first()

        if block:
            return block

        # Se não foi passado o last_subject_id, busca a matéria do último bloco concluído
        if last_subject_id is None:
            last_completed = db.query(PdfDocument.subject_id)\
                .join(Topic, Topic.pdf_id == PdfDocument.id)\
                .join(StudyBlock, StudyBlock.topic_id == Topic.id)\
                .filter(StudyBlock.status == BlockStatus.CONCLUIDO)\
                .order_by(StudyBlock.completed_at.desc())\
                .first()
            if last_completed:
                last_subject_id = last_completed[0]

        # 2. Busca IDs de matérias que possuem blocos PENDENTES
        subjects_with_pending = db.query(Subject.id)\
            .join(PdfDocument, PdfDocument.subject_id == Subject.id)\
            .join(Topic, Topic.pdf_id == PdfDocument.id)\
            .join(StudyBlock, StudyBlock.topic_id == Topic.id)\
            .filter(StudyBlock.status == BlockStatus.PENDENTE)\
            .distinct().all()

        if not subjects_with_pending:
            return None  # Todos os blocos de todas as matérias foram concluídos!

        pending_subject_ids = [s[0] for s in subjects_with_pending]

        # Se houver apenas 1 matéria com pendências, escolhe ela diretamente
        if len(pending_subject_ids) == 1:
            target_subject_id = pending_subject_ids[0]
        else:
            # 3. Contagem Inteligente de Blocos Concluídos por Matéria apenas entre as pendentes
            # Usamos uma subquery ou agregação direta focada na tabela de blocos
            completed_counts_subquery = db.query(
                PdfDocument.subject_id.label('subject_id'),
                func.count(StudyBlock.id).label('completed_count')
            )\
                .join(Topic, Topic.pdf_id == PdfDocument.id)\
                .join(StudyBlock, StudyBlock.topic_id == Topic.id)\
                .filter(StudyBlock.status == BlockStatus.CONCLUIDO)\
                .group_by(PdfDocument.subject_id)\
                .subquery()

            # Monta a consulta de escolha da matéria aplicando a regra de rotação e penalidade
            target_subject = db.query(
                Subject.id,
                func.coalesce(completed_counts_subquery.c.completed_count, 0).label('completed_count'),
                case((Subject.id == last_subject_id, 1), else_=0).label('is_last')
            )\
                .outerjoin(completed_counts_subquery, Subject.id == completed_counts_subquery.c.subject_id)\
                .filter(Subject.id.in_(pending_subject_ids))\
                .order_by(
                    func.coalesce(completed_counts_subquery.c.completed_count, 0).asc(),
                    case((Subject.id == last_subject_id, 1), else_=0).asc(),
                    Subject.id.asc()
                )\
                .first()

            target_subject_id = target_subject[0] if target_subject else pending_subject_ids[0]

        # 4. Retorna o primeiro bloco PENDENTE da matéria escolhida RESPEITANDO A ORDEM DOS TÓPICOS
        next_block = db.query(StudyBlock)\
            .select_from(StudyBlock)\
            .join(Topic, StudyBlock.topic_id == Topic.id)\
            .join(PdfDocument, Topic.pdf_id == PdfDocument.id)\
            .filter(
                PdfDocument.subject_id == target_subject_id,
                StudyBlock.status == BlockStatus.PENDENTE
            )\
            .order_by(Topic.order.asc(), StudyBlock.page_start.asc(), StudyBlock.id.asc())\
            .first()

        return next_block

    @staticmethod
    def update_progress(db: Session, block_id: int, current_page: int, complete: bool = False, seconds_added: int = 0):
        block = db.query(StudyBlock).filter(StudyBlock.id == block_id).first()
        if not block:
            return
        
        block.time_spent_seconds = (block.time_spent_seconds or 0) + seconds_added
        block.current_page = current_page

        if block.status == BlockStatus.PENDENTE:
            block.status = BlockStatus.EM_ANDAMENTO
            block.started_at = datetime.utcnow()

        if complete or current_page >= block.page_end:
            block.current_page = block.page_end
            block.status = BlockStatus.CONCLUIDO
            block.completed_at = datetime.utcnow()

        db.commit()

    @staticmethod
    def create_blocks_for_topic(db: Session, topic_id: int, mode: str = "topic", pages_per_block: int = 15):
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return

        if mode == "topic":
            b = StudyBlock(
                topic_id=topic.id,
                page_start=topic.page_start,
                page_end=topic.page_end,
                current_page=topic.page_start,
                status=BlockStatus.PENDENTE
            )
            db.add(b)
        elif mode == "pages":
            curr = topic.page_start
            while curr <= topic.page_end:
                end = min(curr + pages_per_block - 1, topic.page_end)
                b = StudyBlock(
                    topic_id=topic.id,
                    page_start=curr,
                    page_end=end,
                    current_page=curr,
                    status=BlockStatus.PENDENTE
                )
                db.add(b)
                curr = end + 1
        db.commit()

    @staticmethod
    @staticmethod
    def add_highlight(
        db, 
        pdf_id: int, 
        page_number: int, 
        selected_text: str, 
        color: str = "#FFFF00", 
        rect: tuple = None,
        x: float = None,
        y: float = None,
        width: float = None,
        height: float = None
    ):
        """Salva um novo grifo associado ao PDF e à página."""
        # Se rect foi passado como tupla (x, y, w, h), desempacota
        if rect and isinstance(rect, (tuple, list)) and len(rect) == 4:
            x, y, width, height = rect

        hl = Highlight(
            pdf_id=pdf_id,
            page_number=page_number,
            selected_text=selected_text,
            color=color,
            x=x, 
            y=y, 
            width=width, 
            height=height
        )
        db.add(hl)
        db.commit()
        db.refresh(hl)
        return hl

    @staticmethod
    def get_highlights_by_pdf(db, pdf_id: int, page_number: int = None):
        """Retorna todos os grifos de um PDF (ou filtrado por página)."""
        query = db.query(Highlight).filter(Highlight.pdf_id == pdf_id)
        if page_number is not None:
            query = query.filter(Highlight.page_number == page_number)
        return query.all()

    @staticmethod
    def delete_highlight(db, highlight_id: int):
        """Remove um grifo existente."""
        hl = db.query(Highlight).filter(Highlight.id == highlight_id).first()
        if hl:
            db.delete(hl)
            db.commit()
            return True
        return False