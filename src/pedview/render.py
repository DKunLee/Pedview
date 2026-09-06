from __future__ import annotations

import json
from html import escape
from string import Template

from .insights import build_family_insights
from .layout import NODE_SIZE, PERSON_SPACING, SIBSHIP_DROP, FamilyLayout
from .models import Pedigree, ValidationMessage
from .phenotypes import affected_status_from_metadata, metadata_without_affected_status
from .relatedness import compute_family_relatedness
from .validate import FamilySummary

LANE_TOP_PADDING = 8
LANE_BOTTOM_PADDING = 10
PARTNER_ROUTING_THRESHOLD = PERSON_SPACING * 1.5
PARTNER_LANE_OFFSET = 2
PARTNER_LANE_SPACING = 6

CSS = """
:root {
  color-scheme: light;
  --bg: #f4f4f1;
  --panel: #ffffff;
  --ink: #181818;
  --muted: #6c6c6c;
  --line: #5f5f5f;
  --accent: #0d5b87;
  --accent-hover: #0a496c;
  --highlight-strong: #0d5b87;
  --highlight-mid: #4f7992;
  --highlight-soft: #7f9bab;
  --highlight-faint: #a9bac4;
  --warning: #8a5a00;
  --error: #9f3027;
  --male-fill: #e8f0f6;
  --male-border: #5a7890;
  --male-affected-fill: #9cbcd1;
  --female-fill: #f6e7ee;
  --female-border: #bb7b96;
  --female-affected-fill: #ddb0c5;
  --unknown-fill: #f0efe9;
  --unknown-border: #8c877c;
  --unknown-affected-fill: #cbc5bb;
  --border: #d9d9d4;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 8px 22px rgba(0, 0, 0, 0.04);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
  color: var(--ink);
  background: var(--bg);
  padding-bottom: 400px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  max-width: 1520px;
  margin: 0 auto;
  padding: 24px;
}

.content {
  min-width: 0;
}

.summary,
.family-card,
.details {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
}

.hero {
  padding: 18px 20px;
  margin-bottom: 16px;
}

.hero h1 {
  margin: 0 0 8px;
  font-size: 1.6rem;
  font-weight: 650;
  letter-spacing: -0.015em;
  line-height: 1.2;
}

.hero p,
.summary p,
.details p {
  margin: 0;
  color: var(--muted);
  line-height: 1.5;
}

.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  padding: 14px;
  margin-bottom: 16px;
}

.metric {
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e5e5df;
  box-shadow: var(--shadow-sm);
}

.metric strong {
  display: block;
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 14px;
}

.search-bar {
  flex: 1 1 320px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.search-bar input[type="search"] {
  flex: 1 1 240px;
  min-width: 0;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #d9d9d4;
  background: #ffffff;
  color: var(--ink);
  font: inherit;
}

.search-bar input[type="search"]:focus {
  outline: 2px solid rgba(13, 91, 135, 0.18);
  outline-offset: 1px;
  border-color: var(--accent);
}

.search-feedback {
  margin-top: 10px;
  min-height: 1.4em;
  color: var(--muted);
  font-size: 0.88rem;
}

.search-feedback.is-error {
  color: var(--error);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

button {
  appearance: none;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 8px 12px;
  font: inherit;
  font-weight: 500;
  color: white;
  background: var(--accent);
  cursor: pointer;
  box-shadow: none;
  transition: background 150ms ease, border-color 150ms ease;
}

button:hover {
  background: var(--accent-hover);
}

button:active {
  background: var(--accent-hover);
}

button.secondary {
  color: var(--ink);
  background: #f3f3ef;
  border-color: #d9d9d4;
}

button.secondary:hover {
  background: #ebebe5;
}

.family-card {
  padding: 16px;
  margin-bottom: 16px;
}

.family-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.family-card h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.family-stats {
  color: var(--muted);
  font-size: 0.88rem;
}

.family-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-level {
  min-width: 52px;
  text-align: center;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 600;
}

.svg-wrap {
  overflow: auto;
  border-radius: 8px;
  border: 1px solid #e5e5df;
  background: #ffffff;
  padding: 4px;
}

.family-insights-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.insight-card {
  border: 1px solid #e6e6e0;
  border-radius: 10px;
  background: #fbfbf8;
  padding: 14px;
}

.insight-card--wide {
  grid-column: span 2;
}

.insight-card--full {
  grid-column: 1 / -1;
}

.insight-card h3 {
  margin: 0 0 4px;
  font-size: 0.92rem;
  font-weight: 650;
}

.insight-card p {
  margin: 0;
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.45;
}

.insight-metrics {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(86px, 1fr));
  gap: 8px;
}

.mini-metric {
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e6e6e0;
}

.mini-metric span {
  display: block;
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.mini-metric strong {
  display: block;
  margin-top: 4px;
  font-size: 1.05rem;
  letter-spacing: -0.01em;
}

.insight-table-wrap {
  margin-top: 10px;
  overflow-x: auto;
}

.insight-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.insight-table th,
.insight-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e8e8e2;
  text-align: left;
  white-space: nowrap;
}

.insight-table th {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.insight-table tbody tr:last-child td {
  border-bottom: 0;
}

.branch-list,
.flag-list,
.id-pill-list {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}

.branch-list,
.flag-list {
  display: grid;
  gap: 8px;
}

.flag-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.branch-item,
.flag-item,
.transmission-card {
  border: 1px solid #e6e6e0;
  border-radius: 8px;
  background: #ffffff;
  padding: 10px 12px;
}

.branch-item strong,
.flag-item strong,
.transmission-card h4 {
  display: block;
  margin: 0;
  font-size: 0.86rem;
  font-weight: 650;
}

.branch-item span,
.flag-item span,
.transmission-card p {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.45;
}

.flag-severity {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 74px;
  margin: 0 0 6px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.flag-item[data-severity="warning"] .flag-severity {
  background: rgba(153, 107, 0, 0.12);
  color: var(--warning);
}

.flag-item[data-severity="notice"] .flag-severity {
  background: rgba(13, 91, 135, 0.1);
  color: var(--accent);
}

.transmission-groups {
  display: grid;
  gap: 8px;
}

.id-pill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.id-pill-list li {
  padding: 4px 8px;
  border-radius: 999px;
  background: #f2f4f5;
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 600;
}

svg {
  display: block;
}

.family-boundary {
  fill: none;
  stroke: #ecece6;
  stroke-width: 1.2;
  opacity: 1;
}

.connector,
.union {
  fill: none;
  stroke: var(--line);
  stroke-width: 1.8;
  stroke-linecap: square;
  stroke-linejoin: miter;
  opacity: 1;
}

.union {
  stroke-width: 2;
}

.relationship {
  transition: opacity 140ms ease;
}

.relationship line {
  transition: stroke 140ms ease, stroke-width 140ms ease, opacity 140ms ease;
}

.relationship [data-role="partner-line"],
.relationship [data-role="relationship-bridge"],
.relationship [data-role="sibship-line"] {
  cursor: ns-resize;
  pointer-events: stroke;
  touch-action: none;
}

.relationship.is-faded {
  opacity: 0.14;
}

.relationship[data-distance="0"] line,
.relationship[data-distance="1"] line {
  stroke: var(--highlight-strong);
}

.relationship[data-distance="2"] line {
  stroke: var(--highlight-mid);
}

.relationship[data-distance="3"] line {
  stroke: var(--highlight-soft);
}

.relationship[data-distance="4"] line,
.relationship[data-distance="5"] line,
.relationship[data-distance="6"] line {
  stroke: var(--highlight-faint);
}

.person {
  cursor: grab;
  touch-action: none;
  transition: opacity 140ms ease;
}

.person.dragging {
  cursor: grabbing;
}

.person.is-faded {
  opacity: 0.18;
}

.person-shape {
  stroke-width: 1.8;
  filter: none;
  transition: stroke 120ms ease, stroke-width 120ms ease, fill 120ms ease;
}

.person:hover .person-shape {
  stroke-width: 2.2;
}

.person--male .person-shape {
  fill: var(--male-fill);
  stroke: var(--male-border);
}

.person--female .person-shape {
  fill: var(--female-fill);
  stroke: var(--female-border);
}

.person--unknown .person-shape {
  fill: var(--unknown-fill);
  stroke: var(--unknown-border);
}

.person[data-affected-status="affected"].person--male .person-shape {
  fill: var(--male-affected-fill);
}

.person[data-affected-status="affected"].person--female .person-shape {
  fill: var(--female-affected-fill);
}

.person[data-affected-status="affected"].person--unknown .person-shape {
  fill: var(--unknown-affected-fill);
}

.person[data-anomaly-count]:not([data-anomaly-count="0"]) .person-shape {
  stroke-dasharray: 2.4 1.4;
}

.person.selected .person-shape {
  stroke: var(--accent);
  stroke-width: 2.4;
}

.person[data-distance="0"] .person-shape {
  stroke: var(--highlight-strong);
  stroke-width: 2.8;
}

.person[data-distance="1"] .person-shape {
  stroke: var(--highlight-strong);
  stroke-width: 2.4;
}

.person[data-distance="2"] .person-shape {
  stroke: var(--highlight-mid);
  stroke-width: 2.2;
}

.person[data-distance="3"] .person-shape {
  stroke: var(--highlight-soft);
  stroke-width: 2;
}

.person[data-distance="4"] .person-shape,
.person[data-distance="5"] .person-shape,
.person[data-distance="6"] .person-shape {
  stroke: var(--highlight-faint);
  stroke-width: 1.9;
}

.person-label {
  font-size: 10.5px;
  font-weight: 500;
  text-anchor: middle;
  fill: var(--ink);
  pointer-events: none;
  user-select: none;
  transition: fill 120ms ease, opacity 120ms ease, font-weight 120ms ease;
}

.coefficient-label {
  display: none;
  font-size: 8px;
  font-weight: 700;
  text-anchor: middle;
  dominant-baseline: middle;
  alignment-baseline: middle;
  fill: var(--ink);
  pointer-events: none;
  user-select: none;
}

.person[data-affected-status="affected"] .coefficient-label {
  fill: #ffffff;
}

.person[data-distance="0"] .person-label {
  fill: var(--highlight-strong);
  font-weight: 650;
}

.person[data-distance="1"] .person-label {
  fill: var(--accent-hover);
  font-weight: 600;
}

.person.is-faded .person-label {
  opacity: 0.46;
}

/* Clinical Symbology */
.deceased-slash {
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: square;
  pointer-events: none;
}

.proband-indicator {
  pointer-events: none;
}

.proband-indicator line {
  stroke: var(--ink);
  stroke-width: 2;
  stroke-linecap: round;
}

.proband-label {
  font-size: 11px;
  font-weight: 700;
  fill: var(--ink);
  text-anchor: middle;
  dominant-baseline: central;
  user-select: none;
}

.carrier-fill {
  pointer-events: none;
}

.person--male .carrier-fill {
  fill: var(--male-affected-fill);
}

.person--female .carrier-fill {
  fill: var(--female-affected-fill);
}

.person--unknown .carrier-fill {
  fill: var(--unknown-affected-fill);
}

/* Multi-line labels */
.person-sublabel {
  font-size: 9px;
  text-anchor: middle;
  dominant-baseline: central;
  fill: var(--muted);
  font-weight: 500;
  pointer-events: none;
  user-select: none;
}

.person-genotype-label {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  font-size: 9.5px;
  font-weight: 600;
  fill: var(--accent);
}

.person-genotype-label[data-genotype="1/1"],
.person-genotype-label[data-genotype="HOM_ALT"] {
  fill: var(--error);
  font-weight: 700;
}

.person-genotype-label[data-genotype="0/1"],
.person-genotype-label[data-genotype="HET"] {
  fill: #7c3aed;
  font-weight: 600;
}

.person-genotype-label[data-genotype="0/0"],
.person-genotype-label[data-genotype="HOM_REF"] {
  fill: var(--muted);
}

body.hide-genotypes .person-genotype-label {
  display: none;
}

.segregation-card {
  background: rgba(31, 35, 40, 0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 12px;
}

.segregation-mode {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 6px;
}

.segregation-list {
  margin: 0;
  padding-left: 18px;
  font-size: 0.82rem;
  color: var(--ink);
  line-height: 1.45;
}

.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 500;
  margin-top: 14px;
}

.legend span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend span::before {
  content: "";
  display: inline-block;
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  border-width: 1.6px;
  border-style: solid;
}

.legend .male::before {
  background: var(--male-fill);
  border-color: var(--male-border);
  border-radius: 2px;
}

.legend .female::before {
  border-radius: 50%;
  background: var(--female-fill);
  border-color: var(--female-border);
}

.legend .unknown::before {
  transform: rotate(45deg);
  background: var(--unknown-fill);
  border-color: var(--unknown-border);
}

.legend .affected::before {
  background: var(--highlight-strong);
  border-color: var(--highlight-strong);
  border-radius: 2px;
}

.legend .unaffected::before {
  background: #ffffff;
  border-color: #8c877c;
  border-radius: 2px;
}

.legend .carrier::before {
  border-radius: 2px;
  background: linear-gradient(to right, var(--ink) 50%, #ffffff 50%);
  border-color: #8c877c;
}

.legend .proband::before {
  content: "P ↗";
  border: none;
  font-size: 11px;
  font-weight: 700;
  color: var(--ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.legend .deceased::before {
  content: "/";
  border: none;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.messages {
  margin-top: 16px;
  padding: 0;
  list-style: none;
}

.messages li {
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  border-left: 3px solid;
}

.messages .warning {
  background: rgba(153, 107, 0, 0.08);
  color: var(--warning);
  border-color: var(--warning);
}

.messages .error {
  background: rgba(163, 54, 47, 0.08);
  color: var(--error);
  border-color: var(--error);
}

.details {
  position: sticky;
  top: 24px;
  align-self: start;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 18px;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.details::-webkit-scrollbar {
  width: 6px;
}

.details::-webkit-scrollbar-track {
  background: transparent;
}

.details::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

.details::-webkit-scrollbar-thumb:hover {
  background: var(--muted);
}

.details h2 {
  margin: 0 0 6px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.details h3 {
  margin: 18px 0 10px;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
}

.details dl {
  margin: 16px 0 0;
}

.details dt {
  margin-top: 14px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.details dd {
  margin: 6px 0 0;
  font-size: 0.95rem;
  font-weight: 500;
}

.relatedness-groups {
  display: grid;
  gap: 10px;
}

.relatedness-group {
  border: 1px solid #e5e5df;
  border-radius: 8px;
  background: #fbfbf8;
  overflow: hidden;
}

.relatedness-group summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.relatedness-group summary span:last-child {
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 500;
}

.relatedness-group ul {
  margin: 0;
  padding: 0 12px 12px 28px;
}

.relatedness-group li + li {
  margin-top: 6px;
}

.tooltip {
  position: fixed;
  pointer-events: none;
  z-index: 10;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(24, 24, 24, 0.96);
  color: white;
  font-size: 0.8rem;
  font-weight: 500;
  line-height: 1.35;
  max-width: min(500px, 90vw);
  white-space: pre-line;
  opacity: 0;
  transform: translate(12px, 12px);
  transition: none;
  box-shadow: var(--shadow-md);
}

@media (max-width: 980px) {
  .page {
    grid-template-columns: 1fr;
  }

  .details {
    position: static;
    max-height: none;
    overflow-y: visible;
  }

  .insight-card--wide {
    grid-column: auto;
  }

  .insight-card--full {
    grid-column: auto;
  }

  .flag-list {
    grid-template-columns: 1fr;
  }
}

@media print {
  .details {
    position: static;
    max-height: none;
    overflow: visible;
    box-shadow: none;
  }
}
"""

JS = """
const data = window.PEDVIEW_DATA || window.PEDIVIZ_DATA;
const tooltip = document.getElementById("tooltip");
const details = document.getElementById("person-details");
let selectedNode = null;
let selectedPerson = null;
let activeDrag = null;
const EXPORT_SCALE = 4;
const MIN_ZOOM = 0.65;
const MAX_ZOOM = 2.4;
const ZOOM_STEP = 1.2;
const NODE_SIZE = data.node_size || 24;
const NODE_HALF = NODE_SIZE / 2;
const RELATIONSHIP_DROP = 18;
const SIBSHIP_DROP = 16;
const LANE_TOP_PADDING = 8;
const LANE_BOTTOM_PADDING = 10;
const PARTNER_ROUTING_THRESHOLD = 126;
const PARTNER_LANE_OFFSET = 2;
const PARTNER_LANE_SPACING = 6;
const FAMILY_BOUNDARY_INSET = 12;
const PERSON_DRAG_PADDING = NODE_HALF + 18;
const RELEASE_FIT_PADDING = 60;
const DRAG_SCROLL_EDGE = 72;
const DRAG_SCROLL_STEP = 26;
const DRAG_EXPAND_PADDING = 26;
const DRAG_EXPAND_STEP = 96;
const familyStates = {};

const SCREEN_EXPORT_STYLES = `
svg { background: white; }
.family-boundary { fill: none; stroke: #ecece6; stroke-width: 1.2; opacity: 1; }
.connector,
.union { fill: none; stroke: #5f5f5f; stroke-linecap: square; stroke-linejoin: miter; opacity: 1; }
.connector { stroke-width: 1.8; }
.union { stroke-width: 2; }
.person-shape { stroke-width: 1.8; }
.person--male .person-shape { fill: #e8f0f6; stroke: #5a7890; }
.person--female .person-shape { fill: #f6e7ee; stroke: #bb7b96; }
.person--unknown .person-shape { fill: #f0efe9; stroke: #8c877c; }
.person[data-affected-status="affected"].person--male .person-shape { fill: #9cbcd1; }
.person[data-affected-status="affected"].person--female .person-shape { fill: #ddb0c5; }
.person[data-affected-status="affected"].person--unknown .person-shape { fill: #cbc5bb; }
.person-label {
  fill: #181818;
  font: 500 10.5px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  text-anchor: middle;
}
.coefficient-label {
  display: none;
  fill: #181818;
  font: 700 6.2px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  text-anchor: middle;
  dominant-baseline: middle;
  alignment-baseline: middle;
  pointer-events: none;
}
.person[data-affected-status="affected"] .coefficient-label { fill: #ffffff; }
.deceased-slash { stroke: #181818; stroke-width: 2; stroke-linecap: square; }
.proband-indicator line { stroke: #181818; stroke-width: 2; stroke-linecap: round; }
.proband-label { fill: #181818; font-weight: bold; font-size: 11px; text-anchor: middle; dominant-baseline: central; }
.carrier-fill { fill: #5a7890; }
.person--female .carrier-fill { fill: #bb7b96; }
.person--unknown .carrier-fill { fill: #8c877c; }
.person-sublabel { fill: #555555; font: 500 9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; text-anchor: middle; }
.person-genotype-label { font-family: monospace; font-size: 9.5px; font-weight: bold; fill: #7c3aed; }
`;

const JOURNAL_EXPORT_STYLES = `
svg { background: white; }
.family-boundary { fill: none; stroke: #c6c6c6; stroke-width: 1; opacity: 1; }
.connector,
.union {
  fill: none;
  stroke: black;
  stroke-width: 1.8;
  stroke-linecap: square;
  stroke-linejoin: miter;
  opacity: 1;
}
.union { stroke-width: 2; }
.person-shape {
  fill: white;
  stroke: black;
  stroke-width: 1.8;
  filter: none;
}
.person[data-affected-status="affected"] .person-shape { fill: black; }
.deceased-slash { stroke: black; stroke-width: 2; stroke-linecap: square; }
.proband-indicator line { stroke: black; stroke-width: 2; stroke-linecap: round; }
.proband-label { fill: black; font-weight: bold; font-size: 11px; text-anchor: middle; dominant-baseline: central; font-family: Arial, sans-serif; }
.carrier-fill { fill: black; }
.person-label {
  fill: black;
  font: 500 10.5px Arial, sans-serif;
  text-anchor: middle;
}
.person-sublabel { fill: black; font: 500 9px Arial, sans-serif; text-anchor: middle; }
.person-genotype-label { fill: black; font-weight: bold; font-family: monospace; font-size: 9.5px; }
.coefficient-label {
  display: none;
  fill: black;
  font: 700 6.2px Arial, sans-serif;
  text-anchor: middle;
  dominant-baseline: middle;
  alignment-baseline: middle;
}
.person[data-affected-status="affected"] .coefficient-label { fill: white; }
`;

function toTitle(label) {
  return label.replace(/_/g, " ").replace(/\\b\\w/g, ch => ch.toUpperCase());
}

function formatCoefficientText(value, { compact = false, precision = 2 } = {}) {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "";
  }
  const formatted = value.toFixed(precision);
  if (compact && value >= 0 && value < 1) {
    return formatted.replace(/^0/, "");
  }
  return formatted;
}

function relatednessForPerson(state, personId) {
  if (!state || !personId) {
    return {};
  }
  return state.wrightRelatedness?.[personId] || {};
}

function groupedRelativesForPerson(relatedness, selectedPersonId) {
  const grouped = new Map();
  Object.entries(relatedness)
    .filter(([relativeId, value]) => relativeId !== selectedPersonId && value > 0)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .forEach(([relativeId, value]) => {
      const roundedValue = Number.parseFloat(value.toFixed(4));
      const scoreKey = roundedValue.toFixed(4);
      if (!grouped.has(scoreKey)) {
        grouped.set(scoreKey, {
          label: formatCoefficientText(roundedValue, { precision: 4 }),
          value: roundedValue,
          relatives: [],
        });
      }
      grouped.get(scoreKey).relatives.push(relativeId);
    });
  return Array.from(grouped.values()).sort(
    (left, right) => right.value - left.value || left.label.localeCompare(right.label),
  );
}

function clearCoefficientLabels(state) {
  if (!state) {
    return;
  }
  state.svg.querySelectorAll(".coefficient-label").forEach(node => {
    node.textContent = "";
    node.style.display = "none";
  });
}

function clearAllCoefficientLabels() {
  Object.values(familyStates).forEach(clearCoefficientLabels);
}

function applyCoefficientLabels(state, selectedPersonId) {
  if (!state) {
    return;
  }
  const relatedness = relatednessForPerson(state, selectedPersonId);
  state.svg.querySelectorAll(".person").forEach(node => {
    const label = node.querySelector(".coefficient-label");
    if (!label) {
      return;
    }
    const personId = node.dataset.personId;
    const coefficient = relatedness[personId];
    if (coefficient === undefined || coefficient <= 0) {
      label.textContent = "";
      label.style.display = "none";
      return;
    }
    label.textContent = formatCoefficientText(coefficient, { compact: true });
    label.style.display = "inline";
  });
}

function renderDetails(person) {
  if (!person) {
    details.innerHTML = "<h2>Select an individual</h2><p>Click a person to inspect metadata, transmission summaries, anomaly flags, and Wright relatedness coefficients. You can also drag nodes horizontally, search for an ID, or move horizontal relationship lines vertically to refine spacing.</p>";
    return;
  }

  const state = familyStates[person.family_id];
  const relatedness = relatednessForPerson(state, person.person_id);
  const selfRelatedness = relatedness[person.person_id] ?? 1;
  const wrightSettings = state?.wrightSettings || { ancestor_inbreeding: 0, used_default: true };
  const transmissionSummary = person.transmission_summary || null;
  const anomalyFlags = person.anomaly_flags || [];
  const dl = document.createElement("dl");
  const orderedEntries = [
    ["Family", person.family_id],
    ["Individual", person.person_id],
    ["Sex", person.sex],
    ["Generation", person.generation ?? "Unknown"],
    ["Father", person.father_id || "Unknown"],
    ["Mother", person.mother_id || "Unknown"],
    ["Wright Self", formatCoefficientText(selfRelatedness, { precision: 4 })],
    [
      "Ancestor f_a",
      `${formatCoefficientText(wrightSettings.ancestor_inbreeding, { precision: 4 })}${wrightSettings.used_default ? " (default)" : ""}`,
    ],
  ];

  if (person.affected_status) {
    orderedEntries.splice(3, 0, ["Affected Status", toTitle(person.affected_status)]);
  }

  if (person.age !== undefined && person.age !== null && person.age !== "") {
    orderedEntries.push(["Age", person.age]);
  }
  if (person.genotype) {
    orderedEntries.push(["Genotype", person.genotype]);
  }
  if (person.proband) {
    orderedEntries.push(["Proband", "Yes"]);
  }
  if (person.deceased) {
    orderedEntries.push(["Deceased", "Yes"]);
  }
  if (person.carrier) {
    orderedEntries.push(["Carrier", "Yes"]);
  }

  if (person.metadata) {
    for (const [key, value] of Object.entries(person.metadata)) {
      orderedEntries.push([toTitle(key), value]);
    }
  }

  for (const [label, value] of orderedEntries) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    dl.append(dt, dd);
  }

  details.innerHTML = "";
  const heading = document.createElement("h2");
  heading.textContent = `${person.family_id} / ${person.person_id}`;
  const subcopy = document.createElement("p");
  subcopy.textContent = "Closer relatives are highlighted more strongly than distant generations, and Wright relatedness coefficients appear on the selected family.";
  details.append(heading, subcopy, dl);

  if (transmissionSummary) {
    const transmissionHeading = document.createElement("h3");
    transmissionHeading.textContent = "Transmission Summary";
    details.append(transmissionHeading);

    const groups = document.createElement("div");
    groups.className = "transmission-groups";
    [
      ["Parents", transmissionSummary.parents],
      ["Siblings", transmissionSummary.siblings],
      ["Children", transmissionSummary.children],
      ["Descendants", transmissionSummary.descendants],
      ["First-Degree", transmissionSummary.first_degree],
    ].forEach(([label, summary]) => {
      if (!summary) {
        return;
      }
      const card = document.createElement("section");
      card.className = "transmission-card";
      const cardHeading = document.createElement("h4");
      cardHeading.textContent = label;
      const summaryCopy = document.createElement("p");
      summaryCopy.textContent = transmissionSummaryText(summary);
      card.append(cardHeading, summaryCopy);
      const ids = Array.isArray(summary.ids) ? summary.ids : [];
      if (ids.length) {
        card.append(buildIdPillList(ids));
      }
      groups.append(card);
    });

    if (Array.isArray(transmissionSummary.partners) && transmissionSummary.partners.length) {
      const partnerCard = document.createElement("section");
      partnerCard.className = "transmission-card";
      const partnerHeading = document.createElement("h4");
      partnerHeading.textContent = "Partners";
      const partnerCopy = document.createElement("p");
      partnerCopy.textContent = `${transmissionSummary.partners.length} recorded`;
      partnerCard.append(partnerHeading, partnerCopy, buildIdPillList(transmissionSummary.partners));
      groups.append(partnerCard);
    }
    details.append(groups);
  }

  const flagHeading = document.createElement("h3");
  flagHeading.textContent = "Anomaly Flags";
  details.append(flagHeading);
  if (!anomalyFlags.length) {
    const emptyFlags = document.createElement("p");
    emptyFlags.textContent = "No pedigree anomaly flags were triggered for this individual.";
    details.append(emptyFlags);
  } else {
    details.append(buildFlagList(anomalyFlags));
  }

  if (state?.segregation) {
    const seg = state.segregation;
    const segHeading = document.createElement("h3");
    segHeading.textContent = "Variant Segregation";
    details.append(segHeading);

    const card = document.createElement("section");
    card.className = "segregation-card";

    const modeBadge = document.createElement("div");
    modeBadge.className = "segregation-mode";
    modeBadge.textContent = `${seg.variant_name || "Variant"}: ${seg.mode}`;
    card.append(modeBadge);

    const list = document.createElement("ul");
    list.className = "segregation-list";

    if (person.genotype) {
      const gtItem = document.createElement("li");
      let gtDesc = `Individual genotype: ${person.genotype}`;
      if (seg.de_novo_ids?.includes(person.person_id)) {
        gtDesc += " — Candidate De Novo Mutation";
      } else if (seg.hom_alt_ids?.includes(person.person_id)) {
        gtDesc += " — Homozygous Alternate";
      } else if (seg.carrier_ids?.includes(person.person_id)) {
        gtDesc += " — Heterozygous Carrier";
      } else if (seg.hom_ref_ids?.includes(person.person_id)) {
        gtDesc += " — Homozygous Reference";
      }
      gtItem.textContent = gtDesc;
      list.append(gtItem);
    }

    const cohortItem = document.createElement("li");
    cohortItem.textContent = `Family: ${seg.total_genotyped} genotyped (${seg.carrier_ids.length} het, ${seg.hom_alt_ids.length} hom-alt).`;
    list.append(cohortItem);

    card.append(list);
    details.append(card);
  }

  const relatives = groupedRelativesForPerson(relatedness, person.person_id);
  const relatednessHeading = document.createElement("h3");
  relatednessHeading.textContent = "Wright Relatedness";
  details.append(relatednessHeading);
  if (!relatives.length) {
    const emptyState = document.createElement("p");
    emptyState.textContent = "No positive Wright relatedness coefficients were found beyond the selected individual.";
    details.append(emptyState);
    return;
  }

  const groups = document.createElement("div");
  groups.className = "relatedness-groups";
  relatives.forEach((group, index) => {
    const dropdown = document.createElement("details");
    dropdown.className = "relatedness-group";
    dropdown.open = index === 0;

    const summary = document.createElement("summary");
    const score = document.createElement("span");
    score.textContent = group.label;
    const count = document.createElement("span");
    count.textContent = `${group.relatives.length} ${group.relatives.length === 1 ? "individual" : "individuals"}`;
    summary.append(score, count);

    const list = document.createElement("ul");
    group.relatives.forEach(relativeId => {
      const item = document.createElement("li");
      item.textContent = relativeId;
      list.append(item);
    });

    dropdown.append(summary, list);
    groups.append(dropdown);
  });
  details.append(groups);
}

function tooltipTextFromPayload(payload) {
  if (typeof payload === "string") {
    return payload;
  }
  if (payload && typeof payload === "object" && payload.person_id) {
    return `${payload.person_id} (${payload.sex || "unknown"})`;
  }
  if (payload === undefined || payload === null) {
    return "";
  }
  return String(payload);
}

function showTooltip(event, payload) {
  const text = tooltipTextFromPayload(payload);
  if (!text) {
    hideTooltip();
    return;
  }
  tooltip.textContent = text;
  tooltip.style.opacity = "1";
  moveTooltip(event);
}

function showPersonTooltip(event, person) {
  showTooltip(event, person);
}

function moveTooltip(event) {
  tooltip.style.left = `${event.clientX}px`;
  tooltip.style.top = `${event.clientY}px`;
}

function hideTooltip() {
  tooltip.style.opacity = "0";
}

function selectorEscape(value) {
  return String(value).replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"');
}

function normalizeSearchValue(value) {
  return String(value || "").trim().toLowerCase();
}

function transmissionSummaryText(summary) {
  const parts = [`${summary.total || 0} recorded`];
  if (summary.affected) {
    parts.push(`${summary.affected} affected`);
  }
  if (summary.unaffected) {
    parts.push(`${summary.unaffected} unaffected`);
  }
  if (summary.unknown_status) {
    parts.push(`${summary.unknown_status} unknown status`);
  }
  return parts.join(" · ");
}

function buildIdPillList(ids) {
  const list = document.createElement("ul");
  list.className = "id-pill-list";
  ids.forEach(id => {
    const item = document.createElement("li");
    item.textContent = id;
    list.append(item);
  });
  return list;
}

function buildFlagList(flags) {
  const list = document.createElement("ul");
  list.className = "flag-list";
  flags.forEach(flag => {
    const item = document.createElement("li");
    item.className = "flag-item";
    item.dataset.severity = flag.severity || "notice";

    const severity = document.createElement("span");
    severity.className = "flag-severity";
    severity.textContent = toTitle(flag.severity || "notice");

    const subject = document.createElement("strong");
    subject.textContent = flag.person_id || "Family";

    const message = document.createElement("span");
    const related = Array.isArray(flag.related_ids) && flag.related_ids.length
      ? ` Related: ${flag.related_ids.join(", ")}.`
      : "";
    message.textContent = `${flag.message}${related}`;

    item.append(severity, subject, message);
    list.append(item);
  });
  return list;
}

function parseSvgSize(svg) {
  const viewBox = svg.viewBox && svg.viewBox.baseVal;
  if (viewBox && viewBox.width && viewBox.height) {
    return { width: viewBox.width, height: viewBox.height };
  }
  return {
    width: Number.parseFloat(svg.getAttribute("width")) || svg.getBoundingClientRect().width || 1,
    height: Number.parseFloat(svg.getAttribute("height")) || svg.getBoundingClientRect().height || 1,
  };
}

function buildExportSvgMarkup(svg, { journal = false } = {}) {
  const clone = svg.cloneNode(true);
  const { width, height } = parseSvgSize(svg);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", `${width}`);
  clone.setAttribute("height", `${height}`);
  clone.removeAttribute("style");
  clone.querySelectorAll("title").forEach(node => node.remove());
  clone.querySelectorAll(".person").forEach(node => {
    node.classList.remove("selected", "dragging");
    node.classList.remove("is-faded");
    node.removeAttribute("data-distance");
  });
  clone.querySelectorAll(".relationship").forEach(node => {
    node.classList.remove("is-faded");
    node.removeAttribute("data-distance");
  });

  if (journal) {
    clone.querySelectorAll(".person--male .person-shape").forEach(node => node.setAttribute("rx", "0"));
    clone.querySelectorAll(".family-boundary").forEach(node => node.setAttribute("rx", "0"));
  }

  const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
  style.textContent = journal ? JOURNAL_EXPORT_STYLES : SCREEN_EXPORT_STYLES;
  clone.insertBefore(style, clone.firstChild);
  return new XMLSerializer().serializeToString(clone);
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadSvg(svg, filename, options = {}) {
  const markup = buildExportSvgMarkup(svg, options);
  const blob = new Blob([markup], { type: "image/svg+xml;charset=utf-8" });
  triggerDownload(blob, filename);
}

async function downloadPng(svg, filename, { journal = false, scale = EXPORT_SCALE } = {}) {
  const markup = buildExportSvgMarkup(svg, { journal });
  const svgBlob = new Blob([markup], { type: "image/svg+xml;charset=utf-8" });
  const svgUrl = URL.createObjectURL(svgBlob);
  const { width, height } = parseSvgSize(svg);

  try {
    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("The pedigree image could not be rasterized for PNG export."));
      img.src = svgUrl;
    });

    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Canvas export is unavailable in this browser.");
    }

    context.fillStyle = "white";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    const pngBlob = await new Promise((resolve, reject) => {
      canvas.toBlob(blob => {
        if (blob) {
          resolve(blob);
          return;
        }
        reject(new Error("PNG export failed."));
      }, "image/png");
    });

    triggerDownload(pngBlob, filename);
  } catch (error) {
    window.alert(error.message);
  } finally {
    URL.revokeObjectURL(svgUrl);
  }
}

function findFamilySvg(familyId) {
  return document.querySelector(`svg[data-family-id="${familyId}"]`);
}

function clientToSvgPoint(svg, clientX, clientY) {
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  return point.matrixTransform(svg.getScreenCTM().inverse());
}

function applyLine(line, coordinates) {
  if (!line) {
    return;
  }
  if (!coordinates) {
    line.style.display = "none";
    return;
  }
  line.style.display = "";
  line.setAttribute("x1", coordinates.x1.toFixed(1));
  line.setAttribute("y1", coordinates.y1.toFixed(1));
  line.setAttribute("x2", coordinates.x2.toFixed(1));
  line.setAttribute("y2", coordinates.y2.toFixed(1));
}

function buildFamilyStates() {
  Object.entries(data.families).forEach(([familyId, family]) => {
    const svg = findFamilySvg(familyId);
    if (!svg) {
      return;
    }
    const people = {};
    family.person_ids.forEach(personId => {
      const person = data.people[`${familyId}::${personId}`];
      people[personId] = {
        x: person.x,
        y: person.y,
        generation: person.generation,
      };
    });
    familyStates[familyId] = {
      svg,
      wrap: svg.closest(".svg-wrap"),
      width: family.width,
      height: family.height,
      minWidth: family.width,
      people,
      relationships: family.relationships,
      relationshipById: Object.fromEntries(
        family.relationships.map(relationship => [relationship.relationship_id, relationship]),
      ),
      relationshipAdjustments: {},
      wrightRelatedness: family.wright_relatedness || {},
      wrightSettings: family.wright_settings || { ancestor_inbreeding: 0, used_default: true },
      adjacency: buildKinshipGraph(family),
      segregation: family.segregation || null,
      zoom: 1,
    };
    applyZoom(familyStates[familyId]);
    renderFamily(familyId);
  });
}

function buildKinshipGraph(family) {
  const adjacency = Object.fromEntries(
    family.person_ids.map(personId => [personId, new Set()]),
  );

  function connect(leftId, rightId) {
    if (!leftId || !rightId || !adjacency[leftId] || !adjacency[rightId]) {
      return;
    }
    adjacency[leftId].add(rightId);
    adjacency[rightId].add(leftId);
  }

  family.relationships.forEach(relationship => {
    const parentIds = [relationship.father_id, relationship.mother_id].filter(
      personId => personId && adjacency[personId],
    );
    const childIds = relationship.child_ids.filter(personId => adjacency[personId]);

    if (parentIds.length === 2) {
      connect(parentIds[0], parentIds[1]);
    }

    parentIds.forEach(parentId => {
      childIds.forEach(childId => connect(parentId, childId));
    });
  });

  return adjacency;
}

function clampDistance(distance) {
  return Math.min(distance, 6);
}

function computeKinshipDistances(state, startPersonId) {
  const distances = {};
  if (!state || !state.adjacency[startPersonId]) {
    return distances;
  }

  const queue = [startPersonId];
  distances[startPersonId] = 0;

  while (queue.length) {
    const personId = queue.shift();
    const nextDistance = distances[personId] + 1;
    state.adjacency[personId].forEach(neighborId => {
      if (distances[neighborId] !== undefined) {
        return;
      }
      distances[neighborId] = nextDistance;
      queue.push(neighborId);
    });
  }

  return distances;
}

function clearFamilyHighlight(state) {
  if (!state) {
    return;
  }
  state.svg.querySelectorAll(".person").forEach(node => {
    node.classList.remove("is-faded");
    node.removeAttribute("data-distance");
  });
  state.svg.querySelectorAll(".relationship").forEach(node => {
    node.classList.remove("is-faded");
    node.removeAttribute("data-distance");
  });
}

function clearAllHighlights() {
  Object.values(familyStates).forEach(clearFamilyHighlight);
}

function highlightDistanceForRelationship(relationship, distances) {
  const participantIds = [
    relationship.father_id,
    relationship.mother_id,
    ...relationship.child_ids,
  ].filter(Boolean);
  let best = Infinity;
  participantIds.forEach(personId => {
    if (distances[personId] !== undefined) {
      best = Math.min(best, distances[personId]);
    }
  });
  return Number.isFinite(best) ? clampDistance(best) : null;
}

function applyFamilyHighlight(state, selectedPersonId) {
  if (!state) {
    return;
  }

  const distances = computeKinshipDistances(state, selectedPersonId);
  state.svg.querySelectorAll(".person").forEach(node => {
    const distance = distances[node.dataset.personId];
    if (distance === undefined) {
      node.classList.add("is-faded");
      node.removeAttribute("data-distance");
      return;
    }
    node.classList.remove("is-faded");
    node.dataset.distance = String(clampDistance(distance));
  });

  state.svg.querySelectorAll(".relationship").forEach(group => {
    const relationship = state.relationshipById[group.dataset.relationshipId];
    const distance = relationship ? highlightDistanceForRelationship(relationship, distances) : null;
    if (distance === null) {
      group.classList.add("is-faded");
      group.removeAttribute("data-distance");
      return;
    }
    group.classList.remove("is-faded");
    group.dataset.distance = String(distance);
  });
}

function zoomLabel(familyId) {
  return document.querySelector(`[data-zoom-level-family="${familyId}"]`);
}

function updateSvgCanvas(state) {
  if (!state) {
    return;
  }
  state.svg.setAttribute("viewBox", `0 0 ${state.width.toFixed(1)} ${state.height.toFixed(1)}`);
  state.svg.setAttribute("width", `${state.width.toFixed(1)}`);
  state.svg.setAttribute("height", `${state.height.toFixed(1)}`);
  const boundary = state.svg.querySelector(".family-boundary");
  if (!boundary) {
    return;
  }
  boundary.setAttribute("x", `${FAMILY_BOUNDARY_INSET}`);
  boundary.setAttribute("y", `${FAMILY_BOUNDARY_INSET}`);
  boundary.setAttribute(
    "width",
    `${Math.max(0, state.width - (FAMILY_BOUNDARY_INSET * 2)).toFixed(1)}`,
  );
  boundary.setAttribute(
    "height",
    `${Math.max(0, state.height - (FAMILY_BOUNDARY_INSET * 2)).toFixed(1)}`,
  );
}

function applyZoom(state) {
  if (!state) {
    return;
  }
  updateSvgCanvas(state);
  state.svg.style.width = `${(state.width * state.zoom).toFixed(1)}px`;
  state.svg.style.height = `${(state.height * state.zoom).toFixed(1)}px`;
  const label = zoomLabel(state.svg.dataset.familyId);
  if (label) {
    label.textContent = `${Math.round(state.zoom * 100)}%`;
  }
}

function setZoom(familyId, nextZoom) {
  const state = familyStates[familyId];
  if (!state) {
    return;
  }
  state.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, nextZoom));
  applyZoom(state);
}

function shiftFamilyHorizontally(state, delta) {
  if (!state || !delta) {
    return;
  }
  Object.values(state.people).forEach(position => {
    position.x += delta;
  });
  state.relationships.forEach(relationship => {
    if (relationship.anchor_x !== undefined && relationship.anchor_x !== null) {
      relationship.anchor_x += delta;
    }
  });
  if (state.wrap) {
    state.wrap.scrollLeft += delta * state.zoom;
  }
}

function familyHorizontalExtents(state) {
  if (!state) {
    return null;
  }
  const xs = [];
  Object.values(state.people).forEach(position => {
    xs.push(position.x);
  });
  state.relationships.forEach(relationship => {
    if (relationship.anchor_x !== undefined && relationship.anchor_x !== null) {
      xs.push(relationship.anchor_x);
    }
  });
  if (!xs.length) {
    return null;
  }
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
  };
}

function autoScrollWrapOnDrag(state, clientX) {
  if (!state?.wrap) {
    return;
  }
  const rect = state.wrap.getBoundingClientRect();
  if (!rect.width) {
    return;
  }
  let delta = 0;
  if (clientX > rect.right - DRAG_SCROLL_EDGE) {
    const ratio = (clientX - (rect.right - DRAG_SCROLL_EDGE)) / DRAG_SCROLL_EDGE;
    delta = Math.min(DRAG_SCROLL_STEP, Math.max(0, ratio * DRAG_SCROLL_STEP));
  } else if (clientX < rect.left + DRAG_SCROLL_EDGE) {
    const ratio = ((rect.left + DRAG_SCROLL_EDGE) - clientX) / DRAG_SCROLL_EDGE;
    delta = -Math.min(DRAG_SCROLL_STEP, Math.max(0, ratio * DRAG_SCROLL_STEP));
  }
  if (delta) {
    state.wrap.scrollLeft += delta;
  }
}

function expandFamilyBoundsForPersonDrag(state, targetX) {
  if (!state) {
    return targetX;
  }
  let nextX = targetX;
  if (nextX < PERSON_DRAG_PADDING) {
    const delta = Math.max(
      DRAG_EXPAND_STEP,
      (PERSON_DRAG_PADDING - nextX) + DRAG_EXPAND_PADDING,
    );
    shiftFamilyHorizontally(state, delta);
    state.width += delta;
    nextX += delta;
    applyZoom(state);
  }
  const rightLimit = state.width - PERSON_DRAG_PADDING;
  if (nextX > rightLimit) {
    const delta = Math.max(
      DRAG_EXPAND_STEP,
      (nextX - rightLimit) + DRAG_EXPAND_PADDING,
    );
    state.width += delta;
    applyZoom(state);
  }
  return nextX;
}

function keepDraggedPersonVisible(state, personId) {
  if (!state?.wrap) {
    return;
  }
  const position = state.people[personId];
  if (!position) {
    return;
  }
  const leftPx = Math.max(0, (position.x - PERSON_DRAG_PADDING) * state.zoom);
  const rightPx = Math.max(0, (position.x + PERSON_DRAG_PADDING) * state.zoom);
  if (leftPx < state.wrap.scrollLeft) {
    state.wrap.scrollLeft = leftPx;
  } else if (rightPx > state.wrap.scrollLeft + state.wrap.clientWidth) {
    state.wrap.scrollLeft = rightPx - state.wrap.clientWidth;
  }
}

function fitFamilyToCurrentContent(state) {
  if (!state) {
    return;
  }
  const extents = familyHorizontalExtents(state);
  if (!extents) {
    return;
  }
  const shiftDelta = RELEASE_FIT_PADDING - extents.minX;
  if (Math.abs(shiftDelta) > 0.1) {
    shiftFamilyHorizontally(state, shiftDelta);
  }
  const fittedMaxX = extents.maxX + shiftDelta;
  state.width = Math.max(
    FAMILY_BOUNDARY_INSET * 2 + NODE_SIZE,
    fittedMaxX + RELEASE_FIT_PADDING,
  );
  applyZoom(state);
  if (state.wrap) {
    const maxScrollLeft = Math.max(0, state.wrap.scrollWidth - state.wrap.clientWidth);
    state.wrap.scrollLeft = Math.max(0, Math.min(state.wrap.scrollLeft, maxScrollLeft));
  }
}

function resolveRelationshipAnchorX(relationship, parentPositions, childPositions = []) {
  if (parentPositions.length === 2) {
    const minX = Math.min(...parentPositions.map(position => position.x));
    const maxX = Math.max(...parentPositions.map(position => position.x));
    const preferredX = relationship.anchor_x ?? (
      parentPositions.reduce((sum, position) => sum + position.x, 0) / parentPositions.length
    );
    return Math.max(minX, Math.min(maxX, preferredX));
  }
  if (parentPositions.length === 1) {
    return parentPositions[0].x;
  }
  if (relationship.anchor_x !== undefined && relationship.anchor_x !== null) {
    return relationship.anchor_x;
  }
  if (childPositions.length) {
    return childPositions.reduce((sum, position) => sum + position.x, 0) / childPositions.length;
  }
  return 0;
}

function shouldRoutePartnerBridge(parentPositions) {
  if (parentPositions.length !== 2) {
    return false;
  }
  const span = Math.abs(parentPositions[0].x - parentPositions[1].x);
  return span > PARTNER_ROUTING_THRESHOLD;
}

function resolveRelationshipDropX(parentPositions, unionX) {
  if (parentPositions.length === 2) {
    return parentPositions.reduce((sum, position) => sum + position.x, 0) / parentPositions.length;
  }
  return unionX;
}

function buildRelationshipLanes(state) {
  const grouped = new Map();
  state.relationships.forEach((relationship, index) => {
    const childPositions = relationship.child_ids
      .map(childId => state.people[childId])
      .filter(Boolean);
    if (!childPositions.length) {
      return;
    }
    const childGeneration = Math.min(...childPositions.map(position => position.generation));
    const parentPositions = [relationship.father_id, relationship.mother_id]
      .map(parentId => (parentId ? state.people[parentId] : null))
      .filter(Boolean);
    const parentGeneration = parentPositions.length
      ? Math.max(...parentPositions.map(position => position.generation))
      : childGeneration - 1;
    const unionX = resolveRelationshipAnchorX(relationship, parentPositions, childPositions);
    const dropX = resolveRelationshipDropX(parentPositions, unionX);
    const intervalStart = Math.min(
      ...childPositions.map(position => position.x),
      dropX,
    );
    const intervalEnd = Math.max(
      ...childPositions.map(position => position.x),
      dropX,
    );
    const groupKey = `${parentGeneration}:${childGeneration}`;
    const entries = grouped.get(groupKey) || [];
    entries.push({
      relationshipId: relationship.relationship_id,
      start: intervalStart,
      end: intervalEnd,
      order: index,
    });
    grouped.set(groupKey, entries);
  });

  const laneMap = {};
  grouped.forEach(entries => {
    const laneEnds = [];
    const assigned = [];
    entries
      .sort((left, right) => left.start - right.start || left.order - right.order)
      .forEach(entry => {
        let lane = 0;
        while (lane < laneEnds.length && entry.start <= laneEnds[lane]) {
          lane += 1;
        }
        if (lane === laneEnds.length) {
          laneEnds.push(entry.end);
        } else {
          laneEnds[lane] = entry.end;
        }
        assigned.push({ relationshipId: entry.relationshipId, lane });
      });

    assigned.forEach(item => {
      laneMap[item.relationshipId] = {
        lane: item.lane,
        laneCount: laneEnds.length,
      };
    });
  });

  return laneMap;
}

function buildPartnerRelationshipLanes(state) {
  const grouped = new Map();
  state.relationships.forEach((relationship, index) => {
    const parentPositions = [relationship.father_id, relationship.mother_id]
      .map(parentId => (parentId ? state.people[parentId] : null))
      .filter(Boolean);
    if (!shouldRoutePartnerBridge(parentPositions)) {
      return;
    }
    const generation = Math.max(...parentPositions.map(position => position.generation));
    const start = Math.min(...parentPositions.map(position => position.x));
    const end = Math.max(...parentPositions.map(position => position.x));
    const entries = grouped.get(generation) || [];
    entries.push({
      relationshipId: relationship.relationship_id,
      start,
      end,
      order: index,
    });
    grouped.set(generation, entries);
  });

  const laneMap = {};
  grouped.forEach(entries => {
    const laneEnds = [];
    const assigned = [];
    entries
      .sort((left, right) => left.start - right.start || left.order - right.order)
      .forEach(entry => {
        let lane = 0;
        while (lane < laneEnds.length && entry.start <= laneEnds[lane]) {
          lane += 1;
        }
        if (lane === laneEnds.length) {
          laneEnds.push(entry.end);
        } else {
          laneEnds[lane] = entry.end;
        }
        assigned.push({ relationshipId: entry.relationshipId, lane });
      });

    assigned.forEach(item => {
      laneMap[item.relationshipId] = {
        lane: item.lane,
        laneCount: laneEnds.length,
      };
    });
  });

  return laneMap;
}

function relationshipLineTarget(line) {
  const role = line.dataset.role;
  if (role === "partner-line") {
    return "partner";
  }
  if (role === "relationship-bridge" || role === "sibship-line") {
    return "spine";
  }
  return null;
}

function describeRelationshipGeometry(state, relationship, laneInfo = { lane: 0, laneCount: 1 }) {
  const father = relationship.father_id ? state.people[relationship.father_id] : null;
  const mother = relationship.mother_id ? state.people[relationship.mother_id] : null;
  const parents = [father, mother].filter(Boolean);
  const parentEntries = [
    relationship.father_id ? { parentId: relationship.father_id, position: father } : null,
    relationship.mother_id ? { parentId: relationship.mother_id, position: mother } : null,
  ].filter(entry => Boolean(entry && entry.position));
  if (!parents.length) {
    return null;
  }

  const unionX = resolveRelationshipAnchorX(
    relationship,
    parents,
    relationship.child_ids
      .map(childId => state.people[childId])
      .filter(Boolean),
  );
  const unionY = Math.max(...parents.map(parent => parent.y)) + NODE_HALF + RELATIONSHIP_DROP;
  const routedPartnerLane = state.partnerLaneMap?.[relationship.relationship_id];
  const routedPartner = shouldRoutePartnerBridge(parents);
  const children = relationship.child_ids
    .map(childId => ({ childId, position: state.people[childId] }))
    .filter(entry => Boolean(entry.position));
  const adjustments = state.relationshipAdjustments?.[relationship.relationship_id] || {};
  const parentBottomY = Math.max(...parents.map(parent => parent.y)) + NODE_HALF;
  const childTopY = children.length
    ? Math.min(...children.map(entry => entry.position.y - NODE_HALF))
    : parentBottomY + 72;
  const partnerMinY = parentBottomY + 2;
  const partnerMaxY = Math.max(partnerMinY, childTopY - 18);
  const defaultPartnerY = routedPartner
    ? Math.min(
        unionY - 4,
        parentBottomY + PARTNER_LANE_OFFSET + (routedPartnerLane?.lane || 0) * PARTNER_LANE_SPACING,
      )
    : null;
  const partnerY = adjustments.partnerY !== undefined
    ? Math.max(partnerMinY, Math.min(partnerMaxY, adjustments.partnerY))
    : defaultPartnerY;
  const routedPartnerLine = father && mother && (routedPartner || adjustments.partnerY !== undefined);
  const relationshipDropX = resolveRelationshipDropX(parents, unionX);
  const relationshipStartY = parents.length === 2
    ? (routedPartnerLine && partnerY !== null ? partnerY : Math.max(...parents.map(parent => parent.y)))
    : unionY;
  const childXs = children.map(entry => entry.position.x);

  let spineY = relationshipStartY + SIBSHIP_DROP;
  if (laneInfo.laneCount > 1) {
    const topY = relationshipStartY + LANE_TOP_PADDING;
    const bottomY = Math.max(topY, childTopY - LANE_BOTTOM_PADDING);
    const ratio = (laneInfo.lane + 1) / (laneInfo.laneCount + 1);
    spineY = topY + (bottomY - topY) * ratio;
  } else {
    const midpointY = relationshipStartY + (childTopY - relationshipStartY) / 2;
    spineY = Math.max(relationshipStartY + 10, Math.min(childTopY - 10, midpointY));
  }
  if (adjustments.spineY !== undefined) {
    const spineMinY = relationshipStartY + 10;
    const spineMaxY = Math.max(spineMinY, childTopY - 10);
    spineY = Math.max(spineMinY, Math.min(spineMaxY, adjustments.spineY));
  }
  const childMinX = childXs.length ? Math.min(...childXs) : unionX;
  const childMaxX = childXs.length ? Math.max(...childXs) : unionX;
  const branchX = Math.max(childMinX, Math.min(childMaxX, unionX));

  return {
    partnerLine: father && mother
      ? (
          routedPartnerLine && partnerY !== null
            ? { x1: Math.min(father.x, mother.x), y1: partnerY, x2: Math.max(father.x, mother.x), y2: partnerY }
            : { x1: father.x, y1: father.y, x2: mother.x, y2: mother.y }
        )
      : null,
    parentLines: Object.fromEntries(
      (routedPartnerLine && partnerY !== null ? parentEntries : []).map(entry => [
        entry.parentId,
        {
          x1: entry.position.x,
          y1: entry.position.y + NODE_HALF,
          x2: entry.position.x,
          y2: partnerY,
        },
      ]),
    ),
    relationshipDrop: children.length
      ? { x1: relationshipDropX, y1: relationshipStartY, x2: relationshipDropX, y2: spineY }
      : null,
    relationshipBridge: children.length && Math.abs(branchX - relationshipDropX) > 0.1
      ? { x1: relationshipDropX, y1: spineY, x2: branchX, y2: spineY }
      : null,
    sibshipLine: children.length
      ? {
          x1: childMinX,
          y1: spineY,
          x2: childMaxX,
          y2: spineY,
        }
      : null,
    childLines: Object.fromEntries(
      children.map(entry => [
        entry.childId,
        {
          x1: entry.position.x,
          y1: spineY,
          x2: entry.position.x,
          y2: entry.position.y - NODE_HALF,
        },
      ]),
    ),
  };
}

function updateRelationship(state, relationship) {
  const group = state.svg.querySelector(
    `[data-relationship-id="${selectorEscape(relationship.relationship_id)}"]`,
  );
  if (!group) {
    return;
  }

  const laneMap = state.laneMap || {};
  const geometry = describeRelationshipGeometry(
    state,
    relationship,
    laneMap[relationship.relationship_id],
  );
  const partnerLine = group.querySelector('[data-role="partner-line"]');
  const relationshipDrop = group.querySelector('[data-role="relationship-drop"]');
  const relationshipBridge = group.querySelector('[data-role="relationship-bridge"]');
  const sibshipLine = group.querySelector('[data-role="sibship-line"]');

  if (!geometry) {
    applyLine(partnerLine, null);
    applyLine(relationshipDrop, null);
    applyLine(relationshipBridge, null);
    applyLine(sibshipLine, null);
    group.querySelectorAll("[data-parent-id]").forEach(line => applyLine(line, null));
    group.querySelectorAll("[data-child-id]").forEach(line => applyLine(line, null));
    return;
  }

  applyLine(partnerLine, geometry.partnerLine);
  applyLine(relationshipDrop, geometry.relationshipDrop);
  applyLine(relationshipBridge, geometry.relationshipBridge);
  applyLine(sibshipLine, geometry.sibshipLine);
  [relationship.father_id, relationship.mother_id].filter(Boolean).forEach(parentId => {
    const line = group.querySelector(`[data-parent-id="${selectorEscape(parentId)}"]`);
    applyLine(line, geometry.parentLines[parentId] || null);
  });
  relationship.child_ids.forEach(childId => {
    const line = group.querySelector(`[data-child-id="${selectorEscape(childId)}"]`);
    applyLine(line, geometry.childLines[childId] || null);
  });
}

function renderFamily(familyId) {
  const state = familyStates[familyId];
  if (!state) {
    return;
  }

  Object.entries(state.people).forEach(([personId, position]) => {
    const node = state.svg.querySelector(`[data-person-id="${selectorEscape(personId)}"]`);
    if (!node) {
      return;
    }
    node.setAttribute(
      "transform",
      `translate(${position.x.toFixed(1)} ${position.y.toFixed(1)})`,
    );
  });

  state.laneMap = buildRelationshipLanes(state);
  state.partnerLaneMap = buildPartnerRelationshipLanes(state);
  state.relationships.forEach(relationship => updateRelationship(state, relationship));
}

function clearSelection() {
  if (selectedNode) {
    selectedNode.classList.remove("selected");
    selectedNode = null;
  }
  selectedPerson = null;
  clearAllHighlights();
  clearAllCoefficientLabels();
  renderDetails(null);
}

function selectPersonNode(node, person) {
  if (selectedNode) {
    selectedNode.classList.remove("selected");
  }
  selectedNode = node;
  selectedPerson = person;
  node.classList.add("selected");
  clearAllHighlights();
  const state = familyStates[person.family_id];
  clearAllCoefficientLabels();
  applyCoefficientLabels(state, person.person_id);
  applyFamilyHighlight(state, person.person_id);
  renderDetails(person);
}

function centerPersonInWrap(state, personId) {
  if (!state?.wrap) {
    return;
  }
  const position = state.people[personId];
  if (!position) {
    return;
  }
  const targetLeft = Math.max(0, (position.x * state.zoom) - (state.wrap.clientWidth / 2));
  const targetTop = Math.max(0, (position.y * state.zoom) - (state.wrap.clientHeight / 2));
  state.wrap.scrollTo({ left: targetLeft, top: targetTop, behavior: "smooth" });
}

function focusPerson(person, { revealFamily = true } = {}) {
  if (!person) {
    return false;
  }
  const state = familyStates[person.family_id];
  const node = state?.svg.querySelector(`[data-person-id="${selectorEscape(person.person_id)}"]`);
  if (!state || !node) {
    return false;
  }
  selectPersonNode(node, person);
  if (revealFamily) {
    node.closest(".family-card")?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  }
  centerPersonInWrap(state, person.person_id);
  return true;
}

function setSearchFeedback(message, { error = false } = {}) {
  const feedback = document.getElementById("person-search-feedback");
  if (!feedback) {
    return;
  }
  if (!message) {
    feedback.hidden = true;
    feedback.textContent = "";
    feedback.classList.remove("is-error");
    return;
  }
  feedback.hidden = false;
  feedback.textContent = message;
  feedback.classList.toggle("is-error", error);
}

function findPeopleByQuery(query) {
  const normalizedQuery = normalizeSearchValue(query);
  if (!normalizedQuery) {
    return { kind: "empty", matches: [] };
  }

  const people = Object.values(data.people || {});
  const exactFamilyMatches = people.filter(person =>
    normalizeSearchValue(`${person.family_id}::${person.person_id}`) === normalizedQuery,
  );
  if (exactFamilyMatches.length) {
    return { kind: "exact-family", matches: exactFamilyMatches };
  }

  const exactPersonMatches = people.filter(person =>
    normalizeSearchValue(person.person_id) === normalizedQuery,
  );
  if (exactPersonMatches.length) {
    return { kind: "exact-person", matches: exactPersonMatches };
  }

  const partialMatches = people.filter(person => {
    const familyKey = normalizeSearchValue(`${person.family_id}::${person.person_id}`);
    return familyKey.includes(normalizedQuery) || normalizeSearchValue(person.person_id).includes(normalizedQuery);
  });
  return { kind: "partial", matches: partialMatches };
}

function runPersonSearch() {
  const input = document.getElementById("person-search");
  if (!input) {
    return;
  }

  const result = findPeopleByQuery(input.value);
  if (result.kind === "empty") {
    setSearchFeedback("Enter a person ID or family::person ID.", { error: true });
    return;
  }
  if (!result.matches.length) {
    setSearchFeedback(`No individual matched "${input.value.trim()}".`, { error: true });
    return;
  }
  if (result.matches.length > 1 && result.kind !== "exact-family") {
    setSearchFeedback(
      `Matched ${result.matches.length} individuals. Use family::person_id to pick one exactly.`,
      { error: true },
    );
    return;
  }

  const person = result.matches[0];
  if (!focusPerson(person)) {
    setSearchFeedback(`Found ${person.family_id}::${person.person_id}, but it could not be focused.`, { error: true });
    return;
  }
  input.value = `${person.family_id}::${person.person_id}`;
  setSearchFeedback(`Jumped to ${person.family_id}::${person.person_id}.`);
}

function startDrag(event) {
  if (event.button !== 0) {
    return;
  }
  const node = event.currentTarget;
  const person = data.people[node.dataset.personKey];
  const state = familyStates[person.family_id];
  if (!state) {
    return;
  }

  const point = clientToSvgPoint(state.svg, event.clientX, event.clientY);
  activeDrag = {
    kind: "person",
    pointerId: event.pointerId,
    node,
    familyId: person.family_id,
    personId: person.person_id,
    offsetX: point.x - state.people[person.person_id].x,
    moved: false,
  };
  node.classList.add("dragging");
  hideTooltip();
  if (typeof node.setPointerCapture === "function") {
    node.setPointerCapture(event.pointerId);
  }
  event.preventDefault();
}

function startRelationshipLineDrag(event) {
  if (event.button !== 0) {
    return;
  }
  const line = event.currentTarget;
  const target = relationshipLineTarget(line);
  if (!target) {
    return;
  }
  const group = line.closest(".relationship");
  const svg = line.closest("svg[data-family-id]");
  const familyId = svg?.dataset.familyId;
  const relationshipId = group?.dataset.relationshipId;
  if (!familyId || !relationshipId) {
    return;
  }
  const state = familyStates[familyId];
  const relationship = state?.relationshipById?.[relationshipId];
  if (!state || !relationship) {
    return;
  }

  const point = clientToSvgPoint(state.svg, event.clientX, event.clientY);
  const geometry = describeRelationshipGeometry(
    state,
    relationship,
    state.laneMap?.[relationshipId],
  );
  const currentY = target === "partner"
    ? geometry.partnerLine?.y1
    : (geometry.sibshipLine?.y1 ?? geometry.relationshipBridge?.y1);
  if (currentY === undefined || currentY === null) {
    return;
  }

  activeDrag = {
    kind: "relationship-line",
    pointerId: event.pointerId,
    node: line,
    familyId,
    relationshipId,
    target,
    offsetY: point.y - currentY,
    moved: false,
  };
  line.classList.add("dragging");
  hideTooltip();
  if (typeof line.setPointerCapture === "function") {
    line.setPointerCapture(event.pointerId);
  }
  event.preventDefault();
  event.stopPropagation();
}

function handleDragMove(event) {
  if (!activeDrag || event.pointerId !== activeDrag.pointerId) {
    return;
  }

  const state = familyStates[activeDrag.familyId];
  if (!state) {
    return;
  }

  if (activeDrag.kind === "person") {
    autoScrollWrapOnDrag(state, event.clientX);
    const point = clientToSvgPoint(state.svg, event.clientX, event.clientY);
    const nextX = expandFamilyBoundsForPersonDrag(
      state,
      point.x - activeDrag.offsetX,
    );
    if (Math.abs(nextX - state.people[activeDrag.personId].x) > 0.35) {
      activeDrag.moved = true;
    }
    state.people[activeDrag.personId].x = nextX;
  } else if (activeDrag.kind === "relationship-line") {
    const point = clientToSvgPoint(state.svg, event.clientX, event.clientY);
    const relationship = state.relationshipById[activeDrag.relationshipId];
    if (!relationship) {
      return;
    }
    const adjustments = state.relationshipAdjustments[activeDrag.relationshipId] || {};
    const geometry = describeRelationshipGeometry(
      state,
      relationship,
      state.laneMap?.[activeDrag.relationshipId],
    );
    const parents = [relationship.father_id, relationship.mother_id]
      .map(parentId => (parentId ? state.people[parentId] : null))
      .filter(Boolean);
    const children = relationship.child_ids
      .map(childId => state.people[childId])
      .filter(Boolean);
    const parentBottomY = parents.length
      ? Math.max(...parents.map(parent => parent.y)) + NODE_HALF
      : NODE_HALF;
    const childTopY = children.length
      ? Math.min(...children.map(child => child.y - NODE_HALF))
      : parentBottomY + 72;
    const nextYRaw = point.y - activeDrag.offsetY;
    let nextY = nextYRaw;
    if (activeDrag.target === "partner") {
      const minY = parentBottomY + 2;
      const maxY = Math.max(minY, childTopY - 18);
      nextY = Math.max(minY, Math.min(maxY, nextYRaw));
      if (Math.abs(nextY - (geometry.partnerLine?.y1 ?? nextY)) > 0.35) {
        activeDrag.moved = true;
      }
      adjustments.partnerY = nextY;
    } else {
      const relationshipStartY = geometry.relationshipDrop?.y1 ?? (parentBottomY + 18);
      const minY = relationshipStartY + 10;
      const maxY = Math.max(minY, childTopY - 10);
      nextY = Math.max(minY, Math.min(maxY, nextYRaw));
      const currentSpineY = geometry.sibshipLine?.y1 ?? geometry.relationshipBridge?.y1 ?? nextY;
      if (Math.abs(nextY - currentSpineY) > 0.35) {
        activeDrag.moved = true;
      }
      adjustments.spineY = nextY;
    }
    state.relationshipAdjustments[activeDrag.relationshipId] = adjustments;
  }
  renderFamily(activeDrag.familyId);
  if (activeDrag.kind === "person") {
    keepDraggedPersonVisible(state, activeDrag.personId);
  }
}

function finishDrag(event) {
  if (!activeDrag || event.pointerId !== activeDrag.pointerId) {
    return;
  }

  const state = familyStates[activeDrag.familyId];
  const node = activeDrag.node;
  if (activeDrag.moved) {
    node.dataset.dragSuppress = "1";
  }
  node.classList.remove("dragging");
  if (state && activeDrag.kind === "person") {
    fitFamilyToCurrentContent(state);
    renderFamily(activeDrag.familyId);
    keepDraggedPersonVisible(state, activeDrag.personId);
  }
  activeDrag = null;
}

document.addEventListener("pointermove", handleDragMove);
document.addEventListener("pointerup", finishDrag);
document.addEventListener("pointercancel", finishDrag);

document.querySelectorAll("[data-person-key]").forEach(node => {
  const key = node.dataset.personKey;
  const person = data.people[key];
  node.addEventListener("mouseenter", event => showPersonTooltip(event, person));
  node.addEventListener("mousemove", moveTooltip);
  node.addEventListener("mouseleave", hideTooltip);
  node.addEventListener("pointerdown", startDrag);
  node.addEventListener("click", event => {
    if (node.dataset.dragSuppress === "1") {
      delete node.dataset.dragSuppress;
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (selectedNode === node) {
      clearSelection();
      return;
    }
    selectPersonNode(node, person);
  });
});

document.querySelectorAll('.relationship [data-role="partner-line"], .relationship [data-role="relationship-bridge"], .relationship [data-role="sibship-line"]').forEach(line => {
  line.addEventListener("pointerdown", startRelationshipLineDrag);
});

document.querySelectorAll("[data-zoom-in-family]").forEach(button => {
  button.addEventListener("click", () => {
    setZoom(button.dataset.zoomInFamily, (familyStates[button.dataset.zoomInFamily]?.zoom || 1) * ZOOM_STEP);
  });
});

document.querySelectorAll("[data-zoom-out-family]").forEach(button => {
  button.addEventListener("click", () => {
    setZoom(button.dataset.zoomOutFamily, (familyStates[button.dataset.zoomOutFamily]?.zoom || 1) / ZOOM_STEP);
  });
});

document.querySelectorAll("[data-zoom-reset-family]").forEach(button => {
  button.addEventListener("click", () => {
    setZoom(button.dataset.zoomResetFamily, 1);
  });
});

document.querySelectorAll(".svg-wrap").forEach(wrap => {
  wrap.addEventListener("click", event => {
    if (event.target.closest("[data-person-key]")) {
      return;
    }
    clearSelection();
  });
  wrap.addEventListener("wheel", event => {
    if (!event.ctrlKey && !event.metaKey) {
      return;
    }
    const familyId = wrap.dataset.familyId;
    if (!familyId || !familyStates[familyId]) {
      return;
    }
    event.preventDefault();
    const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
    setZoom(familyId, familyStates[familyId].zoom * factor);
  }, { passive: false });
});

document.querySelectorAll("[data-download-family]").forEach(button => {
  button.addEventListener("click", () => {
    const familyId = button.dataset.downloadFamily;
    const svg = findFamilySvg(familyId);
    if (!svg) {
      return;
    }
    downloadSvg(svg, `${familyId}.svg`);
  });
});

document.querySelectorAll("[data-download-journal-svg-family]").forEach(button => {
  button.addEventListener("click", () => {
    const familyId = button.dataset.downloadJournalSvgFamily;
    const svg = findFamilySvg(familyId);
    if (!svg) {
      return;
    }
    downloadSvg(svg, `${familyId}.journal.svg`, { journal: true });
  });
});

document.querySelectorAll("[data-download-journal-png-family]").forEach(button => {
  button.addEventListener("click", async () => {
    const familyId = button.dataset.downloadJournalPngFamily;
    const svg = findFamilySvg(familyId);
    if (!svg) {
      return;
    }
    await downloadPng(svg, `${familyId}.journal.png`, { journal: true });
  });
});

const printButton = document.getElementById("print-report");
if (printButton) {
  printButton.addEventListener("click", () => window.print());
}

const personSearchButton = document.getElementById("person-search-button");
if (personSearchButton) {
  personSearchButton.addEventListener("click", runPersonSearch);
}

const personSearchInput = document.getElementById("person-search");
if (personSearchInput) {
  personSearchInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      runPersonSearch();
    }
  });
}

const toggleGenotypesBtn = document.getElementById("toggle-genotypes");
if (toggleGenotypesBtn) {
  toggleGenotypesBtn.addEventListener("click", () => {
    const active = toggleGenotypesBtn.dataset.active === "1";
    toggleGenotypesBtn.dataset.active = active ? "0" : "1";
    document.body.classList.toggle("hide-genotypes", active);
    toggleGenotypesBtn.textContent = active ? "Show Genotypes" : "Hide Genotypes";
  });
}

buildFamilyStates();
renderDetails(null);
"""

HTML_TEMPLATE = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$title</title>
  <style>$css</style>
</head>
<body>
  <div class="page">
    <main class="content">
      <section class="hero">
        <h1>$title</h1>
        <p>Standalone pedigree report generated from <code>$source_name</code>.</p>
        <div class="toolbar">
          <button id="print-report" type="button">Print / Save PDF</button>
          <button id="toggle-genotypes" type="button" class="secondary" data-active="1">Toggle Genotypes</button>
          <div class="search-bar">
            <label class="sr-only" for="person-search">Search for an individual</label>
            <input id="person-search" type="search" list="person-search-options" placeholder="Search person ID or family::person">
            <datalist id="person-search-options">$search_options_html</datalist>
            <button id="person-search-button" type="button" class="secondary">Search / Jump</button>
          </div>
        </div>
        <p class="search-feedback" id="person-search-feedback" hidden></p>
        <div class="legend">
          <span class="male">Male</span>
          <span class="female">Female</span>
          <span class="unknown">Unknown</span>
          <span class="affected">Affected</span>
          <span class="unaffected">Unaffected</span>
          <span class="carrier">Carrier</span>
          <span class="proband">Proband (P ↗)</span>
          <span class="deceased">Deceased ( / )</span>
        </div>
$messages_html
      </section>
      <section class="summary">$summary_html</section>
$family_sections
    </main>
    <aside class="details" id="person-details"></aside>
  </div>
  <div class="tooltip" id="tooltip"></div>
  <script>window.PEDVIEW_DATA = window.PEDIVIZ_DATA = $data_json;</script>
  <script>$js</script>
</body>
</html>
"""
)


def render_report(
    pedigree: Pedigree,
    family_layouts: dict[str, FamilyLayout],
    family_summaries: list[FamilySummary],
    messages: list[ValidationMessage],
    title: str,
    ancestor_inbreeding: float = 0.0,
    used_default_ancestor_inbreeding: bool = True,
    variant_name: str | None = None,
) -> str:
    family_insights_by_family = {
        family_id: build_family_insights(family, variant_name=variant_name)
        for family_id, family in pedigree.families.items()
    }
    family_sections = "\n".join(
        render_family_section(
            family=pedigree.families[summary.family_id],
            layout=family_layouts[summary.family_id],
            summary=summary,
            insights=family_insights_by_family.get(summary.family_id, {}),
        )
        for summary in family_summaries
        if summary.family_id in family_layouts
    )
    summary_html = "".join(build_summary_metrics(pedigree, family_summaries, messages))
    search_options_html = build_search_options(pedigree)
    messages_html = render_messages(messages)
    data_json = json.dumps(
        build_browser_data(
            pedigree,
            family_layouts,
            family_insights_by_family=family_insights_by_family,
            ancestor_inbreeding=ancestor_inbreeding,
            used_default_ancestor_inbreeding=used_default_ancestor_inbreeding,
        ),
        separators=(",", ":"),
    )
    return HTML_TEMPLATE.substitute(
        title=escape(title),
        source_name=escape(pedigree.source_path),
        css=CSS,
        js=JS,
        summary_html=summary_html,
        search_options_html=search_options_html,
        family_sections=family_sections,
        messages_html=messages_html,
        data_json=data_json,
    )


def metric(label: str, value: str) -> str:
    return (
        '<div class="metric">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(value)}</strong>"
        "</div>"
    )


def build_summary_metrics(
    pedigree: Pedigree,
    family_summaries: list[FamilySummary],
    messages: list[ValidationMessage],
) -> list[str]:
    male_count = 0
    female_count = 0
    unknown_sex_count = 0
    affected_count = 0
    unaffected_count = 0
    has_affected_data = False

    for family in pedigree.families.values():
        for person in family.people():
            if person.sex == "male":
                male_count += 1
            elif person.sex == "female":
                female_count += 1
            else:
                unknown_sex_count += 1

            affected_status = affected_status_from_metadata(person.metadata)
            if affected_status is None:
                continue
            has_affected_data = True
            if affected_status == "affected":
                affected_count += 1
            elif affected_status == "unaffected":
                unaffected_count += 1

    metrics = [
        metric("Families", str(len(family_summaries))),
        metric("Individuals", str(pedigree.people_count())),
        metric(
            "Founders", str(sum(summary.founders_count for summary in family_summaries))
        ),
        metric("Male", str(male_count)),
        metric("Female", str(female_count)),
        metric("Unknown Sex", str(unknown_sex_count)),
    ]
    if has_affected_data:
        metrics.extend(
            [
                metric("Affected", str(affected_count)),
                metric("Unaffected", str(unaffected_count)),
            ]
        )
    metrics.extend(
        [
            metric(
                "Warnings",
                str(sum(message.severity == "warning" for message in messages)),
            ),
            metric(
                "Errors", str(sum(message.severity == "error" for message in messages))
            ),
        ]
    )
    return metrics


def render_messages(messages: list[ValidationMessage]) -> str:
    if not messages:
        return ""
    items = "".join(
        f'<li class="{escape(message.severity)}">{escape(message.format_for_cli())}</li>'
        for message in messages
    )
    return f'<ul class="messages">{items}</ul>'


def build_search_options(pedigree: Pedigree) -> str:
    options: list[str] = []
    for family in pedigree.families.values():
        for person in family.people():
            value = f"{family.family_id}::{person.person_id}"
            options.append(f'<option value="{escape(value)}"></option>')
    return "".join(options)


def mini_metric(label: str, value: str) -> str:
    return (
        '<div class="mini-metric">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(value)}</strong>"
        "</div>"
    )


def render_insight_metrics(
    stats: dict[str, int],
    *,
    include_unknown_status: bool = True,
) -> str:
    metrics = [
        mini_metric("Total", str(stats.get("total", 0))),
        mini_metric("Affected", str(stats.get("affected", 0))),
        mini_metric("Unaffected", str(stats.get("unaffected", 0))),
    ]
    if include_unknown_status:
        metrics.append(
            mini_metric("Unknown Status", str(stats.get("unknown_status", 0)))
        )
    metrics.extend(
        [
            mini_metric("Male", str(stats.get("male", 0))),
            mini_metric("Female", str(stats.get("female", 0))),
            mini_metric("Unknown Sex", str(stats.get("unknown_sex", 0))),
        ]
    )
    return f'<div class="insight-metrics">{"".join(metrics)}</div>'


def render_generation_table(generation_stats: list[dict[str, int]]) -> str:
    if not generation_stats:
        return "<p>No generation statistics are available.</p>"
    rows = "".join(
        (
            "<tr>"
            f"<td>{escape(str(stats.get('generation', '?')))}</td>"
            f"<td>{escape(str(stats.get('total', 0)))}</td>"
            f"<td>{escape(str(stats.get('affected', 0)))}</td>"
            f"<td>{escape(str(stats.get('unaffected', 0)))}</td>"
            f"<td>{escape(str(stats.get('unknown_status', 0)))}</td>"
            f"<td>{escape(str(stats.get('male', 0)))}</td>"
            f"<td>{escape(str(stats.get('female', 0)))}</td>"
            f"<td>{escape(str(stats.get('unknown_sex', 0)))}</td>"
            "</tr>"
        )
        for stats in generation_stats
    )
    return (
        '<div class="insight-table-wrap">'
        '<table class="insight-table">'
        "<thead><tr>"
        "<th>Gen</th>"
        "<th>Total</th>"
        "<th>Affected</th>"
        "<th>Unaffected</th>"
        "<th>Unknown Status</th>"
        "<th>Male</th>"
        "<th>Female</th>"
        "<th>Unknown Sex</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
    )


def render_branch_summaries(branch_summaries: list[dict[str, object]]) -> str:
    if not branch_summaries:
        return "<p>No branch summaries are available for this family.</p>"
    items = "".join(
        (
            '<li class="branch-item">'
            f"<strong>{escape(str(branch.get('label', 'Unknown branch')))}</strong>"
            f"<span>{escape(', '.join(str(root_id) for root_id in branch.get('root_ids', [])) or 'No recorded roots')}</span>"
            f"<span>{escape(str(branch.get('member_count', 0)))} members · "
            f"{escape(str(branch.get('descendant_count', 0)))} descendants · "
            f"{escape(str(branch.get('affected_count', 0)))} affected · "
            f"{escape(str(branch.get('affected_descendant_count', 0)))} affected descendants</span>"
            "</li>"
        )
        for branch in branch_summaries
    )
    return f'<ul class="branch-list">{items}</ul>'


def render_flag_list(flags: list[dict[str, object]], empty_message: str) -> str:
    if not flags:
        return f"<p>{escape(empty_message)}</p>"
    items = "".join(
        (
            f'<li class="flag-item" data-severity="{escape(str(flag.get("severity", "notice")))}">'
            f'<span class="flag-severity">{escape(str(flag.get("severity", "notice")).title())}</span>'
            f"<strong>{escape(str(flag.get('person_id', 'Family')))}</strong>"
            f"<span>{escape(str(flag.get('message', '')))}"
            + (
                f" Related: {escape(', '.join(str(value) for value in flag.get('related_ids', [])))}."
                if flag.get("related_ids")
                else ""
            )
            + "</span></li>"
        )
        for flag in flags
    )
    return f'<ul class="flag-list">{items}</ul>'


def render_family_insights(insights: dict[str, object]) -> str:
    founder_stats = insights.get("founder_stats", {})
    generation_stats = insights.get("generation_stats", [])
    branch_summaries = insights.get("branch_summaries", [])
    family_flags = insights.get("family_flags", [])
    return (
        '<div class="family-insights-grid">'
        '<section class="insight-card">'
        "<h3>Founder Snapshot</h3>"
        "<p>People with no recorded in-family parents.</p>"
        f"{render_insight_metrics(founder_stats if isinstance(founder_stats, dict) else {})}"
        "</section>"
        '<section class="insight-card insight-card--wide">'
        "<h3>Generation Breakdown</h3>"
        "<p>Counts across generations, with phenotype and sex splits.</p>"
        f"{render_generation_table(generation_stats if isinstance(generation_stats, list) else [])}"
        "</section>"
        '<section class="insight-card">'
        "<h3>Branch Summaries</h3>"
        "<p>Top founder-rooted branches ordered by affected descendants.</p>"
        f"{render_branch_summaries(branch_summaries if isinstance(branch_summaries, list) else [])}"
        "</section>"
        '<section class="insight-card insight-card--wide insight-card--full">'
        "<h3>Pedigree Flags</h3>"
        "<p>Phenotype patterns that may deserve a closer look.</p>"
        f"{render_flag_list(family_flags if isinstance(family_flags, list) else [], 'No pedigree anomaly flags were triggered for this family.')}"
        "</section>"
        "</div>"
    )


def render_family_section(
    family,
    layout: FamilyLayout,
    summary: FamilySummary,
    insights: dict[str, object],
) -> str:
    stats_text = (
        f"{summary.people_count} individuals · "
        f"{summary.founders_count} founders · "
        f"{summary.relationship_count} parent references · "
        f"{summary.generation_count} generations"
    )
    return (
        '<section class="family-card">'
        "<header>"
        f"<div><h2>Family {escape(family.family_id)}</h2>"
        f'<div class="family-stats">{escape(stats_text)}</div></div>'
        '<div class="family-actions">'
        '<div class="zoom-controls">'
        f'<button type="button" class="secondary" data-zoom-out-family="{escape(family.family_id)}">'
        "Zoom -"
        "</button>"
        f'<button type="button" class="secondary" data-zoom-in-family="{escape(family.family_id)}">'
        "Zoom +"
        "</button>"
        f'<button type="button" class="secondary" data-zoom-reset-family="{escape(family.family_id)}">'
        "100%"
        "</button>"
        f'<span class="zoom-level" data-zoom-level-family="{escape(family.family_id)}">100%</span>'
        "</div>"
        f'<button type="button" class="secondary" data-download-family="{escape(family.family_id)}">'
        "Download SVG"
        "</button>"
        f'<button type="button" class="secondary" data-download-journal-svg-family="{escape(family.family_id)}">'
        "Journal SVG"
        "</button>"
        f'<button type="button" data-download-journal-png-family="{escape(family.family_id)}">'
        "Journal PNG"
        "</button>"
        "</div>"
        "</header>"
        f'<div class="svg-wrap" data-family-id="{escape(family.family_id)}">{render_family_svg(family, layout, insights)}</div>'
        f"{render_family_insights(insights)}"
        "</section>"
    )


def render_family_svg(
    family, layout: FamilyLayout, insights: dict[str, object] | None = None
) -> str:
    lane_map = build_relationship_lane_map(layout)
    partner_lane_map = build_partner_bridge_lane_map(layout)
    person_summaries = {}
    if insights:
        person_summaries = insights.get("person_summaries", {}) or {}
    elements: list[str] = [
        (
            f'<svg viewBox="0 0 {layout.width:.0f} {layout.height:.0f}" '
            f'width="{layout.width:.0f}" '
            f'height="{layout.height:.0f}" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'data-family-id="{escape(family.family_id)}" '
            f'aria-label="Pedigree for family {escape(family.family_id)}">'
        ),
        (
            "<defs>"
            '<marker id="proband-arrow" viewBox="0 0 10 10" refX="6" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            '<path d="M 0 1 L 8 5 L 0 9 z" fill="var(--ink, #1f2937)" />'
            "</marker>"
            "</defs>"
        ),
        (
            f'<rect class="family-boundary" x="12" y="12" width="{layout.width - 24:.0f}" '
            f'height="{layout.height - 24:.0f}" rx="8" />'
        ),
    ]

    for union in layout.unions:
        elements.extend(render_union(layout, union, lane_map, partner_lane_map))

    for person in family.people():
        person_summary = person_summaries.get(person.person_id, {})
        anomaly_count = (
            len(person_summary.get("flags", []))
            if isinstance(person_summary, dict)
            else 0
        )
        elements.append(
            render_person(
                person,
                layout.people[person.person_id],
                anomaly_count=anomaly_count,
            )
        )

    elements.append("</svg>")
    return "".join(elements)


def render_union(
    layout: FamilyLayout,
    union,
    lane_map: dict[str, tuple[int, int]],
    partner_lane_map: dict[str, tuple[int, int]],
) -> list[str]:
    geometry = describe_relationship_geometry(
        layout,
        union,
        lane_map.get(union.relationship_id, (0, 1)),
        partner_lane_map.get(union.relationship_id),
    )
    elements: list[str] = [
        f'<g class="relationship" data-relationship-id="{escape(union.relationship_id)}">'
    ]
    elements.append(
        render_line(
            css_class="union partner-line",
            role="partner-line",
            line=geometry["partner_line"],
        )
    )
    for parent_id in (union.father_id, union.mother_id):
        if parent_id is None:
            continue
        elements.append(
            render_line(
                css_class="union partner-connector",
                parent_id=parent_id,
                line=geometry["parent_lines"].get(parent_id),
            )
        )
    elements.append(
        render_line(
            css_class="connector relationship-drop",
            role="relationship-drop",
            line=geometry["relationship_drop"],
        )
    )
    elements.append(
        render_line(
            css_class="connector relationship-bridge",
            role="relationship-bridge",
            line=geometry["relationship_bridge"],
        )
    )
    elements.append(
        render_line(
            css_class="connector sibship-line",
            role="sibship-line",
            line=geometry["sibship_line"],
        )
    )
    for child_id in union.child_ids:
        elements.append(
            render_line(
                css_class="connector child-drop",
                child_id=child_id,
                line=geometry["child_lines"].get(child_id),
            )
        )
    elements.append("</g>")
    return elements


def render_person(person, layout_person, anomaly_count: int = 0) -> str:
    person_key = person_key_for(person.family_id, person.person_id)
    affected_status = (
        person.affected
        or affected_status_from_metadata(person.metadata)
        or "unspecified"
    )
    shape_markup = render_shape(person.sex, carrier=person.carrier)

    decorations: list[str] = []
    if person.deceased:
        decorations.append(
            '<line class="deceased-slash" x1="-15" y1="15" x2="15" y2="-15" />'
        )
    if person.proband:
        decorations.append(
            '<g class="proband-indicator">'
            '<line x1="-22" y1="22" x2="-14" y2="14" marker-end="url(#proband-arrow)" />'
            '<text x="-26" y="27" class="proband-label">P</text>'
            "</g>"
        )

    labels: list[str] = []
    curr_y = NODE_SIZE / 2 + 14
    labels.append(
        f'<text class="person-label" x="0" y="{curr_y:.1f}">{escape(person.person_id)}</text>'
    )

    if person.age:
        age_str = (
            f"d. {person.age}"
            if person.deceased and not str(person.age).lower().startswith("d")
            else str(person.age)
        )
        curr_y += 12
        labels.append(
            f'<text class="person-sublabel person-age-label" x="0" y="{curr_y:.1f}">{escape(age_str)}</text>'
        )
    elif person.deceased:
        curr_y += 12
        labels.append(
            f'<text class="person-sublabel person-deceased-label" x="0" y="{curr_y:.1f}">d.</text>'
        )

    if person.genotype:
        curr_y += 12
        labels.append(
            f'<text class="person-sublabel person-genotype-label" data-genotype="{escape(person.genotype)}" x="0" y="{curr_y:.1f}">{escape(person.genotype)}</text>'
        )

    return (
        f'<g class="person person--{escape(person.sex)}" '
        f'data-family-id="{escape(person.family_id)}" '
        f'data-person-id="{escape(person.person_id)}" '
        f'data-person-key="{escape(person_key)}" '
        f'data-affected-status="{escape(affected_status)}" '
        f'data-carrier="{str(person.carrier).lower()}" '
        f'data-proband="{str(person.proband).lower()}" '
        f'data-deceased="{str(person.deceased).lower()}" '
        f'data-genotype="{escape(person.genotype or "")}" '
        f'data-anomaly-count="{escape(str(anomaly_count))}" '
        f'transform="translate({layout_person.x:.1f} {layout_person.y:.1f})">'
        f"<title>{escape(person.person_id)}</title>"
        f"{shape_markup}"
        f"{''.join(decorations)}"
        '<text class="coefficient-label" x="0" y="0"></text>'
        f"{''.join(labels)}"
        "</g>"
    )


def render_shape(sex: str, carrier: bool = False) -> str:
    half = NODE_SIZE / 2
    elements: list[str] = []
    if sex == "male":
        elements.append(
            f'<rect class="person-shape" x="{-half:.1f}" y="{-half:.1f}" '
            f'width="{NODE_SIZE}" height="{NODE_SIZE}" rx="2" />'
        )
        if carrier:
            elements.append(
                f'<rect class="carrier-fill" x="{-half:.1f}" y="{-half:.1f}" '
                f'width="{half:.1f}" height="{NODE_SIZE}" rx="2" />'
            )
    elif sex == "female":
        elements.append(f'<circle class="person-shape" cx="0" cy="0" r="{half:.1f}" />')
        if carrier:
            elements.append(
                f'<path class="carrier-fill" d="M 0,{-half:.1f} A {half:.1f},{half:.1f} 0 0,0 0,{half:.1f} Z" />'
            )
    else:
        points = [
            (0, -half),
            (half, 0),
            (0, half),
            (-half, 0),
        ]
        point_string = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        elements.append(f'<polygon class="person-shape" points="{point_string}" />')
        if carrier:
            elements.append(
                f'<polygon class="carrier-fill" points="0,{-half:.1f} 0,{half:.1f} {-half:.1f},0" />'
            )
    return "".join(elements)


def build_browser_data(
    pedigree: Pedigree,
    family_layouts: dict[str, FamilyLayout],
    family_insights_by_family: dict[str, dict[str, object]],
    ancestor_inbreeding: float = 0.0,
    used_default_ancestor_inbreeding: bool = True,
) -> dict[str, object]:
    people: dict[str, dict[str, object]] = {}
    families: dict[str, dict[str, object]] = {}
    for family in pedigree.families.values():
        family.ensure_relationships()
        layout = family_layouts.get(family.family_id)
        insights = family_insights_by_family.get(family.family_id, {})
        person_summaries = (
            insights.get("person_summaries", {}) if isinstance(insights, dict) else {}
        )
        relatedness = compute_family_relatedness(
            family,
            ancestor_inbreeding=ancestor_inbreeding,
        )
        union_by_relationship = (
            {union.relationship_id: union for union in layout.unions} if layout else {}
        )
        for person in family.people():
            key = person_key_for(family.family_id, person.person_id)
            layout_person = layout.people.get(person.person_id) if layout else None
            affected_status = affected_status_from_metadata(person.metadata)
            people[key] = {
                "family_id": family.family_id,
                "person_id": person.person_id,
                "father_id": person.father_id,
                "mother_id": person.mother_id,
                "sex": person.sex,
                "affected_status": person.affected or affected_status,
                "proband": person.proband,
                "deceased": person.deceased,
                "carrier": person.carrier,
                "age": person.age,
                "genotype": person.genotype,
                "variant_id": person.variant_id,
                "metadata": {
                    k: v
                    for k, v in metadata_without_affected_status(
                        person.metadata
                    ).items()
                    if k.lower()
                    not in {"proband", "deceased", "carrier", "age", "genotype"}
                },
                "x": layout_person.x if layout_person else None,
                "y": layout_person.y if layout_person else None,
                "generation": layout_person.generation if layout_person else None,
                "transmission_summary": person_summaries.get(person.person_id, {}),
                "anomaly_flags": (
                    person_summaries.get(person.person_id, {}).get("flags", [])
                    if isinstance(person_summaries.get(person.person_id, {}), dict)
                    else []
                ),
            }
        families[family.family_id] = {
            "width": layout.width if layout else None,
            "height": layout.height if layout else None,
            "person_ids": list(family.order),
            "wright_relatedness": {
                person_id: {
                    relative_id: round(value, 6)
                    for relative_id, value in relatedness[person_id].items()
                }
                for person_id in family.order
            },
            "wright_settings": {
                "ancestor_inbreeding": ancestor_inbreeding,
                "used_default": used_default_ancestor_inbreeding,
            },
            "relationships": [
                {
                    "relationship_id": relationship.relationship_id,
                    "father_id": relationship.father_id,
                    "mother_id": relationship.mother_id,
                    "child_ids": list(relationship.child_ids),
                    "anchor_x": (
                        union_by_relationship[relationship.relationship_id].x
                        if relationship.relationship_id in union_by_relationship
                        else None
                    ),
                    "kind": relationship.kind,
                }
                for relationship in family.relationships
            ],
            "generation_stats": insights.get("generation_stats", [])
            if isinstance(insights, dict)
            else [],
            "founder_stats": insights.get("founder_stats", {})
            if isinstance(insights, dict)
            else {},
            "branch_summaries": insights.get("branch_summaries", [])
            if isinstance(insights, dict)
            else [],
            "family_flags": insights.get("family_flags", [])
            if isinstance(insights, dict)
            else [],
            "person_summaries": person_summaries
            if isinstance(person_summaries, dict)
            else {},
            "segregation": insights.get("segregation")
            if isinstance(insights, dict)
            else None,
        }
    return {
        "node_size": NODE_SIZE,
        "people": people,
        "families": families,
    }


def person_key_for(family_id: str, person_id: str) -> str:
    return f"{family_id}::{person_id}"


def describe_relationship_geometry(
    layout: FamilyLayout,
    union,
    lane_info: tuple[int, int] = (0, 1),
    partner_lane_info: tuple[int, int] | None = None,
) -> dict[str, object]:
    father = layout.people.get(union.father_id) if union.father_id else None
    mother = layout.people.get(union.mother_id) if union.mother_id else None
    parents = [parent for parent in (father, mother) if parent is not None]
    if not parents:
        return {
            "partner_line": None,
            "parent_lines": {},
            "relationship_drop": None,
            "sibship_line": None,
            "child_lines": {},
        }

    child_positions = [layout.people[child_id] for child_id in union.child_ids]
    child_xs = [child.x for child in child_positions]
    union_y = max(parent.y for parent in parents) + NODE_SIZE / 2 + 18
    routed_partner = should_route_partner_bridge(parents)
    partner_y = None
    if routed_partner:
        partner_lane, _partner_lane_count = partner_lane_info or (0, 1)
        partner_y = min(
            union_y - 4,
            max(parent.y for parent in parents)
            + NODE_SIZE / 2
            + PARTNER_LANE_OFFSET
            + partner_lane * PARTNER_LANE_SPACING,
        )
    relationship_drop_x = resolve_relationship_drop_x(parents, union.x)
    relationship_start_y = (
        partner_y
        if routed_partner and partner_y is not None
        else max(parent.y for parent in parents)
        if len(parents) == 2
        else union_y
    )
    spine_y = relationship_start_y + SIBSHIP_DROP
    child_top = (
        min(child.y - NODE_SIZE / 2 for child in child_positions)
        if child_positions
        else relationship_start_y + SIBSHIP_DROP
    )
    lane_index, lane_count = lane_info
    if lane_count > 1:
        top_y = relationship_start_y + LANE_TOP_PADDING
        bottom_y = max(top_y, child_top - LANE_BOTTOM_PADDING)
        ratio = (lane_index + 1) / (lane_count + 1)
        spine_y = top_y + (bottom_y - top_y) * ratio
    else:
        midpoint = relationship_start_y + (child_top - relationship_start_y) / 2
        spine_y = max(relationship_start_y + 10, min(child_top - 10, midpoint))
    child_min_x = min(child_xs, default=union.x)
    child_max_x = max(child_xs, default=union.x)
    branch_x = max(child_min_x, min(child_max_x, union.x))

    return {
        "partner_line": (
            (
                min(father.x, mother.x),
                partner_y,
                max(father.x, mother.x),
                partner_y,
            )
            if routed_partner
            and father is not None
            and mother is not None
            and partner_y is not None
            else (father.x, father.y, mother.x, mother.y)
            if father is not None and mother is not None
            else None
        ),
        "parent_lines": {
            parent_id: (
                layout.people[parent_id].x,
                layout.people[parent_id].y + NODE_SIZE / 2,
                layout.people[parent_id].x,
                partner_y,
            )
            for parent_id in (union.father_id, union.mother_id)
            if routed_partner and partner_y is not None and parent_id in layout.people
        },
        "relationship_drop": (
            (
                relationship_drop_x,
                relationship_start_y,
                relationship_drop_x,
                spine_y,
            )
            if child_positions
            else None
        ),
        "relationship_bridge": (
            (relationship_drop_x, spine_y, branch_x, spine_y)
            if child_positions and abs(branch_x - relationship_drop_x) > 0.1
            else None
        ),
        "sibship_line": (
            (
                child_min_x,
                spine_y,
                child_max_x,
                spine_y,
            )
            if child_positions
            else None
        ),
        "child_lines": {
            child_id: (
                layout.people[child_id].x,
                spine_y,
                layout.people[child_id].x,
                layout.people[child_id].y - NODE_SIZE / 2,
            )
            for child_id in union.child_ids
            if child_id in layout.people
        },
    }


def build_relationship_lane_map(layout: FamilyLayout) -> dict[str, tuple[int, int]]:
    grouped: dict[tuple[int, int], list[tuple[float, float, int, str]]] = {}
    for order, union in enumerate(layout.unions):
        child_positions = [
            layout.people[child_id]
            for child_id in union.child_ids
            if child_id in layout.people
        ]
        if not child_positions:
            continue
        child_generation = min(child.generation for child in child_positions)
        parent_positions = [
            layout.people[parent_id]
            for parent_id in (union.father_id, union.mother_id)
            if parent_id in layout.people
        ]
        parent_generation = (
            max(parent.generation for parent in parent_positions)
            if parent_positions
            else child_generation - 1
        )
        relationship_drop_x = resolve_relationship_drop_x(parent_positions, union.x)
        interval_start = min(
            [relationship_drop_x, *[child.x for child in child_positions]]
        )
        interval_end = max(
            [relationship_drop_x, *[child.x for child in child_positions]]
        )
        grouped.setdefault((parent_generation, child_generation), []).append(
            (interval_start, interval_end, order, union.relationship_id)
        )

    lane_map: dict[str, tuple[int, int]] = {}
    for entries in grouped.values():
        lane_ends: list[float] = []
        assigned: list[tuple[str, int]] = []
        for start, end, order, relationship_id in sorted(
            entries, key=lambda item: (item[0], item[2])
        ):
            lane = 0
            while lane < len(lane_ends) and start <= lane_ends[lane]:
                lane += 1
            if lane == len(lane_ends):
                lane_ends.append(end)
            else:
                lane_ends[lane] = end
            assigned.append((relationship_id, lane))
        lane_count = len(lane_ends)
        for relationship_id, lane in assigned:
            lane_map[relationship_id] = (lane, lane_count)

    return lane_map


def build_partner_bridge_lane_map(layout: FamilyLayout) -> dict[str, tuple[int, int]]:
    grouped: dict[int, list[tuple[float, float, int, str]]] = {}
    for order, union in enumerate(layout.unions):
        parent_positions = [
            layout.people[parent_id]
            for parent_id in (union.father_id, union.mother_id)
            if parent_id in layout.people
        ]
        if not should_route_partner_bridge(parent_positions):
            continue
        generation = max(parent.generation for parent in parent_positions)
        interval_start = min(parent.x for parent in parent_positions)
        interval_end = max(parent.x for parent in parent_positions)
        grouped.setdefault(generation, []).append(
            (interval_start, interval_end, order, union.relationship_id)
        )

    lane_map: dict[str, tuple[int, int]] = {}
    for entries in grouped.values():
        lane_ends: list[float] = []
        assigned: list[tuple[str, int]] = []
        for start, end, order, relationship_id in sorted(
            entries, key=lambda item: (item[0], item[2])
        ):
            lane = 0
            while lane < len(lane_ends) and start <= lane_ends[lane]:
                lane += 1
            if lane == len(lane_ends):
                lane_ends.append(end)
            else:
                lane_ends[lane] = end
            assigned.append((relationship_id, lane))
        lane_count = len(lane_ends)
        for relationship_id, lane in assigned:
            lane_map[relationship_id] = (lane, lane_count)

    return lane_map


def should_route_partner_bridge(parent_positions) -> bool:
    if len(parent_positions) != 2:
        return False
    span = max(parent.x for parent in parent_positions) - min(
        parent.x for parent in parent_positions
    )
    return span > PARTNER_ROUTING_THRESHOLD


def resolve_relationship_drop_x(parent_positions, union_x: float) -> float:
    if len(parent_positions) == 2:
        return sum(parent.x for parent in parent_positions) / len(parent_positions)
    return union_x


def render_line(
    css_class: str,
    line: tuple[float, float, float, float] | None,
    role: str | None = None,
    child_id: str | None = None,
    parent_id: str | None = None,
) -> str:
    attributes = [f'class="{css_class}"']
    if role is not None:
        attributes.append(f'data-role="{escape(role)}"')
    if child_id is not None:
        attributes.append(f'data-child-id="{escape(child_id)}"')
    if parent_id is not None:
        attributes.append(f'data-parent-id="{escape(parent_id)}"')
    if line is None:
        return f'<line {" ".join(attributes)} style="display:none" />'
    x1, y1, x2, y2 = line
    attributes.extend(
        [
            f'x1="{x1:.1f}"',
            f'y1="{y1:.1f}"',
            f'x2="{x2:.1f}"',
            f'y2="{y2:.1f}"',
        ]
    )
    return f"<line {' '.join(attributes)} />"
