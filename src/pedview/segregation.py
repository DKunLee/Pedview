from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Family


def normalize_genotype(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    lower = cleaned.lower()
    if lower in {"./.", ".", "na", "n/a", "missing", "unknown"}:
        return "./."
    if lower in {"0/0", "0|0", "hom_ref", "ref", "wt", "wildtype", "hom-ref"}:
        return "0/0"
    if lower in {"0/1", "1/0", "0|1", "1|0", "het", "heterozygous", "carrier"}:
        return "0/1"
    if lower in {"1/1", "1|1", "hom_alt", "hom-alt", "mut/mut", "alt/alt"}:
        return "1/1"
    return cleaned


def analyze_family_segregation(
    family: Family, variant_name: str | None = None
) -> dict[str, object] | None:
    people = family.people()
    genotyped = [p for p in people if p.genotype and p.genotype != "./."]
    if not genotyped:
        return None

    de_novo_ids: list[str] = []
    mendelian_errors: list[dict[str, str]] = []
    carriers: list[str] = []
    hom_alts: list[str] = []
    hom_refs: list[str] = []

    person_by_id = {p.person_id: p for p in people}

    for p in people:
        gt = normalize_genotype(p.genotype)
        if gt == "0/1":
            carriers.append(p.person_id)
        elif gt == "1/1":
            hom_alts.append(p.person_id)
        elif gt == "0/0":
            hom_refs.append(p.person_id)

    # Trio Mendelian analysis
    for p in people:
        child_gt = normalize_genotype(p.genotype)
        if not child_gt or child_gt == "./.":
            continue

        father = person_by_id.get(p.father_id) if p.father_id else None
        mother = person_by_id.get(p.mother_id) if p.mother_id else None

        fat_gt = normalize_genotype(father.genotype) if father else None
        mot_gt = normalize_genotype(mother.genotype) if mother else None

        # Check for candidate de novo: child is 0/1 or 1/1, but both biological parents are confirmed 0/0
        if child_gt in {"0/1", "1/1"} and fat_gt == "0/0" and mot_gt == "0/0":
            de_novo_ids.append(p.person_id)

        # Check Mendelian incompatibilities
        if child_gt == "1/1":
            if fat_gt == "0/0" or mot_gt == "0/0":
                parent_desc = "father is 0/0" if fat_gt == "0/0" else "mother is 0/0"
                if fat_gt == "0/0" and mot_gt == "0/0":
                    parent_desc = "both parents are 0/0"
                mendelian_errors.append(
                    {
                        "person_id": p.person_id,
                        "message": f"Child {p.person_id} is homozygous alternate (1/1), but {parent_desc}.",
                    }
                )
        elif child_gt == "0/0":
            if fat_gt == "1/1" or mot_gt == "1/1":
                parent_desc = "father is 1/1" if fat_gt == "1/1" else "mother is 1/1"
                mendelian_errors.append(
                    {
                        "person_id": p.person_id,
                        "message": f"Child {p.person_id} is homozygous reference (0/0), but {parent_desc}.",
                    }
                )

    # Segregation consistency assessment
    affected_people = [p for p in people if p.affected == "affected"]
    unaffected_people = [p for p in people if p.affected == "unaffected"]

    candidate_mode = "Candidate Variant"
    if de_novo_ids:
        candidate_mode = "Candidate De Novo"
    elif (
        all(
            normalize_genotype(p.genotype) == "1/1"
            for p in affected_people
            if p.genotype
        )
        and all(
            normalize_genotype(p.genotype) in {"0/1", "0/0", None}
            for p in unaffected_people
        )
        and len(hom_alts) > 0
    ):
        candidate_mode = "Autosomal Recessive"
    elif (
        all(
            normalize_genotype(p.genotype) in {"0/1", "1/1"}
            for p in affected_people
            if p.genotype
        )
        and all(
            normalize_genotype(p.genotype) in {"0/0", None} for p in unaffected_people
        )
        and len(affected_people) > 0
    ):
        candidate_mode = "Autosomal Dominant"

    return {
        "variant_name": variant_name or "Candidate Variant",
        "mode": candidate_mode,
        "total_genotyped": len(genotyped),
        "de_novo_ids": de_novo_ids,
        "carrier_ids": carriers,
        "hom_alt_ids": hom_alts,
        "hom_ref_ids": hom_refs,
        "mendelian_errors": mendelian_errors,
    }
