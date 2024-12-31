from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import os
import uuid


@dataclass_json
@dataclass
class Config:
    server_url: str = "http://SERVER_HOST:32400"
    server_id: str = "SERVER_ID_HERE"
    lang: str = "en"
    host: str = "127.0.0.1"
    port: int = 8766
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    secret: str = field(default_factory=lambda: str(uuid.uuid4()))

def save_config():
    with open("config.json", "w") as config_file:
        config_file.write(config.to_json())

if os.path.exists("config.json"):
    try:
        with open("config.json", "r") as config_file:
            config = Config.from_json(config_file.read())
    except Exception as e:
        print("Error while reading config.json")
        raise
else:
    config = Config()
    if os.getenv("IS_DOCKER") == "1":
        config.host = "0.0.0.0"
    else:
        print("No config.json found, creating it -- please fill it with your server details")
        print("You can also set the environment variables: PDW_SERVER_URL, PDW_SERVER_ID, PDW_LANG, ...")
        save_config()
        exit()

for key in config.to_dict().keys():
    if val := os.getenv(f"PDW_{key.upper()}"):
        setattr(config, key, val)

save_config()
