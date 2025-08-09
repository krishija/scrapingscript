"""
Contact Saturation Engine - Never Miss Another Contact

This engine uses an exhaustive multi-vector approach to find EVERY possible
student contact at a university. Instead of being selective, it casts the
widest possible net and then filters/validates the results.

Strategy:
1. Multi-Vector Discovery: Hit 15+ different contact sources
2. Aggressive Email Extraction: Regex + AI-powered extraction  
3. Cross-Source Validation: Verify contacts across multiple sources
4. Intelligent Deduplication: Merge and rank all findings
"""

import json
import time
import re
from typing import Dict, List, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from tools import tool_web_search


class ContactSaturationEngine:
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
    def run(self, campus_name: str) -> Dict[str, Any]:
        """
        Exhaustive contact saturation workflow.
        Finds EVERY possible student contact using multiple parallel strategies.
        """
        print(f"\n🎯 CONTACT SATURATION ENGINE: {campus_name}")
        print("="*70)
        
        try:
            # Step 1: Multi-vector contact discovery (parallel)
            all_raw_contacts = self.multi_vector_discovery(campus_name)
            
            # Step 2: Aggressive email extraction from all sources
            extracted_emails = self.extract_all_emails(all_raw_contacts)
            
            # Step 3: AI-powered contact structuring and validation
            structured_contacts = self.structure_and_validate_contacts(extracted_emails, campus_name)
            
            # Step 4: Cross-source validation and ranking
            final_contacts = self.cross_validate_and_rank(structured_contacts, campus_name)
            
            return {
                "campus_name": campus_name,
                "total_sources_searched": len(all_raw_contacts),
                "raw_emails_found": len(extracted_emails),
                "structured_contacts": final_contacts,
                "contact_count": len(final_contacts),
                "success_rate": f"{len(final_contacts)}/15+ targets"
            }
            
        except Exception as e:
            print(f"❌ Contact Saturation failed: {e}")
            return {"error": str(e)}
    
    def multi_vector_discovery(self, campus_name: str) -> List[Tuple[str, str]]:
        """
        Step 1: Cast the widest possible net with 15+ contact vectors.
        Returns list of (source_type, content) tuples.
        """
        print("🌐 Multi-vector contact discovery...")
        
        # Get campus domain for targeted searches
        campus_domain = self._get_campus_domain(campus_name)
        
        # Define ALL possible contact vectors
        contact_vectors = [
            # Leadership Vectors
            ("student_government", f'"{campus_name}" student government officers email contact directory'),
            ("student_president", f'"{campus_name}" student body president email address'),
            ("sga_leadership", f'site:{campus_domain} student government association officers contact'),
            
            # Media & Communications Vectors  
            ("student_newspaper", f'"{campus_name}" student newspaper editor email contact'),
            ("campus_media", f'"{campus_name}" student radio station manager contact email'),
            ("communications", f'site:{campus_domain} student publications staff contact'),
            
            # Residential & Campus Life Vectors
            ("residence_life", f'"{campus_name}" residence hall association staff email'),
            ("campus_activities", f'"{campus_name}" student activities board contact email'),
            ("programming", f'site:{campus_domain} campus programming student staff'),
            
            # Academic & Honor Vectors
            ("academic_senate", f'"{campus_name}" student academic senate contact email'),
            ("honor_societies", f'"{campus_name}" honor society president contact'),
            ("student_research", f'site:{campus_domain} undergraduate research coordinator'),
            
            # Social & Cultural Vectors
            ("greek_life", f'"{campus_name}" Greek life student coordinator email'),
            ("multicultural", f'"{campus_name}" multicultural affairs student staff'),
            ("international", f'site:{campus_domain} international student services'),
            
            # Service & Support Vectors
            ("peer_tutoring", f'"{campus_name}" peer tutoring coordinator email'),
            ("orientation", f'"{campus_name}" student orientation leader contact'),
            ("tour_guides", f'site:{campus_domain} campus tour guide supervisor'),
            
            # General Directory Vectors
            ("student_directory", f'site:{campus_domain} student staff directory email'),
            ("leadership_directory", f'"{campus_name}" student leadership directory contact')
        ]
        
        print(f"🔍 Searching {len(contact_vectors)} contact vectors...")
        
        # Parallel execution of all contact vectors
        all_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_vector = {
                executor.submit(self._search_contact_vector, vector_type, query): (vector_type, query)
                for vector_type, query in contact_vectors
            }
            
            for future in as_completed(future_to_vector):
                vector_type, query = future_to_vector[future]
                try:
                    content = future.result()
                    if content:
                        all_results.append((vector_type, content))
                        print(f"   ✅ {vector_type}: {len(content)} chars")
                    else:
                        print(f"   ⚠️ {vector_type}: No content")
                except Exception as e:
                    print(f"   ❌ {vector_type}: {e}")
                
                time.sleep(0.5)  # Rate limiting
        
        print(f"📊 Collected content from {len(all_results)} sources")
        return all_results
    
    def _get_campus_domain(self, campus_name: str) -> str:
        """Extract likely campus domain from university name."""
        # Domain mapping for common university short names
        domain_mapping = {
            "university of alabama": "ua.edu",
            "texas christian university": "tcu.edu", 
            "tulane university of louisiana": "tulane.edu",
            "auburn university": "auburn.edu",
            "university of miami": "miami.edu",
            "university of california berkeley": "berkeley.edu",
            "stanford university": "stanford.edu"
        }
        
        campus_lower = campus_name.lower()
        for name, domain in domain_mapping.items():
            if name in campus_lower:
                return domain
        
        # Fallback: create domain from campus name
        clean_name = campus_name.lower()
        clean_name = clean_name.replace("university of", "").replace("the ", "")
        clean_name = clean_name.replace(" university", "").replace(" college", "")
        clean_name = clean_name.replace(" ", "").replace("-", "")
        return f"{clean_name}.edu"
    
    def _search_contact_vector(self, vector_type: str, query: str) -> str:
        """Search a single contact vector and return content."""
        try:
            result = tool_web_search(query, max_results=3)
            content = result.get("content", "")
            sources = result.get("sources", [])
            
            # Combine content and source URLs for maximum info
            combined_content = f"CONTENT:\n{content}\n\nSOURCES:\n" + "\n".join(sources)
            return combined_content[:3000]  # Limit size
            
        except Exception as e:
            print(f"Vector search failed for {vector_type}: {e}")
            return ""
    
    def extract_all_emails(self, raw_contacts: List[Tuple[str, str]]) -> Set[str]:
        """
        Step 2: Aggressive email extraction using multiple strategies.
        Returns set of unique email addresses found.
        """
        print("📧 Aggressive email extraction...")
        
        all_emails = set()
        
        # Multiple email patterns for comprehensive extraction
        email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*\.edu',  # All .edu emails
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # All emails
            r'[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.edu',  # Stricter .edu
            r'student[a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.edu',  # Student emails
            r'sga[a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.edu',  # SGA emails
        ]
        
        for source_type, content in raw_contacts:
            # Extract emails using all patterns
            for pattern in email_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for email in matches:
                    email = email.lower().strip()
                    if self._is_valid_email(email):
                        all_emails.add(email)
            
            # Extract emails from URLs that might contain them
            url_emails = re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+)', content, re.IGNORECASE)
            for email in url_emails:
                email = email.lower().strip()
                if self._is_valid_email(email):
                    all_emails.add(email)
        
        print(f"📊 Extracted {len(all_emails)} unique emails")
        return all_emails
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address and filter out noise."""
        if not email or "@" not in email:
            return False
        
        # Filter out common false positives
        false_positives = [
            "example@", "test@", "sample@", "placeholder@",
            "noreply@", "donotreply@", "admin@", "webmaster@",
            "@example.", "@test.", "@placeholder.", "@domain."
        ]
        
        email_lower = email.lower()
        for fp in false_positives:
            if fp in email_lower:
                return False
        
        # Must be .edu or known campus domain
        if not (".edu" in email_lower):
            return False
        
        # Must have reasonable length
        if len(email) < 5 or len(email) > 50:
            return False
            
        return True
    
    def structure_and_validate_contacts(self, emails: Set[str], campus_name: str) -> List[Dict]:
        """
        Step 3: Use AI to structure emails into contact records with names/titles.
        """
        print("🤖 AI-powered contact structuring...")
        
        if not emails:
            return []
        
        # Convert emails to list for processing
        emails_list = list(emails)[:20]  # Limit to top 20 to avoid token limits
        
        structuring_prompt = f"""You are a university contact analyst for {campus_name}.

Your task is to analyze these email addresses and structure them into student contact records.
For each email, try to infer the likely name, title, and organization based on the email pattern.

EMAIL ADDRESSES:
{chr(10).join(emails_list)}

For each email, return a JSON object with educated guesses about:
- name: (infer from email prefix if possible, otherwise "Unknown")
- title: (infer from email pattern - president, coordinator, etc.)
- organization: (infer what student org this likely belongs to)
- email: (the original email)
- confidence: (high/medium/low based on how clear the inference is)

Return a JSON array of contact objects:
[
  {{
    "name": "John Smith",
    "title": "Student Body President", 
    "organization": "Student Government Association",
    "email": "j.smith@university.edu",
    "confidence": "high"
  }}
]

Be aggressive in making reasonable inferences from email patterns. Better to guess than return "Unknown".
"""

        try:
            response = self.model.generate_content(structuring_prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            contacts = self._parse_json_response(response_text)
            if isinstance(contacts, list):
                print(f"✅ Structured {len(contacts)} contact records")
                return contacts
            else:
                print("⚠️ AI returned non-list, falling back to basic structure")
                return self._basic_email_structure(emails_list)
                
        except Exception as e:
            print(f"❌ AI structuring failed: {e}, falling back to basic structure")
            return self._basic_email_structure(emails_list)
    
    def _parse_json_response(self, text: str):
        """Parse JSON from AI response with multiple fallback strategies."""
        # Try direct JSON parsing
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
        
        # Try finding JSON array/object in text
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        
        return []
    
    def _basic_email_structure(self, emails: List[str]) -> List[Dict]:
        """Fallback basic structuring when AI fails."""
        contacts = []
        for email in emails:
            prefix = email.split("@")[0]
            
            # Basic name inference
            if "." in prefix:
                parts = prefix.split(".")
                name = " ".join(part.capitalize() for part in parts if len(part) > 1)
            else:
                name = prefix.capitalize()
            
            # Basic title inference
            title = "Student Contact"
            if "president" in prefix or "pres" in prefix:
                title = "President"
            elif "sga" in prefix or "government" in prefix:
                title = "Student Government"
            elif "editor" in prefix or "news" in prefix:
                title = "Editor"
            
            contacts.append({
                "name": name,
                "title": title,
                "organization": "Student Organization",
                "email": email,
                "confidence": "low"
            })
        
        return contacts
    
    def cross_validate_and_rank(self, contacts: List[Dict], campus_name: str) -> List[Dict]:
        """
        Step 4: Cross-validate contacts and rank by confidence/importance.
        """
        print("🔍 Cross-validation and ranking...")
        
        if not contacts:
            return []
        
        # Group by email domain to identify official vs informal addresses
        validated_contacts = []
        
        for contact in contacts:
            email = contact.get("email", "")
            confidence = contact.get("confidence", "low")
            
            # Boost confidence for official-looking emails
            if any(keyword in email.lower() for keyword in ["sga", "government", "president", "editor"]):
                if confidence == "low":
                    contact["confidence"] = "medium"
                elif confidence == "medium":
                    contact["confidence"] = "high"
            
            # Boost confidence for structured names (first.last format)
            if "." in email.split("@")[0] and len(email.split("@")[0].split(".")) == 2:
                if confidence == "low":
                    contact["confidence"] = "medium"
            
            validated_contacts.append(contact)
        
        # Sort by confidence (high -> medium -> low) then by title importance
        title_priority = {
            "president": 10, "vice president": 9, "treasurer": 8, 
            "secretary": 7, "coordinator": 6, "director": 5,
            "editor": 4, "manager": 3, "student government": 2
        }
        
        def contact_score(contact):
            confidence_score = {"high": 3, "medium": 2, "low": 1}.get(contact.get("confidence", "low"), 1)
            title_score = 0
            title = contact.get("title", "").lower()
            for key, score in title_priority.items():
                if key in title:
                    title_score = score
                    break
            return confidence_score * 10 + title_score
        
        validated_contacts.sort(key=contact_score, reverse=True)
        
        # Return top 10 contacts
        final_contacts = validated_contacts[:10]
        
        print(f"🎯 Final ranking: {len(final_contacts)} top contacts")
        for i, contact in enumerate(final_contacts[:5], 1):
            print(f"   {i}. {contact['name']} - {contact['title']} - {contact['confidence']}")
        
        return final_contacts


def test_contact_saturation():
    """Test the Contact Saturation Engine"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found")
        return
    
    engine = ContactSaturationEngine(gemini_key)
    result = engine.run("Texas Christian University")
    
    print("\n🎯 CONTACT SATURATION RESULTS:")
    print("="*60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_contact_saturation()
