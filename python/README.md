# docimprint (Python)

Verifiable document memory for AI agents — evidence bundles, Merkle proofs, and signatures.

## Install

```bash
pip install docimprint           # REST client only
pip install "docimprint[crewai]"  # + CrewAI tools & toolkit (Python 3.10–3.13)
```

Set `DOCIMPRINT_API_KEY` or pass `api_key=` to the client. Default API base URL is `https://api.docimprint.com`.

## CrewAI quickstart

```python
import os
from crewai import Agent, Crew, Task
from docimprint.crewai import DocImprintToolkit

toolkit = DocImprintToolkit(
    api_key=os.environ["DOCIMPRINT_API_KEY"],
    collection_id="col_your_collection",  # optional; enables collection search/ask tools
)
researcher = Agent(role="Researcher", goal="Extract verifiable evidence", tools=toolkit.research_tools())
task = Task(description="Extract evidence from https://example.com/contract", agent=researcher)
Crew(agents=[researcher], tasks=[task]).kickoff()
```

`DocImprintToolkit` groups tools for research (`ExtractEvidenceTool`, `SummarizeTool`, `QATool`, `CheckClaimsTool`), legal (`VerifyBundleTool`, `NotarizeTool`), and collection search. Use `toolkit.all_tools()` for the full set.

## REST client

```python
from docimprint import DocImprintClient

with DocImprintClient(api_key="...") as client:
    bundle = client.extract_evidence(url="https://example.com")
    print(bundle["bundle_id"])
```

## Docs

- Source & CrewAI integration: [`python/`](https://github.com/sawftware-apps/docimprint-sdk/tree/main/python) in the [DocImprint SDK repo](https://github.com/sawftware-apps/docimprint-sdk)
- API reference: https://docimprint.com/docs

## License

MIT — see [LICENSE](LICENSE).
