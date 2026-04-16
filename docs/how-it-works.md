# UK Tariff Data Explorer — How It Works

A plain-English walkthrough of every page in the dashboard, what
algorithms power them, and why we chose them. Written for engineers
who want to understand the system without reading the source code.

---

## Architecture at a Glance

```
data/*.csv
    ↓
app/csv_loader.py            ← reads CSVs, coerces types
app/main.py                  ← FastAPI serves them as JSON endpoints
    ↓
    GET /api/commodities
    GET /api/measures_on_declarable_commodities
    GET /api/trade_quotas
    ...etc
    ↓
streamlit_app/lib/data.py    ← fetches data from the API via HTTP
    ↓
streamlit_app/pages/*.py     ← one file per dashboard page
    ↓
Streamlit                    ← renders the UI in the browser
```

The dashboard never reads CSV files directly. All data flows through
the FastAPI layer. This means:

- The API is the single source of truth.
- The dashboard doesn't need filesystem access to the data directory.
- Later, we can add CSV upload endpoints to the API and the dashboard
  will pick up new datasets automatically.
- We could swap the CSV backend for a database without changing any
  Streamlit code.

The API base URL defaults to `http://127.0.0.1:8000` and can be
overridden with the `API_BASE_URL` environment variable.

To run both together:

```bash
# Terminal 1 — start the API
pixi run serve

# Terminal 2 — start the dashboard
pixi run dashboard
```

All dependencies are managed by Pixi (`pixi.toml`).

---

## The Data

Eight CSV files generated to mirror the real open datasets published
by the Department for Business and Trade at data.api.trade.gov.uk.

| File | API Endpoint | Records |
|------|-------------|---------|
| `commodities.csv` | `GET /api/commodities` | 86 |
| `measures_on_declarable_commodities.csv` | `GET /api/measures_on_declarable_commodities` | 62 |
| `trade_quotas.csv` | `GET /api/trade_quotas` | 15 |
| `preferential_measures.csv` | `GET /api/preferential_measures` | 24 |
| `commodity_code_changes.csv` | `GET /api/commodity_code_changes` | 15 |
| `geographical_areas.csv` | `GET /api/geographical_areas` | 42 |
| `measure_types.csv` | `GET /api/measure_types` | 24 |
| `certificates_and_licences.csv` | `GET /api/certificates_and_licences` | 24 |

All data is fictional. The structure and column names match the real
datasets so the code would work with live data.

### How the API works

The FastAPI app (`app/main.py`) auto-discovers every CSV file in the
`data/` directory at startup. Each file becomes a queryable endpoint:

- `GET /` — lists all available datasets with record counts and columns
- `GET /api/{resource}` — returns records with filtering, pagination,
  and field projection
- `GET /api/{resource}/{index}` — returns a single record by index
- `POST /reload` — re-scans the data directory without restarting

Query parameters:
- Any column name as a filter: `?commodity_code=0201100000`
- `_limit` and `_offset` for pagination
- `_fields` for column projection: `?_fields=commodity_code,description`

### How the dashboard fetches data

The Streamlit data layer (`streamlit_app/lib/data.py`) makes HTTP
requests to the API using Python's built-in `urllib`. Each loader
function fetches all records for a resource, converts the JSON
response into a pandas DataFrame, and applies type coercion (dates,
numerics, strings). Results are cached for 60 seconds using
Streamlit's `@st.cache_data` decorator.

If the API is unreachable, the dashboard shows a clear error message
and stops rather than crashing with a confusing traceback.

---

## Page 1 — Commodity Code Classifier

### What the user sees

A search box. Type "beef" or "laptop" and get a ranked list of the
most relevant commodity codes, a bar chart of similarity scores,
expandable hierarchy trees, and a histogram of how your query scored
across all codes.

### The algorithm: TF-IDF cosine similarity with synonym expansion

We tried logistic regression first (a proper classifier), but with
only 55 declarable codes and one training example per class, the model
couldn't learn anything — every prediction came back at ~1.9%.

Instead we treat it as a **search problem**:

**Step 1 — Build the index (runs once, cached):**

- Take every declarable commodity code and walk up the hierarchy to
  collect all parent descriptions. "Boneless" becomes "Meat and
  edible meat offal > Meat of bovine animals, fresh or chilled >
  Boneless".
- Append trade synonyms. The tariff uses formal language ("bovine")
  but users type everyday words ("beef"). A synonym map expands
  "bovine" to "beef cattle cow", "data-processing" to "computer
  laptop pc desktop", and so on.
- Feed all enriched descriptions into a **TF-IDF vectoriser**. TF-IDF
  (Term Frequency-Inverse Document Frequency) converts text into
  numbers by measuring how important each word is to a document
  relative to the whole corpus. Common words get low scores, rare
  distinctive words get high scores.

**Step 2 — At query time:**

- The user's query is vectorised using the same TF-IDF model.
- We compute **cosine similarity** between the query vector and every
  commodity vector. Cosine similarity measures the angle between two
  vectors — 1.0 means identical direction (perfect match), 0.0 means
  completely unrelated.
- Results are ranked by similarity and the top 10 are displayed.

### Why this approach

- Works with tiny datasets (no training needed, just indexing).
- Fast — the entire search takes milliseconds.
- Interpretable — the score directly tells you how much word overlap
  there is between your query and the commodity description.
- The synonym map is easy to extend.

### Limitations

- Only matches on word overlap. "Red meat" won't match "bovine"
  unless we add that synonym.
- With the full tariff (~15,000 codes), we'd switch to a sentence
  embedding model (e.g. all-MiniLM) for semantic similarity.

---

## Page 2 — Quota Exhaustion Dashboard

### What the user sees

A summary of critical quotas, a table with traffic-light indicators,
gauge charts showing fill rates, and a line chart forecasting when
each quota will run out.

### The algorithm: linear regression for fill-rate forecasting

**Gauge charts** are pure visualisation. Each quota's fill rate is
plotted on a gauge with three zones: green (0-60%), amber (60-90%),
red (90-100%).

**The forecast works like this:**

1. Generate synthetic monthly data points between the quota period
   start and the last allocation date, interpolating from 0% to the
   current fill rate with small random noise.
2. Fit a scikit-learn `LinearRegression` to these points
   (X = days since period start, y = fill rate).
3. Project the model forward to the end of the quota period.
4. Calculate the exhaustion date algebraically:
   `exhaustion_day = (100 - intercept) / slope`.

### Why linear regression

- Quotas generally fill at a roughly steady rate within a period.
- With only a handful of data points, anything more complex (ARIMA,
  Prophet) would overfit.
- The forecast is easy to explain: "at the current rate of fill,
  this quota will be exhausted by [date]".

### Limitations

- Real quota fill rates are lumpy (big shipments cause step changes).
- With real historical data across multiple years, we could use
  seasonal models to account for patterns.

---

## Page 3 — Tariff Landscape Overview

### What the user sees

A histogram of duty rates, a pie chart of duty bands, a heatmap of
mean duty by chapter, and a scatter plot of commodity clusters.

### The algorithms: K-means clustering + PCA

**Histogram and pie chart** are straightforward aggregations. Duty
rates are bucketed into bands (zero-rated, low, medium, high).

**Heatmap** shows mean MFN duty rate per commodity chapter (first two
digits of the code), coloured green (low) to red (high).

**Clustering works like this:**

1. For each declarable commodity, build a feature vector:
   `[duty_amount, is_specific_duty, n_preferential_agreements, n_certificate_requirements]`
2. Standardise features (zero mean, unit variance) using
   `StandardScaler` so no single feature dominates.
3. **K-means** groups commodities into k clusters (user-selectable,
   default 3). It places k centroids in feature space and iteratively
   assigns each point to its nearest centroid, then moves centroids
   to the mean of their assigned points. Converges when assignments
   stop changing.
4. **PCA** (Principal Component Analysis) reduces the 4D feature
   space to 2D for plotting. PCA finds the directions of maximum
   variance and projects onto those axes. The first two principal
   components capture the most information possible in two dimensions.

### Why K-means + PCA

- K-means is the simplest clustering algorithm and works well when
  clusters are roughly spherical.
- PCA gives a 2D view that preserves as much structure as possible.
- Together they answer: "are there natural groupings in how the UK
  applies tariffs?" (e.g. zero-rated tech vs protected agriculture).

### Limitations

- K-means requires you to choose k. The slider lets users explore
  different values.
- With more features, DBSCAN would be better as it finds clusters of
  arbitrary shape without needing k upfront.

---

## Page 4 — FTA Coverage Map

### What the user sees

An interactive world map coloured by preferential coverage depth,
tables of trade agreements, a Sankey diagram showing flows from
agreements to commodity chapters, and a cumulation network.

### How it works (no ML — data joining and visualisation)

**Choropleth map:** The preferential measures table is grouped by
country. The count of distinct commodity codes with a preferential
rate becomes the colour intensity on a Plotly choropleth.

**Sankey diagram:** Each preferential measure links a trade agreement
to a commodity chapter. The Sankey shows these flows, sized by the
number of preferential lines. Agreements on the left, chapters on
the right.

**Cumulation network:** Countries sharing a trade agreement are
linked. If Colombia, Peru, and Ecuador are all in the UK-Andean
agreement, they form a triangle. This shows where diagonal cumulation
(using materials from partner countries in rules of origin) is
possible.

### Why these visualisations

- The map gives an instant global picture of "where do we have deals?"
- The Sankey shows which sectors each deal covers.
- The network reveals cumulation opportunities not obvious from a
  flat table.

---

## Page 5 — Change Timeline

### What the user sees

A scatter plot timeline of commodity code changes, a stacked bar chart
by quarter, anomaly alerts, and a detail table.

### The algorithm: z-score anomaly detection

**Timeline and bar chart** are straightforward — each change is
plotted by effective date, colour-coded by type (split, merge, new,
end, duty change, description change).

**Anomaly detection works like this:**

1. Count total changes per quarter.
2. Calculate the mean and standard deviation across all quarters.
3. Any quarter with changes > mean + 1.5 x standard deviation is
   flagged as anomalous.

This is a simple z-score threshold — no model training needed.

### Why z-score

- With only 15 changes across a few quarters, anything more
  sophisticated (isolation forest, autoencoders) would be overkill.
- The 1.5 sigma threshold is a common choice that balances sensitivity
  with false positives.

### Limitations

- With more data, an isolation forest would catch subtler anomalies
  (e.g. unusual combinations of change type and chapter, not just
  volume).

---

## Page 6 — Document Requirements Checker

### What the user sees

A dropdown to pick a commodity code. Below it, a checklist of all
certificates, licences, and controls required to import that commodity,
with links to GOV.UK guidance. Plus bar charts of the most common
document types.

### How it works (no ML — lookup and aggregation)

This is a simple join: filter the certificates table by the selected
commodity code and display the results. The bar chart groups by
document code across all commodities.

### Why it's useful

Traders frequently get caught by missing paperwork at the border.
This gives them a single view of what's needed before they ship.

### Future ML opportunity

A multi-label random forest classifier could predict which documents
are likely needed for a commodity code not yet in the dataset, based
on features like chapter, description keywords, and duty type.

---

## Page 7 — Duty Comparison Tool

### What the user sees

Pick a commodity code and one or more countries. A grouped bar chart
shows MFN vs preferential duty rates side by side. Savings callouts
highlight the benefit of each trade agreement. A detail table shows
rules of origin references and cumulation types. Applicable quotas
are listed below.

### How it works (no ML — data joining)

1. Look up the MFN (Most Favoured Nation) rate for the selected
   commodity from the measures table.
2. Look up any preferential rates from the preferential measures
   table, filtered by the selected countries.
3. Look up any applicable quotas from the trade quotas table.
4. Display everything side by side.

### Why it's useful

Sourcing decisions. An importer choosing between suppliers in
different countries can see the landed cost difference at a glance.
"Importing from Australia under the UK-Australia FTA saves 12% +
147 GBP/100kg compared to MFN."

---

## Page 8 — Tariff Protection Index

### What the user sees

A horizontal bar chart ranking commodity chapters from most to least
"protected". A radar chart lets you compare two or three chapters
across four dimensions. A methodology table explains the scoring.

### The algorithm: weighted composite index with min-max scaling

1. For each commodity chapter, calculate four raw metrics:
   - **Mean duty rate** — average MFN duty across all codes in the
     chapter.
   - **Max duty rate** — the highest single duty in the chapter.
   - **Quota fill pressure** — mean fill rate of quotas covering
     that chapter (high fill = more pressure = more protection).
   - **Certificate burden** — count of document requirements for
     codes in that chapter.

2. **Min-max scale** each metric to 0-1 across all chapters. This
   puts them on the same scale regardless of units (percentages vs
   counts).

3. Apply **weights** to create a composite score:
   - Mean duty: 35%
   - Max duty: 20%
   - Quota fill pressure: 25%
   - Certificate burden: 20%

4. The radar chart plots all four normalised components for selected
   chapters, making it easy to see *why* a chapter scores high (is it
   the duty rate? the quotas? the paperwork?).

### Why a weighted composite

- Simple, transparent, and explainable to non-technical stakeholders.
- The weights can be adjusted based on policy priorities.
- No black box — you can see exactly which component drives the score.

### Limitations

- The weights are subjective. An alternative would be to use PCA to
  derive the index from the data without manually choosing weights.
- With real data, trade volume should be a factor (a high duty on a
  commodity nobody imports isn't really "protection").

---

## Summary of Algorithms Used

| Page | Algorithm | Library | Purpose |
|------|-----------|---------|---------|
| 1. Classifier | TF-IDF + cosine similarity | scikit-learn | Text search / commodity code matching |
| 2. Quotas | Linear regression | scikit-learn | Fill-rate forecasting |
| 3. Landscape | K-means + PCA | scikit-learn | Tariff profile clustering |
| 4. FTA Map | — | plotly | Geospatial visualisation |
| 5. Timeline | Z-score threshold | numpy | Anomaly detection |
| 6. Documents | — | pandas | Lookup and aggregation |
| 7. Comparison | — | pandas | Data joining |
| 8. Protection | Min-max scaling + weighted composite | scikit-learn | Composite scoring |

---

## What We'd Do Differently at Scale

If this moved from a demo to a production system with the full
~15,000 commodity codes and real trade data:

1. **Classifier** — Replace TF-IDF with a sentence transformer
   (e.g. all-MiniLM-L6-v2) for semantic similarity. "Red meat" would
   match "bovine" without needing a synonym map.

2. **Quota forecasting** — Use Facebook Prophet or a gradient-boosted
   model trained on historical fill-rate time series across multiple
   years, with seasonality and external regressors (exchange rates,
   trade policy announcements).

3. **Clustering** — Switch to DBSCAN or HDBSCAN for arbitrary-shape
   clusters. Add features like trade volume, number of active quotas,
   and anti-dumping measures.

4. **Anomaly detection** — Use an isolation forest trained on
   multi-dimensional change features (chapter, type, magnitude,
   timing) rather than a simple volume threshold.

5. **Data pipeline** — Replace static CSVs with a scheduled pull from
   the real data.api.trade.gov.uk API, with change detection and
   alerting. The FastAPI layer already supports `POST /reload` for
   hot-reloading new data.

6. **CSV uploads** — Add a `POST /api/upload` endpoint to the FastAPI
   app that accepts CSV files, validates them, and adds them as new
   datasets. The dashboard would pick them up automatically on the
   next cache refresh (currently 60 seconds).

7. **Caching** — Move from Streamlit's in-process cache to Redis or
   similar for multi-user deployments. The API could also add
   ETags/Last-Modified headers so the dashboard only re-fetches when
   data has changed.

8. **Authentication** — Add API key or OAuth2 authentication to the
   FastAPI layer. The dashboard would pass credentials via the
   `API_BASE_URL` or a separate config.
