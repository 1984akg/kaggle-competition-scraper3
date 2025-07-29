import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from markdownify import markdownify as md
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Try to import Kaggle API, but make it optional
try:
    from kaggle.api.kaggle_api_extended import KaggleApi
    KAGGLE_API_AVAILABLE = True
except ImportError:
    KAGGLE_API_AVAILABLE = False
    print("Warning: Kaggle API not available. Some features will be limited.")
except Exception as e:
    KAGGLE_API_AVAILABLE = False
    print(f"Warning: Could not import Kaggle API: {e}")
    print("Continuing with web scraping only.")


class KaggleCompetitionScraper:
    def __init__(self, use_selenium=True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.kaggle_api = None
        self.use_selenium = use_selenium
        self.driver = None
        self._init_kaggle_api()
        if use_selenium:
            self._init_selenium_driver()
    
    def _init_kaggle_api(self):
        """Initialize Kaggle API if credentials are available"""
        if not KAGGLE_API_AVAILABLE:
            self.kaggle_api = None
            return
            
        try:
            self.kaggle_api = KaggleApi()
            self.kaggle_api.authenticate()
            print("Kaggle API authenticated successfully")
        except Exception as e:
            print(f"Warning: Could not authenticate with Kaggle API: {e}")
            print("Some features (notebooks) will not be available")
            self.kaggle_api = None
    
    def _init_selenium_driver(self):
        """Initialize Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(
                service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            print("Selenium WebDriver initialized successfully")
            
        except Exception as e:
            print(f"Warning: Could not initialize Selenium WebDriver: {e}")
            print("Falling back to requests-based scraping")
            self.driver = None
            self.use_selenium = False
    
    def __del__(self):
        """Clean up WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def extract_competition_slug(self, url: str) -> str:
        """Extract competition slug from URL"""
        patterns = [
            r'/c/([^/]+)',
            r'/competitions/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract competition slug from URL: {url}")
    
    def scrape_competition_overview(self, competition_slug: str) -> Dict:
        """Scrape competition overview information"""
        url = f"https://www.kaggle.com/competitions/{competition_slug}/overview"
        
        try:
            if self.use_selenium and self.driver:
                # Use Selenium for dynamic content
                self.driver.get(url)
                # Wait for content to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
                time.sleep(2)  # Additional wait for dynamic content
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                print("Using Selenium for scraping")
            else:
                # Fallback to requests
                response = self.session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                print("Using requests for scraping")
            
            # Debug: Print some of the HTML to understand structure
            print(f"Page title: {soup.title.string if soup.title else 'No title'}")
            
            # Look for h1 tags to debug title extraction
            h1_tags = soup.find_all('h1')
            print(f"Found {len(h1_tags)} h1 tags")
            for i, h1 in enumerate(h1_tags[:3]):
                print(f"H1 {i+1}: {h1.get_text().strip()[:100]}")
            
            # Extract basic information
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            timeline = self._extract_timeline(soup)
            reward = self._extract_reward(soup)
            evaluation = self._extract_evaluation(soup)
            
            return {
                "id": competition_slug,
                "title": title,
                "description": description,
                "timeline": timeline,
                "reward": reward,
                "evaluation": evaluation,
                "url": url
            }
            
        except Exception as e:
            print(f"Error scraping competition overview: {e}")
            return {}
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract competition title"""
        title_selectors = [
            'h1[data-testid="competition-title"]',
            'h1.sc-fFeiMQ',  # Updated selector
            'h1.sc-hKMtZM',  # Another common selector
            '.competition-title h1',
            'h1',
            '.competition-header h1'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Title not found"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract competition description"""
        description_selectors = [
            '[data-testid="competition-description"]',
            '.sc-competition-overview__content',
            '.competition-description',
            '.competition-overview-description',
            '.markdown',
            '.rendered-markdown'
        ]
        
        for selector in description_selectors:
            element = soup.select_one(selector)
            if element:
                return md(str(element))
        
        # Try to find any markdown content
        markdown_elements = soup.find_all(['div'], class_=lambda x: x and 'markdown' in x.lower() if x else False)
        if markdown_elements:
            return md(str(markdown_elements[0]))
        
        return "Description not found"
    
    def _extract_timeline(self, soup: BeautifulSoup) -> Dict:
        """Extract competition timeline"""
        timeline = {}
        
        # Look for timeline information
        timeline_selectors = [
            '.competition-timeline',
            '.competition-sidebar',
            '[data-testid="competition-timeline"]'
        ]
        
        for selector in timeline_selectors:
            element = soup.select_one(selector)
            if element:
                # Extract dates from the timeline section
                date_elements = element.find_all(['time', 'span'], class_=re.compile(r'date|time'))
                for date_elem in date_elements:
                    if date_elem.get('datetime'):
                        timeline['deadline'] = date_elem.get('datetime')
                        break
        
        return timeline
    
    def _extract_reward(self, soup: BeautifulSoup) -> str:
        """Extract competition reward information"""
        reward_selectors = [
            '[data-testid="competition-prize"]',
            '.competition-prize',
            '.prize-amount'
        ]
        
        for selector in reward_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Reward information not found"
    
    def _extract_evaluation(self, soup: BeautifulSoup) -> str:
        """Extract evaluation metric information"""
        eval_selectors = [
            '[data-testid="competition-evaluation"]',
            '.evaluation-metric',
            '.competition-evaluation'
        ]
        
        for selector in eval_selectors:
            element = soup.select_one(selector)
            if element:
                return md(str(element))
        
        return "Evaluation information not found"
    
    def scrape_discussion_threads(self, competition_slug: str, max_threads: int = 50) -> List[Dict]:
        """Scrape discussion threads from competition forum"""
        url = f"https://www.kaggle.com/competitions/{competition_slug}/discussion"
        threads = []
        
        try:
            if self.use_selenium and self.driver:
                # Use Selenium for dynamic content
                self.driver.get(url)
                # Wait for content to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                    time.sleep(3)  # Additional wait for dynamic content
                except:
                    pass
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                print("Using Selenium for discussion scraping")
            else:
                # Fallback to requests
                response = self.session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                print("Using requests for discussion scraping")
            
            # Find thread elements with updated selectors
            thread_selectors = [
                'div[data-testid="discussion-topic"]',
                '.sc-discussion-topic',
                'tr.sc-topic-row',
                'div.topic-item',
                'tr.topic-row',
                'a[href*="/discussion/"]'
            ]
            
            thread_elements = []
            for selector in thread_selectors:
                elements = soup.select(selector)
                if elements:
                    thread_elements = elements
                    print(f"Found {len(elements)} discussion elements with selector: {selector}")
                    break
            
            # Fallback to generic search
            if not thread_elements:
                thread_elements = soup.find_all(['div', 'tr'], class_=re.compile(r'topic|thread|discussion'))
                print(f"Fallback found {len(thread_elements)} discussion elements")
            
            for thread_elem in thread_elements[:max_threads]:
                thread_data = self._extract_thread_info(thread_elem, competition_slug)
                if thread_data:
                    threads.append(thread_data)
                
                # Rate limiting
                time.sleep(0.5)
            
            return threads
            
        except Exception as e:
            print(f"Error scraping discussion threads: {e}")
            return []
    
    def _extract_thread_info(self, thread_elem, competition_slug: str) -> Optional[Dict]:
        """Extract information from a single thread element"""
        try:
            # Extract thread title and link with multiple selectors
            title_link_selectors = [
                'a[href*="/discussion/"]',
                'a[data-testid="discussion-link"]',
                '.discussion-title a',
                '.topic-title a'
            ]
            
            title_link = None
            for selector in title_link_selectors:
                title_link = thread_elem.select_one(selector)
                if title_link:
                    break
            
            # Fallback to generic search
            if not title_link:
                title_link = thread_elem.find('a', href=re.compile(r'/discussion/'))
            
            if not title_link:
                return None
            
            title = title_link.get_text().strip()
            thread_id = re.search(r'/discussion/(\d+)', title_link.get('href', ''))
            if thread_id:
                thread_id = thread_id.group(1)
            else:
                return None
            
            # Extract author, reply count, vote count
            author = self._extract_thread_author(thread_elem)
            reply_count = self._extract_reply_count(thread_elem)
            vote_count = self._extract_vote_count(thread_elem)
            
            # Get thread posts
            posts = self.scrape_thread_posts(competition_slug, thread_id)
            
            return {
                "id": thread_id,
                "title": title,
                "author": author,
                "replyCount": reply_count,
                "voteCount": vote_count,
                "url": f"https://www.kaggle.com/competitions/{competition_slug}/discussion/{thread_id}",
                "posts": posts
            }
            
        except Exception as e:
            print(f"Error extracting thread info: {e}")
            return None
    
    def _extract_thread_author(self, thread_elem) -> str:
        """Extract thread author"""
        author_selectors = [
            '.author',
            '.username',
            '[data-testid="author"]'
        ]
        
        for selector in author_selectors:
            element = thread_elem.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Unknown"
    
    def _extract_reply_count(self, thread_elem) -> int:
        """Extract reply count"""
        reply_selectors = [
            '.reply-count',
            '.posts-count',
            '[data-testid="reply-count"]'
        ]
        
        for selector in reply_selectors:
            element = thread_elem.select_one(selector)
            if element:
                count_text = element.get_text().strip()
                numbers = re.findall(r'\d+', count_text)
                if numbers:
                    return int(numbers[0])
        
        return 0
    
    def _extract_vote_count(self, thread_elem) -> int:
        """Extract vote count"""
        vote_selectors = [
            '.vote-count',
            '.upvotes',
            '[data-testid="vote-count"]'
        ]
        
        for selector in vote_selectors:
            element = thread_elem.select_one(selector)
            if element:
                count_text = element.get_text().strip()
                numbers = re.findall(r'\d+', count_text)
                if numbers:
                    return int(numbers[0])
        
        return 0
    
    def scrape_thread_posts(self, competition_slug: str, thread_id: str, max_posts: int = 20) -> List[Dict]:
        """Scrape posts from a specific discussion thread"""
        url = f"https://www.kaggle.com/competitions/{competition_slug}/discussion/{thread_id}"
        posts = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find post elements
            post_elements = soup.find_all(['div'], class_=re.compile(r'post|comment|message'))
            
            for post_elem in post_elements[:max_posts]:
                post_data = self._extract_post_info(post_elem)
                if post_data:
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            print(f"Error scraping thread posts: {e}")
            return []
    
    def _extract_post_info(self, post_elem) -> Optional[Dict]:
        """Extract information from a single post element"""
        try:
            # Extract author
            author_elem = post_elem.find(['span', 'div'], class_=re.compile(r'author|username'))
            author = author_elem.get_text().strip() if author_elem else "Unknown"
            
            # Extract content
            content_elem = post_elem.find(['div', 'p'], class_=re.compile(r'content|text|message'))
            content = md(str(content_elem)) if content_elem else "Content not found"
            
            # Extract date
            date_elem = post_elem.find(['time', 'span'], class_=re.compile(r'date|time'))
            date = date_elem.get('datetime') or date_elem.get_text().strip() if date_elem else "Unknown"
            
            return {
                "author": author,
                "content": content,
                "date": date
            }
            
        except Exception as e:
            print(f"Error extracting post info: {e}")
            return None
    
    def get_competition_notebooks(self, competition_slug: str, max_notebooks: int = 1000) -> List[Dict]:
        """Get notebooks for a competition using Kaggle API or web scraping"""
        # Try Kaggle API first
        if self.kaggle_api:
            try:
                # Get notebooks list
                notebooks = self.kaggle_api.kernels_list(
                    competition=competition_slug,
                    page_size=max_notebooks
                )
                
                notebook_data = []
                for notebook in notebooks:
                    notebook_info = {
                        "id": notebook.ref,
                        "title": notebook.title,
                        "author": notebook.author,
                        "votes": getattr(notebook, 'totalVotes', 0),
                        "url": f"https://www.kaggle.com/{notebook.ref}",
                        "lastRunTime": getattr(notebook, 'lastRunTime', None),
                        "language": getattr(notebook, 'language', 'unknown')
                    }
                    notebook_data.append(notebook_info)
                
                return notebook_data
                
            except Exception as e:
                print(f"Error getting notebooks via API: {e}")
        
        # Fallback to web scraping
        print("Falling back to web scraping for notebooks...")
        return self._scrape_notebooks_from_web(competition_slug, max_notebooks)
    
    def _scrape_notebooks_from_web(self, competition_slug: str, max_notebooks: int = 1000) -> List[Dict]:
        """Scrape notebooks from competition code page"""
        url = f"https://www.kaggle.com/competitions/{competition_slug}/code"
        notebooks = []
        
        try:
            if self.use_selenium and self.driver:
                # Use Selenium for dynamic content
                self.driver.get(url)
                # Wait for content to load
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                    time.sleep(3)  # Additional wait for dynamic content
                except:
                    pass
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                print("Using Selenium for notebook scraping")
            else:
                # Fallback to requests
                response = self.session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                print("Using requests for notebook scraping")
            
            # Find notebook elements
            notebook_selectors = [
                'div[data-testid="code-item"]',
                '.sc-code-item',
                '.kernel-item',
                'div.code-item',
                'a[href*="/code/"]'
            ]
            
            notebook_elements = []
            for selector in notebook_selectors:
                elements = soup.select(selector)
                if elements:
                    notebook_elements = elements
                    print(f"Found {len(elements)} notebook elements with selector: {selector}")
                    break
            
            # Fallback to generic search
            if not notebook_elements:
                notebook_elements = soup.find_all(['div'], class_=re.compile(r'kernel|code|notebook'))
                print(f"Fallback found {len(notebook_elements)} notebook elements")
            
            for notebook_elem in notebook_elements[:max_notebooks]:
                notebook_data = self._extract_notebook_info(notebook_elem)
                if notebook_data:
                    notebooks.append(notebook_data)
            
            return notebooks
            
        except Exception as e:
            print(f"Error scraping notebooks from web: {e}")
            return []
    
    def _extract_notebook_info(self, notebook_elem) -> Optional[Dict]:
        """Extract information from a notebook element"""
        try:
            # Extract title and link
            title_link_selectors = [
                'a[href*="/code/"]',
                '.kernel-title a',
                '.code-title a',
                'h3 a',
                'h4 a'
            ]
            
            title_link = None
            for selector in title_link_selectors:
                title_link = notebook_elem.select_one(selector)
                if title_link:
                    break
            
            if not title_link:
                return None
            
            title = title_link.get_text().strip()
            href = title_link.get('href', '')
            
            # Extract author
            author_selectors = [
                '.kernel-author',
                '.code-author',
                '[data-testid="author"]',
                '.author'
            ]
            
            author = "Unknown"
            for selector in author_selectors:
                author_elem = notebook_elem.select_one(selector)
                if author_elem:
                    author = author_elem.get_text().strip()
                    break
            
            # Extract vote count
            vote_selectors = [
                '.vote-count',
                '.votes',
                '[data-testid="votes"]'
            ]
            
            votes = 0
            for selector in vote_selectors:
                vote_elem = notebook_elem.select_one(selector)
                if vote_elem:
                    vote_text = vote_elem.get_text().strip()
                    numbers = re.findall(r'\d+', vote_text)
                    if numbers:
                        votes = int(numbers[0])
                    break
            
            return {
                "id": href.split('/')[-1] if href else "unknown",
                "title": title,
                "author": author,
                "votes": votes,
                "url": f"https://www.kaggle.com{href}" if href.startswith('/') else href,
                "lastRunTime": None,
                "language": "unknown"
            }
            
        except Exception as e:
            print(f"Error extracting notebook info: {e}")
            return None
    
    def scrape_all_competition_data(self, competition_url: str) -> Dict:
        """Scrape all data for a competition"""
        competition_slug = self.extract_competition_slug(competition_url)
        
        print(f"Scraping competition: {competition_slug}")
        
        # Get competition overview
        print("Scraping competition overview...")
        competition_data = self.scrape_competition_overview(competition_slug)
        
        # Get discussion threads
        print("Scraping discussion threads...")
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
    
    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def generate_markdown_report(self, data: Dict) -> str:
        """Generate a markdown report from scraped data"""
        competition = data.get("competition", {})
        threads = data.get("discussionThreads", [])
        notebooks = data.get("notebooks", [])
        
        md_content = f"""# {competition.get('title', 'Competition Report')}

## Competition Overview

**Competition ID:** {competition.get('id', 'N/A')}
**URL:** {competition.get('url', 'N/A')}
**Reward:** {competition.get('reward', 'N/A')}

### Description
{competition.get('description', 'No description available')}

### Evaluation
{competition.get('evaluation', 'No evaluation information available')}

## Discussion Threads ({len(threads)} threads)

"""
        
        for thread in threads[:10]:  # Show top 10 threads
            md_content += f"""### [{thread.get('title', 'Untitled')}]({thread.get('url', '#')})
- **Author:** {thread.get('author', 'Unknown')}
- **Replies:** {thread.get('replyCount', 0)}
- **Votes:** {thread.get('voteCount', 0)}

"""
            # Add first few posts
            posts = thread.get('posts', [])
            for post in posts[:3]:  # Show first 3 posts
                md_content += f"""**{post.get('author', 'Unknown')}** ({post.get('date', 'Unknown date')}):
{post.get('content', 'No content')}

---

"""
        
        md_content += f"""## Notebooks ({len(notebooks)} notebooks)

"""
        
        for notebook in notebooks[:20]:  # Show top 20 notebooks
            md_content += f"""### [{notebook.get('title', 'Untitled')}]({notebook.get('url', '#')})
- **Author:** {notebook.get('author', 'Unknown')}
- **Votes:** {notebook.get('votes', 0)}
- **Language:** {notebook.get('language', 'Unknown')}

"""
        
        md_content += f"""---
*Report generated on {data.get('scrapedAt', 'Unknown date')}*
"""
        
        return md_content


if __name__ == "__main__":
    scraper = KaggleCompetitionScraper()
    
    # Example usage
    competition_url = "https://www.kaggle.com/competitions/titanic"
    data = scraper.scrape_all_competition_data(competition_url)
    
    # Save as JSON
    scraper.save_to_json(data, "competition_data.json")
    
    # Generate markdown report
    markdown_report = scraper.generate_markdown_report(data)
    with open("competition_report.md", "w", encoding="utf-8") as f:
        f.write(markdown_report)
    
    print("Scraping completed!")