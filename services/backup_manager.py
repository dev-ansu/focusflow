import shutil
from pathlib import Path
from config.app import config
from database.connection import get_db_path


class BackupManager:
    @staticmethod
    def export_backup(destination_zip_path: str | Path):
        """Exporta o arquivo de banco de dados SQLite para um arquivo ZIP."""
        db_path = Path(get_db_path())

        if not db_path.exists():
            raise FileNotFoundError("Banco de dados não encontrado para backup.")

        dest_path = Path(destination_zip_path)
        base_dir = dest_path.parent
        # Remove a extensão .zip se ela for passada no caminho
        base_name = (
            dest_path.stem
            if dest_path.name.endswith(".zip")
            else dest_path.name
        )

        # Garante que o diretório de destino exista
        base_dir.mkdir(parents=True, exist_ok=True)

        # Pasta temporária para empacotamento
        temp_dir = base_dir / "temp_backup"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copia o banco usando o DB_NAME definido nas configurações globais
            shutil.copy(db_path, temp_dir / config.DB_NAME)

            # Gera o arquivo .zip
            shutil.make_archive(
                base_name=str(base_dir / base_name),
                format="zip",
                root_dir=temp_dir,
            )
        finally:
            # Limpa o diretório temporário sempre, mesmo se houver erro
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    @staticmethod
    def import_backup(zip_path: str | Path):
        """Importa e restaura o arquivo de banco de dados SQLite a partir de um ZIP."""
        zip_path = Path(zip_path)
        db_path = Path(get_db_path())

        if not zip_path.exists():
            raise FileNotFoundError(
                f"Arquivo de backup não encontrado em: {zip_path}"
            )

        temp_dir = zip_path.parent / "temp_restore"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Descompacta o arquivo ZIP na pasta temporária
            shutil.unpack_archive(zip_path, temp_dir, "zip")

            # Busca dinamicamente pelo nome do DB configurado no app.py
            extracted_db = temp_dir / config.DB_NAME

            if extracted_db.exists():
                # Garante que a pasta final do banco exista antes de copiar
                db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(extracted_db, db_path)
            else:
                raise ValueError(
                    f"Arquivo de backup inválido: '{config.DB_NAME}' não foi encontrado no ZIP."
                )
        finally:
            # Garante que a pasta temporária seja removida após a operação
            if temp_dir.exists():
                shutil.rmtree(temp_dir)