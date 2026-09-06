from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import Family, Pedigree, Person, ValidationMessage
from .phenotypes import affected_status_from_metadata, normalize_metadata_key
from .segregation import normalize_genotype

MISSING_TOKENS = {"", "0", ".", "-9", "na", "n/a", "none", "null"}


class PedigreeFormatError(ValueError):
    """Raised when the pedigree file cannot be parsed structurally."""


@dataclass(frozen=True)
class ColumnSchema:
    family_id: str | None
    person_id: str
    father_id: str
    mother_id: str
    sex: str | None
    metadata_columns: tuple[str, ...]


def parse_pedigree(path: str | Path) -> Pedigree:
    source_path = Path(path)
    if not source_path.exists():
        raise PedigreeFormatError(f"Input file does not exist: {source_path}")

    raw_lines = source_path.read_text(encoding="utf-8").splitlines()
    header_info = find_header(raw_lines)
    if header_info is None:
        raise PedigreeFormatError("Input file is empty.")
    header_line_number, headers, schema = header_info
    materialized_lines = [
        (line_number, cleaned_line)
        for line_number, line in enumerate(
            raw_lines[header_line_number:], start=header_line_number + 1
        )
        if (cleaned_line := strip_data_line(line))
    ]
    families: dict[str, Family] = {}
    messages: list[ValidationMessage] = []
    default_family_id = source_path.stem

    for line_number, line in materialized_lines:
        fields = split_fields(line)
        if is_redundant_header_row(fields):
            continue
        if len(fields) != len(headers):
            messages.append(
                ValidationMessage(
                    severity="error",
                    code="row_width",
                    message=(
                        f"Expected {len(headers)} columns from header, found "
                        f"{len(fields)}."
                    ),
                    line_number=line_number,
                )
            )
            continue

        row = dict(zip(headers, fields))
        family_id = (
            row[schema.family_id].strip()
            if schema.family_id is not None
            else default_family_id
        )
        person_id = row[schema.person_id].strip()
        father_id = normalize_reference(row[schema.father_id])
        mother_id = normalize_reference(row[schema.mother_id])
        raw_sex = row[schema.sex].strip() if schema.sex is not None else ""
        sex = normalize_sex(raw_sex)

        if not family_id:
            messages.append(
                ValidationMessage(
                    severity="error",
                    code="missing_family_id",
                    message="Family ID is required.",
                    line_number=line_number,
                )
            )
            continue
        if not person_id:
            messages.append(
                ValidationMessage(
                    severity="error",
                    code="missing_person_id",
                    message="Individual ID is required.",
                    family_id=family_id,
                    line_number=line_number,
                )
            )
            continue

        family = families.setdefault(family_id, Family(family_id=family_id))
        if person_id in family.members:
            messages.append(
                ValidationMessage(
                    severity="error",
                    code="duplicate_person_id",
                    message="Duplicate individual ID within family.",
                    family_id=family_id,
                    person_id=person_id,
                    line_number=line_number,
                )
            )
            continue

        metadata = {
            column_name: row[column_name].strip()
            for column_name in schema.metadata_columns
            if row[column_name].strip()
        }
        affected = affected_status_from_metadata(metadata) or "unknown"
        proband = any(
            normalize_metadata_key(k) in {"proband", "prob", "index", "index_patient"}
            and v.strip().lower() in {"1", "true", "t", "yes", "y"}
            for k, v in metadata.items()
        )
        deceased = any(
            (
                normalize_metadata_key(k) in {"deceased", "dead"}
                and v.strip().lower() in {"1", "true", "t", "yes", "y"}
            )
            or (
                normalize_metadata_key(k) in {"status", "vital_status"}
                and v.strip().lower() in {"dead", "deceased", "d"}
            )
            for k, v in metadata.items()
        )
        carrier = any(
            normalize_metadata_key(k) in {"carrier", "obligate_carrier"}
            and v.strip().lower() in {"1", "true", "t", "yes", "y"}
            for k, v in metadata.items()
        )
        age_val: str | None = None
        for k, v in metadata.items():
            if normalize_metadata_key(k) in {"age", "age_of_onset", "onset"}:
                age_val = v.strip()
                break
        gt_val: str | None = None
        variant_id: str | None = None
        for k, v in metadata.items():
            key_norm = normalize_metadata_key(k)
            if key_norm in {"genotype", "gt"}:
                gt_val = v.strip()
            elif key_norm in {
                "variant",
                "candidate_variant",
                "variant_id",
                "mutation",
                "gene",
            }:
                # If looks like a genotype (e.g. 0/1, 1/1), treat as genotype
                val_norm = normalize_genotype(v.strip())
                if val_norm in {"0/0", "0/1", "1/1", "./."}:
                    if not gt_val:
                        gt_val = v.strip()
                else:
                    variant_id = v.strip()

        gt_val = normalize_genotype(gt_val)
        if not carrier and gt_val == "0/1" and affected != "affected":
            carrier = True

        family.add_person(
            Person(
                family_id=family_id,
                person_id=person_id,
                father_id=father_id,
                mother_id=mother_id,
                sex=sex,
                raw_sex=raw_sex,
                affected=affected,
                proband=proband,
                deceased=deceased,
                carrier=carrier,
                age=age_val,
                genotype=gt_val,
                variant_id=variant_id,
                metadata=metadata,
                line_number=line_number,
            )
        )

    if not families and messages:
        raise PedigreeFormatError(
            f"Unable to parse any pedigree rows from {source_path.name}."
        )

    for family in families.values():
        family.rebuild_relationships()

    return Pedigree(families=families, source_path=str(source_path), messages=messages)


def split_fields(line: str) -> list[str]:
    return re.split(r"\s+", line.strip())


def strip_data_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""
    return re.sub(r"\s+#.*$", "", stripped).strip()


def header_candidates(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []
    if stripped.startswith("#"):
        candidate = re.sub(r"^\s*#+\s*", "", line).strip()
        candidate = re.sub(r"\s+#.*$", "", candidate).strip()
        candidate = re.sub(
            r"^(columns|fields|header)\s*:\s*", "", candidate, flags=re.IGNORECASE
        ).strip()
        return [candidate] if candidate else []
    candidate = strip_data_line(line)
    return [candidate] if candidate else []


def find_header(raw_lines: list[str]) -> tuple[int, list[str], ColumnSchema] | None:
    saw_nonempty = False
    first_data_line: tuple[int, list[str]] | None = None

    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        saw_nonempty = True
        for candidate in header_candidates(line):
            headers = split_fields(candidate)
            try:
                schema = resolve_schema(headers)
                return line_number, headers, schema
            except PedigreeFormatError:
                continue
        cleaned = strip_data_line(line)
        if first_data_line is None and cleaned:
            first_data_line = (line_number, split_fields(cleaned))

    if not saw_nonempty:
        return None

    # If no explicit header row was recognized, infer standard PLINK format
    if first_data_line is not None:
        fields = first_data_line[1]
        col_count = len(fields)
        if col_count >= 4:
            base_headers = ["famid", "id", "fid", "mid"]
            sex_header: str | None = None
            meta_cols: list[str] = []
            if col_count >= 5:
                base_headers.append("sex")
                sex_header = "sex"
            if col_count >= 6:
                base_headers.append("affected")
                meta_cols.append("affected")
            if col_count > 6:
                for idx in range(7, col_count + 1):
                    col_name = f"col_{idx}"
                    base_headers.append(col_name)
                    meta_cols.append(col_name)

            schema = ColumnSchema(
                family_id="famid",
                person_id="id",
                father_id="fid",
                mother_id="mid",
                sex=sex_header,
                metadata_columns=tuple(meta_cols),
            )
            # line_number 0 indicates there is no header row to skip
            return 0, base_headers, schema

    raise PedigreeFormatError(
        "Missing required header(s): individual ID, father ID, mother ID."
    )


def is_redundant_header_row(fields: list[str]) -> bool:
    try:
        resolve_schema(fields)
    except PedigreeFormatError:
        return False
    return True


def resolve_schema(headers: list[str]) -> ColumnSchema:
    normalized_lookup: dict[str, str] = {}
    for header in headers:
        normalized = normalize_header(header)
        if normalized in normalized_lookup:
            raise PedigreeFormatError(f"Duplicate header detected: {header}")
        normalized_lookup[normalized] = header

    family_header = resolve_family_header(normalized_lookup)
    person_header = resolve_first(
        normalized_lookup,
        (
            "id",
            "iid",
            "animal",
            "indiv",
            "individ",
            "individual",
            "individual_id",
            "individualid",
            "person_id",
            "personid",
            "sample_id",
            "sampleid",
        ),
    )
    father_header = resolve_parent_header(
        normalized_lookup,
        preferred_aliases=(
            "fid",
            "pat",
            "pid",
            "father_id",
            "fatherid",
            "father",
            "sire",
        ),
        occupied_header=family_header,
    )
    mother_header = resolve_first(
        normalized_lookup,
        ("mid", "mat", "mother_id", "motherid", "mother", "dam"),
    )
    sex_header = resolve_first(normalized_lookup, ("sex", "gender"))

    missing: list[str] = []
    if person_header is None:
        missing.append("individual ID")
    if father_header is None:
        missing.append("father ID")
    if mother_header is None:
        missing.append("mother ID")
    if missing:
        raise PedigreeFormatError(
            "Missing required header(s): " + ", ".join(missing) + "."
        )

    required_headers = {person_header, father_header, mother_header}
    if family_header is not None:
        required_headers.add(family_header)
    if sex_header is not None:
        required_headers.add(sex_header)
    metadata_columns = tuple(
        header_name for header_name in headers if header_name not in required_headers
    )
    return ColumnSchema(
        family_id=family_header,
        person_id=person_header,
        father_id=father_header,
        mother_id=mother_header,
        sex=sex_header,
        metadata_columns=metadata_columns,
    )


def resolve_family_header(normalized_lookup: dict[str, str]) -> str | None:
    direct = resolve_first(
        normalized_lookup,
        ("famid", "family_id", "family", "familyid", "pedigree", "pedigree_id"),
    )
    if direct is not None:
        return direct

    # PLINK-like headers often use FID for family ID and PAT/PID for father ID.
    if "fid" in normalized_lookup and (
        "iid" in normalized_lookup
        or "pat" in normalized_lookup
        or "pid" in normalized_lookup
    ):
        return normalized_lookup["fid"]
    return None


def resolve_parent_header(
    normalized_lookup: dict[str, str],
    preferred_aliases: tuple[str, ...],
    occupied_header: str | None,
) -> str | None:
    for alias in preferred_aliases:
        header_name = normalized_lookup.get(alias)
        if header_name is not None and header_name != occupied_header:
            return header_name
    return None


def resolve_first(
    normalized_lookup: dict[str, str],
    aliases: tuple[str, ...],
) -> str | None:
    for alias in aliases:
        header_name = normalized_lookup.get(alias)
        if header_name is not None:
            return header_name
    return None


def normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def normalize_reference(value: str) -> str | None:
    stripped = value.strip()
    if stripped.lower() in MISSING_TOKENS:
        return None
    return stripped


def normalize_sex(value: str) -> str:
    stripped = value.strip().lower()
    if stripped in {"1", "m", "male"}:
        return "male"
    if stripped in {"2", "f", "female"}:
        return "female"
    return "unknown"
