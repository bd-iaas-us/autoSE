
use anyhow::{anyhow, Result};
use minijinja::{Environment, context};
use std::fs::File;
use std::io::{Read, Write};
use clap::Parser;
use april::llm_client;
use april::git_utils;
use log::{info, warn};
use serde_json::Value;
use serde::Deserialize;




#[derive(Parser, Debug)]
#[command(author, version, about)]
struct Args {
    #[arg(short, long)]
    file_name: String,
    //3 backends, openai, claude, custom
    #[arg(short, long)]
    backend: Option<String>,
    #[arg(short, long)]
    project: Option<String>,
    #[arg(short, long, default_value = "http://localhost:8000/query", env = "API_URL")]
    url: String,
    #[arg(short, long, default_value = "unknown", env = "API_KEY")]
    api_key: String
}

//TODO: find a better prompt:
static QUERY_TEMPLATE :&str = r#"
Rules:
User wants a bug free application, can you tell me is there any potential risks or bugs?
code is below:
{{code}}
"#;


//TODO: read local rules

#[derive(Debug, Deserialize)]
struct AILintResult {
    message: String,
    refs: Vec<String>,
}

fn main() -> Result<()> {

    env_logger::init();
    let args = Args::parse();

    let mut file = File::open(args.file_name).unwrap();
    let mut code_content = String::new();
    file.read_to_string(&mut code_content).unwrap();


    let mut env = Environment::new();
    env.add_template("lint", QUERY_TEMPLATE).unwrap();
    let query = env.get_template("lint").unwrap().render(context!(code=>code_content)).unwrap();


    let project_name = match args.project {
        Some(p) => p,
        None => {
            warn!("project name is empty, auto detect project name from git");
            git_utils::get_git_project_name()?
        }
    };

    let backend = match args.backend {
        Some(b) => b,
        None => {
            warn!("backend is empty, use default backend openai");
            "openai".to_string()
        }
    };
    //check backend should be {openai, claude, custom}
    if backend != "openai" && backend != "claude" && backend != "custom" {
        return Err(anyhow!("backend should be openai, claude, custom"));
    }

    match llm_client::query(&args.url, &args.api_key, &project_name, &query, &backend) {
        Ok(msg)=> {
            match serde_json::from_str::<AILintResult>(&msg) {
                Ok(result) => {
                    println!("{}", result.message);
                    for i in 0..result.refs.len() {
                        println!("considering {}", result.refs[i]);
                    }
                },
                Err(_) => {
                    println!("ERROR: {}", msg);
                }
            }
        },
        Err(e)=>{
            println!("request service error: {}",e);
        }
    }
    
    Ok(())
}
