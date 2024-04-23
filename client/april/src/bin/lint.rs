
use anyhow::{anyhow, Result};
use minijinja::{Environment, context};
use std::fs::File;
use std::io::Read;
use clap::Parser;
use april::llm_client;
use april::git_utils;
use log::{warn, debug};
use serde::Deserialize;




#[derive(Parser, Debug)]
#[command(author, version, about)]
struct Args {
    #[clap(index = 1)]
    file_name: Option<String>,
    //3 backends, openai, claude, custom
    #[arg(long, default_value = "openai", env = "BACKEND")]
    backend: Option<String>,
    #[arg(long, default_value = "http://localhost:8000", env = "API_URL")]
    api_url: String,
    #[arg(long, default_value = "unknown", env = "API_KEY")]
    api_key: String
}

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


fn build_query_single_file(args: &Args) -> Result<String>{
    let file_name = match &args.file_name {
        Some(f) => f,
        None => {
            return Err(anyhow!("file name is empty"));
        }
    };
    
    let mut file = File::open(file_name).unwrap();
    let mut code_content = String::new();
    file.read_to_string(&mut code_content).unwrap();

    let mut env = Environment::new();
    env.add_template("lint", QUERY_CODE_TEMPLATE).unwrap();
    Ok(env.get_template("lint").unwrap().render(context!(code=>code_content)).unwrap())
}

fn build_query_diff(args: &Args) -> Result<String>{
    let file_diff = git_utils::get_git_diff(args.file_name.as_deref())?;

    let mut env = Environment::new();
    env.add_template("lint", QUERY_CODE_DIFF_TEMPLATE).unwrap();
    Ok(env.get_template("lint").unwrap().render(context!(code=>file_diff)).unwrap())
}


fn main() -> Result<()> {

    env_logger::init();

    let args = Args::parse();



    let backend = match &args.backend {
        Some(b) => b,
        None => {
            warn!("backend is empty, use default backend openai");
            "openai"
        }
    };

    
    //check backend should be {openai, claude, custom}
    if backend != "openai" && backend != "claude" && backend != "custom" {
        return Err(anyhow!("backend should be openai, claude, custom"));
    }
    debug!("backend is {}", backend);


    let msg = llm_client::supported_topics(&args.api_url, &args.api_key)?;
    let result = match serde_json::from_str::<AILintSupportedTopics>(&msg) {
        Ok(r) => r,
        Err(e) => {
            return Err(anyhow!("parse supported topics error: {},{}", e, msg));
        }
    };

    let mut project_name = match git_utils::get_git_project_name() {
        Ok(p) => p,
        Err(e) => {
            debug!("get project name error: {}", e);
            String::new()
        }
    };

    let is_rag_supported = result.topics.contains(&project_name);
    

    //debug info
    debug!("is rag supported: {}, supported topics are {:?}", is_rag_supported, result.topics);

    
    let mut query = String::new();

    if !is_rag_supported {
            query = build_query_single_file(&args)?;
            project_name = "".to_string();

    } else {/*rag is supported*/
            //is rag is supported, use the code diff as prompt
            let file_diff = git_utils::get_git_diff(args.file_name.as_deref())?;

            if file_diff.len() >0  {
                query = build_query_diff(&args)?;
            } else {
                query = build_query_single_file(&args)?;
            }
    }

    match llm_client::query(&args.api_url, &args.api_key, &project_name, &query, &backend) {
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
