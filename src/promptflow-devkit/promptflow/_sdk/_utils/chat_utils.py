from pathlib import Path
from typing import Tuple, TypedDict
from urllib.parse import urlencode, urlunparse

from promptflow._sdk._constants import PROMPT_FLOW_DIR_NAME, SESSION_CONFIG_FILE_NAME
from promptflow._utils.flow_utils import resolve_flow_path
from promptflow.exceptions import UserErrorException


def construct_session_id(flow: str) -> str:
    # TODO: register chat session so that we may store related information in db and allow multiple
    #  debug sessions on the same flow
    flow_dir, flow_file = resolve_flow_path(flow)
    return (flow_dir / flow_file).absolute().resolve().as_posix()


def register_chat_session(
    session_id: str, flow_dir: Path, pfs_port, url_params: dict, enable_internal_features: bool
) -> Tuple[str, str]:
    from promptflow._sdk._service.utils.utils import encrypt_flow_path

    session_config_file_path = flow_dir / PROMPT_FLOW_DIR_NAME / SESSION_CONFIG_FILE_NAME
    session_config_file_path.parent.mkdir(parents=True, exist_ok=True)
    if session_config_file_path.is_file():
        # TODO: remove session config automatically if there is no service found in target port
        raise UserErrorException(
            f"Session config file {session_config_file_path} already exists. "
            f"Please close existing flow test session first.\n"
            "If there is no existing session, please remove the session config file manually."
        )

    # Todo: use base64 encode for now, will consider whether need use encryption or use db to store flow path info
    query_dict = {"flow": encrypt_flow_path(session_id), **url_params}
    if enable_internal_features:
        query_dict["enable_internal_features"] = "true"
    query_params = urlencode(query_dict)

    return session_id, urlunparse(("http", f"127.0.0.1:{pfs_port}", "/v1.0/ui/chat", "", query_params, ""))


def unregister_chat_session(session_id: str, *, flow_dir: Path):
    session_config_file_path = flow_dir / PROMPT_FLOW_DIR_NAME / SESSION_CONFIG_FILE_NAME
    if session_config_file_path.is_file():
        session_config_file_path.unlink()


def get_info_for_flow_monitor(*, session_id, flow_dir: Path) -> TypedDict("FlowInfo", {"hash": str}):
    return {
        # TODO: calculate hash for flow file
        "hash": "hash",
    }


def update_session_config(session_id, *, serving_port, flow_dir: Path):
    session_config_file_path = flow_dir / PROMPT_FLOW_DIR_NAME / SESSION_CONFIG_FILE_NAME
    with open(session_config_file_path, "w") as f:
        f.write(f"{serving_port}\n")
