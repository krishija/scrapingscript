#!/usr/bin/env python3
"""
AI Ranking for Institution Play (Top 20 Selector)
- Input: CSV from Instagram mapping (result (1).csv)
- Filter: Keep real Pepperdine student orgs; exclude athletes/brands/overarching bodies
- Criteria: followersCount, postsCount, presence of website/publicEmail, and diversity (not all Greek)
- Output: CSV of 20 selected orgs with key fields
"""

import os
import sys
import csv
import json
from typing import List, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
import google.generativeai as genai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(ROOT_DIR, '.env'))


def _init_gemini():
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY not set')
    genai.configure(api_key=key)
    return genai.GenerativeModel('gemini-1.5-pro')


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _to_int(s: str) -> int:
    try:
        return int(float(s)) if s not in (None, '') else 0
    except Exception:
        return 0


def _pre_filter(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for r in rows:
        full = (r.get('fullName') or '').strip()
        prof = (r.get('profileName') or '').strip()
        cat = (r.get('category') or '').strip().lower()
        bio = (r.get('bio') or '').lower()
        url = (r.get('profileUrl') or '').strip()
        followers = _to_int(r.get('followersCount'))
        posts = _to_int(r.get('postsCount'))
        website = (r.get('website') or '').strip()
        email = (r.get('publicEmail') or '').strip()

        text = ' '.join([full.lower(), prof.lower(), bio])
        if not full and not prof:
            continue
        # Must be Pepperdine related
        if not any(k in text for k in ['pepperdine', 'pepp']):
            continue
        # Exclude obvious non-student-orgs
        if cat in ['athlete', 'public figure', 'brand']:
            continue
        # Keep likely student orgs (greek/media/clubs)
        filtered.append({
            'profileUrl': url,
            'fullName': full or prof,
            'followersCount': followers,
            'postsCount': posts,
            'website': website,
            'publicEmail': email,
            'category': cat,
        })
    return filtered


def _ask_gemini_select(model, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Limit to top 80 by followers to keep prompt size sane
    cand_sorted = sorted(candidates, key=lambda x: (x.get('followersCount', 0), x.get('postsCount', 0)), reverse=True)[:80]
    payload = json.dumps(cand_sorted)
    prompt = (
        "You are selecting 20 Pepperdine student organizations for an outreach campaign.\n"
        "Constraints:\n"
        "- Include only actual student orgs/clubs and specific fraternities/sororities.\n"
        "- EXCLUDE overarching bodies like Panhellenic Council, IFC, ICC, Student Activities central pages.\n"
        "- Favor higher followersCount and postsCount.\n"
        "- Prefer entries with a website or publicEmail (don't auto-include).\n"
        "- Maintain diversity: cap Greek at 8; include media, cultural, pre-professional, club sports, interest groups.\n"
        "Return STRICT JSON array of 20 objects from the input, each with original fields. No extra keys. No commentary.\n\n"
        f"CANDIDATES (JSON):\n{payload}\n\nOUTPUT JSON ONLY:"
    )
    resp = model.generate_content(prompt)
    text = (resp.text or '').strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data[:20]
    except Exception:
        # Try to extract the first array
        l = text.find('[')
        r = text.rfind(']')
        if l != -1 and r != -1 and r > l:
            try:
                arr = json.loads(text[l:r+1])
                return arr[:20] if isinstance(arr, list) else []
            except Exception:
                pass
    return cand_sorted[:20]


def _write_csv(rows: List[Dict[str, Any]], out_path: str):
    fields = ['profileUrl','fullName','followersCount','postsCount','website','publicEmail','category']
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_csv', nargs='?', default=os.path.join(ROOT_DIR, 'result (1).csv'))
    parser.add_argument('--out', default=None)
    args = parser.parse_args()

    model = _init_gemini()
    rows = _read_csv(args.input_csv)
    candidates = _pre_filter(rows)
    selected = _ask_gemini_select(model, candidates)

    ts = datetime.utcnow().strftime('%Y%m%d_%H%M')
    out = args.out or os.path.join(os.path.dirname(__file__), f'institution_play_top20_{ts}.csv')
    _write_csv(selected, out)
    print(f'✅ Wrote top 20 to {out}')


if __name__ == '__main__':
    main()
