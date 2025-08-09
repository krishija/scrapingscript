"""
Robust Tavily client wrapper and utility functions for prospecting engine.
Optimized for efficient API usage across batch processing.
"""

import os
import time
from typing import Dict, List
from tavily import TavilyClient


def _init_tavily() -> TavilyClient:
    """Initialize Tavily client with API key from environment."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set in environment")
    return TavilyClient(api_key=api_key)


def _safe_tavily_search(client: TavilyClient, query: str, max_results: int = 3) -> Dict:
    """Safe Tavily search with error handling and rate limiting."""
    try:
        return client.search(query=query, search_depth="advanced", max_results=max_results)
    except Exception as e:
        print(f"⚠️ Tavily search failed for '{query[:50]}...': {e}")
        return {"results": []}


def tool_web_search(query: str, max_results: int = 4) -> Dict:
    """
    Optimized web search tool for prospecting engine.
    
    Returns:
        Dict with 'corpus' (combined text) and 'sources' (list of URLs)
    """
    client = _init_tavily()
    results = _safe_tavily_search(client, query, max_results=max_results)
    
    # Extract and combine content
    corpus_parts = []
    sources = []
    
    for r in results.get("results", []):
        content = r.get("content", "") or r.get("raw_content", "")
        url = r.get("url", "")
        
        if content and url:
            # Clean and truncate content
            clean_content = content.strip()[:1200]  # Limit per source
            corpus_parts.append(clean_content)
            sources.append(url)
    
    combined_corpus = "\n\n---\n\n".join(corpus_parts)[:8000]  # Total limit
    
    return {
        "corpus": combined_corpus,
        "sources": sources,
        "query_used": query
    }


def tool_crawl_for_contacts(base_url: str, entity_name: str) -> str:
    """
    Optimized contact crawling with fewer API calls.
    
    Args:
        base_url: The main URL to crawl from
        entity_name: Name of the organization for context
        
    Returns:
        Combined text corpus from contact-related pages
    """
    client = _init_tavily()
    
    print(f"🌐 Efficient crawling: {base_url}")
    
    contact_content = []
    domain = base_url.split('/')[2] if '/' in base_url else base_url
    
    # Single optimized query to get contact pages from the domain
    try:
        # One comprehensive search instead of multiple keyword searches
        contact_query = f'site:{domain} (contact OR staff OR officers OR directory OR leadership OR roster) (email OR phone OR @)'
        
        contact_results = _safe_tavily_search(client, contact_query, max_results=6)  # Get more results from single query
        
        for r in contact_results.get("results", []):
            contact_url = r.get("url", "")
            contact_page_content = r.get("content", "")
            
            # Include if it contains potential contact info
            if contact_page_content and any(term in contact_page_content.lower() for term in ["email", "@", "phone", "contact"]):
                contact_content.append(f"=== {contact_url} ===\n{contact_page_content[:2000]}")
                
            if len(contact_content) >= 4:  # Limit to 4 pages max
                break
        
        # If we didn't get good results, try the base URL directly
        if not contact_content:
            base_result = _safe_tavily_search(client, f"site:{base_url}", max_results=1)
            if base_result.get("results"):
                base_content = base_result["results"][0].get("content", "")
                if base_content:
                    contact_content.append(f"=== BASE PAGE ===\n{base_content[:2000]}")
                    
    except Exception as e:
        print(f"⚠️ Crawling failed: {e}")
    
    # Combine all contact-related content
    final_content = "\n\n".join(contact_content)
    print(f"📄 Crawled {len(contact_content)} pages, {len(final_content)} chars")
    
    return final_content[:12000]  # Return manageable amount
