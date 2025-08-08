#!/usr/bin/env python3
"""
Two-Engine Campus Intelligence Scraper
Parallel execution of Quantitative Engine + Diamond Finder Engine for scalable GTM intelligence.
"""

import argparse
import json
import os
import time
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from quantitative_engine import QuantitativeEngine
from diamond_finder_engine import DiamondFinderEngine
from event_intelligence_engine import EventIntelligenceEngine


def load_api_keys():
    load_dotenv()
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in .env file")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    return tavily_api_key, gemini_api_key


def run_parallel_engines(campus_name: str, gemini_api_key: str) -> Dict:
    """Run both engines in parallel for maximum efficiency."""
    
    print(f"\n🚀 TWO-ENGINE SCRAPER: {campus_name}")
    print("🏗️  Running Quantitative + Diamond Finder engines in parallel...")
    print("="*80)
    
    start_time = time.time()
    
    # Run engines in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both engines
        quantitative_future = executor.submit(run_quantitative_engine, campus_name, gemini_api_key)
        diamond_future = executor.submit(run_diamond_finder_engine, campus_name, gemini_api_key)
        
        # Collect results as they complete
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
    
    elapsed = time.time() - start_time
    
    # Combine results into final dossier
    final_dossier = {
        "campus_name": campus_name,
        "generated_at": datetime.now().isoformat(),
        "generation_time_seconds": round(elapsed, 1),
        
        # Quantitative Engine Results
        "growth_correlates_scorecard": results.get("quantitative", {}).get("growth_correlates", {}),
        "data_quality": results.get("quantitative", {}).get("data_quality", {"quality_score": 0}),
        
        # Diamond Finder Engine Results  
        "diamond_targets": results.get("qualitative", {}).get("diamond_orgs", []),
        "universal_inroads": results.get("qualitative", {}).get("universal_inroads", {}),
        "analysis_quality": results.get("qualitative", {}).get("analysis_quality", {}),
        
        # Strategic Assessment
        "strategic_assessment": generate_strategic_assessment(results),
        
        # Execution metadata
        "engines_used": ["quantitative_engine", "diamond_finder_engine"],
        "parallel_execution": True
    }
    
    return final_dossier


def generate_strategic_assessment(results: Dict) -> Dict:
    """Generate strategic assessment based on both engines' outputs."""
    
    quant_data = results.get("quantitative", {}).get("growth_correlates", {})
    qual_data = results.get("qualitative", {})
    
    # Calculate overall data completeness
    quant_quality = results.get("quantitative", {}).get("data_quality", {}).get("quality_score", 0)
    diamonds_count = len(qual_data.get("diamond_orgs", []))
    inroads_count = qual_data.get("analysis_quality", {}).get("inroads_found", 0)
    
    # Determine tier based on data quality and completeness
    if quant_quality >= 80 and diamonds_count >= 5 and inroads_count >= 2:
        tier = "Tier 1 - Ready for GTM"
    elif quant_quality >= 60 and (diamonds_count >= 3 or inroads_count >= 2):
        tier = "Tier 2 - Needs Additional Research"
    else:
        tier = "Tier 3 - Insufficient Intelligence"
    
    # Identify best first contact
    inroads = qual_data.get("universal_inroads", {})
    first_contact = "Unknown"
    
    if inroads.get("student_newspaper", {}).get("contact"):
        first_contact = f"Student Newspaper: {inroads['student_newspaper']['contact']}"
    elif inroads.get("student_government", {}).get("contact"):
        first_contact = f"Student Government: {inroads['student_government']['contact']}"
    elif diamonds_count > 0:
        first_contact = f"Diamond Org: {qual_data['diamond_orgs'][0]['name']}"
    
    return {
        "tier": tier,
        "data_completeness": f"{quant_quality}% quantitative, {diamonds_count} diamonds, {inroads_count}/4 inroads",
        "first_contact_recommendation": first_contact,
        "gtm_readiness": quant_quality >= 70 and (diamonds_count >= 3 or inroads_count >= 2),
        "notes": f"Quantitative: {quant_quality}%, Diamonds: {diamonds_count}, Inroads: {inroads_count}/4"
    }


def run_batch_analysis(campus_list: List[str], output_file: str = None) -> None:
    """Run analysis on multiple campuses for Growth Correlates project."""
    
    print(f"\n🎯 BATCH ANALYSIS MODE")
    print(f"📊 Processing {len(campus_list)} campuses for Growth Correlates analysis")
    print("="*80)
    
    _, gemini_api_key = load_api_keys()
    all_results = []
    
    for i, campus in enumerate(campus_list, 1):
        print(f"\n[{i}/{len(campus_list)}] Processing: {campus}")
        
        try:
            result = run_parallel_engines(campus, gemini_api_key)
            all_results.append(result)
            
            # Brief summary
            tier = result["strategic_assessment"]["tier"]
            quality = result.get("data_quality", {}).get("quality_score", 0)
            diamonds = len(result.get("diamond_targets", []))
            print(f"✅ {campus}: {tier} ({quality}% data, {diamonds} diamonds)")
            
        except Exception as e:
            print(f"❌ {campus}: Failed - {e}")
            all_results.append({
                "campus_name": campus,
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            })
        
        # Rate limiting between campuses
        if i < len(campus_list):
            time.sleep(2)
    
    # Save results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n📁 Results saved to: {output_file}")
    
    # Summary statistics
    successful = [r for r in all_results if "error" not in r]
    tier1_count = len([r for r in successful if "Tier 1" in r.get("strategic_assessment", {}).get("tier", "")])
    
    print(f"\n📊 BATCH ANALYSIS COMPLETE")
    print(f"   Successful: {len(successful)}/{len(campus_list)}")
    print(f"   Tier 1 Ready: {tier1_count}")
    print(f"   Average Data Quality: {sum(r.get('data_quality', {}).get('quality_score', 0) for r in successful) / len(successful):.1f}%" if successful else "N/A")


def main():
    parser = argparse.ArgumentParser(description="Two-Engine Campus Intelligence Scraper")
    parser.add_argument("--campus", help="Single campus to analyze")
    parser.add_argument("--batch", help="File containing list of campuses (one per line)")
    parser.add_argument("--output", help="Output file for batch results (JSON)")
    
    args = parser.parse_args()
    
    try:
        _, gemini_api_key = load_api_keys()
        
        if args.campus:
            # Single campus mode
            result = run_parallel_engines(args.campus, gemini_api_key)
            
            print(f"\n{'='*80}")
            print(f"🎉 TWO-ENGINE ANALYSIS COMPLETE")
            print(f"⏱️  Time: {result['generation_time_seconds']}s")
            print(f"📊 Data Quality: {result['data_quality']['quality_score']}%")
            print(f"💎 Diamonds Found: {len(result['diamond_targets'])}")
            print(f"🎯 Inroads: {result['analysis_quality']['inroads_found']}/4")
            print(f"🏆 Assessment: {result['strategic_assessment']['tier']}")
            print('='*80)
            print(json.dumps(result, indent=2))
            
        elif args.batch:
            # Batch mode
            with open(args.batch, 'r') as f:
                campus_list = [line.strip() for line in f if line.strip()]
            
            output_file = args.output or f"batch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            run_batch_analysis(campus_list, output_file)
            
        else:
            print("❌ Error: Must specify either --campus or --batch")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
