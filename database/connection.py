import sqlite3
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.app import config

Base = declarative_base()


def get_db_path() -> Path:
    """
    Retorna o caminho completo do arquivo .db dentro do diretório do usuário.
    Garante persistência de dados mesmo ao atualizar o executável (.exe ou Linux).
    """
    return config.DATA_DIR / config.DB_NAME


# Garante que as pastas do usuário (%APPDATA% / .local/share) existam no disco
config.ensure_directories_exist()

db_file_path = get_db_path()

# Configuração da engine do SQLAlchemy
engine = create_engine(
    f"sqlite:///{db_file_path}",
    connect_args={"check_same_thread": False},
    echo=config.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_migrations():
    """
    Garante que colunas novas sejam adicionadas em bancos SQLite existentes
    sem quebrar o banco de dados do usuário.
    """
    if not db_file_path.exists():
        return

    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()

    try:
        # 1. Migração para 'subjects' (coluna 'order')
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subjects';")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(subjects);")
            columns = [column[1] for column in cursor.fetchall()]
            if "order" not in columns:
                cursor.execute('ALTER TABLE subjects ADD COLUMN "order" INTEGER DEFAULT 0;')
                conn.commit()

        # 2. Migração para 'question_errors' (coluna 'is_resolved')
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='question_errors';")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(question_errors);")
            columns = [column[1] for column in cursor.fetchall()]
            if "is_resolved" not in columns:
                cursor.execute('ALTER TABLE question_errors ADD COLUMN "is_resolved" BOOLEAN DEFAULT 0;')
                conn.commit()

    except Exception as e:
        print(f"[Migration Warning] Erro durante auto-migração: {e}")
    finally:
        conn.close()


def init_db():
    """Inicializa as migrações e cria tabelas pendentes no SQLite."""
    run_migrations()
    Base.metadata.create_all(bind=engine)