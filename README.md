# Geospatial Librarian Agent

A Claude Code subagent that maintains a curated catalog of geospatial datasets and recommends the right data for analyst queries.

## Quick Start

1. Open this directory as a Claude Code project:
   ```bash
   cd /path/to/geospatial-librarian
   claude
   ```

2. The librarian agent is automatically available as a subagent. Invoke it by asking Claude to use it:
   ```
   Use the geospatial-librarian agent to find datasets for detecting
   parking lots in Phoenix and measuring their area.
   ```

3. Or reference it directly in a prompt to the analyst agent (when built):
   ```
   Ask the librarian what datasets would help us assess flood risk
   in a mountainous watershed.
   ```

## Project Structure

```
.claude/agents/
  geospatial-librarian.md   — Subagent definition and system prompt

datasets/
  index.yaml                — Tier 1: lightweight index (loaded fully into context)
  profiles/                 — Tier 2: detailed dataset profiles (loaded on demand)
    sentinel-2-l2a.yaml       Sentinel-2 L2A multispectral (10m, free)
    sentinel-1-rtc.yaml       Sentinel-1 RTC SAR (10m, free)
    landsat-8-9.yaml          Landsat 8/9 multispectral+thermal (30m, free)
    naip.yaml                 NAIP aerial imagery (0.6m, US only, free)
    pleiades.yaml             Pleiades Neo (1m, 6-band, commercial)
    skysat.yaml               Planet SkySat (1m, RGB+NIR, commercial)
    superdove.yaml            Planet SuperDove (3m, 8-band, commercial)
    spot-ms.yaml              SPOT multispectral (6m, commercial)
    worldview.yaml            Maxar WorldView (2m/0.5m pan, commercial)
    wyvern.yaml               Wyvern hyperspectral (5.3m, 23-band, commercial)
    capella.yaml              Capella X-band SAR (1m, commercial)
    umbra.yaml                Umbra X-band SAR (1m, commercial)
    esa-worldcover.yaml       ESA WorldCover land classification (10m, free)
    io-lulc-annual.yaml       IO LULC Annual land cover (10m, 2017-2023, free)
    cop-dem.yaml              Copernicus DEM (30m, free)
    nasadem.yaml              NASADEM reprocessed SRTM (30m, free)
    hwsd2-soils.yaml          Harmonized World Soil Database v2 (~1km, free)
    gpw-population.yaml       Gridded Population of the World (~1km, free)
    udel-weather-normals.yaml U.Delaware climate normals (~55km, free)
    modis-nbar-vegetation.yaml MODIS NBAR vegetation indices (500m, free)
    osm-features.yaml         OpenStreetMap vector features (free)
  recipes/                  — Data Engine access guides and code snippets
    {id}.md                   Natural language guide for each dataset
    {id}.py                   Python code snippets using hum_ai.data_engine

schemas/
  index-entry.schema.yaml   — Field definitions for index entries
  profile.schema.yaml       — Field definitions for full profiles

.beads/                     — Beads issue tracker (dependency-aware task tracking)
```

## How It Works

The librarian uses a **two-tier catalog**:

**Tier 1 (Index):** A compact summary of every dataset, loaded fully into the agent's context. Contains enough info (type, modality, resolution, coverage, key traits) for the agent to quickly identify candidate datasets for any query.

**Tier 2 (Profiles):** Rich, detailed profiles for each dataset. The agent loads only the profiles it needs after scanning the index. Contains strengths, limitations, preprocessing notes, access methods, and expert knowledge.

The agent reasons from **dataset capabilities** rather than pre-enumerated use cases. For example, it doesn't need "parking lot detection" listed anywhere — it can reason that a dataset with 10m resolution that distinguishes built surfaces can identify parking lots.

**Tier 3 (Recipes):** Practical guides for accessing each dataset through the [Hum Data Engine](https://github.com/Coastal-Carbon/data-engine). Each recipe has two files:
- A **markdown guide** (`{id}.md`) explaining how the Data Engine loads the dataset, what bands/layers are available, and how to configure pipelines
- A **Python script** (`{id}.py`) with importable code snippets using `hum_ai.data_engine` classes like `CollectionInput`, `CollectionName`, and the ancillary data framework

## Adding a New Dataset

### 1. Choose an ID

Pick a lowercase, hyphenated identifier that's concise but unambiguous. This ID ties everything together — it's the filename, the index reference, and what other profiles use in `commonly_paired_with`.

Good: `sentinel-2-l2a`, `cop-dem`, `osm-features`
Bad: `s2`, `Sentinel 2 Level 2A`, `my_dataset`

### 2. Write the full profile first

Create `datasets/profiles/{id}.yaml`. Use an existing profile as a starting point — copy one that's similar in data type and modify it.

Reference `schemas/profile.schema.yaml` for field definitions. Every profile needs:

**Required fields:**
- `id`, `name`, `provider`
- `spatial` (resolution, coverage, coordinate_system)
- `formats` (native, common_conversions)
- `access` (method, auth)
- `strengths` — when and why to use this dataset
- `limitations` — when NOT to use it, known gotchas
- `preprocessing_notes` — what the analyst needs to do before using it

**Conditional fields (include when applicable):**
- `temporal` — include for any dataset with a time dimension; omit for static products (e.g., a single DEM release)
- `bands` — for raster imagery with spectral bands
- `feature_classes` — for vector datasets
- `layers` — for multi-layer products (e.g., DEM with slope, aspect)
- `commonly_paired_with` — list of other dataset IDs that are frequently used alongside this one

**Writing the prose fields (strengths, limitations, preprocessing_notes):**

These are the most valuable part of the profile. Write them as if you're advising a colleague who's never used this dataset before. Be specific, be honest, and include things you've learned from experience that aren't in the official documentation.

For `strengths`: explain what makes this the RIGHT choice for certain problems. Don't just list features — explain why they matter.

For `limitations`: be blunt. Coverage gaps, resolution constraints, known quality issues, temporal limitations. The librarian needs to know when NOT to recommend something.

For `preprocessing_notes`: practical, step-by-step guidance. What tools to use, what pitfalls to avoid, what decisions need to be made before analysis.

### 3. Add an index entry

Add an entry to `datasets/index.yaml` under the `datasets:` list. Reference `schemas/index-entry.schema.yaml` for field definitions.

The critical field is `key_traits`. This is what the librarian agent scans to identify candidates, so it needs to capture the dataset's **capabilities** — what it can perceive, distinguish, or measure.

**Do this:**
```yaml
key_traits: |
  Distinguishes vegetation, water, bare soil, and built surfaces
  at 10m resolution. Multitemporal analysis possible with 5-day
  revisit. Free and open access.
```

**Not this:**
```yaml
key_traits: |
  Used for parking lot detection, crop monitoring, flood mapping,
  urban growth analysis, deforestation tracking...
```

The first version describes capabilities that the agent can reason over. The second pre-enumerates applications, which means the agent can only recommend the dataset for problems someone already thought of.

### 4. Update cross-references

Check if any existing profiles should add your new dataset to their `commonly_paired_with` list. For example, if you add a SAR dataset, the Sentinel-2 profile might want to reference it as a complement for cloud-covered conditions.

### 5. Write a Data Engine recipe

If the dataset is accessible through the Hum Data Engine, create two recipe files:

- `datasets/recipes/{id}.md` — A natural language guide explaining how the Data Engine accesses this dataset (STAC catalog, collection ID, band IDs, resolution, data type), how to configure a `CollectionInput` or ancillary data class, and how to use it in pipeline configurations (ImageChips, OlmoEarth, etc.)
- `datasets/recipes/{id}.py` — Python code snippets showing imports, `CollectionInput` construction, pipeline setup, and spectral index computation. Use actual class names and enum values from `hum_ai.data_engine`.

Use an existing recipe pair as a template — satellite imagery recipes follow a different pattern than ancillary data recipes.

### 6. Verify

The agent picks up new datasets automatically on its next invocation — no restart or configuration needed. Test by asking the librarian a question that your new dataset should be relevant to and confirm it gets recommended with sensible reasoning.

## Current Catalog (21 datasets)

| Category | Datasets | Resolution | Access |
|----------|----------|------------|--------|
| **Free Optical** | Sentinel-2 L2A, Landsat 8/9, NAIP | 10m, 30m, 0.6m | Free/open |
| **SAR** | Sentinel-1 RTC, Capella, Umbra | 10m, 1m, 1m | Free (S1) / Commercial |
| **Commercial VHR** | Pleiades, SkySat, SuperDove, SPOT-MS, WorldView | 1-6m | Commercial |
| **Hyperspectral** | Wyvern | 5.3m | Commercial |
| **Land Cover** | ESA WorldCover, IO LULC Annual | 10m | Free/open |
| **Elevation** | Copernicus DEM, NASADEM | 30m | Free/open |
| **Ancillary** | HWSD2 Soils, GPW Population, U.Delaware Weather, MODIS NBAR | 500m-55km | Free/open |
| **Vector** | OpenStreetMap | Feature-level | Free/open |

## Task Tracking

This project uses [beads](https://github.com/steveyegge/beads) for dependency-aware issue tracking. Use `bd list` to see open tasks and `bd ready` to find unblocked work.

## Architecture Context

This is one agent in a planned multi-agent geospatial system:

- **Librarian** (this agent) — knows the data catalog, recommends datasets
- **Analyst** (future) — performs geospatial analysis, consumes librarian recommendations
- **Archivist** (future) — discovers and catalogs new datasets, maintains the library

The librarian is read-only: it does not fetch data, modify the catalog, or perform analysis.
