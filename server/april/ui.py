import pandas as pd
import streamlit as st
import metrics
import argparse


def main(traj_dir :str, lint_file: str):
    st.title("Log Visualization")

    traj_points = metrics.parse_swe_traj(traj_dir)
    lint_points = metrics.parse_lint(lint_file)


    df = pd.DataFrame([{
        'time': tp.time,
        'api_calls': tp.api_calls,
        'tokens_sent': tp.tokens_sent,
        'tokens_received': tp.tokens_received,
        'total_cost': tp.total_cost,
        'instance_cost': tp.instance_cost,
        'exit_status': tp.exit_status
    } for tp in traj_points])

    st.write(f'### total dev requests {len(traj_points)}')
    st.write("### Open API Calls Over Time")
    st.bar_chart(df[['time', 'api_calls']], x="time")

    st.write("### Open API tokens send/received Over Time")
    st.bar_chart(df[['time', 'tokens_sent', 'tokens_received']], x="time")


    #only time.
    st.write("### when lint is invoked")
    df = pd.DataFrame([{"time":lp.time, "dur": lp.dur} for lp in lint_points])
    st.scatter_chart(df, x='time')

if __name__ == "__main__":
    """
    example: streamlit run ui.py lint.log .
    """
    parser = argparse.ArgumentParser(description="Parse log files")
    parser.add_argument('lint_log_file', type=str, help='filename of log file')
    parser.add_argument("traj_dir", type=str, help="diretory of traj")
    args = parser.parse_args()

    main(args.traj_dir, args.lint_log_file)