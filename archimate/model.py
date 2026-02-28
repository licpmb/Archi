"""
ArchiMate domain model: elements, relationships, auto-layout.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants and mappings
# ---------------------------------------------------------------------------

LAYER_ORDER = [
    "motivation",
    "strategy",
    "business",
    "application",
    "technology",
    "physical",
    "implementation_migration",
    "other",
]

LAYER_LABELS = {
    "motivation": "Motivación",
    "strategy": "Estrategia",
    "business": "Negocio",
    "application": "Aplicación",
    "technology": "Tecnología",
    "physical": "Física",
    "implementation_migration": "Implementación y Migración",
    "other": "Otro",
}

# Maps every valid ArchiMate element type to its layer key
ELEMENT_LAYER_MAP: dict[str, str] = {
    # Strategy
    "Resource": "strategy",
    "Capability": "strategy",
    "CourseOfAction": "strategy",
    "ValueStream": "strategy",
    # Business
    "BusinessActor": "business",
    "BusinessRole": "business",
    "BusinessCollaboration": "business",
    "BusinessInterface": "business",
    "BusinessProcess": "business",
    "BusinessFunction": "business",
    "BusinessInteraction": "business",
    "BusinessEvent": "business",
    "BusinessService": "business",
    "BusinessObject": "business",
    "Contract": "business",
    "Representation": "business",
    "Product": "business",
    # Application
    "ApplicationComponent": "application",
    "ApplicationCollaboration": "application",
    "ApplicationInterface": "application",
    "ApplicationFunction": "application",
    "ApplicationInteraction": "application",
    "ApplicationProcess": "application",
    "ApplicationEvent": "application",
    "ApplicationService": "application",
    "DataObject": "application",
    # Technology
    "Node": "technology",
    "Device": "technology",
    "SystemSoftware": "technology",
    "TechnologyCollaboration": "technology",
    "TechnologyInterface": "technology",
    "Path": "technology",
    "CommunicationNetwork": "technology",
    "TechnologyFunction": "technology",
    "TechnologyProcess": "technology",
    "TechnologyInteraction": "technology",
    "TechnologyEvent": "technology",
    "TechnologyService": "technology",
    "Artifact": "technology",
    # Physical
    "Equipment": "physical",
    "Facility": "physical",
    "DistributionNetwork": "physical",
    "Material": "physical",
    # Motivation
    "Stakeholder": "motivation",
    "Driver": "motivation",
    "Assessment": "motivation",
    "Goal": "motivation",
    "Outcome": "motivation",
    "Principle": "motivation",
    "Requirement": "motivation",
    "Constraint": "motivation",
    "Meaning": "motivation",
    "Value": "motivation",
    # Implementation & Migration
    "WorkPackage": "implementation_migration",
    "Deliverable": "implementation_migration",
    "ImplementationEvent": "implementation_migration",
    "Plateau": "implementation_migration",
    "Gap": "implementation_migration",
}

VALID_RELATIONSHIP_TYPES: set[str] = {
    "CompositionRelationship",
    "AggregationRelationship",
    "AssignmentRelationship",
    "RealizationRelationship",
    "ServingRelationship",
    "AccessRelationship",
    "InfluenceRelationship",
    "AssociationRelationship",
    "TriggeringRelationship",
    "FlowRelationship",
    "SpecializationRelationship",
}

# Aliases for common misspellings / short forms the AI might use
RELATIONSHIP_ALIASES: dict[str, str] = {
    "Composition": "CompositionRelationship",
    "Aggregation": "AggregationRelationship",
    "Assignment": "AssignmentRelationship",
    "Realization": "RealizationRelationship",
    "Realisation": "RealizationRelationship",
    "Serving": "ServingRelationship",
    "Access": "AccessRelationship",
    "Influence": "InfluenceRelationship",
    "Association": "AssociationRelationship",
    "Triggering": "TriggeringRelationship",
    "Flow": "FlowRelationship",
    "Specialization": "SpecializationRelationship",
    "Specialisation": "SpecializationRelationship",
    # Keep full names too (idempotent)
    **{t: t for t in VALID_RELATIONSHIP_TYPES},
}

# Layout constants
ELEM_W = 120
ELEM_H = 55
H_GAP = 40
V_GAP = 80
V_LAYER_GAP = 30  # extra vertical gap between layers
MARGIN = 40
MAX_PER_ROW = 8


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

def _new_id(prefix: str = "id") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class ArchiElement:
    id: str
    name: str
    element_type: str       # e.g. "BusinessActor"
    documentation: str = ""

    @property
    def layer(self) -> str:
        return ELEMENT_LAYER_MAP.get(self.element_type, "other")


@dataclass
class ArchiRelationship:
    id: str
    relationship_type: str  # e.g. "ServingRelationship"
    source_id: str
    target_id: str
    name: str = ""
    documentation: str = ""


@dataclass
class DiagramNode:
    id: str          # diagram object ID (do-...)
    element_id: str  # reference to ArchiElement.id
    x: int
    y: int
    width: int = ELEM_W
    height: int = ELEM_H


@dataclass
class DiagramConnection:
    id: str               # connection ID
    source_node_id: str   # DiagramNode.id of source
    target_node_id: str   # DiagramNode.id of target
    relationship_id: str  # ArchiRelationship.id


@dataclass
class ArchiDiagram:
    id: str
    name: str
    nodes: list[DiagramNode] = field(default_factory=list)
    connections: list[DiagramConnection] = field(default_factory=list)


@dataclass
class ArchiModel:
    id: str = field(default_factory=lambda: _new_id("model"))
    name: str = "Modelo ArchiMate"
    elements: dict[str, ArchiElement] = field(default_factory=dict)
    relationships: dict[str, ArchiRelationship] = field(default_factory=dict)

    # Deduplication indexes (not serialised)
    _elem_index: dict[tuple[str, str], str] = field(
        default_factory=dict, repr=False, compare=False
    )
    _rel_index: dict[tuple[str, str, str], str] = field(
        default_factory=dict, repr=False, compare=False
    )

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_element(
        self,
        name: str,
        element_type: str,
        documentation: str = "",
    ) -> tuple[ArchiElement, bool]:
        """
        Add element, deduplicating by (name_lower, type).
        Returns (element, is_new).
        """
        key = (name.strip().lower(), element_type)
        if key in self._elem_index:
            elem = self.elements[self._elem_index[key]]
            if documentation and not elem.documentation:
                elem.documentation = documentation
            return elem, False
        elem = ArchiElement(
            id=_new_id("e"),
            name=name.strip(),
            element_type=element_type,
            documentation=documentation,
        )
        self.elements[elem.id] = elem
        self._elem_index[key] = elem.id
        return elem, True

    def add_relationship(
        self,
        relationship_type: str,
        source_id: str,
        target_id: str,
        name: str = "",
    ) -> tuple[ArchiRelationship, bool]:
        """
        Add relationship, deduplicating by (type, source, target).
        Returns (relationship, is_new).
        """
        key = (relationship_type, source_id, target_id)
        if key in self._rel_index:
            return self.relationships[self._rel_index[key]], False
        rel = ArchiRelationship(
            id=_new_id("r"),
            relationship_type=relationship_type,
            source_id=source_id,
            target_id=target_id,
            name=name,
        )
        self.relationships[rel.id] = rel
        self._rel_index[key] = rel.id
        return rel, True

    def find_element_by_name(self, name: str) -> Optional[ArchiElement]:
        """Case-insensitive lookup; partial match as fallback."""
        name_lower = name.strip().lower()
        # Exact match first
        for elem in self.elements.values():
            if elem.name.strip().lower() == name_lower:
                return elem
        # Partial match
        for elem in self.elements.values():
            if name_lower in elem.name.strip().lower():
                return elem
        return None

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def elements_by_layer(self) -> dict[str, list[ArchiElement]]:
        result: dict[str, list[ArchiElement]] = {k: [] for k in LAYER_ORDER}
        for elem in self.elements.values():
            layer = elem.layer
            if layer not in result:
                result[layer] = []
            result[layer].append(elem)
        return result

    def to_tree(self) -> dict[str, list[dict]]:
        """Return {layer: [{id, name, type}]} for the frontend sidebar."""
        tree: dict[str, list[dict]] = {}
        for layer in LAYER_ORDER:
            elems = [
                {"id": e.id, "name": e.name, "type": e.element_type}
                for e in self.elements.values()
                if e.layer == layer
            ]
            if elems:
                tree[layer] = elems
        return tree

    def summary(self) -> str:
        """Compact text summary injected into the AI system prompt."""
        if not self.elements:
            return "The model is currently empty."
        lines = [
            f"Model has {len(self.elements)} elements "
            f"and {len(self.relationships)} relationships."
        ]
        by_layer = self.elements_by_layer()
        for layer in LAYER_ORDER:
            elems = by_layer[layer]
            if not elems:
                continue
            names = ", ".join(
                f"{e.name} ({e.element_type})" for e in elems[:12]
            )
            suffix = f" (+{len(elems)-12} more)" if len(elems) > 12 else ""
            lines.append(f"  {LAYER_LABELS.get(layer, layer)}: {names}{suffix}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Auto-layout
# ---------------------------------------------------------------------------

def compute_layout(model: ArchiModel, view_name: str = "Vista Principal") -> ArchiDiagram:
    """
    Build a single ArchiDiagram with auto-computed positions.
    Elements are grouped by layer and placed in rows of MAX_PER_ROW.
    Layers stack vertically in canonical order.
    """
    by_layer = model.elements_by_layer()

    # Assign (x, y) to every element
    elem_to_node: dict[str, DiagramNode] = {}
    current_y = MARGIN

    for layer in LAYER_ORDER:
        elems = by_layer[layer]
        if not elems:
            continue

        rows = [elems[i: i + MAX_PER_ROW] for i in range(0, len(elems), MAX_PER_ROW)]
        for row in rows:
            for col_idx, elem in enumerate(row):
                x = MARGIN + col_idx * (ELEM_W + H_GAP)
                node = DiagramNode(
                    id=_new_id("do"),
                    element_id=elem.id,
                    x=x,
                    y=current_y,
                )
                elem_to_node[elem.id] = node
            current_y += ELEM_H + V_GAP

        current_y += V_LAYER_GAP  # extra gap between layers

    # Build connections
    connections: list[DiagramConnection] = []
    for rel in model.relationships.values():
        src_node = elem_to_node.get(rel.source_id)
        tgt_node = elem_to_node.get(rel.target_id)
        if src_node and tgt_node:
            connections.append(DiagramConnection(
                id=_new_id("c"),
                source_node_id=src_node.id,
                target_node_id=tgt_node.id,
                relationship_id=rel.id,
            ))

    return ArchiDiagram(
        id=_new_id("view"),
        name=view_name,
        nodes=list(elem_to_node.values()),
        connections=connections,
    )
