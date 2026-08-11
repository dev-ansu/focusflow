# 📚 EstudoFlow

> **EstudoFlow** é um aplicativo desktop moderno para organização e acompanhamento de rotinas de estudo. Ele permite gerenciar matérias, organizar tópicos por ciclos, importar materiais em PDF com detecção de sumário (TOC), dividir leituras em blocos e realizar estudos em um leitor integrado com marca-texto, anotações e exportação de resumos.

---

## 🚀 Funcionalidades Principais

* **📊 Dashboard de Desempenho:** Acompanhamento visual do progresso de estudos, tempo dedicado e blocos pendentes/concluídos.
* **📚 Gestão de Matérias e Ciclos:** Organização hierárquica por matérias, tópicos e subtópicos com reordenação via *Drag & Drop*.
* **📥 Importação Inteligente de PDFs:**
  * Reconhecimento automático da estrutura de sumário (TOC) e metadados dos arquivos.
  * Divisão flexível de PDFs em **blocos de leitura** por metas de páginas.
* **📖 Leitor de PDF Integrado:**
  * Leitura nativa com suporte a **marca-texto (grifos)** e inclusão de **anotações** vinculadas às páginas.
  * Botão de início rápido (`▶️ Estudar Bloco`) ou acionamento via duplo clique nos tópicos/blocos.
* **🔍 Busca Global (`Ctrl + F`):** Pesquisa rápida por termos em toda a estrutura de matérias e tópicos com navegação automática.
* **📝 Exportação de Anotações:** Geração automática de cadernos de resumo (com grifos e anotações) exportáveis nos formatos **Markdown (`.md`)** e **Texto Puro (`.txt`)**.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Interface Gráfica (GUI):** PySide6 (Qt for Python)
* **Processamento de PDF:** PyMuPDF (`fitz`)
* **Banco de Dados & ORM:** SQLite3 + SQLAlchemy
* **Compilação / Empacotamento:** PyInstaller

---

## 📂 Estrutura do Projeto

```text
EstudoFlow/
├── database/            # Conexão e configurações do banco SQLite
├── models/              # Modelos de dados ORM (SQLAlchemy)
├── services/            # Serviços de detecção de TOC, parsing de PDF e regras de negócio
├── ui/                  # Componentes de interface e janelas (PySide6)
│   ├── dashboard.py
│   ├── global_search_dialog.py
│   ├── main_window.py
│   ├── pdf_import.py
│   ├── reader.py
│   ├── settings.py
│   ├── study_session.py
│   ├── subjects.py
│   └── toc_review.py
├── main.py              # Ponto de entrada da aplicação
└── requirements.txt     # Dependências do projeto

💻 Como Rodar em Ambiente de Desenvolvimento
Pré-requisitos
Python 3.10+ instalado.

Passo a Passo
Clone o repositório:

Bash
git clone [https://github.com/seu-usuario/estudoflow.git](https://github.com/seu-usuario/estudoflow.git)
cd estudoflow
Crie e ative um ambiente virtual (venv):

Linux/macOS:

Bash
python3 -m venv venv
source venv/bin/activate
Windows:

DOS
python -m venv venv
venv\Scripts\activate
Instale as dependências:

Bash
pip install -r requirements.txt
Execute a aplicação:

Bash
python main.py
📦 Como Gerar o Executável Standalone (PyInstaller)
🐧 No Linux (Linux Mint / Ubuntu)
Garanta que as dependências base do X11/XCB estejam instaladas:

Bash
sudo apt update
sudo apt install -y libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0
Gere o executável no terminal:

Bash
pyinstaller --noconfirm --onedir --windowed \
  --name "EstudoFlow" \
  --add-data "database:database" \
  --collect-all PySide6 \
  main.py
O executável final estará disponível em: dist/EstudoFlow/EstudoFlow.

🪟 No Windows
Execute no Prompt de Comando (cmd):

DOS
pyinstaller --noconfirm --onedir --windowed ^
  --name "EstudoFlow" ^
  --add-data "database;database" ^
  --collect-all PySide6 ^
  main.py
O arquivo executável estará disponível em: dist\EstudoFlow\EstudoFlow.exe.

📄 Licença
Este projeto é disponibilizado para fins de organização pessoal de estudos.