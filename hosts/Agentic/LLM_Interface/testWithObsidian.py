import os
import json
import requests
from pathlib import Path

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL_NAME = os.getenv("LOCAL_GPT_MODEL", "qwen3.5:9B")
OBSIDIAN_VAULT_DIR = Path("./A.I.Brain")

# Define the tools available to the model
with open("toolsDefinition.json", "r") as f:
    TOOLS = json.load(f)

def execute_tool(tool_name, arguments):
    """Safely execute the requested tool after validating boundaries."""
    if tool_name == "create_file":
        file_path = arguments.get("file_path")
        content = arguments.get("content")
        
        # Security sandbox check
        full_path = (ALLOWED_ROOT / file_path).resolve()
        if not str(full_path).startswith(str(ALLOWED_ROOT.resolve())):
            return "Error: Permission denied. Path is outside the allowed root directory."
        
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: File created at {full_path}"
        except Exception as e:
            return f"Error writing file: {e}"
            
    elif tool_name == "write_memory":
        filename = arguments.get("filename")
        content = arguments.get("content")
        
        if not filename.endswith(".md"):
            filename += ".md"
            
        full_path = (OBSIDIAN_VAULT_DIR / filename).resolve()
        if not str(full_path).startswith(str(OBSIDIAN_VAULT_DIR.resolve())):
            return "Error: Access denied outside the Obsidian vault."
            
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: Saved '{filename}' with graph links."
        except Exception as e:
            return f"Error writing memory: {e}"
            
    elif tool_name == "read_memory":
        filename = arguments.get("filename")
        if not filename.endswith(".md"):
            filename += ".md"
            
        full_path = (OBSIDIAN_VAULT_DIR / filename).resolve()
        if not full_path.exists():
            return f"Error: Note '{filename}' not found."
            
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Brain Feature: Extract and load connected notes (1-hop traversal)
            linked_notes = extract_wikilinks(content)
            graph_context = "\n\n--- [Obsidian Graph Context: Connected Notes] ---\n"
            
            for link in linked_notes:
                link_path = (OBSIDIAN_VAULT_DIR / f"{link}.md").resolve()
                if link_path.exists() and str(link_path).startswith(str(OBSIDIAN_VAULT_DIR.resolve())):
                    with open(link_path, "r", encoding="utf-8") as lf:
                        # Pull a snippet of the linked note
                        snippet = lf.read()[:300].replace("\n", " ")
                        graph_context += f"- **[[{link}]]**: {snippet}...\n"
                else:
                    graph_context += f"- **[[{link}]]**: (Note does not exist yet)\n"
            
            return content + (graph_context if linked_notes else "")
            
        except Exception as e:
            return f"Error reading memory: {e}"
            
    return f"Error: Unknown tool {tool_name}"


def run_agent_agentic_loop(initial_prompt: str):
    messages = [
        {
            "role": "system", 
            "content": (
                "You are an AI brain assistant connected to Obsidian. "
                "You can call 'read_memory' to explore notes and their connected [[Wikilinks]]. "
                "If you need more context to answer the user, call a tool, inspect the data, "
                "and continue your reasoning until you have the final answer."
            )
        },
        {"role": "user", "content": initial_prompt}
    ]

    # Maximum turns to prevent infinite loops
    max_turns = 5
    turn = 0

    while turn < max_turns:
        turn += 1
        
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "tools": TOOLS,
            "stream": False # Non-streaming is cleaner for multi-turn orchestration
        }

        try:
            response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=60)
            if not response.ok:
                print(f"Ollama Error: {response.status_code}")
                break

            result = response.json()
            message = result.get("message", {})

            # 1. If the model generated thinking/content, show it
            if message.get("thinking"):
                print(f"🧠 [Thinking]: {message['thinking'][:150]}...")
            
            if message.get("content"):
                print(f"💬 Assistant: {message['content']}")

            # 2. Check if the model wants to call a tool
            tool_calls = message.get("tool_calls")
            
            if tool_calls:
                # IMPORTANT: Append the assistant's message (containing the tool call) to history
                messages.append(message)

                for tool_call in tool_calls:
                    func_info = tool_call.get("function", {})
                    func_name = func_info.get("name")
                    func_args = func_info.get("arguments", {})
                    
                    print(f"\n🔧 [Turn {turn}] Executing tool: {func_name} with args: {func_args}")
                    
                    # Execute your Obsidian memory tool (which fetches note + linked notes)
                    tool_output = execute_tool(func_name, func_args)
                    print(f"-> Obsidian Data Retrieved (Length: {len(tool_output)} chars)")

                    # Append the tool's output back into the message history
                    # Ollama expects role 'tool' (or 'function') with the result
                    messages.append({
                        "role": "tool",
                        "content": str(tool_output)
                    })
                
                # Loop continues automatically, sending the updated history back to Ollama
                print("🔄 Feeding data back to model for next reasoning step...\n")
                continue
            else:
                # No more tools requested; the agent has finished its task
                break

        except Exception as e:
            print(f"\n⚠️ Error in agent loop: {e}")
            break

if __name__ == "__main__":
    run_agent_agentic_loop("What do my notes say about my NixOS configuration, and how does it connect to my python workflow?")