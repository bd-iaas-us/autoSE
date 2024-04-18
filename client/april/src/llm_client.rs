use serde_json::json;
use thiserror::Error;
use ehttp;
use std::sync::mpsc::channel;
use std::sync::mpsc::RecvError;


#[derive(Error, Debug)]
pub enum CustomError {
    #[error("internal channel error")]
    InternalError(#[from] RecvError),
    #[error("invalid parameters")]
    InvalidParameters,
    #[error("env error")]
    EnvError(#[from] std::env::VarError),
}

pub type Result<T> = std::result::Result<T, CustomError>;


pub fn query(url :&str, api_key :&str, topic: &str, query: &str, ai :&str) -> Result<String> {
        //parameters should be non-empty
        if query.is_empty() || topic.is_empty() || ai.is_empty() {
            return Err(CustomError::InvalidParameters);
        }
        let message = json!({
                             "query": query,
                             "topic": topic,
                             "ai": ai,
        });

     
        let mut request = ehttp::Request::post(
                    url,
                    serde_json::to_vec(&message).unwrap(),
        );
        request.headers.insert("Authorization", api_key);
    

        let (sender, receiver) = channel::<String>();
        ehttp::fetch(request, move |response| match response {
            Ok(resp) => {
                resp.text().map(|txt| {
                    sender.send(txt.to_string()).unwrap()
                });
            }
            Err(e) => {
                sender.send(e.to_string()).unwrap();
            }
        });

        return Ok(receiver.recv()?);
}
