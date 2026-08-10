import json
import shutil
import os
from database.connection import get_db_path

class BackupManager:
    @staticmethod
    def export_backup(destination_zip_path: str):
        db_path = get_db_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError("Banco de dados não encontrado para backup.")
        
        base_dir = os.path.dirname(destination_zip_path)
        base_name = os.path.basename(destination_zip_path).replace('.zip', '')
        
        # Cria arquivo ZIP contendo o banco de dados
        temp_dir = os.path.join(base_dir, "temp_backup")
        os.makedirs(temp_dir, exist_ok=True)
        shutil.copy(db_path, os.path.join(temp_dir, "estudoflow.db"))
        
        shutil.make_archive(os.path.join(base_dir, base_name), 'zip', temp_dir)
        shutil.rmtree(temp_dir)

    @staticmethod
    def import_backup(zip_path: str):
        db_path = get_db_path()
        temp_dir = os.path.join(os.path.dirname(zip_path), "temp_restore")
        shutil.unpack_archive(zip_path, temp_dir, 'zip')
        
        extracted_db = os.path.join(temp_dir, "estudoflow.db")
        if os.path.exists(extracted_db):
            shutil.copy(extracted_db, db_path)
            shutil.rmtree(temp_dir)
        else:
            shutil.rmtree(temp_dir)
            raise ValueError("Arquivo de backup inválido: 'estudoflow.db' não encontrado.")
