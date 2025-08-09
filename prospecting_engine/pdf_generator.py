"""
PDF Report Generator for Prospecting Engine
Creates a professional report with rankings, metrics, and contact information.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import json


def generate_prospecting_pdf(report_data: dict) -> str:
    """Generates a comprehensive PDF report from the prospecting engine results."""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"University_Prospecting_Report_{timestamp}.pdf"
    
    doc = SimpleDocTemplate(filename, pagesize=letter, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch,
                          topMargin=1*inch, bottomMargin=1*inch)
    
    styles = getSampleStyleSheet()
    
    # Custom styles (avoid conflicts with existing styles)
    styles.add(ParagraphStyle(name='TitleCentered', fontSize=24, leading=28, alignment=1, 
                             spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='ReportHeading1', fontSize=16, leading=20, spaceBefore=20, 
                             spaceAfter=12, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='ReportHeading2', fontSize=14, leading=18, spaceBefore=15, 
                             spaceAfter=8, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='ReportBodyText', fontSize=10, leading=13, spaceAfter=6))
    styles.add(ParagraphStyle(name='ReportSmallText', fontSize=8, leading=10, spaceAfter=4, 
                             textColor=colors.gray))
    styles.add(ParagraphStyle(name='ContactText', fontSize=9, leading=11, spaceAfter=3))
    
    story = []
    
    # Title Page
    story.append(Paragraph("University Prospecting Report", styles['TitleCentered']))
    story.append(Paragraph("Community-Focused Growth Analysis", styles['TitleCentered']))
    story.append(Spacer(1, 0.5*inch))
    
    # Executive Summary
    summary = report_data.get("prospecting_summary", {})
    story.append(Paragraph("Executive Summary", styles['ReportHeading1']))
    story.append(Paragraph(f"Generated: {summary.get('generated_at', 'N/A')}", styles['ReportSmallText']))
    story.append(Paragraph(f"Universities Analyzed: {summary.get('total_universities_analyzed', 0)}", styles['ReportBodyText']))
    story.append(Paragraph(f"Successful Scorecards: {summary.get('successful_scorecards', 0)}", styles['ReportBodyText']))
    story.append(Paragraph(f"Top Prospects Sourced: {summary.get('top_prospects_sourced', 0)}", styles['ReportBodyText']))
    story.append(Paragraph(f"Student Contacts Found: {summary.get('total_student_contacts_found', 0)}", styles['ReportBodyText']))
    story.append(Spacer(1, 0.2*inch))
    
    # Key Insights
    insights = report_data.get("key_insights", {})
    story.append(Paragraph("Key Insights", styles['ReportHeading2']))
    story.append(Paragraph(f"<b>Highest Potential Campus:</b> {insights.get('highest_potential', 'N/A')}", styles['ReportBodyText']))
    story.append(Paragraph(f"<b>Contact Success Rate:</b> {insights.get('contact_success_rate', 'N/A')}", styles['ReportBodyText']))
    
    hidden_gems = insights.get('hidden_gems', [])
    if hidden_gems:
        gems_text = ", ".join(hidden_gems)
        story.append(Paragraph(f"<b>Hidden Gems:</b> {gems_text}", styles['ReportBodyText']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Strategic Rankings
    ranking_data = report_data.get("strategic_ranking", {})
    ranked_universities = ranking_data.get("ranked_universities", [])
    
    if ranked_universities:
        story.append(Paragraph("Strategic University Rankings", styles['ReportHeading1']))
        story.append(Paragraph("Universities ranked by community potential based on housing density, campus centricity, social infrastructure, and market opportunity.", styles['ReportBodyText']))
        story.append(Spacer(1, 0.1*inch))
        
        # Create rankings table
        ranking_table_data = [['Rank', 'University', 'Score', 'Key Strengths']]
        
        for uni in ranked_universities[:15]:  # Show top 15
            rank = uni.get('rank', 'N/A')
            name = uni.get('university', 'N/A')
            score = uni.get('community_potential_score', 'N/A')
            strengths = ', '.join(uni.get('key_strengths', [])) if uni.get('key_strengths') else 'N/A'
            
            ranking_table_data.append([
                str(rank),
                name[:35] + "..." if len(name) > 35 else name,
                str(score),
                strengths[:40] + "..." if len(strengths) > 40 else strengths
            ])
        
        ranking_table = Table(ranking_table_data, colWidths=[0.5*inch, 2.5*inch, 0.7*inch, 2.8*inch])
        ranking_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(ranking_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Complete University Scorecards
    story.append(PageBreak())
    story.append(Paragraph("Complete University Scorecards", styles['ReportHeading1']))
    story.append(Paragraph("Detailed quantitative analysis for all universities with collected data.", styles['ReportBodyText']))
    story.append(Spacer(1, 0.1*inch))
    
    # Get all universities with data
    detailed_scorecards = report_data.get("detailed_scorecards", [])
    universities_with_data = [u for u in detailed_scorecards 
                             if u.get("scorecard", {}).get("data_quality", {}).get("quality_score", 0) > 0]
    
    # Sort by quality score (highest first)
    universities_with_data.sort(key=lambda x: x.get("scorecard", {}).get("data_quality", {}).get("quality_score", 0), reverse=True)
    
    for uni_data in universities_with_data:
        university = uni_data.get("university", "Unknown")
        scorecard = uni_data.get("scorecard", {}).get("prospect_scorecard", {})
        quality = uni_data.get("scorecard", {}).get("data_quality", {})
        
        story.append(Paragraph(f"🎯 {university}", styles['ReportHeading2']))
        story.append(Paragraph(f"Data Quality: {quality.get('quality_score', 0):.1f}% ({quality.get('valid_metrics', 0)}/9 metrics)", styles['ReportBodyText']))
        
        # Create detailed metrics table for this university
        metrics_data = [['Metric', 'Value', 'Confidence', 'Source']]
        
        # Define metric order and labels
        metric_mapping = {
            'housing': ('Housing %', 'percentInHousing'),
            'centricity': ('Campus Centricity', 'campusCentricityScore'), 
            'ncaa': ('NCAA Division', 'ncaaDivision'),
            'greek': ('Greek Life %', 'percentGreekLife'),
            'ratio': ('Student:Faculty Ratio', 'studentFacultyRatio'),
            'acceptance': ('Acceptance Rate %', 'acceptanceRate'),
            'out_of_state': ('Out-of-State %', 'percentOutOfState'),
            'endowment': ('Endowment/Student', 'endowmentPerStudent'),
            'retention': ('Freshman Retention %', 'freshmanRetentionRate')
        }
        
        for metric_key, (label, value_key) in metric_mapping.items():
            metric_data = scorecard.get(metric_key, {})
            if metric_data and "error" not in metric_data:
                value = metric_data.get(value_key, metric_data.get('value', 'N/A'))
                confidence = metric_data.get('confidence', 'N/A')
                source = metric_data.get('source', 'N/A')
                
                # Format values nicely
                if isinstance(value, (int, float)) and metric_key in ['housing', 'greek', 'acceptance', 'out_of_state', 'retention']:
                    value = f"{value}%"
                elif isinstance(value, (int, float)) and metric_key == 'endowment':
                    value = f"${value:,}" if value < 1000000 else f"${value/1000000:.1f}M"
                
                metrics_data.append([label, str(value), confidence, source[:30] + "..." if len(str(source)) > 30 else str(source)])
            else:
                metrics_data.append([label, "Not Available", "N/A", "N/A"])
        
        # Create table for this university
        uni_table = Table(metrics_data, colWidths=[1.8*inch, 1.2*inch, 0.8*inch, 2.7*inch])
        uni_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(uni_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Top 10 Detailed Analysis
    top_10 = report_data.get("top_10_prospects", [])
    if top_10:
        story.append(Paragraph("Top 10 Prospects - Detailed Analysis", styles['ReportHeading1']))
        
        for i, uni in enumerate(top_10, 1):
            story.append(Paragraph(f"{i}. {uni.get('university', 'N/A')}", styles['ReportHeading2']))
            story.append(Paragraph(f"Community Score: {uni.get('community_potential_score', 'N/A')}/100", styles['ReportBodyText']))
            
            strengths = uni.get('key_strengths', [])
            if strengths:
                story.append(Paragraph(f"Strengths: {', '.join(strengths)}", styles['ReportBodyText']))
            
            reasoning = uni.get('reasoning', '')
            if reasoning:
                story.append(Paragraph(f"Analysis: {reasoning}", styles['ReportBodyText']))
            
            story.append(Spacer(1, 0.15*inch))
        
        story.append(PageBreak())
    
    # Student Contacts Section
    contacts_data = report_data.get("social_leader_contacts", {})
    if contacts_data:
        story.append(Paragraph("Student Contact Information", styles['ReportHeading1']))
        story.append(Paragraph("Direct contacts for outreach at top-ranked universities.", styles['ReportBodyText']))
        story.append(Spacer(1, 0.2*inch))
        
        for university, contact_info in contacts_data.items():
            story.append(Paragraph(f"🎯 {university}", styles['ReportHeading2']))
            
            # Handle new nested structure: {student_contacts: {student_contacts: [...], event_organizers: {...}}}
            if isinstance(contact_info, dict) and "student_contacts" in contact_info:
                student_data = contact_info.get("student_contacts", {})
                if isinstance(student_data, dict):
                    contacts = student_data.get("student_contacts", [])
                else:
                    contacts = student_data if isinstance(student_data, list) else []
                
                # Also get event organizers if available
                event_data = contact_info.get("event_organizers", {})
                event_organizers = []
                if isinstance(event_data, dict) and "event_organizers" in event_data:
                    event_organizers = event_data.get("event_organizers", [])
            else:
                # Legacy format
                contacts = contact_info.get("student_contacts", contact_info.get("social_leaders", []))
                event_organizers = []
            
            # Show event organizers first (high-agency targets)
            if event_organizers:
                story.append(Paragraph("🎪 Recent Event Organizers", styles['ReportHeading3']))
                for j, organizer in enumerate(event_organizers, 1):
                    name = organizer.get("name", "Unknown")
                    role = organizer.get("role", "N/A")
                    org = organizer.get("organization", "N/A")
                    event = organizer.get("recent_event", "N/A")
                    email = organizer.get("email", "No email available")
                    
                    story.append(Paragraph(f"<b>{j}. {name}</b> (Event Organizer)", styles['ContactText']))
                    story.append(Paragraph(f"   Role: {role}", styles['ContactText']))
                    story.append(Paragraph(f"   Organization: {org}", styles['ContactText']))
                    story.append(Paragraph(f"   Recent Event: {event}", styles['ContactText']))
                    
                    if "@" in email:
                        story.append(Paragraph(f"   📧 Email: <b>{email}</b>", styles['ContactText']))
        else:
                        story.append(Paragraph(f"   📧 Email: {email}", styles['ContactText']))
                    
                    story.append(Spacer(1, 0.08*inch))
                
                story.append(Spacer(1, 0.1*inch))
            
            # Show regular student contacts
            if contacts:
                if event_organizers:
                    story.append(Paragraph("📧 Student Organization Contacts", styles['ReportHeading3']))
                
                for j, contact in enumerate(contacts, 1):
                    name = contact.get("name", "Unknown")
                    title = contact.get("title", "N/A")
                    org = contact.get("organization", "N/A")
                    email = contact.get("email", "No email available")
                    
                    story.append(Paragraph(f"<b>{j}. {name}</b>", styles['ContactText']))
                    story.append(Paragraph(f"   Title: {title}", styles['ContactText']))
                    story.append(Paragraph(f"   Organization: {org}", styles['ContactText']))
                    
                    if "@" in email:
                        story.append(Paragraph(f"   📧 Email: <b>{email}</b>", styles['ContactText']))
                    else:
                        story.append(Paragraph(f"   📧 Email: {email}", styles['ContactText']))
                    
                    story.append(Spacer(1, 0.08*inch))
            else:
                story.append(Paragraph("No student contacts found.", styles['ContactText']))
            
            story.append(Spacer(1, 0.2*inch))
    
    # Methodology
    story.append(PageBreak())
    story.append(Paragraph("Methodology", styles['ReportHeading1']))
    methodology = report_data.get("methodology", {})
    
    story.append(Paragraph("<b>Phase 1:</b> Quantitative Prospect Scoring", styles['ReportBodyText']))
    story.append(Paragraph("Systematic extraction of 9 key growth metrics including housing percentage, campus centricity, Greek life participation, retention rates, and market indicators.", styles['ReportBodyText']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Phase 2:</b> AI-Powered Strategic Ranking", styles['ReportBodyText']))
    story.append(Paragraph("Machine learning analysis to rank universities by community potential, weighting factors like housing density, social infrastructure, and market opportunity.", styles['ReportBodyText']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Phase 3:</b> Targeted Contact Sourcing", styles['ReportBodyText']))
    story.append(Paragraph("Automated discovery and extraction of student leader contact information from university directories, student government pages, and organizational rosters.", styles['ReportBodyText']))
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Paragraph(f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['ReportSmallText']))
    
    # Build PDF
    doc.build(story)
    return filename


def add_pdf_to_main():
    """Add PDF generation capability to main.py"""
    return '''
# Add this import at the top of main.py
from pdf_generator import generate_prospecting_pdf

# Add this in the main function after saving the JSON report:
        
        # Generate PDF report
        try:
            pdf_filename = generate_prospecting_pdf(final_report)
            print(f"📄 PDF report generated: {pdf_filename}")
        except Exception as e:
            print(f"⚠️ PDF generation failed: {e}")
'''