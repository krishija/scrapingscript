"""
PDF Reporting for Gatekeeper Recon Script
"""

from datetime import datetime
from typing import List, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors


def generate_pdf_report(university_name: str,
                        gatekeepers: List[Dict],
                        wom_contacts: List[Dict],
                        clinics: List[Dict],
                        output_filename: str):
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.darkblue, alignment=1
    )
    section_style = ParagraphStyle(
        'CustomSection', parent=styles['Heading2'], fontSize=16, spaceAfter=10, textColor=colors.darkblue
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'], fontSize=10, textColor=colors.darkblue
    )

    story.append(Paragraph(f"Gatekeeper Intelligence Report", title_style))
    story.append(Paragraph(f"University: {university_name}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 0.4*inch))

    # Tier 1 University Gatekeepers
    story.append(Paragraph("Tier 1 University Gatekeepers", section_style))
    g_fields = ['Name', 'Title', 'Email', 'Seniority']
    g_data = [g_fields]
    for c in gatekeepers:
        seniority = c.get('seniority_level', 'N/A')
        leader = '⭐️' if c.get('is_thought_leader') else ''
        name_with_leader = f"{c.get('name', '')} {leader}".strip()
        g_data.append([
            name_with_leader, c.get('title', ''), c.get('email', 'No email'), seniority
        ])
    g_table = Table(g_data, colWidths=[2.0*inch, 2.0*inch, 1.8*inch, 1.0*inch])
    g_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(g_table)
    story.append(PageBreak())

    # WoM Influence Evidence
    story.append(Paragraph("WoM Influence Evidence", section_style))
    has_leaders = False
    for c in wom_contacts:
        if c.get('is_thought_leader'):
            has_leaders = True
            evidence = c.get('wom_evidence', 'No evidence provided')
            story.append(Paragraph(f"<b>{c.get('name','Unknown')}</b> — {c.get('title','')} ⭐️", styles['Heading3']))
            story.append(Paragraph(f"Evidence: {evidence}", styles['Normal']))
            if c.get('bio_url'):
                story.append(Paragraph(f"Bio: {c.get('bio_url')}", subtitle_style))
            story.append(Spacer(1, 0.2*inch))
    
    if not has_leaders:
        story.append(Paragraph("No thought leaders identified with specific evidence.", styles['Normal']))
    
    story.append(PageBreak())

    # Local Ecosystem "Shadow System"
    story.append(Paragraph("Local Ecosystem — Shadow System", section_style))
    if not clinics:
        story.append(Paragraph("No local ecosystem clinics found.", styles['Normal']))
    else:
        # Header row with all fields
        c_fields = ['Clinic Name', 'Practitioners', 'Specialization']
        c_data = [c_fields]
        for cl in clinics:
            clinic_name = cl.get('clinic_name', 'Unknown')
            practitioners = cl.get('key_practitioners', 'N/A')
            specialization = cl.get('specialization', 'N/A')
            c_data.append([
                clinic_name[:35],  # Truncate long names
                practitioners[:40] if practitioners else 'N/A',
                specialization[:40] if specialization else 'N/A'
            ])
        
        c_table = Table(c_data, colWidths=[2.2*inch, 2.2*inch, 2.0*inch])
        c_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(c_table)
        
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Clinic Details", subtitle_style))
        for cl in clinics:
            story.append(Paragraph(f"<b>{cl.get('clinic_name', 'Unknown')}</b>", styles['Normal']))
            if cl.get('key_practitioners'):
                story.append(Paragraph(f"Practitioners: {cl.get('key_practitioners')}", styles['Normal']))
            if cl.get('athletic_affiliations'):
                story.append(Paragraph(f"Affiliations: {cl.get('athletic_affiliations')}", styles['Normal']))
            if cl.get('website'):
                story.append(Paragraph(f"Website: {cl.get('website')}", styles['Normal']))
            if cl.get('location'):
                story.append(Paragraph(f"Location: {cl.get('location')}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))

    doc.build(story)
    print(f"📄 Gatekeeper PDF generated: {output_filename}")


