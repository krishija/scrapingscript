#!/usr/bin/env python3
"""
Organization & Community Intelligence Processor
Generates comprehensive organization lists and community analysis.
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
from intelligence_sources import RedditSource

def load_api_keys():
    """Load API keys from environment."""
    load_dotenv('../.env')
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment")
    return gemini_key

def discover_organizations_and_intelligence(campus_name: str, gemini_key: str) -> Dict[str, Any]:
    """Discover organizations and community intelligence for a single university."""
    try:
        print(f"💎 Organizations: {campus_name}")
        start_time = time.time()
        
        # Initialize Gemini
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Get comprehensive organization list
        organizations = _find_comprehensive_organizations(campus_name, model)
        time.sleep(2.0)
        
        # Get community clusters analysis
        community_clusters = _analyze_community_clusters(campus_name, model)
        time.sleep(2.0)
        
        # Get Reddit intelligence (if available)
        reddit_intelligence = _get_reddit_intelligence(campus_name, gemini_key)
        
        elapsed = time.time() - start_time
        org_count = len(organizations.get('comprehensive_orgs', []))
        cluster_count = len(community_clusters.get('community_clusters', []))
        
        print(f"✅ {campus_name}: {org_count} orgs, {cluster_count} clusters ({elapsed:.1f}s)")
        
        return {
            "campus_name": campus_name,
            "status": "success",
            "organizations": organizations,
            "community_clusters": community_clusters,
            "reddit_intelligence": reddit_intelligence,
            "org_count": org_count,
            "cluster_count": cluster_count,
            "elapsed_time": elapsed
        }
        
    except Exception as e:
        print(f"❌ {campus_name}: {str(e)}")
        return {
            "campus_name": campus_name,
            "status": "failed",
            "error": str(e),
            "organizations": {},
            "community_clusters": {},
            "reddit_intelligence": {},
            "org_count": 0,
            "cluster_count": 0,
            "elapsed_time": 0
        }

def _find_comprehensive_organizations(campus_name: str, model) -> Dict[str, Any]:
    """Find comprehensive list of 30+ student organizations."""
    try:
        # Comprehensive searches for ALL types of orgs
        searches = [
            f'"{campus_name}" complete student organization directory list',
            f'"{campus_name}" student clubs list academic professional recreational',
            f'"{campus_name}" greek life fraternities sororities complete list',
            f'"{campus_name}" cultural ethnic international student organizations',
            f'"{campus_name}" sports clubs intramural recreation organizations'
        ]
        
        all_content = []
        for search_query in searches:
            result = tool_web_search(search_query, max_results=2)  # Reduced for rate limiting
            if result.get('content'):
                all_content.append(result['content'][:2500])
            time.sleep(2.0)  # Conservative rate limiting
        
        combined_content = "\n\n".join(all_content)
        
        # AI analysis for comprehensive org list
        analysis_prompt = f"""Extract a comprehensive list of student organizations from {campus_name}.

CONTENT: {combined_content[:12000]}

Extract ALL types of organizations mentioned:
- Academic/Professional clubs
- Greek life organizations  
- Cultural/Ethnic groups
- Sports/Recreation clubs
- Arts/Creative organizations
- Service/Volunteer groups
- Religious/Spiritual groups
- Honor societies
- Student government entities
- Special interest clubs

For each organization found, provide:
- name: Full official name
- category: Type (Academic/Greek/Cultural/Sports/Arts/Service/Religious/Government/Special)
- engagement_indicators: Evidence of activity (Instagram, events, news mentions)
- target_priority: high/medium/low (based on social influence potential)

Return JSON: {{"comprehensive_orgs": [{{"name": "...", "category": "...", "engagement_indicators": "...", "target_priority": "..."}}]}}

TARGET: Find as many organizations as possible. Be comprehensive."""

        response = model.generate_content(analysis_prompt)
        orgs_data = _parse_json_response(response.text)
        
        # Process comprehensive org list
        if isinstance(orgs_data, dict) and "comprehensive_orgs" in orgs_data:
            comprehensive_orgs = orgs_data["comprehensive_orgs"]
            
            return {
                "comprehensive_orgs": comprehensive_orgs,
                "total_found": len(comprehensive_orgs),
                "phantombuster_ready": True,
                "categories_breakdown": _analyze_org_categories(comprehensive_orgs)
            }
        
        return orgs_data
        
    except Exception as e:
        return {"error": str(e)}

def _analyze_community_clusters(campus_name: str, model) -> Dict[str, Any]:
    """Analyze community clusters and social dynamics."""
    try:
        # Strategic searches for community analysis
        searches = [
            f'"{campus_name}" student life culture social groups campus vibe',
            f'"{campus_name}" what are students like social scene campus culture'
        ]
        
        all_content = []
        for search_query in searches:
            result = tool_web_search(search_query, max_results=2)
            if result.get('content'):
                all_content.append(result['content'][:2500])
            time.sleep(1.5)
        
        combined_content = "\n\n".join(all_content)
        
        analysis_prompt = f"""Analyze the social community structure at {campus_name}.

CONTENT: {combined_content[:8000]}

Identify the main "tribes" or community clusters on campus. These are distinct social groups with different values, activities, and social dynamics.

For each cluster, provide:
- name: Descriptive name (e.g., "The Tech & Entrepreneurship Scene")
- description: What defines this group, their activities, values
- influence: high/medium/low (their impact on campus culture)
- size_estimate: large/medium/small (relative size on campus)

Return JSON: {{"community_clusters": [{{"name": "...", "description": "...", "influence": "...", "size_estimate": "..."}}]}}

TARGET: Find 3-5 main community clusters that capture the campus social landscape."""

        response = model.generate_content(analysis_prompt)
        return _parse_json_response(response.text)
        
    except Exception as e:
        return {"error": str(e)}

def _get_reddit_intelligence(campus_name: str, gemini_key: str) -> Dict[str, Any]:
    """Get Reddit intelligence if available."""
    try:
        reddit_source = RedditSource(gemini_key)
        
        # Guess subreddit name
        subreddit_name = _guess_subreddit_name(campus_name)
        if subreddit_name:
            return reddit_source.get_humint_report(subreddit_name)
        else:
            return {"error": "Could not determine subreddit name"}
            
    except Exception as e:
        return {"error": str(e)}

def _guess_subreddit_name(campus_name: str) -> str:
    """Guess likely subreddit name from campus name."""
    name_mapping = {
        "georgetown university": "georgetown",
        "university of michigan-ann arbor": "uofm",
        "tulane university of louisiana": "tulane",
        "auburn university": "auburn",
        "arizona state university": "asu",
        "howard university": "howard",
        "university of central florida": "ucf",
        "pepperdine university": "pepperdine",
        "syracuse university": "syracuse",
        "university of miami": "umiami"
    }
    
    campus_lower = campus_name.lower()
    for name, subreddit in name_mapping.items():
        if name in campus_lower:
            return subreddit
    
    return None

def _analyze_org_categories(orgs: List[Dict]) -> Dict[str, int]:
    """Analyze organization categories for insights."""
    categories = {}
    for org in orgs:
        category = org.get("category", "Unknown")
        categories[category] = categories.get(category, 0) + 1
    return categories

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

def main():
    """Main organization processing function."""
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
    
    print(f"💎 Organization & Intelligence Processing: {len(universities)} Universities")
    print("=" * 60)
    
    # Setup
    gemini_key = load_api_keys()
    start_time = time.time()
    results = []
    
    # Process sequentially to avoid rate limits
    for university in universities:
        try:
            result = discover_organizations_and_intelligence(university, gemini_key)
            results.append(result)
        except Exception as e:
            print(f"❌ {university} failed with exception: {e}")
            results.append({
                "campus_name": university,
                "status": "failed", 
                "error": str(e),
                "organizations": {},
                "community_clusters": {},
                "reddit_intelligence": {},
                "org_count": 0,
                "cluster_count": 0,
                "elapsed_time": 0
            })
    
    # Generate PDF
    pdf_path = f"../../generated_pdfs/Organization_Intelligence_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    generate_organization_pdf(results, pdf_path)
    
    # Save JSON data
    json_path = f"organization_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    total_time = time.time() - start_time
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len([r for r in results if r['status'] == 'failed'])
    total_orgs = sum(r['org_count'] for r in results if r['status'] == 'success')
    
    print("\n" + "=" * 60)
    print(f"💎 ORGANIZATION INTELLIGENCE COMPLETE")
    print(f"✅ Results: {successful} successful, {failed} failed")
    print(f"🏢 Total organizations found: {total_orgs}")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📄 PDF: {pdf_path}")
    print(f"💾 JSON: {json_path}")
    print("=" * 60)

def generate_organization_pdf(results: List[Dict], output_filename: str):
    """Generate PDF focused on organizations and community intelligence."""
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
    story.append(Paragraph("Organization & Community Intelligence Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"Universities Analyzed: {len([r for r in results if r['status'] == 'success'])}", styles['Normal']))
    story.append(Spacer(1, 0.5*inch))
    
    # Summary table
    story.append(Paragraph("Organization Summary", section_style))
    
    summary_data = [['University', 'Organizations', 'Community Clusters', 'PhantomBuster Ready']]
    
    for result in results:
        if result['status'] == 'success':
            campus_name = result['campus_name']
            org_count = str(result['org_count'])
            cluster_count = str(result['cluster_count'])
            pb_ready = "✅" if result['organizations'].get('phantombuster_ready') else "❌"
            
            summary_data.append([campus_name, org_count, cluster_count, pb_ready])
    
    summary_table = Table(summary_data, colWidths=[3*inch, 1.2*inch, 1.5*inch, 1.3*inch])
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
    
    # Detailed analysis for each university
    for result in results:
        if result['status'] == 'success':
            story.append(Paragraph(f"{result['campus_name']} - Organization Intelligence", section_style))
            
            # Community Clusters
            clusters = result['community_clusters'].get('community_clusters', [])
            if clusters:
                story.append(Paragraph("Community Clusters", styles['Heading3']))
                for i, cluster in enumerate(clusters, 1):
                    name = cluster.get('name', 'Unknown')
                    description = cluster.get('description', 'No description')
                    influence = cluster.get('influence', 'Unknown')
                    size = cluster.get('size_estimate', 'Unknown')
                    
                    story.append(Paragraph(f"<b>{i}. {name}</b> (Influence: {influence}, Size: {size})", styles['Normal']))
                    story.append(Paragraph(description, styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                
                story.append(Spacer(1, 0.2*inch))
            
            # Organizations for PhantomBuster
            orgs = result['organizations'].get('comprehensive_orgs', [])
            if orgs:
                story.append(Paragraph(f"Organizations Found ({len(orgs)})", styles['Heading3']))
                
                # Group by category
                categories = {}
                for org in orgs:
                    cat = org.get('category', 'Unknown')
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(org)
                
                for category, cat_orgs in categories.items():
                    story.append(Paragraph(f"<b>{category} Organizations:</b>", styles['Normal']))
                    for org in cat_orgs[:8]:  # Show top 8 per category
                        name = org.get('name', 'Unknown')
                        priority = org.get('target_priority', 'Unknown')
                        indicators = org.get('engagement_indicators', 'No indicators')
                        
                        story.append(Paragraph(f"• <b>{name}</b> (Priority: {priority})", styles['Normal']))
                        story.append(Paragraph(f"  Engagement: {indicators}", styles['Normal']))
                    
                    if len(cat_orgs) > 8:
                        story.append(Paragraph(f"  ... and {len(cat_orgs) - 8} more {category} organizations", styles['Normal']))
                    
                    story.append(Spacer(1, 0.1*inch))
            
            story.append(PageBreak())
    
    doc.build(story)
    print(f"💎 Organization PDF generated: {output_filename}")

if __name__ == "__main__":
    main()