# DocImprint TypeScript demos

**Prove what your AI agent read from a document — with citations and a signed evidence bundle.**

Part of [`docimprint-sdk`](https://github.com/sawftware-apps/docimprint-sdk). Same story as the [Python demos](../python): claim-check + evidence bundle + action receipt.

Receipts are **required** by default (the demo exits non-zero without a valid receipt).

## Quick start

From the SDK repo root:

```bash
cd examples/typescript
npm install

cp .env.example .env
# set DOCIMPRINT_API_KEY from https://docimprint.com

npm run prove
```

Installs `docimprint` from npm (`^0.2.0`), same as any real project would — not a local monorepo path.

## What you'll see

```
Prove what the agent read
Problem
  An agent asserted two clauses about this MSA.
  A chat log cannot prove either claim — DocImprint can.

1/3 Claim-check + store evidence bundle…
Claim check
  supported      Either party may terminate…thirty days' prior written notice.
  contradicted   Customer may terminate…without notice and without cause.

  bundle_id = ev_…
  manifest  = …
  valid = true
  inline receipt_id = rcpt_…
  receipt valid = true

Shareable artifacts
  bundle_id / manifest_sha256 / receipt_id
  verify (UI)   https://docimprint.com/tools/verify-bundle?bundle_id=ev_…
  evidence pack out/evidence_pack_ev_….json
```

## Demos

| Demo | Command | What it shows |
|------|---------|---------------|
| **Prove what the agent read** (start here) | `npm run prove` | Claim-check + stored evidence + **required** receipt |
| Evidence + receipt (URL) | `npm run production-flow -- --url https://…` | Same integrity/receipt path against any public URL |
| Collection Q&A (RAG) | `npm run collection-qa` | Index multiple documents, ask across them, cite the source bundle |
| Optional on-chain | add `--notarize` | Anchors the manifest on-chain (uses plan credits) |
| Dev-only soft receipt | `--allow-missing-receipt` | Skip receipt failure (not for demos / PH) |

## Agent frameworks

The Python SDK ships a first-class [CrewAI](https://www.crewai.com/) toolkit (`docimprint.crewai`) — see the [Python demos](../python#crewai). There's no framework-specific wrapper for Node/TS yet (LangChain.js, Vercel AI SDK, etc.) — integrate by calling the `DocImprintClient` methods directly as tools, same as any other SDK call in this package.

## Develop

```bash
npm run typecheck
npm test
```

## Layout

```
../fixtures/     # shared MSA + claims
src/             # hero + URL deep dive + RAG + shared helpers
out/             # gitignored evidence packs
```

## Environment

| Variable | Required | Default |
|----------|----------|---------|
| `DOCIMPRINT_API_KEY` | yes | — |
| `DOCIMPRINT_BASE_URL` | no | `https://api.docimprint.com` |

## Links

- Docs: https://docimprint.com/docs  
- Verify tool: https://docimprint.com/tools/verify-bundle  
- npm SDK: https://www.npmjs.com/package/docimprint  
- Python twin: [../python](../python)
