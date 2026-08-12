from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.app import config
from models.models import ErrorReason, QuestionError


class ErrorManager:

    @staticmethod
    def create_error(
        db: Session,
        subject_id: int,
        statement: str,
        correct_answer: str,
        reason: ErrorReason,
        topic_id: Optional[int] = None,
        banca: Optional[str] = None,
        ano: Optional[int] = None,
        user_answer: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> QuestionError:
        """Cadastra um novo caderno/registro de erro no banco de dados."""
        error_entry = QuestionError(
            subject_id=subject_id,
            topic_id=topic_id,
            banca=banca,
            ano=ano,
            statement=statement,
            user_answer=user_answer,
            correct_answer=correct_answer,
            reason=reason,
            explanation=explanation,
        )

        try:
            db.add(error_entry)
            db.commit()
            db.refresh(error_entry)
            return error_entry
        except Exception as e:
            db.rollback()
            if config.DEBUG:
                print(f"[{config.APP_NAME}] Erro ao salvar caderno de erro: {e}")
            raise e

    @staticmethod
    def get_errors_filtered(
        db: Session,
        subject_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        reason: Optional[ErrorReason] = None,
    ) -> List[QuestionError]:
        """Retorna os registros de erro ordenados do mais recente ao mais antigo."""
        query = db.query(QuestionError)

        if subject_id:
            query = query.filter(QuestionError.subject_id == subject_id)
        if topic_id:
            query = query.filter(QuestionError.topic_id == topic_id)
        if reason:
            query = query.filter(QuestionError.reason == reason)

        return query.order_by(QuestionError.created_at.desc()).all()

    @staticmethod
    def get_error_statistics(db: Session) -> Dict[str, List[Any]]:
        """Retorna a contagem de erros agrupada por Matéria e por Motivo."""
        by_subject = (
            db.query(
                QuestionError.subject_id,
                func.count(QuestionError.id).label("total"),
            )
            .group_by(QuestionError.subject_id)
            .all()
        )

        by_reason = (
            db.query(
                QuestionError.reason,
                func.count(QuestionError.id).label("total"),
            )
            .group_by(QuestionError.reason)
            .all()
        )

        return {"by_subject": by_subject, "by_reason": by_reason}