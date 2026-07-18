# DocImprint Python demos

**Prove what your AI agent read from a document — with citations and a signed evidence bundle.**

Part of [`docimprint-sdk`](https://github.com/sawftware-apps/docimprint-sdk). Chat logs and RAG traces are not evidence. These demos show claim-check + evidence bundles + action receipts in Python.

Receipts are **required** by default (the demo exits non-zero without a valid receipt).

## Quick start

From the SDK repo root:

```bash
cd examples/python
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env
# set DOCIMPRINT_API_KEY from https://docimprint.com

python -m docimprint_examples.prove_what_agent_read
```

## What you'll see

Real prod shape (ids will differ on your run):

```
┌─ Prove what the agent read ──────────────────────────┐
│ Problem                                              │
│ An agent asserted two clauses about this MSA.        │
│ A chat log cannot prove either claim — DocImprint can.│
└──────────────────────────────────────────────────────┘

Claim check
┃ supported    │ …thirty days' prior written notice. │ Either party may terminate… │
┃ contradicted │ …without notice and without cause.  │ …thirty (30) days' prior…   │

  bundle_id = ev_…
  manifest  = …
  valid = true
  inline receipt_id = rcpt_…
  receipt valid = true  (signature_valid=True, manifest_matches_current=True)

┌─ Shareable artifacts ────────────────────────────────┐
│ bundle_id / manifest_sha256 / receipt_id             │
│ verify (UI)   https://docimprint.com/tools/verify-bundle?bundle_id=ev_… │
│ evidence pack out/evidence_pack_ev_….json            │
└──────────────────────────────────────────────────────┘
```

## Demos

| Demo | Command | What it shows |
|------|---------|---------------|
| **Prove what the agent read** (start here) | `python -m docimprint_examples.prove_what_agent_read` | Claim-check + stored evidence + **required** receipt |
| Evidence + receipt (URL) | `python -m docimprint_examples.production_flow --url https://…` | Same integrity/receipt path against any public URL |
| Optional on-chain | add `--notarize` | Anchors the manifest on-chain (uses plan credits) |
| Dev-only soft receipt | `--allow-missing-receipt` | Skip receipt failure (not for demos / PH) |

```bash
docimprint-prove
docimprint-production-flow --url https://example.com/contract.pdf
```

## Artifacts explained

| Artifact | Proves |
|----------|--------|
| Claim verdict + quote | Whether a specific assertion is supported by the document text |
| `bundle_id` + `manifest_sha256` | A tamper-evident capture of what was read |
| [Verify tool](https://docimprint.com/tools/verify-bundle) / `GET …/verify` | Anyone can re-check integrity |
| Action `receipt_id` + `…/receipts/{id}/verify` | A specific actor + action was bound to that exact manifest |

## Develop

```bash
pip install -e ".[dev]"
pytest -q
```

## Layout

```
../fixtures/              # shared MSA + claims (supported + gotcha)
src/docimprint_examples/  # hero + URL deep dive + shared helpers
tests/                    # unit tests (respx, no live key required)
out/                      # gitignored evidence packs from local runs
```

## Environment

| Variable | Required | Default |
|----------|----------|---------|
| `DOCIMPRINT_API_KEY` | yes | — |
| `DOCIMPRINT_BASE_URL` | no | `https://api.docimprint.com` |

## Links

- Docs: https://docimprint.com/docs  
- Verify tool: https://docimprint.com/tools/verify-bundle  
- Python client: https://pypi.org/project/docimprint/  
- SDK: https://github.com/sawftware-apps/docimprint-sdk  

## License

MIT — same as the parent SDK (see repo root `LICENSE`).
