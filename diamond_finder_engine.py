#!/usr/bin/env python3
"""
Diamond Finder Engine - "The Art"
Finds the "Berkeley Cheese Clubs" and Universal Inroads for each campus.
"""

import os
import time
import json
from typing import Dict, List
from dotenv import load_dotenv

import google.generativeai as genai
from tools import tool_web_search, tool_crawl_for_contacts


# Diamond finding prompts
DIAMOND_FINDER_PROMPT = """You are a journalist for VICE covering college subcultures. Your job is to find the most interesting, authentic, and high-energy student communities.

Analyze the following articles, blog posts, and Reddit threads about {campus_name}. 

Identify up to 10 'diamond in the rough' organizations. These are NOT generic pre-professional clubs. They are the quirky, passionate, and active groups that define the soul of the campus.

For each, provide:
- name: Exact organization name
- category: Type of organization  
- story: One-sentence story that makes it compelling for a community-focused startup
- signal: What evidence shows they're active/passionate

Search Results:
{search_data}

Return ONLY valid JSON:
{{
  "diamond_orgs": [
    {{"name": "Berkeley Cheese Club", "category": "Food/Social", "story": "Weekly cheese tastings create tight-knit foodie community", "signal": "Active Instagram with 500+ engaged followers"}},
    {{"name": "Midnight Frisbee Society", "category": "Sports/Quirky", "story": "...", "signal": "..."}}
  ]
}}"""

# Contact extraction prompt for individual entities
CONTACT_EXTRACTION_PROMPT = """You are an aggressive data extraction specialist. From the following text scraped from an organization's website, find ANY contact information available.

CRITICAL: Look for ANY email addresses, even if they're not clearly labeled. Common patterns:
- editor@domain.com, info@domain.com, contact@domain.com
- firstname.lastname@domain.edu
- Email addresses in staff listings, about pages, contact forms
- Look in mailto: links, staff directories, footer text

Find:
- organization_name: The official name of the organization  
- leader_name: Look for titles like President, Editor-in-Chief, Coordinator, Chair, Director, Managing Editor
- leader_title: The specific title/position
- contact_email: ANY email address found - personal, general, or departmental
- phone: Phone number if available

Website Content:
{content}

Return ONLY valid JSON:
{{
  "organization_name": "The Water Tower",
  "leader_name": "Jane Doe", 
  "leader_title": "Editor-in-Chief",
  "contact_email": "watertower@uvm.edu",
  "phone": "802-555-0123"
}}

IMPORTANT: If you find ANY email address (@domain), include it. Don't be picky - any contact is better than none. If a field cannot be found, return null for that key."""


class DiamondFinderEngine:
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
            try:
                self.model = genai.GenerativeModel(model_name)
                _ = self.model.generate_content("test")
                print(f"💎 Diamond Finder Engine: {model_name}")
                break
            except Exception as e:
                print(f"Failed to init {model_name}: {e}")
                continue
        else:
            raise RuntimeError("Failed to initialize Gemini model")
    
    def _parse_json(self, text: str) -> Dict:
        """Extract JSON from Gemini response."""
        text = text.strip()
        
        # Try direct parsing
        if text.startswith('{') and text.endswith('}'):
            try:
                return json.loads(text)
            except:
                pass
        
        # Look for JSON in markdown blocks
        import re
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
        
        # Look for any JSON-like structure
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        
        return {"error": "Failed to parse JSON response"}
    
    def find_diamonds(self, campus_name: str) -> Dict:
        """Find diamond in the rough organizations."""
        print(f"\n💎 DIAMOND DISCOVERY: {campus_name}")
        
        # Get campus-specific subreddit/newspaper names first
        campus_slug = campus_name.lower().replace(" ", "").replace("university", "").replace("college", "")
        
        diamond_queries = [
            f'site:{campus_slug}.edu "club spotlight" OR "student organization feature"',
            f'"most unusual student clubs at {campus_name}"',
            f'site:reddit.com "{campus_name}" "most active club" OR "best clubs"',
            f'"{campus_name}" student-run business OR startup competition',
            f'"{campus_name}" student newspaper unique organizations quirky',
            f'site:reddit.com/r/{campus_slug} club recommendations active'
        ]
        
        search_results = []
        for query in diamond_queries:
            print(f"🔍 {query[:60]}...")
            try:
                result = tool_web_search(query)
                if result.get("corpus"):
                    search_results.append(result["corpus"])
                time.sleep(0.3)
            except Exception as e:
                print(f"❌ Query failed: {e}")
        
        combined_data = "\n\n---\n\n".join(search_results)[:15000]
        
        if not combined_data:
            return {"diamond_orgs": [], "error": "No search data found"}
        
        # Extract diamonds using AI
        prompt = DIAMOND_FINDER_PROMPT.format(campus_name=campus_name, search_data=combined_data)
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json(response.text)
            
            if "error" in result:
                return {"diamond_orgs": [], "error": result["error"]}
            
            diamonds = result.get("diamond_orgs", [])
            print(f"✅ Found {len(diamonds)} diamond organizations")
            return {"diamond_orgs": diamonds}
            
        except Exception as e:
            return {"diamond_orgs": [], "error": str(e)}
    
    def get_entity_contact(self, entity_name: str, campus_name: str) -> Dict:
        """Get contact information for a specific entity using deep crawling."""
        print(f"\n📞 CONTACT FINDER: {entity_name}")
        
        # Step 1: Crawl for contact information
        contact_content = tool_crawl_for_contacts(entity_name, campus_name)
        
        if "Could not find" in contact_content or len(contact_content) < 100:
            return {
                "organization_name": entity_name,
                "leader_name": None,
                "leader_title": None, 
                "contact_email": None,
                "phone": None,
                "error": "Insufficient contact data found"
            }
        
        # Step 2: Extract contact information using AI
        prompt = CONTACT_EXTRACTION_PROMPT.format(content=contact_content[:10000])
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json(response.text)
            
            if "error" in result:
                return {
                    "organization_name": entity_name,
                    "leader_name": None,
                    "leader_title": None,
                    "contact_email": None, 
                    "phone": None,
                    "error": result["error"]
                }
            
            # Ensure organization name is set
            if not result.get("organization_name"):
                result["organization_name"] = entity_name
                
            print(f"✅ Contact found: {result.get('leader_name', 'N/A')} ({result.get('contact_email', 'N/A')})")
            return result
            
        except Exception as e:
            return {
                "organization_name": entity_name,
                "leader_name": None,
                "leader_title": None,
                "contact_email": None,
                "phone": None, 
                "error": str(e)
            }
    
    def discover_entity_name(self, campus_name: str, entity_type: str) -> str:
        """Discover the actual name of an entity at a specific campus."""
        print(f"🔍 Discovering {entity_type} name for {campus_name}")
        
        # Search queries to find the actual entity name
        discovery_queries = {
            "student_newspaper": [
                f'"{campus_name}" main student newspaper "independent voice"',
                f'"{campus_name}" official student newspaper "since"',
                f'site:{campus_name.lower().replace(" ", "").replace("university", "").replace("college", "")}.edu student newspaper weekly',
                f'"{campus_name}" campus newspaper weekly publication'
            ],
            "student_government": [
                f'"{campus_name}" main student government "undergraduate"',
                f'"{campus_name}" student government association "SGA"',
                f'site:{campus_name.lower().replace(" ", "").replace("university", "").replace("college", "")}.edu student government officers',
                f'"{campus_name}" undergraduate student government council'
            ],
            "residence_hall": [
                f'"{campus_name}" residence hall association "RHA"',
                f'"{campus_name}" residential life office "housing"',
                f'site:{campus_name.lower().replace(" ", "").replace("university", "").replace("college", "")}.edu housing contact',
                f'"{campus_name}" housing residential life staff'
            ]
        }
        
        queries = discovery_queries.get(entity_type, [])
        all_content = []
        
        for query in queries[:2]:  # Limit queries to prevent timeout
            try:
                result = tool_web_search(query)
                if result.get("corpus"):
                    all_content.append(result["corpus"])
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠️ Discovery query failed: {e}")
        
        if not all_content:
            return None
        
        combined_content = "\n\n".join(all_content)[:8000]
        
        # AI prompt to extract the actual entity name
        discovery_prompt = f"""You are a university research specialist. From the following search results about {campus_name}, identify the EXACT, OFFICIAL name of the PRIMARY {entity_type}.

Search Results:
{combined_content}

Instructions for student newspaper:
- Look for the MAIN, PRIMARY student newspaper (usually the largest, most established)
- Keywords: "independent voice", "since [year]", "official student newspaper", "main campus publication"
- Avoid: departmental newsletters, specialty publications, secondary papers
- Examples: "The Stanford Daily", "The Harvard Crimson", "The Vermont Cynic"

Instructions for student government:
- Look for the MAIN undergraduate student government (not graduate or departmental)
- Keywords: "student government association", "undergraduate council", "SGA", "student senate"
- Examples: "ASUC", "Harvard Undergraduate Council", "Rice Student Association"

Instructions for residence hall:
- Look for the PRIMARY housing/residential life office or RHA
- Keywords: "residence hall association", "residential life", "housing office", "RHA"
- Examples: "Rice Residential Colleges", "Harvard Housing", "Residence Hall Association"

CRITICAL: If multiple publications appear, choose the one that seems to be the primary/main campus newspaper with the broadest coverage and longest history.

Return ONLY the exact official name. If not found, return "NOT_FOUND".

Official Name:"""

        try:
            response = self.model.generate_content(discovery_prompt)
            entity_name = response.text.strip().replace('"', '')
            
            if "NOT_FOUND" in entity_name or len(entity_name) < 3:
                return None
                
            print(f"✅ Discovered: {entity_name}")
            return entity_name
            
        except Exception as e:
            print(f"⚠️ Discovery failed: {e}")
            return None

    def find_universal_inroads(self, campus_name: str) -> Dict:
        """Find the Four Universal Inroads using smart discovery + contact finder."""
        print(f"\n🎯 UNIVERSAL INROADS WITH SMART DISCOVERY: {campus_name}")
        
        inroad_types = ["student_newspaper", "student_government", "residence_hall"]  # Removed tour_guides to minimize Tavily calls
        universal_inroads = {}
        successful_contacts = 0
        
        for inroad_type in inroad_types:
            print(f"\n🔍 Processing: {inroad_type}")
            
            # Step 1: Discover the actual entity name for this campus
            discovered_name = self.discover_entity_name(campus_name, inroad_type)
            
            if discovered_name:
                # Step 2: Get contact info for the discovered entity
                contact_info = self.get_entity_contact(discovered_name, campus_name)
                
                # If discovered name failed, try fallback approaches
                if not contact_info.get("contact_email") or "Could not find homepage" in str(contact_info):
                    print(f"⚠️ Discovered name '{discovered_name}' failed, trying fallback...")
                    
                    # Try generic fallback names
                    fallback_names = {
                        "student_newspaper": [f"{campus_name} student newspaper", "student newspaper"],
                        "student_government": [f"{campus_name} student government", "student government"],
                        "residence_hall": [f"{campus_name} housing", "residential life"],
                        "tour_guides": [f"{campus_name} admissions", "admissions office"]
                    }
                    
                    for fallback_name in fallback_names.get(inroad_type, []):
                        fallback_contact = self.get_entity_contact(fallback_name, campus_name)
                        if fallback_contact.get("contact_email") and "@" in fallback_contact["contact_email"]:
                            contact_info = fallback_contact
                            print(f"✅ Fallback successful with: {fallback_name}")
                            break
                
                # Step 3: Format the results
                if contact_info.get("contact_email") and "@" in contact_info["contact_email"]:
                    successful_contacts += 1
                    
                if inroad_type == "student_newspaper":
                    universal_inroads[inroad_type] = {
                        "name": contact_info.get("organization_name", discovered_name),
                        "editor": contact_info.get("leader_name"),
                        "editor_title": contact_info.get("leader_title"),
                        "contact": contact_info.get("contact_email"),
                        "phone": contact_info.get("phone")
                    }
                elif inroad_type == "student_government":
                    universal_inroads[inroad_type] = {
                        "name": contact_info.get("organization_name", discovered_name),
                        "president": contact_info.get("leader_name"),
                        "president_title": contact_info.get("leader_title"),
                        "contact": contact_info.get("contact_email"),
                        "phone": contact_info.get("phone")
                    }
                else:
                    universal_inroads[inroad_type] = {
                        "name": contact_info.get("organization_name", discovered_name),
                        "coordinator": contact_info.get("leader_name"),
                        "coordinator_title": contact_info.get("leader_title"),
                        "contact": contact_info.get("contact_email"),
                        "phone": contact_info.get("phone")
                    }
            else:
                # Fallback if discovery failed
                print(f"❌ Could not discover {inroad_type} name")
                universal_inroads[inroad_type] = {
                    "name": f"{campus_name} {inroad_type.replace('_', ' ').title()}",
                    "contact": None,
                    "error": "Entity name discovery failed"
                }
        
        print(f"✅ Smart Discovery completed: {successful_contacts}/4 inroads with email contacts")
        return {"universal_inroads": universal_inroads, "contacts_found": successful_contacts}
    
    def run_diamond_analysis(self, campus_name: str) -> Dict:
        """Run the complete diamond finding analysis."""
        print(f"\n💎 DIAMOND FINDER ENGINE: {campus_name}")
        print("="*60)
        
        # Find diamonds and inroads
        diamonds_result = self.find_diamonds(campus_name)
        inroads_result = self.find_universal_inroads(campus_name)
        
        # Combine results
        results = {
            "campus_name": campus_name,
            "diamond_orgs": diamonds_result.get("diamond_orgs", []),
            "universal_inroads": inroads_result.get("universal_inroads", {}),
            "analysis_quality": {
                "diamonds_found": len(diamonds_result.get("diamond_orgs", [])),
                "inroads_found": inroads_result.get("contacts_found", 0),
                "total_inroads": 4,
                "contact_success_rate": f"{inroads_result.get('contacts_found', 0)}/4",
                "diamond_errors": diamonds_result.get("error"),
                "inroads_errors": inroads_result.get("error")
            }
        }
        
        print(f"\n💎 DIAMOND FINDER ANALYSIS COMPLETE")
        print(f"   Diamonds: {results['analysis_quality']['diamonds_found']} organizations")
        print(f"   Inroads: {results['analysis_quality']['inroads_found']}/4 contact paths")
        
        return results


def run_diamond_finder_engine(campus_name: str, gemini_api_key: str) -> Dict:
    """Entry point for diamond finder analysis."""
    engine = DiamondFinderEngine(gemini_api_key)
    return engine.run_diamond_analysis(campus_name)
