"""
    Configurações globais da aplicação (FocusFlow).
    Inspirado no padrão de configurações do Laravel.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Diretório raiz do código-fonte do projeto
BASE_DIR = Path(__file__).resolve().parent.parent


def get_user_data_dir(app_slug: str) -> Path:
    """
    Retorna a pasta padrão de dados do sistema operacional do usuário.
    Garante que o banco de dados e arquivos persistam entre atualizações do app.
    
    - Windows: C:\\Users\\<usuario>\\AppData\\Roaming\\FocusFlow
    - Linux:   /home/<usuario>/.local/share/FocusFlow
    """
    if sys.platform == "win32":
        base_path = Path(os.environ.get("APPDATA", Path.home()))
    else:
        # Linux / XDG Data Home
        base_path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    return base_path / app_slug


@dataclass(frozen=True)
class AppConfig:
    """ Configurações gerais do aplicativo. """

    # Identificação da aplicação
    APP_NAME: str = "FocusFlow"
    APP_SLUG: str = "focusFlow"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Gerenciador de Ciclos de Estudos e Leitor de PDF"
    AUTHOR: str = "Anderson Souza"

    BASE_DIR: Path = BASE_DIR

    # Ambiente
    ENV: str = "development"
    DEBUG: bool = True

    # Diretórios persitentes no sistema do usuário (não são apagados em atualizações)
    DATA_DIR: Path = field(default_factory=lambda: get_user_data_dir("FocusFlow") / "data")
    BACKUP_DIR: Path = field(default_factory=lambda: get_user_data_dir("FocusFlow") / "backups")
    LOG_DIR: Path = field(default_factory=lambda: get_user_data_dir("FocusFlow") / "logs")

    # Banco de dados
    DB_NAME: str = "focusflow.db"

    @property
    def DB_URL(self) -> str:
        """ Retorna a URI formatada do SQLAlchemy para SQLite local. """
        db_path = self.DATA_DIR / self.DB_NAME
        return f"sqlite:///{db_path}"

    # Configurações do leitor de PDF / Interface
    DEFAULT_ZOOM_LEVEL: float = 1.2
    AUTO_ADVANCE_BLOCK: bool = True
    THEME: str = "dark"  # dark, light

    def ensure_directories_exist(self) -> None:
        """ Garante que as pastas essenciais do sistema existam no disco. """
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)


# Instância global única (Singleton) para ser importada em qualquer lugar
config = AppConfig()

# Garante que os diretórios necessários sejam criados ao carregar a config
config.ensure_directories_exist()