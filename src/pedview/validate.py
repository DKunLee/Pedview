from __future__ import annotations

from dataclasses import dataclass

from .layout import assign_generations
from .models import Family, Pedigree, ValidationMessage
from .parser import MISSING_TOKENS

VALID_SEX_VALUES = {
    "",
    "0",
    "1",
    "2",
    ".",
    "na",
    "n/a",
    "m",
    "f",
    "male",
    "female",
    "unknown",
    "u",
}


@dataclass(frozen=True)
class FamilySummary:
    family_id: str
    people_count: int
    founders_count: int
    relationship_count: int
    generation_count: int


def validate_pedigree(pedigree: Pedigree) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    for family in pedigree.families.values():
        messages.extend(validate_family(family))
    return messages


def validate_family(family: Family) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    for person in family.people():
        raw_sex = person.raw_sex.strip().lower()
        if raw_sex not in VALID_SEX_VALUES:
            messages.append(
                ValidationMessage(
                    severity="warning",
                    code="invalid_sex",
                    message=f"Unrecognized sex value '{person.raw_sex}' treated as unknown.",
                    family_id=family.family_id,
                    person_id=person.person_id,
                    line_number=person.line_number,
                )
            )

        if person.father_id and person.father_id == person.mother_id:
            messages.append(
                ValidationMessage(
                    severity="error",
                    code="duplicate_parent_reference",
                    message="Father ID and mother ID refer to the same individual.",
                    family_id=family.family_id,
                    person_id=person.person_id,
                    line_number=person.line_number,
                )
            )

        for parent_id, role in (
            (person.father_id, "father"),
            (person.mother_id, "mother"),
        ):
            if parent_id and parent_id not in family.members:
                messages.append(
                    ValidationMessage(
                        severity="error",
                        code="missing_parent",
                        message=f"Referenced {role} '{parent_id}' does not exist in family.",
                        family_id=family.family_id,
                        person_id=person.person_id,
                        line_number=person.line_number,
                    )
                )

        if person.father_id and person.father_id in family.members:
            father = family.members[person.father_id]
            if father.sex == "female":
                messages.append(
                    ValidationMessage(
                        severity="warning",
                        code="father_sex_mismatch",
                        message="Referenced father is marked as female.",
                        family_id=family.family_id,
                        person_id=person.person_id,
                        line_number=person.line_number,
                    )
                )
        if person.mother_id and person.mother_id in family.members:
            mother = family.members[person.mother_id]
            if mother.sex == "male":
                messages.append(
                    ValidationMessage(
                        severity="warning",
                        code="mother_sex_mismatch",
                        message="Referenced mother is marked as male.",
                        family_id=family.family_id,
                        person_id=person.person_id,
                        line_number=person.line_number,
                    )
                )

    try:
        assign_generations(family)
    except ValueError:
        messages.append(
            ValidationMessage(
                severity="error",
                code="cycle",
                message="Family contains a relationship cycle and cannot be laid out.",
                family_id=family.family_id,
            )
        )
    return messages


def summarize_pedigree(pedigree: Pedigree) -> list[FamilySummary]:
    summaries: list[FamilySummary] = []
    for family in pedigree.families.values():
        relationship_count = sum(
            1
            for person in family.people()
            for parent_id in (person.father_id, person.mother_id)
            if parent_id and parent_id.lower() not in MISSING_TOKENS
        )
        founders_count = sum(
            1
            for person in family.people()
            if not person.father_id and not person.mother_id
        )
        try:
            generation_count = max(assign_generations(family).values(), default=0) + 1
        except ValueError:
            generation_count = 0
        summaries.append(
            FamilySummary(
                family_id=family.family_id,
                people_count=len(family.members),
                founders_count=founders_count,
                relationship_count=relationship_count,
                generation_count=generation_count,
            )
        )
    return summaries
