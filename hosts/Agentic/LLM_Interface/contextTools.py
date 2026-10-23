import os
import json
import requests
from pathlib import Path
from transformers import AutoTokenizer

class Formatting:
    Bold = "\x1b[1m"
    Dim = "\x1b[2m"    
    Reset = "\x1b[0m"


OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
ALLOWED_ROOT = Path.cwd()
TEMPERATURE = 0.7

# MODEL_NAME = "llama3.1:8b"  
# MODEL_NAME = "qwen3.5:9B"
# MODEL_NAME = "qwen2.5-coder:7b"
# MODEL_NAME = "customQwen3.5"
# MODEL_NAME = "customQwen3.5_RT"
# MODEL_NAME = "customQwen2.5"
MODEL_NAME = "granite4.1:8b"



# import re

# ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


# def print(string="", end="", flush=False):
#   clean_string = ANSI_ESCAPE.sub("", str(string))
#   with open("session.log", "a") as f:
#     f.write(clean_string + "\n" if not flush else "")


def printNiceList(lst, indentation=0):
    for element in lst:
        if isinstance(element, dict):
            printNiceJSON(element, indentation)
        else:
            print(f"{' '*indentation}{element}")


def printNiceJSON(jsonResponse, indentation=0):
    for key in jsonResponse.keys():
        if isinstance(jsonResponse[key], dict):
            print(f"{' '*indentation}{key} -> ")
            printNiceJSON(jsonResponse[key], indentation + len(key) + 4)
        elif isinstance(jsonResponse[key], list):
            print(f"{' '*indentation}{key} -> ")
            printNiceList(jsonResponse[key], indentation + len(key) + 4)
        else:
            print(f"{' '*indentation}{key} : {jsonResponse[key] if jsonResponse[key] else "-NULL-"}")


def revealStructure(jsonResponse, indentation=0):
    if indentation==0:
        print("json response structure:")

    for key in jsonResponse.keys():
        if isinstance(jsonResponse[key], dict):
            print(f"{' '*indentation}{key} -> ")
            revealStructure(jsonResponse[key], indentation + len(key) + 4)
        else:
            print(f"{' '*indentation}{key}")

    if indentation==0:
        print("----------------------------")
    
def printMetadata(jsonResponse, indentation=0):
    if indentation==0:
        print("model response:")

    for key in jsonResponse.keys():
        if isinstance(jsonResponse[key], dict):
            print(f"{' '*indentation}{key} -> ")
            printMetadata(jsonResponse[key], indentation + len(key) + 4)
        else:
            if key != "message":
                print(f"{' '*indentation}{key}:{jsonResponse[key] if key != "message" else "[...]" }")

    if indentation==0:        
        print()

def calculate_kv_cache_vram(
    input_tokens: int, 
    output_tokens: int, 
    kv_cache_type: str = "f16",
    layers: int = 32,          # Adjust based on your specific Qwen3.5 size
    kv_heads: int = 8,          # Adjust based on your specific Qwen3.5 size
    head_dim: int = 128
) -> float:
    """
    Calculates estimated VRAM usage for the KV cache in Megabytes (MB).
    """
    # 1. Map the bytes per element based on OLLAMA_KV_CACHE_TYPE
    if kv_cache_type == "f16":
        bytes_per_element = 2.0
    elif kv_cache_type == "q8":
        bytes_per_element = 1.0625  # Includes quantization scale block factor
    elif kv_cache_type == "q4":
        bytes_per_element = 0.5625  # Includes quantization scale block factor
    else:
        raise ValueError("Unsupported KV cache type. Use 'f16', 'q8', or 'q4'.")

    # 2. Compute total tokens processed in this sequence
    total_tokens = input_tokens + output_tokens

    # 3. Apply the standard GQA KV cache formula
    # (2 * Layers * KV_Heads * Head_Dim) * total_tokens * bytes_per_element
    total_bytes = 2 * layers * kv_heads * head_dim * total_tokens * bytes_per_element

    # Convert bytes to Megabytes (MB)
    vram_mb = total_bytes / (1024 * 1024)
    return round(vram_mb, 2)

def calculateStatistics(payload, response):
    fullContext = ""
    for line in payload["messages"]:
        fullContext += line["content"] + " "
    contextWordCount = len(fullContext.split())
    contextLoadTime = round(response["prompt_eval_duration"] / 10**9, 4) # nanoseconds to seconds with 4 decimal points
    contextTokenSize = response["prompt_eval_count"]
    contextWordPerToken = contextTokenSize / contextWordCount if contextWordCount != 0 else -1

    answer = response["message"]["content"]
    responseWordCount = len(answer.split())
    responseTime = round(response["eval_duration"] / 10**9, 4) # nanoseconds to seconds with 4 decimal points
    responseTokenSize = response["eval_count"]
    responseWordPerToken = responseTokenSize / responseWordCount if responseWordCount != 0 else -1
    tokensPerSecond = responseTokenSize / responseTime

    if("thinking" in response["message"].keys()):
        thinking = response["message"]["thinking"]
        thinkingWordCount = len(thinking.split())
        totalGeneratedTokens = responseTokenSize
        thinkingToResponseRatio = thinkingWordCount / (responseWordCount + thinkingWordCount)
        responseToThinkingRatio = responseWordCount / (responseWordCount + thinkingWordCount)
        thinkingTokenSize = responseTokenSize * thinkingToResponseRatio
        responseTokenSize = responseTokenSize * responseToThinkingRatio

    print("-----------------------------stats---------------------------")
    print(f" context load time: {contextLoadTime}s               context tocken size: {contextTokenSize}")
    print(f" context word count: {contextWordCount}                    word per token: {contextWordPerToken}")

    if("thinking" in response["message"].keys()):
        print()
        print(f" thinking word count {thinkingWordCount}              thinking estimated token size: {thinkingTokenSize}")
        print(f"                                                total generated tokens: {totalGeneratedTokens}")



    print(f" response generation time: {responseTime}s               response tocken size: {responseTokenSize}")
    print(f" response word count: {responseWordCount}                      tokens per word: {responseWordPerToken}")
    print(f"average tokens per second: {tokensPerSecond}")
    print(f"-------------- RAM used: {calculate_kv_cache_vram(contextTokenSize, totalGeneratedTokens, kv_cache_type="q4")}")


def run_agent(prompt: str):
    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": { "temperature":TEMPERATURE }
    }

    print("payload sent to the API")
    printNiceJSON(payload)
    print()

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=60)
        if not response.ok:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return

        result = response.json()

        # print(f"raw:\n{result}\n\n")

        # reveal the structure of the message for development purposes
        # revealStructure(result)

        printMetadata(result)

        message = result.get("message", {})
        print(message["content"])
        print()

        calculateStatistics(payload, result)

    except Exception as e:
        print(e)


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
    
def run_agent_streaming(prompt: str):
    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,  # <-- Enables streaming responses
        "options": { 
            "temperature":TEMPERATURE
            }
    }

    try:
        # stream=True keeps the connection open to read chunks incrementally
        response = requests.post(OLLAMA_CHAT_URL, json=payload, stream=True, timeout=60)
        if not response.ok:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return

        accumulated_tool_calls = []

        doneThinking = False
        fullThinking = ""
        fullContent = ""

        # Iterate line-by-line through Ollama's streaming NDJSON output
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                message = chunk.get("message", {})

                # Stream the thinking process
                thinkingChunk = streamThinking(message)
                isThinking = thinkingChunk != False
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


                # try:
                #     printMetadata(chunk)
                # except Exception as e:
                #     pass
        else:
            chunk["message"]["thinking"] = fullThinking
            chunk["message"]["content"] = fullContent
            # printMetadata(chunk)
            calculateStatistics(payload, chunk)


        print() # Print newline after text stream finishes

    except Exception as e:
        print(f"\n⚠️ Error during streaming: {e}")


def testToolsTheory(prompt: str):
    messages = [
        {"role": "system", "content": "you are an AI model with access to google search. Users can ask you a question, and you can search the web. You can use the provided tool to search the web. You should suspend your activity during the search and resume it once you receive the results. You should specify the fact that you are waiting by returning done:False and done_reason:Waiting_for_tool"},
        {"role": "user", "content": prompt}
    ]

    tools=[
        {
            "type": "function",
            "function": {
                "name": "searchTheWeb",
                "description": "use a web search engine and receive the top [1-5] most relevant links and the contents of respective sites.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_string": {
                            "type": "string",
                            "description": "Target file path."
                        },
                        "number_of_relevant_pages": {
                            "type": "integer",
                            "description": "The number of links from top results of the search, that you consider necessary to form a more relevant answer. This number can range between 1 and 5. Only use 4 or 5 if you consider the multiple sources will provie a much better overview. By default this will be 1",
                            "default": "1"
                        }
                    },
                    "required": [
                        "search_string",
                    ]
                }
            }
        }
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "tools": tools,
        "options": { "temperature":TEMPERATURE }
    }

    print("payload sent to the API")
    printNiceJSON(payload)
    print()

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=60)
        if not response.ok:
            print(f"Ollama Error: {response.status_code} - {response.text}")
            return

        result = response.json()

        # print(f"raw:\n{result}\n\n")

        # reveal the structure of the message for development purposes
        # revealStructure(result)

        printMetadata(result)

        message = result.get("message", {})
        print(message["content"])
        print()

        calculateStatistics(payload, result)

    except Exception as e:
        print(e)
    
    


def get_token_count(text: str, model_name: str = "Qwen/Qwen3.5-27B") -> int:
    """
    Primește un text și returnează strict numărul de tokeni în care este encodat.
    """
    # Încarcă tokenizer-ul (se descarcă o singură dată, apoi este preluat din cache)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Encodează textul și extrage lista de ID-uri de tokeni
    tokens = tokenizer.encode(text)
    
    # Returnează lungimea listei de tokeni
    return len(tokens)


def main():
  with open("session.log", "r") as f:
    context = f.read()

    prompt =  context + \
        "answer shortly with minimal thinking. This is a new test, and I need a short answer, so I will ask you a short quesion. What i model is running this session?"


    #prompt="this is a test"

    # run_agent(prompt)
    run_agent_streaming(prompt)  # <- 
    # testToolsTheory("find what is the weather going to be tomorrow in Cluj Napoca")


main()


