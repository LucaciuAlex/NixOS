#!/usr/bin/env python3
import os
import sys
import json
import requests
import re
from datetime import datetime

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
LOG_FILE = "session_log.md"
STATE_FILE = ".session_state.json"

BLINK = lambda x: f"\033[32;5m {x} \033[0m"

# resolve the path for the manifest file
MANIFEST_PATH = os.environ.get("AGENT_MANIFEST_PATH", "models_manifest.json")
SYS_PROMPT_PATH = os.environ.get("ORCHESTRATOR_SYSTEM_PROMPT_PATH", "models_manifest.json")

def load_manifest():
    try:
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading models manifest from {MANIFEST_PATH}: {e}")
        sys.exit(1)

MANIFEST = load_manifest()

def load_history():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def load_history():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def generate_arbitrator_system_prompt():
    manifest_str = json.dumps(MANIFEST, indent=2)
    history_str = json.dumps(load_history(), indent=2)
    try:
        with open(SYS_PROMPT_PATH, "r") as f:
            sysPrompt = f.read().replace('\n', ' ')
            sysPrompt.replace("<<manifest_str>>", manifest_str)
            sysPrompt.replace("<<conversation_history>>", history_str)
            return sysPrompt

    except Exception as e:
        print(f"❌ Error loading the system prompts and history {SYS_PROMPT_PATH}: {e}")
        sys.exit(1)

def setup_session_files():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("# Persistent Local NixOS Agent Orchestration Ledger\n")
            f.write(f"* **Initialized at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
#           f.write("* **Environment:** HP ZBook Laptop (RTX A3000 6GB VRAM, 32GB RAM)\n")
            f.write("---\n\n")
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump([], f)



def save_history(history):
    with open(STATE_FILE, "w") as f:
        json.dump(history, f, indent=2)

def append_to_ledger(text):
    with open(LOG_FILE, "a") as f:
        f.write(text + "\n")

def query_ollama(model, system_prompt, messages):
    payload_messages = [{"role": "system", "content": system_prompt}] + messages
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": payload_messages,
            "stream": False
        })
        r.raise_for_status()
        return r.json()['message']['content']
    except Exception as e:
        print(f"\n❌ Error contacting local Ollama service: {e}")
        return None

def extract_json_block(text):
    """Robust extraction of JSON payload even if the LLM includes conversational filler."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text

def main_loop():
    setup_session_files()
    history = load_history()

    print("\n=======================================================")
    print("🤖 NixOS Assistant Orchestrator Activated")
    print("💬 Type your prompt to begin.")
    print("🚪 Type 'exit' or '/end' to gracefully save and close the session.")
    print("=======================================================\n")

    while True:
        try:
            user_input = input(">>>").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Exiting session loop safely...")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "/end"]:
            print("\n💾 Session successfully preserved. Ledger saved to 'session_log.md'.")
            print("👋 Have a great day!")
            break

        history.append({"role": "user", "content": user_input})

        print("⚖️ [Arbitrator] Evaluating proficiencies...")
        arbitrator_prompt = generate_arbitrator_system_prompt()

        # FIX: We now pass the entire context (history) so the Arbitrator understands follow-up requests (e.g., "fix this")
        arbitrator_raw = query_ollama("llama3.1:8b", arbitrator_prompt, history)

        if not arbitrator_raw:
            print("⚠️ Orchestrator decision failed. Defaulting to generalist Llama 3.1.")
            selected_model = "llama3.1:8b"
            reasoning = "Fallback default due to connection error."
        else:
            try:
                clean_json = extract_json_block(arbitrator_raw.strip())
                decision = json.loads(clean_json)
                reasoning = decision.get("reasoning", "No specific reasoning recorded.")
                selected_model = decision.get("selected_model", "llama3.1:8b")

                # Double-check that the model selected actually exists in our manifest
                if selected_model not in MANIFEST:
                    print(f"⚠️ Arbitrator hallucinated model ID '{selected_model}'. Falling back to Llama.")
                    selected_model = "llama3.1:8b"
            except Exception:
                reasoning = "Failed to parse Arbitrator JSON syntax output. Defaulting to generalist."
                selected_model = "llama3.1:8b"

        model_info = MANIFEST.get(selected_model, {"name": "Llama 3.1 (8B)", "role": "Generalist, Systems & Web Research Assistant"})
        model_display = model_info.get("name")
        model_role = model_info.get("role")

        print(f"🎯 [Match] Selected: {model_display} (Role: {model_role})")
        print(f"📖 [Reason] {reasoning}\n")

        log_step = len([msg for msg in history if msg['role'] == 'user'])
        ledger_entry = f"""## 🔄 Step {log_step}
* **Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
* **User Input:** `{user_input}`

### ⚖️ Arbitrator Evaluation & Match
* **Selected Engine:** **{model_display}** (`{selected_model}`)
* **Assigned Role:** *{model_role}*
* **Reasoning:**
  > "{reasoning}"

### 🧠 {model_display} Thinking & Output
"""
        append_to_ledger(ledger_entry)

        print(f"🚀 [{model_display}] Processing command...")

        if "coder" in selected_model:
            system_prompt = "You are the NixOS Assistant (Specialist: Code & Compilers). Your focus is syntax precision, Nix modules, and microcontroller engineering. Provide exact code, configs, or terminal lines."
        else:
            system_prompt = "You are the NixOS Assistant (Specialist: Generalist & Research). Your focus is file structures, concepts, explanations, and system architecture."

        agent_response = query_ollama(selected_model, system_prompt, history)

        if not agent_response:
            agent_response = "❌ Failed to retrieve response from local specialist."

        print("\n----------------- Specialist Output -----------------")
        print(agent_response)
        print("-----------------------------------------------------\n")

        append_to_ledger(agent_response + "\n\n---\n")
        history.append({"role": "assistant", "content": agent_response})
        save_history(history)

if __name__ == "__main__":
    main_loop()
