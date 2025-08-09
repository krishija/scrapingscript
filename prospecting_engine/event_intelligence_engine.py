"""
Event Intelligence Engine - Find High-Agency Event Planners

This engine uses "Time-Sliced Search" to find recent student-organized events
and extract the organizer contact information. These are the highest-agency
students on campus - the ones actually making things happen.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import google.generativeai as genai
from tools import tool_web_search


class EventIntelligenceEngine:
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
    def run(self, campus_name: str) -> Dict[str, Any]:
        """
        Main workflow: Find recent event organizers at a university.
        Returns contact info for students who planned recent events.
        """
        print(f"\n🎪 EVENT INTELLIGENCE ENGINE: {campus_name}")
        print("="*60)
        
        try:
            # Step 1: Find event calendar domain
            event_domain = self.discover_event_calendar(campus_name)
            if not event_domain:
                return {"error": "Could not find event calendar domain"}
            
            # Step 2: Time-sliced event scraping (last 4 months)
            event_corpus = self.scrape_recent_events(campus_name, event_domain)
            if not event_corpus:
                return {"error": "No recent events found"}
            
            # Step 3: Filter for student-organized events
            student_events = self.filter_student_events(event_corpus, campus_name)
            if not student_events:
                return {"error": "No student-organized events found"}
            
            # Step 4: Extract organizer contacts
            event_contacts = self.extract_event_organizers(student_events, campus_name)
            
            return {
                "campus_name": campus_name,
                "event_domain": event_domain,
                "total_events_found": len(student_events),
                "event_organizers": event_contacts,
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Event Intelligence failed: {e}")
            return {"error": str(e)}
    
    def discover_event_calendar(self, campus_name: str) -> str:
        """Step 1: Find the main events calendar URL"""
        print("🔍 Discovering event calendar...")
        
        # Try multiple search strategies
        queries = [
            f'"{campus_name}" events calendar site:.edu',
            f'"{campus_name}" student events calendar university',
            f'site:events.{campus_name.lower().replace(" ", "").replace("university", "")}.edu'
        ]
        
        for query in queries:
            try:
                result = tool_web_search(query, max_results=3)
                sources = result.get("sources", [])
                
                for url in sources:
                    if "events" in url.lower() and ".edu" in url:
                        domain = url.split("//")[1].split("/")[0] if "//" in url else url
                        print(f"✅ Found event domain: {domain}")
                        return domain
                        
                time.sleep(1.0)
            except Exception as e:
                print(f"⚠️ Query failed: {e}")
                continue
        
        print("⚠️ No event calendar found")
        return None
    
    def scrape_recent_events(self, campus_name: str, event_domain: str) -> str:
        """Step 2: Time-sliced event scraping for last 4 months"""
        print("📅 Time-sliced event scraping...")
        
        # Generate last 4 months (PAST events)
        months = []
        current = datetime.now()
        for i in range(1, 5):  # Start from 1 to skip current month
            month_date = current - timedelta(days=30*i)
            months.append({
                "name": month_date.strftime("%B %Y"),
                "short": month_date.strftime("%b %Y")
            })
        
        all_event_content = []
        
        for month in months:
            print(f"   📅 Searching {month['name']}...")
            
            # Time-sliced queries for this month
            month_queries = [
                f'site:{event_domain} "student organization" "{month["name"]}"',
                f'site:{event_domain} "club event" "{month["short"]}"',
                f'site:{event_domain} "student" "contact" "{month["name"]}"'
            ]
            
            for query in month_queries:
                try:
                    result = tool_web_search(query, max_results=2)
                    content = result.get("content", "")
                    if content and len(content) > 100:
                        all_event_content.append(f"=== {month['name']} EVENTS ===\n{content[:1500]}")
                    
                    time.sleep(1.2)  # Rate limiting
                except Exception as e:
                    print(f"   ⚠️ Month query failed: {e}")
                    continue
            
            if len(all_event_content) >= 8:  # Don't overload
                break
        
        final_corpus = "\n\n".join(all_event_content[:8])
        print(f"📊 Collected {len(all_event_content)} event pages, {len(final_corpus)} chars")
        return final_corpus
    
    def filter_student_events(self, event_corpus: str, campus_name: str) -> List[Dict]:
        """Step 3: AI filtering for student-organized events"""
        print("🔍 Filtering for student-organized events...")
        
        filter_prompt = f"""You are a student life analyst for {campus_name}.
        
From the following event listings, extract ONLY the events that are:
1. Student-organized (not faculty lectures or admin events)
2. Social, cultural, or community-focused
3. Have clear organizer information

EXCLUDE: Academic deadlines, faculty lectures, varsity sports games, administrative meetings.

Return a JSON list of student events in this format:
[
  {{
    "event_name": "Late Night Pancakes",
    "date": "October 2024",
    "organization": "Residence Hall Council",
    "description": "Free pancakes in the dining hall...",
    "organizer_info": "Contact Sarah at sarah@university.edu"
  }}
]

EVENT CONTENT:
{event_corpus[:12000]}

Return ONLY valid JSON - no other text."""

        try:
            response = self.model.generate_content(filter_prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "[" in response_text and "]" in response_text:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                json_text = response_text[start:end]
            else:
                json_text = response_text
            
            events = json.loads(json_text)
            print(f"✅ Found {len(events)} student-organized events")
            return events
            
        except Exception as e:
            print(f"❌ Event filtering failed: {e}")
            return []
    
    def extract_event_organizers(self, student_events: List[Dict], campus_name: str) -> List[Dict]:
        """Step 4: Extract specific organizer contact information"""
        print("📧 Extracting event organizer contacts...")
        
        events_text = json.dumps(student_events, indent=2)
        
        extractor_prompt = f"""You are a talent sourcing specialist for {campus_name}.

From the following student events, extract the organizer contact information.
Focus on finding the actual student who planned each event.

Look for:
- Contact Person names
- Email addresses (especially @university.edu)
- Phone numbers
- Organization leadership roles

Return a JSON list of organizers:
[
  {{
    "name": "Sarah Johnson",
    "email": "sarah.johnson@university.edu", 
    "organization": "Residence Hall Council",
    "role": "Event Coordinator",
    "recent_event": "Late Night Pancakes",
    "event_date": "October 2024"
  }}
]

STUDENT EVENTS:
{events_text}

Extract up to 5 organizers. Return ONLY valid JSON - no other text."""

        try:
            response = self.model.generate_content(extractor_prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "[" in response_text and "]" in response_text:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                json_text = response_text[start:end]
            else:
                json_text = response_text
            
            organizers = json.loads(json_text)
            
            # Clean up and validate organizers
            valid_organizers = []
            for org in organizers:
                if org.get("email") and "@" in org.get("email", ""):
                    valid_organizers.append(org)
            
            print(f"✅ Extracted {len(valid_organizers)} event organizer contacts")
            return valid_organizers
            
        except Exception as e:
            print(f"❌ Organizer extraction failed: {e}")
            return []


def test_event_intelligence():
    """Quick test of the Event Intelligence Engine"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found in environment")
        return
    
    engine = EventIntelligenceEngine(gemini_key)
    result = engine.run("University of Alabama")
    
    print("\n🎪 EVENT INTELLIGENCE RESULTS:")
    print("="*50)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_event_intelligence()
