"""Jenkins agent selection: no placeholder image by default, Docker agent opt-in."""

import argparse

import pytest

from devops_os.core import scaffold_jenkins
from mcp_server.server import generate_jenkins_pipeline
from mcp_server.validators import ValidationError, validate_image_reference

TYPES = ["build", "test", "deploy", "complete", "parameterized"]


@pytest.mark.parametrize("pipeline_type", TYPES)
def test_default_uses_agent_any_and_no_placeholder(pipeline_type):
    text = generate_jenkins_pipeline(name="demo", pipeline_type=pipeline_type, languages="python")
    assert "yourorg" not in text
    assert text.startswith("pipeline {\n    agent any\n")
    assert "docker.sock" not in text


@pytest.mark.parametrize("pipeline_type", TYPES)
def test_container_image_opts_in_to_docker_agent(pipeline_type):
    text = generate_jenkins_pipeline(name="demo", pipeline_type=pipeline_type, container_image="python:3.12")
    assert "agent {\n        docker {\n            image 'python:3.12'" in text
    assert "agent any" not in text


@pytest.mark.parametrize("bad", ["x' ; sh 'evil", "a b", "$(id)", "img\\", 'a"b', "-x", "a\nb", "img`id`"])
def test_image_that_could_break_out_of_the_groovy_string_is_rejected(bad):
    with pytest.raises(ValueError):
        generate_jenkins_pipeline(name="demo", container_image=bad)


@pytest.mark.parametrize("good", [
    "python:3.12", "ghcr.io/org/app:v1.2.3", "registry.local:5000/team/app:latest",
    "alpine", "org/app@sha256:" + "a" * 64,
])
def test_valid_image_references_still_accepted(good):
    assert validate_image_reference(good) == good


def test_cli_namespace_without_image_attribute_still_works():
    args = argparse.Namespace(name="d", type="build", languages="python", kubernetes=False, k8s_method="kubectl",
                              parameters=False, registry="docker.io", scm="git", output="x")
    configs = {"languages": scaffold_jenkins.generate_language_config("python", {}),
               "kubernetes": scaffold_jenkins.generate_kubernetes_config(False, "kubectl", {}),
               "cicd": scaffold_jenkins.generate_cicd_config({}),
               "build_tools": scaffold_jenkins.generate_build_tools_config({}),
               "code_analysis": scaffold_jenkins.generate_code_analysis_config({}),
               "devops_tools": scaffold_jenkins.generate_devops_tools_config({})}
    assert "agent any" in scaffold_jenkins.generate_pipeline(args, configs)


def test_validation_error_is_a_value_error():
    assert issubclass(ValidationError, ValueError)


@pytest.mark.parametrize("bad", ["app:1:2", "reg:5000/app:1:2", "a@b@c", "a/b:c:d"])
def test_malformed_references_still_rejected(bad):
    with pytest.raises(ValidationError):
        validate_image_reference(bad)
