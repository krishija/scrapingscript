# Campus Intelligence Scraper

A Python project that generates structured "Campus Dossiers" by scraping public web sources for university information. The project uses the Tavily API for intelligent search and scraping, and the Gemini API for summarization and analysis.

## Features

- **Student Organization Discovery**: Automatically finds and scrapes student organization directories
- **Reddit Activity Analysis**: Scrapes campus subreddits for current student discussions and trends
- **AI-Powered Summaries**: Uses Gemini AI to generate comprehensive campus social life summaries
- **Structured Output**: Produces clean, JSON-formatted campus dossiers

## Project Structure

```
Campus Intelligence Scraper/
├── main.py              # Main entry point with CLI interface
├── agents.py            # API interaction logic (Tavily & Gemini)
├── requirements.txt     # Python dependencies
├── env.example          # Example environment variables
└── README.md           # This file
```

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Campus Intelligence Scraper"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up API Keys

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your API keys:
   - **Tavily API Key**: Get from [https://tavily.com/](https://tavily.com/)
   - **Gemini API Key**: Get from [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

   ```bash
   TAVILY_API_KEY=your_actual_tavily_key_here
   GEMINI_API_KEY=your_actual_gemini_key_here
   ```

## Usage

### Basic Usage

```bash
python main.py --campus "University of California, Berkeley"
```

### Example Output

The script will generate a structured Campus Dossier in JSON format:

```json
{
  "campus_name": "University of California, Berkeley",
  "generated_at": "2024-01-01T12:00:00Z",
  "social_life_summary": "Based on the scraped data, 5 student organizations were identified...",
  "student_organizations": [
    {
      "name": "Computer Science Club",
      "category": "Academic"
    },
    {
      "name": "Photography Society", 
      "category": "Arts & Culture"
    }
  ],
  "reddit_activity": [
    {
      "title": "Best study spots on campus?",
      "score": 45,
      "comments": 23
    }
  ],
  "data_sources": {
    "student_orgs_source": "https://example.com/uc-berkeley/student-orgs",
    "reddit_source": "https://reddit.com/r/ucberkeley"
  }
}
```

## API Integration Status

### Current Implementation

- ✅ Project structure and CLI interface
- ✅ Environment variable management
- ✅ Placeholder functions for all major features
- ✅ Error handling and logging

### TODO

- 🔄 Tavily API integration for web scraping
- 🔄 Gemini API integration for AI summaries
- 🔄 Data parsing and structuring
- 🔄 Rate limiting and error handling
- 🔄 Caching for repeated requests

## Development

### Adding New Data Sources

To add new data sources, create new functions in `agents.py` following the existing pattern:

```python
def find_and_scrape_new_source(campus_name: str, tavily_client) -> Dict:
    """
    Scrape data from a new source.
    
    Args:
        campus_name (str): Name of the university
        tavily_client: Initialized Tavily API client
    
    Returns:
        dict: Structured data from the new source
    """
    # Implementation here
    pass
```

Then update `main.py` to call the new function and include the data in the final dossier.

### Testing

```bash
# Test with a sample university
python main.py --campus "Stanford University"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please open an issue on the GitHub repository.
