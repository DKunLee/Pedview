from __future__ import annotations

import heapq
from dataclasses import dataclass

from .models import Family, Person

NODE_SIZE = 24
PERSON_SPACING = 84
GENERATION_SPACING = 132
LANE_SPACING_BONUS = 12
MARGIN_X = 48
MARGIN_Y = 40
RELATIONSHIP_DROP = 18
SIBSHIP_DROP = 16


@dataclass(frozen=True)
class LayoutPerson:
    person_id: str
    x: float
    y: float
    generation: int


@dataclass(frozen=True)
class LayoutUnion:
    relationship_id: str
    father_id: str | None
    mother_id: str | None
    child_ids: tuple[str, ...]
    x: float
    y: float


@dataclass(frozen=True)
class FamilyLayout:
    family_id: str
    people: dict[str, LayoutPerson]
    unions: tuple[LayoutUnion, ...]
    width: float
    height: float
    generation_count: int


@dataclass(frozen=True)
class GenerationUnit:
    unit_id: str
    generation: int
    person_ids: tuple[str, ...]
    order_key: int


@dataclass(frozen=True)
class LayoutGraphUnit:
    unit_id: str
    layer: int
    person_ids: tuple[str, ...]
    order_key: float
    kind: str
    relationship_id: str | None = None


def assign_generations(family: Family) -> dict[str, int]:
    family.ensure_relationships()
    if family.generation_map and len(family.generation_map) == len(family.members):
        return dict(family.generation_map)

    order_index = family.order_index()
    component_by_person, component_order = build_same_generation_components(
        family, order_index
    )
    children_by_component: dict[str, set[str]] = {
        component_id: set() for component_id in component_order
    }
    in_degree: dict[str, int] = {component_id: 0 for component_id in component_order}
    component_generations: dict[str, int] = {
        component_id: 0 for component_id in component_order
    }

    for relationship in family.relationships:
        parent_components = {
            component_by_person[parent_id]
            for parent_id in relationship.parent_ids
            if parent_id in family.members
        }
        child_components = {
            component_by_person[child_id]
            for child_id in relationship.child_ids
            if child_id in family.members
        }
        for parent_component in parent_components:
            for child_component in child_components:
                if parent_component == child_component:
                    raise ValueError(f"Cycle detected in family {family.family_id}")
                if child_component not in children_by_component[parent_component]:
                    children_by_component[parent_component].add(child_component)
                    in_degree[child_component] += 1

    heap: list[tuple[int, str]] = [
        (component_order[component_id], component_id)
        for component_id, degree in in_degree.items()
        if degree == 0
    ]
    heapq.heapify(heap)
    visited = 0

    while heap:
        _, component_id = heapq.heappop(heap)
        visited += 1
        for child_component in sorted(
            children_by_component[component_id],
            key=lambda value: component_order[value],
        ):
            component_generations[child_component] = max(
                component_generations[child_component],
                component_generations[component_id] + 1,
            )
            in_degree[child_component] -= 1
            if in_degree[child_component] == 0:
                heapq.heappush(
                    heap, (component_order[child_component], child_component)
                )

    if visited != len(component_order):
        raise ValueError(f"Cycle detected in family {family.family_id}")

    generations = {
        person_id: component_generations[component_by_person[person_id]]
        for person_id in family.members
    }
    family.generation_map = dict(generations)
    return generations


def build_family_layout(family: Family) -> FamilyLayout:
    family.ensure_relationships()
    generations = assign_generations(family)
    order_index = family.order_index()
    partner_map = build_partner_map(family, generations)
    generation_layers, _units_by_id, unit_id_by_person = build_generation_unit_layers(
        family=family,
        generations=generations,
        partner_map=partner_map,
        order_index=order_index,
    )
    layout_graph_layers, layout_graph_units, relationship_paths = (
        build_layout_graph_layers(
            family=family,
            generations=generations,
            generation_layers=generation_layers,
            order_index=order_index,
        )
    )
    outgoing_units, incoming_units = build_layout_graph_adjacency(
        family=family,
        layout_units_by_id=layout_graph_units,
        unit_id_by_person=unit_id_by_person,
        relationship_paths=relationship_paths,
    )
    ordered_layout_graph_layers = reduce_crossings_with_sugiyama(
        generation_layers=layout_graph_layers,
        family=family,
        order_index=order_index,
        outgoing_units=outgoing_units,
        incoming_units=incoming_units,
    )
    unit_centers = assign_layout_graph_unit_positions(
        generation_layers=ordered_layout_graph_layers,
        outgoing_units=outgoing_units,
    )
    people_coordinates = materialize_people_coordinates(
        generations=generations,
        layout_units_by_id=layout_graph_units,
        unit_centers=unit_centers,
    )
    union_anchor_x_by_relationship = build_union_anchor_x_map(
        family=family,
        people_coordinates=people_coordinates,
        unit_centers=unit_centers,
    )
    people_coordinates = apply_dynamic_generation_spacing(
        family=family,
        people_coordinates=people_coordinates,
        union_anchor_x_by_relationship=union_anchor_x_by_relationship,
    )

    if people_coordinates:
        min_x = min(position.x for position in people_coordinates.values())
        max_x = max(position.x for position in people_coordinates.values())
        widest_generation_size = max(
            generation_population(generations).values(),
            default=0,
        )
        base_inner_width = max(widest_generation_size - 1, 0) * PERSON_SPACING
        actual_inner_width = max_x - min_x
        centering_offset = max((base_inner_width - actual_inner_width) / 2, 0)
        x_shift = MARGIN_X + NODE_SIZE / 2 - min_x + centering_offset
        if x_shift != 0:
            people_coordinates = {
                person_id: LayoutPerson(
                    person_id=position.person_id,
                    x=position.x + x_shift,
                    y=position.y,
                    generation=position.generation,
                )
                for person_id, position in people_coordinates.items()
            }
            union_anchor_x_by_relationship = {
                relationship_id: anchor_x + x_shift
                for relationship_id, anchor_x in union_anchor_x_by_relationship.items()
            }

    unions: list[LayoutUnion] = []
    for relationship in family.relationships:
        father_id = relationship.father_id
        mother_id = relationship.mother_id
        parent_positions = [
            people_coordinates[parent_id]
            for parent_id in (father_id, mother_id)
            if parent_id is not None
        ]
        if not parent_positions:
            continue
        union_x = union_anchor_x_by_relationship.get(
            relationship.relationship_id,
            resolve_union_anchor_x(relationship, people_coordinates),
        )
        parent_generation = max(position.generation for position in parent_positions)
        union_y = (
            MARGIN_Y
            + parent_generation * GENERATION_SPACING
            + NODE_SIZE / 2
            + RELATIONSHIP_DROP
        )
        ordered_children = tuple(
            sorted(
                relationship.child_ids,
                key=lambda child_id: (
                    people_coordinates[child_id].x,
                    order_index[child_id],
                ),
            )
        )
        unions.append(
            LayoutUnion(
                relationship_id=relationship.relationship_id,
                father_id=father_id,
                mother_id=mother_id,
                child_ids=ordered_children,
                x=union_x,
                y=union_y,
            )
        )

    generation_count = max(generations.values(), default=0) + 1
    widest_generation_size = max(
        generation_population(generations).values(),
        default=0,
    )
    widest_generation_width = (
        MARGIN_X * 2 + max(widest_generation_size - 1, 0) * PERSON_SPACING + NODE_SIZE
    )
    max_x = max(
        (position.x for position in people_coordinates.values()), default=MARGIN_X
    )
    width = max(widest_generation_width, max_x + MARGIN_X + (NODE_SIZE / 2), 320)
    max_y = max(
        (position.y for position in people_coordinates.values()), default=MARGIN_Y
    )
    height = max_y + MARGIN_Y + NODE_SIZE + 56
    return FamilyLayout(
        family_id=family.family_id,
        people=people_coordinates,
        unions=tuple(unions),
        width=width,
        height=height,
        generation_count=generation_count,
    )


def build_layout_graph_layers(
    family: Family,
    generations: dict[str, int],
    generation_layers: dict[int, list[GenerationUnit]],
    order_index: dict[str, int],
) -> tuple[
    dict[int, list[LayoutGraphUnit]],
    dict[str, LayoutGraphUnit],
    dict[str, tuple[str, ...]],
]:
    layout_layers: dict[int, list[LayoutGraphUnit]] = {}
    layout_units_by_id: dict[str, LayoutGraphUnit] = {}
    relationship_paths: dict[str, tuple[str, ...]] = {}

    for generation, units in generation_layers.items():
        layer = generation_to_person_layer(generation)
        layout_layers[layer] = [
            LayoutGraphUnit(
                unit_id=unit.unit_id,
                layer=layer,
                person_ids=unit.person_ids,
                order_key=float(unit.order_key),
                kind="person",
            )
            for unit in units
        ]
        for unit in layout_layers[layer]:
            layout_units_by_id[unit.unit_id] = unit

    for relationship in family.relationships:
        child_ids = [
            child_id for child_id in relationship.child_ids if child_id in generations
        ]
        if not child_ids:
            continue

        parent_ids = [
            parent_id
            for parent_id in relationship.parent_ids
            if parent_id in generations
        ]
        child_generation = min(generations[child_id] for child_id in child_ids)
        parent_generation = (
            max(generations[parent_id] for parent_id in parent_ids)
            if parent_ids
            else child_generation - 1
        )
        child_layer = generation_to_person_layer(child_generation)
        union_layer = generation_to_person_layer(parent_generation) + 1
        order_key = relationship_layout_order_key(
            relationship=relationship,
            order_index=order_index,
        )

        path_unit_ids: list[str] = []
        union_unit = LayoutGraphUnit(
            unit_id=f"{relationship.relationship_id}::union",
            layer=union_layer,
            person_ids=(),
            order_key=order_key,
            kind="union",
            relationship_id=relationship.relationship_id,
        )
        layout_layers.setdefault(union_layer, []).append(union_unit)
        layout_units_by_id[union_unit.unit_id] = union_unit
        path_unit_ids.append(union_unit.unit_id)

        for dummy_index, layer in enumerate(
            range(union_layer + 1, child_layer), start=1
        ):
            dummy_unit = LayoutGraphUnit(
                unit_id=f"{relationship.relationship_id}::dummy::{dummy_index}",
                layer=layer,
                person_ids=(),
                order_key=order_key,
                kind="dummy",
                relationship_id=relationship.relationship_id,
            )
            layout_layers.setdefault(layer, []).append(dummy_unit)
            layout_units_by_id[dummy_unit.unit_id] = dummy_unit
            path_unit_ids.append(dummy_unit.unit_id)

        relationship_paths[relationship.relationship_id] = tuple(path_unit_ids)

    for layer in layout_layers:
        layout_layers[layer] = sorted(
            layout_layers[layer],
            key=lambda unit: (unit.order_key, unit.unit_id),
        )

    return layout_layers, layout_units_by_id, relationship_paths


def build_layout_graph_adjacency(
    family: Family,
    layout_units_by_id: dict[str, LayoutGraphUnit],
    unit_id_by_person: dict[str, str],
    relationship_paths: dict[str, tuple[str, ...]],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    outgoing_units: dict[str, set[str]] = {
        unit_id: set() for unit_id in layout_units_by_id
    }
    incoming_units: dict[str, set[str]] = {
        unit_id: set() for unit_id in layout_units_by_id
    }

    def add_edge(source_id: str, target_id: str) -> None:
        if source_id == target_id:
            return
        source_unit = layout_units_by_id[source_id]
        target_unit = layout_units_by_id[target_id]
        if source_unit.layer >= target_unit.layer:
            return
        outgoing_units[source_id].add(target_id)
        incoming_units[target_id].add(source_id)

    for relationship in family.relationships:
        path = relationship_paths.get(relationship.relationship_id)
        if not path:
            continue

        parent_unit_ids = {
            unit_id_by_person[parent_id]
            for parent_id in relationship.parent_ids
            if parent_id in unit_id_by_person
        }
        child_unit_ids = {
            unit_id_by_person[child_id]
            for child_id in relationship.child_ids
            if child_id in unit_id_by_person
        }

        for parent_unit_id in parent_unit_ids:
            add_edge(parent_unit_id, path[0])

        for source_id, target_id in zip(path, path[1:]):
            add_edge(source_id, target_id)

        for child_unit_id in child_unit_ids:
            add_edge(path[-1], child_unit_id)

    return outgoing_units, incoming_units


def generation_to_person_layer(generation: int) -> int:
    return generation * 2


def relationship_layout_order_key(
    relationship,
    order_index: dict[str, int],
) -> float:
    participant_order = [
        order_index[person_id]
        for person_id in (*relationship.parent_ids, *relationship.child_ids)
        if person_id in order_index
    ]
    if not participant_order:
        return float("inf")
    return sum(participant_order) / len(participant_order)


def build_partner_map(
    family: Family,
    generations: dict[str, int],
) -> dict[str, set[str]]:
    family.ensure_relationships()
    partner_map: dict[str, set[str]] = {
        person_id: set() for person_id in family.members
    }
    for relationship in family.relationships:
        father_id = relationship.father_id
        mother_id = relationship.mother_id
        if (
            father_id
            and mother_id
            and father_id in family.members
            and mother_id in family.members
            and generations[father_id] == generations[mother_id]
        ):
            partner_map[father_id].add(mother_id)
            partner_map[mother_id].add(father_id)
    return partner_map


def build_generation_units(
    members: list[Person],
    partner_map: dict[str, set[str]],
    order_index: dict[str, int],
) -> list[list[Person]]:
    visited: set[str] = set()
    units: list[list[Person]] = []

    for person in members:
        if person.person_id in visited:
            continue
        same_generation_partners = sorted(
            partner_map[person.person_id],
            key=lambda partner_id: order_index[partner_id],
        )
        pair: list[Person] | None = None
        if len(same_generation_partners) == 1:
            partner_id = same_generation_partners[0]
            if partner_id not in visited and len(partner_map[partner_id]) == 1:
                pair = sort_pair(
                    [
                        person,
                        next(
                            member
                            for member in members
                            if member.person_id == partner_id
                        ),
                    ],
                    order_index,
                )

        if pair is not None:
            units.append(pair)
            visited.update(member.person_id for member in pair)
        else:
            units.append([person])
            visited.add(person.person_id)

    return units


def sort_pair(pair: list[Person], order_index: dict[str, int]) -> list[Person]:
    left, right = pair
    if left.sex == "female" and right.sex == "male":
        return [right, left]
    if left.sex == "male" and right.sex == "female":
        return [left, right]
    return sorted(pair, key=lambda person: order_index[person.person_id])


def build_generation_unit_layers(
    family: Family,
    generations: dict[str, int],
    partner_map: dict[str, set[str]],
    order_index: dict[str, int],
) -> tuple[dict[int, list[GenerationUnit]], dict[str, GenerationUnit], dict[str, str]]:
    generation_layers: dict[int, list[GenerationUnit]] = {}
    units_by_id: dict[str, GenerationUnit] = {}
    unit_id_by_person: dict[str, str] = {}

    for generation in sorted({value for value in generations.values()}):
        members = [
            family.members[person_id]
            for person_id in family.order
            if generations[person_id] == generation
        ]
        raw_units = build_generation_units(members, partner_map, order_index)
        generation_units: list[GenerationUnit] = []

        for index, raw_unit in enumerate(raw_units, start=1):
            person_ids = tuple(person.person_id for person in raw_unit)
            unit = GenerationUnit(
                unit_id=f"{family.family_id}::gen::{generation}::unit::{index}",
                generation=generation,
                person_ids=person_ids,
                order_key=min(order_index[person_id] for person_id in person_ids),
            )
            generation_units.append(unit)
            units_by_id[unit.unit_id] = unit
            for person_id in person_ids:
                unit_id_by_person[person_id] = unit.unit_id

        generation_layers[generation] = generation_units

    return generation_layers, units_by_id, unit_id_by_person


def build_unit_adjacency(
    family: Family,
    units_by_id: dict[str, GenerationUnit],
    unit_id_by_person: dict[str, str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    outgoing_units: dict[str, set[str]] = {unit_id: set() for unit_id in units_by_id}
    incoming_units: dict[str, set[str]] = {unit_id: set() for unit_id in units_by_id}

    for relationship in family.relationships:
        parent_unit_ids = {
            unit_id_by_person[parent_id]
            for parent_id in relationship.parent_ids
            if parent_id in unit_id_by_person
        }
        child_unit_ids = {
            unit_id_by_person[child_id]
            for child_id in relationship.child_ids
            if child_id in unit_id_by_person
        }

        for parent_unit_id in parent_unit_ids:
            for child_unit_id in child_unit_ids:
                if parent_unit_id == child_unit_id:
                    continue
                if (
                    units_by_id[parent_unit_id].generation
                    >= units_by_id[child_unit_id].generation
                ):
                    continue
                outgoing_units[parent_unit_id].add(child_unit_id)
                incoming_units[child_unit_id].add(parent_unit_id)

    return outgoing_units, incoming_units


def reduce_crossings_with_sugiyama(
    generation_layers: dict[int, list[GenerationUnit]],
    family: Family,
    order_index: dict[str, int],
    outgoing_units: dict[str, set[str]],
    incoming_units: dict[str, set[str]],
) -> dict[int, list[GenerationUnit]]:
    ordered_layers = {
        generation: list(units) for generation, units in generation_layers.items()
    }
    generations = sorted(ordered_layers)
    if len(generations) < 2:
        return ordered_layers

    initial_rank = {
        unit.unit_id: index
        for units in generation_layers.values()
        for index, unit in enumerate(units)
    }
    unit_group_keys = {
        unit.unit_id: unit_group_key(unit, family, order_index)
        for units in generation_layers.values()
        for unit in units
    }

    best_layers = {
        generation: list(units) for generation, units in ordered_layers.items()
    }
    best_crossings = count_total_crossings(best_layers, outgoing_units)

    for _ in range(8):
        for generation_index in range(1, len(generations)):
            generation = generations[generation_index]
            previous_generation = generations[generation_index - 1]
            ordered_layers[generation] = reorder_layer_with_barycenters(
                layer_units=ordered_layers[generation],
                fixed_layer=ordered_layers[previous_generation],
                neighbor_map=incoming_units,
                unit_group_keys=unit_group_keys,
                initial_rank=initial_rank,
            )

        for generation_index in range(len(generations) - 2, -1, -1):
            generation = generations[generation_index]
            next_generation = generations[generation_index + 1]
            ordered_layers[generation] = reorder_layer_with_barycenters(
                layer_units=ordered_layers[generation],
                fixed_layer=ordered_layers[next_generation],
                neighbor_map=outgoing_units,
                unit_group_keys=unit_group_keys,
                initial_rank=initial_rank,
            )

        crossing_count = count_total_crossings(ordered_layers, outgoing_units)
        if crossing_count < best_crossings:
            best_crossings = crossing_count
            best_layers = {
                generation: list(units) for generation, units in ordered_layers.items()
            }

    return best_layers


def reorder_layer_with_barycenters(
    layer_units: list[GenerationUnit],
    fixed_layer: list[GenerationUnit],
    neighbor_map: dict[str, set[str]],
    unit_group_keys: dict[str, tuple[str, str, str]],
    initial_rank: dict[str, int],
) -> list[GenerationUnit]:
    fixed_positions = {unit.unit_id: index for index, unit in enumerate(fixed_layer)}
    current_positions = {unit.unit_id: index for index, unit in enumerate(layer_units)}
    blocks = build_layer_blocks(layer_units, unit_group_keys)
    scored_blocks: list[tuple[tuple[float, ...], tuple[GenerationUnit, ...]]] = []

    for block_index, block in enumerate(blocks):
        neighbor_positions = [
            fixed_positions[neighbor_id]
            for unit in block
            for neighbor_id in neighbor_map.get(unit.unit_id, set())
            if neighbor_id in fixed_positions
        ]
        stable_rank = min(current_positions[unit.unit_id] for unit in block)
        original_rank = min(initial_rank[unit.unit_id] for unit in block)

        if neighbor_positions:
            median = median_value(neighbor_positions)
            barycenter = sum(neighbor_positions) / len(neighbor_positions)
            sort_key = (
                0.0,
                median,
                barycenter,
                stable_rank,
                original_rank,
                block_index,
            )
        else:
            sort_key = (1.0, stable_rank, original_rank, block_index)

        scored_blocks.append((sort_key, block))

    scored_blocks.sort(key=lambda item: item[0])
    return [unit for _, block in scored_blocks for unit in block]


def build_layer_blocks(
    layer_units: list[GenerationUnit],
    unit_group_keys: dict[str, tuple[str, str, str]],
) -> list[tuple[GenerationUnit, ...]]:
    blocks: list[tuple[GenerationUnit, ...]] = []
    current_key: tuple[str, str, str] | None = None
    current_block: list[GenerationUnit] = []

    for unit in layer_units:
        group_key = unit_group_keys[unit.unit_id]
        if current_block and group_key != current_key:
            blocks.append(tuple(current_block))
            current_block = [unit]
            current_key = group_key
            continue
        if not current_block:
            current_key = group_key
        current_block.append(unit)

    if current_block:
        blocks.append(tuple(current_block))

    return blocks


def unit_group_key(
    unit: GenerationUnit,
    family: Family,
    order_index: dict[str, int],
) -> tuple[str, str, str]:
    parent_candidates: list[tuple[int, str, str]] = []

    for person_id in unit.person_ids:
        person = family.members[person_id]
        father_id = person.father_id if person.father_id in family.members else ""
        mother_id = person.mother_id if person.mother_id in family.members else ""
        if not father_id and not mother_id:
            continue
        parent_candidates.append((order_index[person_id], father_id, mother_id))

    if not parent_candidates:
        return ("unit", unit.unit_id, unit.unit_id)

    _, father_id, mother_id = min(parent_candidates)
    return ("parents", father_id, mother_id)


def median_value(values: list[int]) -> float:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def count_total_crossings(
    generation_layers: dict[int, list[GenerationUnit]],
    outgoing_units: dict[str, set[str]],
) -> int:
    total_crossings = 0
    generations = sorted(generation_layers)

    for generation_index in range(len(generations) - 1):
        upper_generation = generations[generation_index]
        lower_generation = generations[generation_index + 1]
        lower_positions = {
            unit.unit_id: index
            for index, unit in enumerate(generation_layers[lower_generation])
        }
        edges: list[tuple[int, int]] = []

        for upper_index, unit in enumerate(generation_layers[upper_generation]):
            for child_unit_id in outgoing_units.get(unit.unit_id, set()):
                if child_unit_id in lower_positions:
                    edges.append((upper_index, lower_positions[child_unit_id]))

        for left_index in range(len(edges)):
            left_start, left_end = edges[left_index]
            for right_index in range(left_index + 1, len(edges)):
                right_start, right_end = edges[right_index]
                if (left_start - right_start) * (left_end - right_end) < 0:
                    total_crossings += 1

    return total_crossings


def assign_generation_unit_positions(
    generation_layers: dict[int, list[GenerationUnit]],
    outgoing_units: dict[str, set[str]],
) -> dict[str, LayoutPerson]:
    people_coordinates: dict[str, LayoutPerson] = {}
    unit_centers: dict[str, float] = {}

    for generation in reversed(sorted(generation_layers)):
        next_left = 0.0
        y = MARGIN_Y + generation * GENERATION_SPACING

        for unit in generation_layers[generation]:
            unit_width = (len(unit.person_ids) - 1) * PERSON_SPACING
            descendant_centers = [
                unit_centers[child_unit_id]
                for child_unit_id in outgoing_units.get(unit.unit_id, set())
                if child_unit_id in unit_centers
            ]

            left = next_left
            if descendant_centers:
                left = (
                    sum(descendant_centers) / len(descendant_centers) - unit_width / 2
                )
            left = max(left, next_left)

            for position_in_unit, person_id in enumerate(unit.person_ids):
                x = left + position_in_unit * PERSON_SPACING
                people_coordinates[person_id] = LayoutPerson(
                    person_id=person_id,
                    x=x,
                    y=y,
                    generation=generation,
                )

            unit_centers[unit.unit_id] = left + unit_width / 2
            next_left = left + unit_width + PERSON_SPACING

    return people_coordinates


def assign_layout_graph_unit_positions(
    generation_layers: dict[int, list[LayoutGraphUnit]],
    outgoing_units: dict[str, set[str]],
) -> dict[str, float]:
    unit_centers: dict[str, float] = {}

    for generation in reversed(sorted(generation_layers)):
        next_left = 0.0

        for unit in generation_layers[generation]:
            unit_width = max(len(unit.person_ids) - 1, 0) * PERSON_SPACING
            descendant_centers = [
                unit_centers[child_unit_id]
                for child_unit_id in outgoing_units.get(unit.unit_id, set())
                if child_unit_id in unit_centers
            ]

            left = next_left
            if descendant_centers:
                left = (
                    sum(descendant_centers) / len(descendant_centers) - unit_width / 2
                )
            left = max(left, next_left)
            unit_centers[unit.unit_id] = left + unit_width / 2
            next_left = left + unit_width + PERSON_SPACING

    return unit_centers


def materialize_people_coordinates(
    generations: dict[str, int],
    layout_units_by_id: dict[str, LayoutGraphUnit],
    unit_centers: dict[str, float],
) -> dict[str, LayoutPerson]:
    people_coordinates: dict[str, LayoutPerson] = {}

    for unit in layout_units_by_id.values():
        if unit.kind != "person" or unit.unit_id not in unit_centers:
            continue
        unit_width = max(len(unit.person_ids) - 1, 0) * PERSON_SPACING
        left = unit_centers[unit.unit_id] - unit_width / 2
        for position_in_unit, person_id in enumerate(unit.person_ids):
            generation = generations[person_id]
            people_coordinates[person_id] = LayoutPerson(
                person_id=person_id,
                x=left + position_in_unit * PERSON_SPACING,
                y=MARGIN_Y + generation * GENERATION_SPACING,
                generation=generation,
            )

    return people_coordinates


def build_union_anchor_x_map(
    family: Family,
    people_coordinates: dict[str, LayoutPerson],
    unit_centers: dict[str, float],
) -> dict[str, float]:
    return {
        relationship.relationship_id: resolve_union_anchor_x(
            relationship=relationship,
            people_coordinates=people_coordinates,
            preferred_x=unit_centers.get(f"{relationship.relationship_id}::union"),
        )
        for relationship in family.relationships
    }


def apply_dynamic_generation_spacing(
    family: Family,
    people_coordinates: dict[str, LayoutPerson],
    union_anchor_x_by_relationship: dict[str, float] | None = None,
) -> dict[str, LayoutPerson]:
    if not people_coordinates:
        return people_coordinates

    lane_counts = compute_transition_lane_counts(
        family=family,
        people_coordinates=people_coordinates,
        union_anchor_x_by_relationship=union_anchor_x_by_relationship,
    )
    generation_values = sorted(
        {position.generation for position in people_coordinates.values()}
    )
    generation_y: dict[int, float] = {}
    current_y = MARGIN_Y

    for index, generation in enumerate(generation_values):
        if index == 0:
            generation_y[generation] = current_y
            continue

        previous_generation = generation_values[index - 1]
        lane_count = lane_counts.get(previous_generation, 1)
        extra_spacing = max(0, lane_count - 1) * LANE_SPACING_BONUS
        current_y += GENERATION_SPACING + extra_spacing
        generation_y[generation] = current_y

    return {
        person_id: LayoutPerson(
            person_id=position.person_id,
            x=position.x,
            y=generation_y[position.generation],
            generation=position.generation,
        )
        for person_id, position in people_coordinates.items()
    }


def compute_transition_lane_counts(
    family: Family,
    people_coordinates: dict[str, LayoutPerson],
    union_anchor_x_by_relationship: dict[str, float] | None = None,
) -> dict[int, int]:
    grouped: dict[tuple[int, int], list[tuple[float, float, int]]] = {}

    for order, relationship in enumerate(family.relationships):
        child_positions = [
            people_coordinates[child_id]
            for child_id in relationship.child_ids
            if child_id in people_coordinates
        ]
        if not child_positions:
            continue

        child_generation = min(child.generation for child in child_positions)
        parent_positions = [
            people_coordinates[parent_id]
            for parent_id in relationship.parent_ids
            if parent_id in people_coordinates
        ]
        parent_generation = (
            max(parent.generation for parent in parent_positions)
            if parent_positions
            else child_generation - 1
        )
        union_x = (
            union_anchor_x_by_relationship.get(relationship.relationship_id)
            if union_anchor_x_by_relationship is not None
            else None
        )
        if union_x is None:
            union_x = resolve_union_anchor_x(
                relationship=relationship,
                people_coordinates=people_coordinates,
            )
        relationship_drop_x = resolve_relationship_drop_x(
            relationship=relationship,
            people_coordinates=people_coordinates,
            union_x=union_x,
        )
        interval_start = min(
            [relationship_drop_x, *[child.x for child in child_positions]]
        )
        interval_end = max(
            [relationship_drop_x, *[child.x for child in child_positions]]
        )
        grouped.setdefault((parent_generation, child_generation), []).append(
            (interval_start, interval_end, order)
        )

    lane_counts_by_generation: dict[int, int] = {}
    for (parent_generation, _child_generation), entries in grouped.items():
        lane_ends: list[float] = []
        for start, end, order in sorted(entries, key=lambda item: (item[0], item[2])):
            lane = 0
            while lane < len(lane_ends) and start <= lane_ends[lane]:
                lane += 1
            if lane == len(lane_ends):
                lane_ends.append(end)
            else:
                lane_ends[lane] = end
        lane_counts_by_generation[parent_generation] = max(
            lane_counts_by_generation.get(parent_generation, 1),
            len(lane_ends),
        )

    return lane_counts_by_generation


def resolve_union_anchor_x(
    relationship,
    people_coordinates: dict[str, LayoutPerson],
    preferred_x: float | None = None,
) -> float:
    parent_positions = [
        people_coordinates[parent_id]
        for parent_id in relationship.parent_ids
        if parent_id in people_coordinates
    ]
    child_positions = [
        people_coordinates[child_id]
        for child_id in relationship.child_ids
        if child_id in people_coordinates
    ]

    if len(parent_positions) == 2:
        min_x = min(parent.x for parent in parent_positions)
        max_x = max(parent.x for parent in parent_positions)
        if preferred_x is None:
            preferred_x = sum(parent.x for parent in parent_positions) / len(
                parent_positions
            )
        return max(min_x, min(max_x, preferred_x))

    if len(parent_positions) == 1:
        return parent_positions[0].x

    if preferred_x is not None:
        return preferred_x

    if child_positions:
        return sum(child.x for child in child_positions) / len(child_positions)

    return 0.0


def resolve_relationship_drop_x(
    relationship,
    people_coordinates: dict[str, LayoutPerson],
    union_x: float,
) -> float:
    parent_positions = [
        people_coordinates[parent_id]
        for parent_id in relationship.parent_ids
        if parent_id in people_coordinates
    ]
    if len(parent_positions) == 2:
        return sum(parent.x for parent in parent_positions) / len(parent_positions)
    return union_x


def generation_population(generations: dict[str, int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for generation in generations.values():
        counts[generation] = counts.get(generation, 0) + 1
    return counts


def build_same_generation_components(
    family: Family,
    order_index: dict[str, int],
) -> tuple[dict[str, str], dict[str, int]]:
    parent: dict[str, str] = {person_id: person_id for person_id in family.members}

    def find(person_id: str) -> str:
        while parent[person_id] != person_id:
            parent[person_id] = parent[parent[person_id]]
            person_id = parent[person_id]
        return person_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if order_index[left_root] <= order_index[right_root]:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    for relationship in family.relationships:
        if (
            relationship.father_id in family.members
            and relationship.mother_id in family.members
        ):
            union(relationship.father_id, relationship.mother_id)

    component_members: dict[str, list[str]] = {}
    component_by_person: dict[str, str] = {}
    for person_id in family.order:
        component_id = find(person_id)
        component_by_person[person_id] = component_id
        component_members.setdefault(component_id, []).append(person_id)

    ordered_components = sorted(
        component_members,
        key=lambda component_id: min(
            order_index[person_id] for person_id in component_members[component_id]
        ),
    )
    component_order = {
        component_id: index for index, component_id in enumerate(ordered_components)
    }
    return component_by_person, component_order
