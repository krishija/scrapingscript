#!/usr/bin/env python3
"""
Prospecting Engine - Main Orchestrator

This is the central command for our systematic prospecting workflow:
1. Prospect Scoring: Quantitative analysis of all universities
2. Strategic Ranking: AI-powered ranking based on community potential  
3. Targeted Sourcing: Deep dive contact finding for top prospects

Designed for efficient batch processing of university prospects.
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
from qualitative_engine import QualitativeEngine
from event_intelligence_engine import EventIntelligenceEngine
from master_contact_engine import MasterContactEngine
from prompts import STRATEGIC_RANKING_PROMPT
from pdf_generator import generate_prospecting_pdf


def load_api_keys():
    """Load API keys from environment."""
    load_dotenv()
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in .env file")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    return tavily_api_key, gemini_api_key


def init_gemini(api_key: str):
    """Initialize Gemini for strategic ranking."""
    genai.configure(api_key=api_key)
    for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            _ = model.generate_content("test")
            return model
        except Exception as e:
            print(f"Failed to init {model_name}: {e}")
            continue
    raise RuntimeError("Failed to initialize any Gemini model")


def parse_json_response(text: str):
    """Parse JSON from AI response with fallback strategies."""
    text = text.strip()
    if text.startswith('{') and text.endswith('}'):
        try:
            return json.loads(text)
        except:
            pass
    
    import re
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


def process_single_university(university: str, gemini_api_key: str, existing_data: Dict = None) -> Dict:
    """Process a single university for parallel execution."""
    # Skip if we already have good data for this university
    if existing_data and existing_data.get("scorecard", {}).get("data_quality", {}).get("quality_score", 0) > 50:
        print(f"   ♻️ Using cached data for {university} ({existing_data['scorecard']['data_quality']['quality_score']:.1f}%)")
        return existing_data
    
    try:
        quantitative_engine = QuantitativeEngine(gemini_api_key)
        scorecard = quantitative_engine.run(university)
        return {
            "university": university,
            "scorecard": scorecard,
            "processed_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "university": university,
            "scorecard": {"error": str(e)},
            "processed_at": datetime.now().isoformat()
        }


def load_existing_data(output_file: str) -> Dict:
    """Load existing data to avoid reprocessing."""
    try:
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                existing_report = json.load(f)
            existing_data = {item["university"]: item for item in existing_report.get("detailed_scorecards", [])}
            print(f"📂 Loaded existing data for {len(existing_data)} universities")
            return existing_data
    except Exception as e:
        print(f"⚠️ Could not load existing data: {e}")
    return {}


def phase1_prospect_scoring(universities: List[str], gemini_api_key: str, max_workers: int = 4, existing_data: Dict = None) -> List[Dict]:
    """
    Phase 1: Run quantitative analysis on all universities in parallel.
    
    Returns list of university data with prospect scorecards.
    """
    if existing_data is None:
        existing_data = {}
    
    print(f"\n🎯 PHASE 1: PROSPECT SCORING ({len(universities)} universities, {max_workers} parallel workers)")
    print("="*70)
    
    university_data = []
    
    # Process universities in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks with existing data check
        future_to_university = {
            executor.submit(process_single_university, university, gemini_api_key, existing_data.get(university)): university 
            for university in universities
        }
        
        # Collect results as they complete
        for i, future in enumerate(as_completed(future_to_university), 1):
            university = future_to_university[future]
            print(f"\n[{i}/{len(universities)}] Completed: {university}")
            
            try:
                result = future.result()
                university_data.append(result)
                
                # Quick status check
                if "error" in result["scorecard"]:
                    print(f"   ❌ Failed: {result['scorecard']['error']}")
                else:
                    quality = result["scorecard"].get("data_quality", {}).get("quality_score", 0)
                    print(f"   ✅ Success: {quality:.1f}% data quality")
                    
            except Exception as e:
                print(f"   ❌ Exception processing {university}: {e}")
                university_data.append({
                    "university": university,
                    "scorecard": {"error": str(e)},
                    "processed_at": datetime.now().isoformat()
                })
    
    successful = len([u for u in university_data if "error" not in u["scorecard"]])
    print(f"\n✅ PHASE 1 COMPLETE: {successful}/{len(universities)} universities analyzed")
    
    return university_data


def phase2_strategic_ranking(university_data: List[Dict], gemini_api_key: str) -> Dict:
    """
    Phase 2: AI-powered strategic ranking based on community potential.
    
    Returns ranked list with strategic insights.
    """
    print(f"\n📈 PHASE 2: STRATEGIC RANKING")
    print("="*70)
    
    # Prepare data for ranking AI
    ranking_data = []
    for uni_data in university_data:
        if "error" not in uni_data["scorecard"]:
            university = uni_data["university"]
            scorecard = uni_data["scorecard"]["prospect_scorecard"]
            quality = uni_data["scorecard"]["data_quality"]["quality_score"]
            
            ranking_data.append({
                "university": university,
                "data_quality": quality,
                "metrics": scorecard
            })
    
    if not ranking_data:
        print("❌ No valid university data for ranking")
        return {"error": "No valid data for ranking"}
    
    # Format data for AI prompt
    data_summary = json.dumps(ranking_data, indent=2)
    
    # Strategic ranking with AI
    ranking_model = init_gemini(gemini_api_key)
    ranking_prompt = STRATEGIC_RANKING_PROMPT.format(university_data=data_summary)
    
    try:
        print("🧠 Running strategic analysis...")
        response = ranking_model.generate_content(ranking_prompt)
        ranking_result = parse_json_response(response.text)
        
        if ranking_result:
            print(f"✅ PHASE 2 COMPLETE: {len(ranking_result.get('ranked_universities', []))} universities ranked")
            return ranking_result
        else:
            print("❌ Failed to parse ranking results")
            return {"error": "Failed to parse ranking"}
            
    except Exception as e:
        print(f"❌ Strategic ranking failed: {e}")
        return {"error": str(e)}


def process_single_university_contacts(university: str, gemini_api_key: str) -> tuple:
    """Process contact sourcing for a single university using Master Contact Engine."""
    try:
        # Use the new Master Contact Engine for bulletproof contact finding
        master_engine = MasterContactEngine(gemini_api_key)
        result = master_engine.run(university)
        
        # Convert to expected format for compatibility
        if "final_contacts" in result:
            contacts = {
                "student_contacts": result["final_contacts"],
                "contacts_with_email": len(result["final_contacts"]),
                "total_contacts_found": result.get("total_contacts_found", len(result["final_contacts"])),
                "engines_used": result.get("engines_used", []),
                "success_rate": result.get("success_rate", "unknown")
            }
        else:
            contacts = {"error": result.get("error", "Unknown error")}
        
        return university, contacts
    except Exception as e:
        return university, {"error": str(e)}


def phase3_targeted_sourcing(top_universities: List[str], gemini_api_key: str, max_workers: int = 2) -> Dict:
    """
    Phase 3: Deep dive contact finding for top-ranked universities in parallel.
    
    Returns social leader contacts for priority targets.
    """
    print(f"\n👥 PHASE 3: TARGETED SOURCING (Top {len(top_universities)} universities, {max_workers} parallel workers)")
    print("="*70)
    
    contact_results = {}
    
    # Process universities in parallel (fewer workers for API rate limiting)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_university = {
            executor.submit(process_single_university_contacts, university, gemini_api_key): university 
            for university in top_universities
        }
        
        # Collect results as they complete
        for i, future in enumerate(as_completed(future_to_university), 1):
            university = future_to_university[future]
            print(f"\n[{i}/{len(top_universities)}] Completed: {university}")
            
            try:
                university_result, contacts = future.result()
                contact_results[university_result] = contacts
                
                # Quick status check
                if "error" in contacts:
                    print(f"   ❌ Failed: {contacts['error']}")
                else:
                    contacts_found = len(contacts.get("student_contacts", contacts.get("social_leaders", [])))
                    emails = contacts.get("contacts_with_email", contacts.get("leaders_with_email", 0))
                    print(f"   ✅ Success: {contacts_found} contacts, {emails} with emails")
                    
            except Exception as e:
                print(f"   ❌ Exception processing {university}: {e}")
                contact_results[university] = {"error": str(e)}
    
    # Summary statistics  
    total_contacts = sum(len(result.get("student_contacts", result.get("social_leaders", []))) for result in contact_results.values())
    total_emails = sum(result.get("contacts_with_email", result.get("leaders_with_email", 0)) for result in contact_results.values())
    
    print(f"\n✅ PHASE 3 COMPLETE:")
    print(f"   Total Student Contacts: {total_contacts}")
    print(f"   With Email Contacts: {total_emails}")
    
    return contact_results


def generate_final_report(university_data: List[Dict], ranking_result: Dict, contact_results: Dict) -> Dict:
    """Generate comprehensive prospecting report."""
    
    # Extract top 10 for summary
    top_10 = ranking_result.get("ranked_universities", [])[:10]
    
    # Calculate summary statistics
    total_universities = len(university_data)
    successful_scores = len([u for u in university_data if "error" not in u["scorecard"]])
    total_contacts = sum(len(result.get("student_contacts", result.get("social_leaders", []))) for result in contact_results.values())
    
    final_report = {
        "prospecting_summary": {
            "generated_at": datetime.now().isoformat(),
            "total_universities_analyzed": total_universities,
            "successful_scorecards": successful_scores,
            "universities_ranked": len(ranking_result.get("ranked_universities", [])),
            "top_prospects_sourced": len(contact_results),
            "total_student_contacts_found": total_contacts
        },
        "methodology": {
            "phase_1": "Quantitative prospect scoring (9 key metrics)",
            "phase_2": "AI-powered strategic ranking based on community potential",
            "phase_3": "Targeted social leader contact sourcing for top prospects"
        },
        "strategic_ranking": ranking_result,
        "top_10_prospects": top_10,
        "detailed_scorecards": university_data,
        "social_leader_contacts": contact_results,
        "key_insights": {
            "highest_potential": top_10[0]["university"] if top_10 else "N/A",
            "hidden_gems": ranking_result.get("hidden_gems", []),
            "contact_success_rate": f"{sum(r.get('contacts_with_email', r.get('leaders_with_email', 0)) for r in contact_results.values())}/{total_contacts}"
        }
    }
    
    return final_report


def main():
    """Main orchestrator workflow."""
    parser = argparse.ArgumentParser(description="Run University Prospecting Engine")
    parser.add_argument("--universities", default="example_campus_list.txt", 
                       help="Text file with list of universities (one per line)")
    parser.add_argument("--output", default="prospecting_report.json",
                       help="Output JSON file for final report")
    parser.add_argument("--top-n", type=int, default=10,
                       help="Number of top universities to source contacts for")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of parallel workers for quantitative analysis")
    parser.add_argument("--contact-workers", type=int, default=2,
                       help="Number of parallel workers for contact sourcing")
    parser.add_argument("--pdf", action="store_true",
                       help="Generate PDF report in addition to JSON")
    parser.add_argument("--batch-size", type=int, default=10,
                       help="Process universities in batches of this size (default: 10)")
    args = parser.parse_args()
    
    # Load configuration
    tavily_api_key, gemini_api_key = load_api_keys()
    
    # Load universities list
    try:
        with open(args.universities, 'r') as f:
            universities = [line.strip() for line in f if line.strip()]
        print(f"📋 Loaded {len(universities)} universities from {args.universities}")
    except FileNotFoundError:
        print(f"❌ University list file not found: {args.universities}")
        return 1
    
    start_time = time.time()
    
    # Load existing data to avoid reprocessing
    existing_data = load_existing_data(args.output)
    
    # Phase 1: Prospect Scoring (Batched with caching)
    all_university_data = []
    
    # Process in batches to avoid rate limits
    for batch_num, i in enumerate(range(0, len(universities), args.batch_size), 1):
        batch = universities[i:i + args.batch_size]
        print(f"\n🔄 PROCESSING BATCH {batch_num}/{(len(universities) + args.batch_size - 1) // args.batch_size} ({len(batch)} universities)")
        
        batch_data = phase1_prospect_scoring(batch, gemini_api_key, max_workers=min(args.workers, len(batch)), existing_data=existing_data)
        all_university_data.extend(batch_data)
        
        # Save progress after each batch
        progress_report = generate_final_report(all_university_data, {"ranked_universities": []}, {})
        try:
            with open(args.output, 'w') as f:
                json.dump(progress_report, f, indent=2)
            print(f"💾 Progress saved after batch {batch_num}")
        except Exception as e:
            print(f"⚠️ Failed to save progress: {e}")
        
        # Longer pause between batches
        if batch_num < (len(universities) + args.batch_size - 1) // args.batch_size:
            print(f"⏸️ Cooling down for 30 seconds between batches...")
            time.sleep(30)
    
    university_data = all_university_data
    
    # Phase 2: Strategic Ranking  
    ranking_result = phase2_strategic_ranking(university_data, gemini_api_key)
    
    if "error" in ranking_result:
        print(f"❌ Cannot proceed to Phase 3: {ranking_result['error']}")
        return 1
    
    # Phase 3: Targeted Sourcing (top N universities, Parallelized)
    top_universities = [u["university"] for u in ranking_result.get("ranked_universities", [])[:args.top_n]]
    contact_results = phase3_targeted_sourcing(top_universities, gemini_api_key, max_workers=args.contact_workers)
    
    # Generate final report
    final_report = generate_final_report(university_data, ranking_result, contact_results)
    
    # Save results
    try:
        with open(args.output, 'w') as f:
            json.dump(final_report, f, indent=2)
        print(f"\n📄 Final report saved: {args.output}")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")
        return 1
    
    # Generate PDF report if requested
    if args.pdf:
        try:
            pdf_filename = generate_prospecting_pdf(final_report)
            print(f"📄 PDF report generated: {pdf_filename}")
        except Exception as e:
            print(f"⚠️ PDF generation failed: {e}")
            # Don't fail the whole script for PDF issues
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n🎉 PROSPECTING ENGINE COMPLETE")
    print(f"⏱️  Total Time: {elapsed/60:.1f} minutes")
    print(f"📊 Universities Analyzed: {len(university_data)}")
    print(f"🏆 Top Prospect: {final_report['key_insights']['highest_potential']}")
    print(f"👥 Student Contacts Found: {final_report['prospecting_summary']['total_student_contacts_found']}")
    
    return 0


if __name__ == "__main__":
    exit(main())
