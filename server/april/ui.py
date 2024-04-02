import gradio as gr
import requests



choices_list = ["jedi", "faust", "rider"]
dropdown_input = gr.Dropdown(choices=choices_list, label="Select one topic")

def predict(message, _ , topic):
    response = requests.post("http://localhost:8080/query", json={"topic": topic, "query": message})
    return response.json()['message']


ui = gr.ChatInterface(
        predict,
        title="LLM Lint playground",
        description="This is a LLM playground for RAG(jedi, rider, faust)",
        theme="soft",
        textbox = gr.Textbox(placeholder="input", container=False, scale=7),
        additional_inputs=[dropdown_input],
        additional_inputs_accordion_name = "Choose a topic",
        retry_btn=None,
        undo_btn="Delete Previous",
        clear_btn="Clear",
)

ui.launch(share=True, height="auto", width="80%")
