"""CrewAI demo: two-agent legal review crew with cryptographic chain of custody.

A Researcher agent extracts a verifiable evidence bundle from a document and
summarizes it; a Legal Reviewer agent independently verifies that bundle's
integrity before signing off. A chat transcript can't prove either agent
actually looked at the real document — DocImprint's signed action receipts
can. ProvenanceTracker auto-logs every tool call that touches a bundle, and
an explicit handoff is recorded between the two agents.

Requires the crewai extra:
  pip install -e ".[crewai]"

Usage:
  python -m docimprint_examples.crewai_legal_review
  python -m docimprint_examples.crewai_legal_review --url https://example.com/contract.pdf
  python -m docimprint_examples.crewai_legal_review --notarize
"""

from __future__ import annotations

import argparse
from typing import Any

from docimprint import DocImprintError
from docimprint.crewai.tracking import extract_bundle_ids
from rich.panel import Panel
from rich.table import Table

from docimprint_examples.shared import console, load_config, print_error, write_evidence_pack

try:
    from crewai import Agent, Crew, Task
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        'This demo requires the crewai extra. Install with:\n  pip install -e ".[crewai]"'
    ) from exc

from docimprint.crewai import DocImprintToolkit

DEFAULT_URL = "https://en.wikipedia.org/wiki/Non-disclosure_agreement"


def _bundle_id_from(*texts: str) -> str | None:
    for text in texts:
        found = extract_bundle_ids(text or "")
        if found:
            return found[0]
    return None


def run(*, url: str, notarize: bool, api_key: str, base_url: str) -> dict[str, Any]:
    console.print(
        Panel.fit(
            "[bold]Problem[/]\n"
            "A researcher agent reads a document and a legal reviewer agent signs off on it. "
            "A chat transcript can't prove either agent actually looked at the real document — "
            "DocImprint's signed receipts can.",
            title="CrewAI: legal review crew",
            border_style="magenta",
        )
    )
    console.print(f"[dim]Source:[/] {url}")
    console.print()

    toolkit = DocImprintToolkit(api_key=api_key, base_url=base_url)

    researcher = Agent(
        role="Contract Researcher",
        goal="Extract a verifiable evidence bundle from the document and summarize its key terms",
        backstory="You read incoming documents and produce a citation-backed summary for legal review.",
        tools=toolkit.research_tools(),
        verbose=True,
    )
    reviewer = Agent(
        role="Legal Reviewer",
        goal="Independently verify the evidence bundle's cryptographic integrity before sign-off",
        backstory="You never sign off on a summary you haven't independently verified against the source.",
        tools=toolkit.legal_tools(),
        verbose=True,
    )

    extract_task = Task(
        description=(
            f"Extract a verifiable evidence bundle from {url} and summarize its key terms. "
            "State the bundle_id explicitly in your final answer — the reviewer needs it next."
        ),
        expected_output="The bundle_id and a short summary of the document's key terms.",
        agent=researcher,
    )
    verify_task = Task(
        description=(
            "Using the bundle_id the researcher extracted, call verify_bundle to confirm the "
            "evidence bundle's cryptographic integrity has not been tampered with. State the "
            "bundle_id and whether it is valid in your final answer."
        ),
        expected_output="Confirmation that the bundle is valid, restating its bundle_id.",
        agent=reviewer,
        context=[extract_task],
    )
    tasks = [extract_task, verify_task]

    if notarize:
        notarize_task = Task(
            description="Notarize the verified bundle on-chain for a permanent, public timestamp.",
            expected_output="The on-chain attestation transaction hash.",
            agent=reviewer,
            context=[verify_task],
        )
        tasks.append(notarize_task)

    crew = Crew(agents=[researcher, reviewer], tasks=tasks, verbose=True)

    console.print("[bold]Running crew…[/] (researcher extracts, reviewer verifies)")
    console.print()

    with toolkit.track_crew("legal-review-crew") as tracker:
        result = crew.kickoff()

    console.print()
    console.print(Panel(str(result), title="Crew result", border_style="cyan"))
    console.print()

    bundle_id = _bundle_id_from(str(getattr(extract_task.output, "raw", "")), str(result))
    if not bundle_id:
        console.print(
            "[yellow]warning:[/] could not find a bundle_id in the crew output — "
            "skipping handoff + receipt audit"
        )
        pack = {"demo": "crewai_legal_review", "source_url": url, "crew_result": str(result), "bundle_id": None}
        pack_path = write_evidence_pack("crewai-legal-review", pack)
        console.print(f"[dim]Evidence pack written to {pack_path}[/]")
        return pack

    tracker.record_handoff(
        bundle_id,
        from_agent="researcher",
        to_agent="legal-reviewer",
        note="Handing off extracted evidence bundle for independent verification",
    )
    console.print(f"[dim]Recorded handoff: researcher → legal-reviewer for {bundle_id}[/]")
    console.print()

    console.print("[bold]Auditing the signed receipts the crew's run produced…[/]")
    listed = toolkit.client.list_receipts(bundle_id)
    rows = listed.get("receipts") or []
    receipt_check: dict[str, Any] | None = None
    if not rows:
        console.print("[yellow]warning:[/] no signed receipts found for this bundle")
    else:
        table = Table(title=f"Action receipts for {bundle_id}", show_lines=True)
        table.add_column("action", style="bold")
        table.add_column("agent_id")
        table.add_column("receipt_id", style="cyan")
        for row in rows:
            table.add_row(str(row.get("action")), str(row.get("agent_id")), str(row.get("id")))
        console.print(table)

        last_receipt_id = rows[-1].get("id")
        receipt_check = toolkit.client.verify_receipt(last_receipt_id)
        console.print(
            f"  receipt [cyan]{last_receipt_id}[/] valid = [green]{receipt_check.get('valid')}[/] "
            f"(signature_valid={receipt_check.get('signature_valid')}, "
            f"manifest_matches_current={receipt_check.get('manifest_matches_current')})"
        )

    pack = {
        "demo": "crewai_legal_review",
        "source_url": url,
        "crew_result": str(result),
        "bundle_id": bundle_id,
        "receipts": rows,
        "receipt_verify": receipt_check,
    }
    pack_path = write_evidence_pack(bundle_id, pack)
    console.print()
    console.print(f"[dim]Evidence pack written to {pack_path}[/]")
    return pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CrewAI demo: a researcher agent extracts a verifiable evidence bundle, a legal "
            "reviewer agent independently verifies it, and DocImprint's signed action receipts "
            "prove the handoff actually happened."
        )
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Document URL for the crew to review (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--notarize",
        action="store_true",
        help="Also notarize the verified bundle on-chain (uses plan quota / credits)",
    )
    args = parser.parse_args(argv)

    try:
        api_key, base_url = load_config()
        run(url=args.url, notarize=args.notarize, api_key=api_key, base_url=base_url)
    except DocImprintError as exc:
        print_error(exc)
        return 1
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
