# Golf Coach AI Agent

## Overview

This project implements an intelligent golf coaching agent that provides personalized golf coaching. The agent utilizes advanced AI techniques including context awareness, long-term memory, and self-improvement capabilities to deliver increasingly helpful golf advice over time.

## Features

- **Contextual Awareness**: Maintains conversation history to provide coherent responses
- **Long-term Memory**: Remembers important details about your golf game across sessions
- **Self-improvement**: Reflects on past interactions to improve coaching advice
- **Profile Building**: Automatically builds a profile of your golf game, including swing issues and goals
- **Interactive Web Interface**: Streamlit-based UI for easy interaction with the coach
- **Terminal Interface**: Simple command-line interface alternative

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/astevens246/AI-Frameworks_Final_Project.git
   cd Final-Project
   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**

   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   Create a `.env` file in the project root directory and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

### Running the Application

You can run the Golf Coach AI using either the web interface or the terminal interface:

#### Web Interface (Recommended)

```bash
streamlit run web_interface.py
```

This will start the Streamlit server and automatically open the application in your default web browser. If it doesn't open automatically, you can access it at http://localhost:8501.

The web interface provides:

- Chat with the golf coach
- View your golfer profile
- Explore the coach's memory and insights

#### Terminal Interface

```bash
python3 main.py
```

This launches the text-based interface in your terminal. Follow the prompts to interact with the golf coach.

### Usage Tips

1. **First-time Setup**: When you first use the application, you'll be asked to enter a golfer ID. This ID is used to keep track of your profile and conversation history.

2. **Asking Questions**: You can ask any golf-related questions, such as:

   - "How can I fix my slice?"
   - "What's the best way to practice putting?"
   - "I'm a beginner, what should I focus on first?"

3. **Building Your Profile**: The more you interact with the coach, the more it learns about your game. Mention your skill level, swing issues, and goals to get more personalized advice.

4. **Viewing Memory**: In the web interface, use the "Memory" tab to see what the coach remembers about your conversations.

## Project Structure

- `main.py`: Core Golf Coach AI implementation
- `web_interface.py`: Streamlit web interface
- `coach_data/`: Directory where user profiles and conversation data are stored
- `requirements.txt`: Python dependencies

## Advanced Configuration

You can modify the AI model and other parameters by editing the `GolfCoachAgent` class initialization in `main.py`. By default, the application uses the "gpt-3.5-turbo" model, but you can switch to other OpenAI models like "gpt-4o" for potentially better results (requires appropriate API access).

