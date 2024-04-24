import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)


def find_available_port() -> str:
    """Find an available port on localhost"""
    # TODO: replace find_available_port in CSharpExecutorProxy with this one
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        _, port = s.getsockname()
        return str(port)


def serve_flow_csharp(flow_file_path, flow_dir, port):
    from promptflow._proxy._csharp_executor_proxy import EXECUTOR_SERVICE_DLL

    try:
        command = [
            "dotnet",
            EXECUTOR_SERVICE_DLL,
            "--port",
            str(port),
            "--yaml_path",
            flow_file_path,
            "--assembly_folder",
            ".",
            "--connection_provider_url",
            "",
            "--log_path",
            "",
            "--serving",
        ]
        subprocess.run(command, cwd=flow_dir, stdout=sys.stdout, stderr=sys.stderr)
    except KeyboardInterrupt:
        pass


def _resolve_python_flow_additional_includes(source) -> Path:
    # Resolve flow additional includes
    from promptflow.client import load_flow

    flow = load_flow(source)
    from promptflow._sdk.operations import FlowOperations

    with FlowOperations._resolve_additional_includes(flow.path) as resolved_flow_path:
        if resolved_flow_path == flow.path:
            return source
        # Copy resolved flow to temp folder if additional includes exists
        # Note: DO NOT use resolved flow path directly, as when inner logic raise exception,
        # temp dir will fail due to file occupied by other process.
        temp_flow_path = Path(tempfile.TemporaryDirectory().name)
        shutil.copytree(src=resolved_flow_path.parent, dst=temp_flow_path, dirs_exist_ok=True)

    return temp_flow_path


def serve_flow_python(*, static_folder, source, host, port, config, environment_variables, init, skip_open_browser):
    from promptflow._sdk._configuration import Configuration
    from promptflow.core._serving.app import create_app

    if static_folder:
        static_folder = Path(static_folder).absolute().as_posix()
    pf_config = Configuration(overrides=config)
    logger.info(f"Promptflow config: {pf_config}")
    connection_provider = pf_config.get_connection_provider()
    source = _resolve_python_flow_additional_includes(source)
    os.environ["PROMPTFLOW_PROJECT_PATH"] = source.absolute().as_posix()
    logger.info(f"Change working directory to model dir {source}")
    os.chdir(source)
    app = create_app(
        static_folder=static_folder,
        environment_variables=environment_variables,
        connection_provider=connection_provider,
        init=init,
    )
    if not skip_open_browser:
        target = f"http://{host}:{port}"
        logger.info(f"Opening browser {target}...")
        webbrowser.open(target)
    # Debug is not supported for now as debug will rerun command, and we changed working directory.
    app.run(port=port, host=host)
