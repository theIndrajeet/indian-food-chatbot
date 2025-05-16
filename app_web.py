from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
import requests
import json

app = Flask(__name__)
CORS(app) # Enable CORS for all routes, allowing requests from any origin by default.
          # For production, you might want to restrict origins: CORS(app, resources={r"/suggest_food": {"origins": "https://your-netlify-site.netlify.app"}})

# --- Configuration for your Local LLM Server (LM Studio or Ollama) ---
# Ensure one of these is uncommented and correctly configured for your local setup
# Option 1: LM Studio
LLM_API_URL = "http://localhost:1234/v1/chat/completions" 
LLM_MODEL_NAME = "lmstudio-community/DeepSeek-R1-Distill-Qwen-7B" # Or your preferred model in LM Studio

# Option 2: Ollama 
# LLM_API_URL = "http://localhost:11434/api/chat" 
# LLM_MODEL_NAME = "deepseek-coder:1.3b" # Or your preferred model in Ollama

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

    data = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 400
    }

    try:
        print(f"Sending to LLM: {user_prompt}")
        response = requests.post(LLM_API_URL, headers=headers, data=json.dumps(data), timeout=120)
        response.raise_for_status()

        response_json = response.json()

        suggestion = ""
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

@app.route("/") # Optional: A simple message to show the API is running
def api_home():
    return jsonify({"message": "IK Food Recommender API is running!"})

@app.route("/suggest_food", methods=['POST', 'OPTIONS']) # Added OPTIONS for CORS preflight
def suggest_food_route():
    if request.method == 'OPTIONS': # Handle CORS preflight request
        return _build_cors_preflight_response()

    try:
        data = request.json
        user_prompt_from_js = data.get('prompt')

        if not user_prompt_from_js:
            return jsonify({"error": "No prompt provided from frontend"}), 400

        ai_suggestion = ask_llm_for_food(user_prompt_from_js)
        response = jsonify({"suggestion": ai_suggestion})
        return _corsify_actual_response(response) # Add CORS headers to actual response

    except Exception as e:
        print(f"Error in /suggest_food endpoint: {e}")
        return jsonify({"error": "Server error processing food suggestion request"}), 500

# --- CORS Helper Functions ---
def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*") # Or your specific Netlify domain in production
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

def _corsify_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*") # Or your specific Netlify domain in production
    return response

# This import is needed for make_response if you are using older Flask, but usually included with jsonify
from flask import make_response 

if __name__ == "__main__":
    print("Starting Food Recommender API Server (Backend)...")
    print(f"Attempting to connect to LLM at: {LLM_API_URL} with model {LLM_MODEL_NAME}")
    print("Make sure your local LLM server (LM Studio or Ollama) is running with the model loaded!")
    print("API will be available. Frontend (HTML) needs to be served separately.")
    app.run(host='127.0.0.1', port=5000, debug=True)