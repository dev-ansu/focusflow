"""
    Configurações globais da aplicação (FocusFlow).
    Inspirado no padrão de configurações do Laravel.
"""

from dataclasses import dataclass, field
from pathlib import Path
import sys

# Diretório raiz do projeto

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass(frozen=TRUE)
class AppConfig:
    """ Configurações gerais do aplicativo. """

    # Identificação da aplicação
    APP_NAME: str = "FocusFlow"