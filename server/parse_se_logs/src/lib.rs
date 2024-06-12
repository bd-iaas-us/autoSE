use anyhow::{anyhow, Result};
use chrono::{Datelike, Local, NaiveDateTime, Timelike};
use pyo3::prelude::*;
use pyo3::types::{PyDateTime, PyDict, PyList};
use pyo3::wrap_pyfunction;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::Path;
use walkdir::WalkDir;

#[derive(Debug)]
struct TrajPoint {
    api_calls: i32,
    tokens_sent: i32,
    tokens_received: i32,
    total_cost: f64,
    instance_cost: f64,
    exit_status: String,
    time: NaiveDateTime,
}

#[derive(Debug)]
struct LintPoint {
    time: NaiveDateTime,
    dur: f64,
}

fn _parse_swe_traj<P: AsRef<Path>>(directory: P) -> Result<Vec<(TrajPoint)>> {
    let mut ret = Vec::new();
    for entry in WalkDir::new(directory).into_iter() {
        let entry = entry?;
        let path = entry.path();
        if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("traj") {
            let metadata = fs::metadata(&path)?;
            let creation_time = metadata.created()?;
            use chrono::DateTime;
            let creation_datetime: DateTime<Local> = creation_time.into();
            let file_content = fs::read_to_string(path)?;
            let data: serde_json::Value = serde_json::from_str(&file_content)?;
            ret.push(TrajPoint {
                api_calls: data["info"]["model_stats"]["api_calls"]
                    .as_i64()
                    .ok_or(anyhow!("Missing api_calls"))? as i32,
                tokens_sent: data["info"]["model_stats"]["tokens_sent"]
                    .as_i64()
                    .ok_or(anyhow!("Missing tokens_sent"))? as i32,
                tokens_received: data["info"]["model_stats"]["tokens_received"]
                    .as_i64()
                    .ok_or(anyhow!("Missing tokens_received"))?
                    as i32,
                total_cost: data["info"]["model_stats"]["total_cost"]
                    .as_f64()
                    .ok_or(anyhow!("Missing total_cost"))?,
                instance_cost: data["info"]["model_stats"]["instance_cost"]
                    .as_f64()
                    .ok_or(anyhow!("Missing instance_cost"))?,
                exit_status: data["info"]["exit_status"]
                    .as_str()
                    .unwrap_or("unknown")
                    .to_string(),
                time: creation_datetime.naive_local(),
            });
        }
    }
    Ok(ret)
}

fn _parse_log_line(line: &str) -> Result<LintPoint> {
    let parts: Vec<&str> = line.split_whitespace().collect();
    let datetime_part = format!("{} {}", parts[1], parts[2]);
    let duration_str = parts
        .iter()
        .find(|&&part| part.starts_with("dur:"))
        .unwrap()
        .split(':')
        .nth(1)
        .unwrap();
    let time_obj = NaiveDateTime::parse_from_str(&datetime_part, "%Y-%m-%d %H:%M:%S")?;
    let lint_point = LintPoint {
        time: time_obj,
        dur: duration_str.parse::<f64>()?,
    };
    Ok(lint_point)
}

fn _parse_lint<P: AsRef<Path>>(log_path: P) -> Result<Vec<LintPoint>> {
    let file = fs::File::open(log_path)?;
    let reader = BufReader::new(file);
    let mut ret = Vec::new();
    for line in reader.lines() {
        let line = line?;
        if line.contains("lint code len") {
            let lint_point = _parse_log_line(&line)?;
            ret.push(lint_point);
        }
    }
    Ok(ret)
}

fn naive_datetime_to_pydatetime(py: Python, naive_dt: &NaiveDateTime) -> PyResult<PyObject> {
    let py_datetime = PyDateTime::new_bound(
        py,
        naive_dt.year(),
        naive_dt.month() as u8,
        naive_dt.day() as u8,
        naive_dt.hour() as u8,
        naive_dt.minute() as u8,
        naive_dt.second() as u8,
        naive_dt.timestamp_subsec_nanos() / 1000,    // Convert nanoseconds to microseconds
        None, // No timezone for naive datetime
    )?;
    Ok(py_datetime.into())
}

#[pyfunction]
fn parse_traj_log(py: Python, log_dir: String) -> PyResult<PyObject> {
    let traj_points = _parse_swe_traj(log_dir).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to parse traj log: {}", e))
    })?;

    let py_list = PyList::empty_bound(py);
    for point in traj_points {
        let py_dict = PyDict::new_bound(py);
        let time_py = naive_datetime_to_pydatetime(py, &point.time)?;
        py_dict.set_item("time", time_py)?;
        py_dict.set_item("api_calls", point.api_calls)?;
        py_dict.set_item("tokens_sent", point.tokens_sent)?;
        py_dict.set_item("tokens_received", point.tokens_received)?;
        py_dict.set_item("total_cost", point.total_cost)?;
        py_dict.set_item("instance_cost", point.instance_cost)?;
        py_dict.set_item("exit_status", point.exit_status)?;
        py_list.append(py_dict)?;
    }
    Ok(py_list.to_object(py))
}

#[pyfunction]
fn parse_lint_log(py: Python, log_path: String) -> PyResult<PyObject> {
    let lint_points = _parse_lint(log_path).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to parse lint log: {}", e))
    })?;

    let py_list = PyList::empty_bound(py);
    for point in lint_points {
        let py_dict = PyDict::new_bound(py);
        let time_py = naive_datetime_to_pydatetime(py, &point.time)?;
        py_dict.set_item("time", time_py)?;
        py_dict.set_item("dur", point.dur)?;
        py_list.append(py_dict)?;
    }
    Ok(py_list.to_object(py))
}

/// A Python module implemented in Rust. The name of this function must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pymodule]
fn parse_se_logs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_lint_log, m)?)?;
    m.add_function(wrap_pyfunction!(parse_traj_log, m)?)?;
    Ok(())
}

// correctly parses log lines containing "lint code len"
#[test]
fn correctly_parses_log_lines_with_lint_code_len() {
    use std::fs::File;
    use std::io::Write;
    use tempfile::tempdir;

    let dir = tempdir().unwrap();
    let file_path = dir.path().join("test.log");
    let mut file = File::create(&file_path).unwrap();
    writeln!(file, "INFO 2023-10-01 12:00:00 lint code len dur:123").unwrap();

    let result = _parse_lint(&file_path);
    match result {
        Ok(lint_points) => {
            assert_eq!(lint_points.len(), 1);
            assert_eq!(lint_points[0].dur, 123.0);
        }
        Err(e) => {
            panic!("Error: {:?}", e);
        }
    }
}

#[test]
fn correctly_parses_traj_files() {
    use std::fs::File;
    use std::io::Write;
    use tempfile::tempdir;

    let dir = tempdir().unwrap();
    let file_path = dir.path().join("test.traj");
    let mut file = File::create(&file_path).unwrap();
    writeln!(file, r#"{{"info": {{"model_stats": {{"api_calls": 1, "tokens_sent": 2, "tokens_received": 3, "total_cost": 4.0, "instance_cost": 5.0}}, "exit_status": "success"}}}}"#).unwrap();

    let result = _parse_swe_traj(&dir.path());
    match result {
        Ok(traj_points) => {
            assert_eq!(traj_points.len(), 1);
            assert_eq!(traj_points[0].api_calls, 1);
            assert_eq!(traj_points[0].tokens_sent, 2);
            assert_eq!(traj_points[0].tokens_received, 3);
            assert_eq!(traj_points[0].total_cost, 4.0);
            assert_eq!(traj_points[0].instance_cost, 5.0);
            assert_eq!(traj_points[0].exit_status, "success");
        }
        Err(e) => {
            panic!("Error: {:?}", e);
        }
    }
}
