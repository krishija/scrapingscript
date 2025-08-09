"""
GTM-Ready Dossier PDF Generator

Creates professional PDF reports from GTM-Ready dossier JSON data.
Optimized for the 5-section structure: Executive Summary, Quantitative Scorecard,
Qualitative Intelligence, Actionable Playbook, and Proven Planners.
"""

import json
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


def generate_gtm_pdf(dossier_data: Dict[str, Any], output_filename: str = None) -> str:
    """Generate professional PDF from GTM-Ready dossier data."""
    
    if not output_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        campus = dossier_data.get("campus_name", "Campus").replace(" ", "_")
        output_filename = f"GTM_Ready_Dossier_{campus}_{timestamp}.pdf"
    
    # Create PDF document
    doc = SimpleDocTemplate(output_filename, pagesize=letter, 
                          rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles for GTM report
    title_style = ParagraphStyle(
        'GTMTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    section_style = ParagraphStyle(
        'GTMSection',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkblue
    )
    
    subsection_style = ParagraphStyle(
        'GTMSubsection',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=12,
        textColor=colors.darkgreen
    )
    
    body_style = ParagraphStyle(
        'GTMBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    metric_style = ParagraphStyle(
        'GTMMetric',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20
    )
    
    # Build story
    story = []
    
    # Title page
    campus_name = dossier_data.get("campus_name", "University")
    story.append(Paragraph(f"GTM-Ready Campus Dossier", title_style))
    story.append(Paragraph(f"{campus_name}", title_style))
    story.append(Spacer(1, 0.5*inch))
    
    generation_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated: {generation_date}", body_style))
    story.append(PageBreak())
    
    dossier = dossier_data.get("dossier", {})
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", section_style))
    exec_summary = dossier.get("EXECUTIVE_SUMMARY", {})
    
    if exec_summary:
        # Tier classification
        tier = exec_summary.get("tier", "Unknown")
        story.append(Paragraph(f"<b>Classification:</b> {tier}", body_style))
        
        # Community potential score
        score = exec_summary.get("community_potential_score")
        if score:
            story.append(Paragraph(f"<b>Community Potential Score:</b> {score}/100", body_style))
        
        # Key insight
        key_insight = exec_summary.get("key_insight", "")
        if key_insight:
            story.append(Paragraph(f"<b>Key Strategic Insight:</b>", subsection_style))
            story.append(Paragraph(key_insight, body_style))
        
        # First outreach target
        target = exec_summary.get("first_outreach_target", "")
        if target:
            story.append(Paragraph(f"<b>Priority Target:</b> {target}", body_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Quantitative Scorecard
    story.append(Paragraph("Quantitative Scorecard", section_style))
    story.append(Paragraph("Verified metrics for data-driven decision making.", body_style))
    
    scorecard = dossier.get("Quantitative_Scorecard", {})
    if scorecard:
        # Create metrics table
        table_data = [['Metric', 'Value', 'Confidence', 'Source']]
        
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
            metric_data = scorecard.get(metric_key, {})
            if metric_data and "error" not in metric_data:
                # Extract value based on metric type
                if metric_key == 'housing':
                    value = f"{metric_data.get('percentInHousing', 'N/A')}%"
                elif metric_key == 'centricity':
                    value = f"{metric_data.get('campusCentricityScore', 'N/A')}/10"
                elif metric_key == 'ncaa':
                    value = metric_data.get('ncaaDivision', 'N/A')
                elif metric_key == 'greek':
                    value = f"{metric_data.get('percentGreekLife', 'N/A')}%"
                elif metric_key == 'ratio':
                    value = metric_data.get('studentFacultyRatio', 'N/A')
                elif metric_key == 'acceptance':
                    value = f"{metric_data.get('acceptanceRate', 'N/A')}%"
                elif metric_key == 'out_of_state':
                    value = f"{metric_data.get('percentOutOfState', 'N/A')}%"
                elif metric_key == 'endowment':
                    endow = metric_data.get('endowmentPerStudent', 'N/A')
                    if isinstance(endow, (int, float)):
                        value = f"${endow:,}"
                    else:
                        value = str(endow)
                elif metric_key == 'retention':
                    value = f"{metric_data.get('freshmanRetentionRate', 'N/A')}%"
                else:
                    value = "N/A"
                
                confidence = metric_data.get('confidence', 'N/A')
                source = str(metric_data.get('source', 'N/A'))[:30]
                
                table_data.append([label, value, confidence, source])
        
        metrics_table = Table(table_data, colWidths=[2*inch, 1*inch, 1*inch, 2.5*inch])
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
    
    story.append(PageBreak())
    
    # Key Community Clusters
    clusters = dossier.get("Key_Community_Clusters", [])
    if clusters:
        story.append(Paragraph("Key Community Clusters", section_style))
        for i, cluster in enumerate(clusters, 1):
            if isinstance(cluster, dict):
                name = cluster.get("name", f"Cluster {i}")
                description = cluster.get("description", "No description available")
                story.append(Paragraph(f"<b>{i}. {name}</b>", subsection_style))
                story.append(Paragraph(description, metric_style))
                story.append(Spacer(1, 0.15*inch))
            else:
                story.append(Paragraph(f"{i}. {cluster}", metric_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Influence Rankings
    rankings = dossier.get("Influence_Rankings", [])
    if rankings:
        story.append(Paragraph("Top 15 Most Influential Orgs & Individuals", section_style))
        for i, ranking in enumerate(rankings[:15], 1):
            if isinstance(ranking, dict):
                name = ranking.get("name", "Unknown")
                category = ranking.get("category", "Unknown")
                justification = ranking.get("justification", "No justification provided")
                story.append(Paragraph(f"<b>{i}. {name}</b> ({category})", subsection_style))
                story.append(Paragraph(justification, metric_style))
                story.append(Spacer(1, 0.1*inch))
        story.append(Spacer(1, 0.2*inch))
    
    # Social Heatmap Analysis
    heatmap_analysis = dossier.get("Social_Heatmap_Analysis", "")
    if heatmap_analysis:
        story.append(Paragraph("Social Heatmap Analysis", section_style))
        story.append(Paragraph(heatmap_analysis, metric_style))
        story.append(Spacer(1, 0.2*inch))
    
    story.append(PageBreak())
    
    # Actionable Contacts
    story.append(Paragraph("Actionable Contacts", section_style))
    contacts = dossier.get("Contact_Intelligence", {})
    
    if contacts:
        # Show verified contacts with emails
        verified_contacts = contacts.get("verified_contacts", [])
        if verified_contacts:
            story.append(Paragraph("Verified Student Contacts", subsection_style))
            for i, contact in enumerate(verified_contacts[:15], 1):
                if isinstance(contact, dict):
                    name = contact.get("name", "Unknown")
                    title = contact.get("title", "Student")
                    org = contact.get("organization", "")
                    email = contact.get("email", "No email")
                    
                    story.append(Paragraph(f"<b>{i}. {name}</b> - {title}", metric_style))
                    if org:
                        story.append(Paragraph(f"   Organization: {org}", metric_style))
                    story.append(Paragraph(f"   📧 {email}", metric_style))
                    story.append(Spacer(1, 0.1*inch))
            story.append(Spacer(1, 0.2*inch))
        
        # Show contact summary
        total_contacts = contacts.get("total_email_contacts", 0)
        if total_contacts:
            story.append(Paragraph(f"Total Email Contacts Found: {total_contacts}", subsection_style))
        
        # Proven Planners
        planners = contacts.get("proven_planners", [])
        if planners:
            story.append(Paragraph("Proven Event Planners", subsection_style))
            for planner in planners:
                if isinstance(planner, dict):
                    name = planner.get("planner_name", "Unknown")
                    email = planner.get("planner_email", "")
                    event = planner.get("event_organized", "")
                    org = planner.get("hosting_org", "")
                    
                    story.append(Paragraph(f"<b>{name}</b>", metric_style))
                    if event:
                        story.append(Paragraph(f"Event: {event}", metric_style))
                    if org:
                        story.append(Paragraph(f"Organization: {org}", metric_style))
                    if email:
                        story.append(Paragraph(f"Email: {email}", metric_style))
                    story.append(Spacer(1, 0.1*inch))
        
        # Priority Targets
        priorities = contacts.get("priority_targets", [])
        if priorities:
            story.append(Paragraph("Priority Targets", subsection_style))
            story.append(Paragraph("Recommended first contacts for outreach:", body_style))
            for i, target in enumerate(priorities, 1):
                story.append(Paragraph(f"{i}. {target}", metric_style))
    
    # Methodology
    story.append(PageBreak())
    story.append(Paragraph("Methodology", section_style))
    methodology_text = """
    This dossier was generated using the GTM-Ready Intelligence Engine, which combines:
    
    • Quantitative Analysis: 9 core metrics from verified sources
    • Community Intelligence: Reddit analysis and targeted web searches  
    • Contact Discovery: Strategic searches for student leaders and event planners
    • AI Synthesis: Advanced natural language processing for insights
    
    All data points are verified and sources are provided for transparency.
    """
    story.append(Paragraph(methodology_text, body_style))
    
    # Build PDF
    doc.build(story)
    
    return output_filename


def main():
    """CLI interface for PDF generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate GTM-Ready Dossier PDF")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", help="Output PDF file (optional)")
    
    args = parser.parse_args()
    
    # Load dossier data
    with open(args.input, "r") as f:
        dossier_data = json.load(f)
    
    # Generate PDF
    output_file = generate_gtm_pdf(dossier_data, args.output)
    print(f"✅ GTM-Ready PDF generated: {output_file}")


if __name__ == "__main__":
    main()
