"""
NASADEM Elevation -- Standalone Recipe

Demonstrates how the Data Engine loads NASADEM elevation data from Microsoft
Planetary Computer via STAC and computes zonal statistics (median, range)
per H3 cell.

This is a self-contained version of the pipeline in:
    hum_ai.data_engine.ancillary.elevation.ElevationAncillaryData

Usage:
    python nasadem.py

Requirements:
    pip install pystac-client planetary-computer odc-stac h3 rioxarray rasterstats shapely
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

import h3
import odc.stac
import pandas as pd
import planetary_computer
import pystac_client
from rasterstats import zonal_stats
from shapely.geometry import Polygon
from shapely.ops import unary_union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration -- mirrors METADATA dict in elevation.py
# ---------------------------------------------------------------------------

STAC_CATALOG_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
STAC_COLLECTION = "nasadem"
DEFAULT_H3_RESOLUTION = 11  # ~2000 m2 cells, ~24.8m spacing
OUTPUT_COLUMNS = ["cell", "elevation_median", "elevation_range"]
NODATA_VALUE = -999


# ---------------------------------------------------------------------------
# Helper: convert H3 cells to a unified polygon (from h3_utils.py)
# ---------------------------------------------------------------------------


def h3_cells_to_polygon(h3_cells: Iterable[str]) -> Polygon:
    """Convert a collection of H3 cell IDs to a single Shapely polygon."""
    polygons = []
    for cell in h3_cells:
        # h3.cell_to_boundary returns (lat, lng) pairs; Shapely wants (lng, lat)
        lonlats = [(lng, lat) for (lat, lng) in h3.cell_to_boundary(cell)]
        polygons.append(Polygon(lonlats))
    return unary_union(polygons)


# ---------------------------------------------------------------------------
# Step 1: Search Planetary Computer STAC for NASADEM tiles
# ---------------------------------------------------------------------------


def search_nasadem_tiles(bbox: tuple[float, float, float, float]):
    """
    Search the Planetary Computer STAC catalog for NASADEM tiles
    intersecting the given bounding box.

    Parameters
    ----------
    bbox : tuple
        (west, south, east, north) in EPSG:4326

    Returns
    -------
    pystac.ItemCollection
        Matched STAC items
    """
    catalog = pystac_client.Client.open(
        STAC_CATALOG_URL,
        modifier=planetary_computer.sign_inplace,
    )

    search = catalog.search(
        collections=[STAC_COLLECTION],
        bbox=bbox,
    )
    items = search.item_collection()
    logger.info("STAC search returned %d NASADEM items", len(items))
    return items


# ---------------------------------------------------------------------------
# Step 2: Load raster data via odc.stac
# ---------------------------------------------------------------------------


def load_nasadem_raster(items, bbox: tuple[float, float, float, float]):
    """
    Load NASADEM tiles as a dask-backed xarray DataArray.

    Parameters
    ----------
    items : pystac.ItemCollection
        STAC items from the search step
    bbox : tuple
        (west, south, east, north) to spatially subset the load

    Returns
    -------
    xarray.DataArray
        Elevation values with nodata set to -999
    """
    data = odc.stac.load(
        items,
        chunks={"x": 128, "y": 128},
        bbox=bbox,
    )

    # NASADEM comes back with an extra singleton 'variable' dimension
    # after .to_array() -- squeeze it out
    data = data.to_array().squeeze(dim="variable")
    data.rio.write_nodata(NODATA_VALUE, inplace=True)

    logger.info(
        "Loaded raster: shape=%s, CRS=%s", data.shape, data.rio.crs
    )
    return data


# ---------------------------------------------------------------------------
# Step 3: Compute zonal statistics per H3 cell
# ---------------------------------------------------------------------------


def compute_elevation_stats(
    data,
    h3_cells: list[str],
    default_h3_resolution: int = DEFAULT_H3_RESOLUTION,
) -> pd.DataFrame:
    """
    Compute elevation median and range for each H3 cell.

    This mirrors the logic in ElevationAncillaryData.summarize_from_cells
    which delegates to summarize_numerical() in zonal_summary.py.

    Parameters
    ----------
    data : xarray.DataArray
        The loaded NASADEM raster
    h3_cells : list of str
        H3 cell IDs to summarize
    default_h3_resolution : int
        The H3 resolution that matches the raster pixel spacing.
        Cells finer than this use all_touched=True.

    Returns
    -------
    pd.DataFrame
        Columns: cell, elevation_median, elevation_range
    """
    resolution = h3.get_resolution(h3_cells[0])
    if resolution > default_h3_resolution:
        # Cells are small relative to 30m raster pixels
        logger.info("Using all_touched=True (H3 res %d > default %d)",
                     resolution, default_h3_resolution)
        all_touched = True
    else:
        all_touched = False

    crs = str(data.rio.crs)
    nodata = data.rio.nodata

    results = []
    for cell in h3_cells:
        # Get H3 cell boundary as a Shapely polygon in the raster's CRS
        boundary = h3.cell_to_boundary(cell)
        poly = Polygon([(lng, lat) for lat, lng in boundary])

        try:
            subset = data.rio.clip(geometries=[poly], crs="EPSG:4326")
        except Exception:
            # Cell has no data coverage (e.g., over ocean)
            continue

        summary = zonal_stats(
            [poly],
            subset.to_numpy(),
            affine=subset.rio.transform(),
            nodata=nodata,
            stats=["median", "range"],
            all_touched=all_touched,
        )[0]

        if None not in summary.values():
            results.append({
                "cell": cell,
                "elevation_median": summary["median"],
                "elevation_range": summary["range"],
            })

    df = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
    logger.info("Computed elevation stats for %d / %d cells",
                len(df), len(h3_cells))
    return df


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def summarize_elevation(h3_cells: list[str]) -> pd.DataFrame:
    """
    End-to-end pipeline: search, load, and summarize NASADEM elevation
    for the given H3 cells.

    This is the standalone equivalent of calling:
        ElevationAncillaryData().summarize_from_cells(h3_cells)
    """
    # Convert H3 cells to a bounding box for the STAC search
    polygon = h3_cells_to_polygon(h3_cells)
    bbox = polygon.bounds  # (minx, miny, maxx, maxy)

    # Search for NASADEM tiles
    items = search_nasadem_tiles(bbox)
    if len(items) == 0:
        logger.warning("No NASADEM tiles found for the given area")
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # Load the raster data (lazy / dask-backed)
    data = load_nasadem_raster(items, bbox)

    # Compute zonal statistics per H3 cell
    df = compute_elevation_stats(data, h3_cells)
    return df


# ---------------------------------------------------------------------------
# Demo / test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: a small cluster of H3 cells in coastal Alaska
    # (same test region used in the Data Engine's elevation.py)
    #
    # Generate H3 cells covering a small area near (60.66N, 145.91W)
    lat, lng = 60.66, -145.91
    center_cell = h3.latlng_to_cell(lat, lng, DEFAULT_H3_RESOLUTION)
    # Get the center cell plus its immediate neighbors
    test_cells = list(h3.grid_disk(center_cell, k=1))
    logger.info("Test area: %d H3 cells at resolution %d",
                len(test_cells), DEFAULT_H3_RESOLUTION)

    result = summarize_elevation(test_cells)
    print("\n--- NASADEM Elevation Summary ---")
    print(result.to_string(index=False))
    print(f"\nMedian elevation across cells: {result['elevation_median'].median():.1f} m")
    print(f"Max elevation range in a cell: {result['elevation_range'].max():.1f} m")
