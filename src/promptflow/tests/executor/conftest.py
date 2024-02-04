import multiprocessing
from pathlib import Path
from unittest.mock import patch

import pytest
from executor.process_utils import MockForkServerProcess, MockSpawnProcess
from sdk_cli_test.recording_utilities import (
    RecordStorage,
    delete_count_lock_file,
    inject_async_with_recording,
    inject_sync_with_recording,
    is_live,
    is_record,
    is_replay,
    mock_tool,
    recording_array_extend,
    recording_array_reset,
)
from sdk_cli_test.recording_utilities.record_storage import is_recording_enabled

from promptflow._core.openai_injector import inject_openai_api

PROMPTFLOW_ROOT = Path(__file__) / "../../.."
RECORDINGS_TEST_CONFIGS_ROOT = Path(PROMPTFLOW_ROOT / "tests/test_configs/node_recordings").resolve()


@pytest.fixture
def recording_setup():
    patches = setup_recording()
    try:
        yield
    finally:
        for patcher in patches:
            patcher.stop()


def setup_recording():
    patches = []

    def start_patches(patch_targets):
        for target, mock_func in patch_targets.items():
            patcher = patch(target, mock_func)
            patches.append(patcher)
            patcher.start()

    if is_replay() or is_record():
        file_path = RECORDINGS_TEST_CONFIGS_ROOT / "executor_node_cache.shelve"
        RecordStorage.get_instance(file_path)

        from promptflow._core.tool import tool as original_tool

        mocked_tool = mock_tool(original_tool)
        patch_targets = {
            "promptflow._core.tool.tool": mocked_tool,
            "promptflow._internal.tool": mocked_tool,
            "promptflow.tool": mocked_tool,
            "promptflow._core.openai_injector.inject_sync": inject_sync_with_recording,
            "promptflow._core.openai_injector.inject_async": inject_async_with_recording,
        }
        start_patches(patch_targets)
        inject_openai_api()

    if is_live():
        patch_targets = {
            "promptflow._core.openai_injector.inject_sync": inject_sync_with_recording,
            "promptflow._core.openai_injector.inject_async": inject_async_with_recording,
        }
        start_patches(patch_targets)
        inject_openai_api()

    return patches


def override_recording_file():
    if is_replay() or is_record():
        file_path = RECORDINGS_TEST_CONFIGS_ROOT / "executor_node_cache.shelve"
        RecordStorage.get_instance(file_path)


@pytest.fixture
def process_override():
    # This fixture is used to override the Process class to ensure the recording mode works
    start_methods_mocks = {"spawn": MockSpawnProcess, "forkserver": MockForkServerProcess}
    original_process_class = {}
    for start_method, MockProcessClass in start_methods_mocks.items():
        if start_method in multiprocessing.get_all_start_methods():
            original_process_class[start_method] = multiprocessing.get_context(start_method).Process
            multiprocessing.get_context(start_method).Process = MockProcessClass
            if start_method == multiprocessing.get_start_method():
                multiprocessing.Process = MockProcessClass

    try:
        yield
    finally:
        for start_method, MockProcessClass in start_methods_mocks.items():
            if start_method in multiprocessing.get_all_start_methods():
                multiprocessing.get_context(start_method).Process = original_process_class[start_method]
                if start_method == multiprocessing.get_start_method():
                    multiprocessing.Process = original_process_class[start_method]


@pytest.fixture
def recording_injection(recording_setup, process_override):
    # This fixture is used to main entry point to inject recording mode into the test
    try:
        yield (is_replay() or is_record(), recording_array_extend)
    finally:
        if is_replay() or is_record():
            RecordStorage.get_instance().delete_lock_file()
            delete_count_lock_file()
        recording_array_reset()


@pytest.fixture(autouse=True, scope="session")
def inject_api_executor():
    """Inject OpenAI API during test session when recording not enabled

    AOAI call in promptflow should involve trace logging and header injection. Inject
    function to API call in test scenario."""
    if not is_recording_enabled():
        inject_openai_api()
