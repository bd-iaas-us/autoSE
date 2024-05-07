use anyhow::{anyhow, Result};
use april::llm_client;
use april::utils::git;
use april::utils::markdown;
use april::utils::markdown::MarkdownRender;
use april::utils::spinner;
use clap::{Parser, Subcommand};
use lazy_static::lazy_static;
use log::{debug, warn};
use serde::Deserialize;
use std::fmt;
use std::fs::File;
use std::io::Read;
use std::io::{self, Write};
use std::sync::mpsc;
use std::sync::Mutex;
use websocket::message::OwnedMessage;
use websocket::ClientBuilder;
use websocket::Message;

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
        /// Detail level
        #[clap(index = 1)]
        description: String,
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
            "Code  :{}\nReason:{}\nFix   :{}\n",
            render.render(&self.which_part_of_code),
            render.render(&self.reason),
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
    let handler = spinner::run_spinner("Generating", rx);

    match llm_client::query(api_url, api_key, &project_name, &code) {
        Ok(msg) => {
            //close the fancy spinner.
            let _ = tx.send(());
            let _ = handler.join();

            //return 200
            match serde_json::from_str::<Risks>(&msg) {
                Ok(risks) => {
                    if risks.backend == "openai" {
                        for risk in risks.risks {
                            println!("{}", risk);
                        }
                    } else {
                        let mut render = RENDER.lock().unwrap();
                        println!("{}", render.render(&risks.plain_risks));
                    }
                }
                Err(_) => {
                    println!("parse error{}", msg);
                }
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

//TODO:
fn dev(description: &str) -> Result<()> {
    // println!("not implemented");
    // Ok(())

    let server_addr = "ws://127.0.0.1:8000/ws";

    let client = ClientBuilder::new(server_addr)
        .unwrap()
        .connect_insecure()
        .unwrap();

    let (mut receiver, mut sender) = client.split().unwrap();

    for message in receiver.incoming_messages() {
        let message = message.unwrap();
        match message {
            OwnedMessage::Close(_) => {
                let _ = sender.send_message(&Message::close());
                break;
            }
            // OwnedMessage::Ping(ping) => {
            //     let _ = sender.send_message(&Message::pong(ping));
            // }
            OwnedMessage::Text(text) => {
                println!("Received message: {}", text);
            }
            _ => {}
        }
    }

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
