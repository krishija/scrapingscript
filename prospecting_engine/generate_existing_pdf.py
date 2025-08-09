#!/usr/bin/env python3
"""
Generate PDF from existing data without making any new API calls.
Perfect for presenting results we already have!
"""

import json
import sys
from pdf_generator import generate_prospecting_pdf

def main():
    input_file = "full_report.json"
    
    try:
        # Load existing report
        with open(input_file, 'r') as f:
            report_data = json.load(f)
        
        print(f"📂 Loaded existing report: {input_file}")
        
        # Check what data we have
        summary = report_data.get("prospecting_summary", {})
        universities = summary.get("total_universities_analyzed", 0)
        ranked = len(report_data.get("strategic_ranking", {}).get("ranked_universities", []))
        
        print(f"📊 Data Summary:")
        print(f"   Universities Analyzed: {universities}")
        print(f"   Universities Ranked: {ranked}")
        print(f"   Top Prospect: {report_data.get('key_insights', {}).get('highest_potential', 'N/A')}")
        
        # Generate PDF from existing data
        print(f"\n📄 Generating PDF from existing data...")
        pdf_filename = generate_prospecting_pdf(report_data)
        
        print(f"✅ SUCCESS! PDF generated: {pdf_filename}")
        print(f"\nYour professional prospecting report is ready! 🎉")
        
    except FileNotFoundError:
        print(f"❌ File not found: {input_file}")
        print("Make sure you have run the prospecting engine at least once.")
        return 1
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
