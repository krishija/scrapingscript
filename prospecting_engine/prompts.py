"""
Centralized prompts for the prospecting engine.
All strategic AI prompts are defined here for easy modification and consistency.
"""

# ============================================================================
# QUANTITATIVE METRICS EXTRACTION PROMPTS
# ============================================================================

EXTRACT_HOUSING_PROMPT = """You are a data analyst extracting housing statistics.

From the following search results, find the MOST ACCURATE percentage of undergraduate students living in university housing at {campus_name}.

Look for:
- Common Data Set reports (highest priority)
- Official university statistics
- US News/IPEDS data
- Housing office websites

Search Results:
{search_data}

Return ONLY a JSON object:
{{"percentInHousing": 45.5, "source": "Common Data Set 2024", "confidence": "high/medium/low"}}

If no data found, return: {{"percentInHousing": null, "source": "not found", "confidence": "none"}}"""

EXTRACT_CENTRICITY_PROMPT = """You are analyzing campus centricity from search results.

Based on these results about {campus_name}, assign a Campus-Centricity Score (1-10 scale):
- 10 = Highly isolated college town (like Dartmouth, rural setting)
- 7-9 = Strong college town feel (like Tuscaloosa, College Station)
- 4-6 = Mixed urban/campus environment (like Berkeley, Austin)
- 1-3 = Fully integrated urban campus (like NYU, BU)

Search Results:
{search_data}

Return ONLY: {{"campusCentricityScore": 7, "justification": "Brief reasoning", "confidence": "high/medium/low"}}"""

EXTRACT_NCAA_PROMPT = """Find the NCAA Division for {campus_name} athletics.

Search Results:
{search_data}

Return ONLY: {{"ncaaDivision": "D1", "conference": "SEC", "confidence": "high/medium/low"}}"""

EXTRACT_GREEK_PROMPT = """Extract Greek Life participation rate for {campus_name}.

Look for percentage of students in fraternities/sororities.

Search Results:
{search_data}

Return ONLY: {{"percentGreekLife": 25.0, "source": "Official source", "confidence": "high/medium/low"}}"""

EXTRACT_RATIO_PROMPT = """Find the student-to-faculty ratio for {campus_name}.

Search Results:
{search_data}

Return ONLY: {{"studentFacultyRatio": "15:1", "source": "US News", "confidence": "high/medium/low"}}"""

EXTRACT_ACCEPTANCE_PROMPT = """Extract the acceptance rate for {campus_name}.

Look for most recent admissions statistics.

Search Results:
{search_data}

Return ONLY: {{"acceptanceRate": 15.5, "source": "Admissions office", "confidence": "high/medium/low"}}"""

EXTRACT_OUT_OF_STATE_PROMPT = """Find the percentage of out-of-state students at {campus_name}.

Search Results:
{search_data}

Return ONLY: {{"percentOutOfState": 65.0, "source": "Common Data Set", "confidence": "high/medium/low"}}"""

EXTRACT_ENDOWMENT_PROMPT = """Calculate endowment per student for {campus_name}.

Look for total endowment and total student enrollment to calculate per-student figure.

Search Results:
{search_data}

Return ONLY: {{"endowmentPerStudent": 150000, "totalEndowment": "3.2 billion", "source": "University reports", "confidence": "high/medium/low"}}"""

EXTRACT_RETENTION_PROMPT = """Find the freshman retention rate for {campus_name}.

Look for the percentage of first-year students who return for their second year.

Search Results:
{search_data}

Return ONLY: {{"freshmanRetentionRate": 94.5, "source": "Common Data Set", "confidence": "high/medium/low"}}"""

# ============================================================================
# STRATEGIC RANKING PROMPT
# ============================================================================

STRATEGIC_RANKING_PROMPT = """You are the Head of Growth at Homie, a community-focused housing platform. Your mission is to rank these 30+ universities based on their potential for building tight-knit residential communities.

CORE ETHOS: We prioritize campuses where students form deep, lasting friendships through shared living experiences. Our ideal targets have high community density, strong social traditions, and active residential life.

RANKING CRITERIA (in order of importance):
1. **Community Density** (40% weight)
   - % in University Housing (higher = better community formation)
   - Campus-Centricity Score (higher = more self-contained community)
   
2. **Social Infrastructure** (30% weight)
   - % Greek Life (indicates strong social traditions)
   - Subreddit Activity (proxy for engaged student community)
   
3. **Market Opportunity** (20% weight)
   - Student-Faculty Ratio (larger classes = more housing pressure)
   - % Out-of-State Students (more likely to need housing solutions)
   
4. **Selectivity & Resources** (10% weight)
   - Acceptance Rate (lower = higher quality students)
   - Endowment per Student (indicates resource availability)

UNIVERSITY DATA:
{university_data}

INSTRUCTIONS:
1. Calculate a Community Potential Score (1-100) for each university
2. Rank all universities from highest to lowest potential
3. Provide brief reasoning for top 10 schools
4. Identify any "Hidden Gems" - schools that might be undervalued

Return ONLY valid JSON:
{{
  "ranked_universities": [
    {{
      "rank": 1,
      "university": "University Name",
      "community_potential_score": 87,
      "key_strengths": ["High housing %", "Strong Greek life"],
      "reasoning": "Brief explanation of ranking"
    }},
    ...
  ],
  "top_10_summary": "Strategic overview of best targets",
  "hidden_gems": ["University 1", "University 2"],
  "ranking_methodology": "Brief explanation of approach"
}}"""

# ============================================================================
# SOCIAL LEADER CONTACT FINDER PROMPTS
# ============================================================================

SOCIAL_LEADER_EXTRACTION_PROMPT = """You are an aggressive contact extraction specialist. Your ONLY goal is to find 3 student email addresses from {campus_name}. 

BE EXTREMELY LIBERAL in what counts as a "contact":
- ANY student government member (president, senator, treasurer, etc.)
- ANY club officer (president, vice president, secretary, etc.)
- ANY residence hall staff (RA, floor coordinator, etc.)
- ANY Greek life member with a title
- ANY student activities staff
- ANY student organization member with contact info listed

DO NOT be picky about "high agency" or "influence" - just find ANY 3 students with email addresses.

SEARCH CONTENT:
{search_content}

INSTRUCTIONS:
Scour the text aggressively for ANY email addresses that belong to students. Look for:
- @university.edu addresses
- firstname.lastname@domain patterns
- Any email with student titles/positions
- Contact pages with student emails
- Officer rosters with emails
- "Contact us" sections with student emails

Return EXACTLY 3 student contacts (or as many as you can find up to 3):

{{
  "student_contacts": [
    {{
      "name": "John Smith",
      "title": "Student Government Senator", 
      "organization": "Student Government",
      "email": "john.smith@university.edu"
    }},
    {{
      "name": "Jane Doe",
      "title": "Club President",
      "organization": "Campus Activities Board", 
      "email": "jane.doe@university.edu"
    }},
    {{
      "name": "Mike Johnson",
      "title": "RA",
      "organization": "Residence Life",
      "email": "mike.johnson@university.edu"
    }}
  ],
  "total_found": 3
}}

CRITICAL: Find ANY 3 student emails - don't overthink the "quality" just get emails that work."""

# ============================================================================
# DIRECTORY HUNTER PROMPT
# ============================================================================

DIRECTORY_HUNTER_PROMPT = """You are a web analyst helping to identify the most promising URLs for finding student leader contact information at {campus_name}.

From the following search results, identify the top 5 URLs most likely to contain comprehensive contact information for student leaders, especially those in:
- Residence Life / Housing
- Greek Life organizations  
- Student Activities / Programming
- Student Government

PRIORITIZE:
- Official university pages with staff/officer directories
- Student organization websites with contact pages
- Greek Life council rosters
- Housing/Residence Life staff pages

AVOID:
- Social media profiles
- News articles or blogs
- General university information pages
- Academic department pages

Search Results:
{search_results}

Return ONLY a JSON list of the 5 most promising URLs:
{{
  "promising_urls": [
    {{
      "url": "https://housing.university.edu/staff",
      "organization": "Housing & Residence Life",
      "rationale": "Staff directory likely contains RAs and community coordinators"
    }},
    ...
  ]
}}"""
