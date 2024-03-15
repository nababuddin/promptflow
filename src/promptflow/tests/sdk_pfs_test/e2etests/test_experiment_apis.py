# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
import uuid
from pathlib import Path
from time import sleep

import pytest

from promptflow._sdk._constants import ExperimentStatus
from promptflow._sdk._pf_client import PFClient

from ..utils import PFSOperations, check_activity_end_telemetry

EXPERIMENT_PATH = (
    Path(__file__).parent.parent.parent / "test_configs/experiments/basic-script-template/basic-script.exp.yaml"
)


@pytest.mark.e2etest
class TestExperimentAPIs:
    def test_experiment_create_and_list(self, pf_client: PFClient, pfs_op: PFSOperations) -> None:
        name = str(uuid.uuid4())

        # Create experiment
        with check_activity_end_telemetry(
            expected_activities=[
                {"activity_name": "pf.experiment.get", "first_call": False},
                {"activity_name": "pf.experiment.create_or_update"},
            ]
        ):
            experiment = pfs_op.experiment_create(
                name=name, body={"template": EXPERIMENT_PATH.absolute().as_posix()}
            ).json
            assert name == experiment["name"]

        # Get experiment
        with check_activity_end_telemetry(activity_name=["pf.experiment.get"]):
            experiment = pfs_op.experiment_get(name=name).json
            assert name == experiment["name"]

        # List experiment
        with check_activity_end_telemetry(activity_name=["pf.experiment.list"]):
            experiments = pfs_op.experiment_list(max_results=10).json
            assert any([exp["name"] == name for exp in experiments])

    def test_experiment_start(self, pf_client: PFClient, pfs_op: PFSOperations) -> None:
        # Create experiment
        with check_activity_end_telemetry(
            expected_activities=[
                {"activity_name": "pf.experiment.get", "first_call": False},
                {"activity_name": "pf.experiment.create_or_update", "first_call": False},
                {"activity_name": "pf.experiment.start"},
            ]
        ):
            # start anonymous experiment
            pfs_op.experiment_start(body={"template": EXPERIMENT_PATH.absolute().as_posix()}).json

        name = str(uuid.uuid4())
        pfs_op.experiment_create(name=name, body={"template": EXPERIMENT_PATH.absolute().as_posix()}).json
        with check_activity_end_telemetry(
            expected_activities=[
                {"activity_name": "pf.experiment.get"},
                {"activity_name": "pf.experiment.get", "first_call": False},
                {"activity_name": "pf.experiment.create_or_update", "first_call": False},
                {"activity_name": "pf.experiment.start"},
            ]
        ):
            # start named experiment
            experiment = pfs_op.experiment_start(body={"name": name}).json
            assert name == experiment["name"]

    def test_experiment_stop(self, pf_client: PFClient, pfs_op: PFSOperations) -> None:
        exp = pfs_op.experiment_start(body={"template": EXPERIMENT_PATH.absolute().as_posix()}).json
        status = exp["status"]
        while status != ExperimentStatus.IN_PROGRESS:
            sleep(1)
            exp = pfs_op.experiment_get(exp["name"]).json
            status = exp["status"]
        with check_activity_end_telemetry(
            expected_activities=[
                {"activity_name": "pf.experiment.get", "first_call": False},
                {"activity_name": "pf.experiment.get", "first_call": False},
                {"activity_name": "pf.experiment.stop"},
            ]
        ):
            experiment = pfs_op.experiment_stop(body={"name": exp["name"]}).json
            assert experiment["status"] == ExperimentStatus.TERMINATED
