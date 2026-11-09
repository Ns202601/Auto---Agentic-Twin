"""Catalog: what each project kind needs, and how domain tags map to the repository's research data.

The dataset IDs refer to research/data/dataset_inventory.csv; the field groups to
research/data/data_dictionary.csv. Keeping this mapping in one place means the
graph's data-assessment step stays deterministic and testable.
"""

from __future__ import annotations

from twinorch.domain.models import DomainTag, ProjectKind

KIND_LABELS = {
    ProjectKind.llm_agent: "LLM agent",
    ProjectKind.ml_model: "ML model",
    ProjectKind.data_pipeline: "Data pipeline",
    ProjectKind.hybrid: "Hybrid (agent + model)",
}

KIND_DESCRIPTIONS = {
    ProjectKind.llm_agent: "Claude-backed agent with tools; reasons over text, documents and APIs.",
    ProjectKind.ml_model: "Supervised or forecasting model trained on tabular or time-series data.",
    ProjectKind.data_pipeline: "Scheduled ingest, cleaning, quality checks and loading into a warehouse.",
    ProjectKind.hybrid: "Agent that calls a trained model as one of its tools.",
}

# Which kinds need a data assessment before planning
KINDS_NEEDING_DATA = {ProjectKind.ml_model, ProjectKind.data_pipeline, ProjectKind.hybrid}

# Domain tag -> candidate open datasets (dataset_inventory.csv IDs)
TAG_DATASETS: dict[DomainTag, list[str]] = {
    DomainTag.engine_health: ["DS-01", "DS-03"],
    DomainTag.maintenance: ["DS-01", "DS-11"],
    DomainTag.remaining_useful_life: ["DS-03", "DS-04"],
    DomainTag.turbocharger: ["DS-03"],
    DomainTag.ev_battery: ["DS-10"],
    DomainTag.market_registrations: ["DS-05", "DS-06", "DS-07", "DS-09"],
    DomainTag.emissions_compliance: ["DS-08"],
    DomainTag.fleet_operations: ["DS-06"],
}

# Domain tag -> data_dictionary.csv group substrings whose D/E fields become "gaps"
TAG_FIELD_GROUPS: dict[DomainTag, list[str]] = {
    DomainTag.engine_health: ["Engine"],
    DomainTag.turbocharger: ["Engine"],
    DomainTag.after_treatment: ["After-treatment"],
    DomainTag.emissions_compliance: ["After-treatment"],
    DomainTag.fuel_efficiency: ["Fleet", "Vehicle"],
    DomainTag.driver_behaviour: ["Vehicle"],
    DomainTag.fleet_operations: ["Fleet"],
    DomainTag.maintenance: ["Maintenance"],
    DomainTag.ev_battery: ["EV"],
}

# Keyword vocabulary used by the offline classifier (and as hints in the Claude prompt)
TAG_KEYWORDS: dict[DomainTag, list[str]] = {
    DomainTag.engine_health: ["engine", "coolant", "oil pressure", "breakdown", "failure", "fault"],
    DomainTag.after_treatment: ["dpf", "scr", "def", "adblue", "egr", "after-treatment", "aftertreatment", "regen"],
    DomainTag.turbocharger: ["turbo", "boost"],
    DomainTag.fuel_efficiency: ["fuel", "mileage", "km/l", "consumption"],
    DomainTag.driver_behaviour: ["driver", "harsh", "braking", "idling", "behaviour", "behavior"],
    DomainTag.fleet_operations: ["fleet", "route", "trip", "utilisation", "utilization", "dispatch"],
    DomainTag.maintenance: ["maintenance", "service", "repair", "downtime", "warranty", "spare"],
    DomainTag.remaining_useful_life: ["rul", "remaining useful", "degradation", "wear", "life"],
    DomainTag.ev_battery: ["battery", "soc", "soh", "state of health", "charging", "ev "],
    DomainTag.market_registrations: ["registration", "vahan", "market share", "sales", "demand"],
    DomainTag.emissions_compliance: ["nox", "emission", "bs6", "bs-vi", "cpcb", "compliance"],
    DomainTag.service_operations: ["technician", "workshop", "dealer", "job card", "field service"],
    DomainTag.documents_knowledge: ["manual", "document", "knowledge", "procedure", "sop", "bulletin", "pdf"],
}

KIND_KEYWORDS: dict[ProjectKind, list[str]] = {
    ProjectKind.llm_agent: ["agent", "assistant", "copilot", "chat", "answer", "guide", "triage",
                            "explain", "summar", "retriev", "question", "technician"],
    ProjectKind.ml_model: ["predict", "forecast", "classif", "detect", "anomal", "estimate",
                           "regression", "model", "score", "rul"],
    ProjectKind.data_pipeline: ["pipeline", "ingest", "etl", "elt", "warehouse", "dashboard",
                                "airflow", "schedule", "load", "data quality", "report"],
}

DEFAULT_STACK = {
    ProjectKind.llm_agent: ["Python 3.11", "LangGraph", "Anthropic SDK (claude-opus-5-5)", "pytest"],
    ProjectKind.ml_model: ["Python 3.11", "pandas", "scikit-learn", "LightGBM", "pytest"],
    ProjectKind.data_pipeline: ["Python 3.11", "pandas", "PostgreSQL", "Airflow (optional)", "pytest"],
    ProjectKind.hybrid: ["Python 3.11", "LangGraph", "Anthropic SDK", "scikit-learn", "pytest"],
}
