from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv
import os
import json
import time
import datetime
import pickle
import pathlib

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


class GolfCoachAgent:
    """
    A Golf Coach Agent that combines elements from multiple agent patterns:
    #20 Simple Conversational, #22 Memory-Enhanced, #23 Self-Improving, #24 Multi-Persona
    """

    def __init__(
        self, model_name="gpt-4o-mini", temperature=0.2, data_dir="coach_data"
    ):
        self.llm = ChatOpenAI(
            model=model_name, max_tokens=1000, temperature=temperature
        )

        # Set up data directory for persistence
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Memory stores
        self.session_store = {}  # Conversation histories
        self.golfer_profiles = {}  # Long-term memory profiles
        self.last_interactions = {}  # Store last interactions for each golfer

        # Knowledge and personas
        self.coaching_personas = {
            "beginner": "You are a patient golf coach for beginners. Use simple terms and focus on fundamentals.",
            "intermediate": "You are a technical golf coach. Use proper terminology and focus on refining skills.",
            "advanced": "You are an elite golf coach. Use advanced concepts and focus on optimization.",
        }

        self.coaching_knowledge = {
            "common_mistakes": [
                "Over-swinging",
                "Poor grip",
                "Improper alignment",
                "Lifting head",
            ],
            "effective_tips": [],  # Will be populated through reflection
        }

        # Load persisted data if it exists
        self._load_data()

        # Create the prompt and chain
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{coaching_persona}"),
                ("system", "Coaching insights: {coaching_knowledge}"),
                ("system", "Golfer profile: {golfer_profile}"),
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

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5

    def get_chat_history(self, session_id):
        """Get or create chat history for this session"""
        if session_id not in self.session_store:
            self.session_store[session_id] = ChatMessageHistory()
        return self.session_store[session_id]

    def coach(self, input_text, golfer_id):
        """Main method to interact with the golf coach"""
        # Rate limiting
        self._apply_rate_limiting()

        # Get context for this interaction
        golfer_profile = self._get_profile_summary(golfer_id)
        coaching_persona = self._select_persona(golfer_id)
        relevant_knowledge = self._get_relevant_knowledge(input_text)

        # Generate response
        response = self.chain_with_history.invoke(
            {
                "input": input_text,
                "golfer_profile": golfer_profile,
                "coaching_persona": coaching_persona,
                "coaching_knowledge": relevant_knowledge,
            },
            config={"configurable": {"session_id": golfer_id}},
        )

        # Update knowledge
        self._update_profile(golfer_id, input_text)
        self._reflect_on_interaction(input_text, response.content, golfer_id)

        # Store this interaction for summary feature
        self.last_interactions[golfer_id] = {
            "user_input": input_text,
            "coach_response": response.content,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        return response.content

    def _apply_rate_limiting(self):
        """Apply simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _get_profile_summary(self, golfer_id):
        """Get a summary of the golfer's profile"""
        if golfer_id not in self.golfer_profiles:
            return "No profile information available."

        profile = self.golfer_profiles[golfer_id]
        parts = []

        # Add relevant profile sections if they exist
        if profile.get("swing_issues"):
            parts.append(f"Swing issues: {', '.join(profile['swing_issues'])}")
        if (
            profile.get("equipment")
            and isinstance(profile["equipment"], dict)
            and profile["equipment"]
        ):
            equip_str = ", ".join(
                [f"{k}: {v}" for k, v in profile["equipment"].items()]
            )
            parts.append(f"Equipment: {equip_str}")
        if profile.get("goals"):
            parts.append(f"Goals: {', '.join(profile['goals'])}")
        if profile.get("playing_history"):
            if isinstance(profile["playing_history"], str):
                parts.append(f"Playing history: {profile['playing_history']}")
            elif isinstance(profile["playing_history"], dict):
                history_str = ", ".join(
                    [f"{k}: {v}" for k, v in profile["playing_history"].items()]
                )
                parts.append(f"Playing history: {history_str}")
        if profile.get("skill_level"):
            parts.append(f"Skill level: {profile['skill_level']}")

        return " | ".join(parts) if parts else "Limited profile information available."

    def _select_persona(self, golfer_id):
        """Select appropriate coaching persona"""
        if golfer_id not in self.golfer_profiles:
            return self.coaching_personas["beginner"]

        skill_level = self.golfer_profiles[golfer_id].get("skill_level", "beginner")
        return self.coaching_personas.get(
            skill_level, self.coaching_personas["beginner"]
        )

    def _get_relevant_knowledge(self, query):
        """Find relevant coaching knowledge"""
        # Find tips with matching keywords
        matching_tips = []
        for tip in self.coaching_knowledge["effective_tips"]:
            if any(kw.lower() in query.lower() for kw in tip.get("keywords", [])):
                matching_tips.append(tip["tip"])

        if matching_tips:
            return f"Relevant tips: {'; '.join(matching_tips)}"
        else:
            return f"Common mistakes: {', '.join(self.coaching_knowledge['common_mistakes'])}"

    def _update_profile(self, golfer_id, new_information):
        """Update golfer profile with new information"""
        # Initialize profile if it doesn't exist
        if golfer_id not in self.golfer_profiles:
            self.golfer_profiles[golfer_id] = {
                "swing_issues": [],
                "equipment": {},
                "goals": [],
                "playing_history": "",
                "skill_level": "beginner",
                "last_message": "",
                "interaction_count": 0,
            }

        # Update interaction count
        self.golfer_profiles[golfer_id]["interaction_count"] = (
            self.golfer_profiles[golfer_id].get("interaction_count", 0) + 1
        )
        self.golfer_profiles[golfer_id]["last_message"] = new_information

        # Extract structured information using LLM
        extraction_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Extract golf information into these categories:
            - swing_issues: Any technique problems (slice, hook, etc.)
            - equipment: Details about the golfer's clubs, etc.
            - goals: What the golfer wants to achieve
            - playing_history: Experience level, handicap, etc.
            - skill_level: If "beginner", "intermediate", or "advanced"
            
            Return ONLY a valid JSON object with these categories.
            """,
                ),
                ("human", new_information),
            ]
        )

        try:
            # Get and parse the structured information
            extraction_chain = extraction_prompt | self.llm
            result = extraction_chain.invoke({})

            # Extract JSON from response
            self._extract_and_update_profile(result.content, golfer_id)
        except Exception as e:
            print(f"Error updating profile: {e}")

    def _extract_and_update_profile(self, response_text, golfer_id):
        """Helper to extract JSON and update profile"""
        start = response_text.find("{")
        end = response_text.rfind("}") + 1

        if start >= 0 and end > start:
            try:
                json_str = response_text[start:end]
                extracted_info = json.loads(json_str)

                # Update each category
                for category, value in extracted_info.items():
                    if category not in self.golfer_profiles[golfer_id]:
                        continue

                    if isinstance(value, list) and isinstance(
                        self.golfer_profiles[golfer_id][category], list
                    ):
                        # For lists, add new items without duplicates
                        if all(isinstance(item, str) for item in value):
                            self.golfer_profiles[golfer_id][category] = list(
                                set(self.golfer_profiles[golfer_id][category] + value)
                            )
                    elif isinstance(value, dict) and isinstance(
                        self.golfer_profiles[golfer_id][category], dict
                    ):
                        # For dictionaries, update with new key-values
                        self.golfer_profiles[golfer_id][category].update(value)
                    elif value:  # For strings/other types, replace if not empty
                        if category in ["swing_issues", "goals"] and isinstance(
                            value, str
                        ):
                            # Convert string to list item instead of individual characters
                            self.golfer_profiles[golfer_id][category] = [value]
                        else:
                            self.golfer_profiles[golfer_id][category] = value
            except json.JSONDecodeError:
                print(f"Failed to parse JSON: {json_str}")

    def _reflect_on_interaction(self, user_input, response, golfer_id):
        """Reflect on and learn from interactions"""
        # Only reflect occasionally (every 5 interactions)
        if self.golfer_profiles.get(golfer_id, {}).get("interaction_count", 0) % 5 != 0:
            return

        try:
            reflection_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """Reflect on this golf coaching interaction.
                Return ONLY a JSON object with:
                - "insights": Brief reflection on what was learned
                - "effective_tip": Most actionable advice given
                - "keywords": 2-3 relevant golf terms
                """,
                    ),
                    ("human", f"USER: {user_input}\n\nCOACH: {response}"),
                ]
            )

            result = reflection_prompt | self.llm
            response_text = result.invoke({})

            # Extract JSON and update knowledge base
            start = response_text.content.find("{")
            end = response_text.content.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response_text.content[start:end]
                reflection = json.loads(json_str)

                if "effective_tip" in reflection and "keywords" in reflection:
                    # Add to knowledge base
                    new_tip = {
                        "tip": reflection["effective_tip"],
                        "keywords": reflection["keywords"],
                        "date_added": datetime.datetime.now().isoformat(),
                    }
                    self.coaching_knowledge["effective_tips"].append(new_tip)

                    # Limit size of knowledge base
                    if len(self.coaching_knowledge["effective_tips"]) > 20:
                        self.coaching_knowledge["effective_tips"] = (
                            self.coaching_knowledge["effective_tips"][-20:]
                        )
        except Exception as e:
            print(f"Error during reflection: {e}")

    def get_last_interaction_summary(self, golfer_id):
        """Generate a summary of the last interaction"""
        if golfer_id not in self.last_interactions:
            return "No previous interactions found."

        try:
            last = self.last_interactions[golfer_id]

            # Generate a summary using the LLM
            summary_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """Create a concise summary of this golf coaching interaction.
                Highlight:
                1. The main question or issue raised
                2. Key advice or tips provided
                3. Any specific techniques or drills suggested
                4. Next steps if any were mentioned
                
                Keep it brief but actionable.
                """,
                    ),
                    (
                        "human",
                        f"USER: {last['user_input']}\n\nCOACH: {last['coach_response']}",
                    ),
                ]
            )

            summary_chain = summary_prompt | self.llm
            result = summary_chain.invoke({})

            return result.content
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Unable to generate summary of last interaction."

    def _load_data(self):
        """Load persisted data from disk"""
        try:
            # Load golfer profiles
            profiles_path = self.data_dir / "golfer_profiles.json"
            if profiles_path.exists():
                with open(profiles_path, "r") as f:
                    self.golfer_profiles = json.load(f)

            # Load coaching knowledge
            knowledge_path = self.data_dir / "coaching_knowledge.json"
            if knowledge_path.exists():
                with open(knowledge_path, "r") as f:
                    self.coaching_knowledge = json.load(f)

            # Load last interactions
            interactions_path = self.data_dir / "last_interactions.json"
            if interactions_path.exists():
                with open(interactions_path, "r") as f:
                    self.last_interactions = json.load(f)
                    
            # Load session history if it exists
            history_path = self.data_dir / "session_history.pkl"
            if history_path.exists():
                with open(history_path, "rb") as f:
                    try:
                        self.session_store = pickle.load(f)
                    except Exception as e:
                        print(f"Error loading session history: {e}")

            print(f"Loaded data from {self.data_dir}")
        except Exception as e:
            print(f"Warning: Failed to load persisted data: {e}")

    def save_data(self):
        """Save data to disk for persistence across sessions"""
        try:
            # Save golfer profiles
            profiles_path = self.data_dir / "golfer_profiles.json"
            with open(profiles_path, "w") as f:
                json.dump(self.golfer_profiles, f, indent=2)

            # Save coaching knowledge
            knowledge_path = self.data_dir / "coaching_knowledge.json"
            with open(knowledge_path, "w") as f:
                json.dump(self.coaching_knowledge, f, indent=2)

            # Save last interactions
            interactions_path = self.data_dir / "last_interactions.json"
            with open(interactions_path, "w") as f:
                json.dump(self.last_interactions, f, indent=2)
                
            # Save session history
            history_path = self.data_dir / "session_history.pkl"
            with open(history_path, "wb") as f:
                pickle.dump(self.session_store, f)

            print(f"Data saved to {self.data_dir}")
        except Exception as e:
            print(f"Warning: Failed to save data: {e}")


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

            # Check for profile command
            elif user_input.lower() == "profile":
                print("\n--- Your Golfer Profile ---")
                if golfer_id in coach.golfer_profiles:
                    print(json.dumps(coach.golfer_profiles[golfer_id], indent=2))
                else:
                    print("No profile built yet. Start asking golf questions!")
                continue

            # Check for knowledge command
            elif user_input.lower() == "knowledge":
                print("\n--- Coaching Knowledge Base ---")
                print(json.dumps(coach.coaching_knowledge, indent=2))
                continue

            # Check for summary command
            elif user_input.lower() in ["summary", "last"]:
                print("\n--- Last Interaction Summary ---")
                print(coach.get_last_interaction_summary(golfer_id))
                continue

            # Normal coaching interaction
            if not user_input:
                print("Please ask a question about your golf game.")
                continue

            # Get and display response
            print("\nGOLF COACH:", end=" ")

            # For a smoother experience, print a thinking message
            # while the model generates a response
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
            print("\n--- Session Summary ---")
            print(
                f"Total interactions: {coach.golfer_profiles[golfer_id].get('interaction_count', 0)}"
            )
            print(
                f"Identified skill level: {coach.golfer_profiles[golfer_id].get('skill_level', 'beginner')}"
            )
            if coach.golfer_profiles[golfer_id].get("swing_issues"):
                print(
                    f"Swing issues discussed: {', '.join(coach.golfer_profiles[golfer_id]['swing_issues'])}"
                )
            if coach.golfer_profiles[golfer_id].get("goals"):
                print(
                    f"Goals identified: {', '.join(coach.golfer_profiles[golfer_id]['goals'])}"
                )

        # Save data for persistence between sessions
        coach.save_data()
