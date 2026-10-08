#!/usr/bin/env python3
"""Validate executable parity cases for remote scoring tools and blood calculations."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TOLERANCE = 1e-6


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object.")
    return value


def truth(inputs: dict[str, Any], criterion_id: str) -> bool:
    return inputs.get(criterion_id) is True


def criterion_score(criterion: dict[str, Any], value: Any) -> float:
    input_type = criterion["inputType"]
    if input_type == "boolean":
        return float(criterion["scoreWhenTrue"]) if value is True else 0.0
    if input_type == "choice":
        for choice in criterion["choices"]:
            if choice["id"] == value:
                return float(choice["score"])
        raise ValueError(
            f"Unknown choice {value!r} for criterion {criterion['id']}."
        )
    if input_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(
                f"Criterion {criterion['id']} requires a number."
            )
        for rule in criterion["rules"]:
            if matches_numeric_rule(float(value), rule):
                return float(rule["score"])
        return 0.0
    raise ValueError(f"Unsupported input type: {input_type!r}.")


def matches_numeric_rule(value: float, rule: dict[str, Any]) -> bool:
    operator = rule["operator"]
    threshold = float(rule["value"])
    upper = rule.get("upperValue")
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "=":
        return value == threshold
    if operator == ">=":
        return value >= threshold
    if operator == ">":
        return value > threshold
    if operator == "between":
        if upper is None:
            raise ValueError(f"Rule {rule['id']} has no upperValue.")
        return threshold <= value <= float(upper)
    raise ValueError(f"Unsupported operator: {operator!r}.")


def result_for_score(
    definition: dict[str, Any],
    score: float,
    bands: list[dict[str, Any]],
) -> dict[str, Any]:
    for result in bands:
        if (
            float(result["minimumScore"])
            <= score
            <= float(result["maximumScore"])
        ):
            return result
    raise ValueError(
        f"No result band in {definition['id']} contains score {score}."
    )


def active_alternate_mode(
    definition: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any] | None:
    """Mirror the app: the first mode whose criteria are all optional and omitted."""
    omitted = {
        criterion["id"]
        for criterion in definition["criteria"]
        if criterion.get("required", True) is False
        and criterion["id"] not in inputs
    }
    for mode in definition.get("alternateModes", []):
        trigger = mode["whenOmittedCriterionIds"]
        if trigger and all(criterion_id in omitted for criterion_id in trigger):
            return mode
    return None


def criterion_is_active(
    criterion: dict[str, Any],
    inputs: dict[str, Any],
) -> bool:
    """Whether a conditional criterion's `activeWhen` currently holds.

    Declared in the content rather than hardcoded here, so a second tool with
    mutually exclusive criteria needs no tooling or app change. NEWS2's SpO2
    Scale 1/Scale 2 rows are the first user.
    """
    active_when = criterion.get("activeWhen")
    if not isinstance(active_when, dict):
        return True
    return inputs.get(active_when["criterionId"]) == active_when["equalsChoiceId"]


def filter_by_active_when(
    criterion_ids: list[str],
    criteria: dict[str, Any],
    inputs: dict[str, Any],
) -> list[str]:
    """Drop criteria whose `activeWhen` does not hold for these inputs."""
    return [
        criterion_id
        for criterion_id in criterion_ids
        if criterion_id not in criteria
        or criterion_is_active(criteria[criterion_id], inputs)
    ]


def matching_escalation(
    definition: dict[str, Any],
    selected_result_id: str,
    highest_criterion_score: float,
) -> dict[str, Any] | None:
    """Mirror the app: the first escalation (array order) that applies.

    An escalation applies when the band selected by score is one of its
    ``fromResultIds`` and any single scored criterion contributed at least
    ``whenAnyCriterionScoresAtLeast``.
    """
    for escalation in definition.get("escalations", []):
        if selected_result_id in escalation["fromResultIds"] and (
            highest_criterion_score
            >= float(escalation["whenAnyCriterionScoresAtLeast"])
        ):
            return escalation
    return None


def escalation_target_id(
    definition: dict[str, Any],
    bands: list[dict[str, Any]],
    escalation: dict[str, Any],
) -> str:
    """Check toResultId names one of the active bands or the tool's results."""
    target = escalation["toResultId"]
    known = [*bands, *definition["results"]]
    if not any(result["id"] == target for result in known):
        raise ValueError(
            f"{definition['id']}: escalation {escalation['id']!r} refers to "
            f"unknown result {target!r}."
        )
    return target


def evaluate_scoring(
    definition: dict[str, Any],
    inputs: dict[str, Any],
) -> tuple[float, str]:
    criteria = {
        criterion["id"]: criterion for criterion in definition["criteria"]
    }
    evaluation = definition["evaluation"]
    kind = evaluation["kind"]
    alternate_mode = active_alternate_mode(definition, inputs)
    bands = alternate_mode["results"] if alternate_mode else definition["results"]

    def result_id_for(result_id: str, score: float) -> str:
        if alternate_mode is None:
            if not any(result["id"] == result_id for result in definition["results"]):
                raise ValueError(
                    f"{definition['id']} refers to unknown result {result_id!r}."
                )
            return result_id
        return result_for_score(definition, score, bands)["id"]

    if kind == "none":
        raise ValueError(
            f"{definition['id']} is a pathway reference, not a calculator."
        )

    if kind == "required-sum":
        required = evaluation["requiredTrue"]
        if not all(truth(inputs, criterion_id) for criterion_id in required):
            failure_result = evaluation["failureResultId"]
            failure_score = evaluation["failureScore"]
            if failure_result is None or failure_score is None:
                raise ValueError(
                    f"{definition['id']} has incomplete required-sum failure metadata."
                )
            return float(failure_score), result_id_for(
                str(failure_result), float(failure_score)
            )

    if kind in {"sum", "required-sum"}:
        criterion_ids = filter_by_active_when(
            evaluation["scoreCriteria"] or list(criteria), criteria, inputs
        )
        score = 0.0
        highest_criterion_score = -math.inf
        for criterion_id in criterion_ids:
            if criterion_id not in criteria:
                raise ValueError(
                    f"{definition['id']} evaluation refers to unknown "
                    f"criterion {criterion_id!r}."
                )
            criterion = criteria[criterion_id]
            if criterion_id not in inputs:
                # The app refuses to score a missing required answer.
                if criterion.get("required", True) is False:
                    continue
                raise ValueError(
                    f"{criterion_id} requires an answer before scoring."
                )
            contribution = criterion_score(criterion, inputs[criterion_id])
            score += contribution
            highest_criterion_score = max(highest_criterion_score, contribution)
        result_id = result_for_score(definition, score, bands)["id"]
        escalation = matching_escalation(
            definition, result_id, highest_criterion_score
        )
        if escalation is not None:
            result_id = escalation_target_id(definition, bands, escalation)
        return score, result_id

    if kind == "group-count":
        score = 0.0
        for group in evaluation["groups"]:
            all_true = all(
                truth(inputs, criterion_id)
                for criterion_id in group["allTrue"]
            )
            any_true = (
                not group["anyTrue"]
                or any(
                    truth(inputs, criterion_id)
                    for criterion_id in group["anyTrue"]
                )
            )
            if all_true and any_true:
                score += 1.0
        return score, result_for_score(definition, score, bands)["id"]

    if kind == "decision":
        for rule in evaluation["decisionRules"]:
            if decision_rule_matches(rule, inputs):
                if rule["resultId"] is None:
                    raise ValueError(
                        f"{definition['id']}: decision rule {rule['id']} has no result ID."
                    )
                return float(rule["score"]), result_id_for(
                    str(rule["resultId"]), float(rule["score"])
                )
        raise ValueError(
            f"No decision rule matched for scoring tool {definition['id']}."
        )

    raise ValueError(f"Unsupported evaluation kind: {kind!r}.")


def decision_rule_matches(
    rule: dict[str, Any],
    inputs: dict[str, Any],
) -> bool:
    if rule["always"]:
        return True
    if rule["anyTrue"] and not any(
        truth(inputs, criterion_id) for criterion_id in rule["anyTrue"]
    ):
        return False
    if rule["allTrue"] and not all(
        truth(inputs, criterion_id) for criterion_id in rule["allTrue"]
    ):
        return False
    if rule["noneTrue"] and any(
        truth(inputs, criterion_id) for criterion_id in rule["noneTrue"]
    ):
        return False
    false_criterion = rule["falseCriterion"]
    if false_criterion is not None and truth(inputs, false_criterion):
        return False
    return True


# Mirror the app tokenizer: skip every character Dart's String.trim() treats
# as whitespace (anywhere in the expression), and only accept ASCII digits.
_WHITESPACE = (
    "\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000\ufeff"
)
_TOKEN = re.compile(
    r"[" + re.escape(_WHITESPACE) + r"]*"
    r"(?:([0-9]+(?:\.[0-9]+)?)|([A-Za-z][A-Za-z0-9]*)|(.))",
    re.DOTALL,
)
_TRAILING_WHITESPACE = re.compile(r"[" + re.escape(_WHITESPACE) + r"]+\Z")


class ExpressionParser:
    def __init__(self, expression: str, inputs: dict[str, float]) -> None:
        self.tokens: list[tuple[str, str]] = []
        expression = _TRAILING_WHITESPACE.sub("", expression)
        for number, identifier, symbol in _TOKEN.findall(expression):
            if number:
                self.tokens.append(("number", number))
            elif identifier:
                self.tokens.append(("identifier", identifier))
            elif symbol in "+-*/()":
                self.tokens.append((symbol, symbol))
            else:
                raise ValueError(f"Unsupported expression token: {symbol!r}.")
        self.position = 0
        self.inputs = inputs

    def parse(self) -> float:
        value = self._expression()
        if self.position != len(self.tokens):
            raise ValueError("Unexpected trailing expression tokens.")
        return value

    def _expression(self) -> float:
        value = self._term()
        while self._peek("+") or self._peek("-"):
            operator = self._take()[0]
            right = self._term()
            value = value + right if operator == "+" else value - right
        return value

    def _term(self) -> float:
        value = self._factor()
        while self._peek("*") or self._peek("/"):
            operator = self._take()[0]
            right = self._factor()
            value = value * right if operator == "*" else value / right
        return value

    def _factor(self) -> float:
        if self._peek("-"):
            self._take()
            return -self._factor()
        if self._peek("+"):
            self._take()
            return self._factor()
        if self._peek("("):
            self._take()
            value = self._expression()
            self._expect(")")
            return value
        token_type, token_value = self._take()
        if token_type == "number":
            return float(token_value)
        if token_type == "identifier":
            if token_value not in self.inputs:
                raise ValueError(
                    f"No value supplied for expression input {token_value!r}."
                )
            return float(self.inputs[token_value])
        raise ValueError(f"Expected number, identifier or parenthesis.")

    def _peek(self, token_type: str) -> bool:
        return (
            self.position < len(self.tokens)
            and self.tokens[self.position][0] == token_type
        )

    def _take(self) -> tuple[str, str]:
        if self.position >= len(self.tokens):
            raise ValueError("Unexpected end of expression.")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def _expect(self, token_type: str) -> None:
        if not self._peek(token_type):
            raise ValueError(f"Expected {token_type!r}.")
        self._take()


def acid_base_pattern(
    inputs: dict[str, float],
    parameters: dict[str, float],
) -> str:
    ph = float(inputs["ph"])
    co2 = float(inputs["pco2"])
    hco3 = float(inputs["bicarbonate"])

    low_ph = float(parameters["lowPh"])
    high_ph = float(parameters["highPh"])
    low_co2 = float(parameters["lowPco2"])
    high_co2 = float(parameters["highPco2"])
    low_hco3 = float(parameters["lowBicarbonate"])
    high_hco3 = float(parameters["highBicarbonate"])

    acidotic = ph < low_ph
    alkalotic = ph > high_ph
    high_co2_value = co2 > high_co2
    low_co2_value = co2 < low_co2
    high_hco3_value = hco3 > high_hco3
    low_hco3_value = hco3 < low_hco3

    if acidotic and high_co2_value and not low_hco3_value:
        return (
            "respiratory-acidosis-with-raised-bicarbonate"
            if high_hco3_value
            else "primary-respiratory-acidosis"
        )
    if acidotic and low_hco3_value and not high_co2_value:
        return (
            "metabolic-acidosis-with-respiratory-compensation"
            if low_co2_value
            else "primary-metabolic-acidosis"
        )
    if acidotic and high_co2_value and low_hco3_value:
        return "mixed-respiratory-metabolic-acidosis"
    if alkalotic and low_co2_value and not high_hco3_value:
        return (
            "respiratory-alkalosis-with-reduced-bicarbonate"
            if low_hco3_value
            else "primary-respiratory-alkalosis"
        )
    if alkalotic and high_hco3_value and not low_co2_value:
        return (
            "metabolic-alkalosis-with-respiratory-compensation"
            if high_co2_value
            else "primary-metabolic-alkalosis"
        )
    if alkalotic and low_co2_value and high_hco3_value:
        return "mixed-respiratory-metabolic-alkalosis"
    if not acidotic and not alkalotic:
        if high_co2_value and high_hco3_value:
            return "compensated-respiratory-acidosis"
        if low_co2_value and low_hco3_value:
            return "compensated-respiratory-alkalosis-or-mixed"
        return "normal"
    return "mixed-or-indeterminate"


def round_like_dart(value: float, precision: int) -> float:
    """Mirror the app: (value * 10^p).roundToDouble() / 10^p.

    Dart's roundToDouble() rounds half away from zero on the scaled value,
    unlike Python's round(), which is round-half-even on the exact binary value.
    """
    factor = float(10**precision)
    scaled = value * factor
    if not math.isfinite(scaled):
        return scaled / factor
    rounded = math.floor(abs(scaled))
    if abs(scaled) - rounded >= 0.5:
        rounded += 1
    return math.copysign(rounded, scaled) / factor


def evaluate_calculation(
    calculation: dict[str, Any],
    inputs: dict[str, Any],
) -> tuple[float | None, str | None]:
    numeric_inputs = {
        key: float(value) for key, value in inputs.items()
    }
    engine = calculation["engine"]
    kind = engine["kind"]
    if kind == "expression":
        expression = engine["expression"]
        if not isinstance(expression, str):
            raise ValueError(
                f"Calculation {calculation['id']} has no expression."
            )
        value = ExpressionParser(expression, numeric_inputs).parse()
        precision = engine["precision"]
        if precision is not None:
            value = round_like_dart(value, int(precision))
        return value, None
    if kind == "acid-base-basic":
        code = acid_base_pattern(
            numeric_inputs,
            {
                key: float(value)
                for key, value in engine["parameters"].items()
            },
        )
        return None, engine.get("textResults", {}).get(code, code)
    if kind == "aki-creatinine-stage":
        parameters = engine.get("parameters", {})
        baseline = numeric_inputs["baselineCreatinine"]
        current = numeric_inputs["currentCreatinine"]
        interval_hours = numeric_inputs["intervalHours"]
        if baseline <= 0:
            raise ValueError("Baseline creatinine must be greater than zero.")

        ratio = current / baseline
        rise = current - baseline
        stage1_ratio = float(parameters.get("stage1Ratio", 1.5))
        stage2_ratio = float(parameters.get("stage2Ratio", 2.0))
        stage3_ratio = float(parameters.get("stage3Ratio", 3.0))
        absolute_rise = float(parameters.get("absoluteRise", 26.0))
        absolute_window = float(parameters.get("absoluteRiseWindowHours", 48.0))
        stage3_creatinine = float(parameters.get("stage3Creatinine", 354.0))

        if ratio >= stage3_ratio or (
            current >= stage3_creatinine and ratio >= stage1_ratio
        ):
            code = "aki-stage-3"
        elif ratio >= stage2_ratio:
            code = "aki-stage-2"
        elif ratio >= stage1_ratio or (
            interval_hours <= absolute_window and rise >= absolute_rise
        ):
            code = "aki-stage-1"
        else:
            code = "no-aki"

        return None, engine.get("textResults", {}).get(code, code)
    raise ValueError(
        f"Calculation {calculation['id']} has unsupported engine {kind!r}."
    )


def main() -> None:
    errors: list[str] = []
    calculator_count = 0
    scoring_case_count = 0
    pathway_count = 0
    calculation_count = 0
    calculation_case_count = 0

    scoring_directory = ROOT / "scoring_tools"
    blood_directory = ROOT / "blood_panels"

    if not scoring_directory.is_dir():
        errors.append(f"Missing scoring-tools directory: {scoring_directory}")
    if not blood_directory.is_dir():
        errors.append(f"Missing blood-panels directory: {blood_directory}")

    for path in sorted(scoring_directory.glob("*.json")):
        definition = load_json(path)
        mode = definition.get("mode")
        if not isinstance(mode, str):
            errors.append(f"{path}: missing string field 'mode'.")
            continue

        raw_cases = definition.get("parityCases")

        if mode == "pathway-reference":
            pathway_count += 1
            if raw_cases is None:
                errors.append(
                    f"{path}: missing 'parityCases'; pathway references "
                    "must contain an empty array."
                )
            elif not isinstance(raw_cases, list):
                errors.append(f"{path}: 'parityCases' must be an array.")
            elif raw_cases:
                errors.append(
                    f"{path}: pathway-reference must not contain parity cases."
                )
            continue

        calculator_count += 1
        if raw_cases is None:
            errors.append(
                f"{path}: calculator is missing required 'parityCases'."
            )
            continue
        if not isinstance(raw_cases, list):
            errors.append(f"{path}: 'parityCases' must be an array.")
            continue
        if not raw_cases:
            errors.append(f"{path}: calculator has no parity cases.")
            continue

        for case in raw_cases:
            scoring_case_count += 1
            case_id = case.get("id", "<missing-id>") if isinstance(case, dict) else "<invalid-case>"
            if not isinstance(case, dict):
                errors.append(f"{path}: parity case must be an object.")
                continue
            try:
                score, result_id = evaluate_scoring(
                    definition,
                    case["inputs"],
                )
            except (
                KeyError,
                RecursionError,
                TypeError,
                ValueError,
                ZeroDivisionError,
            ) as exc:
                errors.append(f"{path} case {case_id}: {exc}")
                continue

            try:
                expected_score = float(case["expectedScore"])
                expected_result = case["expectedResultId"]
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(
                    f"{path} case {case_id}: invalid expected output: {exc}"
                )
                continue

            if not math.isclose(
                score,
                expected_score,
                rel_tol=0,
                abs_tol=TOLERANCE,
            ):
                errors.append(
                    f"{path} case {case_id}: expected score "
                    f"{expected_score}, received {score}."
                )
            if result_id != expected_result:
                errors.append(
                    f"{path} case {case_id}: expected result "
                    f"{expected_result!r}, received {result_id!r}."
                )

    for path in sorted(blood_directory.glob("*.json")):
        definition = load_json(path)
        calculations = definition.get("calculations")
        if calculations is None:
            errors.append(f"{path}: missing required 'calculations' array.")
            continue
        if not isinstance(calculations, list):
            errors.append(f"{path}: 'calculations' must be an array.")
            continue

        for calculation in calculations:
            if not isinstance(calculation, dict):
                errors.append(f"{path}: calculation entry must be an object.")
                continue
            calculation_id = calculation.get("id", "<missing-id>")
            calculation_count += 1
            raw_cases = calculation.get("parityCases")
            if raw_cases is None:
                errors.append(
                    f"{path} calculation {calculation_id}: missing required "
                    "'parityCases'."
                )
                continue
            if not isinstance(raw_cases, list):
                errors.append(
                    f"{path} calculation {calculation_id}: "
                    "'parityCases' must be an array."
                )
                continue
            if not raw_cases:
                errors.append(
                    f"{path} calculation {calculation_id}: "
                    "has no parity cases."
                )
                continue

            for case in raw_cases:
                calculation_case_count += 1
                case_id = case.get("id", "<missing-id>") if isinstance(case, dict) else "<invalid-case>"
                if not isinstance(case, dict):
                    errors.append(
                        f"{path} calculation {calculation_id}: "
                        "parity case must be an object."
                    )
                    continue
                try:
                    number, text = evaluate_calculation(
                        calculation,
                        case["inputs"],
                    )
                except (
                    KeyError,
                    RecursionError,
                    TypeError,
                    ValueError,
                    ZeroDivisionError,
                ) as exc:
                    errors.append(
                        f"{path} calculation {calculation_id} "
                        f"case {case_id}: {exc}"
                    )
                    continue

                expected_number = case.get("expectedNumber")
                expected_text = case.get("expectedText")
                if expected_number is not None:
                    if number is None or not math.isclose(
                        number,
                        float(expected_number),
                        rel_tol=0,
                        abs_tol=TOLERANCE,
                    ):
                        errors.append(
                            f"{path} calculation {calculation_id} "
                            f"case {case_id}: expected number "
                            f"{expected_number}, received {number}."
                        )
                elif text != expected_text:
                    errors.append(
                        f"{path} calculation {calculation_id} "
                        f"case {case_id}: expected text "
                        f"{expected_text!r}, received {text!r}."
                    )

    if errors:
        print("Remote engine parity validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(
        "Remote engine parity validation passed: "
        f"{calculator_count} calculators, {scoring_case_count} scoring cases, "
        f"{pathway_count} pathway references, {calculation_count} blood "
        f"calculations, {calculation_case_count} calculation cases."
    )


if __name__ == "__main__":
    main()
