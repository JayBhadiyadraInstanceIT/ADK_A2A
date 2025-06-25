# import random
# from collections.abc import AsyncIterable
# from datetime import date, datetime, timedelta
# from typing import Any, List, Literal

# from langchain_core.messages import AIMessage, ToolMessage
# from langchain_core.runnables import RunnableConfig
# from langchain_core.tools import tool
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langgraph.checkpoint.memory import MemorySaver
# from langgraph.prebuilt import create_react_agent
# from pydantic import BaseModel, Field

# memory = MemorySaver()


# def generate_kaitlyns_calendar() -> dict[str, list[str]]:
#     """Generates Kaitlyn's calendar for the next 7 days."""
#     calendar = {}
#     today = date.today()
#     # Kaitlyn's availability: evenings on weekdays, more free on weekends.
#     for i in range(7):
#         current_date = today + timedelta(days=i)
#         date_str = current_date.strftime("%Y-%m-%d")
#         day_of_week = current_date.weekday()  # Monday is 0 and Sunday is 6

#         if day_of_week < 5:  # Weekday
#             possible_times = [f"{h:02}:00" for h in range(18, 22)]  # 6 PM to 10 PM
#             available_slots = sorted(
#                 random.sample(possible_times, random.randint(2, 3))
#             )
#         else:  # Weekend
#             possible_times = [f"{h:02}:00" for h in range(10, 20)]  # 10 AM to 8 PM
#             available_slots = sorted(
#                 random.sample(possible_times, random.randint(4, 6))
#             )

#         calendar[date_str] = available_slots
#     return calendar


# KAITLYNS_CALENDAR = generate_kaitlyns_calendar()


# class AvailabilityToolInput(BaseModel):
#     """Input schema for the availability tool."""

#     date_range: str = Field(
#         ...,
#         description=(
#             "The date or date range to check for availability, e.g., "
#             "'2024-07-28' or '2024-07-28 to 2024-07-30'."
#         ),
#     )


# @tool(args_schema=AvailabilityToolInput)
# def get_availability(date_range: str) -> str:
#     """Use this to get Kaitlyn's availability for a given date or date range."""
#     dates_to_check = [d.strip() for d in date_range.split("to")]
#     start_date_str = dates_to_check[0]
#     end_date_str = dates_to_check[-1]

#     try:
#         start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
#         end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

#         if start > end:
#             return "Invalid date range. The start date cannot be after the end date."

#         results = []
#         delta = end - start
#         for i in range(delta.days + 1):
#             day = start + timedelta(days=i)
#             date_str = day.strftime("%Y-%m-%d")
#             available_slots = KAITLYNS_CALENDAR.get(date_str, [])
#             if available_slots:
#                 availability = (
#                     f"On {date_str}, Kaitlyn is available at: "
#                     f"{', '.join(available_slots)}."
#                 )
#                 results.append(availability)
#             else:
#                 results.append(f"Kaitlyn is not available on {date_str}.")

#         return "\n".join(results)

#     except ValueError:
#         return (
#             "I couldn't understand the date. "
#             "Please ask to check availability for a date like 'YYYY-MM-DD'."
#         )


# class ResponseFormat(BaseModel):
#     """Respond to the user in this format."""

#     status: Literal["input_required", "completed", "error"] = "input_required"
#     message: str


# class KaitlynAgent:
#     """KaitlynAgent - a specialized assistant for scheduling."""

#     SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

#     SYSTEM_INSTRUCTION = (
#         "You are Kaitlyn's scheduling assistant. "
#         "Your sole purpose is to use the 'get_availability' tool to answer questions about Kaitlyn's schedule for playing pickleball. "
#         "You will be provided with the current date to help you understand relative date queries like 'tomorrow' or 'next week'. "
#         "Use this information to correctly call the tool with a specific date (e.g., 'YYYY-MM-DD'). "
#         "If the user asks about anything other than scheduling pickleball, "
#         "politely state that you cannot help with that topic and can only assist with scheduling queries. "
#         "Do not attempt to answer unrelated questions or use tools for other purposes."
#         "Set response status to input_required if the user needs to provide more information."
#         "Set response status to error if there is an error while processing the request."
#         "Set response status to completed if the request is complete."
#     )

#     def __init__(self):
#         self.model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
#         self.tools = [get_availability]

#         self.graph = create_react_agent(
#             self.model,
#             tools=self.tools,
#             checkpointer=memory,
#             prompt=self.SYSTEM_INSTRUCTION,
#             response_format=ResponseFormat,
#         )

#     def invoke(self, query, context_id):
#         config: RunnableConfig = {"configurable": {"thread_id": context_id}}
#         today_str = f"Today's date is {date.today().strftime('%Y-%m-%d')}."
#         augmented_query = f"{today_str}\n\nUser query: {query}"
#         self.graph.invoke({"messages": [("user", augmented_query)]}, config)
#         return self.get_agent_response(config)

#     async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
#         today_str = f"Today's date is {date.today().strftime('%Y-%m-%d')}."
#         augmented_query = f"{today_str}\n\nUser query: {query}"
#         inputs = {"messages": [("user", augmented_query)]}
#         config: RunnableConfig = {"configurable": {"thread_id": context_id}}

#         for item in self.graph.stream(inputs, config, stream_mode="values"):
#             message = item["messages"][-1]
#             if (
#                 isinstance(message, AIMessage)
#                 and message.tool_calls
#                 and len(message.tool_calls) > 0
#             ):
#                 yield {
#                     "is_task_complete": False,
#                     "require_user_input": False,
#                     "content": "Checking Kaitlyn's availability...",
#                 }
#             elif isinstance(message, ToolMessage):
#                 yield {
#                     "is_task_complete": False,
#                     "require_user_input": False,
#                     "content": "Processing availability...",
#                 }

#         yield self.get_agent_response(config)

#     def get_agent_response(self, config):
#         current_state = self.graph.get_state(config)
#         structured_response = current_state.values.get("structured_response")
#         if structured_response and isinstance(structured_response, ResponseFormat):
#             if structured_response.status == "input_required":
#                 return {
#                     "is_task_complete": False,
#                     "require_user_input": True,
#                     "content": structured_response.message,
#                 }
#             if structured_response.status == "error":
#                 return {
#                     "is_task_complete": False,
#                     "require_user_input": True,
#                     "content": structured_response.message,
#                 }
#             if structured_response.status == "completed":
#                 return {
#                     "is_task_complete": True,
#                     "require_user_input": False,
#                     "content": structured_response.message,
#                 }

#         return {
#             "is_task_complete": False,
#             "require_user_input": True,
#             "content": (
#                 "We are unable to process your request at the moment. "
#                 "Please try again."
#             ),
#         }



import random
from datetime import date, datetime, timedelta

from google.adk.agents import LlmAgent


def generate_kaitlynn_calendar() -> dict[str, list[str]]:
    calendar = {}
    today = date.today()
    possible_times = [f"{h:02}:00" for h in range(8, 20)]

    for i in range(7):
        current_date = today + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        available_slots = sorted(random.sample(possible_times, 6))  # Slightly different from Karley
        calendar[date_str] = available_slots

    print("Kaitlynn's calendar:", calendar)
    return calendar


KAITLYNN_CALENDAR = generate_kaitlynn_calendar()


def get_availability(start_date: str, end_date: str) -> str:
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            return "Invalid date range. Start date is after end date."

        results = []
        for i in range((end - start).days + 1):
            current_day = start + timedelta(days=i)
            date_str = current_day.strftime("%Y-%m-%d")
            slots = KAITLYNN_CALENDAR.get(date_str, [])
            if slots:
                results.append(f"On {date_str}, Kaitlynn is available at: {', '.join(slots)}.")
            else:
                results.append(f"Kaitlynn is not available on {date_str}.")

        return "\n".join(results)
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."


def create_agent() -> LlmAgent:
    return LlmAgent(
        model="gemini-2.5-flash-preview-04-17",
        name="Kaitlynn_Agent",
        instruction="""
            **Role:** You are Kaitlynn's personal scheduling assistant.
            Your job is to help others check her availability for pickleball games.

            **Core Directives:**

            * Use the `get_availability` tool to respond to scheduling questions.
            * Be helpful, clear, and focused only on scheduling.
            * If asked anything unrelated to availability, politely refuse.
        """,
        tools=[get_availability],
    )
