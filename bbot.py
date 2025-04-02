#!/usr/bin/env python3
from flask import Flask, render_template_string, request, jsonify, send_from_directory
import os
import requests
import json
from dotenv import load_dotenv
import threading
import time
import sys

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Error: OPENAI_API_KEY not found in environment variables")
    sys.exit(1)

# Configuration
API_URL = "https://api.openai.com/v1/chat/completions"
AVAILABLE_MODELS = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]

# Initial prompt
INITIAL_PROMPT = """You are an expert in writing, copywriting, marketing, market research, offer creation, and behavioral psychology. Your job is to write a compelling document for my desired target audience.

The ultimate goal is to profoundly understand my market and develop world-class messaging, which will give me the strategic positioning needed to dominate and scale this market.

To do this, I will give you the following:

1. My Target Niche
2. My previous thoughts and understanding of that niche
3. Context about my company and my offering to this niche
4. Market study questions
5. Competitive Analysis questions
6. Offer Value questions for my product

You write in a conversational, jargon-free tone that a 10-year-old would understand. Be conversational and plain.

Sounds good?"""

# Prompt templates
INTERACTIVE_PROMPT_TEMPLATES = [
    """Great
1. My target niche: This time, I'm aiming to reach out to **{0}**
2. My previous thoughts and understanding of this niche: **{0}**
I can provide you with the context about my company if this is clear. 
Sounds good?""",
    
    """Now, some context about my company and my offer to this niche, **{0}**"""
]

SCRIPTED_PROMPTS = [
    """**Market Study: Demographics**
Please provide general demographics data about my target audience:
* Gender
* Age
* Income
* Geographic Location (Lifestyle)""",

    """**Market Study: Pain Points**
What are the demonetized pain points, desires, and objections?
- What Do They See? 
- What do they hear?
- What do they think & feel?
- What do they see & do?
- Pains, Frustrations, Fears, Problems
- Dreams, Desires, Hopes, Wants, Needs 
- Objections""",

    """**Market Study: Desires**
- List the mass desires of this target market.
- Select the broadest one with the most power.
- List the product performance that satisfies that desire.
- Pick the ONE product performance that is unique and powerfully fulfills the desire.""",

    """**Market Sophistication & Awareness**
Identify the level of market awareness for my offer:
1. Most aware (know product name and price)
2. Product Aware (know product but not price)
3. Solution aware (know possible solution exists)
4. Problem aware (may or may not know they have problem)
5. Unaware (completely new market)""",

    """**Competitor Analysis**
Search for my top 3 competitors that have a similar offer to this niche:
1. 
2.
3,""",

    """**Competitor Positioning**
For each competitor:
1. What is their product/service positioning?
2. What are the deliverables? 
3. Price point? 
4. Payment terms? 
5. Bonuses? 
6. Guarantees/Risk Reversals?""",

    """**Competitor Messaging**
Common headlines competitors are using:
1.
2.
3,
How do competitors position themselves?
1,
2,
3,
What is their unique selling proposition?
1,
2,
3,
What promises and claims are they making?
1,
2,
3,""",

    """**Competitor Mechanisms**
What unique mechanisms are competitors using?
1,
2,
3,
What are people saying in testimonials?
1,
2,
3,
Top sites competitors are advertising on:
1,
2,
3,""",

    """**Offer Appeal**
Categorize my company's appeal:
1. Sex appeal (relationships, social acceptance)
2. Greed (things money can buy)
3. Fear (of losing or not gaining)
4. Duty/honor (what's best for people served)""",

    """**Unique Selling Proposition**
Establish my USP aligned with current offering:
- Most powerful benefit with emotional pulling power
- Current biggest growing trends in market
- How to position as unique characteristic
- How to communicate clearly and concisely
- Can I create a "new category" or niche down?""",

    """**Compiling Final Document**
Compile all responses into a comprehensive marketing strategy document with:
1. Target Niche Analysis
2. Competitive Landscape
3. Offer Positioning & Strategic Advantage
Write in clear, plain, powerful language with bullet points where needed."""
]

PROMPT_NAMES = [
    "Collecting Demographic Data",
    "Analyzing Pain Points",
    "Identifying Market Desires",
    "Assessing Market Awareness",
    "Finding Competitors",
    "Analyzing Competitor Positioning",
    "Studying Competitor Messaging",
    "Examining Competitor Mechanisms",
    "Defining Our Appeal",
    "Crafting Unique Selling Proposition",
    "Compiling Final Strategy Document"
]

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global state
conversation_state = {
    'history': [],
    'step': 0,  # 0=start, 1=niche, 2=offer, 3=processing, 4=complete
    'model': AVAILABLE_MODELS[0],
    'final_response': None,
    'current_prompt': 0,
    'progress': 0,
    'status': "Ready to start",
    'is_processing': False
}

def get_chatgpt_response(prompt, model, history=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    messages = history + [{"role": "user", "content": prompt}] if history else [{"role": "user", "content": prompt}]
    
    try:
        response = requests.post(API_URL, headers=headers, json={
            "model": model,
            "messages": messages,
            "temperature": 0.7
        })
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API Error: {str(e)}")
        return f"Error: {str(e)}"

def process_all_scripted_prompts():
    conversation_state['is_processing'] = True
    conversation_state['step'] = 3
    conversation_state['progress'] = 0
    
    for i, prompt in enumerate(SCRIPTED_PROMPTS):
        conversation_state['current_prompt'] = i
        conversation_state['status'] = PROMPT_NAMES[i]
        conversation_state['progress'] = int((i / len(SCRIPTED_PROMPTS))) * 100
        
        response = get_chatgpt_response(prompt, conversation_state['model'], conversation_state['history'])
        
        conversation_state['history'].extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ])
        
        time.sleep(1)  # Rate limiting
    
    # Final compilation
    conversation_state['status'] = "Finalizing document"
    final_response = get_chatgpt_response(
        "Compile all previous responses into a comprehensive marketing strategy document with clear sections.",
        conversation_state['model'],
        conversation_state['history']
    )
    
    conversation_state['final_response'] = final_response
    conversation_state['step'] = 4
    conversation_state['progress'] = 100
    conversation_state['status'] = "Complete"
    conversation_state['is_processing'] = False

# HTML Template with embedded JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Marketing Research Assistant</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        #chat-container { margin-bottom: 20px; }
        #progress-container { display: none; margin: 20px 0; }
        #progress-bar { height: 20px; background: #ddd; border-radius: 4px; overflow: hidden; }
        #progress-bar-fill { height: 100%; width: 0%; background: #4CAF50; transition: width 0.3s; }
        #status-text { margin-top: 10px; font-style: italic; }
        #results-container { display: none; margin-top: 20px; }
        #final-response { white-space: pre-wrap; background: #f5f5f5; padding: 15px; border-radius: 4px; }
        button { padding: 10px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #45a049; }
        textarea { width: 100%; padding: 10px; margin: 10px 0; }
        .message { margin: 10px 0; padding: 10px; border-radius: 4px; }
        .user { background: #e6f7ff; }
        .assistant { background: #f0f0f0; }
        #model-selector { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Marketing Research Assistant</h1>
    
    <div id="model-selector">
        <label for="model">Select Model:</label>
        <select id="model">
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4-turbo">GPT-4 Turbo</option>
            <option value="gpt-4">GPT-4</option>
            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
        </select>
        <button id="start-btn">Start New Session</button>
    </div>
    
    <div id="chat-container">
        <div id="chat-history"></div>
        <form id="input-form">
            <input type="hidden" id="current-step" value="0">
            <div id="input-area">
                <textarea id="user-input" rows="3" placeholder="Type your response..."></textarea>
                <button type="submit">Send</button>
            </div>
        </form>
    </div>

    <div id="progress-container">
        <h3>Processing Research...</h3>
        <div id="progress-bar">
            <div id="progress-bar-fill"></div>
        </div>
        <p id="status-text">Starting analysis...</p>
    </div>

    <div id="results-container">
        <button id="download-btn">Download Strategy Document</button>
        <div id="final-response"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const chatHistory = document.getElementById('chat-history');
            const inputForm = document.getElementById('input-form');
            const userInput = document.getElementById('user-input');
            const currentStep = document.getElementById('current-step');
            const startBtn = document.getElementById('start-btn');
            const modelSelect = document.getElementById('model');
            
            // Start new session
            startBtn.addEventListener('click', function() {
                startConversation(modelSelect.value);
            });
            
            // Form submission handler
            inputForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const text = userInput.value.trim();
                if (text) {
                    sendMessage(text);
                    userInput.value = '';
                }
            });
            
            // Start conversation
            function startConversation(model) {
                chatHistory.innerHTML = '';
                document.getElementById('progress-container').style.display = 'none';
                document.getElementById('results-container').style.display = 'none';
                
                fetch('/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `model=${model}`
                })
                .then(response => response.json())
                .then(data => {
                    addMessage('assistant', data.response);
                    currentStep.value = data.step;
                    document.getElementById('input-area').style.display = 'block';
                });
            }
            
            // Send message to server
            function sendMessage(text) {
                addMessage('user', text);
                
                fetch('/next', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `input=${encodeURIComponent(text)}&step=${currentStep.value}`
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        addMessage('error', data.error);
                        return;
                    }
                    
                    currentStep.value = data.step;
                    
                    if (data.response) {
                        addMessage('assistant', data.response);
                    }
                    
                    if (data.auto_proceed || data.step === 3) {
                        // Show progress and start checking
                        document.getElementById('progress-container').style.display = 'block';
                        checkProgress();
                    }
                    
                    if (data.complete) {
                        document.getElementById('input-area').style.display = 'none';
                    }
                });
            }
            
            // Check progress periodically
            function checkProgress() {
                fetch('/progress')
                .then(response => response.json())
                .then(data => {
                    // Update progress UI
                    document.getElementById('progress-bar-fill').style.width = data.progress + '%';
                    document.getElementById('status-text').innerText = data.status;
                    
                    if (data.complete) {
                        // Show results
                        document.getElementById('progress-container').style.display = 'none';
                        document.getElementById('results-container').style.display = 'block';
                        
                        // Get and display final response
                        fetch('/get_final_response')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('final-response').textContent = data.response;
                        });
                    } else {
                        // Continue checking
                        setTimeout(checkProgress, 2500);
                    }
                });
            }
            
            // Download button handler
            document.getElementById('download-btn').addEventListener('click', function() {
                window.location.href = '/download';
            });
            
            // Helper to add messages to chat
            function addMessage(role, content) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${role}`;
                messageDiv.innerHTML = `<strong>${role === 'user' ? 'You' : 'Assistant'}:</strong> ${content}`;
                chatHistory.appendChild(messageDiv);
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
def start_conversation():
    conversation_state.update({
        'history': [],
        'step': 0,
        'model': request.form.get('model', AVAILABLE_MODELS[0]),
        'final_response': None,
        'current_prompt': 0,
        'progress': 0,
        'status': "Starting...",
        'is_processing': False
    })
    
    response = get_chatgpt_response(INITIAL_PROMPT, conversation_state['model'])
    conversation_state['history'].extend([
        {"role": "user", "content": INITIAL_PROMPT},
        {"role": "assistant", "content": response}
    ])
    conversation_state['step'] = 1
    
    return jsonify({
        'response': response,
        'step': 1,
        'user_prompt': "Please enter your target niche information:",
        'status': conversation_state['status']
    })

@app.route('/next', methods=['POST'])
def next_step():
    user_input = request.form.get('input', '').strip()
    
    if conversation_state['step'] == 1:  # Niche info
        prompt = INTERACTIVE_PROMPT_TEMPLATES[0].format(user_input)
        response = get_chatgpt_response(prompt, conversation_state['model'], conversation_state['history'])
        
        conversation_state['history'].extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ])
        conversation_state['step'] = 2
        
        return jsonify({
            'response': response,
            'step': 2,
            'user_prompt': "Now please provide context about your company and offer:",
            'status': conversation_state['status']
        })
    
    elif conversation_state['step'] == 2:  # Company info
        prompt = INTERACTIVE_PROMPT_TEMPLATES[1].format(user_input)
        response = get_chatgpt_response(prompt, conversation_state['model'], conversation_state['history'])
        
        conversation_state['history'].extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ])
        
        # Start processing all scripted prompts in background
        if not conversation_state['is_processing']:
            threading.Thread(target=process_all_scripted_prompts).start()
        
        return jsonify({
            'response': "Great! I'm now processing all the marketing research questions. This may take a few minutes...",
            'step': 3,
            'status': "Starting analysis...",
            'progress': 0,
            'auto_proceed': False
        })
    
    return jsonify({'error': 'Invalid step'})

@app.route('/progress')
def get_progress():
    return jsonify({
        'step': conversation_state['step'],
        'progress': conversation_state['progress'],
        'status': conversation_state['status'],
        'current_prompt': conversation_state['current_prompt'],
        'total_prompts': len(SCRIPTED_PROMPTS),
        'complete': conversation_state['step'] == 4,
        'is_processing': conversation_state['is_processing']
    })

@app.route('/download')
def download():
    if not conversation_state['final_response']:
        return jsonify({'error': 'Document not ready yet'}), 404
    
    filename = "marketing_strategy.txt"
    with open(filename, 'w') as f:
        f.write(conversation_state['final_response'])
    
    return send_from_directory('.', filename, as_attachment=True)

@app.route('/get_final_response')
def get_final_response():
    if conversation_state['step'] != 4:
        return jsonify({'error': 'Document not ready yet'}), 404
    return jsonify({'response': conversation_state['final_response']})

if __name__ == '__main__':
    print("Starting Marketing Research Assistant...")
    app.run(host='0.0.0.0', port=5000, debug=False)