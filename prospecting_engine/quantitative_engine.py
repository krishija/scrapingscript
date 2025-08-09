"""
Quantitative Engine - "The Science"
Systematic prospect scoring through 9 key metrics for growth correlates analysis.
"""

import os
import time
import json
from typing import Dict, Optional
from dotenv import load_dotenv
import google.generativeai as genai

from tools import tool_web_search
from prompts import (
    EXTRACT_HOUSING_PROMPT, EXTRACT_CENTRICITY_PROMPT, EXTRACT_NCAA_PROMPT,
    EXTRACT_GREEK_PROMPT, EXTRACT_RATIO_PROMPT, EXTRACT_ACCEPTANCE_PROMPT,
    EXTRACT_OUT_OF_STATE_PROMPT, EXTRACT_ENDOWMENT_PROMPT, EXTRACT_RETENTION_PROMPT
)


class QuantitativeEngine:
    """Impartial data collector for campus prospect scoring."""
    
    def __init__(self, gemini_api_key: str):
        self.model = self._init_gemini(gemini_api_key)

    def _init_gemini(self, api_key: str):
        """Initialize Gemini model with fallback options."""
        genai.configure(api_key=api_key)
        for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                _ = model.generate_content("test")
                print(f"📊 Quantitative Engine: {model_name}")
                return model
            except Exception as e:
                print(f"Failed to init {model_name}: {e}")
                continue
        raise RuntimeError("Failed to initialize any Gemini model")

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Parse JSON from AI response with multiple fallback strategies."""
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

    def extract_metric(self, prompt: str, search_data: str, campus_name: str) -> Dict:
        """Extract a single metric using AI with error handling."""
        try:
            formatted_prompt = prompt.format(campus_name=campus_name, search_data=search_data)
            response = self.model.generate_content(formatted_prompt)
            result = self._parse_json(response.text)
            return result or {"error": "Failed to parse response"}
        except Exception as e:
            return {"error": str(e)}

    def run(self, campus_name: str) -> Dict:
        """
        Main quantitative analysis workflow.
        
        Returns dict with 9 key metrics for prospect scoring.
        """
        print(f"\n📊 QUANTITATIVE PROSPECT SCORING: {campus_name}")
        print("="*60)
        
        # Define all 9 metrics with optimized queries
        metrics_config = {
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
                    f'"{campus_name}" NCAA division athletics sports conference',
                    f'"{campus_name}" athletic conference division'
                ],
                "prompt": EXTRACT_NCAA_PROMPT
            },
            "greek": {
                "queries": [
                    f'"{campus_name}" Common Data Set greek life fraternity percentage',
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
                    f'"{campus_name}" acceptance rate admissions statistics 2024',
                    f'"{campus_name}" admissions rate US News'
                ],
                "prompt": EXTRACT_ACCEPTANCE_PROMPT
            },
            "out_of_state": {
                "queries": [
                    f'"{campus_name}" out of state students percentage',
                    f'"{campus_name}" Common Data Set geographic diversity'
                ],
                "prompt": EXTRACT_OUT_OF_STATE_PROMPT
            },
            "endowment": {
                "queries": [
                    f'"{campus_name}" endowment per student total enrollment',
                    f'"{campus_name}" university endowment size'
                ],
                "prompt": EXTRACT_ENDOWMENT_PROMPT
            },
            "retention": {
                "queries": [
                    f'"{campus_name}" freshman retention rate Common Data Set',
                    f'"{campus_name}" first year student retention statistics'
                ],
                "prompt": EXTRACT_RETENTION_PROMPT
            }
        }
        
        results = {"prospect_scorecard": {}, "data_quality": {}}
        
        # Process each metric with early exit optimization
        for metric_name, config in metrics_config.items():
            print(f"\n🔍 Analyzing: {metric_name.upper()}")
            
            search_results = []
            extracted = None
            
            for i, query in enumerate(config["queries"]):
                print(f"   Query {i+1}/{len(config['queries'])}: {query[:60]}...")
                try:
                    result = tool_web_search(query, max_results=3)  # Reduced for efficiency
                    if result.get("corpus"):
                        search_results.append(result["corpus"])
                    
                    # Early exit check: if first query gives high confidence, stop
                    if i == 0 and search_results:
                        temp_data = search_results[0][:6000]
                        temp_metric = self.extract_metric(config["prompt"], temp_data, campus_name)
                        if temp_metric.get("confidence") == "high":
                            print(f"   ⚡ Early exit: High confidence data found")
                            extracted = temp_metric
                            break
                    
                    time.sleep(1.0)  # Increased rate limiting to avoid 429 errors
                except Exception as e:
                    print(f"   ❌ Query failed: {e}")
            
            # Final extraction if no early exit
            if not extracted:
                if search_results:
                    combined_data = "\n\n---\n\n".join(search_results)[:10000]
                    extracted = self.extract_metric(config["prompt"], combined_data, campus_name)
                else:
                    extracted = {"error": "No search data found"}
            
            results["prospect_scorecard"][metric_name] = extracted
            confidence = extracted.get("confidence", "unknown")
            if extracted.get("error"):
                print(f"   ❌ No data found")
            else:
                print(f"   ✅ Extracted: {confidence} confidence")
        
        # Calculate data quality score
        valid_metrics = sum(1 for m in results["prospect_scorecard"].values() 
                          if "error" not in m and m.get("confidence") != "none")
        results["data_quality"] = {
            "valid_metrics": valid_metrics,
            "total_metrics": 9,
            "quality_score": round(valid_metrics / 9 * 100, 1)
        }
        
        print(f"\n📊 PROSPECT SCORING COMPLETE")
        print(f"   Data Quality: {results['data_quality']['quality_score']:.1f}% ({valid_metrics}/9 metrics)")
        
        return results
