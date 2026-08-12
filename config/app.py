"""
    Configurações globais da aplicação (FocusFlow).
    Inspirado no padrão de configurações do Laravel.
"""

from dataclasses import dataclass, field
from pathlib import Path
import sys

# Diretório raiz do projeto

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class AppConfig:
    """ Configurações gerais do aplicativo. """

    # Identificação da aplicação
    APP_NAME: str = "FocusFlow"
    APP_SLUG: str = "focusFlow"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Gerenciador de Ciclos de Estudos e Leitor de PDF"
    AUTHOR: str = "Anderson Souza"

    # Ambiente
    ENV: str = "development"
    DEBUG: str = True

    # Diretórios do sistema
    DATA_DIR: Path = field(default_factory=lambda: BASE_DIR / "data")
    BACKUP_DIR: Path = field(default_factory=lambda: BASE_DIR / "backups")
    LOG_DIR: Path = field(default_factory=lambda: BASE_DIR / "logs")

    # Banco de dados
    DB_NAME: str = "focusflow.db"

    @property
    def DB_URL(self) -> str:
        """ Retorna a URI formatada do SQLAchemy para SQLite local. """
        db_path = self.DATA_DIR / self.DB_NAME
        return f"sqlite:///{db_path}"

    # Configurações do leitor de PDF / Interface

    DEFAULT_ZOOM_LEVEL: float = 1.2
    AUTO_ADVANCE_BLOCK: bool = True
    THEME: str = "dark" # dark, light

    def ensure_directories_exist(self) -> None:
        """ Garante que as pastas essenciais do sistema existam no disco. """
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

# Instância global única (Singleton) para ser importada em qualquer lugar
config = AppConfig()

# Garante que os diretórios necessários sejam criados ao carregar a config
config.ensure_directories_exist()
