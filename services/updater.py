import os
import sys
import platform
import subprocess
import zipfile
import tarfile
import tempfile
import requests
from pathlib import Path
from PySide6.QtCore import QThread, Signal

GITHUB_REPO = "dev-ansu/focusflow"


def get_current_version() -> str:
    """Busca a versão injetada pelo CI/CD no release_config ou assume fallback."""
    try:
        from config.release_config import APP_VERSION
        return APP_VERSION.lstrip("v")
    except ImportError:
        return os.environ.get("APP_VERSION", "1.0.0").lstrip("v")

def is_frozen() -> bool:
    """Retorna True se a aplicação estiver rodando como executável (PyInstaller)."""
    return getattr(sys, 'frozen', False)

class UpdateCheckerWorker(QThread):
    """Thread em segundo plano para não congelar a UI durante a busca no GitHub."""
    finished_signal = Signal(bool, str, str, str)  # (has_update, latest_version, download_url, asset_name)
    error_signal = Signal(str)

    

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=8)

            if response.status_code != 200:
                self.error_signal.emit("Não foi possível obter informações da última versão no GitHub.")
                return

            data = response.json()
            latest_version = data.get("tag_name", "v0.0.0").lstrip("v")
            current_version = get_current_version()

            # Procura pelo artefato correspondente ao SO do usuário
            current_os = platform.system().lower()
            download_url = ""
            asset_name = ""

            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if current_os == "windows" and name.endswith("Windows.zip"):
                    download_url = asset.get("browser_download_url")
                    asset_name = name
                    break
                elif current_os == "linux" and name.endswith("Linux.tar.gz"):
                    download_url = asset.get("browser_download_url")
                    asset_name = name
                    break

            # Comparação simples semântica (pode-se ajustar conforme padrão)
            if latest_version > current_version and download_url:
                self.finished_signal.emit(True, latest_version, download_url, asset_name)
            else:
                self.finished_signal.emit(False, current_version, "", "")

        except Exception as e:
            self.error_signal.emit(f"Erro ao buscar atualizações: {str(e)}")


def download_and_prepare_update(download_url: str, progress_callback=None) -> Path:
    """
    Baixa o pacote (.zip ou .tar.gz) da nuvem e extrai na pasta temporária do sistema.
    """
    temp_dir = Path(tempfile.gettempdir()) / "focusflow_update"
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    archive_path = temp_dir / ("update.zip" if download_url.endswith(".zip") else "update.tar.gz")

    response = requests.get(download_url, stream=True, timeout=30)
    response.raise_for_status()

    with open(archive_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    extracted_dir = temp_dir / "extracted"
    extracted_dir.mkdir(exist_ok=True)

    if archive_path.name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extracted_dir)
    else:
        with tarfile.open(archive_path, "r:gz") as tar_ref:
            tar_ref.extractall(extracted_dir)

    return extracted_dir


def launch_updater_script_and_exit(extracted_dir: Path):
    """
    Cria um script temporário para fechar o app, substituir os arquivos no diretório 
    de instalação e reabrir o FocusFlow atualizado.
    """
    app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
    current_os = platform.system().lower()

    # Localiza a subpasta extraída
    items = list(extracted_dir.iterdir())
    source_folder = items[0] if len(items) == 1 and items[0].is_dir() else extracted_dir

    if current_os == "windows":
        script_path = extracted_dir / "update.bat"
        exe_path = sys.executable

        # Bat script para Windows: aguarda 2 segs, copia e reabre
        bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
xcopy /E /Y /I "{source_folder}\\*" "{app_dir}"
start "" "{exe_path}"
del "%~f0"
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        subprocess.Popen(["cmd.exe", "/c", str(script_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)

    else:
        # Bash script para Linux
        script_path = extracted_dir / "update.sh"
        sh_content = f"""#!/usr/bin/env bash
sleep 2
cp -rf "{source_folder}"/* "{app_dir}/"
chmod +x "{app_dir}/FocusFlow"* 2>/dev/null || true
if [ -f "{app_dir}/_internal/FocusFlow.sh" ]; then
    chmod +x "{app_dir}/_internal/FocusFlow.sh"
fi
nohup "{sys.executable}" > /dev/null 2>&1 &
rm "$0"
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(sh_content)

        os.chmod(script_path, 0o755)
        subprocess.Popen(["/usr/bin/env", "bash", str(script_path)])

    sys.exit(0)