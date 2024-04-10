import os
import sys
from pathlib import Path

import pytest

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


@pytest.mark.usefixtures("dev_connections", "recording_injection")
@pytest.mark.e2etest
class TestAssistantEagerFlow:
    def test_eager_flow_with_assistant(self):
        flow_path = get_flow_folder("assistant_script", EAGER_FLOWS_ROOT).absolute()
        addon_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_y",
                    "description": "Return Y value based on input X value",
                    "parameters": {
                        "type": "object",
                        "properties": {"x": {"description": "The X value", "type": "number"}},
                        "required": ["x"],
                    },
                },
            }
        ]
        inputs = {
            "assistant_name": "Math Tutor",
            "instruction": "You are a personal math tutor. Write and run code to answer math questions.",
            "model": "gpt-4",
            "question": (
                "I need to solve the equation `3x + 11 = 14`. What is the result of x+y? " "Please use get_y function."
            ),
            "tools": addon_tools,
        }
        result = _client._flows._test(flow=flow_path, inputs=inputs)
        assert result.run_info.status.value == "Completed"
