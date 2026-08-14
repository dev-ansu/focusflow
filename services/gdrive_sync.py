import os
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from config.app import config


class GDriveSyncService:
    def __init__(self):
        # 1. Escopos da API do Google Drive
        default_scope = "https://www.googleapis.com/auth/drive.appdata"
        self.scopes = [config.GDRIVE_SCOPES] if config.GDRIVE_SCOPES else [default_scope]

        # 2. Caminho para persistir os tokens da sessão do usuário
        self.token_path = config.DATA_DIR / "token.json"
        self.creds: Optional[Credentials] = None

    def _get_client_config(self) -> dict:
        """Monta a estrutura do client_config dinâmica utilizando o singleton config."""
        if not config.GDRIVE_CLIENT_ID or not config.GDRIVE_CLIENT_SECRET:
            raise ValueError(
                "Credenciais do Google Drive não configuradas. "
                "Defina GDRIVE_CLIENT_ID e GDRIVE_CLIENT_SECRET no seu arquivo .env"
            )

        return {
            "installed": {
                "client_id": config.GDRIVE_CLIENT_ID,
                "project_id": config.APP_SLUG,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": config.GDRIVE_CLIENT_SECRET,
                "redirect_uris": ["http://localhost"],
            }
        }

    def delete_cloud_database(self) -> bool:
        """Remove o arquivo de banco de dados da AppDataFolder no Google Drive."""
        if not self.is_authenticated():
            return False
        try:
            service = self._get_drive_service()
            query = f"name = '{config.DB_NAME}' and 'appDataFolder' in parents and trashed = false"
            results = service.files().list(q=query, spaces="appDataFolder", fields="files(id)").execute()
            files = results.get("files", [])
            
            for f in files:
                service.files().delete(fileId=f["id"]).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar banco remoto: {e}")
            return False
        
    def _load_credentials(self) -> None:
        """Carrega o token existente e renova se necessário, garantindo diretórios válidos."""
        config.ensure_directories_exist()

        if self.token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)
            except Exception as e:
                print(f"Erro ao ler arquivo de credenciais: {e}")
                self.creds = None

        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(self.creds.to_json())
            except Exception as e:
                print(f"Falha ao renovar token do Google Drive: {e}")
                self.creds = None

    def is_authenticated(self) -> bool:
        """Verifica se há credenciais válidas do usuário salvas."""
        self._load_credentials()
        return self.creds is not None and self.creds.valid

    def authenticate(self) -> bool:
        """Inicia o fluxo OAuth no navegador usando os dados em memória do config."""
        client_config = self._get_client_config()
        flow = InstalledAppFlow.from_client_config(client_config, self.scopes)

        try:
            self.creds = flow.run_local_server(
                port=0,
                timeout_seconds=60,
                authorization_prompt_message="Conclua a autorização no seu navegador..."
            )
        except Exception as e:
            self.creds = None
            raise TimeoutError("O login no navegador foi cancelado ou o tempo limite expirou.") from e

        if self.creds:
            config.ensure_directories_exist()
            with open(self.token_path, "w", encoding="utf-8") as token_file:
                token_file.write(self.creds.to_json())
            return True

        return False

    def logout(self) -> None:
        """Remove completamente a sessão local do usuário."""
        if self.token_path.exists():
            try:
                self.token_path.unlink()
            except Exception as e:
                print(f"Erro ao deletar o arquivo token.json: {e}")

        self.creds = None

    def _get_drive_service(self):
        """Inicializa e retorna o cliente da biblioteca oficial do Google Drive."""
        self._load_credentials()
        if not self.creds or not self.creds.valid:
            raise RuntimeError("Usuário não autenticado no Google Drive.")
        return build("drive", "v3", credentials=self.creds)

    def upload_database(self, local_db_path: Optional[str] = None, force: bool = False) -> bool:
        """Envia a versão local do banco de dados para a pasta appDataFolder se for mais recente ou forçada."""
        service = self._get_drive_service()
        
        db_file_path = local_db_path or str(config.DB_PATH)
        remote_filename = config.DB_NAME

        query = f"name = '{remote_filename}' and 'appDataFolder' in parents and trashed = false"
        results = service.files().list(q=query, spaces="appDataFolder", fields="files(id, modifiedTime)").execute()
        files = results.get("files", [])

        media = MediaFileUpload(db_file_path, mimetype="application/x-sqlite3", resumable=True)

        if files:
            file_id = files[0]["id"]

            if not force:
                remote_time_str = files[0].get("modifiedTime")
                if remote_time_str:
                    dt_remote = datetime.fromisoformat(remote_time_str.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
                    local_mtime = datetime.utcfromtimestamp(os.path.getmtime(db_file_path))
                    
                    if dt_remote > local_mtime:
                        print("Aviso: O banco da nuvem é mais recente que o local.")

            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                "name": remote_filename,
                "parents": ["appDataFolder"]
            }
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        return True

    def download_database(self, local_db_path: Optional[str] = None) -> bool:
        """Baixa o banco SQLite armazenado na nuvem e substitui o arquivo local com fallback de segurança."""
        service = self._get_drive_service()
        
        db_file_path = Path(local_db_path or str(config.DB_PATH))
        temp_db_path = db_file_path.with_suffix(".tmp")
        remote_filename = config.DB_NAME

        query = f"name = '{remote_filename}' and 'appDataFolder' in parents and trashed = false"
        results = service.files().list(q=query, spaces="appDataFolder", fields="files(id)").execute()
        files = results.get("files", [])

        if not files:
            raise FileNotFoundError("Nenhum backup em nuvem foi encontrado no seu Google Drive.")

        file_id = files[0]["id"]
        request = service.files().get_media(fileId=file_id)

        with open(temp_db_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        if temp_db_path.exists():
            temp_db_path.replace(db_file_path)

        return True
    
    def get_cloud_db_metadata(self) -> Optional[dict]:
        """Retorna os metadados (data de modificação e tamanho) do BD remoto na nuvem."""
        if not self.is_authenticated():
            return None
        try:
            service = self._get_drive_service()
            query = f"name = '{config.DB_NAME}' and 'appDataFolder' in parents and trashed = false"
            results = service.files().list(
                q=query, spaces="appDataFolder", fields="files(id, modifiedTime, size)"
            ).execute()
            files = results.get("files", [])
            if files:
                return files[0]
        except Exception as e:
            print(f"Erro ao buscar metadados da nuvem: {e}")
        return None