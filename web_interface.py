import streamlit as st
import json
import time
from main import GolfCoachAgent

# Page configuration
st.set_page_config(page_title="Golf Coach AI", page_icon="🏌️", layout="centered")

# Simple styling
st.markdown(
    """
<style>
    .main-header { font-size: 2.5rem; text-align: center; font-weight: bold; margin-bottom: 0.5rem; color: white; }
    .subheader { font-size: 1.2rem; text-align: center; margin-bottom: 1.5rem; color: white; }
    .coach-message { background-color: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #4a6572; }
    .user-message { background-color: #34495e; color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; text-align: right; border: 1px solid #4a6572; }
    .memory-box { background-color: #1a2634; padding: 10px 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #3a516e; font-size: 0.9rem; }
    .memory-title { color: #5dade2; font-weight: bold; margin-bottom: 5px; }
    .stTextInput > div > div > input { color: white; background-color: #1e2a38; }
    p, li, div { color: #ffffff !important; }
    .stButton > button { background-color: #3498db; color: white; border: none; }
    .tab-content { padding: 20px 0; }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
for key, default in [
    ("messages", []),
    ("coach", GolfCoachAgent()),
    ("golfer_id", "default_user"),
    ("active_tab", "Chat"),
    ("show_memory", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# App header
st.markdown("<div class='main-header'>Golf Coach AI</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subheader'>Your personal AI golf instructor</div>",
    unsafe_allow_html=True,
)

# Main tabs
tabs = st.tabs(["Chat", "Profile", "Memory"])
tab_names = ["Chat", "Profile", "Memory"]
active_tab_index = tab_names.index(st.session_state.active_tab)

# Sidebar for user info
with st.sidebar:
    st.header("Golfer Information")
    new_golfer_id = st.text_input("Golfer ID:", value=st.session_state.golfer_id)

    if new_golfer_id != st.session_state.golfer_id:
        st.session_state.golfer_id = new_golfer_id
        st.session_state.messages = []
        st.rerun()

    # Show profile info summary
    if st.session_state.golfer_id in st.session_state.coach.golfer_profiles:
        profile = st.session_state.coach.golfer_profiles[st.session_state.golfer_id]
        st.subheader("Your Profile")
        st.write(f"Skill Level: {profile.get('skill_level', 'Unknown')}")
        st.write(f"Interactions: {profile.get('interaction_count', 0)}")

        if profile.get("swing_issues") and len(profile.get("swing_issues", [])) > 0:
            st.write("Swing Issues:")
            for issue in profile.get("swing_issues", []):
                st.write(f"- {issue}")

    # Memory toggle
    st.divider()
    memory_toggle = st.checkbox(
        "Show Coach's Memory",
        value=st.session_state.show_memory,
        help="Show what the coach remembers about your conversations",
    )
    if memory_toggle != st.session_state.show_memory:
        st.session_state.show_memory = memory_toggle
        st.rerun()

    # Useful information section
    st.divider()
    st.subheader("Common Golf Questions")
    st.markdown(
        """
        - How can I improve my swing?
        - What's the best way to practice putting?
        - How do I reduce my slice?
        - What clubs should I use for different distances?
        - Tips for course management?
    """
    )


# Helper functions
def display_memory_items(memory_items, title="What I Remember:"):
    st.markdown(f"<div class='memory-title'>{title}</div>", unsafe_allow_html=True)
    for item in memory_items:
        st.markdown(f"<div class='memory-box'>{item}</div>", unsafe_allow_html=True)


def display_messages():
    for message in st.session_state.messages:
        role, content = message["role"], message["content"]
        st.markdown(
            f"<div class='{role}-message'>{content}</div>",
            unsafe_allow_html=True,
        )


# CHAT TAB
with tabs[0]:
    st.session_state.active_tab = "Chat"

    # Show memory if enabled
    if (
        st.session_state.show_memory
        and st.session_state.golfer_id in st.session_state.coach.long_term_memory
    ):
        memory_items = st.session_state.coach.long_term_memory.get(
            st.session_state.golfer_id, []
        )
        if memory_items:
            with st.expander("Coach's Memory", expanded=True):
                display_memory_items(memory_items)

    # Display chat messages
    display_messages()

    # Input area for new messages
    user_input = st.chat_input("Ask your golf coach...")

    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Show thinking message
        with st.status("⛳ Analyzing your golf question...", expanded=True) as status:
            time.sleep(0.5)  # Small delay for UI effect
            status.update(label="🏌️‍♂️ Your golf coach is thinking...", state="running")

            # Get AI response
            response = st.session_state.coach.coach(
                user_input, st.session_state.golfer_id
            )

            status.update(label="✅ Response ready!", state="complete")

        # Add coach response to chat
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Force refresh
        st.rerun()

# PROFILE TAB
with tabs[1]:
    st.session_state.active_tab = "Profile"

    if st.session_state.golfer_id in st.session_state.coach.golfer_profiles:
        profile = st.session_state.coach.golfer_profiles[st.session_state.golfer_id]

        st.subheader("Your Golf Profile")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Skill Level", profile.get("skill_level", "Unknown").capitalize())
        with col2:
            st.metric("Total Interactions", profile.get("interaction_count", 0))

        # Display profile sections with consistent formatting
        sections = [
            (
                "Swing Issues",
                "swing_issues",
                "No specific swing issues identified yet.",
            ),
            ("Golf Goals", "goals", "No specific goals identified yet."),
        ]

        for title, field, empty_msg in sections:
            st.markdown(f"### {title}")
            items = profile.get(field, [])
            if items and isinstance(items, list) and len(items) > 0:
                for item in items:
                    formatted_item = item.replace("_", " ").capitalize()
                    st.markdown(f"- **{formatted_item}**")
            else:
                st.info(empty_msg)

        if profile.get("last_message"):
            st.markdown("### Recent Activity")
            st.write("Last question you asked:")
            st.markdown(f"*\"{profile.get('last_message')}\"*")
    else:
        st.info(
            "No profile built yet. Start asking golf questions to build your profile!"
        )

# MEMORY TAB
with tabs[2]:
    st.session_state.active_tab = "Memory"

    st.subheader("Coach's Memory & Learning")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Long-term Memory")
        memory_items = st.session_state.coach.long_term_memory.get(
            st.session_state.golfer_id, []
        )
        if memory_items:
            for i, item in enumerate(memory_items, 1):
                st.markdown(f"**{i}.** {item}")
        else:
            st.info("No long-term memories stored yet.")

    with col2:
        st.markdown("### Coaching Insights")
        insights = st.session_state.coach.coaching_insights.get(
            st.session_state.golfer_id, []
        )
        if insights:
            for i, insight in enumerate(insights, 1):
                with st.expander(f"Insight #{i}"):
                    st.write(insight)
        else:
            st.info("No coaching insights generated yet.")

    st.markdown("### Last Interaction")
    if st.session_state.golfer_id in st.session_state.coach.last_interactions:
        last = st.session_state.coach.last_interactions[st.session_state.golfer_id]
        st.markdown(f"**Time:** {last['timestamp']}")
        st.markdown(f"**You asked:** {last['user_input']}")
        with st.expander("Coach's response"):
            st.write(last["coach_response"])
    else:
        st.info("No previous interactions found.")
