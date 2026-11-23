from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import vectors

model = OllamaLLM(model="qwen3.5:9b")


template = """
user prompt: {prompt}
"""

vectorData = retriever.invoke("blablabla")

prompt = ChatPromptTemplate.from_template(template)

chain = prompt | model 

print(chain.invoke({"this is a test"}))