from typing import Optional
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    flowlens_url: str = "https://flowlens-api.magentic.ai/flowlens"
    flowlens_max_string_length: int = 50
    flowlens_save_dir_path: str = "./magentic_flowlens_mcp_data/"
    flowlens_api_token: Optional[str] = None
    


settings = AppSettings()