from langchain_ollama import OllamaEmbedings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import pandas as pd 

df = pd.read_csv("test.csv")

embedings = OllamaEmbedings(model="qwen3.5:9b")

db_location = "./chroma_langchain_test_db"
add_documents = not os.path.exists(db_location)
if add_documents:
    documents = []
    ids = []

    for i, row in df.iterrows:
        document = Document(
            page_content= row["what to qwery on"],                       # what to qwery on
            metadata= {"custom": row["data", "from": row["anywhere"]]},  # will not be qwerryed on
            id=str(i)
        )
    ids.append(i)
    documents.append(document)

vector_store = Chroma(
    colection_name= "name_of_the_collection",
    persistent_directory= db_location,         # if not specified, will go in RAM
    embedding_function= embedings
)

if add_documents:
    vector_store.add_documents(documents= documents, ids= ids)

retriever = vector_store.as_retriever(
    search_kwargss= {"k": 5}
)


