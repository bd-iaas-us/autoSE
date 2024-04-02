
use anyhow::Result;
use minijinja::{Environment, context};
use std::fs::File;
use std::io::Read;
use clap::Parser;
use april::llm_client;
use log::info;

#[derive(Parser, Debug)]
#[command(author, version, about)]
struct Args {
    #[arg(short, long)]
    file_name: String,
}

//TODO: find a better prompt:
static QUERY_TEMPLATE :&str = r#"
Rules:
- code should be clean and very documented.
- The code should work on the first try without any errors or bugs.
- Choose the library or dependency you know best.
- The extension used for the Markdown code blocks should be accurate.

User wants a bug free application, can you tell me is there any potential risks or bugs?
code is below:
{{code}}
"#;
fn main() -> Result<()> {

    env_logger::init();
    let args = Args::parse();

    let mut file = File::open(args.file_name).unwrap();
    let mut code_content = String::new();
    file.read_to_string(&mut code_content).unwrap();


    let mut env = Environment::new();
    env.add_template("lint", QUERY_TEMPLATE).unwrap();
    let query = env.get_template("lint").unwrap().render(context!(code=>code_content)).unwrap();
    
    match llm_client::query("TODO URL", "jedi", &query) {
        Ok(msg)=> {
            println!("{}", msg);
        },
        Err(e)=>{
            println!("{}",e);
        }
    }
    Ok(())
}

