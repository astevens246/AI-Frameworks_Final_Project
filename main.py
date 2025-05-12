from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv
import os
import json
import time
import datetime

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


class GolfCoachAgent:
    """
    A Golf Coach Agent that combines elements from multiple agent patterns:
    #20 Simple Conversational, #22 Memory-Enhanced, #23 Self-Improving, #24 Multi-Persona
    """

    def __init__(self, model_name="gpt-4o-mini", temperature=0.2):
        self.llm = ChatOpenAI(
            model=model_name, max_tokens=1000, temperature=temperature
        )

        # Memory stores
        self.session_store = {}  # Conversation histories
        self.golfer_profiles = {}  # Long-term memory profiles

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
                        self.golfer_profiles[golfer_id][category] = list(
                            set(self.golfer_profiles[golfer_id][category] + value)
                        )
                    elif isinstance(value, dict) and isinstance(
                        self.golfer_profiles[golfer_id][category], dict
                    ):
                        # For dictionaries, update with new key-values
                        self.golfer_profiles[golfer_id][category].update(value)
                    elif value:  # For strings/other types, replace if not empty
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


# Example usage
if __name__ == "__main__":
    coach = GolfCoachAgent()
    golfer_id = "player_123"

    # First interaction
    print(
        "USER: I'm a beginner with a 20 handicap and I'm struggling with my slice off the tee. Any advice?"
    )
    response = coach.coach(
        "I'm a beginner with a 20 handicap and I'm struggling with my slice off the tee. Any advice?",
        golfer_id,
    )
    print(f"GOLF COACH: {response}")

    # Second interaction
    print("\nUSER: Would changing my grip help with that issue?")
    response = coach.coach("Would changing my grip help with that issue?", golfer_id)
    print(f"GOLF COACH: {response}")

    # Third interaction
    print(
        "\nUSER: I've been playing for 3 months and I want to break 90 within a year."
    )
    response = coach.coach(
        "I've been playing for 3 months and I want to break 90 within a year.",
        golfer_id,
    )
    print(f"GOLF COACH: {response}")

    # Show results
    print("\n--- Golfer Profile Built So Far ---")
    print(json.dumps(coach.golfer_profiles[golfer_id], indent=2))

    print("\n--- Coaching Knowledge Built So Far ---")
    print(json.dumps(coach.coaching_knowledge, indent=2))
