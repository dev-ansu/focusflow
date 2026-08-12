import os
import sys
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.app import config

Base = declarative_base()


def get_db_path() -> Path:
    """
    Retorna o caminho do banco de dados.
    Se o app estiver empacotado (PyInstaller), salva na pasta do executável.
    Caso contrário, utiliza o diretório de dados configurado no AppConfig.
    """
    if getattr(sys, "frozen", False):
        # Executável compilado (.exe ou binário Linux)
        base_dir = Path(sys.executable).parent
        return base_dir / config.DB_NAME

    # Ambiente de desenvolvimento (.py) - Usa o DATA_DIR da config
    return config.DATA_DIR / config.DB_NAME


# Garante que os diretórios de dados existam no disco
config.ensure_directories_exist()

db_file_path = get_db_path()

# Configuração da engine usando o caminho resolvido
engine = create_engine(
    f"sqlite:///{db_file_path}",
    connect_args={"check_same_thread": False},
    echo=config.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_migrations():
    """Garante que colunas novas sejam adicionadas em bancos SQLite já existentes."""
    if db_file_path.exists():
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        # Verifica se a tabela 'subjects' já foi criada no banco
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='subjects';"
        )
        if cursor.fetchone():
            # Obtém as colunas da tabela 'subjects'
            cursor.execute("PRAGMA table_info(subjects);")
            columns = [column[1] for column in cursor.fetchall()]

            # Adiciona a coluna 'order' caso ela ainda não exista
            if "order" not in columns:
                cursor.execute(
                    'ALTER TABLE subjects ADD COLUMN "order" INTEGER DEFAULT 0;'
                )
                conn.commit()

        conn.close()


def init_db():
    """Inicializa as migrações e cria as tabelas no SQLite."""
    run_migrations()
    Base.metadata.create_all(bind=engine)