// build.rs
use std::process::Command;

fn main() {
    let output = Command::new("git")
        .args(&["describe", "--tags", "--dirty"])
        .output()
        .expect("Failed to execute git command");

    let git_version = String::from_utf8(output.stdout).expect("Invalid UTF-8 in git output");
    let git_version = git_version.trim();

    println!("cargo:rustc-env=GIT_VERSION={}", git_version);
}
