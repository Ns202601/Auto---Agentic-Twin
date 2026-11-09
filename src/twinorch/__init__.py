"""twinorch: LangGraph orchestrator that turns an idea into a planned, reviewed and scaffolded project.

Layers (outer depends on inner, never the reverse):
    domain    -> models and catalog (pure Python, no I/O)
    llm       -> language-model adapters behind one interface (Claude or offline rules)
    graph     -> LangGraph state machine: nodes, routing, human review
    scaffold  -> project templates written to disk
    store     -> SQLite persistence for ideas, runs, events, projects
    service   -> application use-cases that tie the layers together
    api       -> FastAPI HTTP layer consumed by the UI
"""

__version__ = "0.1.0"
