import os
import json
import requests
from pathlib import Path
from TOOLBOX import Tools

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


def executeAllTools(tool_calls):
    # Execute the tool after text streaming completes (if any were requested)
    if tool_calls:
        toolCalsList = []
        toolResponsesList = []

        for tool_call in tool_calls:

            tool_ID = tool_call.get("id")
            func_info = tool_call.get("function", {})
            func_name = func_info.get("name")
            func_args = func_info.get("arguments", {})
            
            
            print(f"[[{func_name}]]({func_args}")
            tool_output = executeTool(func_name, func_args)
            print(f"-> {tool_output}")

            logToolCall = {
                "id": f"{tool_ID}",
                "type": "function",
                "function": {
                    "name": f"{func_name}",
                    "arguments": {}
                }
            }
            for key in func_args.keys():
                logToolCall["function"]["arguments"][key] = func_args[key]

            toolCalsList.append(logToolCall)

            logResponse = {
                "role": "tool",
                "name": f"{func_name}",
                "tool_call_id": f"{tool_ID}",
                "content": f"{tool_output}"
            }
            toolResponsesList.append(logResponse)

    return toolCalsList, toolResponsesList

def executeTool(tool_name, arguments):
    """Safely execute the requested tool after validating boundaries."""
    if tool_name == "create_file":
        return Tools().create_file(arguments)
    if tool_name == "read_file":
        return Tools().read_file(arguments)
    if tool_name == "self_git_status":
        return Tools().git.status(arguments)
    if tool_name == "self_git_add":
        return Tools().git.add(arguments)
    if tool_name == "self_git_reset":
        return Tools().git.reset(arguments)
    if tool_name == "self_git_commit":
        return Tools().git.commit(arguments)
    if tool_name == "self_git_checkout":
        return Tools().git.checkout(arguments)


    return f"Error: Unknown tool {tool_name}"


def streamThinking(message):
    # 1. Capture internal reasoning/thinking tokens (if model uses them)
    thinking_chunk = message.get("thinking", "")
    if thinking_chunk:
        # full_thinking += thinking_chunk
        # Optional: print thinking tokens if you want to see reasoning live
        print(Formatting.Dim + thinking_chunk, end="", flush=True)
        return thinking_chunk
    return False

def streamContent(message):
    # 2. Print regular text tokens in real time
    content_chunk = message.get("content", "")
    if content_chunk:
        # full_content += content_chunk
        print(content_chunk, end="", flush=True)
        return content_chunk

def run_agent_streaming(messages: list):

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
            return []

        doneThinking = False
        fullThinking = ""
        fullContent = ""

        print(f"[{MODEL_NAME}]:")

        # Iterate line-by-line through Ollama's streaming NDJSON output
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                message = chunk.get("message", {})

                # Stream the thinking process
                thinkingChunk = streamThinking(message)
                isThinking = ( thinkingChunk != False )
                if thinkingChunk:
                    fullThinking += thinkingChunk

                if doneThinking and not isThinking:
                    print(Formatting.Reset + "\n")
                    doneThinking = False
                    # revealStructure(chunk)
                    # calculateStatistics(payload, chunk)
                if isThinking:
                    doneThinking = isThinking

                # Stream the response contend the LLM provided to the user
                contentChunk = streamContent(message)
                if contentChunk:
                    fullContent += contentChunk

                # 3. Capture tool call payloads if the model decides to trigger a tool
                if "tool_calls" in message:
                    accumulated_tool_calls = message["tool_calls"]

        # else:
        #     chunk["message"]["thinking"] = fullThinking
        #     chunk["message"]["content"] = fullContent
        #     # printMetadata(chunk)
        #     calculateStatistics(payload, chunk)

                

        print() # Print newline after text stream finishes

        print(accumulated_tool_calls)

        toolCalsList, toolResponsesList = executeAllTools(accumulated_tool_calls)

        assistantRoundLog = {
                    "role": "assistant",
                    "reasoning_content": fullThinking,
                    "content": fullContent,
                    "tool_calls": toolCalsList
                }

        return [assistantRoundLog] + toolResponsesList

    except Exception as e:
        print(f"\n⚠️ Error during streaming: {e}")




# run_agent("what day is today?")

# Example usage
if __name__ == "__main__":

    system_prompt = f"""
        You are a helpful local AI assistant running on NixOS. 
        ----
        You have an internal git versioning sysem that you will use to safelly update files.
        Use the internal git to save the state of the filesystem before making any changes, and rollback in case you need it.
        You will also need to read content of the files that were changed by external entities, such as the user, or other programs, in order to always know what is inside them.
        ----
        When using tool, use the reasoning part as a planning step, to describe the steps necessary to accomplish the task. 
        You can perform several tool cals in one round, and can choose to continue reasoning and answering after the tools have ben executed.
        After calling the tools, you can use the self retriggering mechanism. In case your round needs the tool outoput, or the the action you were performing has more than one step, you can invoke the continue_round tool.
        the continue_round tool should be the last tool called inside 'tool_calls' after the tools that performed the actions you wwanted, and will retrigger the session exactly where you left it before the tool call.
            **`retrigger: -1`** → Do not continue, end the current session (when done with a task)
            **`retrigger: 0/1/2`** → Continue the session to see tool outputs and reason about them when needed
        
    """

    memory = [
        {"role": "system", "content": system_prompt},
    ]
    while True:

        userPrompt = input(">>>")
        memory.append({"role": "user", "content": userPrompt})

        logAssistentAnswer = run_agent_streaming(memory)

        if(logAssistentAnswer):
            memory.extend(logAssistentAnswer)

        cont = Tools().shouldContinue()

        print(f"should continue: {cont}")

        while(cont):

        # if cont:

            memory.append({"role": "user", "content": Tools().shouldThink()})

            print("-------------------------------")
            print(memory)
            print("*******************************")

            print("--- SELF RETRIGGERED ---")
            logAssistentAnswer = run_agent_streaming(memory)

            if(logAssistentAnswer):
                memory.extend(logAssistentAnswer)

            cont = Tools().shouldContinue()

        