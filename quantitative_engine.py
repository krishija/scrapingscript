#!/usr/bin/env python3
"""
Quantitative Engine - "The Science"
Systematically extracts 6 key metrics for Growth Correlates analysis.
"""

import os
import time
import json
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv

import google.generativeai as genai
from tools import tool_web_search


# Quantitative metrics extraction prompts
EXTRACT_HOUSING_PROMPT = """You are a data analyst extracting housing statistics.

From the following search results, find the MOST ACCURATE percentage of undergraduate students living in university housing at {campus_name}.

Look for:
- Common Data Set reports
- Official university statistics
- US News data
- IPEDS data

Search Results:
{search_data}

Return ONLY a JSON object:
{{"percentInHousing": 45.5, "source": "Common Data Set 2024", "confidence": "high/medium/low"}}

If no data found, return: {{"percentInHousing": null, "source": "not found", "confidence": "none"}}"""

EXTRACT_CENTRICITY_PROMPT = """You are analyzing campus centricity from search results.

Based on these results about {campus_name}, assign a Campus-Centricity Score (1-10 scale):
- 10 = Highly isolated college town (like Dartmouth)
- 5-7 = Mixed urban/campus environment 
- 1 = Fully integrated urban campus (like NYU)

Search Results:
{search_data}

Return ONLY: {{"campusCentricityScore": 7, "justification": "Brief reasoning", "confidence": "high/medium/low"}}"""

EXTRACT_NCAA_PROMPT = """Find the NCAA Division for {campus_name} athletics.

Search Results:
{search_data}

Return ONLY: {{"ncaaDivision": "D1/D2/D3/NAIA/None", "conference": "conference name if found", "confidence": "high/medium/low"}}"""

EXTRACT_GREEK_PROMPT = """Find the percentage of students in Greek Life at {campus_name}.

Search Results:
{search_data}

Return ONLY: {{"percentGreekLife": 25.5, "source": "source name", "confidence": "high/medium/low"}}

If no data: {{"percentGreekLife": null, "source": "not found", "confidence": "none"}}"""

EXTRACT_RATIO_PROMPT = """Find the student-to-faculty ratio at {campus_name}.

Search Results:
{search_data}

Return ONLY: {{"studentFacultyRatio": "15:1", "source": "source name", "confidence": "high/medium/low"}}"""

EXTRACT_ACCEPTANCE_PROMPT = """Find the acceptance rate at {campus_name}.

Search Results:
{search_data}

Return ONLY: {{"acceptanceRate": 12.5, "source": "US News 2024", "confidence": "high/medium/low"}}"""


class QuantitativeEngine:
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
            try:
                self.model = genai.GenerativeModel(model_name)
                _ = self.model.generate_content("test")
                print(f"📊 Quantitative Engine: {model_name}")
                break
            except Exception as e:
                print(f"Failed to init {model_name}: {e}")
                continue
        else:
            raise RuntimeError("Failed to initialize Gemini model")
    
    def extract_metric(self, prompt: str, search_data: str, campus_name: str) -> Dict:
        """Extract a single metric using Gemini."""
        try:
            formatted_prompt = prompt.format(campus_name=campus_name, search_data=search_data)
            response = self.model.generate_content(formatted_prompt)
            result = self._parse_json(response.text)
            return result or {"error": "Failed to parse response"}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from Gemini response."""
        text = text.strip()
        
        # Try direct parsing
        if text.startswith('{') and text.endswith('}'):
            try:
                return json.loads(text)
            except:
                pass
        
        # Look for JSON in markdown blocks
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
    
    def run_quantitative_analysis(self, campus_name: str) -> Dict:
        """Run the complete 6-metric quantitative analysis."""
        print(f"\n📊 QUANTITATIVE ENGINE: {campus_name}")
        print("="*60)
        
        # Define metric queries
        metrics = {
            "housing": {
                "queries": [
                    f'"{campus_name}" "Common Data Set" housing undergraduate percentage',
                    f'"{campus_name}" student housing statistics site:.edu'
                ],
                "prompt": EXTRACT_HOUSING_PROMPT
            },
            "centricity": {
                "queries": [
                    f'"{campus_name}" Walk Score college town site:reddit.com',
                    f'"{campus_name}" campus location urban suburban college town'
                ],
                "prompt": EXTRACT_CENTRICITY_PROMPT
            },
            "ncaa": {
                "queries": [
                    f'"{campus_name}" NCAA division athletics sports',
                    f'"{campus_name}" athletic conference division'
                ],
                "prompt": EXTRACT_NCAA_PROMPT
            },
            "greek": {
                "queries": [
                    f'"{campus_name}" Common Data Set greek life fraternity',
                    f'"{campus_name}" greek life percentage statistics'
                ],
                "prompt": EXTRACT_GREEK_PROMPT
            },
            "ratio": {
                "queries": [
                    f'"{campus_name}" student faculty ratio statistics',
                    f'"{campus_name}" US News student faculty ratio'
                ],
                "prompt": EXTRACT_RATIO_PROMPT
            },
            "acceptance": {
                "queries": [
                    f'"{campus_name}" acceptance rate admissions statistics',
                    f'"{campus_name}" US News acceptance rate 2024'
                ],
                "prompt": EXTRACT_ACCEPTANCE_PROMPT
            }
        }
        
        results = {
            "campus_name": campus_name,
            "growth_correlates": {},
            "data_quality": {}
        }
        
        # Process each metric
        for metric_name, config in metrics.items():
            print(f"\n🔍 Analyzing: {metric_name.upper()}")
            
            # Gather search data for this metric with early exit optimization
            search_results = []
            extracted = None
            
            for i, query in enumerate(config["queries"]):
                print(f"   Query {i+1}/{len(config['queries'])}: {query[:60]}...")
                try:
                    result = tool_web_search(query)
                    if result.get("corpus"):
                        search_results.append(result["corpus"])
                    
                    # Early exit check: if first query gives high confidence, stop
                    if i == 0 and search_results:
                        temp_data = search_results[0][:8000]
                        temp_metric = self.extract_metric(config["prompt"], temp_data, campus_name)
                        if temp_metric.get("confidence") == "high":
                            print(f"   ⚡ Early exit: High confidence data found")
                            extracted = temp_metric
                            break
                    
                    time.sleep(0.3)  # Rate limiting
                except Exception as e:
                    print(f"   ❌ Query failed: {e}")
            
            # Use early exit result or combine all data
            if not extracted:
                combined_data = "\n\n---\n\n".join(search_results)[:12000]  # Limit context
            
            # Extract metric using AI (if not already extracted via early exit)
            if not extracted:
                if search_results:
                    combined_data = "\n\n---\n\n".join(search_results)[:12000]
                    extracted = self.extract_metric(config["prompt"], combined_data, campus_name)
                else:
                    extracted = {"error": "No search data found"}
            
            results["growth_correlates"][metric_name] = extracted
            confidence = extracted.get("confidence", "unknown")
            if extracted.get("error"):
                print(f"   ❌ No data found")
            else:
                print(f"   ✅ Extracted: {confidence} confidence")
        
        # Calculate data quality score
        valid_metrics = sum(1 for m in results["growth_correlates"].values() 
                          if "error" not in m and m.get("confidence") != "none")
        results["data_quality"]["valid_metrics"] = valid_metrics
        results["data_quality"]["total_metrics"] = 6
        results["data_quality"]["quality_score"] = round(valid_metrics / 6 * 100, 1)
        
        print(f"\n📊 QUANTITATIVE ANALYSIS COMPLETE")
        print(f"   Data Quality: {results['data_quality']['quality_score']}% ({valid_metrics}/6 metrics)")
        
        return results


def run_quantitative_engine(campus_name: str, gemini_api_key: str) -> Dict:
    """Entry point for quantitative analysis."""
    engine = QuantitativeEngine(gemini_api_key)
    return engine.run_quantitative_analysis(campus_name)
