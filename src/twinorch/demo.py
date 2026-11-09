"""Mock data: a few realistic ideas so a fresh deployment is not empty."""

from __future__ import annotations

from twinorch.domain.models import IdeaIn, ReviewDecision

DEMO_IDEAS = [
    (IdeaIn(title="Technician fault-code copilot",
            problem="Field technicians lose 20-30 minutes per job searching BS6 service manuals for SCR and DPF fault-code procedures.",
            outcome="An assistant that answers fault-code questions with cited manual steps in under 20 seconds",
            data_notes="Service manuals as PDF; fault code tables", constraints="Must work on a tablet in the workshop"), None),
    (IdeaIn(title="Turbocharger failure early warning",
            problem="Turbo failures on 7.2L engines cause roadside breakdowns; boost loss is only noticed after the fault lamp.",
            outcome="Predict turbocharger failure risk 7 days ahead per truck"), "revise"),
    (IdeaIn(title="VAHAN registrations pipeline",
            problem="Market registration data is copied into spreadsheets by hand every month for the sales review.",
            outcome="A scheduled pipeline that loads VAHAN registrations into PostgreSQL with data quality checks and a report",
            data_notes="VAHAN open data by maker and fuel"), "approve"),
]


def seed_demo(service) -> None:
    if service.store.list_runs(limit=1):
        return
    for idea, action in DEMO_IDEAS:
        run = service.submit_idea(idea, wait=True)
        if action == "approve":
            service.review(run["id"], ReviewDecision(action="approve"), wait=True)
        elif action == "revise":
            service.review(run["id"], ReviewDecision(action="revise", comment="Use the C-MAPSS dataset first as a proxy and add a drift monitor"), wait=True)
