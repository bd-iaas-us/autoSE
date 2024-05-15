use anyhow::{anyhow, Result};
use april::llm_client;
use april::utils::git;
use april::utils::markdown;
use april::utils::spinner;
use clap::{Parser, Subcommand};
use lazy_static::lazy_static;
use log::{debug, warn};
use regex::Regex;
use serde::Deserialize;
use std::cell::RefCell;
use std::fmt;
use std::fs::File;
use std::io::prelude::*;
use std::io::BufReader;
use std::io::Read;
use std::sync::mpsc;
use std::sync::Arc;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use std::time::Instant;

#[derive(Parser)]
#[command(author, version, about, long_about = None, arg_required_else_help = true)]
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
    /// lint the file
    Lint {
        /// Configuration file to use
        #[clap(index = 1)]
        file_name: Option<String>,
        #[arg(long)]
        diff_mode: bool,
    },

    /// given a description, wrote a patch.
    Dev {
        /// yaml file describe the task
        #[clap(index = 1)]
        description_filename: Option<String>,
        /// read remote tasks' log
        #[arg(long, short)]
        follow: Option<String>,
        /// get remote tasks' patch
        #[arg(long, short)]
        patch: Option<String>,
    },
}

//TODO: read local rules

#[derive(Debug, Deserialize)]
struct Risk {
    which_part_of_code: String,
    reason: String,
    fix: String,
}

lazy_static! {
    static ref RENDER: Mutex<markdown::MarkdownRender> = {
        let theme =
            bincode::deserialize_from(markdown::DARK_THEME).expect("Invalid builtin light theme");
        let mut options = markdown::RenderOptions::default();
        options.theme = Some(theme);
        options.truecolor = true;
        let render = markdown::MarkdownRender::init(options).unwrap();
        Mutex::new(render)
    };
}

//TODO: should have better highlight.
impl fmt::Display for Risk {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let mut render = RENDER.lock().unwrap();
        write!(
            f,
            "{}  :{}\n{}:{}\n{}   :{}\n",
            render.render(r#"*Code*"#),
            render.render(&self.which_part_of_code),
            render.render(r#"*Reason*"#),
            render.render(&self.reason),
            render.render(r#"*Fix*"#),
            render.render(&self.fix)
        )
    }
}

#[derive(Debug, Deserialize)]
struct Risks {
    risks: Vec<Risk>,    //openai could return structual data
    plain_risks: String, //other LLM will returna un-structual data
    backend: String,     //enum:openai or custom
}

#[derive(Debug, Deserialize)]
struct AILintSupportedTopics {
    topics: Vec<String>,
}

fn display_history(api_url: &str, api_key: &str, task_id: &str) -> Result<()> {
    let (tx, rx) = mpsc::channel();

    //wrap thread handler in Option is a must.
    //because we could use take to make sure handler is removed.
    let handler = RefCell::new(Some(spinner::run_spinner(
        "AI is prepare..., it may take around 1 minutes...",
        rx,
    )));
    let is_first_chunk_arrive = RefCell::new(true);
    let display_history = move |chunk: &Vec<u8>| match String::from_utf8(chunk.clone()) {
        Ok(s) => {
            if *is_first_chunk_arrive.borrow() {
                let _ = tx.send(());
                handler
                    .take()
                    .unwrap()
                    .join()
                    .expect("thread join should be success");
                *is_first_chunk_arrive.borrow_mut() = false;
            }
            debug!("recved time: {:?}", Instant::now());

            let mut render = RENDER.lock().unwrap();
            println!("{}", render.render(&s));
        }
        Err(_) => {}
    };
    llm_client::history(api_url, api_key, task_id, display_history)?;

    Ok(())
}

//lint
fn lint(file_name: Option<String>, diff_mode: bool, api_url: &str, api_key: &str) -> Result<()> {
    let mut project_name = String::new();
    let mut code = String::new();
    if diff_mode {
        project_name = git::get_git_project_name().map_err(|e| {
            println!("diff mode is only supported for git project");
            e
        })?;
        //if file_name is provided in diff_mode, we only lint the file itself.
        //if no file name is provided, we could lint the whole project.
        code = git::get_git_diff(&file_name)?;
    } else
    /* single file mode */
    {
        //project_name could be "" or some project name
        project_name = git::get_git_project_name().unwrap_or_default();

        let file_name = file_name.ok_or(anyhow!("you should provide a file name to lint"))?;
        let mut file = File::open(file_name)?;
        file.read_to_string(&mut code)?;
    }

    let (tx, rx) = mpsc::channel();
    let handler = spinner::run_spinner("Generating", rx);

    match llm_client::lint(api_url, api_key, &project_name, &code) {
        Ok(msg) => {
            //close the fancy spinner.
            let _ = tx.send(());
            let _ = handler.join();
            let risks = serde_json::from_str::<Risks>(&msg).map_err(|e| {
                println!("parse error{}", msg);
                e
            })?;

            if risks.backend == "openai" {
                for risk in risks.risks {
                    println!("{}", risk);
                }
            } else {
                let mut render = RENDER.lock().unwrap();
                println!("{}", render.render(&risks.plain_risks));
            }
        }
        Err(e) => {
            let _ = tx.send(());
            let _ = handler.join();
            println!("request service error: {}", e);
        }
    }

    Ok(())
}

#[derive(Debug, Deserialize)]
struct DevTask {
    repo: String,
    description: String,
    token: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Task {
    task_id: String,
}

#[derive(Debug, Deserialize)]
struct Status {
    status: String,
    patch: Option<String>,
}

fn download_patch(api_url: &str, api_key: &str, uuid: &str) -> Result<()> {
    let resp = llm_client::status(api_url, api_key, &uuid)?;
    let status = serde_json::from_str::<Status>(&resp)?;
    if status.status == "DONE" && status.patch.is_some() {
        let file_name = format!("{}.diff", uuid);
        let patch_content = status.patch.unwrap();
        //save to uuid.diff
        let mut file = File::create(&file_name)?;
        file.write_all(patch_content.as_bytes())?;
        println!("task {} done. saved patch into {}", uuid, file_name);
    } else {
        //display current status
        println!("task {}'s status is {:?}", uuid, status);
    }
    Ok(())
}

//TODO:
fn dev(
    description_filename: Option<String>,
    follow: Option<String>,
    patch: Option<String>,
    api_url: &str,
    api_key: &str,
) -> Result<()> {
    //get patch
    if let Some(uuid) = patch {
        download_patch(api_url, api_key, &uuid)
    //follow history
    } else if let Some(uuid) = follow {
        //follow mode
        display_history(api_url, api_key, &uuid)?;
        Ok(())
    //submit task and follow history.
    } else if let Some(desc_filename) = description_filename {
        let file = File::open(desc_filename)?;
        let reader = BufReader::new(file);
        let task: DevTask = serde_yaml::from_reader(reader).expect("Failed to parse YAML");

        let repo = &task.repo;
        let token = match task.token {
            Some(token) => token,
            None => "".to_string(),
        };
        let desc = task.description;
        /*
        //read local yml file. get this paramters.
        let repo = "https://github.com/bd-iaas-us/AILint.git";
        let token = "FAKE_TOKEN";
        */
        debug!("{},{},{}", repo, token, desc);
        let resp = llm_client::dev(api_url, api_key, &repo, &token, &desc)?;

        let task = serde_json::from_str::<Task>(&resp)
            .map_err(|e| anyhow!("can not parse response for submitting dev {}", e))?;
        println!(
            "TASK {} is accepted...\nDisplaying the log of AI thoughts...\n",
            task.task_id
        );
        //FIXME: backend is too slow, I have to wait
        display_history(api_url, api_key, &task.task_id)?;
        download_patch(api_url, api_key, &task.task_id)?;
        Ok(())
    } else {
        println!("print usage");
        Ok(())
    }
}

fn main() -> Result<()> {
    env_logger::init();
    let cli = Cli::parse();

    match cli.command {
        Commands::Dev {
            description_filename,
            follow,
            patch,
        } => dev(
            description_filename,
            follow,
            patch,
            &cli.api_url,
            &cli.api_key,
        ),
        Commands::Lint {
            file_name,
            diff_mode,
        } => lint(file_name, diff_mode, &cli.api_url, &cli.api_key),
    }
}
