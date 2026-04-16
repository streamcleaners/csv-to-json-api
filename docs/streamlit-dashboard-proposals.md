# Streamlit Dashboard Proposals

Potential views, diagrams, and ML features we could build on top of the
UK tariff open data CSVs. Written in plain English so non-technical
stakeholders can review and prioritise.

---

## 1. Commodity Code Lookup and Classifier

**What the user sees:**
A text box where someone types a plain-English description of a product,
e.g. "frozen boneless beef" or "cotton men's jacket". Below it, a ranked
list of suggested commodity codes with confidence percentages and the
official description alongside each one.

**Diagram / visual:**
- A bar chart showing the top 5 predicted commodity codes and their
  confidence scores.
- A small expandable tree view showing where the suggested code sits in
  the commodity hierarchy (chapter > heading > subheading > code).

**How it works under the hood:**
TF-IDF on the commodity descriptions, fed into a logistic regression or
random forest classifier. Lightweight, fast, no GPU needed.

**Why it's useful:**
Traders and customs brokers spend time manually searching for the right
code. This gives them a starting point and reduces misclassification.

---

## 2. Quota Exhaustion Dashboard

**What the user sees:**
A table of all active tariff rate quotas showing the quota name, country,
opening volume, current fill rate, and a status badge (green / amber / red).
Clicking a row expands a detail panel.

**Diagrams / visuals:**
- A gauge chart per quota showing how full it is (like a fuel gauge).
- A line chart projecting the fill rate forward to the end of the quota
  period, with a dashed line showing the predicted exhaustion date.
- A summary card at the top: "3 quotas on track to exhaust before period
  end" with the names listed.

**How it works under the hood:**
Linear or polynomial regression on synthetic fill-rate time series data.
Could also use Facebook Prophet for seasonal patterns if we generate
enough historical dummy data.

**Why it's useful:**
Importers need to know whether a quota will still be available when their
shipment arrives. Policy teams want early warning of quotas under pressure.

---

## 3. Tariff Landscape Overview

**What the user sees:**
A high-level summary page showing the shape of the UK tariff at a glance.
Filters for commodity chapter, duty type, and country.

**Diagrams / visuals:**
- A heatmap with commodity chapters on one axis and countries on the other,
  coloured by duty rate. Dark red = high duty, white = zero-rated.
- A pie chart breaking down how many commodity codes are zero-rated vs
  low duty vs high duty.
- A histogram of duty rates across all declarable commodities.
- A scatter plot (PCA or t-SNE reduced) showing clusters of commodities
  with similar tariff profiles, colour-coded by chapter.

**How it works under the hood:**
K-means or DBSCAN clustering on features like duty amount, duty type
(percentage vs specific), number of preferential agreements, and whether
the commodity requires certificates.

**Why it's useful:**
Gives policy analysts and ministers a visual answer to "what does our
tariff actually look like?" without scrolling through thousands of rows.

---

## 4. FTA Coverage Map

**What the user sees:**
An interactive world map. Countries with an FTA or trade arrangement are
coloured by the depth of preferential coverage (number of commodity codes
covered). Clicking a country shows which commodity groups have preferences
and under which agreement.

**Diagrams / visuals:**
- A choropleth world map (using plotly) shaded by number of preferential
  commodity lines.
- A sidebar table listing the trade agreements and their start dates.
- A Sankey diagram showing flows from trade agreements to commodity
  chapters, sized by the number of preferential lines.
- A network graph with countries as nodes and shared cumulation
  arrangements as edges.

**How it works under the hood:**
Joins the preferential measures, geographical areas, and commodities
tables. No ML needed for the map itself, but could layer on a clustering
model to group countries by similarity of their preference profiles.

**Why it's useful:**
Trade negotiators and exporters can instantly see where the UK has
coverage and where the gaps are.

---

## 5. Commodity Code Change Timeline

**What the user sees:**
A timeline view showing all changes to commodity codes over time. Filters
for change type (split, merge, new, end, duty change, description change).

**Diagrams / visuals:**
- A horizontal timeline with dots for each change, colour-coded by type.
  Hover shows the detail.
- A stacked bar chart by quarter showing the volume of changes by type.
- An anomaly highlight panel: "These changes are unusual compared to the
  historical pattern" with a brief explanation.

**How it works under the hood:**
Isolation forest or simple z-score anomaly detection on the rate of
changes per chapter per quarter. Flags chapters with unusually high
activity.

**Why it's useful:**
Compliance teams need to track what's changed. Policy teams want to see
whether the nomenclature is stable or churning.

---

## 6. Document Requirements Checker

**What the user sees:**
A dropdown or search box to pick a commodity code. Below it, a checklist
of all certificates, licences, and controls required to import that
commodity, with links to the relevant GOV.UK guidance.

**Diagrams / visuals:**
- A checklist card per document requirement (CHED-A, CHED-PP, CITES,
  etc.) with a green tick or red cross.
- A summary badge: "This commodity requires 2 documents for import."
- A grouped bar chart across all commodities showing which document types
  are most commonly required.

**How it works under the hood:**
For the lookup, it's a simple join. For a predictive version, a
multi-label random forest classifier trained on commodity features
(chapter, description keywords, duty type) to predict which documents
are likely needed for a code not yet in the dataset.

**Why it's useful:**
Traders frequently get caught out by missing paperwork at the border.
This gives them a single view of what's needed.

---

## 7. Duty Comparison Tool

**What the user sees:**
Pick a commodity code and two or more countries. A side-by-side comparison
showing the MFN rate, any preferential rate, the preference margin, and
whether a quota applies.

**Diagrams / visuals:**
- A grouped bar chart with countries on the x-axis and duty rates on the
  y-axis, with MFN and preferential rates side by side.
- A table underneath with the full detail including quota order numbers
  and rules of origin references.
- A small "savings" callout: "Importing from Australia instead of MFN
  saves 12% + 147 GBP/100kg on this commodity."

**How it works under the hood:**
Joins measures, preferential measures, and quotas tables. Pure data
lookup, no ML, but very practical.

**Why it's useful:**
Sourcing decisions. An importer choosing between suppliers in different
countries can see the landed cost difference at a glance.

---

## 8. Tariff Protection Index

**What the user sees:**
A single-page summary ranking commodity chapters by how "protected" they
are, combining ad valorem rates, specific duties, quota restrictions, and
certificate requirements into a composite score.

**Diagrams / visuals:**
- A horizontal bar chart ranking chapters from most to least protected.
- A radar chart for a selected chapter showing the individual components
  of the protection score (duty rate, number of restrictions, quota
  tightness, document burden).
- A comparison mode: overlay two chapters on the same radar chart.

**How it works under the hood:**
Weighted composite index. Could also use PCA to derive the index from
the underlying features without manually choosing weights.

**Why it's useful:**
Quick answer to "which sectors does the UK protect most?" for policy
briefings, academic research, or journalist enquiries.

---

## Summary of Recommended Priority

| # | Proposal | Complexity | ML Involved | Visual Impact |
|---|----------|-----------|-------------|---------------|
| 1 | Commodity Code Classifier | Medium | Yes | High |
| 2 | Quota Exhaustion Dashboard | Medium | Yes | High |
| 3 | Tariff Landscape Overview | Medium | Yes | High |
| 4 | FTA Coverage Map | Low-Medium | Optional | Very High |
| 5 | Change Timeline | Low-Medium | Optional | Medium |
| 6 | Document Requirements Checker | Low | Optional | Medium |
| 7 | Duty Comparison Tool | Low | No | High |
| 8 | Tariff Protection Index | Medium | Optional | High |

Proposals 1, 2, and 4 are recommended as the initial build. They cover
the strongest ML use case (text classification), the most actionable
forecasting (quota exhaustion), and the most visually compelling view
(world map) respectively.
