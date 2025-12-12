# Gatekeeper Recon (Therabody Prototype)

Identify high‑authority athletic department gatekeepers, validate their real‑world influence, and map the trusted “shadow system” of local clinicians — fully autonomously.

## What it does

For a target university (e.g., UC Berkeley), the agent:
- Finds the official athletics site and staff pages
- Extracts Tier‑1 gatekeepers (Director of Sports Medicine, Head AT, S&C leadership, etc.) with emails
- Validates thought leadership (e.g., NATA/NSCA/APTA talks, publications)
- Maps 8–10 local clinics with specific practitioners and affiliations
- Produces a JSON dossier and a clean PDF report

## Why it matters
- Targets the people who drive purchasing decisions for hundreds of athletes
- Prioritizes authority and word‑of‑mouth influence, not follower counts
- Automates a research process that normally takes hours

## Architecture (agentic)

```
Python orchestrator → Gemini (agent) ⇄ Tavily (search tool)
                                 ↓
                         Structured dossier (JSON)
                                 ↓
                          PDF intelligence report
```

- `prospecting_engine/gatekeeper_recon.py`: minimal orchestrator (CLI)
- `prospecting_engine/ai_utils.py`: initializes Gemini agent + master prompt
- `prospecting_engine/tools.py`: Tavily search wrapper (model’s “tool”)
- `prospecting_engine/models.py`: dataclasses for typed, reusable structures
- `prospecting_engine/reporting.py`: PDF generator from the dossier
- `prospecting_engine/config.py`: model candidates and settings

## Setup

1) Create and activate a virtualenv:

```bash
cd "Homie Work Trial"
python3 -m venv myenv
source myenv/bin/activate
pip install -r prospecting_engine/requirements.txt
```

2) Add a `.env` in the repo root:

```bash
TAVILY_API_KEY=your_tavily_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## Run (UC Berkeley example)

```bash
# single university
echo "UC Berkeley" > uc_berkeley_test.txt
python3 prospecting_engine/gatekeeper_recon.py \
  --schools-file uc_berkeley_test.txt \
  --out outputs/uc_berkeley_intel.json
```

- Output JSON: `outputs/uc_berkeley_intel.json`
- PDF: `generated_pdfs/Gatekeeper_Intelligence_Report_UC_Berkeley_<timestamp>.pdf`

## Extend/modify

- Change roles or intelligence scope: edit the single master prompt in `ai_utils.py`.
- Switch model versions: update `prospecting_engine/config.py` model candidates.
- Add new tools (e.g., a LinkedIn search proxy): add a function in `tools.py`, declare it in `ai_utils.py` as a tool, reference it in the prompt.
- Consume programmatically: import `Dossier` from `models.py` and parse the JSON into typed objects for downstream automation.

## Notes

- The agent is designed for thoroughness; tune search depth/results in `config.py` and the prompt if needed.
- Emails are prioritized from staff pages; the agent may infer patterns only when supported by sources.

## Publish to GitHub

From the project root (with `myenv` ignored):

```bash
git init
git add .
git commit -m "Therabody Gatekeeper Recon - agentic prototype"
# create a new public repo on GitHub named gatekeeper-recon
# then add it as a remote and push
git branch -M main
git remote set-url origin https://github.com/<your-username>/gatekeeper-recon.git
git push -u origin main
```

If the repo already exists, just set the correct remote and push.

