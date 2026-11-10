from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Maintains the conversational history and agent message traces. 
    # 'add_messages' ensures new messages are appended rather than overwritten.
    messages: Annotated[list, add_messages]
    
    # Tracks the active intent or routing branch ("ingest", "update", "search", "engage")
    current_action: str          
    
    # Stores raw incoming payloads (e.g., family search filters or unstructured facility PDFs)
    query_payload: Dict[str, Any] 
    
    # Step-by-step audit log of agent operations for debugging and traceability
    agent_logs: List[str]        
    
    # The final structured data or narrative response to return to the FastAPI backend
    output_result: Dict[str, Any]