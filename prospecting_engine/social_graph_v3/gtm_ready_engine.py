"""
GTM-Ready Campus Dossier Engine

This is the final, comprehensive intelligence engine that produces a complete
GTM-ready dossier with 5 sections: Executive Summary, Quantitative Scorecard,
Qualitative Intelligence, Actionable Playbook, and Proven Planners.

Uses strategic API calls - minimal but comprehensive intelligence gathering.
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

# Add parent directory for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

from quantitative_engine import QuantitativeEngine
from tools import tool_web_search
from intelligence_sources import RedditSource
from sg_prompts import MASTER_ANALYST_PROMPT


class GTMReadyEngine:
    """
    The final GTM intelligence engine that produces comprehensive campus dossiers.
    
    Strategy:
    1. Quantitative Foundation (existing engine)
    2. Strategic Intelligence Gathering (targeted searches)
    3. Community Analysis (Reddit + targeted web search)
    4. Contact Discovery (proven planners + universal inroads)
    5. Master Synthesis (comprehensive dossier)
    """
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
    def generate_dossier(self, campus_name: str) -> Dict[str, Any]:
        """
        Generate complete GTM-ready campus dossier.
        """
        print(f"\n🎯 GTM-READY DOSSIER ENGINE: {campus_name}")
        print("="*70)
        
        try:
            # Phase 1: Quantitative Foundation
            quantitative_data = self._get_quantitative_foundation(campus_name)
            
            # Phase 2: Strategic Intelligence Gathering
            intelligence_data = self._gather_strategic_intelligence(campus_name)
            
            # Phase 3: Contact Discovery
            contact_data = self._discover_actionable_contacts(campus_name)
            
            # Phase 4: Master Synthesis
            dossier = self._synthesize_gtm_dossier(
                campus_name, 
                quantitative_data, 
                intelligence_data, 
                contact_data
            )
            
            return {
                "campus_name": campus_name,
                "dossier": dossier,
                "raw_data": {
                    "quantitative": quantitative_data,
                    "intelligence": intelligence_data,
                    "contacts": contact_data
                },
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ GTM Dossier generation failed: {e}")
            return {"error": str(e)}
    
    def _get_quantitative_foundation(self, campus_name: str) -> Dict[str, Any]:
        """Phase 1: Get quantitative scorecard using existing engine."""
        print("📊 Phase 1: Quantitative Foundation...")
        
        try:
            quant_engine = QuantitativeEngine(self.gemini_api_key)
            data = quant_engine.run(campus_name)
            
            # Calculate community potential score
            scorecard = data.get("prospect_scorecard", {})
            community_score = self._calculate_community_potential_score(scorecard)
            
            return {
                "scorecard": scorecard,
                "community_potential_score": community_score,
                "data_quality": data.get("data_quality", {})
            }
            
        except Exception as e:
            print(f"❌ Quantitative analysis failed: {e}")
            return {"error": str(e)}
    
    def _calculate_community_potential_score(self, scorecard: Dict) -> float:
        """Calculate weighted community potential score (1-100)."""
        score = 0
        weights = {
            "housing": 0.25,      # High housing = tight community
            "centricity": 0.20,   # Campus-centric = contained social life
            "greek": 0.15,        # Greek life = social infrastructure
            "retention": 0.15,    # High retention = community satisfaction
            "ncaa": 0.10,         # D1 sports = unifying culture
            "ratio": 0.10,        # Low ratio = intimate environment
            "acceptance": 0.05    # Selectivity indicator
        }
        
        for metric, weight in weights.items():
            metric_data = scorecard.get(metric, {})
            if "error" not in metric_data:
                if metric == "housing":
                    value = metric_data.get("percentInHousing", 0)
                    score += (value / 100) * weight * 100
                elif metric == "centricity":
                    value = metric_data.get("campusCentricityScore", 5)
                    score += (value / 10) * weight * 100
                elif metric == "greek":
                    value = metric_data.get("percentGreekLife", 0)
                    score += (min(value, 40) / 40) * weight * 100  # Cap at 40%
                elif metric == "retention":
                    value = metric_data.get("freshmanRetentionRate", 0)
                    score += (value / 100) * weight * 100
                elif metric == "ncaa":
                    value = metric_data.get("ncaaDivision", "")
                    if value == "D1":
                        score += weight * 100
                    elif value == "D2":
                        score += weight * 70
                    elif value == "D3":
                        score += weight * 40
                elif metric == "ratio":
                    value = metric_data.get("studentFacultyRatio", 20)
                    # Handle string ratios like "13:1"
                    if isinstance(value, str) and ":" in value:
                        try:
                            value = float(value.split(":")[0])
                        except:
                            value = 20
                    # Lower ratio is better, invert scale
                    normalized = max(0, (25 - value) / 25)
                    score += normalized * weight * 100
                elif metric == "acceptance":
                    value = metric_data.get("acceptanceRate", 50)
                    # Lower acceptance rate indicates higher selectivity
                    normalized = max(0, (100 - value) / 100)
                    score += normalized * weight * 100
        
        return round(score, 1)
    
    def _gather_strategic_intelligence(self, campus_name: str) -> Dict[str, Any]:
        """Phase 2: Strategic intelligence gathering with targeted searches."""
        print("🔍 Phase 2: Strategic Intelligence Gathering...")
        
        intelligence = {}
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._analyze_campus_communities, campus_name): "communities",
                executor.submit(self._discover_third_places, campus_name): "third_places", 
                executor.submit(self._find_diamond_orgs, campus_name): "diamond_orgs"
            }
            
            for future in as_completed(futures):
                key = futures[future]
                try:
                    result = future.result()
                    intelligence[key] = result
                    print(f"   ✅ {key}: Success")
                except Exception as e:
                    intelligence[key] = {"error": str(e)}
                    print(f"   ❌ {key}: {e}")
        
        return intelligence
    
    def _analyze_campus_communities(self, campus_name: str) -> Dict[str, Any]:
        """Analyze campus communities using Reddit + targeted search."""
        try:
            # Use Reddit for community insights
            reddit_source = RedditSource(self.gemini_api_key)
            subreddit_name = self._guess_subreddit_name(campus_name)
            reddit_data = reddit_source.get_humint_report(subreddit_name)
            
            # Targeted search for community clusters
            search_query = f'"{campus_name}" student organizations "most popular" OR "biggest" OR "influential"'
            search_result = tool_web_search(search_query, max_results=3)
            
            # AI analysis of community structure
            analysis_prompt = f"""Analyze the community structure at {campus_name}.

REDDIT DATA: {json.dumps(reddit_data)[:3000]}
WEB SEARCH: {search_result.get('content', '')[:3000]}

Identify 3-5 primary "community clusters" or "tribes" on campus. For each cluster, provide:
- Name (e.g., "The Greek Life & Athletics Hub")
- Description (sociological snapshot of this group)
- Influence level (high/medium/low)

Return JSON: {{"community_clusters": [{{"name": "...", "description": "...", "influence": "..."}}]}}"""

            response = self.model.generate_content(analysis_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _discover_third_places(self, campus_name: str) -> Dict[str, Any]:
        """Discover and verify key third places around campus with Google Maps data."""
        try:
            # Strategic search for third places
            search_query = f'"{campus_name}" student favorite places "coffee" OR "cafe" OR "bar" OR "restaurant" near campus'
            search_result = tool_web_search(search_query, max_results=3)
            
            time.sleep(1.0)  # Rate limiting
            
            # Follow up with social context search
            social_query = f'"{campus_name}" students "hang out" OR "meet" best places near campus'
            social_result = tool_web_search(social_query, max_results=2)
            
            # Get Google Maps data via PhantomBuster (if available)
            maps_data = self._get_maps_data(campus_name)
            
            # AI analysis of third places with Maps integration
            analysis_prompt = f"""Identify the key "third places" around {campus_name} - the cafes, bars, parks, etc. where students socialize.

SEARCH DATA: {search_result.get('content', '')[:3000]}
SOCIAL CONTEXT: {social_result.get('content', '')[:2000]}
MAPS DATA: {json.dumps(maps_data)[:2000]}

For each location, provide:
- location_name
- type (cafe/bar/park/etc.)
- address (if available from maps data)
- rating (if available from maps data)
- social_context (why students go there, when it's busy, social dynamics)
- student_popularity (high/medium/low based on mentions)

Return JSON: {{"third_places": [{{"location_name": "...", "type": "...", "address": "...", "rating": ..., "social_context": "...", "student_popularity": "..."}}]}}"""

            response = self.model.generate_content(analysis_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_maps_data(self, campus_name: str) -> Dict[str, Any]:
        """Get Google Maps data via PhantomBuster if available."""
        try:
            from intelligence_sources import GeospatialSource
            geo_source = GeospatialSource(self.gemini_api_key)
            return geo_source.get_geoint_report(campus_name)
        except Exception as e:
            print(f"Maps data unavailable: {e}")
            return {"error": str(e)}
    
    def _find_diamond_orgs(self, campus_name: str) -> Dict[str, Any]:
        """Find comprehensive list of 30+ student organizations for PhantomBuster input."""
        try:
            # Comprehensive searches for ALL types of orgs (not just diamonds)
            searches = [
                f'"{campus_name}" complete student organization directory list',
                f'"{campus_name}" student clubs list academic professional recreational',
                f'"{campus_name}" greek life fraternities sororities complete list',
                f'"{campus_name}" student government departments councils committees',
                f'"{campus_name}" cultural ethnic international student organizations',
                f'"{campus_name}" sports clubs intramural recreation organizations',
                f'"{campus_name}" arts music theater creative student groups',
                f'"{campus_name}" volunteer service community engagement organizations',
                f'"{campus_name}" religious spiritual faith-based student groups',
                f'"{campus_name}" honor societies academic achievement organizations'
            ]
            
            all_content = []
            for search_query in searches:
                result = tool_web_search(search_query, max_results=3)
                if result.get('content'):
                    all_content.append(result['content'][:3000])
                time.sleep(1.0)
            
            combined_content = "\n\n".join(all_content)
            
            # AI analysis for comprehensive org list (30+ orgs for PhantomBuster)
            analysis_prompt = f"""Extract a comprehensive list of 30+ student organizations from {campus_name} for PhantomBuster workflow.

GOAL: Create actionable lists for Instagram profile discovery and engagement campaigns.

CONTENT: {combined_content[:15000]}

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

TARGET: Find 30+ organizations minimum. Be comprehensive, not selective."""

            response = self.model.generate_content(analysis_prompt)
            orgs_data = self._parse_json_response(response.text)
            
            # Process comprehensive org list for PhantomBuster workflow
            if isinstance(orgs_data, dict) and "comprehensive_orgs" in orgs_data:
                comprehensive_orgs = orgs_data["comprehensive_orgs"]
                
                # Sort by priority and limit for manageable output
                high_priority = [org for org in comprehensive_orgs if org.get("target_priority") == "high"]
                medium_priority = [org for org in comprehensive_orgs if org.get("target_priority") == "medium"]
                low_priority = [org for org in comprehensive_orgs if org.get("target_priority") == "low"]
                
                # Combine and limit to top 30 most promising
                final_orgs = (high_priority + medium_priority + low_priority)[:30]
                
                print(f"📋 Found {len(comprehensive_orgs)} total orgs, selected top {len(final_orgs)} for PhantomBuster")
                
                return {
                    "comprehensive_orgs": final_orgs,
                    "total_found": len(comprehensive_orgs),
                    "phantombuster_ready": True,
                    "categories_breakdown": self._analyze_org_categories(final_orgs)
                }
            
            return orgs_data
            
        except Exception as e:
            return {"error": str(e)}
    
    def _verify_org_social_proof(self, orgs: List[Dict], campus_name: str) -> List[Dict]:
        """Verify organizations have social proof via follower counts/engagement."""
        verified_orgs = []
        
        for org in orgs:
            org_name = org.get("name", "")
            instagram_handle = org.get("instagram_handle", "")
            
            # If we have an Instagram handle, try to verify
            if instagram_handle and "@" in instagram_handle:
                handle = instagram_handle.replace("@", "")
                
                # Search for follower count information
                verification_query = f'"{org_name}" {campus_name} Instagram followers OR engagement'
                try:
                    verification_result = tool_web_search(verification_query, max_results=1)
                    verification_content = verification_result.get('content', '')
                    
                    # Use AI to extract social proof metrics
                    metrics_prompt = f"""Analyze this content about {org_name} at {campus_name}.

CONTENT: {verification_content[:1500]}

Extract any social media metrics:
- follower_count (number or estimate)
- engagement_level (high/medium/low)
- social_proof_score (1-10 based on activity/following)

Return JSON: {{"follower_count": "...", "engagement_level": "...", "social_proof_score": ...}}"""

                    metrics_response = self.model.generate_content(metrics_prompt)
                    metrics_data = self._parse_json_response(metrics_response.text)
                    
                    # Add verification data to org
                    if isinstance(metrics_data, dict):
                        org.update(metrics_data)
                        org["verified"] = True
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"Verification failed for {org_name}: {e}")
                    org["verified"] = False
            else:
                org["verified"] = False
            
            verified_orgs.append(org)
        
        # Sort by social proof score (if available)
        def sort_key(org):
            score = org.get("social_proof_score", 0)
            return score if isinstance(score, (int, float)) else 0
        
        verified_orgs.sort(key=sort_key, reverse=True)
        return verified_orgs[:8]  # Return top 8
    
    def _analyze_org_categories(self, orgs: List[Dict]) -> Dict[str, int]:
        """Analyze organization categories for PhantomBuster strategy insights."""
        categories = {}
        for org in orgs:
            category = org.get("category", "Unknown")
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _discover_actionable_contacts(self, campus_name: str) -> Dict[str, Any]:
        """Phase 3: Guarantee 5+ actionable email contacts with multi-strategy approach."""
        print("👥 Phase 3: Smart Contact Discovery (Guaranteeing 5+ emails)...")
        
        # Multi-strategy parallel contact discovery
        all_contacts = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._strategy_1_leadership_contacts, campus_name): "leadership",
                executor.submit(self._strategy_2_directory_mining, campus_name): "directories", 
                executor.submit(self._strategy_3_event_organizers, campus_name): "events",
                executor.submit(self._strategy_4_social_leaders, campus_name): "social"
            }
            
            for future in as_completed(futures):
                strategy = futures[future]
                try:
                    result = future.result()
                    if isinstance(result, dict) and "contacts" in result:
                        contacts_found = len([c for c in result["contacts"] if c.get("email") and "@" in c["email"]])
                        all_contacts.extend(result["contacts"])
                        print(f"   ✅ {strategy}: {contacts_found} emails found")
                    else:
                        print(f"   ⚠️ {strategy}: No valid contacts")
                except Exception as e:
                    print(f"   ❌ {strategy}: {e}")
        
        # Deduplicate and prioritize contacts
        final_contacts = self._deduplicate_and_prioritize_contacts(all_contacts)
        
        # Ensure we have at least 5 contacts with emails
        email_contacts = [c for c in final_contacts if c.get("email") and "@" in c["email"]]
        
        print(f"   🎯 FINAL RESULT: {len(email_contacts)} contacts with emails")
        
        if len(email_contacts) < 5:
            print(f"   ⚠️ Warning: Only found {len(email_contacts)} contacts, running emergency backup search...")
            backup_contacts = self._emergency_contact_search(campus_name)
            final_contacts.extend(backup_contacts)
            email_contacts = [c for c in final_contacts if c.get("email") and "@" in c["email"]]
            print(f"   🔄 After backup: {len(email_contacts)} total email contacts")
        
        return {
            "all_contacts": final_contacts,
            "email_contacts": email_contacts,
            "contact_count": len(email_contacts),
            "strategies_used": ["leadership", "directories", "events", "social"]
        }
    
    def _strategy_1_leadership_contacts(self, campus_name: str) -> Dict[str, Any]:
        """Strategy 1: Target key leadership positions."""
        try:
            leadership_searches = [
                f'"{campus_name}" student government president vice president email contact',
                f'"{campus_name}" student newspaper editor in chief email',
                f'"{campus_name}" residence hall association president email',
                f'"{campus_name}" student activities board director email'
            ]
            
            all_content = []
            for search in leadership_searches:
                result = tool_web_search(search, max_results=2)
                if result.get('content'):
                    all_content.append(result['content'][:2000])
                time.sleep(0.8)
            
            combined_content = "\n\n".join(all_content)
            
            extraction_prompt = f"""Extract student leader contact information from {campus_name}.

CONTENT: {combined_content[:6000]}

Find contacts for key positions:
- Student Government (President, VP, Secretary, Treasurer)
- Student Newspaper (Editor-in-Chief, Managing Editor)  
- Residence Life (RHA President, Programming Director)
- Student Activities (Director, Coordinator)

For each contact found, provide:
- name (full name)
- title (specific position)
- organization (which group they lead)
- email (must include @ symbol)
- confidence (high/medium/low based on source quality)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "...", "confidence": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _strategy_2_directory_mining(self, campus_name: str) -> Dict[str, Any]:
        """Strategy 2: Mine student directories and organization listings."""
        try:
            directory_searches = [
                f'"{campus_name}" student organization directory officers contact',
                f'"{campus_name}" student staff directory email',
                f'site:{self._get_campus_domain(campus_name)} student contact directory'
            ]
            
            all_content = []
            for search in directory_searches:
                result = tool_web_search(search, max_results=2)
                if result.get('content'):
                    all_content.append(result['content'][:2500])
                time.sleep(0.8)
            
            combined_content = "\n\n".join(all_content)
            
            extraction_prompt = f"""Extract student contacts from directory listings at {campus_name}.

CONTENT: {combined_content[:7000]}

Look for:
- Student organization officers with email addresses
- Student staff members with contact info
- Any directory listings with student emails
- Club presidents, VPs, coordinators with emails

For each contact, provide:
- name
- title (position/role)
- organization (club/group name)
- email (must contain @)
- source_type ("directory" or "listing")

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "...", "source_type": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _strategy_3_event_organizers(self, campus_name: str) -> Dict[str, Any]:
        """Strategy 3: Find students who organize events."""
        try:
            event_searches = [
                f'"{campus_name}" student events 2024 organizer contact coordinator',
                f'"{campus_name}" campus programming board event coordinator email',
                f'"{campus_name}" student union programming events contact'
            ]
            
            all_content = []
            for search in event_searches:
                result = tool_web_search(search, max_results=2)
                if result.get('content'):
                    all_content.append(result['content'][:2000])
                time.sleep(0.8)
            
            combined_content = "\n\n".join(all_content)
            
            extraction_prompt = f"""Find student event organizers at {campus_name}.

CONTENT: {combined_content[:6000]}

Look for students who:
- Organize campus events or programming
- Coordinate activities or social events
- Work in student union programming
- Plan residence hall events

For each organizer found, provide:
- name
- title (role in event planning)
- organization (group they organize for)
- email (contact information)
- events_organized (what they've planned)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "...", "events_organized": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _strategy_4_social_leaders(self, campus_name: str) -> Dict[str, Any]:
        """Strategy 4: Find social influencers and community leaders."""
        try:
            social_searches = [
                f'"{campus_name}" student influencers Instagram social media contact',
                f'"{campus_name}" campus tour guide coordinator email contact',
                f'"{campus_name}" orientation leader student coordinator email'
            ]
            
            all_content = []
            for search in social_searches:
                result = tool_web_search(search, max_results=2)
                if result.get('content'):
                    all_content.append(result['content'][:2000])
                time.sleep(0.8)
            
            combined_content = "\n\n".join(all_content)
            
            extraction_prompt = f"""Find social leaders and influencers at {campus_name}.

CONTENT: {combined_content[:6000]}

Look for students who:
- Lead campus tours or orientation
- Have social media influence on campus
- Coordinate peer programs
- Lead outreach or ambassador programs

For each leader found, provide:
- name
- title (leadership role)
- organization (program they're part of)
- email (contact information)
- influence_type (tours/social/peer/ambassador)

Return JSON: {{"contacts": [{{"name": "...", "title": "...", "organization": "...", "email": "...", "influence_type": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _deduplicate_and_prioritize_contacts(self, all_contacts: List[Dict]) -> List[Dict]:
        """Deduplicate contacts and prioritize by quality."""
        if not all_contacts:
            return []
        
        # Deduplicate by email
        seen_emails = set()
        unique_contacts = []
        
        for contact in all_contacts:
            email = contact.get("email", "").lower().strip()
            if email and "@" in email and email not in seen_emails:
                seen_emails.add(email)
                unique_contacts.append(contact)
        
        # Prioritize by position importance
        def priority_score(contact):
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
        
        unique_contacts.sort(key=priority_score, reverse=True)
        return unique_contacts
    
    def _emergency_contact_search(self, campus_name: str) -> List[Dict]:
        """Emergency backup search if we don't have 5 contacts."""
        try:
            # Broader, more aggressive search
            emergency_query = f'"{campus_name}" student email contact @ .edu'
            result = tool_web_search(emergency_query, max_results=3)
            
            if not result.get('content'):
                return []
            
            extraction_prompt = f"""EMERGENCY CONTACT EXTRACTION for {campus_name}.

This is a fallback search. Extract ANY student contacts with email addresses.

CONTENT: {result.get('content', '')[:4000]}

Find ANY students with:
- Name and email address
- Any student role or organization
- Contact information with @ symbol

Be liberal - include any student contact found.

Return JSON: {{"contacts": [{{"name": "...", "title": "Student", "organization": "...", "email": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            emergency_data = self._parse_json_response(response.text)
            
            if isinstance(emergency_data, dict) and "contacts" in emergency_data:
                return emergency_data["contacts"]
            
            return []
            
        except Exception as e:
            print(f"Emergency search failed: {e}")
            return []
    
    def _get_campus_domain(self, campus_name: str) -> str:
        """Get likely campus domain for targeted searches."""
        domain_mapping = {
            "texas christian university": "tcu.edu",
            "university of alabama": "ua.edu",
            "university of california berkeley": "berkeley.edu",
            "stanford university": "stanford.edu",
            "massachusetts institute of technology": "mit.edu"
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
    
    def _find_universal_inroads(self, campus_name: str) -> Dict[str, Any]:
        """Find universal inroads: Student Government, Newspaper, RHA."""
        try:
            # Strategic search for key organizations
            search_query = f'"{campus_name}" student government officers contact email'
            sg_result = tool_web_search(search_query, max_results=2)
            
            time.sleep(1.0)
            
            newspaper_query = f'"{campus_name}" student newspaper editor contact'
            news_result = tool_web_search(newspaper_query, max_results=2)
            
            # AI extraction of contacts
            extraction_prompt = f"""Extract specific contact information for key student leaders at {campus_name}.

STUDENT GOVERNMENT DATA: {sg_result.get('content', '')[:3000]}
NEWSPAPER DATA: {news_result.get('content', '')[:2000]}

Find contacts for:
1. Student Government (President, VP, or other officer)
2. Student Newspaper (Editor-in-Chief or Managing Editor)
3. Any other student leaders mentioned

For each contact, provide:
- organization_name
- leader_name
- leader_title
- contact_email

Return JSON: {{"contacts": [{{"organization_name": "...", "leader_name": "...", "leader_title": "...", "contact_email": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _find_proven_planners(self, campus_name: str) -> Dict[str, Any]:
        """Find students who have proven event planning experience."""
        try:
            # Search for recent events and their organizers
            events_query = f'"{campus_name}" student events 2024 organizer contact'
            events_result = tool_web_search(events_query, max_results=3)
            
            time.sleep(1.0)
            
            # AI extraction of event planners
            extraction_prompt = f"""Find students who have organized events at {campus_name}.

EVENTS DATA: {events_result.get('content', '')[:4000]}

Look for:
- Students who organized specific events
- Names and contact information
- What events they planned
- Which organizations they worked with

For each planner, provide:
- planner_name
- planner_email (if available)
- event_organized
- hosting_org
- evidence_context (brief description of the event/role)

Return JSON: {{"proven_planners": [{{"planner_name": "...", "planner_email": "...", "event_organized": "...", "hosting_org": "...", "evidence_context": "..."}}]}}"""

            response = self.model.generate_content(extraction_prompt)
            return self._parse_json_response(response.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _synthesize_gtm_dossier(self, campus_name: str, quant_data: Dict, intel_data: Dict, contact_data: Dict) -> Dict[str, Any]:
        """Phase 4: Master synthesis into GTM-ready dossier with ALL required sections."""
        print("🧠 Phase 4: Master Synthesis (Full Specification)...")
        
        try:
            # Use the comprehensive MASTER_ANALYST_PROMPT
            synthesis_prompt = f"""You are a senior analyst at a GTM intelligence agency like CACI or a geopolitical advisor at a firm like Eurasia Group. You are an expert at synthesizing disparate, multi-modal data sources into a single, coherent, and ruthlessly actionable strategic briefing.

You have been provided with a complete intelligence file on **{campus_name}** from multiple sources.

YOUR TASK: Synthesize ALL of the following information into a definitive "Social Graph Dossier." Your analysis must be insightful, and your recommendations must be specific and bold.

INTELLIGENCE FILE CONTENTS:
1. Quantitative Scorecard: {json.dumps(quant_data, indent=2)[:3000]}
2. Strategic Intelligence: {json.dumps(intel_data, indent=2)[:3000]}
3. Contact Intelligence: {json.dumps(contact_data, indent=2)[:2000]}

REQUIRED DOSSIER SECTIONS (Your Output):

1. **Executive_Summary**: A 2-3 sentence summary of the strategic opportunity at this campus. Include:
   - campus_tier: "Tier 1 - GTM Now" / "Tier 2 - GTM Next, With Nuance" / "Tier 3 - Deprioritize"
   - community_potential_score: {quant_data.get('community_potential_score', 'N/A')}
   - key_insight: Single most important non-obvious finding

2. **Key_Community_Clusters**: A qualitative description of the 3-5 main "tribes" on campus (e.g., "The Tech & Entrepreneurship Scene," "The Greek Life & Athletics Hub," "The Arts & Activism Collective"). Your analysis must be informed by the intelligence data.

3. **Influence_Rankings**: A ranked list of the **Top 15 Most Influential Orgs & Individuals** on campus. Each entry must have:
   - name: Organization or individual name
   - category: Type of influence (Academic/Social/Athletic/Media/Government)
   - justification: Data-driven reason for ranking citing specific evidence (e.g., "High social media engagement," "Hosts major campus events," "Student government leadership")

4. **Social_Heatmap_Analysis**: A paragraph describing the "where and when" of student social life, using the geospatial and social intelligence data to identify key "third places" and social epicenters.

5. **Actionable_GTM_Playbook**: A specific, three-phase GTM plan:
   - Phase_1_Beachhead: Which community cluster and 2-3 specific contacts to target first
   - Phase_2_Saturation: Relationship-driven GTM strategy and partnership opportunities
   - Phase_3_Scale: Biggest opportunity for compounding growth

6. **PhantomBuster_Ready_Orgs**: Comprehensive list of 30+ student organizations formatted for external PhantomBuster workflows:
   - Organization names for Instagram Profile URL Finder
   - Categories for targeted engagement strategies
   - Priority levels for campaign sequencing

CRITICAL: Include contact information from contact intelligence. Ensure you have at least 5 actionable email contacts.

Return ONLY valid JSON in this exact structure:
{{
  "Executive_Summary": {{
    "campus_tier": "...",
    "community_potential_score": ...,
    "key_insight": "..."
  }},
  "Key_Community_Clusters": [...],
  "Influence_Rankings": [
    {{"name": "...", "category": "...", "justification": "..."}},
    // ... 15 total entries
  ],
  "Social_Heatmap_Analysis": "...",
  "Actionable_GTM_Playbook": {{
    "Phase_1_Beachhead": "...",
    "Phase_2_Saturation": "...",
    "Phase_3_Scale": "..."
  }},
  "Contact_Intelligence": {{
    "verified_contacts": [...],
    "total_email_contacts": ...,
    "priority_targets": [...]
  }},
  "PhantomBuster_Ready_Orgs": [
    {{"name": "...", "category": "...", "target_priority": "high/medium/low", "engagement_indicators": "..."}},
    // ... 30+ total organizations for PhantomBuster workflow
  ]
}}"""

            response = self.model.generate_content(synthesis_prompt)
            dossier = self._parse_json_response(response.text)
            
            # Add quantitative scorecard and comprehensive orgs to dossier
            if isinstance(dossier, dict):
                dossier["Quantitative_Scorecard"] = quant_data.get("scorecard", {})
                
                # Add comprehensive orgs if not already in synthesis
                if "PhantomBuster_Ready_Orgs" not in dossier:
                    comprehensive_orgs = intel_data.get("diamond_orgs", {}).get("comprehensive_orgs", [])
                    if comprehensive_orgs:
                        dossier["PhantomBuster_Ready_Orgs"] = comprehensive_orgs
                
                # Validate we have all required sections
                required_sections = [
                    "Executive_Summary", 
                    "Key_Community_Clusters", 
                    "Influence_Rankings", 
                    "Social_Heatmap_Analysis", 
                    "Actionable_GTM_Playbook"
                ]
                
                missing_sections = [s for s in required_sections if s not in dossier]
                if missing_sections:
                    print(f"⚠️ Warning: Missing sections: {missing_sections}")
                
                # Validate contact count
                contact_count = len(contact_data.get("email_contacts", []))
                print(f"📧 Contact Validation: {contact_count} email contacts found")
                
                if contact_count < 5:
                    print(f"⚠️ Warning: Only {contact_count} contacts found, target is 5+")
            
            return dossier
            
        except Exception as e:
            print(f"❌ Master Synthesis failed: {e}")
            return self._create_fallback_dossier(campus_name, quant_data, contact_data)
    
    def _create_fallback_dossier(self, campus_name: str, quant_data: Dict, contact_data: Dict) -> Dict[str, Any]:
        """Create a basic fallback dossier if synthesis fails."""
        return {
            "Executive_Summary": {
                "campus_tier": "Tier 2 - GTM Next, With Nuance",
                "community_potential_score": quant_data.get("community_potential_score", 50),
                "key_insight": "Analysis incomplete - requires manual review"
            },
            "Key_Community_Clusters": [
                "Analysis pending - synthesis failed",
                "Manual review required"
            ],
            "Influence_Rankings": [
                {"name": "Analysis incomplete", "category": "System", "justification": "Synthesis failed"}
            ],
            "Social_Heatmap_Analysis": "Social analysis incomplete due to synthesis failure. Manual review required.",
            "Actionable_GTM_Playbook": {
                "Phase_1_Beachhead": "Manual analysis required",
                "Phase_2_Saturation": "Manual analysis required", 
                "Phase_3_Scale": "Manual analysis required"
            },
            "Contact_Intelligence": contact_data,
            "Quantitative_Scorecard": quant_data.get("scorecard", {}),
            "synthesis_status": "failed"
        }
    
    def _guess_subreddit_name(self, campus_name: str) -> str:
        """Guess likely subreddit name from campus name."""
        name_mapping = {
            "texas christian university": "tcu",
            "university of alabama": "capstone",
            "university of california berkeley": "berkeley",
            "stanford university": "stanford",
            "massachusetts institute of technology": "mit"
        }
        
        campus_lower = campus_name.lower()
        for full_name, subreddit in name_mapping.items():
            if full_name in campus_lower:
                return subreddit
        
        # Fallback: try last word
        return campus_name.split()[-1].lower()
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON from AI response with multiple fallback strategies."""
        try:
            return json.loads(text)
        except:
            pass
        
        # Try extracting JSON from markdown
        if "```json" in text:
            try:
                json_text = text.split("```json")[1].split("```")[0]
                return json.loads(json_text)
            except:
                pass
        
        # Try finding JSON object in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
        
        return {"raw_response": text[:2000]}


def main():
    """CLI interface for GTM-Ready Dossier Engine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate GTM-Ready Campus Dossier")
    parser.add_argument("--campus", required=True, help="University name")
    parser.add_argument("--output", default="gtm_dossier.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    # Load environment
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY not found in environment")
    
    # Generate dossier
    engine = GTMReadyEngine(gemini_key)
    result = engine.generate_dossier(args.campus)
    
    # Save result
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ GTM-Ready Dossier saved: {args.output}")
    
    # Print executive summary
    dossier = result.get("dossier", {})
    if isinstance(dossier, dict) and "executive_summary" in dossier:
        exec_summary = dossier["executive_summary"]
        print(f"\n🎯 EXECUTIVE SUMMARY:")
        print(f"   Tier: {exec_summary.get('tier', 'Unknown')}")
        print(f"   Score: {exec_summary.get('community_potential_score', 'Unknown')}")
        print(f"   Key Insight: {exec_summary.get('key_insight', 'Unknown')}")


if __name__ == "__main__":
    main()
