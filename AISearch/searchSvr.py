import os
import json
from mcp.server.fastmcp import FastMCP
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'), override=True)

def replace_fields_in_format(file_name, fields_values):
    try:
        # Read the format string from the file
        file_path = os.path.join(os.path.dirname(__file__), "prompts", file_name)
        with open(file_path, 'r') as file:
            format_string = file.read()
        result = format_string.format(**fields_values)
        return result
    except FileNotFoundError:
        print(f"Error: File not found at {file_name}")
        return None
    except KeyError as e:
        print(f"Error: Missing key in fields_values: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# instantiate an MCP server client
mcp = FastMCP("Azure Search")

# create a static variable to hold the index schema
index_schema = None
search_svc_name = os.environ["AZURE_SEARCH_SERVICE_NAME"]
credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_ADMIN_KEY")) if os.getenv("AZURE_SEARCH_ADMIN_KEY") else DefaultAzureCredential()
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
azure_openai_chat_deployment = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4o")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

# DEFINE TOOLS
#Search web tool
# @mcp.tool()
def search(index_name: str, query: str) -> object:
    """Search using Azure Search index"""
    print(f"Searching {index_name} index for: {query}")  
    # If no schema, get it from the index
    global index_schema
    if index_schema is None or index_schema["name"] != index_name:
        url = f"https://{search_svc_name}.search.windows.net/indexes/{index_name}?api-version=2024-07-01"
        search_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + credential.get_token("https://search.azure.com/.default").token,
        }
        response = requests.get(url, headers=search_headers)
        if response.status_code == 200:
            index_schema = json.loads(response.text)
        sortable_fields = ",".join([field["name"] for field in index_schema["fields"] if (not field["type"].startswith("Collection")) and field["sortable"]])
        filterable_fields =",".join([field["name"] for field in index_schema["fields"] if (not field["type"].startswith("Collection")) and field["filterable"]])
        searchable_fields = ",".join([field["name"] for field in index_schema["fields"] if (not field["type"].startswith("Collection")) and field["searchable"]])
        prompt_fields = {
            "sortable_fields": sortable_fields,
            "filterable_fields": filterable_fields,
            "searchable_fields": searchable_fields
        }
        sortDescription = "no sorting" if not sortable_fields else replace_fields_in_format('sortPrompt.txt', prompt_fields)
        filterDescription = "no filtering" if not filterable_fields else replace_fields_in_format('filterPrompt.txt', prompt_fields)
        searchDescription = replace_fields_in_format('searchPrompt.txt', prompt_fields)
        funcDef_str = replace_fields_in_format('searchFunc.json', {
            "sortDescription": sortDescription,
            "filterDescription": filterDescription,
            "searchDescription": searchDescription
        })
        funcDef = json.loads(funcDef_str) if funcDef_str else None        
            
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        api_version=azure_openai_api_version,
        azure_endpoint=azure_openai_endpoint,
        api_key=azure_openai_key,
        azure_ad_token_provider=token_provider if not azure_openai_key else None
    )   

    # Note that 'call_search' is a non-existent function used here so that OpenAI returns correctly formatted json object (otherwise, it returns a markdown string with a json embedded)
    # and not a string. The function is not called, but the json object is returned in the response.
    # The function is defined in the prompt and the function name is used in the tool_choice parameter. 
    response = client.chat.completions.create(
        model=azure_openai_chat_deployment,
        messages=[
            {"role": "system", "content": "Use the following tools to answer the question."},
            {"role": "user", "content": query}
        ],
        tools=[
            {
                "type": "function",
                "function":funcDef
            }
        ],
        max_tokens=1000,
        tool_choice={ "type": "function", "function": { "name": "call_search" } },
    )
    response_message = response.choices[0].message    
    if len(response_message.tool_calls) == 1:
        try:
            query_options = json.loads(response_message.tool_calls[0].function.arguments)
        except:
            query_options = {}
    search_payload = {
        "search": query_options.get("search"),
        "filter": query_options.get("filter"),
        "orderby": query_options.get("orderby"),
        "top": query_options.get("top"),
        "skip": query_options.get("skip"),
        "select": query_options.get("select")
    }
    url = f"https://{search_svc_name}.search.windows.net/indexes/{index_name}?api-version=2024-07-01"
    search_headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + os.getenv("AZURE_SEARCH_ADMIN_KEY"),
    }
    response = requests.post(url, headers=search_headers, data=json.dumps(search_payload))
    if response.status_code == 200:
        response_object = {
            "answers" : response.json().get("value")
        }
    return response_object


# DEFINE RESOURCES
# Add a dynamic greeting resource
# @mcp.resource("help://{name}")
def show_help() -> str:
    return f""


    
 
 # execute and return the stdio output
if __name__ == "__main__":
    # mcp.run(transport="stdio")
    search("deserts", "Which the largest desert in the world?")



