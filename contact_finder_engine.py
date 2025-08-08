import os
import time
import json
import re
from typing import Dict, List, Optional
import google.generativeai as genai
from tavily import TavilyClient


class ContactFinderEngine:
    """Relentless Contact Bot - Four-step workflow to find any organization's contact info."""
    
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
                print(f"🤖 Contact Finder Engine: {model_name}")
                return model
            except Exception as e:
                print(f"Failed to init {model_name}: {e}")
                continue
        else:
            raise RuntimeError("Failed to initialize Gemini model")

    def _safe_tavily_search(self, query: str, max_results: int = 5) -> Dict:
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
        import re
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        return None

    def step1_homepage_hunter(self, entity_name: str, campus_name: str) -> Optional[str]:
        """Step 1: Find the single best homepage URL for the entity."""
        print(f"🔍 STEP 1 - HOMEPAGE HUNTER: {entity_name}")
        
        # Optimized precision queries (reduced from 4 to 2)
        homepage_queries = [
            f'site:.edu "{entity_name}" {campus_name} contact',
            f'"{entity_name}" {campus_name} email leadership staff official'
        ]
        
        # Blacklisted domains - never the actual homepage
        blacklisted_domains = [
            'wikipedia.org', 'en.wikipedia.org', 'facebook.com', 'twitter.com', 
            'linkedin.com', 'instagram.com', 'youtube.com', 'reddit.com',
            'campustours.com', 'collegeconfidential.com', 'niche.com',
            'collegeboard.org', 'princetonreview.com'
        ]
        
        for query in homepage_queries:
            try:
                results = self._safe_tavily_search(query, max_results=8)
                for r in results.get("results", []):
                    url = r.get("url", "").lower()
                    title = r.get("title", "").lower()
                    content = r.get("content", "").lower()
                    
                    # Skip blacklisted domains
                    if any(domain in url for domain in blacklisted_domains):
                        continue
                    
                    # Strongly prefer .edu domains with entity mentions
                    if ".edu" in url:
                        entity_keywords = entity_name.lower().split()
                        if any(keyword in title or keyword in url for keyword in entity_keywords):
                            homepage_url = r.get("url", "")
                            print(f"✅ Found homepage: {homepage_url}")
                            return homepage_url
                    
                    # Accept high-quality non-.edu if it has contact signals
                    entity_keywords = entity_name.lower().split()
                    if (any(keyword in title for keyword in entity_keywords) and 
                        any(term in content for term in ["contact", "email", "editor", "staff", "leadership"])):
                        homepage_url = r.get("url", "")
                        print(f"✅ Found homepage (non-.edu): {homepage_url}")
                        return homepage_url
                        
                time.sleep(0.3)  # Rate limiting
            except Exception as e:
                print(f"⚠️ Homepage query failed: {e}")
                continue
        
        print(f"❌ Could not find homepage for {entity_name}")
        return None

    def step2_link_analyst(self, homepage_url: str) -> List[str]:
        """Step 2: Analyze homepage links to find the most promising contact paths."""
        print(f"🔗 STEP 2 - LINK ANALYST: {homepage_url}")
        
        try:
            # Get homepage content to extract links
            homepage_result = self._safe_tavily_search(f"site:{homepage_url}", max_results=1)
            if not homepage_result.get("results"):
                print("❌ Could not scrape homepage for links")
                return []
            
            homepage_content = homepage_result["results"][0].get("content", "")
            
            # Extract URLs from content using regex (simple approach)
            # Look for common link patterns in scraped content
            url_patterns = re.findall(r'https?://[^\s<>"]+', homepage_content)
            
            # Also look for relative paths mentioned in content
            relative_patterns = re.findall(r'/[a-zA-Z0-9/_-]*(?:contact|about|staff|leadership|roster|officers|masthead|editorial|team)[a-zA-Z0-9/_-]*', homepage_content, re.IGNORECASE)
            
            # Combine and clean URLs
            base_domain = '/'.join(homepage_url.split('/')[:3])
            all_links = url_patterns + [base_domain + path for path in relative_patterns]
            
            # Remove duplicates and filter
            unique_links = list(set(all_links))
            
            # AI Link Analysis
            links_text = "\n".join(unique_links[:20])  # Limit to prevent overflow
            
            link_analyst_prompt = f"""You are a web navigation expert. From the following list of URLs found on {homepage_url}, identify the top 3 links most likely to contain contact information for student leadership.

Prioritize links with keywords like:
- contact, about, staff, leadership, roster, officers, masthead
- editorial, team, directory, people, meet

URL List:
{links_text}

Return ONLY a JSON list of the 3 best URLs:
["url1", "url2", "url3"]

If fewer than 3 good URLs exist, return what you have. If none are good, return an empty list."""

            response = self.model.generate_content(link_analyst_prompt)
            result = self._parse_json(response.text)
            
            if isinstance(result, list):
                promising_urls = result[:3]
                print(f"✅ Link Analyst found {len(promising_urls)} promising paths")
                for url in promising_urls:
                    print(f"   📍 {url}")
                return promising_urls
            else:
                print("⚠️ Link analysis failed, using fallback strategy")
                # Fallback: return URLs with contact keywords
                contact_urls = [url for url in unique_links if any(keyword in url.lower() for keyword in ['contact', 'about', 'staff', 'leadership'])]
                return contact_urls[:3]
                
        except Exception as e:
            print(f"❌ Link analysis failed: {e}")
            return []

    def step3_targeted_scraper(self, promising_urls: List[str]) -> str:
        """Step 3: Scrape the promising URLs to create a high-signal corpus."""
        print(f"📄 STEP 3 - TARGETED SCRAPER: {len(promising_urls)} URLs")
        
        contact_corpus = []
        
        for url in promising_urls:
            try:
                print(f"   📥 Scraping: {url[:60]}...")
                result = self._safe_tavily_search(f"site:{url}", max_results=1)
                
                if result.get("results"):
                    content = result["results"][0].get("content", "")
                    if content:
                        contact_corpus.append(f"=== URL: {url} ===\n{content[:3000]}")
                        
                time.sleep(0.2)  # Rate limiting
            except Exception as e:
                print(f"⚠️ Failed to scrape {url}: {e}")
                continue
        
        combined_corpus = "\n\n".join(contact_corpus)
        print(f"✅ Created corpus: {len(combined_corpus)} characters from {len(contact_corpus)} pages")
        
        return combined_corpus

    def step4_final_extractor(self, corpus: str, entity_name: str) -> Dict:
        """Step 4: Extract contact information from the high-signal corpus."""
        print(f"🎯 STEP 4 - FINAL EXTRACTOR")
        
        if not corpus or len(corpus) < 100:
            return {
                "organization_name": entity_name,
                "leader_name": None,
                "leader_title": None,
                "contact_email": None,
                "phone": None,
                "error": "Insufficient content for extraction"
            }
        
        extractor_prompt = f"""You are an aggressive data extraction specialist. Your ONLY job is to find a person's name and contact email from the text below.

PRIORITY 1: Find a person with a leadership title (President, Editor-in-Chief, Chair, Coordinator, Director, Manager) and their direct email (@domain.edu or @domain.org).

PRIORITY 2: If no specific leader is found, find a general contact email (info@, contact@, editor@, hello@).

BE RELENTLESS: 
- Scour the entire text for ANY email address pattern
- Check for patterns like "firstname dot lastname at domain" or "firstname.lastname@domain"
- Look for staff directories, contact pages, about sections
- Find phone numbers if available

CRITICAL: Look for emails related to "{entity_name}" specifically.

Text Content:
{corpus[:15000]}

Based ONLY on the text provided, return a single JSON object:
{{
  "organization_name": "{entity_name}",
  "leader_name": "First Last",
  "leader_title": "Position Title", 
  "contact_email": "email@domain.edu",
  "phone": "phone number"
}}

If a field is not found, return null. BE AGGRESSIVE - find ANY email that might work."""

        try:
            response = self.model.generate_content(extractor_prompt)
            result = self._parse_json(response.text)
            
            if result and isinstance(result, dict):
                # Ensure organization name is set
                if not result.get("organization_name"):
                    result["organization_name"] = entity_name
                    
                contact_email = result.get("contact_email")
                leader_name = result.get("leader_name")
                
                if contact_email and "@" in contact_email:
                    print(f"🎉 EXTRACTION SUCCESS: {leader_name or 'Contact'} ({contact_email})")
                    return result
                else:
                    print("⚠️ No email found in extraction")
                    return {
                        "organization_name": entity_name,
                        "leader_name": result.get("leader_name"),
                        "leader_title": result.get("leader_title"),
                        "contact_email": None,
                        "phone": result.get("phone"),
                        "error": "No email extracted"
                    }
            else:
                print("❌ Extraction parsing failed")
                return {
                    "organization_name": entity_name,
                    "leader_name": None,
                    "leader_title": None,
                    "contact_email": None,
                    "phone": None,
                    "error": "Failed to parse extraction result"
                }
                
        except Exception as e:
            print(f"❌ Final extraction failed: {e}")
            return {
                "organization_name": entity_name,
                "leader_name": None,
                "leader_title": None,
                "contact_email": None,
                "phone": None,
                "error": str(e)
            }

    def run(self, entity_name: str, campus_name: str) -> Dict:
        """Main workflow: Hunt, Analyze, Scrape, Extract."""
        print(f"\n🤖 RELENTLESS CONTACT BOT: {entity_name}")
        print("="*70)
        
        # Step 1: Find homepage
        homepage_url = self.step1_homepage_hunter(entity_name, campus_name)
        if not homepage_url:
            return {
                "organization_name": entity_name,
                "leader_name": None,
                "leader_title": None,
                "contact_email": None,
                "phone": None,
                "error": "Homepage not found"
            }
        
        # Step 2: Analyze links
        promising_urls = self.step2_link_analyst(homepage_url)
        if not promising_urls:
            # Fallback: use homepage itself
            promising_urls = [homepage_url]
        
        # Step 3: Scrape targeted content
        corpus = self.step3_targeted_scraper(promising_urls)
        
        # Step 4: Extract contact info
        result = self.step4_final_extractor(corpus, entity_name)
        
        print(f"🤖 CONTACT BOT COMPLETE: {'SUCCESS' if result.get('contact_email') else 'FAILED'}")
        return result
