# import logging

# from a2a.server.agent_execution import AgentExecutor, RequestContext
# from a2a.server.events import EventQueue
# from a2a.server.tasks import TaskUpdater
# from a2a.types import (
#     InternalError,
#     Part,
#     TaskState,
#     TextPart,
#     UnsupportedOperationError,
# )
# from a2a.utils.errors import ServerError
# from app.agent import KaitlynAgent

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class KaitlynAgentExecutor(AgentExecutor):
#     """Kaitlyn's Scheduling AgentExecutor."""

#     def __init__(self):
#         self.agent = KaitlynAgent()

#     async def execute(
#         self,
#         context: RequestContext,
#         event_queue: EventQueue,
#     ) -> None:
#         if not context.task_id or not context.context_id:
#             raise ValueError("RequestContext must have task_id and context_id")
#         if not context.message:
#             raise ValueError("RequestContext must have a message")

#         updater = TaskUpdater(event_queue, context.task_id, context.context_id)
#         if not context.current_task:
#             await updater.submit()
#         await updater.start_work()

#         query = context.get_user_input()
#         try:
#             async for item in self.agent.stream(query, context.context_id):
#                 is_task_complete = item["is_task_complete"]
#                 require_user_input = item["require_user_input"]
#                 parts = [Part(root=TextPart(text=item["content"]))]

#                 if not is_task_complete and not require_user_input:
#                     await updater.update_status(
#                         TaskState.working,
#                         message=updater.new_agent_message(parts),
#                     )
#                 elif require_user_input:
#                     await updater.update_status(
#                         TaskState.input_required,
#                         message=updater.new_agent_message(parts),
#                     )
#                     break
#                 else:
#                     await updater.add_artifact(
#                         parts,
#                         name="scheduling_result",
#                     )
#                     await updater.complete()
#                     break

#         except Exception as e:
#             logger.error(f"An error occurred while streaming the response: {e}")
#             raise ServerError(error=InternalError()) from e

#     async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
#         raise ServerError(error=UnsupportedOperationError())



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


class KaitlynnAgentExecutor(AgentExecutor):
    def __init__(self, runner: Runner):
        self.runner = runner

    def _run_agent(
        self, session_id: str, new_message: types.Content
    ) -> AsyncGenerator[Event, None]:
        print(f"Session id for kaitlynn_agent is {session_id}")
        return self.runner.run_async(
            session_id=session_id, user_id="kaitlynn_agent", new_message=new_message
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
            app_name=self.runner.app_name, user_id="kaitlynn_agent", session_id=session_id
        )
        print(f"Session for kaitlynn_agent is this {session} and Session id for kaitlynn_agent is {session_id}")
        if session is None:
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="kaitlynn_agent",
                session_id=session_id,
            )
        if session is None:
            raise RuntimeError(f"Failed to get or create session: {session_id}")
        return session


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    return [types.Part(text=p.root.text) for p in parts if isinstance(p.root, TextPart)]

def convert_genai_parts_to_a2a(parts: list[types.Part]) -> list[Part]:
    return [Part(root=TextPart(text=p.text)) for p in parts if p.text]
