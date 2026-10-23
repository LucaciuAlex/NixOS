import os
import json
import requests
from pathlib import Path

class Formatting:
    Bold = "\x1b[1m"
    Dim = "\x1b[2m"
    Italic = "\x1b[3m"
    Underlined = "\x1b[4m"
    Blink = "\x1b[5m"
    Reverse = "\x1b[7m"
    Hidden = "\x1b[8m"
    # Reset part
    Reset = "\x1b[0m"
    Reset_Bold = "\x1b[21m"
    Reset_Dim = "\x1b[22m"
    Reset_Italic = "\x1b[23m"
    Reset_Underlined = "\x1b[24"
    Reset_Blink = "\x1b[25m"
    Reset_Reverse = "\x1b[27m"
    Reset_Hidden = "\x1b[28m"

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL_NAME = os.getenv("LOCAL_GPT_MODEL", "llama3.1:8b")   # "qwen3.5:9B")
ALLOWED_ROOT = Path.cwd()
OBSIDIAN_VAULT_DIR = Path("./A.I.Brain").expanduser()

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
            
    return f"Error: Unknown tool {tool_name}"

def streamThinking(message):
    # 1. Capture internal reasoning/thinking tokens (if model uses them)
    thinking_chunk = message.get("thinking", "")
    if thinking_chunk:
        # full_thinking += thinking_chunk
        # Optional: print thinking tokens if you want to see reasoning live
        print(Formatting.Dim + thinking_chunk, end="", flush=True)
        return True
    return False

def streamContent(message):
    # 2. Print regular text tokens in real time
    content_chunk = message.get("content", "")
    if content_chunk:
        # full_content += content_chunk
        print(content_chunk, end="", flush=True)
    

# Obsolete, for debugging and testing only
def run_agent(prompt: str):
    messages = [
        {"role": "system", "content": "You are a helpful assistant with file creation capabilities. Use the provided tools when requested."},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": TOOLS,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=60)
        if not response.ok:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return

        result = response.json()

        for key in result.keys():
            if isinstance(result[key], dict):
                print(f"{key} -> {result[key].keys()}")
            else:
                print(key)

        message = result.get("message", {})

        # Check if the model decided to call a tool
        if "tool_calls" in message:
            print("🔧 Model invoked a tool call natively!")
            for tool_call in message["tool_calls"]:
                func_info = tool_call.get("function", {})
                func_name = func_info.get("name")
                func_args = func_info.get("arguments", {})
                
                print(f"-> Executing tool: {func_name} with args: {func_args}")
                tool_output = execute_tool(func_name, func_args)
                print(f"-> Result: {tool_output}")
        else:
            # Regular text response if no tool was needed
            print(f"💬 Assistant: {message.get('content', '')}")
    except Exception as e:
        print(e)

def run_agent_streaming(prompt: str):
    messages = [
        {"role": "system", "content": "You are a helpful assistant with file creation capabilities. Use the provided tools when requested."},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": TOOLS,
        "stream": True  # <-- Enables streaming responses
    }

    try:
        # stream=True keeps the connection open to read chunks incrementally
        response = requests.post(OLLAMA_CHAT_URL, json=payload, stream=True, timeout=60)
        if not response.ok:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return

        full_content = ""
        full_thinking = ""
        accumulated_tool_calls = []

        print(f"[{MODEL_NAME}]:")

        doneThinking = False

        # Iterate line-by-line through Ollama's streaming NDJSON output
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                message = chunk.get("message", {})

                # Stream the thinking process
                isThinking = streamThinking(message)

                if doneThinking and not isThinking:
                    print(Formatting.Reset + "\n")
                    doneThinking = False
                if isThinking:
                    doneThinking = isThinking

                # Stream the response contend the LLM provided to the user
                streamContent(message)

                # 3. Capture tool call payloads if the model decides to trigger a tool
                if "tool_calls" in message:
                    accumulated_tool_calls = message["tool_calls"]

        print() # Print newline after text stream finishes

        # Execute the tool after text streaming completes (if any were requested)
        if accumulated_tool_calls:
            print("\n🔧 Model invoked a tool call natively!")
            for tool_call in accumulated_tool_calls:
                func_info = tool_call.get("function", {})
                func_name = func_info.get("name")
                func_args = func_info.get("arguments", {})
                
                print(f"-> Executing tool: {func_name} with args: {func_args}")
                tool_output = execute_tool(func_name, func_args)
                print(f"-> Result: {tool_output}")

    except Exception as e:
        print(f"\n⚠️ Error during streaming: {e}")




run_agent("what day is today?")

# # Example usage
# if __name__ == "__main__":
#     while True:
#         userPrompt = input(">>>")
#         run_agent_streaming(userPrompt)