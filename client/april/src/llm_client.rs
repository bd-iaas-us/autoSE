use ehttp::Response;
use log::debug;
use serde_json::json;
use thiserror::Error;
use ehttp;
use std::fmt::format;
use std::result;
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
    #[error("http error {0}")]
    HttpError(String),
    #[error("response body is missing")]
    BodyMissing,
}

pub type Result<T> = std::result::Result<T, CustomError>;


pub fn supported_topics(url :&str, api_key :&str) -> Result<String> {
    let mut request = ehttp::Request::get(
        format!("{}/supported_topics", url).as_str(),
    );
    request.headers.insert("Authorization", api_key);
    let (sender, receiver) = channel::<std::result::Result<ehttp::Response, String>>();

    ehttp::fetch(request, move |response| {
            sender.send(response).unwrap();
    });

    match receiver.recv()? {
    Ok(response) => {
        let txt = response.text().ok_or(CustomError::BodyMissing)?;
        Ok(txt.to_string())
    }
    Err(e) => {
        Err(CustomError::HttpError(e))
    }
}

}

pub fn query(url :&str, api_key :&str, topic: &str, query: &str, ai :&str) -> Result<String> {
        //parameters should be non-empty
        if query.is_empty() || ai.is_empty() {
            return Err(CustomError::InvalidParameters);
        }
        let message = json!({
                             "query": query,
                             "topic": topic,
                             "ai": ai,
        });

        debug!("topic is {}", topic);
        let mut request = ehttp::Request::post(
                    format!("{}/query", url).as_str(),
                    serde_json::to_vec(&message).unwrap(),
        );
        request.headers.insert("Authorization", api_key);
    

        let (sender, receiver) = channel::<std::result::Result<ehttp::Response, String>>();

        ehttp::fetch(request, move |response| {
            sender.send(response).unwrap();
        });


        match receiver.recv()? {
            Ok(response) => {
                let txt = response.text().ok_or(CustomError::BodyMissing)?;
                Ok(txt.to_string())
            }
            Err(e) => {
                Err(CustomError::HttpError(e))
            }
        }
}
