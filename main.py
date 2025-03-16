import os
import json
import langgraph
from openai import OpenAI
from crawl4ai import Crawler

# Initialize OpenAI and Crawl4AI Clients
client = OpenAI()
crawler = Crawler()

# Define Workflow State
class BlogState:
    def __init__(self):
        self.topic = None
        self.research_data = None
        self.outline = None
        self.content = None
        self.critique = None
        self.image_paths = []
        self.evaluation = None

# Define Input Guardrails
def sanitize_input(text: str) -> str:
    """Sanitize input to prevent harmful or misleading queries and ensure it's a technical topic."""
    disallowed_words = ["hack", "illegal", "scam", "plagiarize"]
    technical_keywords = ["programming", "AI", "machine learning", "software", "cloud", "database", "networking", "cybersecurity", "blockchain", "data science"]
    
    if any(word in text.lower() for word in disallowed_words):
        raise ValueError("Input contains disallowed content.")
    
    if not any(keyword in text.lower() for keyword in technical_keywords):
        raise ValueError("Input must be related to a technical topic.")
    
    return text.strip()

# Define Output Guardrails
def validate_output(text: str) -> str:
    """Ensure the output is appropriate and fact-based."""
    if len(text) < 100:
        raise ValueError("Generated content is too short.")
    if "lorem ipsum" in text.lower():
        raise ValueError("Generated content is placeholder text.")
    return text

# Define Workflow Nodes

def research_node(state: BlogState):
    """Fetch relevant information from the web using Crawl4AI."""
    state.topic = sanitize_input(state.topic)
    query = f"Latest insights on {state.topic}"
    response = crawler.search(query, num_results=5)
    state.research_data = [result["url"] for result in response["results"]]
    return state

def outline_node(state: BlogState):
    """Generate a structured outline from research data."""
    prompt = f"Generate a structured outline for a technical blog on {state.topic} based on these references: {state.research_data}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are an expert technical writer."},
                  {"role": "user", "content": prompt}]
    )
    state.outline = validate_output(response.choices[0].message.content)
    return state

def write_node(state: BlogState):
    """Write the blog content based on the outline."""
    prompt = f"Write a detailed technical blog post on {state.topic} following this outline: {state.outline}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are an expert technical blogger."},
                  {"role": "user", "content": prompt}]
    )
    state.content = validate_output(response.choices[0].message.content)
    return state

def generate_images_node(state: BlogState):
    """Generate diagrams for the blog content using OpenAI's DALL-E."""
    prompt = f"Generate a simple and clear diagram for the topic: {state.topic}"
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    folder = f"blog_output/{state.topic}/images"
    os.makedirs(folder, exist_ok=True)
    image_path = f"{folder}/diagram.png"
    os.system(f"wget -O {image_path} {image_url}")  # Download image
    state.image_paths.append(image_path)
    return state

def critique_node(state: BlogState):
    """Review and refine the content."""
    prompt = f"Critique and improve the following technical blog content: {state.content}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are a professional editor."},
                  {"role": "user", "content": prompt}]
    )
    state.critique = validate_output(response.choices[0].message.content)
    return state

def evaluation_node(state: BlogState):
    """Evaluate the blog content based on technical depth, clarity, and completeness."""
    prompt = f"Evaluate the following technical blog content for accuracy, clarity, depth, and completeness. Provide a structured feedback report: {state.critique or state.content}"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": "You are an expert technical reviewer."},
                  {"role": "user", "content": prompt}]
    )
    state.evaluation = validate_output(response.choices[0].message.content)
    return state

def save_output_node(state: BlogState):
    """Save the final output in a structured folder."""
    folder = f"blog_output/{state.topic}"
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/README.md", "w") as f:
        f.write(state.critique or state.content or "")
    metadata = {
        "title": state.topic,
        "description": "Generated technical blog post",
        "tags": [],
        "date_created": "2025-03-15",
        "programming_languages_used": [],
        "references": state.research_data,
        "images": state.image_paths,
        "evaluation": state.evaluation
    }
    with open(f"{folder}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
    return state

# Create LangGraph Workflow
graph = langgraph.Graph()
graph.add_node("research", research_node)
graph.add_node("outline", outline_node)
graph.add_node("write", write_node)
graph.add_node("generate_images", generate_images_node)
graph.add_node("critique", critique_node)
graph.add_node("evaluation", evaluation_node)
graph.add_node("save_output", save_output_node)

# Define Execution Order
graph.add_edge("research", "outline")
graph.add_edge("outline", "write")
graph.add_edge("write", "generate_images")
graph.add_edge("generate_images", "critique")
graph.add_edge("critique", "evaluation")
graph.add_edge("evaluation", "save_output")

# Set Entry Point
graph.set_entry_point("research")

# Instantiate and Run Workflow
workflow = graph.compile()
state = BlogState()
state.topic = "Introduction to LangGraph"
workflow.invoke(state)
