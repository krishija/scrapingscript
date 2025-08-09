#!/usr/bin/env python3
"""
Contact Discovery Processor
Generates contact intelligence for multiple universities in parallel.
"""

import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
import google.generativeai as genai

# Add parent directory for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from tools import tool_web_search

def load_api_keys():
    """Load API keys from environment."""
    load_dotenv('../.env')
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment")
    return gemini_key

def _get_campus_domain(campus_name: str) -> str:
    """Get likely campus domain for targeted searches."""
    domain_mapping = {
        "georgetown university": "georgetown.edu",
        "university of michigan-ann arbor": "umich.edu",
        "tulane university of louisiana": "tulane.edu",
        "auburn university": "auburn.edu",
        "arizona state university": "asu.edu",
        "howard university": "howard.edu",
        "university of central florida": "ucf.edu",
        "pepperdine university": "pepperdine.edu",
        "syracuse university": "syracuse.edu",
        "university of miami": "miami.edu"
    }
    
    campus_lower = campus_name.lower()
    for name, domain in domain_mapping.items():
        if name in campus_lower:
            return domain
    
    # Fallback: create domain
    words = campus_name.lower().replace("university of", "").replace("the ", "").split()
    if words:
        return f"{words[-1]}.edu"
    return "university.edu"

def discover_contacts(campus_name: str, gemini_key: str) -> Dict[str, Any]:
    """Discover contacts for a single university using 4-strategy approach."""
    try:
        print(f"👥 Contacts: {campus_name}")
        start_time = time.time()
        
        # Initialize Gemini
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Strategy 1: Leadership contacts
        leadership_contacts = _strategy_leadership_contacts(campus_name, model)
        time.sleep(2.0)  # Rate limiting between strategies
        
        # Strategy 2: Directory mining
        directory_contacts = _strategy_directory_mining(campus_name, model)
        time.sleep(2.0)
        
        # Strategy 3: Event organizers
        event_contacts = _strategy_event_organizers(campus_name, model)
        time.sleep(2.0)
        
        # Strategy 4: Social leaders
        social_contacts = _strategy_social_leaders(campus_name, model)
        
        # Combine and deduplicate
        all_contacts = []
        strategies_used = []
        
        if leadership_contacts.get('contacts'):
            all_contacts.extend(leadership_contacts['contacts'])
            strategies_used.append("leadership")
        
        if directory_contacts.get('contacts'):
            all_contacts.extend(directory_contacts['contacts'])
            strategies_used.append("directories")
            
        if event_contacts.get('contacts'):
            all_contacts.extend(event_contacts['contacts'])
            strategies_used.append("events")
            
        if social_contacts.get('contacts'):
            all_contacts.extend(social_contacts['contacts'])
            strategies_used.append("social")
        
        # Deduplicate by email
        seen_emails = set()
        unique_contacts = []
        
        for contact in all_contacts:
            email = contact.get("email", "").lower().strip()
            if email and "@" in email and email not in seen_emails:
                seen_emails.add(email)
                unique_contacts.append(contact)
        
        # Prioritize by position importance
        unique_contacts.sort(key=lambda c: _priority_score(c), reverse=True)
        
        elapsed = time.time() - start_time
        contact_count = len(unique_contacts)
        
        print(f"✅ {campus_name}: {contact_count} email contacts ({elapsed:.1f}s)")
        
        return {
            "campus_name": campus_name,
            "status": "success",
            "contacts": unique_contacts,
            "contact_count": contact_count,
            "strategies_used": strategies_used,
            "elapsed_time": elapsed
        }
        
    except Exception as e:
        print(f"❌ {campus_name}: {str(e)}")
        return {
            "campus_name": campus_name,
            "status": "failed",
            "error": str(e),
            "contacts": [],
            "contact_count": 0,
            "strategies_used": [],
            "elapsed_time": 0
        }

def _strategy_leadership_contacts(campus_name: str, model) -> Dict[str, Any]:
    """Strategy 1: Target key leadership positions."""
    try:
        leadership_searches = [
            f'"{campus_name}" student government president vice president email contact',
            f'"{campus_name}" student newspaper editor in chief email',
            f'"{campus_name}" residence hall association president email'
        ]
        
        all_content = []
        for search in leadership_searches:
            result = tool_web_search(search, max_results=2)
            if result.get('content'):
                all_content.append(result['content'][:2000])
            time.sleep(1.0)
        
        combined_content = "\n\n".join(all_content)
        
        extraction_prompt = f"""Extract student leader contact information from {campus_name}.

CONTENT: {combined_content[:6000]}

Find contacts for key positions:
- Student Government (President, VP, Secretary, Treasurer)
- Student Newspaper (Editor-in-Chief, Managing Editor)  
- Residence Life (RHA President, Programming Director)

For each contact found, provide:
- name (full name)
- title (specific position)
- organization (which group they lead)
- email (must include @ symbol)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "..."}}]}}"""

        response = model.generate_content(extraction_prompt)
        return _parse_json_response(response.text)
        
    except Exception as e:
        return {"error": str(e)}

def _strategy_directory_mining(campus_name: str, model) -> Dict[str, Any]:
    """Strategy 2: Mine student directories and organization listings."""
    try:
        directory_searches = [
            f'"{campus_name}" student organization directory officers contact',
            f'site:{_get_campus_domain(campus_name)} student directory'
        ]
        
        all_content = []
        for search in directory_searches:
            result = tool_web_search(search, max_results=2)
            if result.get('content'):
                all_content.append(result['content'][:2500])
            time.sleep(1.0)
        
        combined_content = "\n\n".join(all_content)
        
        extraction_prompt = f"""Extract student contacts from directory listings at {campus_name}.

CONTENT: {combined_content[:7000]}

Look for:
- Student organization officers with email addresses
- Student staff members with contact info
- Any directory listings with student emails

For each contact, provide:
- name
- title (position/role)
- organization (club/group name)
- email (must contain @)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "..."}}]}}"""

        response = model.generate_content(extraction_prompt)
        return _parse_json_response(response.text)
        
    except Exception as e:
        return {"error": str(e)}

def _strategy_event_organizers(campus_name: str, model) -> Dict[str, Any]:
    """Strategy 3: Find students who organize events."""
    try:
        event_searches = [
            f'"{campus_name}" student events 2024 organizer contact coordinator',
            f'"{campus_name}" campus programming board event coordinator email'
        ]
        
        all_content = []
        for search in event_searches:
            result = tool_web_search(search, max_results=2)
            if result.get('content'):
                all_content.append(result['content'][:2000])
            time.sleep(1.0)
        
        combined_content = "\n\n".join(all_content)
        
        extraction_prompt = f"""Find student event organizers at {campus_name}.

CONTENT: {combined_content[:6000]}

Look for students who:
- Organize campus events or programming
- Coordinate activities or social events
- Work in student union programming

For each organizer found, provide:
- name
- title (role in event planning)
- organization (group they organize for)
- email (contact information)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "..."}}]}}"""

        response = model.generate_content(extraction_prompt)
        return _parse_json_response(response.text)
        
    except Exception as e:
        return {"error": str(e)}

def _strategy_social_leaders(campus_name: str, model) -> Dict[str, Any]:
    """Strategy 4: Find social influencers and community leaders."""
    try:
        social_searches = [
            f'"{campus_name}" campus tour guide coordinator email contact',
            f'"{campus_name}" orientation leader student coordinator email'
        ]
        
        all_content = []
        for search in social_searches:
            result = tool_web_search(search, max_results=2)
            if result.get('content'):
                all_content.append(result['content'][:2000])
            time.sleep(1.0)
        
        combined_content = "\n\n".join(all_content)
        
        extraction_prompt = f"""Find social leaders at {campus_name}.

CONTENT: {combined_content[:6000]}

Look for students who:
- Lead campus tours or orientation
- Coordinate peer programs
- Lead outreach or ambassador programs

For each leader found, provide:
- name
- title (leadership role)
- organization (program they're part of)
- email (contact information)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "..."}}]}}"""

        response = model.generate_content(extraction_prompt)
        return _parse_json_response(response.text)
        
    except Exception as e:
        return {"error": str(e)}

def _parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON response from Gemini."""
    try:
        return json.loads(text)
    except:
        # Try to extract JSON from fenced code blocks
        if "```json" in text:
            try:
                start = text.find("```json") + 7
                end = text.find("```", start)
                json_text = text[start:end].strip()
                return json.loads(json_text)
            except:
                pass
        
        # Try to find JSON-like structure
        if "{" in text and "}" in text:
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_text = text[start:end]
                return json.loads(json_text)
            except:
                pass
        
        return {"raw_response": text[:2000]}

def _priority_score(contact: Dict) -> int:
    """Calculate priority score for contact ranking."""
    title = contact.get("title", "").lower()
    org = contact.get("organization", "").lower()
    
    score = 0
    
    # High-priority positions
    if any(keyword in title for keyword in ["president", "editor-in-chief", "director"]):
        score += 10
    elif any(keyword in title for keyword in ["vice president", "vp", "secretary", "treasurer"]):
        score += 8
    elif any(keyword in title for keyword in ["coordinator", "manager", "chair"]):
        score += 6
    else:
        score += 3
    
    # High-priority organizations
    if any(keyword in org for keyword in ["student government", "newspaper", "activities board"]):
        score += 5
    elif any(keyword in org for keyword in ["residence", "hall", "programming"]):
        score += 3
    
    return score

def generate_contact_pdf(results: List[Dict], output_filename: str):
    """Generate PDF focused on contact intelligence."""
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
    story.append(Paragraph("Contact Intelligence Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"Universities Analyzed: {len([r for r in results if r['status'] == 'success'])}", styles['Normal']))
    story.append(Spacer(1, 0.5*inch))
    
    # Summary table
    story.append(Paragraph("Contact Summary", section_style))
    
    summary_data = [['University', 'Email Contacts', 'Strategies Used', 'Top Contact']]
    
    for result in results:
        if result['status'] == 'success':
            campus_name = result['campus_name']
            contact_count = str(result['contact_count'])
            strategies = ", ".join(result['strategies_used'])
            
            # Get top contact
            contacts = result['contacts']
            top_contact = "N/A"
            if contacts:
                top = contacts[0]
                top_contact = f"{top.get('name', 'Unknown')} ({top.get('title', 'Unknown')})"
            
            summary_data.append([campus_name, contact_count, strategies, top_contact])
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 1*inch, 2*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(PageBreak())
    
    # Detailed contacts for each university
    for result in results:
        if result['status'] == 'success':
            story.append(Paragraph(f"{result['campus_name']} - Contact Details", section_style))
            
            contacts = result['contacts']
            if contacts:
                for i, contact in enumerate(contacts[:15], 1):  # Show top 15 contacts
                    name = contact.get('name', 'Unknown')
                    title = contact.get('title', 'Unknown')
                    org = contact.get('organization', 'Unknown')
                    email = contact.get('email', 'No email')
                    
                    story.append(Paragraph(f"<b>{i}. {name}</b> - {title}", styles['Normal']))
                    story.append(Paragraph(f"   Organization: {org}", styles['Normal']))
                    story.append(Paragraph(f"   📧 {email}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                if len(contacts) > 15:
                    story.append(Paragraph(f"... and {len(contacts) - 15} more contacts", styles['Normal']))
            else:
                story.append(Paragraph("No contacts found", styles['Normal']))
            
            story.append(Spacer(1, 0.3*inch))
    
    doc.build(story)
    print(f"👥 Contact PDF generated: {output_filename}")

def main():
    """Main contact processing function."""
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
    
    print(f"👥 Contact Discovery Processing: {len(universities)} Universities")
    print("=" * 60)
    
    # Setup
    gemini_key = load_api_keys()
    start_time = time.time()
    results = []
    
    # Process in parallel (with conservative rate limiting)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(discover_contacts, university, gemini_key): university 
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
                    "contacts": [],
                    "contact_count": 0,
                    "strategies_used": [],
                    "elapsed_time": 0
                })
    
    # Generate PDF
    pdf_path = f"../../generated_pdfs/Contact_Intelligence_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    generate_contact_pdf(results, pdf_path)
    
    # Save JSON data
    json_path = f"contact_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    total_time = time.time() - start_time
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len([r for r in results if r['status'] == 'failed'])
    total_contacts = sum(r['contact_count'] for r in results if r['status'] == 'success')
    
    print("\n" + "=" * 60)
    print(f"👥 CONTACT DISCOVERY COMPLETE")
    print(f"✅ Results: {successful} successful, {failed} failed")
    print(f"📧 Total contacts found: {total_contacts}")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📄 PDF: {pdf_path}")
    print(f"💾 JSON: {json_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
