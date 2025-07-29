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
        """Get discussion threads using Kaggle API or fallback methods"""
        
        # Try Kaggle API first for discussions
        if self.kaggle_api:
            try:
                print("Attempting to get discussions via Kaggle API...")
                # Try to get discussion list via API
                discussions = self.kaggle_api.competitions_discussions_list(competition_slug)
                
                discussion_threads = []
                for i, discussion in enumerate(discussions[:max_threads]):
                    thread_data = {
                        "id": str(discussion.id),
                        "title": discussion.title,
                        "author": discussion.author,
                        "replyCount": getattr(discussion, 'totalReplies', 0),
                        "voteCount": getattr(discussion, 'totalVotes', 0),
                        "url": "https://www.kaggle.com/competitions/{}/discussion/{}".format(competition_slug, discussion.id),
                        "posts": []
                    }
                    
                    # Try to get posts for this discussion
                    try:
                        posts = self.kaggle_api.competitions_discussions_comments_list(competition_slug, discussion.id)
                        for post in posts[:5]:  # Limit to first 5 posts
                            post_data = {
                                "author": post.author,
                                "content": getattr(post, 'message', 'No content'),
                                "date": getattr(post, 'postedDate', datetime.now().isoformat())
                            }
                            thread_data["posts"].append(post_data)
                    except Exception as post_error:
                        print("Could not get posts for discussion {}: {}".format(discussion.id, post_error))
                    
                    discussion_threads.append(thread_data)
                
                print("Retrieved {} discussion threads via API".format(len(discussion_threads)))
                return discussion_threads
                
            except Exception as e:
                print("Error getting discussions via API:", e)
        
        # Fallback: Try basic web scraping approach
        print("Trying basic web scraping for discussions...")
        return self._scrape_discussions_web(competition_slug, max_threads)
    
    def _scrape_discussions_web(self, competition_slug, max_threads=20):
        """Fallback web scraping method for discussions"""
        
        # Try different approaches to get discussion data
        approaches = [
            self._try_api_style_discussions,
            self._try_mobile_page_discussions,
            self._try_search_discussions
        ]
        
        for approach in approaches:
            try:
                discussions = approach(competition_slug, max_threads)
                if discussions and len(discussions) > 1:  # More than just placeholder
                    return discussions
            except Exception as e:
                print("Approach failed:", e)
                continue
        
        print("All discussion scraping approaches failed")
        return self._get_placeholder_discussions(competition_slug)
    
    def _try_api_style_discussions(self, competition_slug, max_threads):
        """Try to access discussions via internal API endpoints"""
        # This might not work without authentication, but worth trying
        api_url = "https://www.kaggle.com/api/i/competitions.CompetitionsService/GetCompetitionDiscussionTopics"
        
        # Try with different endpoints that might be publicly accessible
        public_urls = [
            "https://www.kaggle.com/competitions/{}/discussion.json".format(competition_slug),
            "https://www.kaggle.com/api/v1/competitions/{}/topics".format(competition_slug)
        ]
        
        for url in public_urls:
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    data = response.json()
                    print("Found JSON data from:", url)
                    # Process JSON data here
                    return self._process_discussion_json(data, competition_slug)
            except:
                continue
        
        return []
    
    def _try_mobile_page_discussions(self, competition_slug, max_threads):
        """Try mobile version which might have simpler HTML"""
        mobile_url = "https://m.kaggle.com/competitions/{}/discussion".format(competition_slug)
        
        try:
            # Try with mobile user agent
            mobile_headers = self.session.headers.copy()
            mobile_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            
            response = self.session.get(mobile_url, headers=mobile_headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Process mobile page
                return self._extract_discussions_from_soup(soup, competition_slug)
        except:
            pass
        
        return []
    
    def _try_search_discussions(self, competition_slug, max_threads):
        """Try to find discussions through Kaggle search"""
        search_url = "https://www.kaggle.com/search"
        params = {
            'q': 'competition:{} type:discussions'.format(competition_slug)
        }
        
        try:
            response = self.session.get(search_url, params=params)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return self._extract_discussions_from_soup(soup, competition_slug)
        except:
            pass
        
        return []
    
    def _extract_discussions_from_soup(self, soup, competition_slug):
        """Extract discussion data from BeautifulSoup object"""
        discussions = []
        
        # Look for any links that might be discussions
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            if '/discussion/' in href:
                # Extract discussion ID
                match = re.search(r'/discussion/(\d+)', href)
                if match:
                    discussion_id = match.group(1)
                    title = link.get_text().strip()
                    
                    if title and len(title) > 10:  # Meaningful title
                        discussions.append({
                            "id": discussion_id,
                            "title": title,
                            "author": "Unknown",
                            "replyCount": 0,
                            "voteCount": 0,
                            "url": "https://www.kaggle.com" + href if href.startswith('/') else href,
                            "posts": [{
                                "author": "System",
                                "content": "Visit the discussion URL for full content: {}".format(href),
                                "date": datetime.now().isoformat()
                            }]
                        })
        
        return discussions
    
    def _process_discussion_json(self, data, competition_slug):
        """Process JSON discussion data"""
        discussions = []
        # Implementation would depend on JSON structure
        # This is a placeholder for when we find working JSON endpoints
        return discussions
    
    def _get_placeholder_discussions(self, competition_slug):
        """Get placeholder discussion data with helpful information"""
        return [
            {
                "id": "info",
                "title": "How to Access Discussions",
                "author": "System",
                "replyCount": 0,
                "voteCount": 0,
                "url": "https://www.kaggle.com/competitions/{}/discussion".format(competition_slug),
                "posts": [{
                    "author": "System",
                    "content": """Discussion content is dynamically loaded with JavaScript and requires either:
1. Kaggle API access (recommended) - Set up kaggle.json file
2. Browser automation (Selenium) - More complex but possible
3. Manual browsing - Visit the competition discussion page directly

For now, this scraper provides basic competition info and notebook data.""",
                    "date": datetime.now().isoformat()
                }]
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