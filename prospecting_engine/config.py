DEFAULT_MODEL_CANDIDATES = [
    'gemini-2.0-flash-exp',
    'gemini-1.5-flash',
    'gemini-1.5-pro'
]

# Keep temperature low for reproducibility; bump only if recall misses
GENERATION_TEMPERATURE = 0.1

# Max Tavily results per query to balance recall vs. noise
DEFAULT_MAX_RESULTS = 4


