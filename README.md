# Global Fault Splitter

This project, Global Fault Splitter, provides a Python-based solution for processing global active fault data. It takes a comprehensive harmonized fault dataset and organizes it into individual GeoJSON files, one for each country. This tool is incredibly useful for regional geological analysis, integrating data into mobile applications, or any application requiring country-specific fault information.

## Project Structure

The project has a clear and logical folder structure to keep everything organized:

```txt
    .
    ├── environment.yml                     # Conda environment definition for easy setup
    ├── geojsons
    │   └── gem_active_faults_harmonized.geojson # Input: Global Active Faults data
    ├── main.py                             # Main Python script for processing
    ├── output                              # Output directory for processed data
    │   └── faults_by_country               # Subfolder where country-specific GeoJSON files are saved
    │       ├── faults_afghanistan.geojson
    │       └── ... (and many more country-specific fault files)
    ├── requirements.txt                    # Python package requirements (for pip, alternative to environment.yml)
    └── shapefiles
        └── ne_10m_admin_0_countries.shp    # Input: Country boundaries Shapefile (and its components)
        │   ├── ne_10m_admin_0_countries.cpg
        │   ├── ne_10m_admin_0_countries.dbf
        │   ├── ne_10m_admin_0_countries.prj
        │   ├── ne_10m_admin_0_countries.README.html
        │   ├── ne_10m_admin_0_countries.shx
        │   └── ne_10m_admin_0_countries.VERSION.txt
```

## Getting Started

Follow these steps to set up and run the project:

**1. Data Preparation**

Before running the script, you'll need two input datasets:

- **Global Active Faults Data:**

  Download the GEM Global Active Faults Database (GEM GAF-DB). Locate and download the `gem_active_faults_harmonized.geojson` file.

  - Place this file into the `./geojsons/ directory`.

- **Country Boundaries Data:**

  Download the **Admin 0 – Countries** dataset (Shapefile format) from [Natural Earth (1:10m Cultural Vectors)](https://www.naturalearthdata.com/downloads/). Choose the "Download countries" option.

Extract the entire contents of the downloaded `.zip` file (which includes `.shp`, `.shx`, `.dbf`, `.prj`, etc.) into the `./shapefiles/` directory. It's crucial that all these component files are present and not corrupted, especially the `.shx` file.

**2. Set Up Your Conda Environment**

Using Conda is highly recommended for managing the project's dependencies, as it handles complex geospatial libraries effectively.

- **Create the Conda Environment:**

Open your terminal or Anaconda Prompt. Navigate to the project's root directory (where `environment.yml` is located) and run:

```bash
  conda env create -f environment.yml
```

This command creates a new Conda environment named `global_fault_splitter` and installs all necessary packages.

- **Activate the Environment:**

Before running any Python script related to this project, you must activate its Conda environment:

```bash
  conda activate global_fault_splitter
```

You'll see (`global_fault_splitter`) appear in your terminal prompt, indicating the environment is active.

**3. Configure `main.py` (Optional Review)**
   
Open the `main.py` file with a text editor or IDE.

`COUNTRY_NAME_COLUMN:`

The script uses `'NAME_EN'` by default to identify country names from the Natural Earth data. This is typically correct. However, if your country boundaries Shapefile uses a different column name for country names (e.g., `'NAME_LONG'` or `'SOVEREIGNT'`), you'll need to update the `COUNTRY_NAME_COLUMN` variable in `main.py` accordingly. You can verify the correct column names by inspecting the Shapefile's attribute table in a GIS software like QGIS.

`.shx` **File Restoration:**

The script includes a line `gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES')` to help if your `.shx` file (a crucial Shapefile component) is missing or corrupted. This line is active by default. If you know your `.shx` file is perfectly fine and wish to disable this restoration attempt, you can comment it out.

**4. Run the Script**

Once your Conda environment is active and data files are in their correct places, execute the main script:

```bash
  python main.py
```

A **progress bar** will appear in your terminal, showing the processing status as the script works through each country.

Upon successful completion, the processed GeoJSON files will be saved into the `./output/faults_by_country/` directory.

## Output Files

The script generates individual GeoJSON files for each country that contains active fault data. These files are stored in the `./output/faults_by_country/` directory.

- **Naming Convention:** File names are standardized to be entirely lowercase for consistency (e.g., `faults_thailand.geojson`, `faults_united_states.geojson`).

- **Content:** Each GeoJSON file contains the active fault geometries and their associated attributes that intersect or fall within the respective country's boundaries.

## Licensing

- **GEM Global Active Faults Database (GEM GAF-DB):** This dataset is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License](https://creativecommons.org/licenses/by-sa/4.0/). If you use data derived from GEM GAF-DB, please ensure you adhere to its attribution requirements.

- **Natural Earth Country Boundaries Data:** This dataset is in the [public domain](https://www.naturalearthdata.com/about/terms-of-use/).
