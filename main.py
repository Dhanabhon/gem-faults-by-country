import geopandas as gpd
import os
from tqdm.auto import tqdm
from osgeo import gdal
import re
import argparse # Import argparse for command-line arguments

# --- Configuration ---
FAULTS_GEOJSON_PATH = os.path.join("geojsons", "gem_active_faults_harmonized.geojson")
COUNTRIES_FILE_PATH = os.path.join("shapefiles", "ne_10m_admin_0_countries.shp")
BASE_OUTPUT_FOLDER = "output" # Base directory for all outputs
COUNTRY_NAME_COLUMN = 'NAME_EN' # Column holding country names in Natural Earth data

# --- Helper function to get file size ---
def get_file_size_mb(filepath):
    """Returns file size in Megabytes (MB)."""
    if os.path.exists(filepath):
        return os.path.getsize(filepath) / (1024 * 1024)
    return 0

# --- Main Script Logic ---
def split_faults_by_country(
    faults_path: str,
    countries_path: str,
    base_output_dir: str,
    country_name_col: str,
    simplify_tolerance: float = 0.0 # Default to no simplification
):
    """
    Loads global active fault data and country boundaries, then splits the fault
    data into separate GeoJSON files for each country, with optional simplification.

    Args:
        faults_path (str): Path to the GeoJSON file containing active faults.
        countries_path (str): Path to the Shapefile (or GeoJSON) containing country boundaries.
        base_output_dir (str): The base output directory (e.g., 'output').
        country_name_col (str): The column name in the countries data that holds the country's name.
        simplify_tolerance (float): The tolerance for simplifying geometries (in CRS units).
                                    A value of 0.0 means no simplification.
    """
    # Dynamically set the specific output folder name based on tolerance
    if simplify_tolerance > 0:
        folder_suffix = f"simplified_{str(simplify_tolerance).replace('.', '_')}"
    else:
        folder_suffix = "original" # Or "raw", "unsimplified"

    output_dir = os.path.join(base_output_dir, "faults_by_country", folder_suffix)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output folder: {output_dir}")

    # Load faults GeoJSON
    print(f"Loading faults data from: {faults_path}")
    try:
        faults_gdf = gpd.read_file(faults_path)
        print(f"Loaded {len(faults_gdf)} fault features.")
    except Exception as e:
        print(f"Error loading faults GeoJSON from {faults_path}: {e}")
        print("Please ensure 'gem_active_faults_harmonized.geojson' exists in the 'geojsons' folder and is valid.")
        return

    # Load countries Shapefile
    print(f"Loading countries data from: {countries_path}")
    try:
        gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES')
        countries_gdf = gpd.read_file(countries_path)
        print(f"Loaded {len(countries_gdf)} country features.")
    except Exception as e:
        print(f"Error loading countries data from {countries_path}: {e}")
        print("Please ensure all Shapefile components (.shp, .shx, .dbf, .prj) are present and uncorrupted.")
        print("If .shx is missing, ensure 'gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES')' is uncommented.")
        return

    # Set CRS for countries_gdf if it's None
    if countries_gdf.crs is None:
        print(f"Detected naive geometry for countries_gdf. Setting CRS to EPSG:4326 (WGS84).")
        countries_gdf.crs = "EPSG:4326"

    # Check and standardize CRSs
    if faults_gdf.crs != countries_gdf.crs:
        print(f"CRS mismatch detected. Faults CRS: {faults_gdf.crs}, Countries CRS: {countries_gdf.crs}")
        print("Converting countries CRS to match faults CRS...")
        countries_gdf = countries_gdf.to_crs(faults_gdf.crs)
        print("CRS conversion complete.")
    else:
        print(f"CRS match: {faults_gdf.crs}")

    # Validate country name column
    if country_name_col not in countries_gdf.columns:
        print(f"Error: Column '{country_name_col}' not found in countries data.")
        print(f"Available columns in countries data: {countries_gdf.columns.tolist()}")
        print("Please update COUNTRY_NAME_COLUMN in the script to the correct column name found in your country data.")
        return

    # Perform spatial join
    print(f"Performing spatial join (this may take a while for large datasets)...")
    joined_gdf = gpd.sjoin(
        faults_gdf,
        countries_gdf[[country_name_col, 'geometry']],
        how="inner",
        predicate="intersects"
    )
    print(f"Spatial join complete. Found {len(joined_gdf)} fault segments associated with countries.")

    # Get unique country names
    unique_countries = joined_gdf[country_name_col].unique()
    print(f"Found {len(unique_countries)} unique countries with associated fault data.")

    # Process and save fault data by country
    print("Splitting and saving fault data by country...")

    original_sizes = {}
    simplified_sizes = {}

    for country_name in tqdm(unique_countries, desc="Processing Countries"):
        if country_name is None or not isinstance(country_name, (str, bytes)):
            print(f"Skipping fault segments with invalid country name: {country_name}")
            continue

        country_faults = joined_gdf[joined_gdf[country_name_col] == country_name].copy()

        # Sanitize filename for Flutter compatibility
        safe_country_name = str(country_name).strip()
        safe_country_name = safe_country_name.replace("'", "")
        safe_country_name = re.sub(r'[^a-zA-Z0-9_]+', '_', safe_country_name)
        safe_country_name = safe_country_name.lower()
        safe_country_name = safe_country_name.strip('_')
        if not safe_country_name:
            safe_country_name = "unknown_country"

        output_filename = os.path.join(output_dir, f"faults_{safe_country_name}.geojson")
        temp_original_filename = os.path.join(output_dir, f"temp_original_faults_{safe_country_name}.geojson")

        try:
            # Store original size (by saving temporarily) if simplification is active
            if simplify_tolerance > 0:
                country_faults.to_file(temp_original_filename, driver="GeoJSON")
                original_sizes[country_name] = get_file_size_mb(temp_original_filename)

            # Apply simplification if tolerance is greater than 0
            if simplify_tolerance > 0:
                country_faults.geometry = country_faults.geometry.simplify(
                    tolerance=simplify_tolerance,
                    preserve_topology=True
                )
                country_faults = country_faults[~country_faults.is_empty]

            # Save the processed GeoJSON file
            country_faults.to_file(output_filename, driver="GeoJSON")
            simplified_sizes[country_name] = get_file_size_mb(output_filename)

            # Clean up temporary original file
            if os.path.exists(temp_original_filename):
                os.remove(temp_original_filename)

        except Exception as e:
            print(f"Error saving faults for {country_name} to {output_filename}: {e}")
            if os.path.exists(temp_original_filename):
                os.remove(temp_original_filename)

    print("\n--- Process complete! ---")
    print(f"All fault data has been split and saved into the '{output_dir}' folder.")

    # Display size reduction summary (only if simplification was applied)
    if simplify_tolerance > 0:
        print("\n--- File Size Reduction Summary ---")
        total_original_size = 0
        total_simplified_size = 0
        
        for country_name in unique_countries:
            if country_name in original_sizes and country_name in simplified_sizes:
                orig_size = original_sizes[country_name]
                simp_size = simplified_sizes[country_name]
                total_original_size += orig_size
                total_simplified_size += simp_size

                reduction_percent = 0
                if orig_size > 0:
                    reduction_percent = ((orig_size - simp_size) / orig_size) * 100

                print(f"  {country_name}:")
                print(f"    Original: {orig_size:.4f} MB")
                print(f"    Simplified: {simp_size:.4f} MB")
                print(f"    Reduction: {reduction_percent:.2f}%")
            elif country_name is not None: # Only print if simplification was intended
                 if country_name not in original_sizes:
                     print(f"  {country_name}: No original size recorded (might have been skipped due to errors or no faults).")
                 elif country_name not in simplified_sizes:
                     print(f"  {country_name}: No simplified size recorded (might have been skipped due to errors).")

        print("\n--- Overall Summary ---")
        overall_reduction_percent = 0
        if total_original_size > 0:
            overall_reduction_percent = ((total_original_size - total_simplified_size) / total_original_size) * 100
        
        print(f"Total Original Size (all countries): {total_original_size:.4f} MB")
        print(f"Total Simplified Size (all countries): {total_simplified_size:.4f} MB")
        print(f"Overall Size Reduction: {overall_reduction_percent:.2f}%")

# --- Command-line Argument Parsing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Splits global active fault data by country with optional geometry simplification.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows default values in help
    )
    
    # Add an argument for simplification tolerance
    # type=float ensures the input is treated as a floating-point number
    # default=0.0 means no simplification by default
    parser.add_argument(
        '--simplify-tolerance',
        type=float,
        default=0.0,
        help="Tolerance for geometry simplification (in CRS units, typically degrees for WGS84). "
             "Set to 0.0 (default) for no simplification. "
             "Larger values lead to more simplification and smaller file sizes (e.g., 0.001 to 0.01)."
    )

    args = parser.parse_args()

    # Call the main function with the parsed argument
    split_faults_by_country(
        FAULTS_GEOJSON_PATH,
        COUNTRIES_FILE_PATH,
        BASE_OUTPUT_FOLDER,
        COUNTRY_NAME_COLUMN,
        simplify_tolerance=args.simplify_tolerance
    )