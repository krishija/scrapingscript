"""
AI Utilities for Gatekeeper Recon Script
- Agentic Gemini model with tool-calling capabilities
"""

import os
import json
from typing import Any

from dotenv import load_dotenv
import google.generativeai as genai
# Support both package and script execution
try:
    from .config import DEFAULT_MODEL_CANDIDATES
except Exception:
    from config import DEFAULT_MODEL_CANDIDATES


def init_agentic_model() -> Any:
    """Initialize Gemini model with tool-calling capabilities for autonomous research."""
    # Load env from project root
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, '..'))
    load_dotenv(os.path.join(root, '.env'))

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY not set')
    genai.configure(api_key=api_key)
    
    # Import tool dynamically to avoid circular imports
    import sys
    sys.path.append(os.path.dirname(__file__))
    from tools import tool_web_search
    
    # Define the search tool using genai.protos.Tool
    from google.ai.generativelanguage_v1beta import Tool, FunctionDeclaration, Schema, Type
    
    search_tool = Tool(
        function_declarations=[
            FunctionDeclaration(
                name="tool_web_search",
                description="Search the web for information using Tavily. Input is a search query string, output is a text corpus of results with sources.",
                parameters=Schema(
                    type=Type.OBJECT,
                    properties={
                        "query": Schema(
                            type=Type.STRING,
                            description="The search query to execute"
                        ),
                        "max_results": Schema(
                            type=Type.INTEGER,
                            description="Maximum number of search results to return (default 4)"
                        )
                    },
                    required=["query"]
                )
            )
        ]
    )
    
    # Try model candidates in order
    model_candidates = DEFAULT_MODEL_CANDIDATES
    
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                tools=[search_tool]
            )
            return model, tool_web_search
        except Exception:
            continue
    
    raise RuntimeError('No supported Gemini model available for agentic mode')


MASTER_AGENT_PROMPT = """You are an elite intelligence analyst for Therabody conducting deep reconnaissance on university athletic gatekeepers.

Your mission: Build a COMPREHENSIVE intelligence dossier on "{university_name}" that identifies every key decision-maker, validates their industry influence, and maps the complete local sports medicine ecosystem.

## RESEARCH PROTOCOL - Execute Exhaustively:

### PHASE 1: GATEKEEPER IDENTIFICATION (Minimum 5-8 contacts)
1. Find the official athletics website domain (e.g., calbears.com for UC Berkeley)
2. Search the athletics domain for:
   - Staff directory pages
   - Sports medicine department pages
   - Performance/strength staff pages
   - Athletic training staff pages
3. For EACH page found, extract ALL contacts with these roles:
   - Director of Sports Medicine
   - Head Athletic Trainer / Associate Athletic Trainers
   - Director of Performance / Director of Strength & Conditioning
   - Team Physicians (if listed with contact info)
   - Director of Sports Nutrition
   - Director of Mental Performance
   - ANY other high-level sports medicine/performance staff

**CRITICAL:** You MUST find emails. Search staff bio pages, contact pages, and use pattern matching (firstname.lastname@domain.edu). Do NOT return contacts without emails unless absolutely no email exists anywhere.

### PHASE 2: INFLUENCE VALIDATION (For EVERY gatekeeper found)
For each person identified, conduct 2-3 targeted searches:
1. Search: "[Full Name] [University] NATA" (National Athletic Trainers Association)
2. Search: "[Full Name] NSCA speaker" or "[Full Name] APTA presentation"
3. Search: "[Full Name] [University] published research" or "conference"

Look for:
- Conference presentations/speaking engagements
- Published papers or research
- Board positions in professional organizations
- Awards or recognition in sports medicine
- Quotes in industry publications

If you find ANYTHING, mark is_thought_leader=true and provide specific evidence with year/conference name.

### PHASE 3: LOCAL ECOSYSTEM MAPPING (Minimum 8-10 clinics/practitioners)
Search comprehensively for the "shadow system" - private practitioners trusted by elite athletes:

1. Search: "best sports physical therapy [city name] D1 athletes"
2. Search: "top sports medicine clinic [city name] professional athletes"
3. Search: "[university name] athletics preferred provider physical therapy"
4. Search: "[city name] sports chiropractor elite athletes"
5. Search: "[city name] sports performance training center"
6. Search: "[university team name] physical therapy clinic partnership"

For EACH clinic/practitioner found:
- Get the full clinic name
- Identify specific practitioners by name (search clinic website via their domain)
- Note any athletic affiliations, specializations, or reputation indicators
- Get the clinic website URL

**CRITICAL:** Don't just list generic clinics. Find the ones that actually work with elite athletes. Look for mentions of D1 teams, Olympic athletes, professional teams, or university partnerships.

### PHASE 4: DEEP DIVE ON TOP TARGETS
For the 2-3 most senior gatekeepers (Director-level), do additional research:
- Search their LinkedIn profile mentions
- Search for their career history
- Look for their involvement in equipment/product decisions
- Find any public statements about recovery technology

## OUTPUT REQUIREMENTS:

Return a JSON object with:
- 5-8 gatekeepers minimum (with emails for at least 50%)
- Thought leadership validation for ALL gatekeepers
- 8-10 local ecosystem entries minimum with specific practitioner names
- Rich notes and evidence throughout

{{
  "university": "{university_name}",
  "athletics_domain": "official athletics website domain",
  "gatekeepers": [
    {{
      "name": "Full Name",
      "title": "Exact Job Title",
      "email": "email@domain.edu or null if truly not found",
      "phone": "phone if found, else null",
      "bio_url": "URL to their bio page if exists",
      "is_thought_leader": true/false,
      "wom_evidence": "Specific evidence with dates/conferences, or null",
      "seniority_level": "Director/Head/Associate/Team",
      "years_at_institution": "if found, else null"
    }}
  ],
  "local_ecosystem": [
    {{
      "clinic_name": "Full clinic name",
      "key_practitioners": "Dr. First Last, Dr. First Last (specific names)",
      "specialization": "e.g., 'Sports orthopedics, D1 athlete rehab'",
      "athletic_affiliations": "e.g., 'Official provider for Cal Athletics' or 'Works with Olympic swimmers'",
      "website": "clinic URL",
      "location": "city, state"
    }}
  ],
  "research_notes": "Any additional intelligence about purchasing processes, recent hires, facility upgrades, etc."
}}

**EXECUTION MANDATE:** Use tool_web_search 15-25 times. Be thorough. This is intelligence work, not a quick scrape. Return ONLY the JSON object."""
