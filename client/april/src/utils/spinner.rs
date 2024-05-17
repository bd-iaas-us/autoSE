use anyhow::Result;
use crossterm::{cursor, queue, style, terminal};
use std::sync::mpsc;
use std::thread::JoinHandle;
use std::{
    io::{stdout, Stdout, Write},
    thread,
    time::Duration,
};
struct Spinner {
    index: usize,
    message: String,
    stopped: bool,
}

enum Msg {
    CONTINUE(String),
    STOP,
    PAUSE,
}

impl Spinner {
    const DATA: [&'static str; 10] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

    pub fn new(message: &str) -> Self {
        Spinner {
            index: 0,
            message: message.to_string(),
            stopped: false,
        }
    }

    pub fn step(&mut self, writer: &mut Stdout) -> Result<()> {
        if self.stopped {
            return Ok(());
        }
        let frame = Self::DATA[self.index % Self::DATA.len()];
        let dots = ".".repeat((self.index / 5) % 4);
        let line = format!("{frame}{}{:<3}", self.message, dots);
        queue!(writer, cursor::MoveToColumn(0), style::Print(line),)?;
        if self.index == 0 {
            queue!(writer, cursor::Hide)?;
        }
        writer.flush()?;
        self.index += 1;
        Ok(())
    }

    pub fn stop(&mut self, writer: &mut Stdout) -> Result<()> {
        if self.stopped {
            return Ok(());
        }
        self.stopped = true;
        queue!(
            writer,
            cursor::MoveToColumn(0),
            terminal::Clear(terminal::ClearType::FromCursorDown),
            cursor::Show
        )?;
        writer.flush()?;
        Ok(())
    }
}

pub struct SpinnerManager {
    tx: mpsc::Sender<Msg>,
    handler: Option<JoinHandle<()>>,
}

impl SpinnerManager {
    pub fn new(message: &str) -> SpinnerManager {
        let (tx, rx) = mpsc::channel();
        let handler = run_spinner(message, rx);
        SpinnerManager {
            tx,
            handler: Some(handler),
        }
    }
    pub fn pause(&self) {
        self.tx.send(Msg::PAUSE).unwrap();
    }
    pub fn stop(&mut self) {
        self.tx.send(Msg::STOP).unwrap();
        if let Some(h) = self.handler.take() {
            h.join();
        }
        //self.handler.join();
    }
    pub fn cont(&self, msg: &str) {
        self.tx.send(Msg::CONTINUE(msg.to_string()));
    }
}

fn run_spinner(message: &str, rx: mpsc::Receiver<Msg>) -> JoinHandle<()> {
    let mut writer = stdout();
    let mut spinner = Spinner::new(message);
    let handler = thread::spawn(move || loop {
        if let Ok(msg) = rx.try_recv() {
            match msg {
                Msg::STOP => {
                    spinner.stop(&mut writer).unwrap();
                    break;
                }
                Msg::CONTINUE(s) => {
                    if spinner.stopped {
                        spinner.stopped = false;
                        spinner.message = s;
                    }
                }
                Msg::PAUSE => {
                    spinner.stop(&mut writer).unwrap();
                    continue;
                }
            }
        } else {
            thread::sleep(Duration::from_millis(50));
            if !spinner.stopped {
                spinner.step(&mut writer);
            }
        }
    });
    handler
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_run_spinner() {
        let mut sm = SpinnerManager::new("hello, world");
        thread::sleep(Duration::from_secs(3));
        sm.pause();
        thread::sleep(Duration::from_secs(3));
        sm.cont("ME again");
        thread::sleep(Duration::from_secs(3));
        sm.stop();
    }
}
//test
