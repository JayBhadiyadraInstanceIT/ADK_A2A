# from a2a.server.agent_execution import AgentExecutor, RequestContext
# from a2a.server.events import EventQueue
# from a2a.server.tasks import TaskUpdater
# from a2a.types import (
#     InternalError,
#     InvalidParamsError,
#     Part,
#     TextPart,
#     UnsupportedOperationError,
# )
# from a2a.utils.errors import ServerError
# from agent import SchedulingAgent


# class SchedulingAgentExecutor(AgentExecutor):
#     """AgentExecutor for the scheduling agent."""

#     def __init__(self):
#         """Initializes the SchedulingAgentExecutor."""
#         self.agent = SchedulingAgent()

#     async def execute(
#         self,
#         context: RequestContext,
#         event_queue: EventQueue,
#     ) -> None:
#         """Executes the scheduling agent."""
#         if not context.task_id or not context.context_id:
#             raise ValueError("RequestContext must have task_id and context_id")
#         if not context.message:
#             raise ValueError("RequestContext must have a message")

#         updater = TaskUpdater(event_queue, context.task_id, context.context_id)
#         if not context.current_task:
#             await updater.submit()
#         await updater.start_work()

#         if self._validate_request(context):
#             raise ServerError(error=InvalidParamsError())

#         query = context.get_user_input()
#         try:
#             result = self.agent.invoke(query)
#             print(f"Final Result ===> {result}")
#         except Exception as e:
#             print(f"Error invoking agent: {e}")
#             raise ServerError(error=InternalError()) from e

#         parts = [Part(root=TextPart(text=result))]

#         await updater.add_artifact(parts)
#         await updater.complete()

#     async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
#         """Handles task cancellation."""
#         raise ServerError(error=UnsupportedOperationError())

#     def _validate_request(self, context: RequestContext) -> bool:
#         """Validates the request context."""
#         return False


import logging
from collections.abc import AsyncGenerator

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.adk.events import Event
from google.genai import types

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NateAgentExecutor(AgentExecutor):
    def __init__(self, runner: Runner):
        self.runner = runner

    def _run_agent(
        self, session_id: str, new_message: types.Content
    ) -> AsyncGenerator[Event, None]:
        return self.runner.run_async(
            session_id=session_id, user_id="nate_agent", new_message=new_message
        )

    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        session_obj = await self._upsert_session(session_id)
        session_id = session_obj.id

        async for event in self._run_agent(session_id, new_message):
            if event.is_final_response():
                parts = convert_genai_parts_to_a2a(event.content.parts or [])
                task_updater.add_artifact(parts)
                task_updater.complete()
                break
            if not event.get_function_calls():
                task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts or [])
                    ),
                )

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        if not context.task_id or not context.context_id:
            raise ValueError("Missing task_id or context_id")
        if not context.message:
            raise ValueError("Missing message")

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            updater.submit()
        updater.start_work()

        await self._process_request(
            types.UserContent(parts=convert_a2a_parts_to_genai(context.message.parts)),
            context.context_id,
            updater,
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str):
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id="nate_agent", session_id=session_id
        )
        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="nate_agent",
                session_id=session_id,
            )
        if session is None:
            raise RuntimeError(f"Failed to get or create session: {session_id}")
        return session


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    return [types.Part(text=p.root.text) for p in parts if isinstance(p.root, TextPart)]

def convert_genai_parts_to_a2a(parts: list[types.Part]) -> list[Part]:
    return [Part(root=TextPart(text=p.text)) for p in parts if p.text]
