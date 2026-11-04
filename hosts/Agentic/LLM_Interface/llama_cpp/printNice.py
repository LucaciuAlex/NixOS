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
            print(f"{' '*indentation}{key}: [...]")

    if indentation==0:
        print(f"{'-'*70}")
    
def printMetadata(jsonResponse, indentation=0):
    if indentation==0:
        print("model response:")

    for key in jsonResponse.keys():
        if isinstance(jsonResponse[key], dict):
            print(f"{' '*indentation}{key} -> ")
            printMetadata(jsonResponse[key], indentation + len(key) + 4)
        else:
            print(f"{' '*indentation}{key}:{jsonResponse[key] if len(jsonResponse[key]) > 40 else "[...]" }")

    if indentation==0:        
        print()