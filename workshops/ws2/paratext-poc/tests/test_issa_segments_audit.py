"""Guard: issa-segments's prompt and view stay in step with its schema.

`audit_project` checks that every field the view shows exists in the schema, and
that every model_output field is named in the prompt.
"""

from paratext.projects import audit_project

from issa_segments import PROJECT


def test_project_is_consistent():
    problems = audit_project(PROJECT)
    assert not problems, "; ".join(problems)
