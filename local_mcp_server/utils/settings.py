from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    flowlens_url: str = "http://localhost:8000/flowlens"
    max_string_length: int = 50
    save_dir_path: str = "./magentic_mcp_data/"
    


settings = AppSettings()