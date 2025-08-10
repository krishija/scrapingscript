#!/usr/bin/env python3
"""
Email Enrichment Agent
- Input: CSV from Instagram mapping (must include profileUrl, fullName, followersCount, website columns)
- Strategy: For top-N orgs by followersCount
  1) Homepage Finder: use CSV website if valid else targeted Tavily search (prefer .edu)
  2) Relentless Contact Extractor: shallow crawl contact/leadership pages; Gemini extracts best single email
- Output: CSV with columns [profileUrl, fullName, followersCount, homepage_url, email, source, confidence]
"""

import os
import sys
import csv
import re
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime

from dotenv import load_dotenv
import google.generativeai as genai

# Local imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)
from tools import tool_web_search, tool_crawl_for_contacts

load_dotenv(os.path.join(PARENT_DIR, '..', '.env'))

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _init_gemini() -> any:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY not set')
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-pro')


def _read_instagram_csv(csv_path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _parse_int(value: Optional[str]) -> int:
    try:
        return int(float(value)) if value is not None and value != '' else 0
    except Exception:
        return 0


def _pick_top_by_followers(rows: List[Dict[str, str]], top_n: int) -> List[Dict[str, str]]:
    sorted_rows = sorted(rows, key=lambda r: _parse_int(r.get('followersCount')), reverse=True)
    # Filter out rows without profileName/fullName
    sorted_rows = [r for r in sorted_rows if (r.get('fullName') or r.get('profileName'))]
    return sorted_rows[:top_n]


def _clean_url(url: str) -> str:
    if not url:
        return ''
    url = url.strip()
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return f'https://{url}'


def _is_social_link(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(s in host for s in ['instagram.com', 'facebook.com', 'twitter.com', 'x.com', 'tiktok.com', 'linktr.ee', 'beacons.ai', 'linkin.bio'])


def _extract_school_domain(text: str) -> Optional[str]:
    # Simple heuristic: known schools in text
    lower = (text or '').lower()
    if 'pepperdine' in lower:
        return 'pepperdine.edu'
    if 'stanford' in lower:
        return 'stanford.edu'
    if 'tampa' in lower:
        return 'ut.edu'
    if 'bucknell' in lower:
        return 'bucknell.edu'
    if 'alabama a & m' in lower or 'aamu' in lower:
        return 'aamu.edu'
    return None


def _find_homepage(model, org_name: str, website_hint: str, school_domain_hint: Optional[str]) -> Tuple[str, str]:
    """Return (homepage_url, source). Prefer CSV website if not social, else Tavily search + Gemini pick."""
    # 1) Use CSV website if usable
    if website_hint:
        site = _clean_url(website_hint)
        if site and not _is_social_link(site):
            return site, 'csv_website'

    # 2) Tavily search with tight queries (one query per org)
    queries = []
    if school_domain_hint:
        queries.append(f'"{org_name}" site:{school_domain_hint}')
    queries.append(f'"{org_name}" student organization contact')

    # Combine results text
    combined_text = ''
    candidate_urls: List[str] = []
    for q in queries[:1 if school_domain_hint else 1]:  # keep to 1 query for credit control
        result = tool_web_search(q, max_results=3)
        # Extract URLs
        # Our tool returns sources in key 'sources'
        for u in result.get('sources', []):
            if u and u not in candidate_urls and not _is_social_link(u):
                candidate_urls.append(u)
        combined_text += (result.get('corpus') or '')[:4000] + '\n\n'

    # 3) Gemini pick best canonical homepage from candidates
    if candidate_urls:
        prompt = (
            f"Select the single BEST canonical homepage URL for the organization '{org_name}'.\n"
            "You MUST pick a non-social URL (avoid Instagram/Twitter/Linktree). Prefer .edu and relevant university domains.\n"
            "Return ONLY the URL as plain text. Candidates may include:\n" + "\n".join(candidate_urls)
        )
        try:
            resp = model.generate_content(prompt)
            url = (resp.text or '').strip().split()[0]
            url = _clean_url(url)
            if url and not _is_social_link(url):
                return url, 'tavily_gemini_pick'
        except Exception:
            pass

    return '', 'not_found'


def _extract_email_with_gemini(model, org_name: str, school_domain: Optional[str], crawled_text: str) -> Tuple[str, str]:
    text = crawled_text[:12000]
    domain_hint = school_domain or ''
    prompt = (
        f"You are an aggressive data extraction bot. From the following text scraped from '{org_name}', "
        "find the BEST single email address for a student leader.\n"
        "PRIORITY 1: Named leader (President/Captain/Chair/Contact) personal email.\n"
        "PRIORITY 2: General club email (e.g., org@university.edu).\n"
        "Be relentless. Prefer '@" + domain_hint + "' if present. Return ONLY the email string, nothing else.\n\n"
        f"TEXT:\n{text}\n\nEMAIL ONLY:"
    )
    try:
        resp = model.generate_content(prompt)
        guess = (resp.text or '').strip()
        # Extract email from response
        match = EMAIL_REGEX.search(guess)
        if match:
            return match.group(0), 'gemini'
    except Exception:
        pass

    # Fallback: regex directly on crawled text
    if domain_hint:
        domain_pat = re.compile(rf"[A-Za-z0-9._%+-]+@{re.escape(domain_hint)}", re.IGNORECASE)
        m = domain_pat.search(text)
        if m:
            return m.group(0), 'regex_domain'
    m2 = EMAIL_REGEX.search(text)
    if m2:
        return m2.group(0), 'regex_any'

    return '', 'not_found'


def enrich_csv(input_csv: str, output_csv: Optional[str] = None, top_n: int = 20, school_name_hint: Optional[str] = None):
    model = _init_gemini()
    rows = _read_instagram_csv(input_csv)

    # Determine school domain hint from data
    school_domain = None
    if school_name_hint:
        school_domain = _extract_school_domain(school_name_hint)
    if not school_domain and rows:
        # Try from most common words in fullName/bio
        sample = ' '.join([(r.get('fullName') or '') + ' ' + (r.get('bio') or '') for r in rows[:30]])
        school_domain = _extract_school_domain(sample)

    top_rows = _pick_top_by_followers(rows, top_n)

    results: List[Dict[str, str]] = []
    for r in top_rows:
        full_name = r.get('fullName') or r.get('profileName') or ''
        followers = str(_parse_int(r.get('followersCount')))
        profile_url = r.get('profileUrl') or ''
        website_hint = r.get('website') or ''
        existing_email = (r.get('publicEmail') or '').strip()

        # If CSV already provides a publicEmail, trust it and skip costly crawl
        if existing_email:
            results.append({
                'profileUrl': profile_url,
                'fullName': full_name,
                'followersCount': followers,
                'homepage_url': _clean_url(website_hint) if website_hint else '',
                'email': existing_email,
                'email_source': 'csv_publicEmail',
                'homepage_source': 'csv_website' if website_hint else ''
            })
            continue

        homepage_url, homepage_source = _find_homepage(model, full_name, website_hint, school_domain)

        email = ''
        email_source = 'not_found'
        if homepage_url:
            crawled = tool_crawl_for_contacts(homepage_url, full_name)
            email, email_source = _extract_email_with_gemini(model, full_name, school_domain, crawled)

        results.append({
            'profileUrl': profile_url,
            'fullName': full_name,
            'followersCount': followers,
            'homepage_url': homepage_url,
            'email': email,
            'email_source': email_source,
            'homepage_source': homepage_source,
        })

    # Write CSV
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out_path = output_csv or os.path.join(CURRENT_DIR, f"email_enrichment_{ts}.csv")
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['profileUrl','fullName','followersCount','homepage_url','email','email_source','homepage_source'])
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"✅ Enrichment complete: {out_path} ({len(results)} rows)")


if __name__ == '__main__':
    # Defaults: process root-level 'result (1).csv' for Pepperdine-like data
    import argparse
    parser = argparse.ArgumentParser(description='Email Enrichment Agent')
    parser.add_argument('input_csv', nargs='?', default=os.path.join(os.path.dirname(CURRENT_DIR), 'result (1).csv'))
    parser.add_argument('--out', default=None)
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--school', default=None, help='School name hint (e.g., Pepperdine University)')
    args = parser.parse_args()

    # If top exceeds row count, all rows will be processed
    enrich_csv(args.input_csv, args.out, args.top, args.school)
