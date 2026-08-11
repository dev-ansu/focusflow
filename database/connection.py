import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_NAME = "estudoflow.db"
Base = declarative_base()

def get_db_path():
    """
    Retorna o caminho do banco de dados.
    Se o app estiver empacotado (PyInstaller), salva o .db na pasta do executável.
    Caso contrário, salva na raiz do projeto em desenvolvimento.
    """
    if getattr(sys, 'frozen', False):
        # Executável compilado (.exe ou binário Linux)
        base_dir = os.path.dirname(sys.executable)
    else:
        # Ambiente de desenvolvimento (.py)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_dir, DB_NAME)

engine = create_engine(f"sqlite:///{get_db_path()}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)