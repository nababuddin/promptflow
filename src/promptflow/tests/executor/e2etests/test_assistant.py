import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

from promptflow._sdk._pf_client import PFClient
from promptflow.contracts.run_info import Status
from promptflow.executor import FlowExecutor

from ..utils import EAGER_FLOWS_ROOT, get_flow_folder, get_flow_package_tool_definition, get_yaml_file

PACKAGE_TOOL_BASE = Path(__file__).parent.parent / "package_tools"
PACKAGE_TOOL_ENTRY = "promptflow._core.tools_manager.collect_package_tools"
sys.path.insert(0, str(PACKAGE_TOOL_BASE.resolve()))


@pytest.mark.usefixtures("dev_connections", "recording_injection")
@pytest.mark.e2etest
class TestAssistant:
    @pytest.mark.parametrize(
        "flow_folder, line_input",
        [
            ("assistant-tool-with-connection", {"name": "Mike"}),
        ],
    )
    def test_assistant_tool_with_connection(self, flow_folder, line_input, dev_connections):
        executor = FlowExecutor.create(get_yaml_file(flow_folder), dev_connections)
        flow_result = executor.exec_line(line_input)
        print(flow_result.output)
        assert flow_result.run_info.status == Status.Completed
        assert len(flow_result.output["answer"]["content"]) == 1
        assert flow_result.output["answer"]["content"][0]["type"] == "text"
        assert flow_result.output["thread_id"]

    @pytest.mark.parametrize(
        "flow_folder, line_input",
        [
            (
                "food-calorie-assistant",
                {
                    "assistant_input": [
                        {"type": "text", "text": "Please generate the calories report for my meal plan."},
                        {"type": "file_path", "file_path": {"path": "./meal_plan.csv"}},
                    ]
                },
            ),
        ],
    )
    def test_assistant_with_image(self, flow_folder, line_input, dev_connections):
        os.chdir(get_flow_folder(flow_folder))
        executor = FlowExecutor.create(get_yaml_file(flow_folder), dev_connections)
        flow_result = executor.exec_line(line_input)
        print(flow_result.output)
        assert flow_result.run_info.status == Status.Completed
        assert len(flow_result.output["assistant_output"]["content"]) > 0
        assert len(flow_result.output["assistant_output"]["file_id_references"]) > 0
        assert flow_result.output["thread_id"]

    @pytest.mark.parametrize(
        "flow_folder",
        [
            "assistant-with-package-tool",
        ],
    )
    def test_assistant_package_tool_with_conn(self, mocker, flow_folder, dev_connections):
        package_tool_definition = get_flow_package_tool_definition(flow_folder)

        with mocker.patch(PACKAGE_TOOL_ENTRY, return_value=package_tool_definition):
            executor = FlowExecutor.create(get_yaml_file(flow_folder), dev_connections, raise_ex=True)
            flow_result = executor.exec_line({})
            assert flow_result.run_info.status == Status.Completed


_client = PFClient()


def clear_module_cache(module_name):
    try:
        del sys.modules[module_name]
    except Exception:
        pass


@pytest.mark.usefixtures("dev_connections", "recording_injection")
@pytest.mark.e2etest
class TestAssistantEagerFlow:
    def test_eager_flow_with_assistant(self):
        # Need to create .env file for the flow.
        # > python generate_connection_config.py --target_folder <flow_folder>
        flow_path = get_flow_folder("math_tutor", EAGER_FLOWS_ROOT).absolute()
        # Load .env file as env variables
        load_dotenv(dotenv_path=f"{flow_path}/.env")
        inputs = {
            "question": (
                "I need to solve the equation `3x + 11 = 14`. What is the result of x+y? " "Please use get_y function."
            ),
            "assistant_id": "asst_0338THvtgeRnQxCehbI18Kcc",
        }
        result = _client._flows._test(flow=flow_path, inputs=inputs)
        assert result.run_info.status.value == "Completed"

    def test_eager_flow_with_two_assistants1(self):
        # Need to create .env file for the flow.
        # > python generate_connection_config.py --target_folder <flow_folder>
        flow_path = get_flow_folder("story_assistant", EAGER_FLOWS_ROOT).absolute()
        # Load .env file as env variables
        load_dotenv(dotenv_path=f"{flow_path}/.env")

        inputs = {
            "topic": "Basketball.",
            "assistant_1": "asst_QL6GNvHgl5KYaTskQ9CyEzBn",
            "assistant_2": "asst_JXWJGNMrDyXu9nUfqRct7mVe",
        }
        result = _client._flows._test(flow=flow_path, inputs=inputs)
        assert result.run_info.status.value == "Completed"

    def test_eager_flow_with_two_assistants2(self):
        # Need to create .env file for the flow.
        # > python generate_connection_config.py --target_folder <flow_folder>
        flow_path = get_flow_folder("story_assistant_with_tracing_details", EAGER_FLOWS_ROOT).absolute()
        # Load .env file as env variables
        load_dotenv(dotenv_path=f"{flow_path}/.env")

        inputs = {"topic": "Basketball."}
        result = _client._flows._test(flow=flow_path, inputs=inputs)
        assert result.run_info.status.value == "Completed"
