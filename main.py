from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv
import os
import json
import pathlib
import pickle
from datetime import datetime

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


class GolfCoachAgent:
    """A simplified Golf Coach Agent with memory and self-improvement capabilities"""

    def __init__(
        self, model_name="gpt-3.5-turbo", temperature=0.5, data_dir="coach_data"
    ):
        # Initialize core components
        self.llm = ChatOpenAI(
            model=model_name, max_tokens=1000, temperature=temperature
        )
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Initialize data stores
        self.session_store = {}
        self.golfer_profiles = {}
        self.last_interactions = {}
        self.long_term_memory = {}
        self.coaching_insights = {}
        self.coaching_knowledge = self._load_json("coaching_knowledge.json") or {
            "common_mistakes": [
                "Over-swinging",
                "Poor grip",
                "Improper alignment",
                "Lifting head",
            ],
            "effective_tips": [],
        }

        # Load all data
        for store_name in [
            "profiles",
            "last_interactions",
            "session_history",
            "long_term_memory",
            "coaching_insights",
        ]:
            getattr(self, f"_load_{store_name}")()

        # Set up the conversation prompt and chain
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful golf coach. Be supportive and offer practical advice. Use past insights when relevant: {coaching_insights}",
                ),
                ("system", "Golfer profile: {golfer_profile}"),
                ("system", "Long-term memory: {long_term_memory}"),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        self.chain = self.prompt | self.llm
        self.chain_with_history = RunnableWithMessageHistory(
            self.chain,
            self.get_chat_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def get_chat_history(self, session_id):
        """Get or create chat history for this session"""
        if session_id not in self.session_store:
            self.session_store[session_id] = ChatMessageHistory()
        return self.session_store[session_id]

    def coach(self, input_text, golfer_id):
        """Main method to interact with the golf coach"""
        # Initialize profile if needed
        if golfer_id not in self.golfer_profiles:
            self.golfer_profiles[golfer_id] = {
                "skill_level": "unknown",
                "interaction_count": 0,
            }

        # Update profile and counter
        self.golfer_profiles[golfer_id]["interaction_count"] = (
            self.golfer_profiles[golfer_id].get("interaction_count", 0) + 1
        )
        self._update_profile(golfer_id, input_text)

        # Get response with context
        response = self.chain_with_history.invoke(
            {
                "input": input_text,
                "golfer_profile": self._get_profile_summary(golfer_id),
                "long_term_memory": self._get_field_as_string(
                    self.long_term_memory, golfer_id
                ),
                "coaching_insights": self._get_field_as_string(
                    self.coaching_insights, golfer_id, "No insights yet"
                ),
            },
            config={"configurable": {"session_id": golfer_id}},
        )

        # Record the interaction
        self.last_interactions[golfer_id] = {
            "timestamp": datetime.now().isoformat(),
            "user_input": input_text,
            "coach_response": response.content,
        }

        # Learn from interaction
        self._update_long_term_memory(golfer_id, input_text, response.content)
        if self.golfer_profiles[golfer_id].get("interaction_count", 0) % 3 == 0:
            self._reflect_and_improve(golfer_id)

        # Save all data
        self.save_data()

        return response.content

    def get_last_interaction_summary(self, golfer_id):
        """Get a summary of the last interaction with this golfer"""
        if golfer_id not in self.last_interactions:
            return "No previous interactions found."
        last = self.last_interactions[golfer_id]
        return f"Time: {last['timestamp']}\nYOU: {last['user_input']}\nCOACH: {last['coach_response']}"

    def _update_profile(self, golfer_id, input_text):
        """Update profile based on input text"""
        # Create profile structure if needed
        if golfer_id not in self.golfer_profiles:
            self.golfer_profiles[golfer_id] = {
                "interaction_count": 0,
                "swing_issues": [],
                "goals": [],
            }
        profile = self.golfer_profiles[golfer_id]

        # Ensure required fields exist
        for field in ["swing_issues", "goals"]:
            if field not in profile or not isinstance(profile[field], list):
                profile[field] = []

        # Store last message
        profile["last_message"] = input_text

        # Detect skill level
        lower_input = input_text.lower()
        if any(
            term in lower_input for term in ["beginner", "new to golf", "just started"]
        ):
            profile["skill_level"] = "beginner"
        elif any(term in lower_input for term in ["intermediate", "few years"]):
            profile["skill_level"] = "intermediate"
        elif any(
            term in lower_input for term in ["advanced", "handicap", "competitive"]
        ):
            profile["skill_level"] = "advanced"

        # Detect swing issues
        issues_map = {
            "slice": ["slice"],
            "hook": ["hook"],
            "topped_shots": ["top", "topped"],
            "fat_shots": ["fat", "chunked"],
            "yips": ["yips"],
            "pulling": ["pull"],
            "pushing": ["push"],
        }

        for issue, keywords in issues_map.items():
            if (
                any(keyword in lower_input for keyword in keywords)
                and issue not in profile["swing_issues"]
            ):
                profile["swing_issues"].append(issue)

        # Detect goals
        goals_map = {
            "increase_distance": ["distance"],
            "improve_accuracy": ["accuracy"],
            "consistency": ["consistent", "consistency"],
            "lower_scores": ["score"],
            "improve_short_game": ["short game"],
            "improve_putting": ["putt"],
        }

        for goal, keywords in goals_map.items():
            if (
                any(keyword in lower_input for keyword in keywords)
                and goal not in profile["goals"]
            ):
                profile["goals"].append(goal)

    def _update_long_term_memory(self, golfer_id, input_text, response):
        """Update long-term memory with important information"""
        if golfer_id not in self.long_term_memory:
            self.long_term_memory[golfer_id] = []

        # Store longer inputs
        if len(input_text) > 20:
            self.long_term_memory[golfer_id].append(f"Golfer asked: {input_text}")

        # Store important coaching advice
        if any(
            keyword in response.lower()
            for keyword in [
                "practice",
                "technique",
                "drill",
                "problem",
                "improve",
                "struggle",
            ]
        ):
            self.long_term_memory[golfer_id].append(
                f"Coach advised: {response[:100]}..."
            )

        # Limit memory size
        if len(self.long_term_memory[golfer_id]) > 10:
            self.long_term_memory[golfer_id] = self.long_term_memory[golfer_id][-10:]

    def _reflect_and_improve(self, golfer_id):
        """Analyze past interactions and generate insights for improvement"""
        history = self.get_chat_history(golfer_id)
        if len(history.messages) < 4:  # Need at least 2 exchanges
            return

        # Generate insights
        reflection_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a golf coach analyzing your past interactions with a golfer to improve your coaching.",
                ),
                (
                    "human",
                    "Analyze these interactions and provide insights on how to improve future coaching advice: {history}",
                ),
            ]
        )

        reflection_chain = reflection_prompt | self.llm
        insights = reflection_chain.invoke({"history": history.messages[-10:]}).content

        # Store insights
        if golfer_id not in self.coaching_insights:
            self.coaching_insights[golfer_id] = []
        self.coaching_insights[golfer_id].append(insights)

        # Limit insights
        if len(self.coaching_insights[golfer_id]) > 3:
            self.coaching_insights[golfer_id] = self.coaching_insights[golfer_id][-3:]

    # Helper methods
    def _get_profile_summary(self, golfer_id):
        """Get a simple text summary of golfer profile"""
        profile = self.golfer_profiles.get(golfer_id, {})
        return f"Skill level: {profile.get('skill_level', 'unknown')}, Interactions: {profile.get('interaction_count', 0)}"

    def _get_field_as_string(self, data_store, key, default=""):
        """Convert a list from a data store to a string representation"""
        items = data_store.get(key, [])
        return ". ".join(items) if items else default

    def _load_json(self, filename):
        """Load JSON data from a file"""
        file_path = self.data_dir / filename
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_json(self, data, filename):
        """Save data to a JSON file"""
        file_path = self.data_dir / filename
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    # Data loading methods
    def _load_profiles(self):
        self.golfer_profiles = self._load_json("golfer_profiles.json")

    def _load_last_interactions(self):
        self.last_interactions = self._load_json("last_interactions.json")

    def _load_long_term_memory(self):
        self.long_term_memory = self._load_json("long_term_memory.json")

    def _load_coaching_insights(self):
        self.coaching_insights = self._load_json("coaching_insights.json")

    def _load_session_history(self):
        """Load session history from disk"""
        history_path = self.data_dir / "session_history.pkl"
        if history_path.exists():
            try:
                with open(history_path, "rb") as f:
                    self.session_store = pickle.load(f)
            except (pickle.PickleError, EOFError):
                self.session_store = {}

    # Save all data
    def save_data(self):
        """Save all data to disk"""
        self._save_json(self.golfer_profiles, "golfer_profiles.json")
        self._save_json(self.last_interactions, "last_interactions.json")
        self._save_json(self.long_term_memory, "long_term_memory.json")
        self._save_json(self.coaching_insights, "coaching_insights.json")
        self._save_json(self.coaching_knowledge, "coaching_knowledge.json")

        # Save session history separately (pickle)
        history_path = self.data_dir / "session_history.pkl"
        with open(history_path, "wb") as f:
            pickle.dump(self.session_store, f)


# Example usage
if __name__ == "__main__":
    # Get golfer ID with validation to prevent command names from being used as IDs
    reserved_commands = [
        "profile",
        "knowledge",
        "summary",
        "last",
        "quit",
        "exit",
        "bye",
    ]

    while True:
        golfer_id = (
            input(
                "Enter your golfer ID (or press Enter for default 'player_123'): "
            ).strip()
            or "player_123"
        )
        if golfer_id.lower() in reserved_commands:
            print(
                f"'{golfer_id}' is a reserved command name. Please choose a different ID."
            )
        else:
            break

    coach = GolfCoachAgent()

    print("\n=== Golf Coach AI ===")
    print("Welcome to your personalized golf coaching session!")
    print("Ask me any questions about your golf game or type 'quit' to exit.")
    print(
        "Type 'profile' to see your current profile or 'knowledge' to see coaching insights."
    )
    print("Type 'summary' or 'last' to see a summary of your last interaction.")
    print("=" * 21)

    try:
        while True:
            # Get user input
            user_input = input("\nYOU: ").strip()

            # Check for exit command
            if user_input.lower() in ["quit", "exit", "bye"]:
                print(
                    "\nGOLF COACH: Thanks for the session! Keep practicing and see you on the course!"
                )
                break
            elif user_input.lower() == "profile":
                print("\n--- Your Golfer Profile ---")
                if golfer_id in coach.golfer_profiles:
                    print(json.dumps(coach.golfer_profiles[golfer_id], indent=2))
                else:
                    print("No profile built yet. Start asking golf questions!")
            elif user_input.lower() == "knowledge":
                print("\n--- Coaching Knowledge Base ---")
                print(json.dumps(coach.coaching_knowledge, indent=2))
            elif user_input.lower() in ["summary", "last"]:
                print("\n--- Last Interaction Summary ---")
                print(coach.get_last_interaction_summary(golfer_id))
            elif not user_input:
                print("Please ask a question about your golf game.")
            else:
                # Normal coaching interaction
                print("\nGOLF COACH:", end=" ")
                response = coach.coach(user_input, golfer_id)
                print(response)

    except KeyboardInterrupt:
        print("\n\nSession ended. Thanks for using Golf Coach AI!")
    finally:
        # Show a summary at the end
        if (
            golfer_id in coach.golfer_profiles
            and coach.golfer_profiles[golfer_id].get("interaction_count", 0) > 0
        ):
            profile = coach.golfer_profiles[golfer_id]
            print("\n--- Session Summary ---")
            print(f"Total interactions: {profile.get('interaction_count', 0)}")
            print(f"Identified skill level: {profile.get('skill_level', 'beginner')}")

            if profile.get("swing_issues"):
                print(f"Swing issues discussed: {', '.join(profile['swing_issues'])}")
            if profile.get("goals"):
                print(f"Goals identified: {', '.join(profile['goals'])}")

        # Save data for persistence between sessions
        coach.save_data()
