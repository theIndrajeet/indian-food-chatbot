from flask import Flask, request, jsonify, render_template_string
import requests
import json

app = Flask(__name__)

# --- Configuration for your Local LLM Server (LM Studio or Ollama) ---
# Option 1: LM Studio (if you prefer to use that locally)
LLM_API_URL = "http://localhost:1234/v1/chat/completions" # Default LM Studio
LLM_MODEL_NAME = "lmstudio-community/DeepSeek-R1-Distill-Qwen-7B" # Or your preferred model in LM Studio

# Option 2: Ollama (if you prefer to use that locally)
# LLM_API_URL = "http://localhost:11434/api/chat" # Default Ollama
# LLM_MODEL_NAME = "deepseek-coder:1.3b" # Or your preferred model in Ollama

# --- Basic HTML structure (We will improve this a LOT to match your design) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Food Recommender</title>
    <style>
        body { font-family: 'Arial', sans-serif; margin: 20px; background-color: #f9f9f9; color: #333; }
        .container { max-width: 700px; margin: auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #ff6347; } /* Tomato color for food theme */
        .chat-interface { margin-top: 20px; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .input-group input[type="text"], .input-group select {
            width: calc(100% - 22px); padding: 10px; border: 1px solid #ddd; border-radius: 4px;
        }
        .chat-box {
            height: 300px; border: 1px solid #ddd; border-radius: 4px; padding: 10px;
            overflow-y: auto; margin-bottom: 15px; background-color: #fdfdfd;
        }
        .message { margin-bottom: 10px; padding: 8px 12px; border-radius: 15px; line-height: 1.5; }
        .user-message { background-color: #ffe0b2; /* Light orange for user */ text-align: right; margin-left: 40px; }
        .bot-message { background-color: #c8e6c9; /* Light green for bot */ margin-right: 40px; white-space: pre-wrap; }
        .send-button {
            display: block; width: 100%; padding: 10px; background-color: #ff6347; color: white;
            border: none; border-radius: 4px; font-size: 16px; cursor: pointer; transition: background-color 0.3s;
        }
        .send-button:hover { background-color: #e5533d; }
        .disclaimer { font-size: 0.8em; color: #777; text-align: center; padding-top: 10px;}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Food Recommender</h1>
        
        <div class="input-group">
            <label for="mood">What's your current mood?</label>
            <select id="mood">
                <option value="">-- Select Mood --</option>
                <option value="happy">Happy & Energetic</option>
                <option value="sad">Sad / Comfort Food Needed</option>
                <option value="tired">Tired / Quick & Easy</option>
                <option value="celebratory">Celebratory / Special</option>
                <option value="stressed">Stressed / Soothing</option>
                <option value="adventurous">Feeling Adventurous</option>
                <option value="not_sure">Not Sure / Surprise Me!</option>
            </select>
        </div>

        <div class="input-group">
            <label for="query">Any specific cravings or ingredients on hand? (Optional)</label>
            <input type="text" id="query" placeholder="e.g., 'paneer', 'spicy', 'something light'">
        </div>
        
        <button class="send-button" onclick="getFoodSuggestion()">Get Food Suggestion!</button>
        
        <div class="chat-box" id="chatBox">
            </div>
        <div class="disclaimer">[IK Food Bot: Suggestions are for fun! Verify recipes and ingredients.]</div>
    </div>

    <script>
        const moodInput = document.getElementById('mood');
        const queryInput = document.getElementById('query');
        const chatBox = document.getElementById('chatBox');

        async function getFoodSuggestion() {
            const mood = moodInput.value;
            const query = queryInput.value.trim();

            if (mood === "") {
                appendMessage("Please select your mood!", 'bot-message');
                return;
            }

            let userPrompt = `My mood is: ${mood}.`;
            if (query !== "") {
                userPrompt += ` Additional notes or ingredients: ${query}.`;
            }
            userPrompt += " Can you suggest some Indian food for me?";
            
            appendMessage(`You: Mood - ${mood}, Notes - ${query || 'None'}`, 'user-message');
            chatBox.scrollTop = chatBox.scrollHeight; // Scroll to bottom

            // Disable button while waiting
            document.querySelector('.send-button').disabled = true;
            document.querySelector('.send-button').textContent = 'Thinking...';


            try {
                const response = await fetch('/suggest_food', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: userPrompt })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    appendMessage(`Error: ${errorData.error || 'Failed to get suggestion'}`, 'bot-message');
                    return;
                }

                const data = await response.json();
                appendMessage(`AI: ${data.suggestion}`, 'bot-message');

            } catch (error) {
                console.error('Error getting suggestion:', error);
                appendMessage('Sorry, there was an error connecting to the AI.', 'bot-message');
            } finally {
                document.querySelector('.send-button').disabled = false;
                document.querySelector('.send-button').textContent = 'Get Food Suggestion!';
            }
        }

        function appendMessage(text, className) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', className);
            messageDiv.textContent = text;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    </script>
</body>
</html>
"""

def ask_llm_for_food(user_prompt):
    headers = {"Content-Type": "application/json"}
    
    system_message = (
        "You are an expert Indian Food Recommender AI. You are friendly and enthusiastic. "
        "Based on the user's mood and any other preferences or ingredients they mention, "
        "suggest 1 to 3 specific Indian dishes. "
        "Briefly explain why each dish fits the mood/criteria. "
        "If they mention ingredients, try to suggest dishes that can use those ingredients. "
        "Keep suggestions authentic to Indian cuisine. "
        "If a mood is 'Not Sure / Surprise Me!', be creative but suggest popular and generally liked dishes. "
        "Format your answer clearly, perhaps with dish names in bold."
    )
    
    # This payload structure is for OpenAI-compatible APIs (like LM Studio's default or Ollama's /api/chat)
    data = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8, # A bit more creative for food suggestions
        "max_tokens": 400  # Allow for slightly longer suggestions with reasons
    }

    try:
        print(f"Sending to LLM: {user_prompt}")
        response = requests.post(LLM_API_URL, headers=headers, data=json.dumps(data), timeout=120)
        response.raise_for_status()
        
        response_json = response.json()
        
        # Adjust based on whether you're using LM Studio or Ollama for the response structure
        if "v1/chat/completions" in LLM_API_URL: # LM Studio like structure
            suggestion = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        elif "/api/chat" in LLM_API_URL: # Ollama like structure
            suggestion = response_json.get("message", {}).get("content", "")
        else:
            suggestion = "Error: LLM API URL not recognized for response parsing."

        if not suggestion:
            return "The AI gave an empty suggestion. Try rephrasing!"
        
        return suggestion.strip()

    except requests.exceptions.Timeout:
        print("LLM request timed out.")
        return "Sorry, the AI is taking too long to think of food!"
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to LLM: {e}")
        return "Sorry, I couldn't connect to the AI model server. Is it running?"
    except Exception as e:
        print(f"Unexpected error in ask_llm_for_food: {e}")
        return "Sorry, an unexpected error occurred with the AI."

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/suggest_food", methods=['POST'])
def suggest_food_route():
    try:
        data = request.json
        user_prompt_from_js = data.get('prompt')

        if not user_prompt_from_js:
            return jsonify({"error": "No prompt provided from frontend"}), 400

        ai_suggestion = ask_llm_for_food(user_prompt_from_js)
        return jsonify({"suggestion": ai_suggestion})
        
    except Exception as e:
        print(f"Error in /suggest_food endpoint: {e}")
        return jsonify({"error": "Server error processing food suggestion request"}), 500

if __name__ == "__main__":
    print("Starting Food Recommender Web Server...")
    print(f"Attempting to connect to LLM at: {LLM_API_URL} with model {LLM_MODEL_NAME}")
    print("Make sure your local LLM server (LM Studio or Ollama) is running with the model loaded!")
    print("Open your web browser and go to http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)