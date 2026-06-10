fn process_user_config(config: Option<Config>) -> Result<UserSettings, ConfigError> {
    if let Some(cfg) = config {
        if let Some(user_section) = cfg.get_section("user") {
            if let Some(name) = user_section.get_string("name") {
                if let Some(email) = user_section.get_string("email") {
                    if name.len() > 0 && email.contains('@') {
                        return Ok(UserSettings {
                            name: name.to_string(),
                            email: email.to_string(),
                            theme: user_section.get_string("theme").unwrap_or("light"),
                        });
                    }
                }
            }
        }
    }
    Err(ConfigError::InvalidConfig)
}
