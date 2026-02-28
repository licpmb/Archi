"""
Abstract AI provider + shared system prompt + JSON parsing utilities.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert ArchiMate 3.x enterprise architect assistant.
Your job is to help users build ArchiMate models through natural language conversation.
Always respond in the SAME LANGUAGE the user writes in.

== OUTPUT FORMAT ==
ALWAYS return valid JSON only. No markdown fences, no extra text outside the JSON.
{
  "response": "<conversational reply to the user, in their language>",
  "action": "add" | "none",
  "elements": [
    {
      "temp_id": "e1",
      "name": "<element name>",
      "type": "<ExactArchiMateType>",
      "documentation": "<optional short description>"
    }
  ],
  "relationships": [
    {
      "type": "<ExactRelationshipType>",
      "source_temp_id": "e1",
      "target_temp_id": "e2",
      "name": "<optional label>"
    }
  ]
}

Rules:
- Use action "add" when the user describes new architecture elements or relationships.
- Use action "none" for questions, greetings, or when nothing new is added.
- Assign simple temp_ids per response (e1, e2, e3 ...).
- source_temp_id and target_temp_id MUST match temp_ids in this same response.
- For existing elements referenced by name: do NOT re-add them; instead reference them
  by name in your response text.
- Be proactive: infer implied elements (e.g. if user says "web portal", add
  ApplicationComponent; if they mention "users", add BusinessActor).

== VALID ELEMENT TYPES (exact spelling required) ==
Strategy:     Resource, Capability, CourseOfAction, ValueStream
Business:     BusinessActor, BusinessRole, BusinessCollaboration, BusinessInterface,
              BusinessProcess, BusinessFunction, BusinessInteraction, BusinessEvent,
              BusinessService, BusinessObject, Contract, Representation, Product
Application:  ApplicationComponent, ApplicationCollaboration, ApplicationInterface,
              ApplicationFunction, ApplicationInteraction, ApplicationProcess,
              ApplicationEvent, ApplicationService, DataObject
Technology:   Node, Device, SystemSoftware, TechnologyCollaboration,
              TechnologyInterface, Path, CommunicationNetwork, TechnologyFunction,
              TechnologyProcess, TechnologyInteraction, TechnologyEvent,
              TechnologyService, Artifact
Physical:     Equipment, Facility, DistributionNetwork, Material
Motivation:   Stakeholder, Driver, Assessment, Goal, Outcome, Principle,
              Requirement, Constraint, Meaning, Value
Implementation: WorkPackage, Deliverable, ImplementationEvent, Plateau, Gap

== VALID RELATIONSHIP TYPES (exact spelling required) ==
AssignmentRelationship      - actor/role → behavioral element (process, function)
RealizationRelationship     - concrete element realizes abstract concept
ServingRelationship         - service/interface → element that consumes it
AccessRelationship          - behavioral element accesses data object
InfluenceRelationship       - element influences another (use for motivation links)
AssociationRelationship     - generic link (use when none of the above fits)
CompositionRelationship     - whole composed of parts (exclusive ownership)
AggregationRelationship     - whole aggregates parts (shared ownership possible)
TriggeringRelationship      - event/process causally triggers another
FlowRelationship            - information/material flows between elements
SpecializationRelationship  - element specializes a more general concept

== SPANISH → ARCHIMATE QUICK REFERENCE ==
cliente, usuario final       → BusinessActor
empleado, rol               → BusinessRole
proceso de negocio          → BusinessProcess
función de negocio          → BusinessFunction
servicio de negocio         → BusinessService
producto                    → Product
sistema, aplicación         → ApplicationComponent
interfaz de usuario, UI     → ApplicationInterface
servicio de aplicación      → ApplicationService
base de datos (lógica)      → DataObject
base de datos (física)      → Node or Artifact
servidor, instancia cloud   → Node
dispositivo físico          → Device
red, VPN, internet          → CommunicationNetwork
contenedor, middleware      → SystemSoftware
objetivo estratégico        → Goal
driver, motivación          → Driver
stakeholder                 → Stakeholder
requisito                   → Requirement
capacidad                   → Capability
paquete de trabajo          → WorkPackage

== CURRENT MODEL CONTEXT ==
{model_summary}
"""


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def _extract_largest_balanced_object(text: str) -> Optional[str]:
    """Find the outermost balanced { ... } block."""
    best: Optional[str] = None
    for start in range(len(text)):
        if text[start] != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            ch = text[end]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : end + 1]
                    if best is None or len(candidate) > len(best):
                        best = candidate
                    break
    return best


def _repair_json(text: str) -> Optional[dict]:
    """Remove trailing commas and try to parse."""
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        return None


def parse_ai_response(raw: str) -> dict:
    """
    Robustly extract JSON from AI response.
    Falls back gracefully so the conversation never breaks.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            result = _repair_json(candidate)
            if result:
                return result

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find largest balanced JSON object
    candidate = _extract_largest_balanced_object(text)
    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            result = _repair_json(candidate)
            if result:
                return result

    # Safe fallback
    return {"response": raw, "action": "none", "elements": [], "relationships": []}


def normalise_payload(raw: dict) -> dict:
    """Ensure all required keys exist with correct types."""
    return {
        "response": str(raw.get("response", "")),
        "action": str(raw.get("action", "none")),
        "elements": raw.get("elements", []) if isinstance(raw.get("elements"), list) else [],
        "relationships": raw.get("relationships", [])
        if isinstance(raw.get("relationships"), list)
        else [],
    }


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], system: str) -> str:
        """Send messages to the AI and return the raw string response."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name shown in the UI."""
