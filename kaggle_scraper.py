#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

# Try to import Kaggle API, but make it optional
try:
    from kaggle.api.kaggle_api_extended import KaggleApi
    KAGGLE_API_AVAILABLE = True
except ImportError:
    KAGGLE_API_AVAILABLE = False
    print("Warning: Kaggle API not available. Using web scraping only.")
except Exception as e:
    KAGGLE_API_AVAILABLE = False
    print("Warning: Could not import Kaggle API:", e)


class KaggleCompetitionScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })
        self.kaggle_api = None
        self._init_kaggle_api()
    
    def _init_kaggle_api(self):
        """Initialize Kaggle API if credentials are available"""
        if not KAGGLE_API_AVAILABLE:
            return
            
        try:
            self.kaggle_api = KaggleApi()
            self.kaggle_api.authenticate()
            print("Kaggle API authenticated successfully")
        except Exception as e:
            print("Warning: Could not authenticate with Kaggle API:", e)
            self.kaggle_api = None
    
    def extract_competition_slug(self, url):
        """Extract competition slug from URL"""
        patterns = [
            r'/c/([^/]+)',
            r'/competitions/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError("Could not extract competition slug from URL: {}".format(url))
    
    def scrape_competition_overview(self, competition_slug):
        """Scrape competition overview information using meta tags and basic parsing"""
        url = "https://www.kaggle.com/competitions/{}".format(competition_slug)
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title from page title
            title = soup.title.string if soup.title else "Unknown Competition"
            title = title.replace(" | Kaggle", "").strip()
            
            # Extract description from meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', 'No description available') if meta_desc else 'No description available'
            
            print("Successfully scraped basic overview for:", competition_slug)
            print("Title:", title)
            print("Description:", description[:100] + "..." if len(description) > 100 else description)
            
            return {
                "id": competition_slug,
                "title": title,
                "description": description,
                "timeline": {},
                "reward": "Prize information not available",
                "evaluation": "Evaluation details not available",
                "url": url
            }
            
        except Exception as e:
            print("Error scraping competition overview:", e)
            return {
                "id": competition_slug,
                "title": "Error: Could not load competition",
                "description": "Failed to load competition information",
                "timeline": {},
                "reward": "Unknown",
                "evaluation": "Unknown", 
                "url": url
            }
    
    def scrape_discussion_threads(self, competition_slug, max_threads=20):
        """Get basic discussion info - simplified approach"""
        print("Discussion scraping simplified - returning mock data for now")
        
        # For now, return some basic structure
        # In a real implementation, this would need more sophisticated JS handling
        return [
            {
                "id": "1",
                "title": "Discussion threads require JavaScript rendering",
                "author": "System",
                "replyCount": 0,
                "voteCount": 0,
                "url": "https://www.kaggle.com/competitions/{}/discussion".format(competition_slug),
                "posts": [
                    {
                        "author": "System",
                        "content": "Discussion content requires JavaScript execution to load properly.",
                        "date": datetime.now().isoformat()
                    }
                ]
            }
        ]
    
    def get_competition_notebooks(self, competition_slug, max_notebooks=1000):
        """Get notebooks for a competition using Kaggle API"""
        if self.kaggle_api:
            try:
                print("Getting notebooks via Kaggle API...")
                all_notebooks = []
                page = 1
                page_size = min(50, max_notebooks)
                
                while len(all_notebooks) < max_notebooks:
                    try:
                        notebooks = self.kaggle_api.kernels_list(
                            competition=competition_slug,
                            page=page,
                            page_size=page_size
                        )
                        
                        if not notebooks:
                            break
                            
                        all_notebooks.extend(notebooks)
                        page += 1
                        
                        if len(notebooks) < page_size:
                            break
                            
                    except Exception as e:
                        print("Error getting notebooks page {}: {}".format(page, e))
                        break
                
                notebook_data = []
                for notebook in all_notebooks[:max_notebooks]:
                    notebook_info = {
                        "id": notebook.ref,
                        "title": notebook.title,
                        "author": notebook.author,
                        "votes": getattr(notebook, 'totalVotes', 0),
                        "url": "https://www.kaggle.com/{}".format(notebook.ref),
                        "lastRunTime": getattr(notebook, 'lastRunTime', None),
                        "language": getattr(notebook, 'language', 'unknown')
                    }
                    notebook_data.append(notebook_info)
                
                print("Retrieved {} notebooks via API".format(len(notebook_data)))
                return notebook_data
                
            except Exception as e:
                print("Error getting notebooks via API:", e)
        
        # Fallback: return basic structure
        print("Kaggle API not available - returning basic notebook structure")
        return [
            {
                "id": "sample",
                "title": "Notebooks require Kaggle API access",
                "author": "System",
                "votes": 0,
                "url": "https://www.kaggle.com/competitions/{}/code".format(competition_slug),
                "language": "python"
            }
        ]
    
    def scrape_all_competition_data(self, competition_url):
        """Scrape all data for a competition"""
        competition_slug = self.extract_competition_slug(competition_url)
        
        print("Scraping competition: {}".format(competition_slug))
        
        # Get competition overview
        print("Scraping competition overview...")
        competition_data = self.scrape_competition_overview(competition_slug)
        
        # Get discussion threads (simplified)
        print("Getting discussion info...")
        discussion_threads = self.scrape_discussion_threads(competition_slug)
        
        # Get notebooks
        print("Getting notebooks...")
        notebooks = self.get_competition_notebooks(competition_slug)
        
        # Combine all data
        result = {
            "competition": competition_data,
            "discussionThreads": discussion_threads,
            "notebooks": notebooks,
            "scrapedAt": datetime.now().isoformat()
        }
        
        return result
    
    def save_to_json(self, data, filename):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def generate_markdown_report(self, data):
        """Generate a markdown report from scraped data"""
        competition = data.get("competition", {})
        threads = data.get("discussionThreads", [])
        notebooks = data.get("notebooks", [])
        
        md_content = """# {}

## Competition Overview

**Competition ID:** {}
**URL:** {}

### Description
{}

## Discussion Threads ({} threads)

""".format(
            competition.get('title', 'Competition Report'),
            competition.get('id', 'N/A'),
            competition.get('url', 'N/A'),
            competition.get('description', 'No description available'),
            len(threads)
        )
        
        for thread in threads[:10]:
            md_content += """### [{}]({})
- **Author:** {}
- **Replies:** {}
- **Votes:** {}

""".format(
                thread.get('title', 'Untitled'),
                thread.get('url', '#'),
                thread.get('author', 'Unknown'),
                thread.get('replyCount', 0),
                thread.get('voteCount', 0)
            )
        
        md_content += """## Notebooks ({} notebooks)

""".format(len(notebooks))
        
        for notebook in notebooks[:20]:
            md_content += """### [{}]({})
- **Author:** {}
- **Votes:** {}
- **Language:** {}

""".format(
                notebook.get('title', 'Untitled'),
                notebook.get('url', '#'),
                notebook.get('author', 'Unknown'),
                notebook.get('votes', 0),
                notebook.get('language', 'Unknown')
            )
        
        md_content += """---
*Report generated on {}*
""".format(data.get('scrapedAt', 'Unknown date'))
        
        return md_content


if __name__ == "__main__":
    scraper = KaggleCompetitionScraper()
    
    # Example usage
    competition_url = "https://www.kaggle.com/competitions/titanic"
    data = scraper.scrape_all_competition_data(competition_url)
    
    print("\n" + "="*50)
    print("FINAL RESULTS:")
    print("Competition:", data['competition']['title'])
    print("Discussion threads:", len(data['discussionThreads']))
    print("Notebooks:", len(data['notebooks']))