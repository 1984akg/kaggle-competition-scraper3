import streamlit as st
import json
import pandas as pd
from kaggle_scraper import KaggleCompetitionScraper
import time
import os


def main():
    st.set_page_config(
        page_title="Kaggle Competition Scraper",
        page_icon="🏆",
        layout="wide"
    )
    
    st.title("🏆 Kaggle Competition Scraper")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key setup
        st.subheader("Kaggle API Setup")
        st.info("Place your kaggle.json file in ~/.kaggle/ directory or set KAGGLE_USERNAME and KAGGLE_KEY environment variables")
        
        # Scraping options
        st.subheader("Scraping Options")
        max_threads = st.slider("Max Discussion Threads", 5, 100, 20)
        max_notebooks = st.slider("Max Notebooks", 5, 1000, 1000)
        max_posts_per_thread = st.slider("Max Posts per Thread", 3, 50, 10)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Competition URL")
        competition_url = st.text_input(
            "Enter Kaggle Competition URL:",
            placeholder="https://www.kaggle.com/competitions/titanic",
            help="Enter the full URL of the Kaggle competition you want to scrape"
        )
        
        if st.button("🚀 Start Scraping", type="primary"):
            if competition_url:
                scrape_competition(competition_url, max_threads, max_notebooks, max_posts_per_thread)
            else:
                st.error("Please enter a competition URL")
    
    with col2:
        st.header("📊 Output Options")
        output_format = st.selectbox(
            "Choose output format:",
            ["JSON", "Markdown", "Both"]
        )
        
        download_data = st.checkbox("Enable data download", value=True)


def scrape_competition(url: str, max_threads: int, max_notebooks: int, max_posts: int):
    """Scrape competition data and display results"""
    
    # Initialize scraper with Streamlit mode
    scraper = KaggleCompetitionScraper(use_selenium=False, streamlit_mode=True)
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Extract competition slug
        status_text.text("🔍 Extracting competition information...")
        competition_slug = scraper.extract_competition_slug(url)
        progress_bar.progress(10)
        
        # Scrape overview
        status_text.text("📖 Scraping competition overview...")
        competition_data = scraper.scrape_competition_overview(competition_slug)
        progress_bar.progress(30)
        
        # Scrape discussions
        status_text.text("💬 Scraping discussion threads...")
        discussion_threads = scraper.scrape_discussion_threads(competition_slug, max_threads)
        progress_bar.progress(60)
        
        # Get notebooks
        status_text.text("📚 Fetching notebooks...")
        notebooks = scraper.get_competition_notebooks(competition_slug, max_notebooks)
        progress_bar.progress(90)
        
        # Combine data
        status_text.text("📦 Combining data...")
        all_data = {
            "competition": competition_data,
            "discussionThreads": discussion_threads,
            "notebooks": notebooks,
            "scrapedAt": pd.Timestamp.now().isoformat()
        }
        progress_bar.progress(100)
        status_text.text("✅ Scraping completed!")
        
        # Display results
        display_results(all_data, competition_slug)
        
    except Exception as e:
        st.error(f"❌ Error during scraping: {str(e)}")
        status_text.text("❌ Scraping failed")


def display_results(data: dict, competition_slug: str):
    """Display scraped results in the UI"""
    
    st.markdown("---")
    st.header("📊 Results")
    
    competition = data.get("competition", {})
    threads = data.get("discussionThreads", [])
    notebooks = data.get("notebooks", [])
    
    # Competition Overview
    st.subheader("🏆 Competition Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Competition ID", competition.get("id", "N/A"))
    with col2:
        st.metric("Discussion Threads", len(threads))
    with col3:
        st.metric("Notebooks", len(notebooks))
    
    # Competition Details
    if competition.get("title"):
        st.markdown(f"**Title:** {competition['title']}")
    if competition.get("reward"):
        st.markdown(f"**Reward:** {competition['reward']}")
    if competition.get("description"):
        with st.expander("📝 Description"):
            st.markdown(competition["description"])
    
    # Discussion Threads
    if threads:
        st.subheader("💬 Discussion Threads")
        
        # Create DataFrame for threads
        thread_df = pd.DataFrame([
            {
                "Title": thread.get("title", "Untitled"),
                "Author": thread.get("author", "Unknown"),
                "Replies": thread.get("replyCount", 0),
                "Votes": thread.get("voteCount", 0),
                "Posts": len(thread.get("posts", []))
            }
            for thread in threads
        ])
        
        st.dataframe(thread_df, use_container_width=True)
        
        # Thread details
        selected_thread = st.selectbox(
            "Select thread to view details:",
            options=range(len(threads)),
            format_func=lambda x: threads[x].get("title", f"Thread {x+1}")
        )
        
        if selected_thread is not None:
            thread = threads[selected_thread]
            st.markdown(f"**Thread:** {thread.get('title', 'Untitled')}")
            st.markdown(f"**Author:** {thread.get('author', 'Unknown')}")
            
            posts = thread.get("posts", [])
            if posts:
                st.markdown("**Posts:**")
                for i, post in enumerate(posts[:5]):  # Show first 5 posts
                    with st.expander(f"Post {i+1} by {post.get('author', 'Unknown')}"):
                        st.markdown(post.get("content", "No content"))
    
    # Notebooks
    if notebooks:
        st.subheader("📚 Notebooks")
        
        # Create DataFrame for notebooks
        notebook_df = pd.DataFrame([
            {
                "Title": notebook.get("title", "Untitled"),
                "Author": notebook.get("author", "Unknown"),
                "Votes": notebook.get("votes", 0),
                "Language": notebook.get("language", "Unknown"),
                "URL": notebook.get("url", "")
            }
            for notebook in notebooks
        ])
        
        st.dataframe(notebook_df, use_container_width=True)
    
    # Download options
    st.subheader("💾 Download Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # JSON download
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 Download JSON",
            data=json_data,
            file_name=f"{competition_slug}_data.json",
            mime="application/json"
        )
    
    with col2:
        # Markdown download
        scraper = KaggleCompetitionScraper()
        markdown_report = scraper.generate_markdown_report(data)
        st.download_button(
            label="📝 Download Markdown",
            data=markdown_report,
            file_name=f"{competition_slug}_report.md",
            mime="text/markdown"
        )
    
    with col3:
        # CSV download (threads summary)
        if threads:
            thread_df = pd.DataFrame([
                {
                    "Title": thread.get("title", "Untitled"),
                    "Author": thread.get("author", "Unknown"),
                    "Replies": thread.get("replyCount", 0),
                    "Votes": thread.get("voteCount", 0),
                    "URL": thread.get("url", "")
                }
                for thread in threads
            ])
            csv_data = thread_df.to_csv(index=False)
            st.download_button(
                label="📊 Download CSV (Threads)",
                data=csv_data,
                file_name=f"{competition_slug}_threads.csv",
                mime="text/csv"
            )
    
    # Raw data display
    with st.expander("🔍 View Raw JSON Data"):
        st.json(data)


if __name__ == "__main__":
    main()