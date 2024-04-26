use anyhow::{anyhow, Result};
use april::llm_client;
use april::utils::git;
use april::utils::spinner;
use clap::{Parser, Subcommand};
use log::{debug, warn};
use minijinja::{context, Environment};
use serde::Deserialize;
use std::any;
use std::fs::File;
use std::fs::OpenOptions;
use std::io::Read;
use std::sync::mpsc;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// API URL to connect to
    #[arg(
        long,
        global = true,
        default_value = "http://localhost:8000",
        env = "API_URL"
    )]
    api_url: String,

    #[arg(long, global = true, default_value = "unknown", env = "API_KEY")]
    api_key: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Configure the application
    Lint {
        /// Configuration file to use
        #[clap(index = 1)]
        file_name: Option<String>,
        #[arg(long)]
        diff_mode: bool,
    },

    /// Another subcommand, for example to run some operations
    Dev {
        /// Detail level
        #[clap(index = 1)]
        description: String,
    },
}

// #[derive(Parser, Debug)]
// #[command(author, version, about)]
// struct Args {
//     #[clap(index = 1)]
//     file_name: Option<String>,
//     //3 backends, openai, claude, custom
//     #[arg(long, default_value = "openai", env = "BACKEND")]
//     backend: Option<String>,
//     #[arg(long, default_value = "http://localhost:8000", env = "API_URL")]
//     api_url: String,
//     #[arg(long, default_value = "unknown", env = "API_KEY")]
//     api_key: String
// }

/*
static QUERY_CODE_TEMPLATE :&str = r#"
Rules:
User wants a bug free application, can you tell me is there any potential risks or bugs?
code is below:
```
{{code}}
```
"#;

static QUERY_CODE_DIFF_TEMPLATE :&str = r#"
Rules:
User wants a bug free application, can you tell me is there any potential risks or bugs in following code diff?
code is below:
```
{{code}}
```
"#;
*/

//TODO: read local rules

#[derive(Debug, Deserialize)]
struct AILintResult {
    message: String,
    refs: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct AILintSupportedTopics {
    topics: Vec<String>,
}

//lint
fn lint(file_name: Option<String>, diff_mode: bool, api_url: &str, api_key: &str) -> Result<()> {
    let mut project_name = String::new();
    let mut code = String::new();
    if diff_mode {
        project_name = match git::get_git_project_name() {
            Ok(p) => p,
            Err(e) => {
                println!("diff mode is only supported for git project");
                return Err(e);
            }
        };
        //if file_name is provided in diff_mode, we only lint the file itself.
        //if no file name is provided, we could lint the whole project.
        code = git::get_git_diff(&file_name)?;
    } else
    /* single file mode */
    {
        match git::get_git_project_name() {
            Ok(p) => project_name = p,
            Err(e) => {
                //if there is no git project.
            }
        };
        if file_name.is_none() {
            return Err(anyhow!("you should provide a file name to lint"));
        }
        let mut file = File::open(file_name.unwrap())?;
        file.read_to_string(&mut code)?;
    }

    let (tx, rx) = mpsc::channel();
    spinner::run_spinner("Generating", rx);

    match llm_client::query(api_url, api_key, &project_name, &code) {
        Ok(msg) => {
            match serde_json::from_str::<AILintResult>(&msg) {
                Ok(result) => {
                    //close the fancy spinner.
                    let _ = tx.send(());

                    println!("{}", result.message);
                    for i in 0..result.refs.len() {
                        println!("considering {}", result.refs[i]);
                    }
                }
                Err(_) => {
                    let _ = tx.send(());
                    println!("ERROR: {}", msg);
                }
            }
        }
        Err(e) => {
            println!("request service error: {}", e);
        }
    }

    Ok(())
}

//TODO:
fn dev(description: &str) -> Result<()> {
    println!("not implemented");
    Ok(())
}

fn main() -> Result<()> {
    env_logger::init();
    let cli = Cli::parse();

    match cli.command {
        Commands::Dev { description } => dev(&description),
        Commands::Lint {
            file_name,
            diff_mode,
        } => lint(file_name, diff_mode, &cli.api_url, &cli.api_key),
    }
}
