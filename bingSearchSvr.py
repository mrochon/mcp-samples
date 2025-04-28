import os
from mcp.server.fastmcp import FastMCP
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import BingGroundingTool
from dotenv import load_dotenv
load_dotenv()

# instantiate an MCP server client
mcp = FastMCP("Bing Search")

# DEFINE TOOLS
#Search web tool
@mcp.tool()
def search(query: str) -> object:
    """Search bing"""
    print(f"Searching Bing for: {query}")
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=os.getenv("PROJECT_CONNECTION_STRING")
    )
    bing_connection = project_client.connections.get(connection_name="mrbing")
    bing = BingGroundingTool(connection_id=bing_connection.id)
    with project_client:
        agent = project_client.agents.create_agent(
            model="gpt-4o",
            name="bing-assistant",
            instructions="You are a helpful assistant",
            tools=bing.definitions,
            headers={"x-ms-enable-preview": "true"}
        )
        thread = project_client.agents.create_thread()
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=query
        )
        run = project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            raise Exception(f"Run failed: {run.last_error}")
        # run_steps = project_client.agents.list_run_steps(run_id=run.id, thread_id=thread.id)
        # run_steps_data = run_steps['data']
        messages = project_client.agents.list_messages(thread_id=thread.id)
        project_client.agents.delete_agent(agent.id)
        resp = [text_message.text for text_message in messages.text_messages][0]
        response_object = {
            "answer": resp.value,
            "urls": [annotation.url_citation.url for annotation in resp.annotations]
        }
        return response_object

# DEFINE RESOURCES
# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
    
 
 # execute and return the stdio output
if __name__ == "__main__":
    mcp.run(transport="stdio")



