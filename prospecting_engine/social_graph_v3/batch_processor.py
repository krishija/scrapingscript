#!/usr/bin/env python3
"""
Batch GTM Dossier Processor
Runs multiple universities in parallel and generates combined PDF output.
"""

import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from gtm_ready_engine import GTMReadyEngine
from gtm_pdf_generator import generate_gtm_pdf

# Add parent directory for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

def load_api_keys():
    """Load API keys from environment."""
    load_dotenv('../.env')
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment")
    return gemini_key

def process_single_university(campus_name: str, gemini_key: str, output_dir: str) -> Dict[str, Any]:
    """Process a single university and return results."""
    try:
        print(f"🎯 Starting: {campus_name}")
        start_time = time.time()
        
        # Generate dossier
        engine = GTMReadyEngine(gemini_key)
        result = engine.generate_dossier(campus_name)
        
        # Save JSON
        safe_name = campus_name.replace(" ", "_").replace("-", "_").lower()
        json_filename = f"{output_dir}/{safe_name}_dossier.json"
        with open(json_filename, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Generate individual PDF
        pdf_filename = f"{output_dir}/{safe_name}_dossier.pdf"
        generate_gtm_pdf(result, pdf_filename)
        
        elapsed = time.time() - start_time
        
        # Extract key metrics for summary
        dossier = result.get('dossier', {})
        org_count = len(dossier.get('PhantomBuster_Ready_Orgs', []))
        contact_count = dossier.get('Contact_Intelligence', {}).get('total_email_contacts', 0)
        
        print(f"✅ Completed: {campus_name} ({elapsed:.1f}s) - {org_count} orgs, {contact_count} contacts")
        
        return {
            "campus_name": campus_name,
            "status": "success",
            "elapsed_time": elapsed,
            "org_count": org_count,
            "contact_count": contact_count,
            "json_file": json_filename,
            "pdf_file": pdf_filename,
            "dossier_data": result
        }
        
    except Exception as e:
        print(f"❌ Failed: {campus_name} - {str(e)}")
        return {
            "campus_name": campus_name,
            "status": "failed",
            "error": str(e),
            "elapsed_time": 0,
            "org_count": 0,
            "contact_count": 0
        }

def generate_combined_pdf(results: List[Dict], output_filename: str):
    """Generate a combined PDF with all successful dossiers."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    
    # Create document
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
        alignment=1  # Center
    )
    
    section_style = ParagraphStyle(
        'CustomSection',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Title page
    story.append(Paragraph("GTM-Ready Campus Intelligence Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"Universities Analyzed: {len([r for r in results if r['status'] == 'success'])}", styles['Normal']))
    story.append(Spacer(1, 0.5*inch))
    
    # Executive summary table
    story.append(Paragraph("Executive Summary", section_style))
    
    summary_data = [['University', 'Tier', 'Organizations', 'Contacts', 'Key Insight']]
    
    for result in results:
        if result['status'] == 'success':
            dossier = result['dossier_data'].get('dossier', {})
            exec_summary = dossier.get('Executive_Summary', {})
            
            campus_name = result['campus_name']
            tier = exec_summary.get('campus_tier', 'Unknown')
            org_count = str(result['org_count'])
            contact_count = str(result['contact_count'])
            key_insight = exec_summary.get('key_insight', 'N/A')[:50] + "..." if len(exec_summary.get('key_insight', '')) > 50 else exec_summary.get('key_insight', 'N/A')
            
            summary_data.append([campus_name, tier, org_count, contact_count, key_insight])
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1.2*inch, 0.8*inch, 0.8*inch, 2.2*inch])
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
    
    # Individual dossiers
    for result in results:
        if result['status'] == 'success':
            dossier_data = result['dossier_data']
            
            # Generate individual dossier content using existing PDF generator logic
            story.append(Paragraph(f"University Dossier: {result['campus_name']}", title_style))
            
            dossier = dossier_data.get('dossier', {})
            
            # Executive Summary
            exec_summary = dossier.get('Executive_Summary', {})
            if exec_summary:
                story.append(Paragraph("Executive Summary", section_style))
                tier = exec_summary.get('campus_tier', 'Unknown')
                score = exec_summary.get('community_potential_score', 'N/A')
                insight = exec_summary.get('key_insight', 'N/A')
                
                story.append(Paragraph(f"<b>Campus Tier:</b> {tier}", styles['Normal']))
                story.append(Paragraph(f"<b>Community Potential Score:</b> {score}", styles['Normal']))
                story.append(Paragraph(f"<b>Key Insight:</b> {insight}", styles['Normal']))
                story.append(Spacer(1, 0.2*inch))
            
            # Contact Summary
            contacts = dossier.get('Contact_Intelligence', {})
            if contacts:
                story.append(Paragraph(f"Contacts Found: {contacts.get('total_email_contacts', 0)} email contacts", section_style))
                story.append(Spacer(1, 0.1*inch))
            
            # PhantomBuster Ready Orgs
            pb_orgs = dossier.get('PhantomBuster_Ready_Orgs', [])
            if pb_orgs:
                story.append(Paragraph(f"PhantomBuster Ready Organizations ({len(pb_orgs)})", section_style))
                
                # Show top 10 organizations
                for i, org in enumerate(pb_orgs[:10], 1):
                    name = org.get('name', 'Unknown')
                    category = org.get('category', 'Unknown')
                    priority = org.get('target_priority', 'Unknown')
                    story.append(Paragraph(f"{i}. <b>{name}</b> ({category}) - Priority: {priority}", styles['Normal']))
                
                if len(pb_orgs) > 10:
                    story.append(Paragraph(f"... and {len(pb_orgs) - 10} more organizations", styles['Normal']))
                
                story.append(Spacer(1, 0.2*inch))
            
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    print(f"📄 Combined PDF generated: {output_filename}")

def main():
    """Main batch processing function."""
    # Universities to process
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
    
    print(f"🚀 Batch Processing {len(universities)} Universities")
    print("=" * 60)
    
    # Setup
    gemini_key = load_api_keys()
    output_dir = "batch_output"
    os.makedirs(output_dir, exist_ok=True)
    
    start_time = time.time()
    results = []
    
    # Process universities in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:  # Limit to 3 parallel to avoid rate limits
        futures = {
            executor.submit(process_single_university, university, gemini_key, output_dir): university 
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
                    "elapsed_time": 0,
                    "org_count": 0,
                    "contact_count": 0
                })
    
    # Generate combined PDF
    combined_pdf_path = f"../../generated_pdfs/Combined_GTM_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    generate_combined_pdf(results, combined_pdf_path)
    
    # Summary
    total_time = time.time() - start_time
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len([r for r in results if r['status'] == 'failed'])
    total_orgs = sum(r['org_count'] for r in results)
    total_contacts = sum(r['contact_count'] for r in results)
    
    print("\n" + "=" * 60)
    print(f"🎯 BATCH PROCESSING COMPLETE")
    print(f"📊 Results: {successful} successful, {failed} failed")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📋 Total organizations found: {total_orgs}")
    print(f"📧 Total contacts found: {total_contacts}")
    print(f"📄 Combined PDF: {combined_pdf_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
