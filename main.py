import geopandas as gpd
import os
from tqdm.auto import tqdm # Import tqdm

# Import GDAL/OGR's CPLSetOption for setting configuration options
# This is a bit more advanced and directly interacts with the underlying GDAL library
from osgeo import gdal # Requires gdal to be installed, which geopandas usually brings

# --- Configuration ---
# Path to the input GeoJSON file containing global active faults.
FAULTS_GEOJSON_PATH = os.path.join("geojsons", "gem_active_faults_harmonized.geojson")

# Path to the input country boundaries file.
COUNTRIES_FILE_PATH = os.path.join("shapefiles", "ne_10m_admin_0_countries.shp")

# UPDATED: Name of the output folder where the country-specific fault GeoJSON files will be saved.
# Now points to a subfolder named 'faults_by_country' INSIDE the 'output' folder.
OUTPUT_FOLDER = os.path.join("output", "faults_by_country")

# Column name in the countries data that holds the country's name.
COUNTRY_NAME_COLUMN = 'NAME_EN' # Verify this column name in your actual country data

# --- Main Script Execution ---

def split_faults_by_country(
    faults_path: str,
    countries_path: str,
    output_dir: str,
    country_name_col: str
):
    """
    Loads global active fault data and country boundaries, then splits the fault
    data into separate GeoJSON files for each country.

    Args:
        faults_path (str): Path to the GeoJSON file containing active faults.
        countries_path (str): Path to the Shapefile (or GeoJSON) containing country boundaries.
        output_dir (str): Directory where the country-specific fault files will be saved.
        country_name_col (str): The column name in the countries data that holds the country's name.
    """

    # Load the countries Shapefile (geopandas can read .shp directly)
    print(f"Loading countries data from: {countries_path}")
    try:
        # --- ADD THIS LINE TO ATTEMPT RESTORING .shx ---
        gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES') # Tell GDAL to try and restore .shx
        countries_gdf = gpd.read_file(countries_path)
        print(f"Loaded {len(countries_gdf)} country features.")
    except Exception as e:
        print(f"Error loading countries data from {countries_path}: {e}")
        return

    # Create the output directory if it doesn't exist
    # This will create 'output' first, then 'faults_by_country' inside 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output folder: {output_dir}")

    # Load the faults GeoJSON file
    print(f"Loading faults data from: {faults_path}")
    try:
        faults_gdf = gpd.read_file(faults_path)
        print(f"Loaded {len(faults_gdf)} fault features.")
    except Exception as e:
        print(f"Error loading faults GeoJSON from {faults_path}: {e}")
        return

    # Load the countries Shapefile (geopandas can read .shp directly)
    print(f"Loading countries data from: {countries_path}")
    try:
        countries_gdf = gpd.read_file(countries_path)
        print(f"Loaded {len(countries_gdf)} country features.")
    except Exception as e:
        print(f"Error loading countries data from {countries_path}: {e}")
        return

    # Check and standardize Coordinate Reference Systems (CRS)
    if faults_gdf.crs != countries_gdf.crs:
        print(f"CRS mismatch detected. Faults CRS: {faults_gdf.crs}, Countries CRS: {countries_gdf.crs}")
        print("Converting countries CRS to match faults CRS...")
        countries_gdf = countries_gdf.to_crs(faults_gdf.crs)
        print("CRS conversion complete.")
    else:
        print(f"CRS match: {faults_gdf.crs}")

    # Validate the country name column
    if country_name_col not in countries_gdf.columns:
        print(f"Error: Column '{country_name_col}' not found in countries data.")
        print(f"Available columns in countries data: {countries_gdf.columns.tolist()}")
        print("Please update COUNTRY_NAME_COLUMN in the script to the correct column name.")
        return

    # Perform a spatial join between faults and countries
    print(f"Performing spatial join (this may take a while for large datasets)...")
    
    # We only need the country name column and geometry from the countries_gdf for the join
    joined_gdf = gpd.sjoin(
        faults_gdf,
        countries_gdf[[country_name_col, 'geometry']],
        how="inner",
        predicate="intersects"
    )

    print(f"Spatial join complete. Found {len(joined_gdf)} fault segments associated with countries.")

    # Get unique country names to iterate through
    unique_countries = joined_gdf[country_name_col].unique()
    print(f"Found {len(unique_countries)} unique countries with associated fault data.")

    # Iterate through each unique country and save its fault data
    print("Splitting and saving fault data by country...")
    for country_name in tqdm(unique_countries, desc="Processing Countries"):
        # Handle cases where country name might be None
        if country_name is None:
            continue

        # Filter fault data for the current country
        country_faults = joined_gdf[joined_gdf[country_name_col] == country_name].copy()

        # Remove columns introduced by the sjoin that are not part of the original fault data
        columns_to_drop = [col for col in country_faults.columns if col.startswith('index_') or col == country_name_col]
        country_faults = country_faults.drop(columns=columns_to_drop, errors='ignore')

        # Create a clean filename by replacing spaces and slashes
        safe_country_name = str(country_name).replace(" ", "_").replace("/", "_").replace("\\", "_").strip()
        if not safe_country_name:
            safe_country_name = "unknown_country"

        output_filename = os.path.join(output_dir, f"faults_{safe_country_name.lower()}.geojson")

        # Save the filtered fault data to a new GeoJSON file
        try:
            country_faults.to_file(output_filename, driver="GeoJSON")
        except Exception as e:
            print(f"Error saving faults for {country_name} to {output_filename}: {e}")

    print("\n--- Process complete! ---")
    print(f"All fault data has been split and saved into the '{output_dir}' folder.")

# --- Run the main function ---
if __name__ == "__main__":
    split_faults_by_country(
        FAULTS_GEOJSON_PATH,
        COUNTRIES_FILE_PATH,
        OUTPUT_FOLDER,
        COUNTRY_NAME_COLUMN
    )