#
#start service: streamlit run uix.py --browser.gatherUsageStats false --server.port 8080 --server.address  0.0.0.0
import streamlit as st
import os
import json
from index import openai_template, QueryLint, templates
import threading
import time
import queue
import sys
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from streamlit_authenticator.utilities.exceptions import (CredentialsError,
                                                          ForgotError,
                                                          LoginError,
                                                          RegisterError,
                                                          ResetError,
                                                          UpdateError) 





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



def worker(file_content, queue):
    try:
        result = QueryLint("openai").query_lint("XXX", file_content)
        #debug
        # time.sleep(1)
        # result = "asdfasdfasdf,asdfas{}"
    except Exception as e:
        queue.put(e)
    else:
        queue.put(result)



def main_layout():
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








# Streamlit page config
st.set_page_config(page_title="🦁lint playground(no RAG)", page_icon=":memo:")

#disable usage collection
os.environ["STREAMLIT_STATS_ENABLE"] = "false"
prompt = openai_template


try:
    # check os env
    if "OPENAI_API_KEY" not in  os.environ:
        raise KeyError
    with open('./config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
    # Creating the authenticator object
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    authenticator.login()
except KeyError:
    st.error("env OPENAI_API_KEY not set")
    sys.exit(1)
except Exception as e:
    st.error(f"exception: {e}")
    sys.exit(1)

if st.session_state["authentication_status"]:
    authenticator.logout()
    st.write(f'Welcome *{st.session_state["name"]}*')
    main_layout()

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
