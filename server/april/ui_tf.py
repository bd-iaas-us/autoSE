from queue import Queue
from threading import Thread

import streamlit as st
from tf import handle_tf

with open("intro.md", "r") as f:
    intro_content = f.read()


def worker(input, queue):
    try:
        result = handle_tf(input)
    except Exception as e:
        queue.put(e)
    else:
        queue.put(result)


def main_layout():
    st.title("volcengine terraform generator")

    st.markdown(intro_content)

    input_value = st.text_area(r"$\textsf{\large Enter your question}$",
                               "",
                               height=150)

    if st.button("Run"):
        if not input_value.strip():
            st.warning("Please enter your question.")
        else:
            result_queue = Queue()

            # Start the worker thread
            thread = Thread(target=worker, args=(input_value, result_queue))
            thread.start()

            with st.spinner('Processing...'):
                thread.join()
                st.success('Done!')

            # Get the result from the queue
            result = result_queue.get()
            st.text_area(r"$\textsf{\large Result}$", result, height=600)


if __name__ == "__main__":
    main_layout()
