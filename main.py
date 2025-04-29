from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

class GolfCoachAgent:
    """
    A Golf Coach Agent that provides golf coaching advice with conversation history.
    """
    
    def __init__(self, model_name="gpt-4o-mini", temperature=0.2):
        self.llm = ChatOpenAI(model=model_name, max_tokens=1000, temperature=temperature)
        self.session_store = {}  # Store for conversation histories
        
        # Create a coaching prompt template with history
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are GolfPro AI, an expert golf coach with decades of experience.
            Provide actionable golf advice to help players improve their game.
            Be encouraging but honest, and give clear instructions.
            """),
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
    
    def coach(self, input_text: str, session_id: str) -> str:
        """Method to interact with the golf coach agent with conversation history"""
        # Generate a response with history
        response = self.chain_with_history.invoke(
            {"input": input_text},
            config={"configurable": {"session_id": session_id}}
        )
        return response.content

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