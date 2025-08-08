#!/usr/bin/env python3
"""
Three-Engine GTM Intelligence Scraper
Complete GTM intelligence with Quantitative + Diamond Finder + Event Intelligence engines.
"""

import argparse
import json
import os
import time
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import google.generativeai as genai

from quantitative_engine import QuantitativeEngine
from diamond_finder_engine import DiamondFinderEngine
from event_intelligence_engine import EventIntelligenceEngine
from pdf_generator import generate_pdf_report


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
    """Initialize Gemini for strategic assessment."""
    genai.configure(api_key=api_key)
    for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            _ = model.generate_content("ping")
            return model
        except Exception as e:
            print(f"Failed to init {model_name}: {e}")
            continue
    raise RuntimeError("Failed to initialize any Gemini model")


def run_three_engines(campus_name: str, gemini_api_key: str) -> Dict:
    """Run all three engines for complete GTM intelligence."""
    
    print(f"\n🚀 THREE-ENGINE GTM INTELLIGENCE: {campus_name}")
    print("🏗️  Running Quantitative + Diamond Finder + Event Intelligence engines...")
    print("="*80)
    
    start_time = time.time()
    
    # Initialize engines
    quantitative_engine = QuantitativeEngine(gemini_api_key)
    diamond_finder_engine = DiamondFinderEngine(gemini_api_key)
    event_intelligence_engine = EventIntelligenceEngine(gemini_api_key)
    
    # Run first two engines in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        quantitative_future = executor.submit(quantitative_engine.run_quantitative_analysis, campus_name)
        diamond_future = executor.submit(diamond_finder_engine.run_diamond_analysis, campus_name)
        
        # Collect results
        results = {}
        for future in as_completed([quantitative_future, diamond_future]):
            try:
                result = future.result()
                if "growth_correlates" in result:
                    results["quantitative"] = result
                elif "diamond_orgs" in result:
                    results["qualitative"] = result
            except Exception as e:
                print(f"❌ Engine failed: {e}")
                results["error"] = str(e)
    
    # Run Event Intelligence Engine with diamond orgs context
    diamond_orgs = results.get("qualitative", {}).get("diamond_orgs", [])
    try:
        events_result = event_intelligence_engine.run(campus_name, diamond_orgs)
        results["events"] = events_result
    except Exception as e:
        print(f"❌ Event Intelligence Engine failed: {e}")
        results["events"] = {"error": str(e)}
    
    # Strategic Assessment
    assessment_model = init_gemini(gemini_api_key)
    
    # Create comprehensive data summary for assessment
    quantitative_data = results.get("quantitative", {}).get("growth_correlates", {})
    diamond_data = results.get("qualitative", {}).get("diamond_orgs", [])
    contact_data = results.get("qualitative", {}).get("universal_inroads", {})
    events_data = results.get("events", {}).get("events", [])
    
    # Count actionable opportunities
    num_contacts = len([k for k, v in contact_data.items() if v and v.get("contact")])
    num_events = len([e for e in events_data if e.get("homie_opportunity") not in ["No Opportunity", None]])
    data_quality = results.get("quantitative", {}).get("data_quality", {}).get("quality_score", 0)
    
    assessment_prompt = f"""You are the Head of Growth at Homie. Evaluate {campus_name} for GTM readiness based on this comprehensive intelligence.

QUANTITATIVE METRICS:
{json.dumps(quantitative_data, indent=2)}

DIAMOND ORGANIZATIONS ({len(diamond_data)} found):
{json.dumps(diamond_data, indent=2)}

CONTACT INTELLIGENCE ({num_contacts} contacts):
{json.dumps(contact_data, indent=2)}

EVENT OPPORTUNITIES ({num_events} GTM opportunities):
{json.dumps(events_data[:5], indent=2)}  # First 5 events

ASSESSMENT CRITERIA:
- Tier 1: Ready for immediate GTM launch (high data quality + contacts + events)
- Tier 2: Launch next quarter (good fundamentals, some gaps)
- Tier 3: Re-evaluate later (insufficient intelligence or poor fit)

Return ONLY valid JSON:
{{
  "tier": "Tier 1 - Ready for GTM",
  "data_completeness": "{data_quality:.0f}% quantitative, {len(diamond_data)} diamonds, {num_contacts}/3 contacts, {num_events} events",
  "first_contact_recommendation": "Specific organization/contact to approach first",
  "gtm_readiness": true,
  "key_opportunities": ["List", "of", "top", "3", "opportunities"],
  "notes": "Strategic insights and any concerns"
}}"""

    try:
        assessment_response = assessment_model.generate_content(assessment_prompt)
        assessment_text = assessment_response.text.strip()
        
        # Parse JSON from response
        def parse_json(text):
            import re
            text = text.strip()
            if text.startswith('{') and text.endswith('}'):
                try:
                    return json.loads(text)
                except:
                    pass
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end+1])
                except:
                    pass
            return None
        
        strategic_assessment = parse_json(assessment_text)
        if not strategic_assessment:
            raise ValueError("Failed to parse strategic assessment")
            
    except Exception as e:
        print(f"❌ Strategic assessment failed: {e}")
        strategic_assessment = {
            "tier": "Tier 3 - Assessment Failed",
            "data_completeness": f"{data_quality:.0f}% quantitative, {len(diamond_data)} diamonds, {num_contacts}/3 contacts, {num_events} events",
            "first_contact_recommendation": "Manual review required",
            "gtm_readiness": False,
            "key_opportunities": [],
            "notes": f"Assessment failed: {str(e)}"
        }

    elapsed = time.time() - start_time
    
    # Compile final comprehensive dossier
    final_dossier = {
        "campus_name": campus_name,
        "generated_at": datetime.now().isoformat(),
        "generation_time_seconds": round(elapsed, 1),
        
        # Quantitative Intelligence
        "growth_correlates_scorecard": quantitative_data,
        "data_quality": results.get("quantitative", {}).get("data_quality", {"quality_score": 0}),
        
        # Qualitative Intelligence  
        "diamond_targets": diamond_data,
        "universal_inroads": contact_data,
        "contact_intelligence": {
            "contacts_found": num_contacts,
            "total_inroads": len(contact_data),
            "success_rate": f"{num_contacts}/{len(contact_data)}"
        },
        
        # Event Intelligence
        "event_opportunities": events_data,
        "event_analysis": results.get("events", {}).get("analysis", {}),
        
        # Strategic Assessment
        "strategic_assessment": strategic_assessment,
        
        # Meta
        "engines_used": ["quantitative_engine", "diamond_finder_engine", "event_intelligence_engine"],
        "intelligence_completeness": {
            "quantitative": bool(quantitative_data),
            "qualitative": bool(diamond_data),
            "contacts": num_contacts > 0,
            "events": bool(events_data)
        }
    }
    
    return final_dossier


def main():
    parser = argparse.ArgumentParser(description="Run Three-Engine GTM Intelligence Scraper")
    parser.add_argument("--campus", help="Name of a single university (e.g., 'University of California, Berkeley')")
    parser.add_argument("--batch", help="Path to a text file with a list of campus names, one per line")
    parser.add_argument("--output", help="Output JSON file for batch processing results")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF report in addition to JSON")
    args = parser.parse_args()

    if not args.campus and not args.batch:
        parser.error("Either --campus or --batch must be provided.")

    tavily_api_key, gemini_api_key = load_api_keys()

    all_results = []
    campuses_to_process = []

    if args.campus:
        campuses_to_process.append(args.campus)
    elif args.batch:
        try:
            with open(args.batch, 'r') as f:
                campuses_to_process = [line.strip() for line in f if line.strip()]
            print(f"Processing {len(campuses_to_process)} campuses from {args.batch}")
        except FileNotFoundError:
            print(f"Error: Batch file '{args.batch}' not found.")
            return 1

    for campus in campuses_to_process:
        try:
            result = run_three_engines(campus, gemini_api_key)
            all_results.append(result)
            
            # Summary output
            tier = result["strategic_assessment"]["tier"]
            quality = result.get("data_quality", {}).get("quality_score", 0)
            diamonds = len(result.get("diamond_targets", []))
            contacts = result.get("contact_intelligence", {}).get("contacts_found", 0)
            events = len(result.get("event_opportunities", []))
            
            print(f"\n{'='*80}")
            print(f"🎉 THREE-ENGINE INTELLIGENCE COMPLETE")
            print(f"⏱️  Time: {result['generation_time_seconds']:.1f}s")
            print(f"📊 Data Quality: {quality:.1f}%")
            print(f"💎 Diamonds: {diamonds}")
            print(f"📞 Contacts: {contacts}/3")
            print(f"📅 Events: {events}")
            print(f"🏆 Assessment: {tier}")
            print(f"{'='*80}")
            
            if not args.batch:  # Print full dossier only for single campus runs
                print(json.dumps(result, indent=2))
                
                # Generate PDF if requested
                if args.pdf:
                    try:
                        pdf_filename = generate_pdf_report(result)
                        print(f"\n📄 PDF report generated: {pdf_filename}")
                    except Exception as e:
                        print(f"⚠️ PDF generation failed: {e}")
            
        except Exception as e:
            print(f"❌ {campus}: Failed - {e}")
            all_results.append({
                "campus_name": campus,
                "status": "Failed",
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            })
    
    if args.batch and args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"\nBatch results saved to {args.output}")
        except Exception as e:
            print(f"Error saving batch results: {e}")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
