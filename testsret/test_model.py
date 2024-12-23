"""Tests for RetModel."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from warnings import catch_warnings
import os

from pytest import fixture, mark

from mesa.time import RandomActivation
from ret.agents.affiliation import Affiliation
from ret.agents.agent import RetAgent
from ret.agents.groupagent import GroupAgent
from ret.io import v2
from ret.model import RetModel
from ret.parameters import (
    ExperimentalControls,
    ModelParameterSpecification,
    ScenarioDependentData,
)
from ret.scenario_independent_data import ModelMetadata
from ret.space.space import ContinuousSpaceWithTerrainAndCulture2d
from ret.testing.mocks import MockModel2d, MockParametrisedModel
from ret.visualisation.json_writer import JsonWriter
from ret.utilities.save_utilities import get_latest_subfolder, add_datetime_stamp

if TYPE_CHECKING:
    from typing import Any


class MockModelWithSchedule(RetModel):
    """Mock Model with a defined schedule."""

    def __init__(self) -> None:
        """Create model."""
        start_time = datetime(2020, 1, 1, 0, 0)
        time_step = timedelta(minutes=1)
        end_time = datetime(2020, 1, 2, 0, 0)
        space = ContinuousSpaceWithTerrainAndCulture2d(1000, 1000)
        schedule = RandomActivation(self)

        super().__init__(
            start_time,
            time_step,
            end_time,
            space=space,
            schedule=schedule,
        )


class MockModelWithJsonPlaybackWriter(RetModel):
    """Mock Model with a defined schedule."""

    def __init__(self, **kwargs) -> None:
        """Create model."""
        start_time = datetime(2020, 1, 1, 0, 0)
        time_step = timedelta(hours=1)
        end_time = datetime(2020, 1, 2, 0, 0)
        space = ContinuousSpaceWithTerrainAndCulture2d(1000, 1000)

        super().__init__(start_time, time_step, end_time, space=space, **kwargs)


class TestRetModel(unittest.TestCase):
    """Tests for RetModel."""

    def setUp(self):
        """Test case setup."""
        self.model = MockModel2d(
            start_time=datetime(2020, 1, 1, 0, 0), time_step=timedelta(minutes=1), record_position=2
        )

    def test_get_time(self):
        """Test that the model time is correctly tracked following each step."""
        assert self.model.get_time() == datetime(2020, 1, 1, 0, 0)

        self.model.step()
        assert self.model.get_time() == datetime(2020, 1, 1, 0, 1)

        for _ in range(10):
            self.model.step()
        assert self.model.get_time() == datetime(2020, 1, 1, 0, 11)

    def test_providing_schedule(self):
        """Test that a user can provide their own schedule."""
        model = MockModelWithSchedule()

        assert isinstance(model.schedule, RandomActivation)


def test_providing_writer(tmpdir):
    """Test that a user can provide their own playback writer."""
    output = add_datetime_stamp(tmpdir)
    if not os.path.exists(output):
        os.makedirs(output, exist_ok=True)

    kwargs = {"output_path": output}
    model = MockModelWithJsonPlaybackWriter(**kwargs)
    output_path = os.path.join(tmpdir, get_latest_subfolder(tmpdir))
    output_path = os.path.join(output_path, "playback.json")

    assert isinstance(model.playback_writer, JsonWriter)

    map_size = model.playback_writer.json_results.initial_data.map_size

    assert map_size.x_min == model.space.x_min
    assert map_size.x_max == model.space.x_max
    assert map_size.y_min == model.space.y_min
    assert map_size.y_max == model.space.y_max


def test_model_step(tmpdir):
    """Test that the JSON writer is correctly written to following each step."""
    output = add_datetime_stamp(tmpdir)
    if not os.path.exists(output):
        os.makedirs(output, exist_ok=True)

    kwargs = {"output_path": output}
    model = MockModelWithJsonPlaybackWriter(**kwargs)
    output_path = os.path.join(tmpdir, get_latest_subfolder(tmpdir))
    output_path = os.path.join(output_path, "playback.json")

    assert len(model.playback_writer.json_results.step_data) == 0

    model.step()
    assert len(model.playback_writer.json_results.step_data) == 1
    assert len(model.playback_writer.json_results.step_data[0].agents) == 0
    assert model.playback_writer.json_results.step_data[0].step_number == 1

    model.step()
    assert len(model.playback_writer.json_results.step_data) == 2
    assert len(model.playback_writer.json_results.step_data[0].agents) == 0
    assert len(model.playback_writer.json_results.step_data[1].agents) == 0
    assert model.playback_writer.json_results.step_data[0].step_number == 1
    assert model.playback_writer.json_results.step_data[1].step_number == 2


def test_model_finish(tmpdir):
    """Tests that the JSON writer is saved at the final time step."""
    output = add_datetime_stamp(tmpdir)
    if not os.path.exists(output):
        os.makedirs(output, exist_ok=True)

    kwargs = {"output_path": output}
    model = MockModelWithJsonPlaybackWriter(**kwargs)
    output_path = os.path.join(tmpdir, get_latest_subfolder(tmpdir))
    output_path = os.path.join(output_path, "playback.json")

    for _ in range(25):
        model.step()
    with open(output_path, "r") as json_file:
        json_output_results = json_file.read()

    assert model.playback_writer.json_results.json() == json_output_results


def test_get_parameters():
    """Check the contents of the default parameters set generated by a Ret Model.

    This checks that:
        - the `get_parameters()` static method on the base model can be called,
        - the format of the expected return data (e.g., a `ModelParameterSpecification`)
        - the base model is parametrised with an empty parameter set.
    """
    assert RetModel.get_parameters() == ModelParameterSpecification(
        experimental_controls=ExperimentalControls(numeric_parameters={}, categoric_parameters={}),
        scenario_dependent_data=ScenarioDependentData(
            numeric_parameters={}, categoric_parameters={}
        ),
    )


def test_get_scenario_independent_metadata():
    """Checks the contents of the default metadata generated by a Ret Model.

    This checks that:
        - the `get_scenario_independent_metadata()` static method on the base model can be called
        - the format of the expected return data
        - the content of the expected return data
    """
    model_metadata = RetModel.get_scenario_independent_metadata()
    assert isinstance(model_metadata, ModelMetadata)
    assert model_metadata.header == "Default Ret Model"
    assert (
        "This description can be customised by the custodian of the a Ret Model, by extending "
        in model_metadata.subtext[0]
    )
    assert "the `get_scenario_independent_metadata()` static method." in model_metadata.subtext[0]
    assert (
        "It should be used to include a description, in the form of markdown components,"
        in model_metadata.subtext[1]
    )
    assert (
        "of the scenario independent data that is stored in the model." in model_metadata.subtext[1]
    )


@fixture
def schema() -> v2.RetModelSchema:
    """Create a new schema file configured for RetModel."""
    time = v2.TimeSchema(
        start_time=datetime(year=2021, month=1, day=1),
        end_time=datetime(year=2021, month=1, day=2),
        time_step=timedelta(minutes=15),
    )
    space = v2.SpaceSchema(
        dimensions=3,
        x_max=100,
        y_max=100,
        x_min=0,
        y_min=0,
        terrain_image_path=None,
        height_black=1,
        height_white=0,
        culture_image_path=None,
        cultures=[],
        clutter_background_level=0.5,
        ground_clutter_value=0.25,
        ground_clutter_height=0.75,
    )

    schema = v2.RetModelSchema(
        time=time,
        space=space,
        model_name="RetModel",
        model_module_name="ret.model",
        iterations=10,
        max_steps=5,
        experimental_controls=v2.ExperimentalControlsSchema(
            numeric_parameters={}, categoric_parameters={}
        ),
        scenario_dependent_parameters=v2.ScenarioDependentParametersSchema(
            numeric_parameters={}, categoric_parameters={}
        ),
        playback_writer="None",
        n_experiments=10,
        agent_reporters={"id": "unique_id"},
        random_state=100,
        collect_datacollector=True,
    )

    return schema


@fixture
def param_model_schema(schema: v2.RetModelSchema):
    """Create a new schema file configured for MockParametrisedModel."""
    schema.experimental_controls.numeric_parameters["n1"] = v2.NumericParameterSchema(
        name="n1", min_val=5, max_val=50, distribution="range"
    )
    schema.experimental_controls.numeric_parameters["n2"] = v2.NumericParameterSchema(
        name="n2", min_val=30, max_val=50, distribution="range"
    )
    schema.experimental_controls.categoric_parameters["c1"] = v2.CategoricParameterSchema(
        name="c1", options=["Choice 1", "Choice 2"]
    )
    schema.scenario_dependent_parameters.numeric_parameters["x1"] = 15
    schema.scenario_dependent_parameters.categoric_parameters["y1"] = "a"

    schema.model_module_name = "ret.testing.mocks"
    schema.model_name = "MockParametrisedModel"
    return schema


@mark.parametrize(
    "key, expected",
    [
        ["start_time", datetime(year=2021, month=1, day=1)],
        ["end_time", datetime(year=2021, month=1, day=2)],
        ["time_step", timedelta(minutes=15)],
        ["model_reporters", None],
        ["tables", None],
        ["log_config", "all"],
        ["playback_writer", None],
    ],
)
def test_parameter_getter(schema: v2.RetModelSchema, key: str, expected: Any):
    """Test how parameter_getter() static method converts a schema into fixed and variable args.

    Checks that the following parameters are extracted, and interpreted in the fixed data:
        - start_time
        - end_time
        - time_step
        - model_reporters
        - agent_reporters
        - tables
        - log_config
        - playback_writer

    Note - There is no test for the `space` key, which is done in a separate test, due to the
    complexity of comparing ContinuousSpaceAndTime classes.
    """
    fixed, variable = RetModel.parameter_getter(schema)
    assert variable == {}

    assert key in fixed.keys()
    assert fixed[key] == expected


def test_space_parameter_getter(schema: v2.RetModelSchema):
    """Check the properties of the `space` entry in fixed parameters."""
    fixed, _ = RetModel.parameter_getter(schema)
    space = fixed["space"]

    expected_model = schema.space.to_model()

    assert space.height == expected_model.height
    assert space.width == expected_model.width
    assert space.areas == expected_model.areas
    assert space.boundaries == expected_model.boundaries


def test_no_datacollector(schema: v2.RetModelSchema):
    """Check the properties of the `space` entry in fixed parameters."""
    schema.collect_datacollector = False
    fixed, _ = RetModel.parameter_getter(schema)

    expected_model = schema.to_model()

    assert expected_model.collect_datacollector is False


def test_parameter_getter_playback_writer_settings(schema: v2.RetModelSchema):
    """Test that if a particular playback writer is specified, the model will use it."""
    schema.playback_writer = "JsonWriter"

    fixed, _ = RetModel.parameter_getter(schema)

    created_writer = fixed["playback_writer"]

    assert isinstance(created_writer, JsonWriter)


def test_parameter_getter_empty_playback_writer(schema: v2.RetModelSchema):
    """Test parameter getter handling of blank playback writer."""
    schema.playback_writer = "None"
    fixed, _ = RetModel.parameter_getter(schema)

    created_writer = fixed["playback_writer"]
    assert created_writer is None


def test_parameter_getter_invalid_playback_writer(schema: v2.RetModelSchema):
    """Test parameter getter handling of invalid playback writer."""
    schema.playback_writer = "JosnWriterTypo"

    with catch_warnings(record=True) as w:
        fixed, _ = RetModel.parameter_getter(schema)

    assert len(w) == 1
    assert str(w[0].message) == "'JosnWriterTypo' is unregistered. Returning None."

    created_writer = fixed["playback_writer"]
    assert created_writer is None


def test_parameter_getter_missing_numeric_ec_parameter(param_model_schema: v2.RetModelSchema):
    """Test creation of default numerical experimental controls where missing from schema."""
    param_model_schema.experimental_controls.numeric_parameters.clear()

    with catch_warnings(record=True) as w:
        _, variable = MockParametrisedModel.parameter_getter(param_model_schema)

    assert len(w) == 2
    assert str(w[0].message) == "'n1' not found in model file. Defaulting to only use '[0, 100]'"
    assert str(w[1].message) == "'n2' not found in model file. Defaulting to only use '[0.1, 0.2]'"

    assert variable is not None
    assert "n1" in variable.keys()
    assert "n2" in variable.keys()


def test_parameter_getter_missing_categoric_ec_parameter(param_model_schema: v2.RetModelSchema):
    """Test creation of default categoric experimental controls where missing from schema."""
    param_model_schema.experimental_controls.categoric_parameters.clear()

    with catch_warnings(record=True) as w:
        _, variable = MockParametrisedModel.parameter_getter(param_model_schema)

    assert len(w) == 1
    assert (
        str(w[0].message)
        == "'c1' not found in model file. Defaulting to use '['Choice 1', 'Choice 2', 'Choice 3']'"
    )

    assert variable is not None
    assert "c1" in variable.keys()


def test_parameter_getter_missing_numeric_sdd_parameter(param_model_schema: v2.RetModelSchema):
    """Test creation of default numeric scenario dependent data where missing from schema."""
    param_model_schema.scenario_dependent_parameters.numeric_parameters.clear()

    with catch_warnings(record=True) as w:
        fixed, _ = MockParametrisedModel.parameter_getter(param_model_schema)

    assert len(w) == 1
    assert str(w[0].message) == "'x1' not found in model file. Defaulting to min allowable '10'"
    assert fixed is not None
    assert "x1" in fixed.keys()


def test_parameter_getter_missing_categoric_sdd_parameter(param_model_schema: v2.RetModelSchema):
    """Test creation of default categoric scenario dependent data where missing from schema."""
    param_model_schema.scenario_dependent_parameters.categoric_parameters.clear()

    with catch_warnings(record=True) as w:
        fixed, _ = MockParametrisedModel.parameter_getter(param_model_schema)

    assert len(w) == 1
    assert str(w[0].message) == "'y1' not found in model file. Defaulting to 'a'"

    assert fixed is not None
    assert "y1" in fixed.keys()


def test_get_all_agents():
    """Test model get all agents method."""
    model = MockModel2d()
    RetAgent(
        model=model,
        pos=(0, 0),
        name="Agent",
        affiliation=Affiliation.FRIENDLY,
        critical_dimension=2.0,
        reflectivity=0.1,
        temperature=20.0,
    )
    GroupAgent(
        model=model,
        name="Group Agent",
        affiliation=Affiliation.FRIENDLY,
        critical_dimension=2.0,
        agents=[
            RetAgent(
                model=model,
                pos=(0, 0),
                name="SubOrdinate Agent 1",
                affiliation=Affiliation.FRIENDLY,
                critical_dimension=2.0,
                reflectivity=0.1,
                temperature=20.0,
            ),
            RetAgent(
                model=model,
                pos=(0, 0),
                name="SubOrdinate Agent 2",
                affiliation=Affiliation.FRIENDLY,
                critical_dimension=2.0,
                reflectivity=0.1,
                temperature=20.0,
            ),
        ],
    )

    agents = model.get_all_agents()
    assert len(agents) == 4
    assert len([agent for agent in agents if agent.name == "Agent"]) == 1
    assert len([agent for agent in agents if agent.name == "Group Agent"]) == 1
    assert len([agent for agent in agents if agent.name == "SubOrdinate Agent 1"]) == 1
    assert len([agent for agent in agents if agent.name == "SubOrdinate Agent 2"]) == 1
