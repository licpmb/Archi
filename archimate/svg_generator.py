"""
SVG diagram preview generator for ArchiMate models.

Generates a self-contained SVG using the auto-layout coordinates from
compute_layout(). No external dependencies — pure Python + stdlib.
"""
from __future__ import annotations

import math

from .model import ArchiModel, compute_layout

# Layer colours (mirror the UI CSS variables)
LAYER_COLORS: dict[str, str] = {
    "motivation":               "#a855f7",
    "strategy":                 "#f59e0b",
    "business":                 "#fb923c",
    "application":              "#38bdf8",
    "technology":               "#34d399",
    "physical":                 "#a78bfa",
    "implementation_migration": "#f87171",
    "other":                    "#94a3b8",
}

LAYER_LABELS: dict[str, str] = {
    "motivation":               "Motivación",
    "strategy":                 "Estrategia",
    "business":                 "Negocio",
    "application":              "Aplicación",
    "technology":               "Tecnología",
    "physical":                 "Física",
    "implementation_migration": "Implementación",
    "other":                    "Otro",
}


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _trunc(s: str, max_len: int) -> str:
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def generate_svg(model: ArchiModel) -> str:
    """
    Generate an SVG string representing the ArchiMate diagram.
    Returns a self-contained SVG element ready for embedding in HTML.
    """
    diagram = compute_layout(model)

    if not diagram.nodes:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="200"'
            ' style="background:#0f172a;border-radius:8px;display:block">'
            '<text x="260" y="88" text-anchor="middle" fill="#475569"'
            ' font-family="\'Segoe UI\',sans-serif" font-size="15">Modelo vacío</text>'
            '<text x="260" y="114" text-anchor="middle" fill="#334155"'
            ' font-family="\'Segoe UI\',sans-serif" font-size="12">'
            "Describí tu arquitectura en el chat para ver el diagrama"
            "</text>"
            "</svg>"
        )

    PADDING = 48
    elem_map = model.elements
    node_map = {n.id: n for n in diagram.nodes}

    max_x = max(n.x + n.width for n in diagram.nodes) + PADDING
    max_y = max(n.y + n.height for n in diagram.nodes) + PADDING

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{max_x}" height="{max_y}"'
        f' viewBox="0 0 {max_x} {max_y}"'
        f' style="background:#0f172a;border-radius:8px;display:block;'
        f'font-family:\'Segoe UI\',sans-serif">'
    )

    # ── Defs: arrowhead + drop shadow ──────────────────────────────────────
    parts.append(
        """<defs>
  <marker id="arr" markerWidth="8" markerHeight="6"
          refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
    <polygon points="0,0 8,3 0,6" fill="#475569"/>
  </marker>
  <filter id="shadow" x="-15%" y="-15%" width="130%" height="130%">
    <feDropShadow dx="1" dy="2" stdDeviation="3" flood-color="#000" flood-opacity="0.4"/>
  </filter>
</defs>"""
    )

    # ── Layer background bands ──────────────────────────────────────────────
    # Group nodes by layer, compute per-layer bounding box
    layer_bounds: dict[str, dict[str, float]] = {}
    for node in diagram.nodes:
        elem = elem_map.get(node.element_id)
        if not elem:
            continue
        layer = elem.layer
        if layer not in layer_bounds:
            layer_bounds[layer] = {
                "min_x": node.x, "max_x": node.x + node.width,
                "min_y": node.y, "max_y": node.y + node.height,
            }
        else:
            b = layer_bounds[layer]
            b["min_x"] = min(b["min_x"], node.x)
            b["max_x"] = max(b["max_x"], node.x + node.width)
            b["min_y"] = min(b["min_y"], node.y)
            b["max_y"] = max(b["max_y"], node.y + node.height)

    BAND_PAD_X = 16
    BAND_PAD_TOP = 20
    BAND_PAD_BOT = 12

    for layer, b in layer_bounds.items():
        color = LAYER_COLORS.get(layer, "#94a3b8")
        label = LAYER_LABELS.get(layer, layer)
        rx = b["min_x"] - BAND_PAD_X
        ry = b["min_y"] - BAND_PAD_TOP
        rw = b["max_x"] - b["min_x"] + BAND_PAD_X * 2
        rh = b["max_y"] - b["min_y"] + BAND_PAD_TOP + BAND_PAD_BOT
        parts.append(
            f'<rect x="{rx:.0f}" y="{ry:.0f}" width="{rw:.0f}" height="{rh:.0f}"'
            f' rx="10" fill="{color}" fill-opacity="0.07"'
            f' stroke="{color}" stroke-opacity="0.25" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{rx + 8:.0f}" y="{ry + 13:.0f}"'
            f' fill="{color}" font-size="9" font-weight="700" opacity="0.75"'
            f' letter-spacing="0.5">'
            f"{_esc(label.upper())}</text>"
        )

    # ── Connections (drawn behind nodes) ───────────────────────────────────
    for conn in diagram.connections:
        src_node = node_map.get(conn.source_node_id)
        tgt_node = node_map.get(conn.target_node_id)
        if not src_node or not tgt_node:
            continue

        x1 = src_node.x + src_node.width / 2
        y1 = src_node.y + src_node.height / 2
        x2 = tgt_node.x + tgt_node.width / 2
        y2 = tgt_node.y + tgt_node.height / 2

        # Shorten the line so arrowhead touches box edge, not center
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist > 0:
            # Step back from target by half-height + arrowhead length
            step = min(tgt_node.height / 2 + 10, dist - 1)
            ratio = (dist - step) / dist
            ex, ey = x1 + dx * ratio, y1 + dy * ratio
        else:
            ex, ey = x2, y2

        parts.append(
            f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{ex:.0f}" y2="{ey:.0f}"'
            f' stroke="#334155" stroke-width="1.5"'
            f' marker-end="url(#arr)"/>'
        )

    # ── Element nodes ──────────────────────────────────────────────────────
    for node in diagram.nodes:
        elem = elem_map.get(node.element_id)
        if not elem:
            continue

        color = LAYER_COLORS.get(elem.layer, "#94a3b8")
        cx = node.x + node.width / 2

        # Box with drop shadow
        parts.append(
            f'<rect x="{node.x}" y="{node.y}" width="{node.width}" height="{node.height}"'
            f' rx="7" fill="#1e293b" stroke="{color}" stroke-width="1.5"'
            f' filter="url(#shadow)"/>'
        )

        # Element name (white, centred, 11px bold)
        name_display = _trunc(elem.name, 17)
        name_y = node.y + node.height / 2 - 6
        parts.append(
            f'<text x="{cx:.0f}" y="{name_y:.0f}"'
            f' text-anchor="middle" dominant-baseline="middle"'
            f' fill="#e2e8f0" font-size="11" font-weight="600">'
            f"{_esc(name_display)}</text>"
        )

        # Element type (coloured, 9px, near bottom)
        type_display = _trunc(elem.element_type, 19)
        type_y = node.y + node.height - 10
        parts.append(
            f'<text x="{cx:.0f}" y="{type_y:.0f}"'
            f' text-anchor="middle"'
            f' fill="{color}" font-size="9" opacity="0.85">'
            f"{_esc(type_display)}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)
