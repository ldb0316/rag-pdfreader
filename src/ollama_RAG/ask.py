import os

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
import streamlit as st

from ingest import indexing
import os
import ollama

embeddings = OllamaEmbeddings(model="phi4:latest")

# file을 입력받아 처리 후 chain 생성하여 반환
@st.cache_resource
def get_db(uploaded_file):
    indexing(uploaded_file)
    return FAISS.load_local(uploaded_file.name, embeddings=embeddings, allow_dangerous_deserialization=True)

def create_generator(text, db):
    content = "당신은 친절한 어시스턴트입니다. 주어진 데이터를 보고 사용자에 친절하게 대답하세요.\n" 
    content += "*" * 50
    docs = db.similarity_search(text[-1]["content"])
    for doc in docs:
        content += doc.page_content + "\n"
        content += "*" * 50
        
    messages = [
        {
          "role": "system",
          "content": content
        },
        text[-1]
    ]

    gen = ollama.chat(
      model="phi4:latest",
      messages=messages,
      stream=True
    )
    return gen


def main():
    st.title("PDF 파일 내용 물어보기")
    st.chat_input(placeholder="대화를 입력해주세요.", key="chat_input")
    uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf", key="attatch_file")

    db = None

    if uploaded_file is not None:
        db = get_db(uploaded_file)
        
    if "messages" not in st.session_state:
        st.session_state.messages = []        

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.session_state["chat_input"]:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content":user_input})
        if db is not None:
            gen = create_generator(st.session_state.messages, db)
            # print(gen)
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""        
                try:
                    while True:
                        response = next(gen)
                        content = response.message.content
                        if content is not None:
                            full_response += content
                            message_placeholder.markdown(full_response + "▌")
                        else:
                            break
                except StopIteration:
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content":full_response})
        else:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("PDF를 먼저 업로드하세요.")
    return 

if __name__ == "__main__":
    main()
