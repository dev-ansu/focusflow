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
        Retorna o próximo bloco de estudo seguindo o Ciclo Inteligente:
        1. Identifica a matéria do último bloco concluído (se não informada).
        2. Busca as matérias com blocos pendentes ou em andamento.
        3. Aplica a Rotação de Matérias: escolhe a matéria com menor número
           de blocos concluídos, alternando em relação à última estudada.
        4. Retorna o próximo bloco respeitando a sequência do sumário (Topic.order).
        """
        # 1. Identifica a matéria do último bloco concluído caso last_subject_id não venha informado
        if last_subject_id is None:
            last_completed = (
                db.query(PdfDocument.subject_id)
                .join(Topic, Topic.pdf_id == PdfDocument.id)
                .join(StudyBlock, StudyBlock.topic_id == Topic.id)
                .filter(StudyBlock.status == BlockStatus.CONCLUIDO)
                .order_by(StudyBlock.completed_at.desc(), StudyBlock.id.desc())
                .first()
            )
            if last_completed:
                last_subject_id = last_completed[0]

        # 2. Busca IDs das matérias que possuem blocos elegíveis (PENDENTE ou EM_ANDAMENTO)
        subjects_with_pending = (
            db.query(Subject.id)
            .join(PdfDocument, PdfDocument.subject_id == Subject.id)
            .join(Topic, Topic.pdf_id == PdfDocument.id)
            .join(StudyBlock, StudyBlock.topic_id == Topic.id)
            .filter(
                StudyBlock.status.in_([BlockStatus.PENDENTE, BlockStatus.EM_ANDAMENTO])
            )
            .distinct()
            .all()
        )

        if not subjects_with_pending:
            return None  # Todos os blocos de todas as matérias foram concluídos!

        pending_subject_ids = [s[0] for s in subjects_with_pending]

        # 3. Define a matéria alvo aplicando a regra do ciclo
        if len(pending_subject_ids) == 1:
            target_subject_id = pending_subject_ids[0]
        else:
            # Subquery de contagem de concluídos por matéria
            completed_counts_subquery = (
                db.query(
                    PdfDocument.subject_id.label("subject_id"),
                    func.count(StudyBlock.id).label("completed_count"),
                )
                .join(Topic, Topic.pdf_id == PdfDocument.id)
                .join(StudyBlock, StudyBlock.topic_id == Topic.id)
                .filter(StudyBlock.status == BlockStatus.CONCLUIDO)
                .group_by(PdfDocument.subject_id)
                .subquery()
            )

            # Seleciona a matéria com menor número de concluídos e força a troca em relação a last_subject_id
            target_subject = (
                db.query(
                    Subject.id,
                    func.coalesce(
                        completed_counts_subquery.c.completed_count, 0
                    ).label("completed_count"),
                    case((Subject.id == last_subject_id, 1), else_=0).label("is_last"),
                )
                .outerjoin(
                    completed_counts_subquery,
                    Subject.id == completed_counts_subquery.c.subject_id,
                )
                .filter(Subject.id.in_(pending_subject_ids))
                .order_by(
                    func.coalesce(
                        completed_counts_subquery.c.completed_count, 0
                    ).asc(),
                    case((Subject.id == last_subject_id, 1), else_=0).asc(),  # Alterna a matéria
                    Subject.id.asc(),
                )
                .first()
            )

            target_subject_id = (
                target_subject[0] if target_subject else pending_subject_ids[0]
            )

        # 4. Busca e retorna o próximo bloco da matéria escolhida
        # (Dá prioridade a blocos EM_ANDAMENTO dentro da matéria escolhida e depois aos PENDENTES)
        return (
            db.query(StudyBlock)
            .select_from(StudyBlock)
            .join(Topic, StudyBlock.topic_id == Topic.id)
            .join(PdfDocument, Topic.pdf_id == PdfDocument.id)
            .filter(
                PdfDocument.subject_id == target_subject_id,
                StudyBlock.status.in_([BlockStatus.EM_ANDAMENTO, BlockStatus.PENDENTE]),
            )
            .order_by(
                case((StudyBlock.status == BlockStatus.EM_ANDAMENTO, 0), else_=1).asc(),
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