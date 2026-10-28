"""
ZeroFreeze - Módulo Externo de Desenho de Ícones Vetoriais (Cairo)

Este arquivo é totalmente isolado e modular.
Você pode editar diretamente as funções abaixo para personalizar
a aparência visual dos ícones de RAM, CPU ou Armazenamento.

Todas as funções recebem:
- cr: O contexto Cairo para desenho.
- cx, cy: O ponto central (X, Y) do anel/medidor.
- ring_r, ring_g, ring_b: As cores atuais do anel (caso queira usar detalhes combinando).
- scale: Fator de escala proporcional do widget (1.0 = tamanho padrão).
"""

import math


def draw_cpu_icon(cr, cx, cy, icon_r=0.92, icon_g=0.94, icon_b=0.98, scale=1.0):
    """
    Ícone do Processador (CPU).
    Colorido com a cor personalizada do usuário.
    """
    sc = max(0.4, scale)
    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.set_line_width(max(1.0, 1.6 * sc))
    cr.set_line_cap(0)  # BUTT

    s = 10.0 * sc
    x0, y0 = cx - s / 2.0, cy - s / 2.0

    # Corpo central quadrado
    cr.rectangle(x0, y0, s, s)
    cr.stroke()

    # Pinos em todos os 4 lados (3 pinos por lado)
    pin_len = 3.0 * sc
    for off in [-3.0 * sc, 0.0, 3.0 * sc]:
        # Superior e inferior
        cr.move_to(cx + off, y0 - pin_len)
        cr.line_to(cx + off, y0)
        cr.move_to(cx + off, y0 + s)
        cr.line_to(cx + off, y0 + s + pin_len)
        # Esquerda e direita
        cr.move_to(x0 - pin_len, cy + off)
        cr.line_to(x0, cy + off)
        cr.move_to(x0 + s, cy + off)
        cr.line_to(x0 + s + pin_len, cy + off)
    cr.stroke()

    # Núcleo / Die central
    die = 4.0 * sc
    cr.rectangle(cx - die / 2.0, cy - die / 2.0, die, die)
    cr.fill()


def draw_ram_icon(cr, cx, cy, icon_r=0.92, icon_g=0.94, icon_b=0.98, scale=1.0):
    """
    Ícone de Memória RAM Estilizado.
    Colorido com a cor personalizada do usuário.
    """
    sc = max(0.4, scale)
    w, h = 18.0 * sc, 10.0 * sc
    x0, y0 = cx - w / 2.0, cy - h / 2.0

    # Contorno da placa de circuito impresso (PCB da RAM)
    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.set_line_width(max(1.0, 1.4 * sc))
    cr.rectangle(x0, y0, w, h)
    cr.stroke()

    # Chips de memória integrados (4 chips retangulares preenchidos)
    chip_w, chip_h = 2.4 * sc, 4.5 * sc
    chip_y = y0 + 2.0 * sc
    for i in range(4):
        chip_x = x0 + (2.0 + i * 3.8) * sc
        cr.rectangle(chip_x, chip_y, chip_w, chip_h)
    cr.fill()

    # Pinos de contato na borda inferior
    cr.set_line_width(max(0.8, 1.2 * sc))
    pin_len = 2.2 * sc
    for px_base in [2.0, 4.2, 6.4, 10.6, 12.8, 15.0]:
        px = x0 + px_base * sc
        cr.move_to(px, y0 + h)
        cr.line_to(px, y0 + h + pin_len)
    cr.stroke()


def draw_disk_icon(cr, cx, cy, icon_r=0.92, icon_g=0.94, icon_b=0.98, scale=1.0):
    """
    Ícone de Armazenamento / SSD Estilizado.
    Colorido com a cor personalizada do usuário.
    """
    sc = max(0.4, scale)
    w, h = 14.0 * sc, 17.0 * sc
    x0, y0 = cx - w / 2.0, cy - h / 2.0

    # Corpo externo do SSD / Placa
    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.set_line_width(max(1.0, 1.4 * sc))
    cr.rectangle(x0, y0, w, h)
    cr.stroke()

    # Área central com inscrição "SSD"
    if sc >= 0.55:
        cr.select_font_face("Sans", 0, 1)  # Normal, Bold
        cr.set_font_size(max(4.0, 5.2 * sc))
        extents = cr.text_extents("SSD")
        tx = cx - (extents[2] / 2.0) - extents[0]
        ty = cy + 0.5 * sc
        cr.move_to(tx, ty)
        cr.show_text("SSD")

        # Linha divisória de componente abaixo do texto
        cr.set_line_width(max(0.8, 1.0 * sc))
        cr.move_to(x0 + 2.5 * sc, cy + 3.2 * sc)
        cr.line_to(x0 + w - 2.5 * sc, cy + 3.2 * sc)
        cr.stroke()

    # Pinos conectores na borda inferior
    pin_len = 2.2 * sc
    cr.set_line_width(max(0.8, 1.2 * sc))
    for px_base in [2.5, 4.8, 7.0, 9.2, 11.4]:
        px = x0 + px_base * sc
        cr.move_to(px, y0 + h)
        cr.line_to(px, y0 + h + pin_len)
    cr.stroke()

    # Pequenos pontos/furos de fixação no topo
    cr.arc(x0 + 2.5 * sc, y0 + 2.5 * sc, max(0.5, 0.8 * sc), 0, 2 * math.pi)
    cr.arc(x0 + w - 2.5 * sc, y0 + 2.5 * sc, max(0.5, 0.8 * sc), 0, 2 * math.pi)
    cr.fill()


def draw_temp_icon(cr, cx, cy, icon_r=0.92, icon_g=0.94, icon_b=0.98, scale=1.0):
    """
    Ícone de Termômetro Tubular Estilizado (Cairo).
    Bulbo inferior arredondado, haste de vidro e coluna de mercúrio.
    """
    sc = max(0.4, scale)
    stem_w = 4.4 * sc
    bulb_r = 4.6 * sc
    stem_top_r = stem_w / 2.0
    total_h = 22.0 * sc

    y_bottom = cy + 9.0 * sc
    y_bulb_center = y_bottom - bulb_r
    y_top = y_bottom - total_h

    # 1. Contorno externo do tubo de vidro
    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.set_line_width(max(1.0, 1.4 * sc))
    cr.set_line_cap(1)  # ROUND

    # Topo arredondado da haste
    cr.arc(cx, y_top + stem_top_r, stem_top_r, math.pi, 2 * math.pi)
    # Lado direito da haste
    cr.line_to(cx + stem_top_r, y_bulb_center - 2.0 * sc)
    # Bulbo esférico inferior
    # Conexão suave com o bulbo
    angle_offset = math.asin(min(1.0, stem_top_r / bulb_r))
    cr.arc(cx, y_bulb_center, bulb_r, -math.pi / 2.0 + angle_offset, 1.5 * math.pi - angle_offset)
    # Lado esquerdo da haste subindo até o topo
    cr.line_to(cx - stem_top_r, y_top + stem_top_r)
    cr.stroke()

    # 2. Mercúrio / Líquido interno (preenchimento do bulbo e haste até meia altura)
    fill_top = cy - 2.0 * sc
    cr.arc(cx, y_bulb_center, max(1.0, bulb_r - 1.8 * sc), 0, 2 * math.pi)
    cr.fill()
    inner_stem_w = max(1.2, stem_w - 2.2 * sc)
    cr.rectangle(cx - inner_stem_w / 2.0, fill_top, inner_stem_w, y_bulb_center - fill_top)
    cr.fill()

    # 3. Pequenos traços de graduação de temperatura na haste lateral direita
    cr.set_line_width(max(0.7, 1.0 * sc))
    for tick_y in [y_top + 4.5 * sc, y_top + 8.0 * sc, y_top + 11.5 * sc]:
        cr.move_to(cx + stem_top_r + 1.2 * sc, tick_y)
        cr.line_to(cx + stem_top_r + 3.2 * sc, tick_y)
    cr.stroke()


def draw_motherboard_icon(cr, cx, cy, icon_r=0.92, icon_g=0.94, icon_b=0.98, scale=1.0):
    """
    Ícone de Placa-mãe / Gabinete / Circuito Integrado.
    """
    sc = max(0.4, scale)
    w, h = 18.0 * sc, 16.0 * sc
    x0, y0 = cx - w / 2.0, cy - h / 2.0

    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.set_line_width(max(1.0, 1.3 * sc))

    # Borda da PCB com chanfro no canto superior direito
    cr.move_to(x0, y0)
    cr.line_to(x0 + w - 4.0 * sc, y0)
    cr.line_to(x0 + w, y0 + 4.0 * sc)
    cr.line_to(x0 + w, y0 + h)
    cr.line_to(x0, y0 + h)
    cr.close_path()
    cr.stroke()

    # Soquete do processador / chip principal
    socket_sz = 6.0 * sc
    cr.rectangle(x0 + 3.0 * sc, y0 + 3.0 * sc, socket_sz, socket_sz)
    cr.stroke()

    # Slots de expansão / PCIe
    cr.set_line_width(max(0.8, 1.1 * sc))
    cr.move_to(x0 + 3.0 * sc, y0 + h - 3.5 * sc)
    cr.line_to(x0 + w - 3.0 * sc, y0 + h - 3.5 * sc)
    cr.stroke()

    # Trilhas de circuito
    cr.move_to(x0 + 3.0 * sc + socket_sz, y0 + 6.0 * sc)
    cr.line_to(x0 + w - 3.0 * sc, y0 + 6.0 * sc)
    cr.stroke()


def draw_wifi_icon(cr, cx, cy, icon_r=0.92, icon_g=0.94, icon_b=0.98, scale=1.0):
    """
    Ícone de Placa Wi-Fi / Rede sem fio.
    """
    sc = max(0.4, scale)
    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.set_line_width(max(1.0, 1.4 * sc))
    cr.set_line_cap(1)  # ROUND

    # Ponto base
    dot_y = cy + 5.0 * sc
    cr.arc(cx, dot_y, max(1.0, 1.4 * sc), 0, 2 * math.pi)
    cr.fill()

    # Ondas de sinal
    r1 = 5.0 * sc
    cr.arc(cx, dot_y, r1, -math.pi * 0.75, -math.pi * 0.25)
    cr.stroke()

    r2 = 9.0 * sc
    cr.arc(cx, dot_y, r2, -math.pi * 0.75, -math.pi * 0.25)
    cr.stroke()


def draw_lock_icon(cr, cx, cy, icon_r=0.45, icon_g=0.75, icon_b=1.0, scale=1.0):
    """
    Ícone vetorial de Cadeado (Whitelist / Protegido).
    Arco superior arredondado e corpo retangular com orifício de fechadura.
    """
    sc = max(0.4, scale)
    body_w = 9.0 * sc
    body_h = 7.0 * sc
    x0 = cx - body_w / 2.0
    y0 = cy - 0.5 * sc

    # 1. Haste do cadeado (arco superior)
    shackle_r = 3.2 * sc
    shackle_cx = cx
    shackle_cy = y0 - 1.0 * sc
    cr.set_line_width(max(1.0, 1.4 * sc))
    cr.set_line_cap(1)  # ROUND
    cr.set_source_rgba(icon_r, icon_g, icon_b, 0.95)
    cr.arc(shackle_cx, shackle_cy, shackle_r, math.pi, 2 * math.pi)
    cr.line_to(shackle_cx + shackle_r, y0)
    cr.move_to(shackle_cx - shackle_r, shackle_cy)
    cr.line_to(shackle_cx - shackle_r, y0)
    cr.stroke()

    # 2. Corpo do cadeado (retângulo com cantos levemente arredondados)
    cr.rectangle(x0, y0, body_w, body_h)
    cr.fill()

    # 3. Orifício da fechadura (ponto escuro central)
    cr.set_source_rgba(0.08, 0.09, 0.12, 0.95)
    hole_y = y0 + 2.5 * sc
    cr.arc(cx, hole_y, max(0.6, 1.0 * sc), 0, 2 * math.pi)
    cr.fill()
    cr.set_line_width(max(0.6, 0.9 * sc))
    cr.move_to(cx, hole_y)
    cr.line_to(cx, y0 + 5.2 * sc)
    cr.stroke()



