# pedview

[![PyPI version](https://img.shields.io/pypi/v/pedview.svg)](https://pypi.org/project/pedview/)
[![Python versions](https://img.shields.io/pypi/pyversions/pedview.svg)](https://pypi.org/project/pedview/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight command-line tool for visualizing family pedigrees in genetics and clinical research workflows.

`pedview` reads standard pedigree files and generates self-contained, interactive HTML reports with publication-ready SVG diagrams. It has **zero external runtime dependencies** (built purely on Python standard library) and runs completely offline.

---

## Features

- **Zero Runtime Dependencies**: Pure Python standard library (`math`, `html`, `dataclasses`, `pathlib`, `argparse`).
- **Flexible Input**: Auto-detects standard 6-column PLINK `.fam`/`.ped` files and extended headered pedigree files.
- **Clinical & Research Attributes**: Visualizes affected status, proband indicators, carriers, deceased status, age labels, and genotype calls.
- **Layered Graph Engine**: Sugiyama-style layout with barycenter crossing reduction, twin handling, and consanguinity loop routing.
- **Interactive Standalone HTML**: Produces a single offline HTML report with pan/zoom navigation, individual detail drawer, and search.
- **Publication Exports**: One-click download for vector SVG, journal-styled SVG, and high-resolution PNG.
- **Mendelian Quality Control**: Automated parent-child relationship validation and Wright's inbreeding coefficient calculations ($f_a$).

---

## Installation

```bash
pip install pedview
```

Or install from source:

```bash
git clone https://github.com/DKunLee/Pedview.git
cd Pedview
pip install .
```

---

## Quickstart

```bash
# 1. Validate pedigree format, integrity, and relationships
pedview validate <input.ped>

# 2. Preview family and cohort summaries directly in the terminal
pedview preview <input.ped>

# 3. Build a standalone interactive HTML report
pedview build <input.ped> -o <output_report.html>

# 4. Render a single family from a multi-family cohort
pedview build <input.ped> --family <family_id> -o <family_report.html>

# 5. Highlight a candidate variant and set ancestor inbreeding coefficient
pedview build <input.ped> --variant-name "<variant_name>" --ancestor-inbreeding 0.02 -o <output_report.html>
```

---

## Supported Formats

### 1. Standard Headerless PLINK `.fam` / `.ped` (6 Columns)
```text
FAM01 101 0   0   1 1
FAM01 102 0   0   2 1
FAM01 201 101 102 1 2
FAM01 202 101 102 2 1
```
- **Sex**: `1` = Male, `2` = Female, `0` = Unknown.
- **Phenotype**: `1` = Unaffected, `2` = Affected, `0` / `-9` = Unknown.
- **Missing Parents**: `0`, `.`, `-9`, `NA`.

### 2. Headered Extended Pedigree (Tab- or Space-delimited)
```text
famid  id   fid  mid  sex  affected    proband  deceased  age  genotype
FAM01  101  0    0    1    unaffected  0        1         72y  0/0
FAM01  102  0    0    2    unaffected  0        0         68y  0/1
FAM01  201  101  102  1    affected    1        0         14y  0/1
```

Common column header aliases are resolved automatically:
- **Family**: `famid`, `family_id`, `family`, `pedigree`, `fid`
- **Individual**: `id`, `iid`, `individual_id`, `sample_id`
- **Father**: `fid`, `pat`, `pid`, `father`, `father_id`
- **Mother**: `mid`, `mat`, `mother`, `mother_id`
- **Sex**: `sex`, `gender`
- **Phenotype**: `affected`, `phenotype`, `affection`

---

## CLI Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `validate` | Validates file format, parent references, sex codes, and loops | `pedview validate <input.ped>` |
| `preview` | Prints terminal summary of families, founders, and generations | `pedview preview <input.ped>` |
| `build` | Generates interactive HTML report | `pedview build <input.ped> -o <output_report.html>` |

### Build Options

- `-o, --output`: Output file path (defaults to `<input>.html`).
- `--family`: Filter report to a specific family ID (`<family_id>`).
- `--title`: Custom title for the HTML report (`"<title>"`).
- `--variant-name`: Candidate variant annotation label (e.g. `"<variant_name>"`).
- `--ancestor-inbreeding`: Global Wright ancestor inbreeding coefficient ($f_a$). Defaults to `0.0`.

---

## License

This project is licensed under the [MIT License](LICENSE).
