from typing import List, Dict
import json
from mistralai import Any
import requests
from exa_py import Exa

# from smolagents.agents import ToolCallingAgent
from smolagents import CodeAgent, tool, LiteLLMModel
from dotenv import load_dotenv
import os
from google import genai

from apify_client import ApifyClient



load_dotenv()
exa = Exa(api_key=os.getenv("EXA_API_KEY"))# Initialize the ApifyClient with your API token
client = ApifyClient(os.getenv("APIFY_API_TOKEN"))


@tool
def get_latest_tweets_from_twitter(query: str) -> List[Dict]:
    """
    Get the latest tweets from Twitter

    Args:
        query: The query to search for
    
    Returns:
        List[Dict]: The latest tweets from Twitter
    """
    
    # Get user's last tweets
    url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
    headers = {"X-API-Key": os.getenv("TWITTER_IO_API_KEY")}
    params = {"query": f"{query} since:2025-03-12", "queryType": "Top"}

    response = requests.request("GET", url, headers=headers, params=params)
    resp = response.text
    return json.loads(resp)['tweets']

@tool
def get_latest_discussion_from_youtube(query: str) -> List[Dict]:
    """
    Get the latest discussion from YouTube

    Args:
        query: The query to search for
    
    Returns:
        List[Dict]: The latest discussion from YouTube
    """
    
    # Prepare the Actor input
    run_input = {
        "oldestPostDate": "2025-03-12",
        "dateFilter": "week",
        "downloadSubtitles": True,
        "maxResultStreams": 0,
        "maxResults": 10,
        "maxResultsShorts": 0,
        "preferAutoGeneratedSubtitles": False,
        "saveSubsToKVS": True,
        "searchQueries": [
            "cursor"
        ],
        "subtitlesLanguage": "en"
    }

    # Run the Actor and wait for it to finish
    run = client.actor("h7sDV53CddomktSi5").call(run_input=run_input)

    # Fetch and print Actor results from the run's dataset (if there are any)
    return  list(client.dataset(run["defaultDatasetId"]).iterate_items())

    

@tool
def get_latest_discussion_from_linkedin(query: str) -> List[Dict]:
    """
    Get the latest discussion from LinkedIn

    Args:
        query: The query to search for
    
    Returns:
        List[Dict]: The latest discussion from LinkedIn
    """
    r = exa.search_and_contents(query, text=True, include_domains=["linkedin.com"], use_autoprompt=True, start_published_date="2025-03-12")
    # Convert SearchResponse results to dictionaries
    return [
        {
            "id": result.id,
            "title": result.title,
            "url": result.url,
            "published_date": result.published_date,
            "author": result.author,
            "text": result.text,
            "score": result.score
        } 
        for result in r.results
    ]


@tool
def save_to_local_file(content: str, filename: str) -> str:
    """
    Save the content to a local file

    Args:
        content: The content to save
        filename: The filename to save the content to

    Returns:
        str: The path to the saved file
    """
    with open(filename, "w") as f:
        f.write(content)
    return filename

@tool
def summarize_discussion(discussion: Any) -> str:
    """
    Summarize a discussion into bullet points

    Args:
        discussion: The discussion to summarize

    Returns:
        str: The summarized discussion in bullet point format
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Handle potential serialization issues with complex objects
    try:
        discussion_str = json.dumps(discussion)
    except TypeError:
        # If the discussion object is not directly JSON serializable
        if hasattr(discussion, "__dict__"):
            discussion_str = json.dumps(discussion.__dict__)
        else:
            # Create a simple string representation as a fallback
            discussion_str = str(discussion)
    
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents=[
            "Summarize the following discussion into clear, concise bullet points. Focus on the main topics, key opinions, and important facts:\n\n" + discussion_str
        ]
    )
    return response.text


model = LiteLLMModel(model_id="gemini/gemini-2.0-flash", api_key=os.getenv("GEMINI_API_KEY"))

agent = CodeAgent(
    tools=[
        get_latest_tweets_from_twitter,
        get_latest_discussion_from_youtube,
        get_latest_discussion_from_linkedin,
        summarize_discussion,
        save_to_local_file
    ],
    model=model,
    additional_authorized_imports=['codec']
)

# Uncomment the line below to run the agent with a specific query

agent.run("""
    What's the latest discussion about cursor on all channels? 
    Save discussions to a local markdown file with a standarized format, named cursor.md
    Each discussion should contain author, date, bullet point summarization, and a citation link.
    """
)