# Golf Coach AI Agent

## Overview

This project implements an intelligent golf coaching agent that provides personalized golf coaching through natural language interaction. The agent maintains conversation context and offers actionable advice to help golfers improve their game.

## Features

- **Contextual Awareness**: Maintains conversation history to provide coherent responses
- **Golf Expertise**: Provides professional-level coaching advice for various aspects of golf
- **User-Friendly Interaction**: Simple text-based interface for asking golf-related questions

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
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

```bash
python3 main.py
```
