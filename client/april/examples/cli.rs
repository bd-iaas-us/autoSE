use anyhow::{anyhow, Result};
use ehttp;
use serde_json::json;
use std::sync::mpsc::channel;

fn main() -> Result<()> {
    let message = json!({
                     "query": "what is helium?",
                     "topic": "jedi",
    });

    let request = ehttp::Request::post(
        "http://localhost:8080/query",
        serde_json::to_vec(&message).unwrap(),
    );

    let (sender, receiver) = channel::<i8>();
    println!("fetch...");
    ehttp::fetch(request, move |response| match response {
        Ok(resp) => {
            resp.text().map(|txt| {
                println!("{:?}", txt);
                sender.send(0).unwrap()
            });
        }
        Err(e) => {
            println!("{:?}", String::from(e));
            sender.send(-1).unwrap();
        }
    });

    //wait signal to quit
    receiver.recv().unwrap();
    Ok(())
}
