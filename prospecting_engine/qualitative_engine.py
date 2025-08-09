"""
Qualitative Engine - "The Social Leader Contact Finder"
Biased talent scout designed to find high-signal community leaders aligned with our ethos.
"""

import os
import time
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai

from tools import tool_web_search, tool_crawl_for_contacts
from prompts import DIRECTORY_HUNTER_PROMPT, SOCIAL_LEADER_EXTRACTION_PROMPT


class QualitativeEngine:
    """Opinionated talent scout for finding social leaders."""
    
    def __init__(self, gemini_api_key: str):
        self.model = self._init_gemini(gemini_api_key)

    def _init_gemini(self, api_key: str):
        """Initialize Gemini model with fallback options."""
        genai.configure(api_key=api_key)
        for model_name in ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                _ = model.generate_content("test")
                print(f"👥 Qualitative Engine: {model_name}")
                return model
            except Exception as e:
                print(f"Failed to init {model_name}: {e}")
                continue
        raise RuntimeError("Failed to initialize any Gemini model")

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Parse JSON from AI response with multiple fallback strategies."""
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
        json_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
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

    def hunt_for_directories(self, campus_name: str) -> List[str]:
        """
        Step 1: Efficient search for student contact directories.
        
        Returns list of promising URLs for contact extraction.
        """
        print(f"\n🔍 HUNTING FOR DIRECTORIES: {campus_name}")
        
        # More targeted search - focus on the exact university with better filtering
        campus_domain = campus_name.lower().replace("university of", "").replace("the ", "").replace(" university", "").replace(" ", "").replace("college", "")
        
        # Handle special cases for domain extraction
        domain_mapping = {
            "alabama": "ua",
            "tulaneoflouisiana": "tulane", 
            "texaschristian": "tcu"
        }
        campus_domain = domain_mapping.get(campus_domain, campus_domain)
        
        # Try multiple targeted queries with better specificity
        targeted_queries = [
            f'"{campus_name}" student government officers contact site:{campus_domain}.edu',
            f'"{campus_name}" student government roster site:.edu -site:wikipedia.org',
            f'site:{campus_domain}.edu student government contact directory'
        ]
        
        all_promising_urls = []
        
        # Try each targeted query
        for i, query in enumerate(targeted_queries, 1):
            print(f"   🔍 Query {i}: {query[:70]}...")
            
            try:
                result = tool_web_search(query, max_results=4)
                
                if result.get("sources"):
                    for url in result["sources"]:
                        # Filter out unwanted domains
                        url_lower = url.lower()
                        if any(bad_domain in url_lower for bad_domain in ["wikipedia", "facebook", "twitter", "linkedin", "instagram"]):
                            continue
                        
                        # Prioritize .edu domains and relevant keywords
                        if ".edu" in url_lower and any(keyword in url_lower for keyword in ["government", "sga", "student", "contact", "directory", "officers"]):
                            all_promising_urls.append(url)
                        elif ".edu" in url_lower:  # Any .edu is better than non-.edu
                            all_promising_urls.append(url)
                
                if len(all_promising_urls) >= 5:  # Stop early if we have enough
                    break
                    
                time.sleep(1.5)  # Longer pause to avoid rate limits
                
            except Exception as e:
                print(f"   ⚠️ Query {i} failed: {e}")
        
        # Remove duplicates while preserving order
        unique_urls = []
        for url in all_promising_urls:
            if url not in unique_urls:
                unique_urls.append(url)
        
        print(f"   ✅ Found {len(unique_urls)} promising directories")
        return unique_urls[:5] if unique_urls else []

    def crawl_and_extract(self, promising_urls: List[str], campus_name: str) -> List[Dict]:
        """
        Steps 2 & 3: Crawl promising URLs and extract social leader contacts.
        
        Returns list of social leader contacts with details.
        """
        print(f"\n📄 CRAWLING & EXTRACTING CONTACTS")
        
        if not promising_urls:
            print("   ❌ No URLs to crawl")
            return []
        
        # Optimized: Crawl fewer URLs but get better content
        all_contact_content = []
        
        for url in promising_urls[:2]:  # Reduced to top 2 URLs to save API calls
            print(f"   📥 Crawling: {url[:60]}...")
            try:
                contact_content = tool_crawl_for_contacts(url, campus_name)
                if contact_content:
                    all_contact_content.append(contact_content)
                time.sleep(2.0)  # Longer wait time for contact crawling
            except Exception as e:
                print(f"   ⚠️ Crawling failed: {e}")
        
        if not all_contact_content:
            print("   ❌ No contact content extracted")
            return []
        
        # Combine all crawled content
        combined_content = "\n\n".join(all_contact_content)[:15000]
        
        # Extract social leaders using AI
        extraction_prompt = SOCIAL_LEADER_EXTRACTION_PROMPT.format(
            campus_name=campus_name,
            search_content=combined_content
        )
        
        try:
            response = self.model.generate_content(extraction_prompt)
            result = self._parse_json(response.text)
            
            if result and "student_contacts" in result:
                contacts = result["student_contacts"]
                print(f"   ✅ Extracted {len(contacts)} student contacts")
                return contacts
            elif result and "social_leaders" in result:  # Fallback for old format
                leaders = result["social_leaders"]
                print(f"   ✅ Extracted {len(leaders)} student contacts (legacy format)")
                return leaders
            else:
                print("   ⚠️ No contacts extracted from content")
                return []
                
        except Exception as e:
            print(f"   ❌ Leader extraction failed: {e}")
            return []

    def run(self, campus_name: str) -> Dict:
        """
        Main qualitative analysis workflow.
        
        Executes the "Hunt for Directories" strategy to find social leaders.
        
        Returns:
            Dict with social_leaders list and metadata
        """
        print(f"\n👥 SOCIAL LEADER CONTACT FINDER: {campus_name}")
        print("="*60)
        
        # Step 1: Hunt for directories
        promising_urls = self.hunt_for_directories(campus_name)
        
        if not promising_urls:
            return {
                "social_leaders": [],
                "directories_found": 0,
                "error": "No promising directories found"
            }
        
        # Steps 2 & 3: Crawl and extract
        student_contacts = self.crawl_and_extract(promising_urls, campus_name)
        
        # Analyze results
        contacts_with_email = len([c for c in student_contacts if c.get("email") and "@" in c["email"]])
        
        result = {
            "student_contacts": student_contacts,
            "directories_found": len(promising_urls),
            "contacts_extracted": len(student_contacts),
            "contacts_with_email": contacts_with_email,
            "success_rate": f"{contacts_with_email}/{len(student_contacts)}" if student_contacts else "0/0"
        }
        
        print(f"\n👥 STUDENT CONTACT FINDER COMPLETE")
        print(f"   Directories: {len(promising_urls)}")
        print(f"   Contacts Found: {len(student_contacts)}")
        print(f"   With Email: {contacts_with_email}")
        
        return result
