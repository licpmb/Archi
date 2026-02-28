"""
Generate ArchiMate Open Exchange Format 3.x XML.
Spec: https://www.opengroup.org/xsd/archimate/
"""
from __future__ import annotations

import re
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

from .model import ArchiModel, compute_layout

# Strip "Relationship" suffix for Open Exchange type names
_STRIP_REL = re.compile(r"Relationship$")


def _oe_rel_type(archi_type: str) -> str:
    return _STRIP_REL.sub("", archi_type)


def generate_exchange_xml(model: ArchiModel, lang: str = "es") -> str:
    """Return a pretty-printed Open Exchange Format XML string."""

    root = Element("model")
    root.set("xmlns", "http://www.opengroup.org/xsd/archimate/3.0/")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set(
        "xsi:schemaLocation",
        "http://www.opengroup.org/xsd/archimate/3.0/ "
        "http://www.opengroup.org/xsd/archimate/3.1/archimate3_Diagram.xsd",
    )
    root.set("identifier", model.id)

    # Model name
    name_el = SubElement(root, "name")
    name_el.set("xml:lang", lang)
    name_el.text = model.name

    # ---------------------------------------------------------------
    # Elements
    # ---------------------------------------------------------------
    if model.elements:
        elements_el = SubElement(root, "elements")
        for elem in model.elements.values():
            el = SubElement(elements_el, "element")
            el.set("identifier", elem.id)
            el.set("xsi:type", elem.element_type)  # no prefix in OE format
            n = SubElement(el, "name")
            n.set("xml:lang", lang)
            n.text = elem.name
            if elem.documentation:
                doc = SubElement(el, "documentation")
                doc.set("xml:lang", lang)
                doc.text = elem.documentation

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------
    if model.relationships:
        rels_el = SubElement(root, "relationships")
        for rel in model.relationships.values():
            rel_el = SubElement(rels_el, "relationship")
            rel_el.set("identifier", rel.id)
            rel_el.set("xsi:type", _oe_rel_type(rel.relationship_type))
            rel_el.set("source", rel.source_id)
            rel_el.set("target", rel.target_id)
            if rel.name:
                n = SubElement(rel_el, "name")
                n.set("xml:lang", lang)
                n.text = rel.name

    # ---------------------------------------------------------------
    # Views
    # ---------------------------------------------------------------
    if model.elements:
        diagram = compute_layout(model)

        views_el = SubElement(root, "views")
        diagrams_el = SubElement(views_el, "diagrams")
        view_el = SubElement(diagrams_el, "view")
        view_el.set("identifier", diagram.id)
        view_el.set("xsi:type", "Diagram")

        view_name = SubElement(view_el, "name")
        view_name.set("xml:lang", lang)
        view_name.text = diagram.name

        for node in diagram.nodes:
            node_el = SubElement(view_el, "node")
            node_el.set("identifier", node.id)
            node_el.set("xsi:type", "Element")
            node_el.set("elementRef", node.element_id)
            node_el.set("x", str(node.x))
            node_el.set("y", str(node.y))
            node_el.set("w", str(node.width))
            node_el.set("h", str(node.height))

        for conn in diagram.connections:
            conn_el = SubElement(view_el, "connection")
            conn_el.set("identifier", conn.id)
            conn_el.set("xsi:type", "Relationship")
            conn_el.set("relationshipRef", conn.relationship_id)
            conn_el.set("source", conn.source_node_id)
            conn_el.set("target", conn.target_node_id)

    # ---------------------------------------------------------------
    # Pretty-print
    # ---------------------------------------------------------------
    raw = tostring(root, encoding="unicode")
    dom = parseString(raw)
    pretty = dom.toprettyxml(indent="  ", encoding=None)
    lines = pretty.split("\n")
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)
