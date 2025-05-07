from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

class GolfCoachAgent:
    """
    A Golf Coach Agent that provides golf coaching advice with conversation history.
    Now includes basic golfer profiles based on Memory-Enhanced Agent (#22).
    """
    
    def __init__(self, model_name="gpt-4o-mini", temperature=0.2):
        self.llm = ChatOpenAI(model=model_name, max_tokens=1000, temperature=temperature)
        self.session_store = {}  # Store for conversation histories
        self.golfer_profiles = {}  # Long-term memory for golfer profiles - from Memory-Enhanced Agent (#22)
        
        # Create a coaching prompt template with history and golfer profile
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are GolfPro AI, an expert golf coach with decades of experience.
            Provide actionable golf advice to help players improve their game.
            Be encouraging but honest, and give clear instructions.
            """),
            ("system", "Golfer Profile: {golfer_profile}"),  # Added from Memory-Enhanced Agent (#22)
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Create the chain with history
        self.chain = self.prompt | self.llm
        self.chain_with_history = RunnableWithMessageHistory(
            self.chain,
            self.get_chat_history,
            input_messages_key="input",
            history_messages_key="history"
        )
    
    def get_chat_history(self, session_id: str):
        """Retrieve or create a new chat history for the session"""
        if session_id not in self.session_store:
            self.session_store[session_id] = ChatMessageHistory()
        return self.session_store[session_id]
    
    def coach(self, input_text: str, golfer_id: str) -> str:
        """Method to interact with the golf coach agent with memory features"""
        # Get the golfer profile
        golfer_profile = self.get_golfer_profile_summary(golfer_id)
        
        # Generate a response
        response = self.chain_with_history.invoke(
            {"input": input_text, "golfer_profile": golfer_profile},
            config={"configurable": {"session_id": golfer_id}}
        )
        
        # Update the golfer profile with their input
        self.update_golfer_profile(golfer_id, input_text)
        
        return response.content
    
    def update_golfer_profile(self, golfer_id: str, new_information: str):
        """Update the golfer's long-term profile with new information"""
    if golfer_id not in self.golfer_profiles:
        self.golfer_profiles[golfer_id] = {
            "swing_issues": [],
            "equipment": {},
            "goals": [],
            "playing_history": ""
        }
    
    # For now, just store the raw information
    self.golfer_profiles[golfer_id]["last_message"] = new_information

def get_golfer_profile_summary(self, golfer_id: str) -> str:
    """Generate a summary of the golfer's profile for use in prompts"""
    if golfer_id not in self.golfer_profiles:
        return "No profile information available."
    
    return f"Last message: {self.golfer_profiles[golfer_id].get('last_message', 'No previous messages')}"

# Example usage
if __name__ == "__main__":
    coach = GolfCoachAgent()
    session_id = "player_123"
    
    # First interaction
    print("USER: I'm struggling with my slice off the tee. Any advice?")
    response = coach.coach("I'm struggling with my slice off the tee. Any advice?", session_id)
    print(f"GOLF COACH: {response}")
    
    # Second interaction - The agent should remember context
    print("\nUSER: Would changing my grip help with that issue?")
    response = coach.coach("Would changing my grip help with that issue?", session_id)
    print(f"GOLF COACH: {response}")