#!/usr/bin/env python3
"""
Quantitative Metrics Processor
Generates quantitative scorecards for multiple universities in parallel.
"""

import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv

# Add parent directory for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from quantitative_engine import QuantitativeEngine

def load_api_keys():
    """Load API keys from environment."""
    load_dotenv('../.env')
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment")
    return gemini_key

def process_quantitative_metrics(campus_name: str, gemini_key: str) -> Dict[str, Any]:
    """Process quantitative metrics for a single university."""
    try:
        print(f"📊 Quantitative: {campus_name}")
        start_time = time.time()
        
        # Get quantitative data
        quant_engine = QuantitativeEngine(gemini_key)
        results = quant_engine.run(campus_name)
        scorecard = results.get('prospect_scorecard', {})
        
        elapsed = time.time() - start_time
        
        # Calculate completion percentage
        total_metrics = 9
        completed_metrics = len([m for m in scorecard.values() if isinstance(m, dict) and "error" not in m])
        completion_rate = (completed_metrics / total_metrics) * 100
        
        print(f"✅ {campus_name}: {completion_rate:.1f}% complete ({elapsed:.1f}s)")
        
        return {
            "campus_name": campus_name,
            "status": "success",
            "scorecard": scorecard,
            "completion_rate": completion_rate,
            "metrics_found": completed_metrics,
            "elapsed_time": elapsed
        }
        
    except Exception as e:
        print(f"❌ {campus_name}: {str(e)}")
        return {
            "campus_name": campus_name,
            "status": "failed",
            "error": str(e),
            "scorecard": {},
            "completion_rate": 0,
            "metrics_found": 0,
            "elapsed_time": 0
        }

def generate_quantitative_pdf(results: List[Dict], output_filename: str):
    """Generate PDF focused on quantitative metrics."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=1
    )
    
    section_style = ParagraphStyle(
        'CustomSection',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Title page
    story.append(Paragraph("Quantitative Metrics Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"Universities Analyzed: {len([r for r in results if r['status'] == 'success'])}", styles['Normal']))
    story.append(Spacer(1, 0.5*inch))
    
    # Summary table
    story.append(Paragraph("Quantitative Summary", section_style))
    
    summary_data = [['University', 'Completion %', 'Housing %', 'Centricity', 'NCAA', 'Greek %', 'Acceptance %']]
    
    for result in results:
        if result['status'] == 'success':
            scorecard = result['scorecard']
            campus_name = result['campus_name']
            completion = f"{result['completion_rate']:.1f}%"
            
            # Extract key metrics
            housing = scorecard.get('housing', {}).get('percentInHousing', 'N/A')
            housing_str = f"{housing}%" if isinstance(housing, (int, float)) else str(housing)
            
            centricity = scorecard.get('centricity', {}).get('campusCentricityScore', 'N/A')
            centricity_str = f"{centricity}/10" if isinstance(centricity, (int, float)) else str(centricity)
            
            ncaa = scorecard.get('ncaa', {}).get('ncaaDivision', 'N/A')
            
            greek = scorecard.get('greek', {}).get('percentGreekLife', 'N/A')
            greek_str = f"{greek}%" if isinstance(greek, (int, float)) else str(greek)
            
            acceptance = scorecard.get('acceptance', {}).get('acceptanceRate', 'N/A')
            acceptance_str = f"{acceptance}%" if isinstance(acceptance, (int, float)) else str(acceptance)
            
            summary_data.append([campus_name, completion, housing_str, centricity_str, ncaa, greek_str, acceptance_str])
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1*inch, 1.2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(PageBreak())
    
    # Detailed metrics for each university
    for result in results:
        if result['status'] == 'success':
            story.append(Paragraph(f"{result['campus_name']} - Detailed Metrics", section_style))
            
            scorecard = result['scorecard']
            
            # Create detailed metrics table
            metric_data = [['Metric', 'Value', 'Confidence', 'Source']]
            
            metric_labels = {
                'housing': 'University Housing %',
                'centricity': 'Campus Centricity Score',
                'ncaa': 'NCAA Division',
                'greek': 'Greek Life %',
                'ratio': 'Student:Faculty Ratio',
                'acceptance': 'Acceptance Rate %',
                'out_of_state': 'Out-of-State %',
                'endowment': 'Endowment per Student',
                'retention': 'Freshman Retention %'
            }
            
            for metric_key, label in metric_labels.items():
                metric_info = scorecard.get(metric_key, {})
                if isinstance(metric_info, dict) and "error" not in metric_info:
                    # Extract value based on metric type
                    if metric_key == 'housing':
                        value = f"{metric_info.get('percentInHousing', 'N/A')}%"
                    elif metric_key == 'centricity':
                        value = f"{metric_info.get('campusCentricityScore', 'N/A')}/10"
                    elif metric_key == 'ncaa':
                        value = metric_info.get('ncaaDivision', 'N/A')
                    elif metric_key == 'greek':
                        value = f"{metric_info.get('percentGreekLife', 'N/A')}%"
                    elif metric_key == 'ratio':
                        value = metric_info.get('studentFacultyRatio', 'N/A')
                    elif metric_key == 'acceptance':
                        value = f"{metric_info.get('acceptanceRate', 'N/A')}%"
                    elif metric_key == 'out_of_state':
                        value = f"{metric_info.get('percentOutOfState', 'N/A')}%"
                    elif metric_key == 'endowment':
                        endow = metric_info.get('endowmentPerStudent', 'N/A')
                        if isinstance(endow, (int, float)):
                            value = f"${endow:,}"
                        else:
                            value = str(endow)
                    elif metric_key == 'retention':
                        value = f"{metric_info.get('freshmanRetentionRate', 'N/A')}%"
                    else:
                        value = "N/A"
                    
                    confidence = metric_info.get('confidence', 'N/A')
                    source = str(metric_info.get('source', 'N/A'))[:40]
                    
                    metric_data.append([label, value, confidence, source])
                else:
                    metric_data.append([label, 'N/A', 'N/A', 'Data not found'])
            
            metrics_table = Table(metric_data, colWidths=[2*inch, 1.5*inch, 1*inch, 2.5*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(metrics_table)
            story.append(Spacer(1, 0.3*inch))
    
    doc.build(story)
    print(f"📊 Quantitative PDF generated: {output_filename}")

def main():
    """Main quantitative processing function."""
    universities = [
        "Georgetown University",
        "University of Michigan-Ann Arbor", 
        "Tulane University of Louisiana",
        "Auburn University",
        "Arizona State University Campus Immersion",
        "Howard University",
        "University of Central Florida",
        "Pepperdine University", 
        "Syracuse University",
        "University of Miami"
    ]
    
    print(f"📊 Quantitative Metrics Processing: {len(universities)} Universities")
    print("=" * 60)
    
    # Setup
    gemini_key = load_api_keys()
    start_time = time.time()
    results = []
    
    # Process in parallel (quantitative calls are more isolated)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(process_quantitative_metrics, university, gemini_key): university 
            for university in universities
        }
        
        for future in as_completed(futures):
            university = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"❌ {university} failed with exception: {e}")
                results.append({
                    "campus_name": university,
                    "status": "failed", 
                    "error": str(e),
                    "scorecard": {},
                    "completion_rate": 0,
                    "metrics_found": 0,
                    "elapsed_time": 0
                })
    
    # Generate PDF
    pdf_path = f"../../generated_pdfs/Quantitative_Metrics_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    generate_quantitative_pdf(results, pdf_path)
    
    # Save JSON data
    json_path = f"quantitative_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    total_time = time.time() - start_time
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len([r for r in results if r['status'] == 'failed'])
    avg_completion = sum(r['completion_rate'] for r in results if r['status'] == 'success') / max(successful, 1)
    
    print("\n" + "=" * 60)
    print(f"📊 QUANTITATIVE PROCESSING COMPLETE")
    print(f"✅ Results: {successful} successful, {failed} failed")
    print(f"📈 Average completion rate: {avg_completion:.1f}%")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📄 PDF: {pdf_path}")
    print(f"💾 JSON: {json_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
