import geopandas as gpd
import os
from tqdm.auto import tqdm # For progress bar
from osgeo import gdal # Used to potentially restore .shx file for shapefiles
import re # Import regular expression module

# --- Configuration ---
# Path to the input GeoJSON file containing global active faults.
# It's located in the 'geojsons' subfolder.
FAULTS_GEOJSON_PATH = os.path.join("geojsons", "gem_active_faults_harmonized.geojson")

# Path to the input country boundaries file.
# This is expected to be the .shp file you downloaded from Natural Earth.
# It's located in the 'shapefiles' subfolder.
COUNTRIES_FILE_PATH = os.path.join("shapefiles", "ne_10m_admin_0_countries.shp")

# Name of the output folder where the country-specific fault GeoJSON files will be saved.
# This will create 'faults_by_country' inside your 'output' folder.
OUTPUT_FOLDER = os.path.join("output", "faults_by_country")

# Column name in the countries data that holds the country's name.
# For Natural Earth's 'ne_10m_admin_0_countries.shp', common names are 'NAME_EN', 'NAME_LONG', or 'SOVEREIGNT'.
# IMPORTANT: Verify this column name in your actual country data (e.g., by inspecting it in QGIS).
COUNTRY_NAME_COLUMN = 'NAME_EN'

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

    # Create the main output directory and its subfolder if they don't exist.
    # os.makedirs creates all necessary intermediate directories.
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
        print("Please ensure 'gem_active_faults_harmonized.geojson' exists in the 'geojsons' folder and is valid.")
        return

    # Load the countries Shapefile.
    # geopandas can read .shp files directly.
    print(f"Loading countries data from: {countries_path}")
    try:
        # --- POTENTIAL FIX FOR .shx ERROR ---
        # If you encounter "Unable to open .shx" errors, uncomment the line below.
        # This tells GDAL (used by geopandas) to try and restore a missing .shx file.
        gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES')

        countries_gdf = gpd.read_file(countries_path)
        print(f"Loaded {len(countries_gdf)} country features.")
    except Exception as e:
        print(f"Error loading countries data from {countries_path}: {e}")
        print("Please ensure all Shapefile components (.shp, .shx, .dbf, .prj) are present and uncorrupted in the 'shapefiles' folder.")
        print("If .shx is missing, ensure 'gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES')' is uncommented.")
        return

    # --- FIX: Set CRS for countries_gdf if it's None (naive geometry) ---
    # Natural Earth data is typically in WGS84 (EPSG:4326).
    if countries_gdf.crs is None:
        print(f"Detected naive geometry for countries_gdf. Setting CRS to EPSG:4326 (WGS84).")
        countries_gdf.crs = "EPSG:4326"
    # --- END FIX ---


    # Check and standardize Coordinate Reference Systems (CRS).
    # It's crucial for both GeoDataFrames to have the same CRS for accurate spatial operations.
    # GeoJSON typically uses EPSG:4326 (WGS84 - Latitude/Longitude).
    if faults_gdf.crs != countries_gdf.crs:
        print(f"CRS mismatch detected. Faults CRS: {faults_gdf.crs}, Countries CRS: {countries_gdf.crs}")
        print("Converting countries CRS to match faults CRS...")
        countries_gdf = countries_gdf.to_crs(faults_gdf.crs)
        print("CRS conversion complete.")
    else:
        print(f"CRS match: {faults_gdf.crs}")

    # Validate the country name column.
    # Ensures the specified column exists in the countries GeoDataFrame.
    if country_name_col not in countries_gdf.columns:
        print(f"Error: Column '{country_name_col}' not found in countries data.")
        print(f"Available columns in countries data: {countries_gdf.columns.tolist()}")
        print("Please update COUNTRY_NAME_COLUMN in the script to the correct column name found in your country data.")
        return

    # Perform a spatial join between faults and countries.
    # 'inner' join ensures only fault segments that intersect a country are kept.
    # 'predicate="intersects"' means a fault is considered 'in' a country if it overlaps or is contained by it.
    print(f"Performing spatial join (this may take a while for large datasets)...")
    
    # Select only the country name column and geometry from the countries_gdf for the join.
    # This optimizes the spatial join operation.
    joined_gdf = gpd.sjoin(
        faults_gdf,
        countries_gdf[[country_name_col, 'geometry']],
        how="inner",
        predicate="intersects"
    )

    print(f"Spatial join complete. Found {len(joined_gdf)} fault segments associated with countries.")

    # Get unique country names from the joined data to iterate through.
    unique_countries = joined_gdf[country_name_col].unique()
    print(f"Found {len(unique_countries)} unique countries with associated fault data.")

    # Iterate through each unique country and save its fault data to a separate GeoJSON file.
    print("Splitting and saving fault data by country...")
    # Use tqdm to display a progress bar during the country processing loop.
    for country_name in tqdm(unique_countries, desc="Processing Countries"):
        # Handle cases where country name might be None or invalid.
        if country_name is None or not isinstance(country_name, (str, bytes)):
            print(f"Skipping fault segments with invalid country name: {country_name}")
            continue

        # Filter fault data for the current country.
        # .copy() is used to avoid SettingWithCopyWarning, ensuring operations on this subset are independent.
        country_faults = joined_gdf[joined_gdf[country_name_col] == country_name].copy()

        # Remove temporary columns introduced by the sjoin (e.g., 'index_right')
        # and the redundant country name column from the result GeoDataFrame.
        columns_to_drop = [col for col in country_faults.columns if col.startswith('index_') or col == country_name_col]
        country_faults = country_faults.drop(columns=columns_to_drop, errors='ignore')

        # --- MODIFICATION: Sanitize filename for Flutter compatibility ---
        # 1. Convert to string and strip whitespace
        safe_country_name = str(country_name).strip()
        # 2. Remove apostrophes (like in "People's Republic of China")
        safe_country_name = safe_country_name.replace("'", "")
        # 3. Replace spaces, hyphens, and other special characters with underscores
        #    Use regex to replace any non-alphanumeric character (except underscore) with an underscore
        safe_country_name = re.sub(r'[^a-zA-Z0-9_]+', '_', safe_country_name)
        # 4. Convert to lowercase
        safe_country_name = safe_country_name.lower()
        # 5. Handle cases where name might become empty or just underscores after cleaning
        safe_country_name = safe_country_name.strip('_') # Remove leading/trailing underscores
        if not safe_country_name:
            safe_country_name = "unknown_country"
        # --- END MODIFICATION ---

        output_filename = os.path.join(output_dir, f"faults_{safe_country_name}.geojson")

        # Save the filtered fault data to a new GeoJSON file.
        try:
            # Explicitly set driver="GeoJSON" to ensure correct output format.
            country_faults.to_file(output_filename, driver="GeoJSON")
        except Exception as e:
            print(f"Error saving faults for {country_name} to {output_filename}: {e}")

    print("\n--- Process complete! ---")
    print(f"All fault data has been split and saved into the '{output_dir}' folder.")

# --- Run the main function when the script is executed ---
if __name__ == "__main__":
    split_faults_by_country(
        FAULTS_GEOJSON_PATH,
        COUNTRIES_FILE_PATH,
        OUTPUT_FOLDER,
        COUNTRY_NAME_COLUMN
    )