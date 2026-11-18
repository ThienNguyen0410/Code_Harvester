"""Generate functional test-case specifications from a structured requirement."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FieldConstraint:
    name: str
    min_length: int | None = None
    max_length: int | None = None
    provenance: str = "explicit_requirement"


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    source: str
    functionality: str
    action: str
    fields: tuple[FieldConstraint, ...]
    unique_field: str | None = None
    reject_outcome: str | None = None
    create_outcome: str | None = None
    created_state: str | None = None
    duplicate_outcome: str | None = None
    provenance: str = "explicit_requirement"


SAMPLE_REQUIREMENT = Requirement(
    requirement_id="REQ-001",
    source=(
        "The system shall allow users to register an account using a username "
        "and password. The username must contain between 3 and 20 characters. "
        "The password must contain at least 8 characters. If the username "
        "already exists, the system shall reject the registration. Otherwise, "
        "the system shall create a new account."
    ),
    functionality="User Registration",
    action="register",
    fields=(
        FieldConstraint("username", min_length=3, max_length=20),
        FieldConstraint("password", min_length=8),
    ),
    unique_field="username",
    reject_outcome="Reject registration",
    create_outcome="Create a new account",
    created_state="A new account is created",
    duplicate_outcome="Reject registration",
)


def _valid_length(constraint: FieldConstraint) -> int:
    if constraint.min_length is not None:
        return constraint.min_length
    if constraint.max_length is not None:
        return constraint.max_length
    raise ValueError(f"No length constraint is defined for '{constraint.name}'.")


def _value_of_length(field_name: str, length: int) -> str:
    character = "p" if "password" in field_name.lower() else "u"
    return character * length


def _boundary_lengths(constraint: FieldConstraint) -> list[int]:
    candidates: list[int] = []
    if constraint.min_length is not None:
        candidates.extend((constraint.min_length - 1, constraint.min_length))
    if constraint.max_length is not None:
        candidates.extend((constraint.max_length, constraint.max_length + 1))

    return list(dict.fromkeys(length for length in candidates if length >= 0))


def _make_case(
    requirement: Requirement,
    sequence: int,
    behavior_id: str,
    scenario: str,
    arguments: dict[str, str],
    preconditions: list[str],
    expected_behaviors: list[dict[str, str]],
    techniques: list[str],
    status: str = "generated",
) -> dict[str, Any]:
    return {
        "test_case_id": f"TC-{sequence:03d}",
        "requirement_id": requirement.requirement_id,
        "behavior_id": behavior_id,
        "scenario": scenario,
        "preconditions": preconditions,
        "action": {
            "function": requirement.action,
            "arguments": arguments,
        },
        "expected_behaviors": expected_behaviors,
        "testing_technique": techniques,
        "status": status,
    }


def generate_test_cases(requirement: Requirement) -> dict[str, Any]:
    """Generate boundary, duplicate-user, and successful-registration cases."""
    cases: list[dict[str, Any]] = []
    clarifications: list[str] = []

    if requirement.provenance not in {"explicit_requirement", "approved_specification"}:
        clarifications.append(
            "The expected outcomes are not supported by an explicit requirement "
            "or approved specification."
        )
        return _result(requirement, cases, clarifications)

    supported_fields = [
        field
        for field in requirement.fields
        if field.provenance in {"explicit_requirement", "approved_specification"}
        and (field.min_length is not None or field.max_length is not None)
    ]
    for field in requirement.fields:
        if field not in supported_fields:
            if field.provenance not in {
                "explicit_requirement",
                "approved_specification",
            }:
                clarifications.append(
                    f"Constraint for '{field.name}' is not approved; its "
                    "boundaries were not used."
                )
            elif field.min_length is None and field.max_length is None:
                clarifications.append(
                    f"No length constraint is specified for '{field.name}'; "
                    "no boundary values were generated."
                )

    if not supported_fields:
        clarifications.append("No approved field constraints are available.")
        return _result(requirement, cases, clarifications)

    base_arguments = {
        field.name: _value_of_length(field.name, _valid_length(field))
        for field in supported_fields
    }

    sequence = 1
    for field_index, field in enumerate(supported_fields, start=1):
        behavior_id = f"B-{field_index:03d}"
        for length in _boundary_lengths(field):
            arguments = dict(base_arguments)
            arguments[field.name] = _value_of_length(field.name, length)
            is_valid = (
                (field.min_length is None or length >= field.min_length)
                and (field.max_length is None or length <= field.max_length)
            )
            preconditions = (
                [f"'{requirement.unique_field}' does not already exist."]
                if requirement.unique_field is not None
                else []
            )
            if not is_valid:
                expected_behaviors = []
                if requirement.reject_outcome is not None:
                    expected_behaviors.append(
                        {"type": "result", "expected": requirement.reject_outcome}
                    )
                else:
                    clarifications.append(
                        f"Expected behavior for invalid {field.name} values is "
                        "not specified."
                    )
                scenario = (
                    f"{field.name} length {length} is outside its specified "
                    "length constraint"
                )
            else:
                expected_behaviors = []
                if requirement.create_outcome is not None:
                    expected_behaviors.append(
                        {"type": "result", "expected": requirement.create_outcome}
                    )
                    if requirement.created_state is not None:
                        expected_behaviors.append(
                            {
                                "type": "state",
                                "expected": requirement.created_state,
                            }
                        )
                else:
                    clarifications.append(
                        f"Expected behavior for valid {field.name} values is "
                        "not specified."
                    )
                scenario = (
                    f"{field.name} length {length} is on a specified boundary "
                    "and all inputs are valid"
                )

            cases.append(
                _make_case(
                    requirement,
                    sequence,
                    behavior_id,
                    scenario,
                    arguments,
                    preconditions,
                    expected_behaviors,
                    ["EP", "BVA"],
                    "generated" if expected_behaviors else "needs_clarification",
                )
            )
            sequence += 1

    next_behavior_id = len(supported_fields) + 1
    duplicate_behavior_id = None
    if requirement.unique_field is not None:
        duplicate_behavior_id = f"B-{next_behavior_id:03d}"
        next_behavior_id += 1
    if requirement.unique_field is not None and requirement.duplicate_outcome is not None:
        unique_constraint = next(
            (field for field in supported_fields if field.name == requirement.unique_field),
            None,
        )
        if unique_constraint is None:
            clarifications.append(
                f"Uniqueness condition references unknown or unapproved field "
                f"'{requirement.unique_field}'."
            )
        else:
            duplicate_arguments = dict(base_arguments)
            duplicate_arguments[requirement.unique_field] = _value_of_length(
                requirement.unique_field, _valid_length(unique_constraint)
            )
            cases.append(
                _make_case(
                    requirement,
                    sequence,
                    duplicate_behavior_id,
                    f"{requirement.unique_field} already exists",
                    duplicate_arguments,
                    [f"'{requirement.unique_field}' already exists."],
                    [
                        {
                            "type": "result",
                            "expected": requirement.duplicate_outcome,
                        }
                    ],
                    ["Decision Table"],
                )
            )
            sequence += 1
    elif requirement.unique_field is not None:
        clarifications.append(
            f"Expected behavior when '{requirement.unique_field}' already exists "
            "is not specified."
        )

    if requirement.create_outcome is not None:
        preconditions = []
        if requirement.unique_field is not None:
            preconditions.append(
                f"'{requirement.unique_field}' does not already exist."
            )
        expected_behaviors = [
            {"type": "result", "expected": requirement.create_outcome}
        ]
        if requirement.created_state is not None:
            expected_behaviors.append(
                {"type": "state", "expected": requirement.created_state}
            )
        cases.append(
            _make_case(
                requirement,
                sequence,
                f"B-{next_behavior_id:03d}",
                "All specified inputs are valid"
                + (
                    f" and '{requirement.unique_field}' does not already exist"
                    if requirement.unique_field is not None
                    else ""
                ),
                dict(base_arguments),
                preconditions,
                expected_behaviors,
                ["Decision Table", "State Verification"],
            )
        )
    else:
        clarifications.append(
            "Expected behavior when all specified inputs are valid is not specified."
        )

    return _result(requirement, cases, clarifications)


def _result(
    requirement: Requirement,
    cases: list[dict[str, Any]],
    clarifications: list[str],
) -> dict[str, Any]:
    supported_fields = [
        field
        for field in requirement.fields
        if field.provenance in {"explicit_requirement", "approved_specification"}
        and (field.min_length is not None or field.max_length is not None)
    ]
    analysis = {
        "requirement_id": requirement.requirement_id,
        "functionality": requirement.functionality,
        "behaviors": [
            {
                "behavior_id": f"B-{index:03d}",
                "description": (
                    f"Validate the {field.name} length constraint"
                ),
                "testing_technique": ["EP", "BVA"],
            }
            for index, field in enumerate(supported_fields, start=1)
        ],
    }
    next_behavior_id = len(supported_fields) + 1
    if requirement.unique_field is not None:
        analysis["behaviors"].append(
            {
                "behavior_id": f"B-{next_behavior_id:03d}",
                "description": (
                    f"Handle an existing {requirement.unique_field}"
                ),
                "testing_technique": ["Decision Table"],
            }
        )
        next_behavior_id += 1
    if requirement.create_outcome is not None:
        analysis["behaviors"].append(
            {
                "behavior_id": f"B-{next_behavior_id:03d}",
                "description": "Handle valid inputs",
                "testing_technique": ["Decision Table", "State Verification"],
            }
        )
    return {
        "requirement": asdict(requirement),
        "analysis": analysis,
        "test_cases": cases,
        "validation": validate_test_cases(requirement, cases, clarifications),
        "clarifications": clarifications,
    }


def validate_test_cases(
    requirement: Requirement,
    cases: list[dict[str, Any]],
    clarifications: list[str] | None = None,
) -> dict[str, Any]:
    """Check traceability, unique IDs, expected-result provenance, and BVA coverage."""
    issues: list[str] = []
    ids = [case.get("test_case_id") for case in cases]
    if len(ids) != len(set(ids)):
        issues.append("Test case IDs must be unique.")

    supported_outcomes = {
        requirement.reject_outcome,
        requirement.create_outcome,
        requirement.created_state,
        requirement.duplicate_outcome,
    }
    supported_outcomes.discard(None)
    for case in cases:
        if case.get("requirement_id") != requirement.requirement_id:
            issues.append(
                f"{case.get('test_case_id', '<unknown>')} has no valid requirement reference."
            )
        for behavior in case.get("expected_behaviors", []):
            if behavior.get("expected") not in supported_outcomes:
                issues.append(
                    f"{case.get('test_case_id', '<unknown>')} has an unsupported "
                    "expected behavior."
                )
        if not case.get("expected_behaviors"):
            issues.append(
                f"{case.get('test_case_id', '<unknown>')} has no specified "
                "expected behavior."
            )

    for field in requirement.fields:
        if field.provenance not in {"explicit_requirement", "approved_specification"}:
            continue
        expected_lengths = set(_boundary_lengths(field))
        actual_lengths = {
            len(case["action"]["arguments"][field.name])
            for case in cases
            if field.name in case.get("action", {}).get("arguments", {})
            and case.get("behavior_id") == f"B-{requirement.fields.index(field) + 1:03d}"
        }
        missing = expected_lengths - actual_lengths
        if missing:
            issues.append(
                f"Boundary coverage for '{field.name}' is missing lengths "
                f"{sorted(missing)}."
            )

    for clarification in clarifications or []:
        issues.append(f"NEEDS_CLARIFICATION: {clarification}")
    return {"passed": not issues, "issues": issues}


def main() -> None:
    result = generate_test_cases(SAMPLE_REQUIREMENT)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["validation"]["passed"]:
        raise SystemExit("Generated test cases did not pass validation.")


if __name__ == "__main__":
    main()
