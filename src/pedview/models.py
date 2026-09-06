from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationMessage:
    severity: str
    code: str
    message: str
    family_id: str | None = None
    person_id: str | None = None
    line_number: int | None = None

    def format_for_cli(self) -> str:
        location_parts: list[str] = []
        if self.line_number is not None:
            location_parts.append(f"line {self.line_number}")
        if self.family_id:
            location_parts.append(f"family={self.family_id}")
        if self.person_id:
            location_parts.append(f"id={self.person_id}")
        location = f" ({', '.join(location_parts)})" if location_parts else ""
        return f"[{self.severity.upper()}] {self.message}{location}"


@dataclass
class Person:
    family_id: str
    person_id: str
    father_id: str | None
    mother_id: str | None
    sex: str
    raw_sex: str
    affected: str = "unknown"
    proband: bool = False
    deceased: bool = False
    carrier: bool = False
    age: str | None = None
    genotype: str | None = None
    variant_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    line_number: int | None = None

    @property
    def display_name(self) -> str:
        return self.person_id


@dataclass(frozen=True)
class Relationship:
    family_id: str
    relationship_id: str
    father_id: str | None
    mother_id: str | None
    child_ids: tuple[str, ...]
    kind: str = "biological"

    @property
    def parent_ids(self) -> tuple[str, ...]:
        return tuple(
            parent_id
            for parent_id in (self.father_id, self.mother_id)
            if parent_id is not None
        )


@dataclass
class Family:
    family_id: str
    members: dict[str, Person] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    generation_map: dict[str, int] = field(default_factory=dict)

    def add_person(self, person: Person) -> None:
        self.members[person.person_id] = person
        self.order.append(person.person_id)
        self.relationships.clear()
        self.generation_map.clear()

    def people(self) -> list[Person]:
        return [self.members[person_id] for person_id in self.order]

    def order_index(self) -> dict[str, int]:
        return {person_id: index for index, person_id in enumerate(self.order)}

    def rebuild_relationships(self) -> None:
        order_index = self.order_index()
        children_by_parent_pair: dict[tuple[str | None, str | None], list[str]] = {}

        for person_id in self.order:
            person = self.members[person_id]
            father_id = person.father_id if person.father_id in self.members else None
            mother_id = person.mother_id if person.mother_id in self.members else None
            if father_id is None and mother_id is None:
                continue
            children_by_parent_pair.setdefault((father_id, mother_id), []).append(
                person.person_id
            )

        self.relationships = [
            Relationship(
                family_id=self.family_id,
                relationship_id=f"{self.family_id}::rel::{index}",
                father_id=father_id,
                mother_id=mother_id,
                child_ids=tuple(
                    sorted(child_ids, key=lambda child_id: order_index[child_id])
                ),
            )
            for index, ((father_id, mother_id), child_ids) in enumerate(
                children_by_parent_pair.items(),
                start=1,
            )
        ]
        self.generation_map.clear()

    def ensure_relationships(self) -> None:
        if not self.relationships and self.members:
            self.rebuild_relationships()


@dataclass
class Pedigree:
    families: dict[str, Family]
    source_path: str
    messages: list[ValidationMessage] = field(default_factory=list)

    def people_count(self) -> int:
        return sum(len(family.members) for family in self.families.values())

    def family_count(self) -> int:
        return len(self.families)
