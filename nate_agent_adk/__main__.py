# """This file serves as the main entry point for the application.

# It initializes the A2A server, defines the agent's capabilities,
# and starts the server to handle incoming requests.
# """

# import logging
# import os

# import uvicorn
# from a2a.server.apps import A2AStarletteApplication
# from a2a.server.request_handlers import DefaultRequestHandler
# from a2a.server.tasks import InMemoryTaskStore
# from a2a.types import (
#     AgentCapabilities,
#     AgentCard,
#     AgentSkill,
# )
# from agent import SchedulingAgent
# from agent_executor import SchedulingAgentExecutor
# from dotenv import load_dotenv

# load_dotenv()

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class MissingAPIKeyError(Exception):
#     """Exception for missing API key."""


# def main():
#     """Entry point for Nate's Scheduling Agent."""
#     host = "localhost"
#     port = 10003
#     try:
#         if not os.getenv("GOOGLE_API_KEY"):
#             raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

#         capabilities = AgentCapabilities(streaming=False)
#         skill = AgentSkill(
#             id="availability_checker",
#             name="Availability Checker",
#             description="Check my calendar to see when I'm available for a pickleball game.",
#             tags=["schedule", "availability", "calendar"],
#             examples=[
#                 "Are you free tomorrow?",
#                 "Can you play pickleball next Tuesday at 5pm?",
#             ],
#         )

#         agent_host_url = os.getenv("HOST_OVERRIDE") or f"http://{host}:{port}/"
#         agent_card = AgentCard(
#             name="Nate Agent",
#             description="A friendly agent to help you schedule a pickleball game with Nate.",
#             url=agent_host_url,
#             version="1.0.0",
#             defaultInputModes=SchedulingAgent.SUPPORTED_CONTENT_TYPES,
#             defaultOutputModes=SchedulingAgent.SUPPORTED_CONTENT_TYPES,
#             capabilities=capabilities,
#             skills=[skill],
#         )

#         request_handler = DefaultRequestHandler(
#             agent_executor=SchedulingAgentExecutor(),
#             task_store=InMemoryTaskStore(),
#         )
#         server = A2AStarletteApplication(
#             agent_card=agent_card, http_handler=request_handler
#         )

#         uvicorn.run(server.build(), host=host, port=port)

#     except MissingAPIKeyError as e:
#         logger.error(f"Error: {e}")
#         exit(1)
#     except Exception as e:
#         logger.error(f"An error occurred during server startup: {e}")
#         exit(1)


# if __name__ == "__main__":
#     main()


import logging
import os
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent import create_agent
from agent_executor import NateAgentExecutor  
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingAPIKeyError(Exception):
    pass

def main():
    host = "localhost"
    port = 10003  # NATE PORT

    try:
        if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
            if not os.getenv("GOOGLE_API_KEY"):
                raise MissingAPIKeyError("Missing GOOGLE_API_KEY.")

        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="check_schedule",
            name="Check Nate's Schedule",
            description="Checks Nate's availability.",
            tags=["calendar"],
            examples=["When is Nate free tomorrow?"],
        )

        agent_card = AgentCard(
            name="Nate Agent",
            description="Handles Nate's schedule.",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            capabilities=capabilities,
            skills=[skill],
        )

        adk_agent = create_agent()
        runner = Runner(
            app_name=agent_card.name,
            agent=adk_agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        agent_executor = NateAgentExecutor(runner)

        request_handler = DefaultRequestHandler(agent_executor=agent_executor, task_store=InMemoryTaskStore())
        server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Startup error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
