import os
from mcp.server.fastmcp import FastMCP
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
import requests
from dotenv import load_dotenv
load_dotenv(override=True)

# instantiate an MCP server client
mcp = FastMCP("Azure Search")

# create a static variable to hold the index schema
index_schema = None

# DEFINE TOOLS
#Search web tool
@mcp.tool()
def search(index_name: str, query: str) -> object:
    """Search using Azure Search index"""
    print(f"Searching {index_name} index for: {query}")  
    
    search_svc_name = os.environ["AZURE_SEARCH_SERVICE_NAME"]
    credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_ADMIN_KEY")) if os.getenv("AZURE_SEARCH_ADMIN_KEY") else DefaultAzureCredential()
    azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
    azure_openai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    azure_openai_model_name = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")
    azure_openai_chat_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o")
    azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    
    # If no schema, get it from the index
    if index_schema is None or index_schema["name"] != index_name:
        url = f"https://{search_svc_name}.search.windows.net/indexes/{index_name}?api-version=2024-07-01"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + os.getenv("AZURE_SEARCH_ADMIN_KEY"),
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            index_schema = response.json()
           
            
    # Get LLM client
    from openai import AzureOpenAI
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    openai_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(openai_credential, "https://cognitiveservices.azure.com/.default")

    client = AzureOpenAI(
        api_version=azure_openai_api_version,
        azure_endpoint=azure_openai_endpoint,
        api_key=azure_openai_key,
        azure_ad_token_provider=token_provider if not azure_openai_key else None
    )   
    with open("./prompts/sortDescription", "r", encoding="utf-8") as file:
        sort_description = file.read()
        
    response = client.chat.completions.create(
        model=azure_openai_chat_deployment,
        messages=[
            {"role": "system", "content": "Use the following tools to answer the question."},
            {"role": "user", "content": query}
        ],
        tools=tools,
        tool_choice={ "type": "function", "function": { "name": "call_search" } },
    )
    response_message = response.choices[0].message    
    # process the query

    # ------
    
    response_object = {
        "answer": "",
        "urls": [annotation.url_citation.url for annotation in resp.annotations]
    }
    return response_object


# DEFINE RESOURCES
# Add a dynamic greeting resource
@mcp.resource("help://{name}")
def show_help() -> str:
    return f""


    
 
 # execute and return the stdio output
if __name__ == "__main__":
    mcp.run(transport="stdio")



