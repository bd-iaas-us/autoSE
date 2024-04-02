use serde_json::json;
use thiserror::Error;
use ehttp;
use std::sync::mpsc::channel;
use std::sync::mpsc::RecvError;

#[derive(Error, Debug)]
pub enum CustomError {
    #[error("internal channel error")]
    InternalError(#[from] RecvError),
}

pub type Result<T> = std::result::Result<T, CustomError>;


const CUSTOM_URL :&str = "http://localhost:8080/query";

pub fn query(_url :&str, topic: &str, query: &str) -> Result<String> {
        let message = json!({
                             "query": query,
                             "topic": topic,
        });
        let request = ehttp::Request::post(
            CUSTOM_URL,
            serde_json::to_vec(&message).unwrap(),
        );
    
        let (sender, receiver) = channel::<String>();
        ehttp::fetch(request, move |response| match response {
            Ok(resp) => {
                resp.text().map(|txt| {
                    sender.send(txt.to_string()).unwrap()
                });
            }
            Err(e) => {
                println!("{:?}", String::from(e));
                sender.send("failed.".to_string()).unwrap();
            }
        });

        return Ok(receiver.recv()?);
}

//deprecated
/*
pub async fn query_old(url: &str, topic: &str, query: &str) -> Result<String> {
    use reqwest::Client;
    let client = Client::new();
    //body is a json:
    //'{"topic":"faust", "query":"how clickhouse is used ?"}'
    let body = json!({
        "topic": topic,
        "query": query,
    });

    let response = client
        .post(url)
        .header(reqwest::header::CONTENT_TYPE, "application/json")
        .json(&body)
        .send()
        .await?;

    //print!("{:?}", response);
    if !response.status().is_success() {
        return Err(CustomError::InvalidStatusCode(response.status()));
    }
    let body = response.text().await?;
    Ok(body)
}
*/
