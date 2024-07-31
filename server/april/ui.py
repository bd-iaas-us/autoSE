import argparse

import metrics
import pandas as pd
import streamlit as st
from logger import init_logger
from rag import RagDocument
from streamlit_option_menu import option_menu

#lint.log record all lint messages.
logger = init_logger(__name__)

has_parse_se_logs = False
try:
    import parse_se_logs
    has_parse_se_logs = True
except Exception as _:
    import metrics


def display_dataframe(streamlist):
    df = pd.DataFrame(streamlist, columns=["Items"])
    print(df)


def rag():
    tab1, tab2 = st.tabs(["Upload files", "List files"])
    with tab1:
        st.markdown(
            "<span style='color: red'>only utf-8 text file could be accepted</span>",
            unsafe_allow_html=True)
        # Topic input
        topic = st.text_input("Enter the topic of the document")
        # Document name input
        document_name = st.text_input("Enter the name of the document")
        uploaded_file = st.file_uploader("Choose your files",
                                         accept_multiple_files=False)
        if uploaded_file and topic and document_name:
            doc = uploaded_file.getvalue().decode("utf-8")
            logger.info(doc)
            # lazy import
            try:
                rag = RagDocument()
                rag.register_doc(doc, topic, document_name)
                st.success(
                    f"Uploaded document '{document_name}' successfully!")
            except Exception as e:
                st.error(
                    f"Failed to upload files, please check the log for details {e}"
                )
        elif st.button("Upload"):
            st.error(
                "Please provide a topic, document name, and choose a file to upload."
            )

    with tab2:
        st.markdown(
            '<h4 style="color:black;">Here you can review the uploaded files, and each file could be split into multiple documents</h4>',
            unsafe_allow_html=True)
        try:
            rag = RagDocument()
            for record in rag.list_docs():
                st.markdown(
                    f'<h3 style="color:black;">Document {record.id}</h3>',
                    unsafe_allow_html=True)
                st.markdown(
                    f'<span style="color:dimgrey">Document Id: {record.payload["id"]}</span>',
                    unsafe_allow_html=True)
                st.markdown(
                    f'<span style="color:dimgrey">Document Name: {record.payload["meta"]["document_name"]}</span>',
                    unsafe_allow_html=True)
                st.markdown(
                    f'<span style="color:dimgrey">Topic: {record.payload["meta"]["topic"]}</span>',
                    unsafe_allow_html=True)
                col1, col2 = st.columns([0.2, 0.8])
                with col1:
                    # Add a preview button
                    if st.button("Preview", key=f"preview-{record.id}"):
                        st.markdown(f"```\
                        {record.payload['content'][:500]}\
                         ```")
                with col2:
                    # Add a delete button
                    if st.button("Delete", key=f"delete-{record.id}"):
                        try:
                            rag.delete_doc(
                                record.payload["meta"]["topic"],
                                record.payload["meta"]["document_name"])
                            st.success("Deleted the document successfully!")
                        except Exception as e:
                            st.error(
                                f"Failed to delete the document, please check the log for details {e}"
                            )

        except Exception as e:
            st.error(
                f"Failed to List files, please check the log for details {e}")


def metrics(traj_dir: str, lint_file: str):
    if has_parse_se_logs:
        lint_points = parse_se_logs.parse_lint_log(lint_file)
        traj_points = parse_se_logs.parse_traj_log(traj_dir)
        df_traj = pd.DataFrame(traj_points)
        df_lint = pd.DataFrame(lint_points)
    else:
        traj_points = metrics.parse_swe_traj(traj_dir)
        df_traj = pd.DataFrame([tp.model_dump() for tp in traj_points])
        lint_points = metrics.parse_lint(lint_file)
        df_lint = pd.DataFrame([{
            "time": lp.time,
            "dur": lp.dur
        } for lp in lint_points])

    st.write(f'### total dev requests {len(traj_points)}')
    st.write("### Open API Calls Over Time")
    st.bar_chart(df_traj[['time', 'api_calls']], x="time")

    st.write("### Open API tokens send/received Over Time")
    st.bar_chart(df_traj[['time', 'tokens_sent', 'tokens_received']], x="time")

    st.write("### Open API Calls status")
    st.bar_chart(df_traj[['time', 'exit_status']], x="time")

    #only time.
    st.write("### when lint is invoked")
    st.scatter_chart(df_lint, x='time')


#example: streamlit run ui.py lint.log .
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse log files")
    parser.add_argument('lint_log_file', type=str, help='filename of log file')
    parser.add_argument("traj_dir", type=str, help="diretory of traj")
    args = parser.parse_args()

    st.set_page_config(page_title="autose",
                       page_icon="🐼",
                       layout="wide",
                       initial_sidebar_state="expanded")
    st.sidebar.title("Navigation")
    metrics_title = "Metrics"
    rag_title = "RAG File management"
    with st.sidebar:
        app_mode = option_menu("Dashboard", [metrics_title, rag_title],
                               icons=['bar-chart-fill', 'cloud-upload'],
                               menu_icon="cast",
                               default_index=0,
                               orientation="vertical",
                               styles={
                                   "container": {
                                       "padding": "0!important",
                                       "background-color": "#fafafa"
                                   },
                                   "icon": {
                                       "color": "orange",
                                       "font-size": "25px"
                                   },
                                   "nav-link": {
                                       "font-size": "16px",
                                       "text-align": "left",
                                       "margin": "0px",
                                       "--hover-color": "#eee"
                                   },
                                   "nav-link-selected": {
                                       "background-color": "#02ab21"
                                   },
                               })
    #app_mode = st.sidebar.radio("Choose the view", ["Metrics", "Upload File"])
    if app_mode == metrics_title:
        metrics(args.traj_dir, args.lint_log_file)
    elif app_mode == rag_title:
        rag()
