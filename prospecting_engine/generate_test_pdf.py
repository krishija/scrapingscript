#!/usr/bin/env python3
"""
Generate PDF from test_5_report.json
"""

import json
import os
from pdf_generator import generate_prospecting_pdf

def main():
    # Load the test report
    if not os.path.exists("test_5_report.json"):
        print("❌ test_5_report.json not found")
        return
    
    with open("test_5_report.json", "r") as f:
        report_data = json.load(f)
    
    print("📂 Loaded test report: test_5_report.json")
    
    # Extract summary info
    detailed_scorecards = report_data.get("detailed_scorecards", [])
    ranked_universities = report_data.get("strategic_ranking", {}).get("ranked_universities", [])
    top_prospects = report_data.get("top_10_prospects", [])
    
    print("📊 Test Data Summary:")
    print(f"   Universities Analyzed: {len(detailed_scorecards)}")
    print(f"   Universities Ranked: {len(ranked_universities)}")
    print(f"   Top Prospect: {ranked_universities[0].get('university', 'N/A') if ranked_universities else 'N/A'}")
    
    # Generate PDF
    try:
        output_filename = generate_prospecting_pdf(report_data)
        print(f"✅ SUCCESS! PDF generated: {output_filename}")
        print("\nYour test prospecting report is ready! 🎉")
        
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        print("Will fix this tonight!")

if __name__ == "__main__":
    main()
