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


def is_production() -> bool:
    """
    Identifica se a aplicação está rodando em modo de Produção.
    
    Critérios para Produção:
    1. O app foi empacotado como executável (ex: PyInstaller define sys.frozen = True).
    2. A variável de ambiente APP_ENV está explicitamente como 'production'.
    """
    is_frozen = getattr(sys, "frozen", False)
    env_var = os.environ.get("APP_ENV", "").lower()
    
    return is_frozen or env_var == "production"


def get_user_data_dir(app_slug: str, is_prod: bool) -> Path:
    """
    Retorna a pasta de dados do sistema baseada no ambiente.
    
    - Desenvolviemnto: Salva na raiz da pasta do projeto (`.dev_data/`)
    - Produção: Salva na pasta do sistema do usuário (%APPDATA% ou ~/.local/share)
    """
    if not is_prod:
        # No ambiente de dev, salva os dados localmente dentro do próprio projeto
        return BASE_DIR / ".dev_data"

    # No ambiente de produção, salva nos diretórios persistentes do S.O.
    if sys.platform == "win32":
        base_path = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base_path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    return base_path / app_slug


@dataclass(frozen=True)
class AppConfig:
    """ Configurações gerais do aplicativo. """

    # Determina o ambiente dinamicamente na inicialização
    IS_PROD: bool = field(default_factory=is_production)

    # Identificação da aplicação
    APP_NAME: str = "FocusFlow"
    APP_SLUG: str = "focusFlow"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Gerenciador de Ciclos de Estudos e Leitor de PDF"
    AUTHOR: str = "Anderson Souza"

    BASE_DIR: Path = BASE_DIR

    # Atribui dinamicamente o ENV e DEBUG com base no ambiente
    @property
    def ENV(self) -> str:
        return "production" if self.IS_PROD else "development"

    @property
    def DEBUG(self) -> bool:
        return not self.IS_PROD

    # Nome do banco dinâmico (opcional: previne misturar se mudar no dev)
    @property
    def DB_NAME(self) -> str:
        return "focusflow.db" if self.IS_PROD else "focusflow_dev.db"

    # Diretórios persistentes
    DATA_DIR: Path = field(init=False)
    BACKUP_DIR: Path = field(init=False)
    LOG_DIR: Path = field(init=False)

    def __post_init__(self):
        """ Inicializa os diretórios com base no status de produção. """
        root_data_dir = get_user_data_dir(self.APP_SLUG, self.IS_PROD)
        
        # Seta os atributos usando object.__setattr__ por conta do frozen=True no dataclass
        object.__setattr__(self, 'DATA_DIR', root_data_dir / "data")
        object.__setattr__(self, 'BACKUP_DIR', root_data_dir / "backups")
        object.__setattr__(self, 'LOG_DIR', root_data_dir / "logs")

    @property
    def DB_URL(self) -> str:
        """ Retorna a URI formatada do SQLAlchemy para SQLite local. """
        db_path = self.DATA_DIR / self.DB_NAME
        return f"sqlite:///{db_path}"

    # Configurações do leitor de PDF / Interface
    DEFAULT_ZOOM_LEVEL: float = 1.2
    AUTO_ADVANCE_BLOCK: bool = True
    THEME: str = "dark"

    def ensure_directories_exist(self) -> None:
        """ Garante que as pastas essenciais do sistema existam no disco. """
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)


# Instância global única (Singleton)
config = AppConfig()

# Garante que os diretórios necessários sejam criados ao carregar a config
config.ensure_directories_exist()