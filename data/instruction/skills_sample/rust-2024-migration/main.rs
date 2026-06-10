use std::collections::HashMap;

fn process_config(config: Option<HashMap<String, String>>) -> Option<String> {
    if let Some(cfg) = config {
        if let Some(host) = cfg.get("host") {
            if let Some(port) = cfg.get("port") {
                if let Ok(port_num) = port.parse::<u16>() {
                    if port_num > 1024 {
                        return Some(format!("{}:{}", host, port_num));
                    }
                }
            }
        }
    }
    None
}

async fn fetch_user(client: &reqwest::Client, id: u64) -> Result<String, reqwest::Error> {
    let resp = client.get(format!("https://api.example.com/users/{}", id))
        .send()
        .await?
        .text()
        .await?;
    Ok(resp)
}

fn main() {
    let mut config = HashMap::new();
    config.insert("host".to_string(), "localhost".to_string());
    config.insert("port".to_string(), "8080".to_string());
    
    if let Some(addr) = process_config(Some(config)) {
        println!("Server address: {}", addr);
    }
}
