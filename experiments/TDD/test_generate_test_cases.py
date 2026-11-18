import unittest

from generate_test_cases import (
    FieldConstraint,
    Requirement,
    SAMPLE_REQUIREMENT,
    generate_test_cases,
)


class TestFunctionalTestCaseGeneration(unittest.TestCase):
    def test_sample_requirement_generates_valid_traceable_cases(self):
        result = generate_test_cases(SAMPLE_REQUIREMENT)

        self.assertTrue(result["validation"]["passed"])
        self.assertEqual(len(result["test_cases"]), 8)
        self.assertTrue(
            all(
                case["requirement_id"] == SAMPLE_REQUIREMENT.requirement_id
                for case in result["test_cases"]
            )
        )

    def test_sample_covers_specified_boundaries_and_conditions(self):
        result = generate_test_cases(SAMPLE_REQUIREMENT)
        cases = result["test_cases"]
        username_lengths = {
            len(case["action"]["arguments"]["username"])
            for case in cases
            if case["behavior_id"] == "B-001"
        }
        password_lengths = {
            len(case["action"]["arguments"]["password"])
            for case in cases
            if case["behavior_id"] == "B-002"
        }

        self.assertEqual(username_lengths, {2, 3, 20, 21})
        self.assertEqual(password_lengths, {7, 8})
        self.assertTrue(any("already exists" in case["scenario"] for case in cases))

    def test_one_sided_constraint_does_not_invent_an_upper_boundary(self):
        requirement = Requirement(
            requirement_id="REQ-002",
            source=(
                "Password must contain at least 8 characters. Reject a password "
                "below that minimum; otherwise accept and save it."
            ),
            functionality="Password validation",
            action="set_password",
            fields=(FieldConstraint("password", min_length=8),),
            unique_field=None,
            reject_outcome="Reject password",
            create_outcome="Accept password",
            created_state="Password is saved",
        )

        result = generate_test_cases(requirement)
        lengths = {
            len(case["action"]["arguments"]["password"])
            for case in result["test_cases"]
            if case["behavior_id"] == "B-001"
        }

        self.assertEqual(lengths, {7, 8})
        self.assertFalse(
            any("already exists" in case["scenario"] for case in result["test_cases"])
        )
        self.assertTrue(result["validation"]["passed"])

    def test_missing_expected_outcomes_are_flagged_for_clarification(self):
        requirement = Requirement(
            requirement_id="REQ-004",
            source="Username must contain at least 3 characters.",
            functionality="Username validation",
            action="set_username",
            fields=(FieldConstraint("username", min_length=3),),
        )

        result = generate_test_cases(requirement)

        self.assertTrue(result["clarifications"])
        self.assertFalse(result["validation"]["passed"])
        self.assertTrue(
            all(
                not case["expected_behaviors"]
                and case["status"] == "needs_clarification"
                for case in result["test_cases"]
            )
        )

    def test_inferred_requirement_does_not_generate_unsupported_results(self):
        requirement = Requirement(
            requirement_id="REQ-003",
            source="The username must be valid.",
            functionality="User Registration",
            action="register",
            fields=(FieldConstraint("username", min_length=3),),
            provenance="inferred",
        )

        result = generate_test_cases(requirement)

        self.assertEqual(result["test_cases"], [])
        self.assertTrue(result["clarifications"])
        self.assertFalse(result["validation"]["passed"])


if __name__ == "__main__":
    unittest.main()
