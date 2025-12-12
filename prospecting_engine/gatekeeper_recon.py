#!/usr/bin/env python3
"""
Gatekeeper Recon Agent
Orchestrates autonomous AI agents to build university intelligence dossiers.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from ai_utils import init_agentic_model, MASTER_AGENT_PROMPT
from models import Dossier, Gatekeeper, Clinic
from reporting import generate_pdf_report


def run_gatekeeper_agent(university_name: str, city: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs the autonomous research agent for a single university.
    The agent uses Gemini with tool-calling to orchestrate its own research.
    """
    print(f"🎯 Agent dispatched for: {university_name}")
    if city:
        print(f"   📍 Target city: {city}")
    start = time.time()
    
    try:
        # 1. Initialize the agentic model (which has tools)
        model, tool_fn = init_agentic_model()
        
        # 2. Format the master prompt with city context
        city_context = city if city else "the university's city"
        prompt = MASTER_AGENT_PROMPT.format(university_name=university_name)
        prompt = prompt.replace("[city name]", city_context)
        
        if city:
            prompt += f"\n\n**CITY CONTEXT:** The university is located in {city}. Use this for all local ecosystem searches."
        
        # 3. Run the agent with automatic function calling
        chat = model.start_chat()
        response = chat.send_message(prompt)
        
        # Handle function calls in a loop
        while response.candidates[0].content.parts[0].function_call:
            # Extract function call
            function_call = response.candidates[0].content.parts[0].function_call
            function_name = function_call.name
            function_args = dict(function_call.args)
            
            print(f"  🔍 Agent calling: {function_name}({function_args.get('query', '')[:60]}...)")
            
            # Execute the function
            if function_name == "tool_web_search":
                function_response = tool_fn(**function_args)
            else:
                function_response = {"error": f"Unknown function: {function_name}"}
            
            # Send function response back to model
            response = chat.send_message(
                {
                    "function_response": {
                        "name": function_name,
                        "response": function_response
                    }
                }
            )
        
        # 4. Extract the final JSON response
        final_text = response.text
        
        # Try to parse JSON from the response
        try:
            # Handle markdown code blocks
            if "```json" in final_text:
                json_start = final_text.find("```json") + 7
                json_end = final_text.find("```", json_start)
                final_text = final_text[json_start:json_end].strip()
            elif "```" in final_text:
                json_start = final_text.find("```") + 3
                json_end = final_text.find("```", json_start)
                final_text = final_text[json_start:json_end].strip()
            
            response_json = json.loads(final_text)
            dossier = Dossier.from_dict(response_json)
            elapsed = time.time() - start
            response_json['elapsed_sec'] = elapsed
            print(f"✅ Agent returned for: {university_name} in {elapsed:.1f}s")
            return dossier.to_dict()
            
        except json.JSONDecodeError as e:
            print(f"❌ AGENT FAILED: Could not decode JSON response for {university_name}")
            print(f"JSON Error: {e}")
            print(f"Raw output: {final_text[:500]}")
        return {
                "university": university_name,
                "gatekeepers": [],
                "local_ecosystem": [],
                "error": "Failed to parse JSON response from agent.",
                "raw_response": final_text[:1000]
        }
        
    except Exception as e:
        print(f"❌ AGENT EXCEPTION for {university_name}: {e}")
        return {
            "university": university_name,
            "gatekeepers": [],
            "local_ecosystem": [],
            "error": str(e)
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Gatekeeper Recon Agent Orchestrator')
    parser.add_argument('--schools-file', type=str, default=os.path.join(CURRENT_DIR, 'batch_processors', 'test_schools.txt'))
    parser.add_argument('--cities-file', type=str, default=None, help='Optional CSV mapping university,city')
    parser.add_argument('--out', type=str, default=os.path.join(PARENT_DIR, 'outputs', 'gatekeeper_batch.json'))
    args = parser.parse_args()

    # Load universities
    universities: List[str] = []
    if os.path.exists(args.schools_file):
        with open(args.schools_file, 'r') as f:
            universities = [l.strip() for l in f if l.strip()]
            
    city_map: Dict[str, str] = {}
    if args.cities_file and os.path.exists(args.cities_file):
        import csv
        with open(args.cities_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    city_map[row[0].strip().lower()] = row[1].strip()

    print(f"🎯 Gatekeeper Recon Agent: {len(universities)} Universities")
    print("=" * 60)
    all_results: List[Dict[str, Any]] = []
    start = time.time()
    
    for uni in universities:
        city = city_map.get(uni.lower())
        res = run_gatekeeper_agent(uni, city)
        all_results.append(res)
        
        # Generate per-university PDF
        pdf_path = os.path.join(PARENT_DIR, 'generated_pdfs', f"Gatekeeper_Intelligence_Report_{uni.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        generate_pdf_report(
            uni,
            res.get('gatekeepers', []), 
            res.get('gatekeepers', []),
            res.get('local_ecosystem', []), 
            pdf_path
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(all_results, f, indent=2)

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print("🎯 GATEKEEPER RECON COMPLETE")
    print(f"✅ Universities processed: {len(universities)}")
    print(f"⏱️  Total time: {elapsed:.1f}s")
    print(f"💾 JSON: {args.out}")
    print("=" * 60)

if __name__ == "__main__":
    main()
