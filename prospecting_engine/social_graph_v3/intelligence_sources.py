import os
import time
import json
from typing import List, Dict, Any

import google.generativeai as genai

# Optional imports guarded for environments without keys
try:
    import praw
except Exception:
    praw = None

import requests


def _sleep_throttle(seconds: float = 1.0):
    time.sleep(seconds)


class RedditSource:
    """HUMINT source using PRAW. Minimizes calls by using time filters and small limits."""

    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.reddit = None
        if all(os.getenv(k) for k in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"]) and praw:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT"),
            )

    def get_humint_report(self, subreddit_name: str) -> Dict[str, Any]:
        if not self.reddit:
            return {"error": "Reddit credentials not configured"}

        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts_data = []
            # Top from last 3 months: use 'top' with time_filter='year' and limit small
            for post in subreddit.top(time_filter='year', limit=50):
                posts_data.append({
                    "title": post.title,
                    "score": post.score,
                    "id": post.id
                })
            _sleep_throttle(0.5)

            comments_text = []
            for pd in posts_data[:15]:  # limit comment fetches to reduce calls
                submission = self.reddit.submission(id=pd["id"])
                submission.comments.replace_more(limit=0)
                for c in submission.comments[:10]:  # cap comments
                    comments_text.append(c.body[:500])
                _sleep_throttle(0.2)

            corpus = json.dumps({"posts": posts_data, "comments": comments_text})[:15000]
            prompt = f"""Analyze these Reddit discussions. Identify the 5 most influential/helpful user accounts and the 10 most frequently discussed student organizations and local places. Summarize the overall vibe in two sentences.

RETURN JSON:
{{
  "top_users": ["username1", "username2", "username3", "username4", "username5"],
  "mentioned_orgs": ["..."],
  "mentioned_places": ["..."],
  "subreddit_vibe": "..."
}}

CONTENT:
{corpus}

Return ONLY JSON."""
            resp = self.model.generate_content(prompt)
            return self._parse_json(resp.text)
        except Exception as e:
            return {"error": str(e)}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            # Try fenced JSON
            if "```json" in text:
                try:
                    chunk = text.split("```json")[1].split("```", 1)[0]
                    return json.loads(chunk)
                except Exception:
                    pass
            # Fallback
            return {"raw": text[:2000]}


class PhantomBusterClient:
    """PhantomBuster client with proper API integration."""

    def __init__(self):
        self.api_key = os.getenv("PHANTOMBUSTER_API_KEY")
        self.base_v1 = "https://api.phantombuster.com/api/v1"
        self.base_v2 = "https://api.phantombuster.com/api/v2"

    def get_available_agents(self) -> Dict[str, Any]:
        """Get list of available agents in the account."""
        if not self.api_key:
            return {"error": "PHANTOMBUSTER_API_KEY not set"}
        try:
            headers = {"X-Phantombuster-Key-1": self.api_key}
            resp = requests.get(f"{self.base_v2}/agents/fetch-all", headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def launch_agent(self, agent_id: str, argument: Dict[str, Any] = None) -> Dict[str, Any]:
        """Launch a specific agent with arguments."""
        if not self.api_key:
            return {"error": "PHANTOMBUSTER_API_KEY not set"}
        try:
            headers = {"X-Phantombuster-Key-1": self.api_key}
            payload = {"id": agent_id}
            if argument:
                payload["argument"] = argument
                
            resp = requests.post(f"{self.base_v2}/agents/launch", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_agent_output(self, agent_id: str) -> Dict[str, Any]:
        """Get the output/results from an agent."""
        if not self.api_key:
            return {"error": "PHANTOMBUSTER_API_KEY not set"}
        try:
            headers = {"X-Phantombuster-Key-1": self.api_key}
            resp = requests.get(f"{self.base_v2}/agents/fetch-output?id={agent_id}", headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def run_phantom(self, phantom_name: str, argument: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - try to find and run agent by name/type."""
        # First get available agents
        agents = self.get_available_agents()
        if "error" in agents:
            return agents
            
        # Look for agents that might match what we want
        matching_agents = []
        if isinstance(agents, dict) and "data" in agents:
            for agent in agents["data"]:
                agent_name = agent.get("name", "").lower()
                if any(keyword in agent_name for keyword in ["instagram", "google", "maps", "social"]):
                    matching_agents.append(agent)
        
        if not matching_agents:
            return {"error": f"No matching agents found for {phantom_name}", "available_agents": len(agents.get("data", []))}
            
        # Use the first matching agent
        agent_id = matching_agents[0].get("id")
        if not agent_id:
            return {"error": "Agent ID not found"}
            
        return self.launch_agent(agent_id, argument)


class SocialMediaSource:
    """IMINT via PhantomBuster. Uses two phantoms with strict limits."""

    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.ph = PhantomBusterClient()

    def get_imint_report(self, campus_name: str, instagram_handles: List[str] = None) -> Dict[str, Any]:
        """Get Instagram Intelligence Report - both via PhantomBuster and fallback search."""
        try:
            # Strategy 1: PhantomBuster Instagram data (if configured)
            phantom_data = self._get_phantom_instagram_data(instagram_handles or [])
            
            # Strategy 2: Fallback web search for Instagram social proof
            search_data = self._search_instagram_social_proof(campus_name)
            
            # Combine and analyze all data
            combined_data = {
                "phantom_profiles": phantom_data,
                "search_intelligence": search_data
            }
            
            corpus = json.dumps(combined_data)[:15000]
            
            prompt = f"""Analyze Instagram intelligence for {campus_name}.

TASK: Identify student organizations with strong social proof and visual engagement.

DATA: {corpus}

Extract:
1. Organizations with high follower counts (1000+ followers)
2. Most engaging Instagram content/accounts
3. Visual hotspots frequently tagged on campus
4. Influencer students or organizations

RETURN JSON: {{
  "verified_orgs": [{{"name": "...", "handle": "@...", "follower_estimate": "...", "engagement_level": "high/medium/low"}}],
  "campus_hotspots": [{{"location": "...", "tag_frequency": "high/medium/low", "visual_appeal": "..."}}],
  "social_influencers": [{{"handle": "@...", "influence_type": "...", "follower_estimate": "..."}}],
  "summary": "2-3 sentence summary of Instagram landscape"
}}

Return ONLY JSON."""
            
            resp = self.model.generate_content(prompt)
            return self._parse_json(resp.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_phantom_instagram_data(self, handles: List[str]) -> Dict[str, Any]:
        """Get PhantomBuster Instagram data if available."""
        if not self.ph.api_key:
            return {"status": "PhantomBuster not configured"}
        
        if not handles:
            return {"status": "No Instagram handles provided"}
        
        try:
            # First check what agents are available
            agents = self.ph.get_available_agents()
            print(f"PhantomBuster agents available: {len(agents.get('data', []))} agents")
            
            # Try to find Instagram-related agents
            instagram_agents = []
            if isinstance(agents, dict) and "data" in agents:
                for agent in agents["data"]:
                    agent_name = agent.get("name", "").lower()
                    if "instagram" in agent_name:
                        instagram_agents.append(agent)
            
            if instagram_agents:
                # Use the first Instagram agent found
                agent_id = instagram_agents[0].get("id")
                print(f"Using Instagram agent: {instagram_agents[0].get('name')}")
                
                # Prepare Instagram URLs
                instagram_urls = [f"https://instagram.com/{h.replace('@', '')}" for h in handles[:3]]
                
                result = self.ph.launch_agent(agent_id, {
                    "profileUrls": instagram_urls,
                    "sessionCookie": "",  # May need session for private data
                    "maxProfiles": 3
                })
                
                _sleep_throttle(2.0)  # Give agent time to run
                
                # Try to get results
                if result.get("data", {}).get("containerId"):
                    output = self.ph.get_agent_output(agent_id)
                    return {"phantom_data": output, "agent_used": instagram_agents[0].get("name")}
                
                return result
            else:
                return {"error": "No Instagram agents found in PhantomBuster account", "total_agents": len(agents.get("data", []))}
                
        except Exception as e:
            return {"error": f"PhantomBuster Instagram failed: {e}"}
    
    def _search_instagram_social_proof(self, campus_name: str) -> Dict[str, Any]:
        """Fallback web search for Instagram data."""
        try:
            # Import the search function from parent directory
            import sys
            import os
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.append(parent_dir)
            from tools import tool_web_search
            
            query = f'"{campus_name}" student organizations Instagram followers engagement social media'
            result = tool_web_search(query, max_results=3)
            
            return {
                "search_content": result.get("content", "")[:3000],
                "urls_found": result.get("urls", [])
            }
        except Exception as e:
            return {"error": f"Search fallback failed: {e}"}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            if "```json" in text:
                try:
                    chunk = text.split("```json")[1].split("```", 1)[0]
                    return json.loads(chunk)
                except Exception:
                    pass
            return {"raw": text[:2000]}


class GeospatialSource:
    """GEOINT via PhantomBuster Google Maps Search Export with strict radius."""

    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.ph = PhantomBusterClient()

    def get_geoint_report(self, campus_name: str) -> Dict[str, Any]:
        """Get comprehensive geospatial intelligence with PhantomBuster + web search."""
        try:
            # Strategy 1: PhantomBuster Google Maps data (if configured)
            phantom_maps = self._get_phantom_maps_data(campus_name)
            
            # Strategy 2: Web search for local business intelligence
            search_maps = self._search_local_intelligence(campus_name)
            
            # Combine and analyze
            combined_geo_data = {
                "phantom_maps": phantom_maps,
                "search_intelligence": search_maps
            }
            
            corpus = json.dumps(combined_geo_data)[:15000]
            
            prompt = f"""Analyze geospatial intelligence for {campus_name}.

TASK: Map the social geography around campus.

DATA: {corpus}

Extract third places with verified data:
1. Student-popular venues (cafes, bars, restaurants)
2. Ratings and review sentiment 
3. Distance from campus
4. Peak hours/student activity times
5. Social density indicators

RETURN JSON: {{
  "verified_third_places": [{{
    "name": "...", 
    "type": "cafe/bar/restaurant/park", 
    "rating": 4.2, 
    "address": "...",
    "distance_from_campus": "0.3 miles",
    "student_popularity": "high/medium/low",
    "peak_times": "...",
    "social_context": "why students go here"
  }}],
  "campus_geography": {{
    "walkability_score": "high/medium/low",
    "social_density": "concentrated/dispersed", 
    "third_place_proximity": "1-5 scale"
  }},
  "summary": "2-3 sentence geographical social analysis"
}}

Return ONLY JSON."""
            
            resp = self.model.generate_content(prompt)
            return self._parse_json(resp.text)
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_phantom_maps_data(self, campus_name: str) -> Dict[str, Any]:
        """Get PhantomBuster Google Maps data if available."""
        if not self.ph.api_key:
            return {"status": "PhantomBuster not configured"}
        
        try:
            # Check available agents for Google Maps functionality
            agents = self.ph.get_available_agents()
            
            # Look for Google Maps or location-related agents
            maps_agents = []
            if isinstance(agents, dict) and "data" in agents:
                for agent in agents["data"]:
                    agent_name = agent.get("name", "").lower()
                    if any(keyword in agent_name for keyword in ["google", "maps", "location", "search"]):
                        maps_agents.append(agent)
            
            if maps_agents:
                # Use the first maps-related agent
                agent_id = maps_agents[0].get("id")
                print(f"Using Maps agent: {maps_agents[0].get('name')}")
                
                # Prepare search queries for places near campus
                search_queries = [
                    f"cafes near {campus_name}",
                    f"restaurants near {campus_name}",
                    f"bars near {campus_name}"
                ]
                
                result = self.ph.launch_agent(agent_id, {
                    "searches": search_queries,
                    "maxResults": 50,
                    "radius": "2km"
                })
                
                _sleep_throttle(2.0)  # Give agent time to run
                
                # Try to get results
                if result.get("data", {}).get("containerId"):
                    output = self.ph.get_agent_output(agent_id)
                    return {"phantom_data": output, "agent_used": maps_agents[0].get("name")}
                
                return result
            else:
                return {"error": "No Google Maps agents found in PhantomBuster account", "total_agents": len(agents.get("data", []))}
            
        except Exception as e:
            return {"error": f"PhantomBuster Maps failed: {e}"}
    
    def _search_local_intelligence(self, campus_name: str) -> Dict[str, Any]:
        """Web search for local business and geography intelligence."""
        try:
            # Import the search function from parent directory
            import sys
            import os
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.append(parent_dir)
            from tools import tool_web_search
            
            searches = [
                f'"{campus_name}" student favorite restaurants cafes bars near campus',
                f'"{campus_name}" best places to study eat socialize walking distance',
                f'"{campus_name}" campus town walkability student life geography'
            ]
            
            all_content = []
            for query in searches:
                result = tool_web_search(query, max_results=2)
                if result.get("content"):
                    all_content.append(result["content"][:2000])
                _sleep_throttle(0.5)
            
            return {
                "search_content": "\n\n".join(all_content),
                "total_sources": len(all_content)
            }
            
        except Exception as e:
            return {"error": f"Search intelligence failed: {e}"}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            if "```json" in text:
                try:
                    chunk = text.split("```json")[1].split("```", 1)[0]
                    return json.loads(chunk)
                except Exception:
                    pass
            return {"raw": text[:2000]}
