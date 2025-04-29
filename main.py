from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

class GolfCoachAgent:
    """
    A simple Golf Coach Agent that provides golf coaching advice.
    This is the initial version with basic functionality.
    """
    
    def __init__(self, model_name="gpt-4o-mini", temperature=0.2):
        self.llm = ChatOpenAI(model=model_name, max_tokens=1000, temperature=temperature)
        
        # Create a basic coaching prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are GolfPro AI, an expert golf coach with decades of experience.
            Provide actionable golf advice to help players improve their game.
            Be encouraging but honest, and give clear instructions.
            """),
            ("human", "{input}")
        ])
        
        # Create the chain
        self.chain = self.prompt | self.llm
    
    def coach(self, input_text: str) -> str:
        """Simple method to interact with the golf coach agent"""
        # Generate a response
        response = self.chain.invoke({"input": input_text})
        return response.content

# Example usage
if __name__ == "__main__":
    coach = GolfCoachAgent()
    
    # Simple test
    print("USER: I'm struggling with my slice off the tee. Any advice?")
    response = coach.coach("I'm struggling with my slice off the tee. Any advice?")
    print(f"GOLF COACH: {response}")