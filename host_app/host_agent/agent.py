# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# from google.adk.agents import Agent
# from google.adk.tools import google_search  # Import the tool
# import asyncio
# import json
# import uuid
# from datetime import datetime
# from typing import Any, AsyncIterable, List

# import httpx
# import nest_asyncio
# from a2a.client import A2ACardResolver
# from a2a.types import (
#     AgentCard,
#     MessageSendParams,
#     SendMessageRequest,
#     SendMessageResponse,
#     SendMessageSuccessResponse,
#     Task,
# )
# from dotenv import load_dotenv
# from google.adk.agents.readonly_context import ReadonlyContext
# from google.adk.artifacts import InMemoryArtifactService
# from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.adk.tools.tool_context import ToolContext
# from google.genai import types

# from .pickleball_tools import (
#     book_pickleball_court,
#     list_court_availabilities,
# )
# from .remote_agent_connection import RemoteAgentConnections

# load_dotenv()
# nest_asyncio.apply()

# root_agent = Agent(
#    # A unique name for the agent.
#    name="google_search_agent",
#    # The Large Language Model (LLM) that agent will use.
#    # model="gemini-2.0-flash-exp", # if this model does not work, try below
#    model="gemini-2.0-flash-live-001",
#    # A short description of the agent's purpose.
#    description="Agent to answer questions using Google Search.",
#    # Instructions to set the agent's behavior.
#    instruction="Answer the question using the Google Search tool.",
#    # Add google_search tool to perform grounding with Google search.
#    tools=[google_search],
# )
#======================================================================================================================================================
# app/host_agent/agent.py
# import asyncio
# import json
# import uuid
# from datetime import datetime
# from typing import Any, AsyncIterable, List

# import httpx
# import nest_asyncio
# from a2a.client import A2ACardResolver
# from a2a.types import (
#     AgentCard,
#     MessageSendParams,
#     SendMessageRequest,
#     SendMessageResponse,
#     SendMessageSuccessResponse,
#     Task,
# )
# from dotenv import load_dotenv
# from google.adk import Agent
# from google.adk.agents.readonly_context import ReadonlyContext
# from google.adk.artifacts import InMemoryArtifactService
# from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.adk.tools.tool_context import ToolContext
# from google.genai import types
# from typing import Dict

# from .pickleball_tools import (
#     list_court_availabilities,
#     book_pickleball_court,
# )
# from .remote_agent_connection import RemoteAgentConnections

# load_dotenv()

# class HostAgent:
#     """The Host agent that delegates pickleball scheduling tasks to friends."""
#     def __init__(self):
#         self.remote_agent_connections: Dict[str, RemoteAgentConnections] = {}
#         self.cards: Dict[str, AgentCard] = {}
#         self.agents: List[AgentCard] = []
#         self._agent = self.create_agent()
#         self._user_id = "host_agent"
#         # Runner services for local agent reasoning (no persistence needed)
#         self._runner = Runner(
#             app_name=self._agent.name,
#             agent=self._agent,
#             artifact_service=InMemoryArtifactService(),
#             session_service=InMemorySessionService(),
#         )

#     async def _async_init_components(self, remote_agent_addresses: List[str]):
#         """
#         Initialize connections to remote friend agents via A2A.
#         """
#         # Fetch agent cards from each remote address
#         async with httpx.AsyncClient() as client:
#             for address in remote_agent_addresses:
#                 resolver = A2ACardResolver(httpx_client=client, base_url=address)
#                 # resolver = A2ACardResolver(base_url=address)
#                 agent_card = await resolver.get_agent_card()
#                 print(f"Discovered remote agent: {agent_card.name} at {address}")
#                 conn = RemoteAgentConnections(agent_card, address)
#                 self.remote_agent_connections[agent_card.name] = conn
#                 self.cards[agent_card.name] = agent_card
#                 self.agents.append(agent_card)
#         # Allow nested asyncio loops (useful if run inside other loops)
#         nest_asyncio.apply()

#     @classmethod
#     async def create(cls, remote_agent_addresses: List[str]):
#         instance = cls()
#         await instance._async_init_components(remote_agent_addresses)
#         return instance

#     def create_agent(self) -> Agent:
#         """Builds the Google ADK Agent object for the Host."""
#         return Agent(
#             # model="gemini-2.5-flash-preview-04-17",
#             model="gemini-2.0-flash-live-001",
#             name="Host_Agent",
#             instruction=self.root_instruction,
#             description="This Host agent orchestrates scheduling pickleball games with friends.",
#             tools=[
#                 self.send_message,
#                 book_pickleball_court,
#                 list_court_availabilities,
#             ],
#         )

#     def root_instruction(self, context: ReadonlyContext) -> str:
#         """Agent’s system message with role and directives for scheduling tasks."""
#         return (
#             "**Role:** You are the Host Agent, an expert scheduler for pickleball games. "
#             "You have a list of friends to invite and a pickleball court booking system.\n"
#             "**Core Directives:**\n"
#             "- **Initiate Planning:** Ask the user who to invite and desired date range.\n"
#             "- **Task Delegation:** Use `send_message` tool to ask each friend for availability.\n"
#             "- **Plan & Coordinate:** Compile replies, choose best time, and use the booking tools.\n"
#             "- **Failure:** If friends can't play, inform the user and cancel booking.\n"
#         )

#     # async def send_message(self, message_request: SendMessageRequest) -> SendMessageResponse:
#     #     """
#     #     Overrides the built-in send_message tool: dispatches a message to a remote friend via A2A.
#     #     """
#     #     agent_name = message_request.params.agent.card.name
#     #     if agent_name not in self.remote_agent_connections:
#     #         raise ValueError(f"Unknown agent: {agent_name}")
#     #     conn = self.remote_agent_connections[agent_name]
#     #     # Send message via the remote agent's A2A endpoint
#     #     response = await conn.send_message(message_request)
#     #     return response

#     async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
#         """Sends a task to a remote friend agent."""
#         # if agent_name not in self.remote_agent_connections:
#         #     raise ValueError(f"Agent {agent_name} not found")
#         # client = self.remote_agent_connections[agent_name]

#         # if not client:
#         #     raise ValueError(f"Client not available for {agent_name}")

#         alias_map = {
#         "kaitlynn": "Kaitlynn Agent",
#         "karley": "Karley Agent",
#         "nate": "Nate Agent"
#     }
#         key_lower = agent_name.strip().lower()
#         agent_key = alias_map.get(key_lower)
#         if not agent_key:
#             # Fallback: fuzzy-match if a partial substring matches
#             for key in self.remote_agent_connections:
#                 if key_lower in key.lower():
#                     agent_key = key
#                     break

#         if not agent_key:
#             raise ValueError(f"Agent {agent_name} not found")

#         # 🔁 Use the normalized agent key for lookups
#         client = self.remote_agent_connections.get(agent_key)
#         if not client:
#             raise ValueError(f"Client not available for {agent_key}")

#         # Use agent_key for logging if necessary
#         print(f"Routing task to agent: {agent_key}")

#         # Simplified task and context ID management
#         state = tool_context.state
#         task_id = state.get("task_id", str(uuid.uuid4()))
#         context_id = state.get("context_id", str(uuid.uuid4()))
#         message_id = str(uuid.uuid4())

#         payload = {
#             "message": {
#                 "role": "user",
#                 "parts": [{"type": "text", "text": task}],
#                 "messageId": message_id,
#                 "taskId": task_id,
#                 "contextId": context_id,
#             },
#         }

#         message_request = SendMessageRequest(
#             id=message_id, params=MessageSendParams.model_validate(payload)
#         )
#         send_response: SendMessageResponse = await client.send_message(message_request)
#         print("send_response", send_response)

#         if not isinstance(
#             send_response.root, SendMessageSuccessResponse
#         ) or not isinstance(send_response.root.result, Task):
#             print("Received a non-success or non-task response. Cannot proceed.")
#             return

#         response_content = send_response.root.model_dump_json(exclude_none=True)
#         json_content = json.loads(response_content)

#         resp = []
#         if json_content.get("result", {}).get("artifacts"):
#             for artifact in json_content["result"]["artifacts"]:
#                 if artifact.get("parts"):
#                     resp.extend(artifact["parts"])
#         return resp

#     # Methods to start the ADK agent reasoning loop
#     async def _async_main():
#         """
#         Initializes HostAgent with connections and returns its ADK Agent object.
#         """
#         # Friend agents (running separately) on their known ports:
#         friend_agent_urls = [
#             "http://localhost:10002",  # Karley's Agent
#             "http://localhost:10003",  # Nate's Agent
#             "http://localhost:10004",  # Kaitlynn's Agent
#         ]
#         print("Initializing HostAgent with friend agents at:", friend_agent_urls)
#         hosting_agent_instance = await HostAgent.create(remote_agent_addresses=friend_agent_urls)
#         print("HostAgent initialized.")
#         return hosting_agent_instance.create_agent()

#     @staticmethod
#     def _get_initialized_host_agent_sync() -> Agent:
#         """Synchronously initializes the Host agent (for module import)."""
#         try:
#             return asyncio.run(HostAgent._async_main())
#         except RuntimeError as e:
#             if "asyncio.run() cannot be called from a running event loop" in str(e):
#                 print(f"Warning: Already running event loop: {e}. Applying nest_asyncio.")
#                 nest_asyncio.apply()
#                 return asyncio.get_event_loop().run_until_complete(HostAgent._async_main())
#             else:
#                 raise

# # Create the global root_agent when the module is imported
# root_agent = HostAgent._get_initialized_host_agent_sync()
#======================================================================================================================================================
# import asyncio
# import json
# import uuid
# from datetime import datetime
# from typing import Any, AsyncIterable, List, Dict, Optional

# import httpx
# import nest_asyncio
# from a2a.client import A2ACardResolver
# from a2a.types import (
#     AgentCard,
#     MessageSendParams,
#     SendMessageRequest,
#     SendMessageResponse,
#     SendMessageSuccessResponse,
#     Task,
# )
# from dotenv import load_dotenv
# from google.adk import Agent
# from google.adk.agents.readonly_context import ReadonlyContext
# from google.adk.artifacts import InMemoryArtifactService
# from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
# from google.adk.runners import Runner
# from google.adk.sessions import InMemorySessionService
# from google.adk.tools.tool_context import ToolContext
# from google.genai import types

# from .pickleball_tools import (
#     list_court_availabilities,
#     book_pickleball_court,
# )
# from .remote_agent_connection import RemoteAgentConnections

# load_dotenv()

# class HostAgent:
#     """The Host agent that delegates pickleball scheduling tasks to friends."""
    
#     def __init__(self):
#         self.remote_agent_connections: Dict[str, RemoteAgentConnections] = {}
#         self.cards: Dict[str, AgentCard] = {}
#         self.agents: List[AgentCard] = []
#         self._agent = None
#         self._user_id = "host_agent"
#         self._runner = None
#         self._connection_timeout = 30  # seconds
        
#     async def _async_init_components(self, remote_agent_addresses: List[str]):
#         """Initialize connections to remote friend agents via A2A."""
#         connection_tasks = []
        
#         for address in remote_agent_addresses:
#             connection_tasks.append(self._connect_to_agent(address))
        
#         # Connect to all agents concurrently with timeout
#         try:
#             results = await asyncio.wait_for(
#                 asyncio.gather(*connection_tasks, return_exceptions=True),
#                 timeout=self._connection_timeout
#             )
            
#             successful_connections = 0
#             for i, result in enumerate(results):
#                 if isinstance(result, Exception):
#                     print(f"Failed to connect to agent at {remote_agent_addresses[i]}: {result}")
#                 else:
#                     successful_connections += 1
            
#             print(f"Successfully connected to {successful_connections}/{len(remote_agent_addresses)} agents")
            
#         except asyncio.TimeoutError:
#             print(f"Connection timeout after {self._connection_timeout} seconds")
        
#         # Apply nest_asyncio for compatibility
#         nest_asyncio.apply()
    
#     async def _connect_to_agent(self, address: str):
#         """Connect to a single remote agent with proper error handling."""
#         try:
#             async with httpx.AsyncClient(timeout=10.0) as client:
#                 resolver = A2ACardResolver(httpx_client=client, base_url=address)
#                 agent_card = await resolver.get_agent_card()
                
#                 print(f"Discovered remote agent: {agent_card.name} at {address}")
                
#                 conn = RemoteAgentConnections(agent_card, address)
#                 self.remote_agent_connections[agent_card.name] = conn
#                 self.cards[agent_card.name] = agent_card
#                 self.agents.append(agent_card)
                
#                 return True
                
#         except httpx.TimeoutException:
#             print(f"Timeout connecting to agent at {address}")
#             return False
#         except httpx.ConnectError:
#             print(f"Connection error to agent at {address}")
#             return False
#         except Exception as e:
#             print(f"Unexpected error connecting to agent at {address}: {e}")
#             return False

#     @classmethod
#     async def create(cls, remote_agent_addresses: List[str]):
#         """Create and initialize HostAgent instance."""
#         instance = cls()
#         await instance._async_init_components(remote_agent_addresses)
#         instance._agent = instance.create_agent()
        
#         # Initialize runner
#         instance._runner = Runner(
#             app_name=instance._agent.name,
#             agent=instance._agent,
#             artifact_service=InMemoryArtifactService(),
#             session_service=InMemorySessionService(),
#         )
        
#         return instance

#     def create_agent(self) -> Agent:
#         """Builds the Google ADK Agent object for the Host."""
#         return Agent(
#             model="gemini-2.0-flash-live-001",
#             name="Host_Agent",
#             instruction=self.root_instruction,
#             description="This Host agent orchestrates scheduling pickleball games with friends.",
#             tools=[
#                 self.send_message,
#                 book_pickleball_court,
#                 list_court_availabilities,
#             ],
#         )

#     def root_instruction(self, context: ReadonlyContext) -> str:
#         """Agent's system message with role and directives for scheduling tasks."""
#         available_agents = list(self.remote_agent_connections.keys())
#         agent_list = ", ".join(available_agents) if available_agents else "No agents available"
        
#         return (
#             "**Role:** You are the Host Agent, an expert scheduler for pickleball games. "
#             "You have a list of friends to invite and a pickleball court booking system.\n"
#             f"**Available Friends:** {agent_list}\n"
#             "**Core Directives:**\n"
#             "- **Initiate Planning:** Ask the user who to invite and desired date range.\n"
#             "- **Task Delegation:** Use `send_message` tool to ask each friend for availability.\n"
#             "- **Plan & Coordinate:** Compile replies, choose best time, and use the booking tools.\n"
#             "- **Failure Handling:** If friends can't play or agents are unavailable, inform the user and suggest alternatives.\n"
#             "- **Error Recovery:** If a friend agent doesn't respond, continue with available agents.\n"
#         )

#     async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
#         """Sends a task to a remote friend agent with improved error handling."""
        
#         # Normalize agent name
#         agent_key = self._normalize_agent_name(agent_name)
        
#         if not agent_key:
#             available_agents = ", ".join(self.remote_agent_connections.keys())
#             error_msg = f"Agent '{agent_name}' not found. Available agents: {available_agents}"
#             print(error_msg)
#             return [{"type": "text", "text": error_msg}]

#         client = self.remote_agent_connections.get(agent_key)
#         if not client:
#             error_msg = f"Client not available for {agent_key}"
#             print(error_msg)
#             return [{"type": "text", "text": error_msg}]

#         print(f"Routing task to agent: {agent_key}")

#         try:
#             # Generate unique IDs for this message
#             state = tool_context.state
#             task_id = state.get("task_id", str(uuid.uuid4()))
#             context_id = state.get("context_id", str(uuid.uuid4()))
#             message_id = str(uuid.uuid4())

#             payload = {
#                 "message": {
#                     "role": "user",
#                     "parts": [{"type": "text", "text": task}],
#                     "messageId": message_id,
#                     "taskId": task_id,
#                     "contextId": context_id,
#                 },
#             }

#             message_request = SendMessageRequest(
#                 id=message_id, 
#                 params=MessageSendParams.model_validate(payload)
#             )
            
#             # Send message with timeout
#             send_response: SendMessageResponse = await asyncio.wait_for(
#                 client.send_message(message_request),
#                 timeout=30.0  # 30 second timeout
#             )
            
#             print(f"Response from {agent_key}: Success")

#             # Validate response
#             if not isinstance(send_response.root, SendMessageSuccessResponse):
#                 error_msg = f"Received non-success response from {agent_key}"
#                 print(error_msg)
#                 return [{"type": "text", "text": error_msg}]
                
#             if not isinstance(send_response.root.result, Task):
#                 error_msg = f"Received non-task response from {agent_key}"
#                 print(error_msg)
#                 return [{"type": "text", "text": error_msg}]

#             # Parse response content
#             response_content = send_response.root.model_dump_json(exclude_none=True)
#             json_content = json.loads(response_content)

#             resp = []
#             if json_content.get("result", {}).get("artifacts"):
#                 for artifact in json_content["result"]["artifacts"]:
#                     if artifact.get("parts"):
#                         resp.extend(artifact["parts"])
            
#             if not resp:
#                 resp = [{"type": "text", "text": f"Received empty response from {agent_key}"}]
                
#             return resp

#         except asyncio.TimeoutError:
#             error_msg = f"Timeout waiting for response from {agent_key}"
#             print(error_msg)
#             return [{"type": "text", "text": error_msg}]
            
#         except Exception as e:
#             error_msg = f"Error communicating with {agent_key}: {str(e)}"
#             print(error_msg)
#             return [{"type": "text", "text": error_msg}]

#     def _normalize_agent_name(self, agent_name: str) -> Optional[str]:
#         """Normalize agent name to match available connections."""
#         if not agent_name:
#             return None
            
#         # Direct mapping for common aliases
#         alias_map = {
#             "kaitlynn": "Kaitlynn Agent",
#             "karley": "Karley Agent", 
#             "nate": "Nate Agent"
#         }
        
#         key_lower = agent_name.strip().lower()
        
#         # Check direct alias match
#         if key_lower in alias_map:
#             agent_key = alias_map[key_lower]
#             if agent_key in self.remote_agent_connections:
#                 return agent_key
        
#         # Check exact match
#         if agent_name in self.remote_agent_connections:
#             return agent_name
            
#         # Fuzzy match - check if partial substring matches
#         for key in self.remote_agent_connections:
#             if key_lower in key.lower() or key.lower() in key_lower:
#                 return key
                
#         return None

#     @staticmethod
#     async def _async_main():
#         """Initialize HostAgent with connections and return its ADK Agent object."""
#         friend_agent_urls = [
#             "http://localhost:10002",  # Karley's Agent
#             "http://localhost:10003",  # Nate's Agent
#             "http://localhost:10004",  # Kaitlynn's Agent
#         ]
        
#         print("Initializing HostAgent with friend agents at:", friend_agent_urls)
        
#         try:
#             hosting_agent_instance = await HostAgent.create(remote_agent_addresses=friend_agent_urls)
#             print("HostAgent initialized successfully.")
#             return hosting_agent_instance._agent
#         except Exception as e:
#             print(f"Error initializing HostAgent: {e}")
#             # Return a basic agent even if connections fail
#             fallback_instance = HostAgent()
#             fallback_instance._agent = fallback_instance.create_agent()
#             return fallback_instance._agent

#     @staticmethod
#     def _get_initialized_host_agent_sync() -> Agent:
#         """Synchronously initialize the Host agent (for module import)."""
#         try:
#             return asyncio.run(HostAgent._async_main())
#         except RuntimeError as e:
#             if "asyncio.run() cannot be called from a running event loop" in str(e):
#                 print(f"Warning: Already running event loop: {e}. Applying nest_asyncio.")
#                 nest_asyncio.apply()
#                 loop = asyncio.get_event_loop()
#                 return loop.run_until_complete(HostAgent._async_main())
#             else:
#                 raise

# # Create the global root_agent when the module is imported
# root_agent = HostAgent._get_initialized_host_agent_sync()
#===============================================================================================================================================================

import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Any, AsyncIterable, List

import httpx
import nest_asyncio
from a2a.client import A2ACardResolver
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.adk.tools import google_search
from google.genai import types

from .pickleball_tools import (
    book_pickleball_court,
    list_court_availabilities,
)
from .remote_agent_connection import RemoteAgentConnections

load_dotenv()
nest_asyncio.apply()


class HostAgent:
    """The Enhanced Host agent with multimodal capabilities (text + audio)."""

    def __init__(self):
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self.agents: str = ""
        self._agent = self.create_agent()
        self._user_id = "host_agent"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _async_init_components(self, remote_agent_addresses: List[str]):
        """Initialize connections to remote agents with better error handling."""
        async with httpx.AsyncClient(timeout=30) as client:
            for address in remote_agent_addresses:
                try:
                    card_resolver = A2ACardResolver(client, address)
                    card = await card_resolver.get_agent_card()
                    remote_connection = RemoteAgentConnections(
                        agent_card=card, agent_url=address
                    )
                    self.remote_agent_connections[card.name] = remote_connection
                    self.cards[card.name] = card
                    print(f"✅ Successfully connected to {card.name} at {address}")
                except httpx.ConnectError as e:
                    print(f"❌ Failed to connect to {address}: {e}")
                except Exception as e:
                    print(f"❌ Error initializing connection for {address}: {e}")
                    traceback.print_exc()

        agent_info = [
            json.dumps({"name": card.name, "description": card.description})
            for card in self.cards.values()
        ]
        print("📋 Connected agents:", [card.name for card in self.cards.values()])
        self.agents = "\n".join(agent_info) if agent_info else "No friends found"

    @classmethod
    async def create(cls, remote_agent_addresses: List[str]):
        """Factory method to create and initialize the HostAgent."""
        instance = cls()
        await instance._async_init_components(remote_agent_addresses)
        return instance

    def create_agent(self) -> Agent:
        """Create the agent with multimodal capabilities."""
        return Agent(
            # Use the multimodal model that supports both text and audio
            model="gemini-2.0-flash-live-001",
            name="Host_Agent", 
            instruction=self.root_instruction,
            description="This Host agent orchestrates scheduling pickleball with friends and can handle both text and audio interactions.",
            tools=[
                self.send_message,
                book_pickleball_court,
                list_court_availabilities,
                google_search,  # Add Google Search capability
            ],
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        """Enhanced root instruction with multimodal and search capabilities."""
        return f"""
        **Role:** You are the Host Agent, an expert scheduler for pickleball games with enhanced capabilities. You can handle both text and audio interactions, and you can search for information when needed.

        **Core Directives:**

        **Scheduling Functions:**
        * **Initiate Planning:** When asked to schedule a game, first determine who to invite and the desired date range from the user.
        * **Task Delegation:** Use the `send_message` tool to ask each friend for their availability.
            - Frame your request clearly (e.g., "Are you available for pickleball on 2025-06-25 between 17:00 and 18:00?").
            - Use the exact agent names: "Karley Agent", "Nate Agent", "Kaitlynn Agent"
        * **Analyze Responses:** Once you have availability from all friends, analyze the responses to find common timeslots.
        * **Check Court Availability:** Before proposing times to the user, use the `list_court_availabilities` tool to ensure the court is also free at the common timeslots.
        * **Propose and Confirm:** Present the common, court-available timeslots to the user for confirmation.
        * **Book the Court:** After the user confirms a time, use the `book_pickleball_court` tool to make the reservation. This tool requires a `start_time` and an `end_time` in format "YYYY-MM-DD HH:MM".
        * **Transparent Communication:** Relay the final booking confirmation, including the booking ID, to the user.

        **Enhanced Capabilities:**
        * **Multimodal Interaction:** You can understand and respond to both text and audio inputs. When responding to audio, be conversational and natural.
        * **Information Search:** Use the `google_search` tool when you need to find information about:
            - Local weather conditions for outdoor pickleball
            - Pickleball rules or regulations
            - Court locations and facilities
            - General information that might be helpful for scheduling
        * **Adaptive Communication:** Adjust your communication style based on the input modality:
            - For text: Use bullet points and structured responses
            - For audio: Use conversational, natural speech patterns

        **Operational Guidelines:**
        * **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions.
        * **No Permission Required:** Do not ask for permission before contacting friend agents.
        * **Friend Management:** Each available agent represents a friend. So "Karley Agent" represents Karley.
        * **Availability Queries:** When asked for which friends are available, return the names of the available friends (aka the agents that are active).
        * **Error Handling:** If a friend agent is not available, inform the user and proceed with available agents.
        * **Time Format:** Always use 24-hour format (17:00 instead of 5:00 PM) when communicating with other agents and tools.

        **Response Format:**
        * **Text Responses:** Use concise and easy to read format with bullet points when appropriate.
        * **Audio Responses:** Use natural, conversational language that flows well when spoken.

        **Today's Date (YYYY-MM-DD):** {datetime.now().strftime("%Y-%m-%d")}

        <Available Agents>
        {self.agents}
        </Available Agents>

        **Examples of Enhanced Capabilities:**
        - "What's the weather like for outdoor pickleball this weekend?" → Use google_search to find weather information
        - "Are there any new pickleball courts in our area?" → Use google_search to find local court information  
        - Standard scheduling requests → Use existing pickleball scheduling workflow

        **Important Notes:**
        - Always acknowledge user requests immediately
        - When checking friend availability, contact each friend individually
        - Provide clear status updates during the scheduling process
        - Handle errors gracefully and inform the user of any issues
        """

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """
        Streams the agent's response to a given query.
        Enhanced to handle multimodal responses with better error handling.
        """
        try:
            session = await self._runner.session_service.get_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
            )
            content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
            
            if session is None:
                session = await self._runner.session_service.create_session(
                    app_name=self._agent.name,
                    user_id=self._user_id,
                    state={},
                    session_id=session_id,
                )
            
            async for event in self._runner.run_async(
                user_id=self._user_id, session_id=session.id, new_message=content
            ):
                try:
                    if event.is_final_response():
                        response = ""
                        if (
                            event.content
                            and event.content.parts
                            and event.content.parts[0].text
                        ):
                            response = "\n".join(
                                [p.text for p in event.content.parts if p.text]
                            )
                        yield {
                            "is_task_complete": True,
                            "content": response,
                        }
                    else:
                        yield {
                            "is_task_complete": False,
                            "updates": "The host agent is thinking...",
                        }
                except Exception as e:
                    print(f"Error processing event in stream: {e}")
                    traceback.print_exc()
                    continue
                    
        except Exception as e:
            print(f"Error in stream method: {e}")
            traceback.print_exc()
            yield {
                "is_task_complete": True,
                "content": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
            }

    async def send_message(self, agent_name: str, task: str, tool_context: ToolContext):
        """Sends a task to a remote friend agent with better error handling."""
        try:
            print(f"🔄 Sending message to {agent_name}: {task}")
            
            if agent_name not in self.remote_agent_connections:
                available_agents = list(self.remote_agent_connections.keys())
                error_msg = f"Agent {agent_name} not found. Available agents: {available_agents}"
                print(f"❌ {error_msg}")
                return [{"text": error_msg}]
                
            client = self.remote_agent_connections[agent_name]

            if not client:
                error_msg = f"Client not available for {agent_name}"
                print(f"❌ {error_msg}")
                return [{"text": error_msg}]

            # Simplified task and context ID management
            state = tool_context.state
            task_id = state.get("task_id", str(uuid.uuid4()))
            context_id = state.get("context_id", str(uuid.uuid4()))
            message_id = str(uuid.uuid4())

            payload = {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": task}],
                    "messageId": message_id,
                    "taskId": task_id,
                    "contextId": context_id,
                },
            }

            message_request = SendMessageRequest(
                id=message_id, params=MessageSendParams.model_validate(payload)
            )
            
            send_response: SendMessageResponse = await client.send_message(message_request)
            print(f"✅ Received response from {agent_name}")

            if not isinstance(
                send_response.root, SendMessageSuccessResponse
            ) or not isinstance(send_response.root.result, Task):
                error_msg = f"Received invalid response from {agent_name}"
                print(f"❌ {error_msg}")
                return [{"text": error_msg}]

            response_content = send_response.root.model_dump_json(exclude_none=True)
            json_content = json.loads(response_content)

            resp = []
            if json_content.get("result", {}).get("artifacts"):
                for artifact in json_content["result"]["artifacts"]:
                    if artifact.get("parts"):
                        resp.extend(artifact["parts"])
            
            if not resp:
                # Extract text from the response if available
                if hasattr(send_response.root.result, 'artifacts') and send_response.root.result.artifacts:
                    for artifact in send_response.root.result.artifacts:
                        if hasattr(artifact, 'parts') and artifact.parts:
                            for part in artifact.parts:
                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                    resp.append({"text": part.root.text})
            
            print(f"📨 Response from {agent_name}: {resp}")
            return resp
            
        except Exception as e:
            error_msg = f"Error communicating with {agent_name}: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return [{"text": error_msg}]

    def get_agent(self) -> Agent:
        """Returns the configured agent."""
        return self._agent


def _get_initialized_host_agent_sync():
    """Synchronously creates and initializes the HostAgent."""

    async def _async_main():
        # Hardcoded URLs for the friend agents
        friend_agent_urls = [
            "http://localhost:10002",  # Karley's Agent
            "http://localhost:10003",  # Nate's Agent
            "http://localhost:10004",  # Kaitlynn's Agent
        ]

        print("🚀 Initializing host agent...")
        host_instance = await HostAgent.create(
            remote_agent_addresses=friend_agent_urls
        )
        print("✅ HostAgent initialized successfully!")
        return host_instance.get_agent()

    try:
        return asyncio.run(_async_main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print(
                f"⚠️  Warning: Could not initialize HostAgent with asyncio.run(): {e}. "
                "This can happen if an event loop is already running (e.g., in Jupyter). "
                "Consider initializing HostAgent within an async function in your application."
            )
        else:
            raise
    except Exception as e:
        print(f"❌ Error initializing HostAgent: {e}")
        traceback.print_exc()
        raise


# Create the root agent instance
print("🎾 Starting Pickleball Scheduling Host Agent...")
root_agent = _get_initialized_host_agent_sync()