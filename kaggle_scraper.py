import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from kaggle.api.kaggle_api_extended import KaggleApi
import markdown
from markdownify import markdownify as md


class KaggleCompetitionScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.kaggle_api = None
        self._init_kaggle_api()
    
    def _init_kaggle_api(self):
        """Initialize Kaggle API if credentials are available"""
        try:
            self.kaggle_api = KaggleApi()
            self.kaggle_api.authenticate()
        except Exception as e:
            print(f"Warning: Could not authenticate with Kaggle API: {e}")
            print("Some features (notebooks) will not be available")
    
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
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
            'h1.competition-header__title',
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
            '.competition-description',
            '.competition-overview-description'
        ]
        
        for selector in description_selectors:
            element = soup.select_one(selector)
            if element:
                return md(str(element))
        
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
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find thread elements
            thread_elements = soup.find_all(['div', 'tr'], class_=re.compile(r'topic|thread|discussion'))
            
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
            # Extract thread title and link
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
    
    def get_competition_notebooks(self, competition_slug: str, max_notebooks: int = 50) -> List[Dict]:
        """Get notebooks for a competition using Kaggle API"""
        if not self.kaggle_api:
            print("Kaggle API not available")
            return []
        
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
            print(f"Error getting competition notebooks: {e}")
            return []
    
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