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
    sentinel-2-l2a.yaml
    naip.yaml
    osm-features.yaml
    landsat-8-9.yaml
    cop-dem.yaml

schemas/
  index-entry.schema.yaml   — Field definitions for index entries
  profile.schema.yaml       — Field definitions for full profiles
```

## How It Works

The librarian uses a **two-tier catalog**:

**Tier 1 (Index):** A compact summary of every dataset, loaded fully into the agent's context. Contains enough info (type, modality, resolution, coverage, key traits) for the agent to quickly identify candidate datasets for any query.

**Tier 2 (Profiles):** Rich, detailed profiles for each dataset. The agent loads only the profiles it needs after scanning the index. Contains strengths, limitations, preprocessing notes, access methods, and expert knowledge.

The agent reasons from **dataset capabilities** rather than pre-enumerated use cases. For example, it doesn't need "parking lot detection" listed anywhere — it can reason that a dataset with 10m resolution that distinguishes built surfaces can identify parking lots.

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

### 5. Verify

The agent picks up new datasets automatically on its next invocation — no restart or configuration needed. Test by asking the librarian a question that your new dataset should be relevant to and confirm it gets recommended with sensible reasoning.

## Architecture Context

This is one agent in a planned multi-agent geospatial system:

- **Librarian** (this agent) — knows the data catalog, recommends datasets
- **Analyst** (future) — performs geospatial analysis, consumes librarian recommendations
- **Archivist** (future) — discovers and catalogs new datasets, maintains the library

The librarian is read-only: it does not fetch data, modify the catalog, or perform analysis.
