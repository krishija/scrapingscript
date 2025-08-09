import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

# Ensure parent directory (project root) is on sys.path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from quantitative_engine import QuantitativeEngine
from intelligence_sources import RedditSource, SocialMediaSource, GeospatialSource
from sg_prompts import MASTER_ANALYST_PROMPT


def load_api_keys():
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    return gemini_key


def run_intelligence(campus_name: str, gemini_key: str) -> dict:
    """Run Quantitative + HUMINT + IMINT + GEOINT with minimal calls."""
    print(f"\n🧠 Social Graph v3 Orchestration: {campus_name}")
    genai.configure(api_key=gemini_key)

    # Phase 1: Quantitative (reuse existing engine)
    quant_engine = QuantitativeEngine(gemini_key)
    quantitative_data = quant_engine.run(campus_name)

    # Phase 2: Multi-modal sources (parallel, strict limits)
    reddit_source = RedditSource(gemini_key)
    social_source = SocialMediaSource(gemini_key)
    geo_source = GeospatialSource(gemini_key)

    humint_report = {}
    imint_report = {}
    geoint_report = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            # Try to derive a likely subreddit from campus_name (simple heuristic). If fails, returns error quickly.
            executor.submit(reddit_source.get_humint_report, campus_name.split()[-1].lower()): "humint",
            executor.submit(social_source.get_imint_report, [], []): "imint",  # start empty; can seed later
            executor.submit(geo_source.get_geoint_report, campus_name): "geoint",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"error": str(e)}
            if key == "humint":
                humint_report = result
            elif key == "imint":
                imint_report = result
            else:
                geoint_report = result

    # Phase 3: Master synthesis
    prompt = MASTER_ANALYST_PROMPT.format(
        campus_name=campus_name,
        quantitative_data=json.dumps(quantitative_data)[:6000],
        humint_report=json.dumps(humint_report)[:4000],
        imint_report=json.dumps(imint_report)[:4000],
        geoint_report=json.dumps(geoint_report)[:4000],
    )

    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)
    dossier_text = response.text

    return {
        "campus": campus_name,
        "quantitative": quantitative_data,
        "humint": humint_report,
        "imint": imint_report,
        "geoint": geoint_report,
        "dossier": dossier_text,
        "generated_at": datetime.now().isoformat()
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--campus", required=True)
    parser.add_argument("--output", default="social_graph_dossier.json")
    args = parser.parse_args()

    gemini_key = load_api_keys()
    result = run_intelligence(args.campus, gemini_key)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Social Graph Dossier saved: {args.output}")


if __name__ == "__main__":
    main()
