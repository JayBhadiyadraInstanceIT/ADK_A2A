# import logging
# import os
# import sys

# import httpx
# import uvicorn
# from a2a.server.apps import A2AStarletteApplication
# from a2a.server.request_handlers import DefaultRequestHandler
# from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
# from a2a.types import (
#     AgentCapabilities,
#     AgentCard,
#     AgentSkill,
# )
# from app.agent import KaitlynAgent
# from app.agent_executor import KaitlynAgentExecutor
# from dotenv import load_dotenv

# load_dotenv()

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class MissingAPIKeyError(Exception):
#     """Exception for missing API key."""


# def main():
#     """Starts Kaitlyn's Agent server."""
#     host = "localhost"
#     port = 10004
#     try:
#         if not os.getenv("GOOGLE_API_KEY"):
#             raise MissingAPIKeyError("GOOGLE_API_KEY environment variable not set.")

#         capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
#         skill = AgentSkill(
#             id="schedule_pickleball",
#             name="Pickleball Scheduling Tool",
#             description="Helps with finding Kaitlyn's availability for pickleball",
#             tags=["scheduling", "pickleball"],
#             examples=["Are you free to play pickleball on Saturday?"],
#         )
#         agent_card = AgentCard(
#             name="Kaitlynn Agent",
#             description="Helps with scheduling pickleball games",
#             url=f"http://{host}:{port}/",
#             version="1.0.0",
#             defaultInputModes=KaitlynAgent.SUPPORTED_CONTENT_TYPES,
#             defaultOutputModes=KaitlynAgent.SUPPORTED_CONTENT_TYPES,
#             capabilities=capabilities,
#             skills=[skill],
#         )

#         httpx_client = httpx.AsyncClient()
#         request_handler = DefaultRequestHandler(
#             agent_executor=KaitlynAgentExecutor(),
#             task_store=InMemoryTaskStore(),
#             push_notifier=InMemoryPushNotifier(httpx_client),
#         )
#         server = A2AStarletteApplication(
#             agent_card=agent_card, http_handler=request_handler
#         )

#         uvicorn.run(server.build(), host=host, port=port)

#     except MissingAPIKeyError as e:
#         logger.error(f"Error: {e}")
#         sys.exit(1)
#     except Exception as e:
#         logger.error(f"An error occurred during server startup: {e}")
#         sys.exit(1)


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
from agent_executor import KaitlynnAgentExecutor
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
    port = 10004  # Kaitlynn uses a different port

    try:
        if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "TRUE":
            if not os.getenv("GOOGLE_API_KEY"):
                raise MissingAPIKeyError(
                    "GOOGLE_API_KEY not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE."
                )

        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="manage_schedule",
            name="Check Kaitlynn's Schedule",
            description="Checks Kaitlynn's availability for pickleball.",
            tags=["calendar", "availability"],
            examples=["Is Kaitlynn available tomorrow?"],
        )
        agent_card = AgentCard(
            name="Kaitlynn Agent",
            description="Helps manage Kaitlynn's pickleball schedule.",
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
        agent_executor = KaitlynnAgentExecutor(runner)

        request_handler = DefaultRequestHandler(
            agent_executor=agent_executor,
            task_store=InMemoryTaskStore(),
        )
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
