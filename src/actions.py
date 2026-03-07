# src/actions.py
import json
import sys
from typing import Any, Dict, Awaitable, Callable
from src.utils import save_image_pair, reset_calibration_folders
from src.state import stop_event

# Type for action handler functions
ActionHandler = Callable[[Dict[str, Any]], Awaitable[None]]

# Global registry of actions
action_handlers: Dict[str, ActionHandler] = {}

def register_action(action_name: str):
    """Factory that returns the actual decorator"""
    def decorator(handler: ActionHandler):
        action_handlers[action_name] = handler
        return handler
    return decorator

@register_action("save")
async def handle_save(payload: Dict[str, Any]):
    # when saving a calibration pair we consider the system "calibrating" briefly
    from src import state
    state.calibrating = True
    picture_num = payload.get("picture_num")
    success = save_image_pair(picture_num if picture_num is not None else 0)
    print(f"Action 'save' executed → success: {success}")
    state.calibrating = False


@register_action("reset")
async def handle_reset(payload: Dict[str, Any]):
    reset_calibration_folders()
    print("Action 'reset' executed")


@register_action("start_calibration")
async def handle_start_calibration(payload: Dict[str, Any]):
    from src import state
    state.calibrating = True
    print("Action 'start_calibration' executed")


@register_action("stop_calibration")
async def handle_stop_calibration(payload: Dict[str, Any]):
    from src import state
    state.calibrating = False
    print("Action 'stop_calibration' executed")


@register_action("shutdown")
async def handle_shutdown(payload: Dict[str, Any]):
    print("Shutdown requested via websocket")
    stop_event.set()

def get_handler(action: str) -> ActionHandler | None:
    return action_handlers.get(action)