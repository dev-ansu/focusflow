import shutil
import zipfile
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
        base_name = (
            dest_path.stem
            if dest_path.name.endswith(".zip")
            else dest_path.name
        )

        base_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = base_dir / "temp_backup"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy(db_path, temp_dir / config.DB_NAME)
            shutil.make_archive(
                base_name=str(base_dir / base_name),
                format="zip",
                root_dir=temp_dir,
            )
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    @staticmethod
    def import_backup(zip_path: str | Path):
        """
        Importa e restaura o arquivo de banco de dados SQLite a partir de um ZIP,
        com proteção estrita contra Directory Traversal / Zip Slip.
        """
        zip_path = Path(zip_path)
        db_path = Path(get_db_path())

        if not zip_path.exists():
            raise FileNotFoundError(
                f"Arquivo de backup não encontrado em: {zip_path}"
            )

        temp_dir = (zip_path.parent / "temp_restore").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Extração segura com validação de Zip Slip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    # Resolve o caminho final onde o arquivo seria gravado
                    target_path = (temp_dir / member.filename).resolve()

                    # Proteção Zip Slip: garante que o arquivo resolvido pertença estritamente à temp_dir
                    if not str(target_path).startswith(str(temp_dir)):
                        raise SecurityError(
                            f"Tentativa de Zip Slip detectada! O arquivo '{member.filename}' "
                            "tenta acessar caminhos fora do diretório permitido."
                        )

                    zip_ref.extract(member, temp_dir)

            # Busca dinamicamente pelo nome do DB configurado no app.py
            extracted_db = temp_dir / config.DB_NAME

            if extracted_db.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(extracted_db, db_path)
            else:
                raise ValueError(
                    f"Arquivo de backup inválido: '{config.DB_NAME}' não foi encontrado no ZIP."
                )
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)


class SecurityError(Exception):
    """Exceção para violações de segurança e integridade de arquivos."""
    pass