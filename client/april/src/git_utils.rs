use anyhow::Result;
use std::process::Command;
use std::path::Path;


pub fn is_git_installed() -> Result<()> {
    Command::new("git")
        .arg("--version")
        .output()?;
    Ok(())
}

pub fn get_git_project_name() -> Result<String> {

    is_git_installed()?;
    
    let output = Command::new("git")
        .arg("rev-parse")
        .arg("--show-toplevel")
        .output()?;

    let output_str = String::from_utf8(output.stdout).unwrap();
    let project_name = Path::new(&output_str.trim()).file_name().unwrap().to_str().unwrap().to_string();

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
}