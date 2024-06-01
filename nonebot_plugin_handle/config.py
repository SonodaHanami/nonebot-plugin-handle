from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    handle_need_to_me: bool = False
    handle_use_cmd_start: bool = False
    handle_strict_mode: bool = True
    # handle_confirm_mode: bool = False
    handle_color_enhance: bool = False


handle_config = get_plugin_config(Config)
