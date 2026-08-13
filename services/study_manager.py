from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from config.app import config
from models.models import (
    BlockStatus,
    Highlight,
    PdfDocument,
    StudyBlock,
    Subject,
    Topic,
)


class StudyManager:

    @staticmethod
    def get_next_block_to_study(
        db: Session, last_subject_id: Optional[int] = None
    ) -> Optional[StudyBlock]:
        """
        Retorna o próximo bloco de estudo seguindo o Ciclo Sequencial de Matérias:
        1. Se houver bloco EM_ANDAMENTO, retoma ele.
        2. Alterna para a PRÓXIMA matéria pendente na fila (Subject.order e Subject.id).
        3. Pega o PRIMEIRO bloco PENDENTE da matéria selecionada.
        """
        # 1. Se existir algum bloco EM_ANDAMENTO, prioriza ele
        in_progress_block = (
            db.query(StudyBlock)
            .join(Topic, StudyBlock.topic_id == Topic.id)
            .join(PdfDocument, Topic.pdf_id == PdfDocument.id)
            .join(Subject, PdfDocument.subject_id == Subject.id)
            .filter(StudyBlock.status == BlockStatus.EM_ANDAMENTO)
            .order_by(
                Subject.order.asc(),
                PdfDocument.id.asc(),
                Topic.order.asc(),
                StudyBlock.page_start.asc(),
                StudyBlock.id.asc(),
            )
            .first()
        )

        if in_progress_block:
            return in_progress_block

        # 2. Busca todas as matérias ordenadas que contêm pelo menos 1 bloco PENDENTE
        subjects_with_pending = (
            db.query(Subject)
            .join(PdfDocument, PdfDocument.subject_id == Subject.id)
            .join(Topic, Topic.pdf_id == PdfDocument.id)
            .join(StudyBlock, StudyBlock.topic_id == Topic.id)
            .filter(StudyBlock.status == BlockStatus.PENDENTE)
            .order_by(Subject.order.asc(), Subject.id.asc())
            .distinct()
            .all()
        )

        if not subjects_with_pending:
            return None  # Todos os blocos do sistema foram concluídos!

        target_subject = None

        # 3. Avança para a PRÓXIMA matéria estritamente após last_subject_id
        if last_subject_id is not None:
            last_subj = db.query(Subject).filter(Subject.id == last_subject_id).first()
            if last_subj:
                # Procura a primeira matéria da fila com (order, id) estritamente maior que a anterior
                target_subject = next(
                    (
                        s for s in subjects_with_pending 
                        if (s.order, s.id) > (last_subj.order, last_subj.id)
                    ),
                    None
                )

        # Se last_subject_id era a última do ciclo (ou None), volta para a 1ª matéria pendente da fila
        if not target_subject:
            target_subject = subjects_with_pending[0]

        # 4. Retorna o primeiro bloco PENDENTE da matéria escolhida
        return (
            db.query(StudyBlock)
            .join(Topic, StudyBlock.topic_id == Topic.id)
            .join(PdfDocument, Topic.pdf_id == PdfDocument.id)
            .join(Subject, PdfDocument.subject_id == Subject.id)
            .filter(
                Subject.id == target_subject.id,
                StudyBlock.status == BlockStatus.PENDENTE,
            )
            .order_by(
                PdfDocument.id.asc(),
                Topic.order.asc(),
                StudyBlock.page_start.asc(),
                StudyBlock.id.asc(),
            )
            .first()
        )

    @staticmethod
    def update_progress(
        db: Session,
        block_id: int,
        current_page: int,
        complete: bool = False,
        seconds_added: int = 0,
    ) -> Optional[StudyBlock]:
        """Atualiza a página atual, cronômetro e status do bloco de estudos."""
        block = db.query(StudyBlock).filter(StudyBlock.id == block_id).first()
        if not block:
            return None

        try:
            block.time_spent_seconds = (
                block.time_spent_seconds or 0
            ) + seconds_added
            block.current_page = current_page

            if block.status == BlockStatus.PENDENTE:
                block.status = BlockStatus.EM_ANDAMENTO
                block.started_at = datetime.now(timezone.utc)

            # Usa a regra de auto avanço da config global caso acione o final da página
            should_complete = complete or (
                config.AUTO_ADVANCE_BLOCK and current_page >= block.page_end
            )

            if should_complete:
                block.current_page = block.page_end
                block.status = BlockStatus.CONCLUIDO
                block.completed_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(block)
            return block
        except Exception as e:
            db.rollback()
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] Erro ao atualizar progresso do bloco {block_id}: {e}"
                )
            raise e

    @staticmethod
    def create_blocks_for_topic(
        db: Session,
        topic_id: int,
        mode: str = "topic",
        pages_per_block: int = 15,
    ) -> None:
        """Divide um tópico do PDF em blocos de estudo no banco de dados."""
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return

        try:
            if mode == "topic":
                b = StudyBlock(
                    topic_id=topic.id,
                    page_start=topic.page_start,
                    page_end=topic.page_end,
                    current_page=topic.page_start,
                    status=BlockStatus.PENDENTE,
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
                        status=BlockStatus.PENDENTE,
                    )
                    db.add(b)
                    curr = end + 1

            db.commit()
        except Exception as e:
            db.rollback()
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] Erro ao criar blocos para o tópico {topic_id}: {e}"
                )
            raise e

    @staticmethod
    def add_highlight(
        db: Session,
        pdf_id: int,
        page_number: int,
        selected_text: str,
        color: str = "#FFFF00",
        rect: Optional[Union[Tuple[float, float, float, float], List[float]]] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> Highlight:
        """Salva um novo grifo associado ao PDF e à página."""
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
            height=height,
        )

        try:
            db.add(hl)
            db.commit()
            db.refresh(hl)
            return hl
        except Exception as e:
            db.rollback()
            if config.DEBUG:
                print(f"[{config.APP_NAME}] Erro ao salvar grifo no PDF {pdf_id}: {e}")
            raise e

    @staticmethod
    def get_highlights_by_pdf(
        db: Session, pdf_id: int, page_number: Optional[int] = None
    ) -> List[Highlight]:
        """Retorna todos os grifos de um PDF (ou filtrados por página)."""
        query = db.query(Highlight).filter(Highlight.pdf_id == pdf_id)
        if page_number is not None:
            query = query.filter(Highlight.page_number == page_number)
        return query.all()

    @staticmethod
    def delete_highlight(db: Session, highlight_id: int) -> bool:
        """Remove um grifo existente."""
        hl = db.query(Highlight).filter(Highlight.id == highlight_id).first()
        if hl:
            try:
                db.delete(hl)
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                if config.DEBUG:
                    print(
                        f"[{config.APP_NAME}] Erro ao deletar grifo {highlight_id}: {e}"
                    )
                raise e
        return False