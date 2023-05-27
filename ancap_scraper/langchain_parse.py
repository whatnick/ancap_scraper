import pandas as pd
import glob
from dotenv import load_dotenv
from langchain.agents import create_pandas_dataframe_agent
from langchain.llms import OpenAI

load_dotenv()

all_reports = glob.glob("safety_data_excel/*.xlsx")
all_df = []
for report in all_reports:
    all_df.append(pd.read_excel(report))

agent = create_pandas_dataframe_agent(OpenAI(temperature=0), all_df, verbose=True)
agent.run("which features are available in both au and nz for all?")

from langchain.document_loaders import PyPDFDirectoryLoader
from langchain.embeddings import OpenAIEmbeddings 
from langchain.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

loader = PyPDFDirectoryLoader("safety_data/")
docs = loader.load()

embeddings = OpenAIEmbeddings()
vectordb = Chroma.from_documents(docs, embedding=embeddings, 
                                 persist_directory=".")
vectordb.persist()
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
pdf_qa = ConversationalRetrievalChain.from_llm(OpenAI(temperature=0.8) , vectordb.as_retriever(), memory=memory)

query = "which vehicles were tested in 2017?"
result = pdf_qa({"question": query})
print("Answer:")
print(result["answer"])


