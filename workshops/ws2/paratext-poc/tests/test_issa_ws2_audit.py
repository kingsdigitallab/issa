from paratext.projects import audit_project

from issa_ws2 import PROJECT


def test_project_is_consistent():
    problems = audit_project(PROJECT)
    assert not problems, "; ".join(problems)
