from typing import Callable

import httpx
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from dotenv import load_dotenv

load_dotenv()

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):
        print(f"agent_card: {agent_card}")
        print(f"agent_url: {agent_url}")
        self._httpx_client = httpx.AsyncClient(timeout=30)
        self.agent_client = A2AClient(self._httpx_client, agent_card, url=agent_url)
        self.card = agent_card
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(
        self, message_request: SendMessageRequest
    ) -> SendMessageResponse:
        return await self.agent_client.send_message(message_request)


# from typing import Callable
# import asyncio
# import httpx
# from a2a.client import A2AClient
# from a2a.types import (
#     AgentCard,
#     SendMessageRequest,
#     SendMessageResponse,
#     Task,
#     TaskArtifactUpdateEvent,
#     TaskStatusUpdateEvent,
# )
# from dotenv import load_dotenv

# load_dotenv()

# TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
# TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


# class RemoteAgentConnections:
#     """A class to hold the connections to the remote agents with improved error handling."""

#     def __init__(self, agent_card: AgentCard, agent_url: str):
#         print(f"Initializing connection to agent: {agent_card.name} at {agent_url}")
        
#         # Create a persistent HTTP client with appropriate timeouts
#         self._httpx_client = httpx.AsyncClient(
#             timeout=httpx.Timeout(30.0, connect=10.0),
#             limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
#             follow_redirects=True
#         )
        
#         self.agent_client = A2AClient(self._httpx_client, agent_card, url=agent_url)
#         self.card = agent_card
#         self.agent_url = agent_url
#         self.conversation_name = None
#         self.conversation = None
#         self.pending_tasks = set()
#         self._connection_healthy = True
#         self._last_successful_request = None

#     def get_agent(self) -> AgentCard:
#         """Return the agent card."""
#         return self.card

#     async def send_message(self, message_request: SendMessageRequest) -> SendMessageResponse:
#         """Send a message to the remote agent with retry logic and error handling."""
#         max_retries = 3
#         retry_delay = 1.0
        
#         for attempt in range(max_retries):
#             try:
#                 # Check if we need to recreate the HTTP client
#                 if not self._connection_healthy:
#                     await self._recreate_client()
                
#                 # Send the message
#                 response = await self.agent_client.send_message(message_request)
#                 self._connection_healthy = True
#                 self._last_successful_request = asyncio.get_event_loop().time()
#                 return response
                
#             except httpx.TimeoutException as e:
#                 print(f"Timeout on attempt {attempt + 1} to {self.card.name}: {e}")
#                 if attempt < max_retries - 1:
#                     await asyncio.sleep(retry_delay * (attempt + 1))
#                     continue
#                 else:
#                     self._connection_healthy = False
#                     raise
                    
#             except httpx.ConnectError as e:
#                 print(f"Connection error on attempt {attempt + 1} to {self.card.name}: {e}")
#                 self._connection_healthy = False
#                 if attempt < max_retries - 1:
#                     await asyncio.sleep(retry_delay * (attempt + 1))
#                     await self._recreate_client()
#                     continue
#                 else:
#                     raise
                    
#             except httpx.HTTPStatusError as e:
#                 print(f"HTTP error on attempt {attempt + 1} to {self.card.name}: {e.response.status_code}")
#                 if e.response.status_code >= 500 and attempt < max_retries - 1:
#                     # Retry on server errors
#                     await asyncio.sleep(retry_delay * (attempt + 1))
#                     continue
#                 else:
#                     raise
                    
#             except Exception as e:
#                 print(f"Unexpected error on attempt {attempt + 1} to {self.card.name}: {e}")
#                 if attempt < max_retries - 1:
#                     await asyncio.sleep(retry_delay * (attempt + 1))
#                     continue
#                 else:
#                     raise

#     async def _recreate_client(self):
#         """Recreate the HTTP client and A2A client."""
#         try:
#             # Close the old client
#             await self._httpx_client.aclose()
#         except Exception as e:
#             print(f"Error closing old client: {e}")
        
#         # Create new client
#         self._httpx_client = httpx.AsyncClient(
#             timeout=httpx.Timeout(30.0, connect=10.0),
#             limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
#             follow_redirects=True
#         )
        
#         # Recreate A2A client
#         self.agent_client = A2AClient(self._httpx_client, self.card, url=self.agent_url)
#         print(f"Recreated client for {self.card.name}")

#     async def health_check(self) -> bool:
#         """Perform a health check on the connection."""
#         try:
#             # You could implement a simple ping or status check here
#             # For now, we'll just check if the client is still valid
#             return self._connection_healthy and not self._httpx_client.is_closed
#         except Exception:
#             return False

#     async def close(self):
#         """Close the connection and clean up resources."""
#         try:
#             await self._httpx_client.aclose()
#         except Exception as e:
#             print(f"Error closing connection to {self.card.name}: {e}")
#         finally:
#             self._connection_healthy = False

#     def __del__(self):
#         """Cleanup when the object is destroyed."""
#         try:
#             if hasattr(self, '_httpx_client') and not self._httpx_client.is_closed:
#                 # We can't await here, but we can at least try to close
#                 import warnings
#                 warnings.warn(f"RemoteAgentConnection to {self.card.name} was not properly closed")
#         except Exception:
#             pass