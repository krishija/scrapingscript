import os
import time
from typing import Dict, List, Tuple

from tavily import TavilyClient

# Optimized tools with better error handling and efficiency

def _init_tavily() -> TavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set in environment")
    return TavilyClient(api_key=api_key)


def _safe_tavily_search(client: TavilyClient, query: str, max_results: int = 3) -> Dict:
    """Single, robust Tavily search with fallback."""
    try:
        time.sleep(0.3)  # Rate limiting
        return client.search(query=query, search_depth="basic", max_results=max_results)
    except Exception as e:
        print(f"⚠️ Tavily search failed for '{query}': {e}")
        return {"results": []}


def _extract_content(results: Dict, max_chars: int = 8000) -> str:
    """Extract clean content from Tavily results with better organization discovery."""
    chunks = []
    for r in results.get("results", [])[:6]:  # Process more results
        title = r.get("title", "")
        content = r.get("content", "") or r.get("raw_content", "")
        url = r.get("url", "")
        
        if content:
            # For org discovery, take more content per result
            snippet_length = 1800 if "organization" in content.lower() or "club" in content.lower() else 1200
            snippet = content.strip()[:snippet_length]
            chunks.append(f"[{title}] {snippet}")
    
    return "\n\n".join(chunks)[:max_chars]


# Optimized public tools

def tool_web_search(query: str) -> Dict:
    """Enhanced web search with deeper crawling for better org discovery."""
    client = _init_tavily()
    
    # Use deeper search for better content
    results = _safe_tavily_search(client, query, max_results=6)  # More results
    content = _extract_content(results, max_chars=10000)  # More content per result
    sources = [r.get("url", "") for r in results.get("results", [])]
    
    return {
        "corpus": content,
        "sources": [s for s in sources if s],
        "query_used": query
    }


def tool_crawl_for_contacts(entity_name: str, campus_name: str) -> str:
    """Advanced contact crawler - finds homepage then crawls contact-related pages."""
    client = _init_tavily()
    
    print(f"🌐 Finding homepage for: {entity_name}")
    
    # Step 1: Find the most likely homepage URL with intelligent filtering
    homepage_queries = [
        f'site:.edu "{entity_name}" {campus_name}',  # Prioritize .edu domains
        f'"{entity_name}" "{campus_name}" official website',
        f'"{entity_name}" {campus_name} contact email',
        f'"{entity_name}" site:(.edu OR .org)'  # Backup with .org
    ]
    
    # Blacklisted domains that are never the actual homepage
    blacklisted_domains = [
        'wikipedia.org', 'en.wikipedia.org', 'facebook.com', 'twitter.com', 
        'linkedin.com', 'instagram.com', 'youtube.com', 'reddit.com',
        'campustours.com', 'collegeconfidential.com', 'niche.com'
    ]
    
    homepage_url = None
    for query in homepage_queries:
        try:
            results = _safe_tavily_search(client, query, max_results=5)
            for r in results.get("results", []):
                url = r.get("url", "").lower()
                title = r.get("title", "").lower()
                content = r.get("content", "").lower()
                
                # Skip blacklisted domains
                if any(domain in url for domain in blacklisted_domains):
                    continue
                
                # Strongly prefer .edu domains
                if ".edu" in url:
                    entity_keywords = entity_name.lower().split()
                    if any(keyword in title or keyword in url for keyword in entity_keywords):
                        homepage_url = r.get("url", "")  # Get original case URL
                        break
                
                # Accept non-.edu if it seems official and mentions entity
                entity_keywords = entity_name.lower().split()
                if (any(keyword in title for keyword in entity_keywords) and 
                    any(term in content for term in ["contact", "email", "editor", "staff"])):
                    homepage_url = r.get("url", "")
                    break
                    
            if homepage_url:
                break
        except Exception as e:
            print(f"⚠️ Homepage search failed: {e}")
            continue
    
    if not homepage_url:
        print(f"❌ Could not find homepage for {entity_name}")
        return f"Could not find homepage for {entity_name}"
    
    print(f"🏠 Found homepage: {homepage_url}")
    
    # Step 2: Perform shallow crawl for contact pages
    contact_keywords = ["contact", "about", "staff", "leadership", "roster", "directory", "team", "officers", "editorial", "masthead", "editors", "submit"]
    contact_content = []
    
    # First, get the homepage content and look for contact-related links
    try:
        homepage_result = _safe_tavily_search(client, f"site:{homepage_url}", max_results=1)
        homepage_content = ""
        if homepage_result.get("results"):
            homepage_content = homepage_result["results"][0].get("content", "")
            contact_content.append(f"=== HOMEPAGE: {homepage_url} ===\n{homepage_content[:2000]}")
        
        # Extract potential contact page URLs from homepage content
        import re
        # Look for relative and absolute URLs that might contain contact info
        potential_contact_urls = []
        domain = homepage_url.split('/')[2] if '/' in homepage_url else homepage_url
        
        for keyword in contact_keywords:
            # Search for pages that might contain contact info
            contact_queries = [
                f'site:{domain} "{keyword}" {entity_name}',
                f'site:{domain} "{keyword}" email contact'
            ]
            
            for contact_query in contact_queries[:2]:  # Limit to prevent too many calls
                try:
                    contact_results = _safe_tavily_search(client, contact_query, max_results=2)
                    for r in contact_results.get("results", []):
                        contact_url = r.get("url", "")
                        contact_page_content = r.get("content", "")
                        
                        # Only include if it seems to have contact info
                        if any(term in contact_page_content.lower() for term in ["email", "@", "president", "editor", "chair", "coordinator"]):
                            contact_content.append(f"=== CONTACT PAGE: {contact_url} ===\n{contact_page_content[:2000]}")
                            
                        if len(contact_content) >= 6:  # Limit total pages
                            break
                    
                    if len(contact_content) >= 6:
                        break
                        
                except Exception as e:
                    print(f"⚠️ Contact page search failed: {e}")
                    continue
                    
                time.sleep(0.2)  # Rate limiting
            
            if len(contact_content) >= 6:
                break
    
    except Exception as e:
        print(f"⚠️ Crawling failed: {e}")
        if not contact_content:
            contact_content.append(f"Crawling failed for {entity_name}: {str(e)}")
    
    # Combine all contact-related content
    final_content = "\n\n".join(contact_content)
    print(f"📄 Crawled {len(contact_content)} pages, {len(final_content)} chars")
    
    return final_content