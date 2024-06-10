import pandas as pd
import streamlit as st
import metrics
import argparse


has_parse_se_logs = False
try:
    import parse_se_logs
    has_parse_se_logs = True
except:
    import metrics

def main(traj_dir :str, lint_file: str):
    st.title("Log Visualization")

    if has_parse_se_logs:
        lint_points = parse_se_logs.parse_lint_log(lint_file)
        traj_points = parse_se_logs.parse_traj_log(traj_dir)
        df_traj = pd.DataFrame(traj_points)
        df_lint = pd.DataFrame(lint_points)
    else:
        traj_points = metrics.parse_swe_traj(traj_dir)
        df_traj = pd.DataFrame([tp.model_dump() for tp in traj_points])
        lint_points = metrics.parse_lint(lint_file)
        df_lint = pd.DataFrame([{"time":lp.time, "dur": lp.dur} for lp in lint_points])



    st.write(f'### total dev requests {len(traj_points)}')
    st.write("### Open API Calls Over Time")
    st.bar_chart(df_traj[['time', 'api_calls']], x="time")

    st.write("### Open API tokens send/received Over Time")
    st.bar_chart(df_traj[['time', 'tokens_sent', 'tokens_received']], x="time")


    #only time.
    st.write("### when lint is invoked")
    st.scatter_chart(df_lint, x='time')

if __name__ == "__main__":
    """
    example: streamlit run ui.py lint.log .
    """
    parser = argparse.ArgumentParser(description="Parse log files")
    parser.add_argument('lint_log_file', type=str, help='filename of log file')
    parser.add_argument("traj_dir", type=str, help="diretory of traj")
    args = parser.parse_args()

    main(args.traj_dir, args.lint_log_file)