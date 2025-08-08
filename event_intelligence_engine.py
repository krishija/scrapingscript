import os
import time
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from tavily import TavilyClient


class EventIntelligenceEngine:
    """Event Intelligence Engine - Systematic discovery of campus events and opportunities."""
    
    def __init__(self, gemini_api_key: str):
        self.tavily_client = self._init_tavily()
        self.model = self._init_gemini(gemini_api_key)

    def _init_tavily(self) -> TavilyClient:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY not set in environment")
        return TavilyClient(api_key=api_key)

    def _init_gemini(self, api_key: str):
        genai.configure(api_key=api_key)
        for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                _ = model.generate_content("ping")
                print(f"📅 Event Intelligence Engine: {model_name}")
                return model
            except Exception as e:
                print(f"Failed to init {model_name}: {e}")
                continue
        else:
            raise RuntimeError("Failed to initialize Gemini model")

    def _safe_tavily_search(self, query: str, max_results: int = 6) -> Dict:
        try:
            return self.tavily_client.search(query=query, search_depth="advanced", max_results=max_results)
        except Exception as e:
            print(f"⚠️ Tavily search failed for '{query}': {e}")
            return {"results": []}

    def _parse_json(self, text: str) -> Optional[Dict]:
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            try:
                return json.loads(text)
            except:
                pass
        if text.startswith('[') and text.endswith(']'):
            try:
                return json.loads(text)
            except:
                pass
        import re
        json_pattern = r'```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
        return None

    def discover_event_sources(self, campus_name: str) -> Dict[str, List[str]]:
        """Discover the Three Universal Event Sources for a campus."""
        print(f"🔍 DISCOVERING EVENT SOURCES: {campus_name}")
        
        campus_domain = campus_name.lower().replace(" ", "").replace("university", "").replace("college", "")
        
        # The Three Universal Event Sources
        source_queries = {
            "university_calendar": [
                f'site:{campus_domain}.edu events calendar upcoming',
                f'"{campus_name}" official events calendar',
                f'events.{campus_domain}.edu OR calendar.{campus_domain}.edu'
            ],
            "student_union": [
                f'site:{campus_domain}.edu student union activities events',
                f'"{campus_name}" student activities programming events',
                f'"{campus_name}" student center events schedule'
            ],
            "athletics": [
                f'site:{campus_domain}.edu athletics schedule games events',
                f'"{campus_name}" sports schedule upcoming games',
                f'athletics.{campus_domain}.edu OR sports.{campus_domain}.edu'
            ]
        }
        
        discovered_sources = {}
        
        for source_type, queries in source_queries.items():
            print(f"   🔍 Finding {source_type} sources...")
            sources = []
            
            for query in queries[:1]:  # Further reduced to 1 query per source type
                try:
                    results = self._safe_tavily_search(query, max_results=3)
                    for r in results.get("results", []):
                        url = r.get("url", "")
                        title = r.get("title", "").lower()
                        
                        # Prefer .edu domains with event-related content
                        if ".edu" in url and any(keyword in title for keyword in ["event", "calendar", "schedule", "activities"]):
                            sources.append(url)
                            
                    time.sleep(0.3)
                    
                except Exception as e:
                    print(f"⚠️ Source discovery failed: {e}")
                    continue
            
            # Remove duplicates
            discovered_sources[source_type] = list(set(sources))[:3]
            print(f"   ✅ Found {len(discovered_sources[source_type])} {source_type} sources")
        
        return discovered_sources

    def extract_events(self, event_sources: Dict[str, List[str]], campus_name: str) -> List[Dict]:
        """Extract events from discovered sources."""
        print(f"📅 EXTRACTING EVENTS FROM SOURCES")
        
        all_event_content = []
        
        # Scrape content from all sources
        for source_type, urls in event_sources.items():
            print(f"   📥 Scraping {source_type} events...")
            
            for url in urls:
                try:
                    results = self._safe_tavily_search(f"site:{url} events", max_results=2)
                    for r in results.get("results", []):
                        content = r.get("content", "")
                        if content and len(content) > 200:  # Filter out thin content
                            all_event_content.append(f"=== {source_type.upper()}: {url} ===\n{content[:2000]}")
                    
                    time.sleep(0.2)
                except Exception as e:
                    print(f"⚠️ Failed to scrape {url}: {e}")
                    continue
        
        if not all_event_content:
            print("❌ No event content found")
            return []
        
        # Combine all content
        combined_content = "\n\n".join(all_event_content)[:20000]
        
        # AI Event Extraction
        event_extraction_prompt = f"""You are an event intelligence specialist for Homie, a social app for college students. Extract upcoming events from the following campus event information for {campus_name}.

For each event you find, extract:
- event_name: The name/title of the event
- hosting_org: The organization hosting it (if mentioned)
- date: When it's happening (if specified)
- location: Where it's happening (if specified)
- event_type: Category (e.g., "Concert", "Sports", "Academic", "Social", "Career")

Focus on events that are:
1. Upcoming or recently announced
2. Student-focused or open to students
3. Have clear hosting organizations

Event Content:
{combined_content}

Return a JSON list of events:
[
  {{
    "event_name": "Spring Concert",
    "hosting_org": "Programming Board",
    "date": "April 15, 2024",
    "location": "Main Quad",
    "event_type": "Concert"
  }},
  {{
    "event_name": "Career Fair",
    "hosting_org": "Career Services",
    "date": "March 20, 2024", 
    "location": "Student Union",
    "event_type": "Career"
  }}
]

Extract up to 15 events. If dates are unclear, still include the event but note "TBD" for date."""

        try:
            response = self.model.generate_content(event_extraction_prompt)
            events = self._parse_json(response.text)
            
            if isinstance(events, list):
                print(f"✅ Extracted {len(events)} events")
                return events
            else:
                print("⚠️ Event extraction parsing failed")
                return []
                
        except Exception as e:
            print(f"❌ Event extraction failed: {e}")
            return []

    def tag_opportunities(self, events: List[Dict], diamond_orgs: List[Dict]) -> List[Dict]:
        """Tag events with GTM opportunity types."""
        print(f"🏷️ TAGGING OPPORTUNITIES: {len(events)} events")
        
        if not events:
            return []
        
        # Create diamond org names list for reference
        diamond_org_names = [org.get("name", "") for org in diamond_orgs]
        
        # Prepare events and diamond context for AI
        events_text = json.dumps(events, indent=2)
        diamond_text = json.dumps(diamond_org_names, indent=2)
        
        opportunity_tagger_prompt = f"""You are a Homie GTM strategist. For each event in the list, add a "homie_opportunity" tag based on our playbook.

GTM Opportunity Types:
- "Sponsorship Play": Major concerts, sporting events, large campus-wide events (high visibility)
- "Midterm Fuel Play": Study breaks, finals week events, academic support events (stress relief timing)
- "Targeted Friendship Fund": Events hosted by our diamond target organizations (direct outreach)
- "Community Building": Freshman orientation, club fairs, social mixers (recruitment opportunities)
- "No Opportunity": Events that don't fit our GTM strategy

Diamond Target Organizations (prioritize these):
{diamond_text}

Events List:
{events_text}

For each event, analyze:
1. The event type and scale
2. Whether it's hosted by a diamond target org
3. The strategic opportunity for Homie

Return the SAME list of events but with "homie_opportunity" added to each event:
[
  {{
    "event_name": "Spring Concert",
    "hosting_org": "Programming Board",
    "date": "April 15, 2024",
    "location": "Main Quad", 
    "event_type": "Concert",
    "homie_opportunity": "Sponsorship Play"
  }},
  ...
]"""

        try:
            response = self.model.generate_content(opportunity_tagger_prompt)
            tagged_events = self._parse_json(response.text)
            
            if isinstance(tagged_events, list):
                # Count opportunity types
                opportunity_counts = {}
                for event in tagged_events:
                    opp_type = event.get("homie_opportunity", "Unknown")
                    opportunity_counts[opp_type] = opportunity_counts.get(opp_type, 0) + 1
                
                print(f"✅ Tagged opportunities:")
                for opp_type, count in opportunity_counts.items():
                    print(f"   {opp_type}: {count} events")
                    
                return tagged_events
            else:
                print("⚠️ Opportunity tagging failed, returning untagged events")
                return events
                
        except Exception as e:
            print(f"❌ Opportunity tagging failed: {e}")
            return events

    def run(self, campus_name: str, diamond_orgs: List[Dict] = None) -> Dict:
        """Main workflow: Discover sources, extract events, tag opportunities."""
        print(f"\n📅 EVENT INTELLIGENCE ENGINE: {campus_name}")
        print("="*60)
        
        # Step 1: Discover event sources
        event_sources = self.discover_event_sources(campus_name)
        
        total_sources = sum(len(urls) for urls in event_sources.values())
        if total_sources == 0:
            return {
                "campus_name": campus_name,
                "event_sources": event_sources,
                "events": [],
                "analysis": {
                    "total_events": 0,
                    "opportunity_breakdown": {},
                    "error": "No event sources found"
                }
            }
        
        # Step 2: Extract events from sources
        events = self.extract_events(event_sources, campus_name)
        
        # Step 3: Tag with GTM opportunities
        if diamond_orgs:
            tagged_events = self.tag_opportunities(events, diamond_orgs)
        else:
            tagged_events = events
        
        # Analysis
        opportunity_breakdown = {}
        for event in tagged_events:
            opp_type = event.get("homie_opportunity", "Untagged")
            opportunity_breakdown[opp_type] = opportunity_breakdown.get(opp_type, 0) + 1
        
        print(f"\n📅 EVENT INTELLIGENCE COMPLETE")
        print(f"   Sources Found: {total_sources}")
        print(f"   Events Extracted: {len(tagged_events)}")
        print(f"   GTM Opportunities: {sum(v for k, v in opportunity_breakdown.items() if k != 'No Opportunity')}")
        
        return {
            "campus_name": campus_name,
            "event_sources": event_sources,
            "events": tagged_events,
            "analysis": {
                "total_events": len(tagged_events),
                "total_sources": total_sources,
                "opportunity_breakdown": opportunity_breakdown
            }
        }
