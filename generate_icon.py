import os
from pathlib import Path
from PIL import Image, ImageDraw

def generate_focusflow_icons():
    # 1. Definir o diretório assets na raiz do projeto
    base_dir = Path(__file__).resolve().parent
    assets_dir = base_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    # 2. Resolução do ícone base (512x512 para alta qualidade)
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 3. Desenhar fundo com cantos arredondados (Dark Theme / Catppuccin style)
    # Azul/Roxo do FocusFlow
    bg_color = (30, 30, 46, 255)       # #1E1E2E (Fundo principal)
    accent_color = (137, 180, 250, 255) # #89B4FA (Azul de Destaque)
    inner_color = (205, 214, 244, 255)  # #CDD6F4 (Texto/Detalhes)

    # Fundo Arredondado
    margin = 16
    radius = 110
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=bg_color
    )

    # 4. Desenhar o símbolo central (Anéis de Foco + Seta de Fluxo)
    center = size / 2
    
    # Círculo Externo (Mira/Foco)
    r_outer = 140
    draw.ellipse(
        [center - r_outer, center - r_outer, center + r_outer, center + r_outer],
        outline=accent_color,
        width=24
    )

    # Círculo Interno (Ponto de Foco)
    r_inner = 50
    draw.ellipse(
        [center - r_inner, center - r_inner, center + r_inner, center + r_inner],
        fill=accent_color
    )

    # Linhas de Mira (Norte, Sul, Leste, Oeste)
    line_len = 35
    gap = 155
    width = 16

    # Topo
    draw.line([center, center - gap - line_len, center, center - gap], fill=accent_color, width=width)
    # Base
    draw.line([center, center + gap, center, center + gap + line_len], fill=accent_color, width=width)
    # Esquerda
    draw.line([center - gap - line_len, center, center - gap, center], fill=accent_color, width=width)
    # Direita
    draw.line([center + gap, center, center + gap + line_len, center], fill=accent_color, width=width)

    # 5. Salvar o arquivo PNG (Linux)
    png_path = assets_dir / "icon.png"
    img.save(png_path, format="PNG")
    print(f"✅ Ícone PNG gerado em: {png_path}")

    # 6. Salvar o arquivo ICO com múltiplos tamanhos embutidos (Windows & PyInstaller)
    ico_path = assets_dir / "icon.ico"
    # Múltiplas resoluções para garantir nitidez no Windows (Barra de tarefas, Explorer, Alt+Tab)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"✅ Ícone ICO gerado em: {ico_path}")

if __name__ == "__main__":
    generate_focusflow_icons()