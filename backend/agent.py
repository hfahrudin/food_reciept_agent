from langgraph.graph import StateGraph, END
from langchain.prompts import ChatPromptTemplate
from typing import TypedDict
from langchain_openai import ChatOpenAI
from datetime import date
from prompt_schema import *
from tools import ReceiptDB
import json
class AgentState(TypedDict):
    chat_history: list
    state: str
    retrieval : list
    response :str

class AgentPawcha():
    def __init__(self, reciept_db: ReceiptDB):
        self.reciept_db = reciept_db 
        self.llm = ChatOpenAI(model_name="gpt-4o-mini",   temperature=0.7, max_completion_tokens=1200)
        self.workflow = self.builder()

    def invoke(self, messages):
        initial_state = AgentState(
            chat_history=messages,
            state="",
            retrieval=[],
            response=""
        )
        state_result = self.workflow.invoke(initial_state)
        print(state_result)
        return {"content" : state_result.get("response", "Agent Error")}
    
    def query_node(self, state: AgentState) -> AgentState:
        """
        Entry node: determines whether the LLM wants to call a tool (retrieve receipts)
        and executes it if applicable.
        """
        chat_history = state.get("chat_history", []).copy()  # avoid modifying original

        # Append today's date to the last user message
        for i in reversed(range(len(chat_history))):
            if chat_history[i].get("role") == "user":
                chat_history[i]["content"] += f". Today is {date.today()}"
                break  # 

        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools([retrieve_by_date_range])

        # Invoke LLM with chat history
        msg = llm_with_tools.invoke(chat_history)

        # Get any tool calls
        tool_calls = msg.tool_calls

        if tool_calls:
            # Take the first tool call
            first_call = tool_calls[0]
            tool_name = first_call.get("name")
            tool_args = first_call.get("args", {})

            if tool_name == "retrieve_by_date_range":
                # Safely extract start and end dates
                start = tool_args.get("start_date")
                end = tool_args.get("end_date")

                if start and end:
                    try:
                        # Call your database method
                        retrieved_receipts = self.reciept_db.retrieve_by_date_range(start, end)
                        state["retrieval"] =  retrieved_receipts
                        state["state"] = "RETRIEVED"
                    except Exception as e:
                        # Log exception if desired
                        print(f"Error retrieving receipts: {e}")
                        state["state"] = "NOT_RETRIEVED"
                else:
                    # Missing start or end date
                    state["state"] = "NOT_RETRIEVED"
            else:
                # Unknown tool
                state["state"] = "NOT_RETRIEVED"
        else:
            # No tool calls, respond directly
            state["state"] = "NOT_RETRIEVED"

        return state
    
    def respond_node(self, state: AgentState):
        chat_history = state.get("chat_history", [])
        retrieved = state.get("retrieval", None)
        current_state = state.get("state", "NOT_RETRIEVED")

        # Determine which prompt to use
        if current_state == "NOT_RETRIEVED":
            prompt = not_retrieved_prompt
            llm_input = {"chat_history": "; ".join([m["content"] for m in chat_history])}
        elif current_state == "RETRIEVED" and (not retrieved or len(retrieved) == 0):
            prompt = retrieved_empty_prompt
            llm_input = {"chat_history": "; ".join([m["content"] for m in chat_history])}
        elif current_state == "RETRIEVED" and len(retrieved) > 0:
            prompt = retrieved_with_items_prompt
            llm_input = {
                "chat_history": "; ".join([m["content"] for m in chat_history]),
                "retrieved_receipts": json.dumps(retrieved, indent=2)
            }
        else:
            # fallback to generic not_retrieved
            prompt = not_retrieved_prompt
            llm_input = {"chat_history": "; ".join([m["content"] for m in chat_history])}

        # Call LLM with selected prompt
        msg = self.llm.invoke(prompt.format(**llm_input))
        response_content = msg.content  # get only the text
        state["response"] = response_content

        return state
    
    def builder(self):
        graph = StateGraph(AgentState)
        graph.add_node("query", self.query_node)
        graph.add_node("respond", self.respond_node)

        graph.set_entry_point("query")
        graph.add_edge("query", "respond")
        graph.add_edge("respond", END)

        return graph.compile()

        
