#!/usr/bin/env python3
"""
PDF Report Generator for Campus Intelligence
Creates professional GTM intelligence reports in PDF format.
"""

import json
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie


class CampusIntelligenceReport:
    """Professional PDF report generator for campus intelligence data."""
    
    def __init__(self, output_filename: str):
        self.output_filename = output_filename
        self.doc = SimpleDocTemplate(output_filename, pagesize=letter)
        self.styles = getSampleStyleSheet()
        self.story = []
        
        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2E86C1')
        )
        
        self.section_style = ParagraphStyle(
            'CustomSection',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#E74C3C')
        )

    def add_title_page(self, campus_name: str, data: dict):
        """Add executive summary title page."""
        # Title
        title = f"Campus Intelligence Report<br/>{campus_name}"
        self.story.append(Paragraph(title, self.title_style))
        self.story.append(Spacer(1, 0.5*inch))
        
        # Executive summary box
        tier = data.get('strategic_assessment', {}).get('tier', 'Unknown')
        quality = data.get('data_quality', {}).get('quality_score', 0)
        diamonds = len(data.get('diamond_targets', []))
        contacts = data.get('contact_intelligence', {}).get('contacts_found', 0)
        
        summary_data = [
            ['GTM Assessment', tier],
            ['Data Quality', f"{quality:.0f}%"],
            ['Diamond Targets', str(diamonds)],
            ['Contacts Found', f"{contacts}/3"],
            ['Generated', datetime.now().strftime('%B %d, %Y')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(summary_table)
        self.story.append(PageBreak())

    def add_quantitative_scorecard(self, scorecard_data: dict):
        """Add quantitative metrics with visual chart."""
        self.story.append(Paragraph("Quantitative Scorecard", self.section_style))
        
        # Create table of metrics
        metrics_data = [['Metric', 'Value', 'Source', 'Confidence']]
        
        metric_labels = {
            'housing': 'Housing %',
            'centricity': 'Centricity Score',
            'ncaa': 'NCAA Division', 
            'greek': 'Greek Life %',
            'ratio': 'Student:Faculty',
            'acceptance': 'Acceptance Rate %'
        }
        
        for key, label in metric_labels.items():
            metric = scorecard_data.get(key, {})
            if isinstance(metric, dict):
                value = metric.get('percentInHousing') or metric.get('campusCentricityScore') or \
                       metric.get('ncaaDivision') or metric.get('percentGreekLife') or \
                       metric.get('studentFacultyRatio') or metric.get('acceptanceRate') or 'N/A'
                source = metric.get('source', 'Unknown')[:30]
                confidence = metric.get('confidence', 'Unknown')
                metrics_data.append([label, str(value), source, confidence])
        
        metrics_table = Table(metrics_data, colWidths=[1.5*inch, 1*inch, 2*inch, 1*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.story.append(metrics_table)
        self.story.append(Spacer(1, 0.3*inch))

    def add_diamond_targets(self, diamond_data: list):
        """Add diamond organizations section."""
        self.story.append(Paragraph("Diamond Target Organizations", self.section_style))
        
        for i, org in enumerate(diamond_data[:5], 1):  # Top 5
            name = org.get('name', 'Unknown')
            category = org.get('category', 'Unknown')
            story = org.get('story', 'No description available')
            signal = org.get('signal', 'No signal data')
            
            org_title = f"{i}. {name} ({category})"
            self.story.append(Paragraph(org_title, self.styles['Heading3']))
            
            self.story.append(Paragraph(f"<b>Story:</b> {story}", self.styles['Normal']))
            self.story.append(Paragraph(f"<b>Signal:</b> {signal}", self.styles['Normal']))
            self.story.append(Spacer(1, 0.2*inch))

    def add_contact_intelligence(self, contact_data: dict):
        """Add contact information section.""" 
        self.story.append(Paragraph("Contact Intelligence", self.section_style))
        
        contact_table_data = [['Organization Type', 'Name', 'Contact', 'Leader']]
        
        for contact_type, details in contact_data.items():
            if isinstance(details, dict):
                name = details.get('name', 'Unknown')
                contact = details.get('contact') or 'No email found'
                leader = details.get('editor') or details.get('president') or \
                        details.get('coordinator') or 'Unknown'
                
                contact_table_data.append([
                    contact_type.replace('_', ' ').title(),
                    name[:25],
                    contact[:30] if contact != 'No email found' else contact,
                    leader[:20] if leader != 'Unknown' else leader
                ])
        
        contact_table = Table(contact_table_data, colWidths=[1.3*inch, 1.7*inch, 1.7*inch, 1.3*inch])
        contact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.story.append(contact_table)
        self.story.append(Spacer(1, 0.3*inch))

    def add_event_opportunities(self, events_data: list):
        """Add upcoming events section."""
        self.story.append(Paragraph("Event Opportunities", self.section_style))
        
        # Filter for GTM opportunities only
        gtm_events = [e for e in events_data if e.get('homie_opportunity') not in ['No Opportunity', None]]
        
        if gtm_events:
            for event in gtm_events[:8]:  # Top 8 events
                name = event.get('event_name', 'Unknown Event')
                date = event.get('date', 'TBD')
                opportunity = event.get('homie_opportunity', 'Unknown')
                
                event_text = f"<b>{name}</b> ({date}) - <i>{opportunity}</i>"
                self.story.append(Paragraph(event_text, self.styles['Normal']))
                self.story.append(Spacer(1, 0.1*inch))
        else:
            self.story.append(Paragraph("No GTM event opportunities identified.", self.styles['Normal']))

    def add_strategic_assessment(self, assessment_data: dict):
        """Add final strategic assessment."""
        self.story.append(PageBreak())
        self.story.append(Paragraph("Strategic Assessment", self.section_style))
        
        tier = assessment_data.get('tier', 'Unknown')
        readiness = assessment_data.get('gtm_readiness', False)
        recommendation = assessment_data.get('first_contact_recommendation', 'None')
        notes = assessment_data.get('notes', 'No additional notes.')
        
        assessment_content = f"""
        <b>GTM Tier:</b> {tier}<br/>
        <b>Ready for Launch:</b> {'Yes' if readiness else 'No'}<br/>
        <b>First Contact:</b> {recommendation}<br/><br/>
        <b>Strategic Notes:</b><br/>
        {notes}
        """
        
        self.story.append(Paragraph(assessment_content, self.styles['Normal']))

    def generate_report(self, intelligence_data: dict):
        """Generate the complete PDF report."""
        campus_name = intelligence_data.get('campus_name', 'Unknown Campus')
        
        # Add all sections
        self.add_title_page(campus_name, intelligence_data)
        self.add_quantitative_scorecard(intelligence_data.get('growth_correlates_scorecard', {}))
        self.add_diamond_targets(intelligence_data.get('diamond_targets', []))
        self.add_contact_intelligence(intelligence_data.get('universal_inroads', {}))
        self.add_event_opportunities(intelligence_data.get('event_opportunities', []))
        self.add_strategic_assessment(intelligence_data.get('strategic_assessment', {}))
        
        # Build PDF
        self.doc.build(self.story)
        print(f"📄 PDF report generated: {self.output_filename}")


def generate_pdf_report(intelligence_data: dict, output_filename: str = None):
    """Helper function to generate PDF from intelligence data."""
    if not output_filename:
        campus_name = intelligence_data.get('campus_name', 'campus').replace(' ', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_filename = f"{campus_name}_intelligence_{timestamp}.pdf"
    
    report = CampusIntelligenceReport(output_filename)
    report.generate_report(intelligence_data)
    return output_filename


if __name__ == "__main__":
    # Example usage
    with open('example_intelligence.json', 'r') as f:
        data = json.load(f)
    generate_pdf_report(data)
