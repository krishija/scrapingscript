#!/usr/bin/env python3
"""
Campus Intelligence Scraper - Plan-and-Execute Architecture
Forces fresh, verifiable data gathering through structured research workflow.
"""

import argparse
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

import google.generativeai as genai

from tools import tool_web_search


# Stage 1: Generate baseline dossier using AI knowledge
BASELINE_DOSSIER_PROMPT = """You are a Go-to-Market Strategy Analyst at Homie. Generate a complete Campus Dossier for {campus_name} using your knowledge.

Make this comprehensive and accurate based on what you know about the university:

```json
{{
  "campusName": "{campus_name}",
  "communityDensityReport": {{"percentInHousing": 85.0, "housingCultureSummary": "..."}},
  "campusCentricityReport": {{"campusCentricityScore": 6, "justification": "...", "thirdPlaceHeatmap": ["place1", "place2", "place3"]}},
  "diamondInTheRoughOrgs": [{{"name": "...", "category": "...", "justification": "..."}}, ...],
  "strategicRecommendation": {{"tier": "Tier 1/2/3", "reasoning": "...", "first_outreach_target": "..."}}
}}
```"""

# Stage 2: Strategic deep-dive searches to fix specific gaps
AUGMENTATION_PLANNER_PROMPT = """You generated this baseline dossier for {campus_name}:

{baseline_dossier}

Now design 5-6 DEEP SEARCHES to verify and enhance the three critical areas:

1. HOUSING VERIFICATION: Find official statistics to verify percentInHousing
2. DIAMOND ORG DISCOVERY: Find 8-10 ACTUAL popular, active student organizations (not media outlets)
3. THIRD PLACE MAPPING: Find specific student hangouts with activity levels/popularity

Return exactly this format:
{{
  "augmentation_queries": [
    "site:.edu {campus_name} housing statistics common data set",
    "site:reddit.com {campus_name} popular student organizations clubs active",
    "{campus_name} student organization directory membership events",
    "{campus_name} instagram tiktok student groups accounts", 
    "{campus_name} student hangouts cafes bars study spots",
    "{campus_name} reddit students hang out third places"
  ]
}}"""

# Stage 3: Final synthesis with enhanced structure and verification
FINAL_SYNTHESIS_PROMPT = """BASELINE DOSSIER for {campus_name}:
{baseline_dossier}

FRESH WEB RESEARCH DATA:
{research_data}

Generate the FINAL enhanced dossier with these CRITICAL FIXES:

1. **Housing Verification**: Use research to find the MOST ACCURATE percentInHousing from official sources
2. **Diamond Orgs**: List 8-10 ACTUAL student organizations that are popular/active (NO media outlets, generic categories, or made-up clubs)
3. **Third Place Heatmap**: Structure as objects with name, type, and popularity/density level

```json
{{
  "campusName": "{campus_name}",
  "communityDensityReport": {{
    "percentInHousing": "VERIFIED number from research or keep baseline if no better data",
    "housingCultureSummary": "Enhanced with research insights"
  }},
  "campusCentricityReport": {{
    "campusCentricityScore": 6,
    "justification": "...",
    "thirdPlaceHeatmap": [
      {{"name": "Specific Place", "type": "cafe/bar/study", "popularityLevel": "high/medium/low", "studentActivity": "details"}},
      {{"name": "Another Place", "type": "...", "popularityLevel": "...", "studentActivity": "..."}}
    ]
  }},
  "diamondInTheRoughOrgs": [
    {{"name": "ACTUAL ORG NAME from research", "category": "specific type", "justification": "why this specific org is popular/active", "membershipSize": "estimate if available"}},
    {{"name": "ANOTHER REAL ORG", "category": "...", "justification": "...", "membershipSize": "..."}},
    "... 8-10 total REAL organizations ONLY"
  ],
  "strategicRecommendation": {{"tier": "Tier 1/2/3", "reasoning": "...", "first_outreach_target": "SPECIFIC org from your diamond list"}},
  "recentFindings": ["Specific insight 1", "Specific insight 2"],
  "sources": ["url1", "url2", "..."]
}}
```

REQUIREMENTS:
- Only include organizations that appear in the research data or are widely known
- No generic categories like "sports clubs" - be specific
- Verify housing percentage against multiple sources
- Make third places actionable with specific details"""


def load_api_keys():
    load_dotenv()
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in .env file")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    return tavily_api_key, gemini_api_key


def init_gemini(api_key: str):
    genai.configure(api_key=api_key)
    for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            _ = model.generate_content("test")
            print(f"✓ Initialized Gemini model: {model_name}")
            return model
        except Exception as e:
            print(f"✗ Failed to init {model_name}: {e}")
    raise RuntimeError("Failed to initialize any Gemini model")


def extract_json_from_text(text: str) -> dict:
    """Extract JSON from text, handling various formats."""
    text = text.strip()
    
    # Try direct parsing first
    if text.startswith('{') and text.endswith('}'):
        try:
            return json.loads(text)
        except:
            pass
    
    # Look for JSON blocks in markdown
    import re
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except:
            continue
    
    # Look for any JSON-like structure
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except:
            pass
    
    return None


def ai_first_with_augmentation(model, campus_name: str):
    """Three-stage approach: AI baseline → strategic research → enhanced synthesis."""
    
    print(f"\n🧠 STAGE 1: Baseline Dossier Generation")
    # Stage 1: Generate high-quality baseline using AI knowledge
    baseline_prompt = BASELINE_DOSSIER_PROMPT.format(campus_name=campus_name)
    
    try:
        baseline_response = model.generate_content(baseline_prompt)
        baseline_text = baseline_response.text.strip()
        print(f"📝 Generated baseline: {baseline_text[:150]}...")
        
        baseline_dossier = extract_json_from_text(baseline_text)
        if not baseline_dossier:
            raise ValueError("Failed to generate baseline dossier")
        
        print(f"✅ Baseline dossier created with {len(baseline_dossier.get('diamondInTheRoughOrgs', []))} orgs")
        
    except Exception as e:
        print(f"❌ Baseline generation failed: {e}")
        raise RuntimeError(f"Failed to generate baseline: {e}")
    
    print(f"\n🎯 STAGE 2: Strategic Augmentation Planning")
    # Stage 2: AI suggests strategic searches based on its own output
    augmentation_prompt = AUGMENTATION_PLANNER_PROMPT.format(
        campus_name=campus_name, 
        baseline_dossier=json.dumps(baseline_dossier, indent=2)
    )
    
    try:
        planning_response = model.generate_content(augmentation_prompt)
        plan_text = planning_response.text.strip()
        print(f"📋 Generated augmentation plan: {plan_text[:150]}...")
        
        augmentation_plan = extract_json_from_text(plan_text)
        if not augmentation_plan or "augmentation_queries" not in augmentation_plan:
            raise ValueError("Failed to generate augmentation plan")
        
        # Handle both simple list and complex object structures
        raw_queries = augmentation_plan["augmentation_queries"]
        if isinstance(raw_queries[0], dict):
            # Extract query field from objects
            queries = [q.get("query", str(q)) for q in raw_queries]
        else:
            # Use simple list directly
            queries = raw_queries
        print(f"✅ Augmentation plan: {len(queries)} targeted queries")
        
    except Exception as e:
        print(f"❌ Augmentation planning failed: {e}")
        # Fallback to basic recent search
        queries = [
            f'{campus_name} Instagram meme pages student social media',
            f'{campus_name} Reddit recent posts 2024 student life', 
            f'{campus_name} current events student organizations news'
        ]
        print(f"🔄 Using fallback augmentation queries: {len(queries)}")
    
    print(f"\n🔍 STAGE 3: Targeted Web Research")
    # Stage 3: Execute strategic searches
    all_results = []
    all_sources = []
    
    for i, query in enumerate(queries):
        print(f"🔧 Query {i+1}/{len(queries)}: {query[:60]}...")
        try:
            result = tool_web_search(query)
            corpus = result.get('corpus', '')
            sources = result.get('sources', [])
            
            if corpus:
                all_results.append(f"=== QUERY: {query} ===\n{corpus}")
            all_sources.extend(sources)
            
            print(f"📊 Found {len(sources)} sources, {len(corpus)} chars")
            time.sleep(0.3)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            continue
    
    research_corpus = "\n\n".join(all_results)
    unique_sources = list(set([s for s in all_sources if s]))[:10]
    
    print(f"✅ Augmentation research complete: {len(research_corpus)} chars, {len(unique_sources)} sources")
    
    print(f"\n🚀 STAGE 4: Final Enhanced Synthesis")
    # Stage 4: Combine baseline with fresh research
    final_prompt = FINAL_SYNTHESIS_PROMPT.format(
        campus_name=campus_name,
        baseline_dossier=json.dumps(baseline_dossier, indent=2),
        research_data=research_corpus[:15000]
    )
    
    try:
        final_response = model.generate_content(final_prompt)
        final_text = final_response.text.strip()
        print(f"📝 Generated final synthesis: {final_text[:150]}...")
        
        final_dossier = extract_json_from_text(final_text)
        if not final_dossier:
            # Fallback to baseline if synthesis fails
            print("⚠️ Final synthesis failed, using enhanced baseline")
            baseline_dossier["sources"] = unique_sources
            baseline_dossier["recentFindings"] = ["Web research completed but synthesis failed"]
            return baseline_dossier
        
        # Ensure sources are included
        if "sources" not in final_dossier:
            final_dossier["sources"] = unique_sources
        
        return final_dossier
        
    except Exception as e:
        print(f"❌ Final synthesis failed: {e}")
        # Return enhanced baseline as fallback
        baseline_dossier["sources"] = unique_sources  
        baseline_dossier["recentFindings"] = [f"Research completed but synthesis failed: {str(e)}"]
        return baseline_dossier


def main():
    parser = argparse.ArgumentParser(description="Generate a Campus Dossier - Plan-and-Execute Architecture")
    parser.add_argument("--campus", required=True, help="University name")
    args = parser.parse_args()

    try:
        print(f"🎯 Generating enhanced dossier for: {args.campus}")
        print("🧠 Using AI-First with Strategic Augmentation")
        
        _, gemini_api_key = load_api_keys()
        model = init_gemini(gemini_api_key)
        
        start_time = time.time()
        dossier = ai_first_with_augmentation(model, args.campus)
        elapsed = time.time() - start_time
        
        # Ensure required fields
        dossier = dict(dossier or {})
        dossier["campusName"] = args.campus
        dossier["generated_at"] = datetime.now().isoformat()
        dossier["generation_time_seconds"] = round(elapsed, 1)
        
        print(f"\n{'='*60}")
        print(f"🎉 AI-ENHANCED CAMPUS DOSSIER COMPLETED in {elapsed:.1f}s")
        print(f"📚 Sources: {len(dossier.get('sources', []))} URLs")
        print(f"🔍 Recent Findings: {len(dossier.get('recentFindings', []))}")
        print('='*60)
        print(json.dumps(dossier, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
