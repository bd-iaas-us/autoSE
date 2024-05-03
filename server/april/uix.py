import streamlit as st
import os
import json
from index import openai_template, QueryLint, templates
import threading
import time
import queue


os.environ["STREAMLIT_STATS_ENABLE"] = "false"


prompt = openai_template

# Streamlit page config
st.set_page_config(page_title="🦁lint playground(no RAG)", page_icon=":memo:")


# Use session state to store the text and file path
if 'text' not in st.session_state:
    st.session_state.text = "Initial text"
if 'file_path' not in st.session_state:
    st.session_state.file_path = ""

# Function to ensure directory exists
def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

# Upload file section
uploaded_file = st.file_uploader("Upload your file", type=None)
if uploaded_file is not None:
    file_path = os.path.join("uploaded_files", uploaded_file.name)
    ensure_dir(file_path)  # Ensure the directory exists
    # Save the uploaded file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state.file_path = file_path
    st.success("File uploaded successfully!")


# Input text box for new text
new_text = st.text_area("Input Text", value = prompt, height=500, help="KEEP the context prompt, DO NOT delete!!")


placeholder = st.empty()


def worker(file_content, queue):
    result = QueryLint("openai").query_lint("XXX", file_content)
    #debug
    # time.sleep(1)
    # result = "asdfasdfasdf,asdfas{}"
    queue.put(result)


def update_progress(progress):
    with placeholder.container():
        if progress == 100 or progress == 0:
            st.write("done")
        else:
            st.write("openai is working so hard...")
        st.progress(progress)


# Submit button to display the saved content
if st.button("LINT THIS FILE"):
    if st.session_state.file_path:
        # Reading the content from the file to show it
        with open(st.session_state.file_path, 'r') as file:
            file_content = file.read()

        #hacky: replace template. we only support openai version right now.
        templates["openai"] = new_text

        update_progress(0)
        # with placeholder.container():
        #     st.write("openai is working so hard...")
        #     st.progress(0)
        
        #start progress bar
        result_queue = queue.Queue()
        thread = threading.Thread(target=worker, args=(file_content, result_queue))
        thread.start()

        progress = 0
        while thread.is_alive():
            time.sleep(0.1)
            #fake progress never beyond 90
            progress = min(progress+1, 90)
            update_progress(progress)   
        thread.join()

        result = result_queue.get()
        update_progress(100)
        placeholder.empty()
        try:     
            decoded_result = json.loads(result)
        except Exception as e:
            st.error(f"{e}: {result}")
        else:
            st.json(decoded_result)
 
    else:
        st.error("Please upload a file before submitting.")


