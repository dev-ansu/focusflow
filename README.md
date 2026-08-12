# 📚 FocusFlow

> Um gerenciador de estudos desktop moderno, focado em ciclos de estudo, leitura de PDFs, anotações e Caderno de Erros.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PySide6](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt6-green?logo=qt)
![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20SQLAlchemy-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

# 🎯 FocusFlow

> Um aplicativo desktop moderno, modular e inteligente para gerenciamento de ciclos de estudos e leitura ativa de PDFs.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-green.svg)](https://pyside.org/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20SQLAlchemy-orange.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)


---

## 📌 Sobre o Projeto

O **FocusFlow** foi desenvolvido para centralizar toda a rotina de estudos de concursos, vestibulares e graduação em um único aplicativo desktop local, rápido e sem distrações. 

Ele elimina a necessidade de usar planilhas complexas, leitores de PDF genéricos e apps de notas separados, integrando tudo num fluxo de trabalho otimizado.

---

## ✨ Principais Funcionalidades

### 🔄 1. Ciclo de Estudos e Matérias
- Organização de matérias com pesos, horas recomendadas e progresso visual.
- Geração automática e dinâmica do ciclo de estudos.

### 📖 2. Leitor de PDF Integrado & Mapeador de Sumário
- Leitor de PDF com suporte a grifos e criação de anotações por página.
- **Detecção Inteligente de Índice/Sumário (TOC):** Mapeia tópicos e capítulos do PDF automaticamente.

### ❌ 3. Caderno de Erros (Question Error Notebook)
- Registro detalhado de questões incorretas (Enunciado, Explicação, Banca e Matéria).
- Filtros por matéria e navegação rápida direto para o item.

### 🔍 4. Busca Global Estilo *Command Palette* (`Ctrl+F`)
- Busca instantânea e unificada em todo o aplicativo:
  - 📚 Matérias
  - 🔖 Tópicos / Capítulos
  - ❌ Enunciados e bancas do Caderno de Erros
  - 📝 Anotações e 🖍️ Grifos do leitor

### 📊 5. Dashboard & Estatísticas
- Visão geral do tempo estudado, distribuição por matéria e métricas do ciclo.

### ⚙️ 6. Gestão de Dados & Backup
- Exportação e importação de **Backup completo (.zip)** com PDFs e dados salvos.
- Painel de estatísticas de banco de dados e zona de reset seguro.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Interface Gráfica (GUI):** PySide6 (Qt for Python)
- **Banco de Dados & ORM:** SQLite + SQLAlchemy
- **Processamento de PDFs:** PyMuPDF (FitZ)
- **Design/Tema:** Custom QSS (Catppuccin Macchiato Palette)

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
- Python 3.10 ou superior instalado.

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone (https://github.com/dev-ansu/FocusFlow.git)
   cd FocusFlow

2. **Crie e ative um ambiente virtual (venv):**

    ```Bash

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    venv\Scripts\activate

3. **Instale as dependências:**

    ```Bash
    pip install -r requirements.txt

4. **Execute a aplicação:**

    ```Bash
    python3 main.py

📂 Estrutura do Projeto
   
    FocusFlow/
    ├── database/         # Conexão SQLite e inicialização das tabelas
    ├── models/           # Modelos SQLAlchemy (Subject, Note, QuestionError, etc.)
    ├── services/         # Parsers de PDF, leitores de TOC e BackupManager
    ├── ui/               # Views e Modais em PySide6
    │   ├── dashboard.py
    │   ├── error_notebook.py
    │   ├── global_search_dialog.py
    │   ├── reader.py
    │   ├── settings.py
    │   └── subjects.py
    ├── main.py           # Ponto de entrada do aplicativo
    └── requirements.txt  # Dependências do projeto
