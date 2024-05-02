use anyhow::{anyhow, Result};
use std::path::Path;
use std::process::Command;

pub fn is_git_installed() -> Result<()> {
    Command::new("git").arg("--version").output()?;
    Ok(())
}

/*
if file is None, I will get the whole diff or, on one file's diff.
*/
pub fn get_git_diff(file: &Option<String>) -> Result<String> {
    is_git_installed()?;

    let mut command = Command::new("git");
    command.arg("diff");
    command.arg("HEAD");

    if let Some(file) = file {
        command.arg(file);
    }

    Ok(String::from_utf8(command.output()?.stdout)?)
}

pub fn get_git_project_name() -> Result<String> {
    is_git_installed()?;

    let output = Command::new("git")
        .arg("rev-parse")
        .arg("--show-toplevel")
        .output()?;

    let output_str = String::from_utf8(output.stdout)?;
    let project_name = Path::new(&output_str.trim())
        .file_name()
        .ok_or(anyhow!("empty output"))?
        .to_str()
        .ok_or(anyhow!("convert from osstr failed"))?
        .to_string();

    Ok(project_name)
}

//test cases
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_git_installed() {
        assert!(is_git_installed().is_ok());
    }

    #[test]
    fn test_get_git_project_name() {
        assert!(get_git_project_name().is_ok());
    }

    #[test]
    fn test_get_git_diff() {
        assert!(get_git_diff(&Some("git_utils.rs".to_string())).is_ok());
    }
}
