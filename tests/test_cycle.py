# test_cycle.py
from database.connection import SessionLocal
from services.study_manager import StudyManager
from models.models import StudyBlock, BlockStatus

def simulate_cycle():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("🔍 SIMULADOR DE ROTAÇÃO DE CICLO DE ESTUDOS")
        print("=" * 60)

        # Roda 5 simulações seguidas de recomendação
        for step in range(1, 6):
            block = StudyManager.get_next_block_to_study(db)

            if not block:
                print(f"\n[Passo {step}] 🎉 Todos os blocos de todas as matérias foram concluídos!")
                break

            # Dados do bloco recomendado
            subject_name = block.topic.pdf.subject.name
            topic_title = block.topic.title
            
            print(f"\n▶ PASSO {step} DE RECOMENDAÇÃO:")
            print(f"   • Matéria : {subject_name}")
            print(f"   • Tópico  : {topic_title}")
            print(f"   • Faixa   : Págs {block.page_start} a {block.page_end}")
            print(f"   • Status  : {block.status.value}")

            # Pergunta se deseja simular a conclusão deste bloco para ver o próximo
            ans = input("   👉 Simular conclusão deste bloco para ver o próximo? (s/n): ").strip().lower()
            
            if ans == 's':
                # Conclui o bloco usando seu próprio StudyManager
                StudyManager.update_progress(
                    db=db,
                    block_id=block.id,
                    current_page=block.page_end,
                    complete=True,
                    seconds_added=1800 # 30 min simulados
                )
                print(f"   ✅ Bloco #{block.id} marcado como CONCLUÍDO.")
            else:
                print("   ⏹️ Simulação interrompida.")
                break

    finally:
        db.close()
        print("\n" + "=" * 60)

if __name__ == "__main__":
    simulate_cycle()