import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Streamlit App Title
st.title("Google News Content Extractor")

# User Input Options
st.sidebar.header("Input Options")
option = st.sidebar.radio("Choose input method:", ("Google News Sitemap", "Upload CSV", "Enter URLs Manually"))

# Session for requests
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})

# Function to fetch URLs from Sitemap
def fetch_sitemap_urls(sitemap_url):
    try:
        response = session.get(sitemap_url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                     'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
        urls = []
        for url_element in root.findall("ns:url", namespace):
            loc = url_element.find("ns:loc", namespace)
            if loc is not None:
                urls.append(loc.text)
        return urls
    except Exception as e:
        st.error(f"Error fetching sitemap: {e}")
        return []

# Function to extract content from URL
def extract_content(url, css_selector):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        element = soup.select_one(css_selector)
        if element:
            return element.get_text(separator=" ", strip=True)
        else:
            return "Content not found"
    except Exception as e:
        return f"Error: {e}"

# Collect URLs based on user selection
urls = []
if option == "Google News Sitemap":
    sitemap_url = st.sidebar.text_input("Enter Google News Sitemap URL:")
    if st.sidebar.button("Fetch URLs") and sitemap_url:
        urls = fetch_sitemap_urls(sitemap_url)
        st.sidebar.success(f"Fetched {len(urls)} URLs from sitemap.")

elif option == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload CSV file with URLs", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if "URL" in df.columns:
            urls = df["URL"].dropna().tolist()
            st.sidebar.success(f"Loaded {len(urls)} URLs from CSV.")
        else:
            st.sidebar.error("CSV must contain a column named 'URL'")

elif option == "Enter URLs Manually":
    manual_urls = st.sidebar.text_area("Enter URLs (one per line):")
    if manual_urls:
        urls = manual_urls.split("\n")
        urls = [url.strip() for url in urls if url.strip()]
        st.sidebar.success(f"Loaded {len(urls)} URLs manually.")

# CSS Selector Input
css_selector = st.text_input("Enter CSS Selector for extracting content:")

# Process URLs
if st.button("Extract Content") and urls and css_selector:
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_content, url, css_selector): url for url in urls}
        for future in futures:
            url = futures[future]
            content = future.result()
            results.append({"URL": url, "Extracted Content": content})

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    st.write(results_df)

    # Provide download link for results
    csv = results_df.to_csv(index=False).encode("utf-8")
    st.download_button(label="Download CSV", data=csv, file_name="extracted_content.csv", mime="text/csv")
