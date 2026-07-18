# DocImprint examples

**Prove what your AI agent read — with citations and a signed evidence bundle.**

Chat logs and RAG traces are not evidence. These demos show the full proof path against a local MSA fixture:

1. **Claim-check** — `supported` / `contradicted` with exact quotes  
2. **Evidence bundle** — `bundle_id` + `manifest_sha256`  
3. **Action receipt** — bind *who verified* to *which manifest*  
4. **Share pack** — JSON + [verify tool](https://docimprint.com/tools/verify-bundle) URL  

Receipts are **required** by default (demos exit non-zero without a valid receipt).

## Choose a language

| | Python | TypeScript |
|--|--------|------------|
| Folder | [`python/`](python/) | [`typescript/`](typescript/) |
| Install | `pip install -e .` | `npm install` |
| Hero demo | `python -m docimprint_examples.prove_what_agent_read` | `npm run prove` |
| URL flow | `python -m docimprint_examples.production_flow --url …` | `npm run production-flow -- --url …` |
| Details | [python/README.md](python/README.md) | [typescript/README.md](typescript/README.md) |

Shared fixtures: [`fixtures/`](fixtures/) (sample MSA + true/false claims).

## Quick start

Get an API key at [docimprint.com](https://docimprint.com) (free tier, no card).

**Python**

```bash
cd examples/python
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # set DOCIMPRINT_API_KEY
python -m docimprint_examples.prove_what_agent_read
```

**TypeScript**

```bash
cd examples/typescript
npm install
cp .env.example .env   # set DOCIMPRINT_API_KEY
npm run prove
```

Both write an evidence pack under `out/` and print shareable `bundle_id` / `receipt_id` / verify links.

## What each artifact proves

| Artifact | Proves |
|----------|--------|
| Claim verdict + quote | Whether a specific assertion is supported by the document |
| `bundle_id` + `manifest_sha256` | Tamper-evident capture of what was read |
| Verify UI / `GET …/verify` | Anyone can re-check integrity |
| Action `receipt_id` | A specific actor + action was bound to that exact manifest |

## Flags

| Flag | Effect |
|------|--------|
| `--notarize` | Also notarize the bundle on-chain (uses plan credits) |
| `--allow-missing-receipt` | Dev only — do not fail if signing/receipts are unavailable |

## Layout

```
examples/
  fixtures/       # sample_msa.txt + claims.json
  python/         # PyPI client demos
  typescript/     # Node/TS demos (local SDK via file:../..)
  README.md       # this file
```
