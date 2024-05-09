use anyhow::{anyhow, Result};
use ehttp;
use log::debug;
use serde_json::json;
use std::ops::ControlFlow;
use std::sync::mpsc::channel;

/*
use thiserror::Error;
#[derive(Error, Debug)]
pub enum CustomError {
    #[error("internal channel error {0}")]
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
*/

fn block_fetching(request: ehttp::Request) -> Result<String> {
    let (sender, receiver) = channel::<std::result::Result<ehttp::Response, String>>();

    ehttp::fetch(request, move |response| {
        sender.send(response).unwrap();
    });

    let response = receiver.recv()?.map_err(|e| anyhow!(e))?;

    let txt = response
        .text()
        .ok_or(anyhow!("response's body is empty. check the server"))?;

    if response.status != 200 {
        return Err(anyhow!("remote service returns {}", response.status));
    }

    Ok(txt.to_string())
}

pub fn supported_topics(url: &str, api_key: &str) -> Result<String> {
    let mut request = ehttp::Request::get(format!("{}/supported_topics", url).as_str());
    request.headers.insert("Authorization", api_key);

    block_fetching(request)
}
pub fn dev(url: &str, api_key: &str, repo: &str, token: &str, desc: &str) -> Result<String> {
    let message = json!({
                         "repo": repo,
                         "token": token,
                         "prompt": desc,
    });

    let mut request = ehttp::Request::post(
        format!("{}/dev", url).as_str(),
        serde_json::to_vec(&message).unwrap(),
    );
    request.headers.insert("Authorization", api_key);
    request.headers.insert("Content-Type", "application/json");
    block_fetching(request)
}

pub fn status(url: &str, api_key: &str, id: &str) -> Result<String> {
    let mut request = ehttp::Request::get(format!("{}/dev/tasks/{}/status", url, id).as_str());
    request.headers.insert("Authorization", api_key);
    request.headers.insert("Content-Type", "application/json");
    block_fetching(request)
}

pub fn history(
    url: &str,
    api_key: &str,
    id: &str,
    callback: impl Fn(&Vec<u8>) + Send + 'static,
) -> Result<()> {
    let mut request = ehttp::Request::get(format!("{}/dev/histories/{}", url, id,).as_str());
    request.headers.insert("Authorization", api_key);
    request.headers.insert("Content-Type", "application/json");

    //send result in channel
    let (tx, rx) = channel::<Result<()>>();

    ehttp::streaming::fetch(request, move |part| {
        let part = match part {
            Ok(part) => part,
            Err(e) => {
                let _ = tx.send(Err(anyhow!("fetch part failed: {}", e)));
                return ControlFlow::Break(());
            }
        };
        match part {
            ehttp::streaming::Part::Response(response) => {
                debug!("history response: {:?}", response)
            }
            ehttp::streaming::Part::Chunk(chunk) => {
                debug!("chunk recved {:?}", chunk);
                if chunk.len() == 0 {
                    //send signal close thread.
                    let _ = tx.send(Ok(()));
                    return ControlFlow::Break(());
                } else {
                    callback(&chunk);
                }
            }
        }
        return ControlFlow::Continue(());
    });

    rx.recv()??;

    Ok(())
}

pub fn lint(url: &str, api_key: &str, topic: &str, code: &str) -> Result<String> {
    //parameters should be non-empty
    if code.is_empty() {
        return Err(anyhow!("code is empty"));
    }
    let message = json!({
                         "code": code,
                         "topic": topic,
    });

    debug!("topic is {}", topic);
    let mut request = ehttp::Request::post(
        format!("{}/lint", url).as_str(),
        serde_json::to_vec(&message).unwrap(),
    );
    request.headers.insert("Authorization", api_key);
    request.headers.insert("Content-Type", "application/json");

    block_fetching(request)
}
