# pip install azure-ai-projects~=1.0.0b7
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import BingGroundingTool
from dotenv import load_dotenv
load_dotenv()

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.getenv("PROJECT_CONNECTION_STRING")
    )
bing_connection = project_client.connections.get(
    connection_name="mrbing"
)
conn_id = bing_connection.id

print(conn_id)

# Initialize agent bing tool and add the connection id
bing = BingGroundingTool(connection_id=conn_id)

# Create agent with the bing tool and process assistant run
with project_client:
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="my-assistant",
        instructions="You are a helpful assistant",
        tools=bing.definitions,
        headers={"x-ms-enable-preview": "true"}
    )
    print(f"Created agent, ID: {agent.id}")
    
    # Create thread for communication
    thread = project_client.agents.create_thread()
    print(f"Created thread, ID: {thread.id}")

    # Create message to thread
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content="What is todays share price of MSFT?",
    )
    print(f"Created message, ID: {message.id}")

    # Create and process agent run in thread with tools
    run = project_client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")

    # Retrieve run step details to get Bing Search query link
    # To render the webpage, we recommend you replace the endpoint of Bing search query URLs with `www.bing.com` and your Bing search query URL would look like "https://www.bing.com/search?q={search query}"
    run_steps = project_client.agents.list_run_steps(run_id=run.id, thread_id=thread.id)
    run_steps_data = run_steps['data']
    print(f"Last run step detail: {run_steps_data}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # Fetch and log all messages
    messages = project_client.agents.list_messages(thread_id=thread.id)
    print(f"Messages: {messages}")
    # Extract the response message content
    resp = [text_message.text for text_message in messages.text_messages][0]

    # Create the object with answer and URLs
    response_object = {
        "answer": resp.value,
        "urls": [annotation.url_citation.url for annotation in resp.annotations]
    }
    print(f"Response Object: {response_object}")
    
    # Delete the assistant when done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")