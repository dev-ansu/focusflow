from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import QuestionError, ErrorReason

class ErrorManager:

    @staticmethod
    def create_error(db: Session, subject_id: int, statement: str, correct_answer: str, 
                     reason: ErrorReason, topic_id=None, banca=None, ano=None, 
                     user_answer=None, explanation=None):
        error_entry = QuestionError(
            subject_id=subject_id,
            topic_id=topic_id,
            banca=banca,
            ano=ano,
            statement=statement,
            user_answer=user_answer,
            correct_answer=correct_answer,
            reason=reason,
            explanation=explanation
        )
        db.add(error_entry)
        db.commit()
        db.refresh(error_entry)
        return error_entry

    @staticmethod
    def get_errors_filtered(db: Session, subject_id=None, topic_id=None, reason=None):
        query = db.query(QuestionError)
        
        if subject_id:
            query = query.filter(QuestionError.subject_id == subject_id)
        if topic_id:
            query = query.filter(QuestionError.topic_id == topic_id)
        if reason:
            query = query.filter(QuestionError.reason == reason)
            
        return query.order_by(QuestionError.created_at.desc()).all()

    @staticmethod
    def get_error_statistics(db: Session):
        """Retorna a contagem de erros agrupada por Matéria e por Motivo."""
        by_subject = db.query(
            QuestionError.subject_id, 
            func.count(QuestionError.id)
        ).group_by(QuestionError.subject_id).all()

        by_reason = db.query(
            QuestionError.reason, 
            func.count(QuestionError.id)
        ).group_by(QuestionError.reason).all()

        return {"by_subject": by_subject, "by_reason": by_reason}