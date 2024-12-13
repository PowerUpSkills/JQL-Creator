import gradio as gr
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

# Get the Groq API key from environment variable
def get_groq_api_key():
    return os.getenv("GROQ_API_KEY")

# Function to query the Groq API
def query_groq_api(search_query, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {
                "role": "system", 
                "content": """You are a helpful assistant that generates JQL queries for Jira based on natural language descriptions.
                            Follow these strict rules when creating JQL queries:
                            1. For Epics, ALWAYS use 'issuetype = "Program Epic"' (never use just 'Epic')
                            2. For Features, always use 'issuetype = "Feature"'
                            3. For Stories, use 'issuetype = "Story"'
                            4. For Enablers, use 'issuetype = "Enabler"'
                            5. When checking for text matches, use the tilde operator (~)
                            6. When dealing with parent/child relationships:
                               - Use 'parent in (issue in ...)' for parent relationships
                               - Use 'issue in (...)' for direct relationships
                            7. Always use proper parentheses for complex conditions with AND/OR
                            8. Remove any backticks or formatting from the output
                            
                            Respond only with the JQL query, without any explanations or additional text."""
            },
            {"role": "user", "content": f"Create a JQL query for the following request: {search_query}"}
        ],
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        jql = response.json()["choices"][0]["message"]["content"]
        return jql.strip()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 429:
            return "API key limit reached. Please try again later."
        else:
            return f"HTTP error occurred: {http_err}"
    except Exception as err:
        return f"Other error occurred: {err}"





# Function to create a JQL filter
def create_jql_filter(search_query):
    api_key = get_groq_api_key()
    jql = query_groq_api(search_query, api_key)
    return jql

# Function to refine the search query
def refine_query(search_query):
    return create_jql_filter(search_query)

# Function to reset the UI
def reset_ui():
    return "", ""

# Set up the Gradio interface
with gr.Blocks(theme=gr.themes.Soft()) as app:
    gr.Markdown("# Jira JQL Filter Creator")
    
    with gr.Row():
        with gr.Column(scale=1):
            search_query = gr.Textbox(
                label="Search Query",
                placeholder="Describe what you want to search for in natural language..."
            )
            jira_error = gr.Textbox(
                label="Paste Jira Error Message here for query refinement",
                placeholder="If the JQL query didn't work, paste the error message from Jira here..."
            )
            generate_button = gr.Button("Generate JQL")
            refine_button = gr.Button("Refine Query")
            done_button = gr.Button("Done")
        with gr.Column(scale=1):
            jql_output = gr.Textbox(
                label="JQL Query", 
                show_copy_button=True
            )
            explanation_output = gr.Markdown(label="Explanation")
    
    def process_response(response):
        # Remove any backticks and markdown formatting
        parts = response.split('\n\n', 1)
        jql = parts[0].strip().replace('```', '').replace('`', '')
        explanation = parts[1] if len(parts) > 1 else ""
        return jql, explanation
    
    def refine_with_error(search_query, error_message):
        combined_query = f"Original query: {search_query}\nJira error: {error_message}\nPlease fix the JQL query based on this error."
        return process_response(create_jql_filter(combined_query))
    
    generate_button.click(
        lambda x: process_response(create_jql_filter(x)),
        inputs=search_query,
        outputs=[jql_output, explanation_output]
    )
    refine_button.click(
        refine_with_error,
        inputs=[search_query, jira_error],
        outputs=[jql_output, explanation_output]
    )
    done_button.click(
        lambda: ("", "", "", ""),
        outputs=[search_query, jira_error, jql_output, explanation_output]
    )

# Launch the app
app.launch()
