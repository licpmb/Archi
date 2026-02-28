"""
Generate Archi 4.x native .archimate XML format.
"""
from __future__ import annotations

from collections import defaultdict
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

from .model import (
    LAYER_ORDER,
    ArchiModel,
    DiagramConnection,
    DiagramNode,
    compute_layout,
)

# Archi folder metadata: layer_key -> (display_name, folder_type_attr)
_FOLDER_META: dict[str, tuple[str, str]] = {
    "strategy": ("Strategy", "strategy"),
    "business": ("Business", "business"),
    "application": ("Application", "application"),
    "technology": ("Technology & Physical", "technology"),
    "physical": ("Physical", "physical"),
    "motivation": ("Motivation", "motivation"),
    "implementation_migration": ("Implementation & Migration", "implementation_migration"),
    "other": ("Other", "other"),
}


def generate_archimate_xml(model: ArchiModel) -> str:
    """Return a pretty-printed Archi 4.x .archimate XML string."""

    root = Element("archimate:model")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xmlns:archimate", "http://www.archimatetool.com/archimate")
    root.set("name", model.name)
    root.set("id", model.id)
    root.set("version", "4.0")

    # ---------------------------------------------------------------
    # Element folders – one per layer (only emit non-empty layers)
    # ---------------------------------------------------------------
    by_layer = model.elements_by_layer()

    for layer in LAYER_ORDER:
        elems = by_layer.get(layer, [])
        if not elems:
            continue
        folder_name, folder_type = _FOLDER_META.get(
            layer, (layer.capitalize(), layer)
        )
        folder = SubElement(root, "folder")
        folder.set("name", folder_name)
        folder.set("id", f"folder-{layer}")
        folder.set("type", folder_type)

        for elem in elems:
            el = SubElement(folder, "element")
            el.set("xsi:type", f"archimate:{elem.element_type}")
            el.set("id", elem.id)
            el.set("name", elem.name)
            if elem.documentation:
                doc = SubElement(el, "documentation")
                doc.text = elem.documentation

    # ---------------------------------------------------------------
    # Relations folder
    # ---------------------------------------------------------------
    if model.relationships:
        rel_folder = SubElement(root, "folder")
        rel_folder.set("name", "Relations")
        rel_folder.set("id", "folder-relations")
        rel_folder.set("type", "relations")

        for rel in model.relationships.values():
            rel_el = SubElement(rel_folder, "element")
            rel_el.set("xsi:type", f"archimate:{rel.relationship_type}")
            rel_el.set("id", rel.id)
            rel_el.set("source", rel.source_id)
            rel_el.set("target", rel.target_id)
            if rel.name:
                rel_el.set("name", rel.name)

    # ---------------------------------------------------------------
    # Views folder
    # ---------------------------------------------------------------
    views_folder = SubElement(root, "folder")
    views_folder.set("name", "Views")
    views_folder.set("id", "folder-views")
    views_folder.set("type", "diagrams")

    if model.elements:
        diagram = compute_layout(model)
        _write_diagram(views_folder, diagram)

    # ---------------------------------------------------------------
    # Pretty-print
    # ---------------------------------------------------------------
    raw = tostring(root, encoding="unicode")
    dom = parseString(raw)
    pretty = dom.toprettyxml(indent="  ", encoding=None)
    # toprettyxml adds its own XML declaration; replace with UTF-8 version
    lines = pretty.split("\n")
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)


def _write_diagram(parent: Element, diagram) -> None:
    """Write <element xsi:type=ArchimateDiagramModel> with children."""
    view_el = SubElement(parent, "element")
    view_el.set("xsi:type", "archimate:ArchimateDiagramModel")
    view_el.set("id", diagram.id)
    view_el.set("name", diagram.name)

    # Build lookup: DiagramNode.id -> DiagramNode
    node_lookup: dict[str, DiagramNode] = {n.id: n for n in diagram.nodes}

    # Build: source_node_id -> [DiagramConnection]
    src_connections: dict[str, list[DiagramConnection]] = defaultdict(list)
    for conn in diagram.connections:
        src_connections[conn.source_node_id].append(conn)

    for node in diagram.nodes:
        child = SubElement(view_el, "child")
        child.set("xsi:type", "archimate:DiagramObject")
        child.set("id", node.id)
        child.set("archimateElement", node.element_id)

        bounds = SubElement(child, "bounds")
        bounds.set("x", str(node.x))
        bounds.set("y", str(node.y))
        bounds.set("width", str(node.width))
        bounds.set("height", str(node.height))

        # sourceConnection children for outgoing edges from this node
        for conn in src_connections.get(node.id, []):
            sc = SubElement(child, "sourceConnection")
            sc.set("xsi:type", "archimate:Connection")
            sc.set("id", conn.id)
            sc.set("source", conn.source_node_id)
            sc.set("target", conn.target_node_id)
            sc.set("archimateRelationship", conn.relationship_id)
