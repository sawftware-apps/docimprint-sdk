"""RAG demo: index multiple documents into a collection, then ask across them.

A collection is DocImprint's multi-document memory — index several evidence
bundles once, then search or ask cross-document questions with citations back
to the specific bundle + chunk each answer came from. Common pattern for
agents doing due diligence, research, or contract review across a folder of
documents rather than one file at a time.

Usage:
  python -m docimprint_examples.collection_qa
  python -m docimprint_examples.collection_qa --url https://example.com/doc2.pdf
"""

from __future__ import annotations

import argparse
from typing import Any

from docimprint import DocImprintError
from rich.panel import Panel
from rich.table import Table

from docimprint_examples.shared import (
    FIXTURES_DIR,
    bundle_id_of,
    cited_text,
    console,
    extract_uploaded_file,
    load_config,
    open_session,
    print_error,
    write_evidence_pack,
)

DEFAULT_SECOND_URL = "https://en.wikipedia.org/wiki/Non-disclosure_agreement"
DEFAULT_QUESTION = "What does this document say about termination notice periods?"
DEFAULT_SEARCH_QUERY = "termination notice"


def _print_results_table(title: str, rows: list[dict[str, Any]]) -> None:
    table = Table(title=title, show_lines=True)
    table.add_column("bundle_id", style="cyan", width=14)
    table.add_column("score", width=8)
    table.add_column("text")
    for row in rows:
        text = str(row.get("text") or "")
        table.add_row(
            str(row.get("bundle_id") or "—"),
            f"{row.get('score'):.3f}" if isinstance(row.get("score"), (int, float)) else "—",
            text[:160] + ("…" if len(text) > 160 else ""),
        )
    console.print(table)


def run(
    *,
    second_url: str,
    question: str,
    search_query: str,
    api_key: str,
    base_url: str,
) -> dict[str, Any]:
    msa_path = FIXTURES_DIR / "sample_msa.txt"
    if not msa_path.is_file():
        raise DocImprintError(f"missing fixture: {msa_path}", code="MISSING_FIXTURE")

    console.print(
        Panel.fit(
            "[bold]Problem[/]\n"
            "An agent needs to answer questions across a folder of documents, "
            "not just one file — and cite which document each answer came from.",
            title="Collection Q&A (RAG)",
            border_style="green",
        )
    )

    with open_session(api_key, base_url) as session:
        console.print("[bold]1/4[/] Creating a collection…")
        collection = session.client.create_collection("Example collection — MSA + web doc")
        collection_id = collection.get("id") or collection.get("collection_id")
        if not collection_id:
            raise DocImprintError(
                "create_collection response missing collection id",
                code="MISSING_COLLECTION_ID",
                details=collection,
            )
        console.print(f"  collection_id = [cyan]{collection_id}[/]")
        console.print()

        console.print("[bold]2/4[/] Indexing documents into the collection…")
        indexed_bundle_ids: list[str] = []

        with msa_path.open("rb") as fh:
            file_bytes = fh.read()

        extracted_fixture = extract_uploaded_file(
            session.http,
            file_bytes=file_bytes,
            filename="sample_msa.txt",
            mode="extract",
            lean=False,
            wait_for_job=session.client.wait_for_job,
        )
        fixture_bundle_id = bundle_id_of(extracted_fixture)
        if not fixture_bundle_id:
            raise DocImprintError(
                "extract response missing bundle_id",
                code="MISSING_BUNDLE_ID",
                details=extracted_fixture,
            )
        session.client.add_to_collection(collection_id, fixture_bundle_id)
        indexed_bundle_ids.append(fixture_bundle_id)
        console.print(f"  + {msa_path.name} → [cyan]{fixture_bundle_id}[/]")

        extracted_url = session.client.extract(url=second_url)
        url_bundle_id = bundle_id_of(extracted_url)
        if not url_bundle_id:
            raise DocImprintError(
                "extract response missing bundle_id",
                code="MISSING_BUNDLE_ID",
                details=extracted_url,
            )
        session.client.add_to_collection(collection_id, url_bundle_id)
        indexed_bundle_ids.append(url_bundle_id)
        console.print(f"  + {second_url} → [cyan]{url_bundle_id}[/]")
        console.print()

        console.print("[bold]3/4[/] Asking a cross-collection question…")
        answer = session.client.ask_collection(collection_id, question)
        answer_text, citations = cited_text(answer.get("answer"))
        console.print(Panel(answer_text or "(no answer)", title=f'Q: "{question}"', border_style="magenta"))
        if citations:
            console.print(f"  [dim]{len(citations)} citation(s) — see evidence pack for full detail[/]")
        console.print()

        console.print("[bold]4/4[/] Raw search across the collection…")
        search = session.client.search_collection(collection_id, search_query, limit=5)
        results = search.get("results") or []
        _print_results_table(f'search: "{search_query}"', results)
        console.print()

        pack = {
            "demo": "collection_qa",
            "collection_id": collection_id,
            "indexed_bundle_ids": indexed_bundle_ids,
            "question": question,
            "answer": answer.get("answer"),
            "citations": citations,
            "search_query": search_query,
            "search_results": results,
        }
        pack_path = write_evidence_pack(collection_id, pack)
        console.print(f"[dim]Evidence pack written to {pack_path}[/]")
        return pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Index a local fixture + a URL into a DocImprint collection, "
            "then ask a cross-document question and run a raw search."
        )
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SECOND_URL,
        help=f"Second document URL to index alongside the MSA fixture (default: {DEFAULT_SECOND_URL})",
    )
    parser.add_argument("--question", default=DEFAULT_QUESTION, help="Cross-collection question to ask")
    parser.add_argument("--search", default=DEFAULT_SEARCH_QUERY, help="Raw search query to run")
    args = parser.parse_args(argv)

    try:
        api_key, base_url = load_config()
        run(
            second_url=args.url,
            question=args.question,
            search_query=args.search,
            api_key=api_key,
            base_url=base_url,
        )
    except DocImprintError as exc:
        print_error(exc)
        return 1
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
