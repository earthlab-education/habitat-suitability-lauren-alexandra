import os
from glob import glob
from math import floor, ceil
import rioxarray as rxr
from rioxarray.merge import merge_arrays
import xrspatial
import matplotlib.pyplot as plt
import earthaccess

def build_da(urls, bounds):
    """
    Build a DataArray from a list of urls.
    
    Args:
    urls (list): Input list of URLs.
    bounds (tuple): Site boundaries.

    Returns:
    xarray.DataArray: A merged DataArray.
    """
    
    all_das = []

    # Add buffer to bounds for plotting
    buffer = .025
    xmin, ymin, xmax, ymax = bounds
    bounds_buffer = (xmin-buffer, ymin-buffer, xmax+buffer, ymax+buffer)

    for url in urls:
        # Open data granule, mask missing data, scale data, 
        # and remove dimensions of length 1
        tile_da = rxr.open_rasterio(
                url,
                # For the fill/missing value
                mask_and_scale=True
            ).squeeze()
        # Unpack the bounds and crop tile
        cropped_da = tile_da.rio.clip_box(*bounds_buffer)
        all_das.append(cropped_da)

    merged = merge_arrays(all_das)
    return merged

def convert_longitude(longitude):
    """
    Convert longitude values from a range of 0 to 360 to -180 to 180.
    
    Args:
    longitude (float): Input longitude value.

    Returns:
    float: A value in the specified range.
    """
    
    return (longitude - 360) if longitude > 180 else longitude

def convert_temperature(temp):
    """
    Convert temperature from Kelvin to Fahrenheit.
    
    Args:
    temp (float): Input temperature value.

    Returns:
    float: A value in the Fahrenheit temperature scale.
    """

    return temp  * 1.8 - 459.67

def export_raster(da, raster_path, data_dir):
    """
    Export raster DataArray to a raster file.
    
    Args:
    raster (xarray.DataArray): Input raster layer.
    raster_path (str): Output raster directory.
    data_dir (str): Path of data directory.

    Returns: None
    """
    
    output_file = os.path.join(data_dir, os.path.basename(raster_path))
    da.rio.to_raster(output_file)

def harmonize_raster_layers(reference_raster, input_rasters, output_dir):
    """
    Harmonize raster layers to ensure consistent spatial resolution 
    and projection.

    Args:
    reference_raster (xarray.DataArray): Input reference raster.
    input_rasters (list): List of site rasters.
    output_dir (str): Path of raster directory.

    Returns:
    list: A list of harmonized rasters.
    """
    harmonized_files = []

    harmonized_files.append(reference_raster)
    # Load the reference raster
    ref_raster = rxr.open_rasterio(reference_raster, masked=True)

    for raster_path in input_rasters:
        # Load the input raster
        input_raster = rxr.open_rasterio(raster_path, masked=True)

        # Reproject and align the input raster to match the reference raster
        harmonized_raster = input_raster.rio.reproject_match(ref_raster)

        # Save the harmonized raster to the output directory
        output_file = os.path.join(output_dir, os.path.basename(raster_path))
        harmonized_raster.rio.to_raster(output_file)
        harmonized_files.append(output_file)

    print('Harmonized rasters: ', len(harmonized_files))
    return harmonized_files

def plot_site(site_da, site_gdf, plots_dir, site_fig_name, plot_title, 
              bar_label, plot_cmap, boundary_clr, tif_file=False):
    """
    Create custom site plot.
    
    Args:
    site_da (xarray.DataArray): Input site raster.
    site_gdf (geopandas.GeoDataFrame): Input site GeoDataFrame.
    plots_dir (str): Path of plots directory.
    site_fig_name (str): Site figure name.
    plot_title (str): Plot title. 
    bar_label (str): Plot bar variable name.
    plot_cmap (str): Plot colormap name.
    boundary_clr (str): Plot site boundary color.
    tif_file (boolean): Indicates a site file.

    Returns:
    matplotlib.pyplot.plot: A plot of site values.
    """
    
    fig = plt.figure(figsize=(8, 6)) 
    ax = plt.axes()

    if tif_file:
        site_da = rxr.open_rasterio(site_da, masked=True)

    # Plot DataArray values
    site_plot = site_da.plot(
                            cmap=plot_cmap, 
                            cbar_kwargs={'label': bar_label}
                        )

    # Plot site boundary
    site_gdf.boundary.plot(ax=plt.gca(), color=boundary_clr)

    plt.title(f'{plot_title}')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    fig.savefig(f"{plots_dir}/{site_fig_name}.png") 

    return site_plot

def create_polaris_urls(soil_prop, stat, soil_depth, gdf_bounds):
    """
    Create POLARIS dataset URLs using site bounds.

    Args:
    soil_prop (str): Soil property.
    stat (str): Summary statistic. 
    soil_depth (str): Soil depth (cm).
    gdf_bounds (numpy.ndarray): Array of site boundaries.

    Returns:
    list: A list of POLARIS datset URLs. 
    """

    # Get latitude and longitude bounds from site
    min_lon, min_lat, max_lon, max_lat = gdf_bounds

    site_min_lon = floor(min_lon) 
    site_min_lat = floor(min_lat)  
    site_max_lon = ceil(max_lon)  
    site_max_lat = ceil(max_lat)

    all_soil_urls = []

    for lon in range(site_min_lon, site_max_lon): 
        for lat in range(site_min_lat, site_max_lat):
            current_max_lon = lon + 1
            current_max_lat = lat + 1

            soil_template = (
                "http://hydrology.cee.duke.edu/POLARIS/PROPERTIES/v1.0/"
                "{soil_prop}/"
                "{stat}/"
                "{soil_depth}/"
                "lat{min_lat}{max_lat}_lon{min_lon}{max_lon}.tif"
            )

            soil_url = soil_template.format(
                soil_prop=soil_prop, stat=stat, soil_depth=soil_depth,
                min_lat=lat, max_lat=current_max_lat, 
                min_lon=lon, max_lon=current_max_lon
            )

            all_soil_urls.append(soil_url)

    return all_soil_urls

def download_polaris(site_name, site_gdf, soil_prop, stat, soil_depth, 
                     plot_path, plot_title, data_dir, plots_dir):
    """
    Retrieve POLARIS site data, build DataArray, plot site, and export raster.

    Args:
    site_name (str): Name of site.
    site_gdf (geopandas.GeoDataFrame): Site GeoDataFrame.
    soil_prop (str): Soil property.
    stat (str): Summary statistic. 
    soil_depth (str): Soil depth (cm).
    plot_path (str): Path of topographic plot.
    plot_title (str): Title of topographic plot.
    data_dir (str): Path of data directory.
    plots_dir (str): Path of plots directory.

    Returns:
    xarray.DataArray: A soil DataArray for a given location. 
    """
    
    # Collect site urls
    site_polaris_urls = create_polaris_urls(
                        soil_prop, stat, soil_depth, 
                        site_gdf.total_bounds
                    )
    
    # Gather site data into a single DataArray
    site_soil_da = build_da(site_polaris_urls, tuple(site_gdf.total_bounds))
    
    # Export soil data to raster
    export_raster(site_soil_da, f"{site_name}_soil_{soil_prop}.tif", data_dir)

    # Create site plot
    plot_site(
        site_soil_da, site_gdf, plots_dir,
        f'{plot_path}-Soil', f'{plot_title} Soil',
        'pH', 'viridis', 'lightblue'
    )

    return site_soil_da

def select_dem(bounds, site_gdf, download_dir):
    """
    Create elevation DataArray from NASA Shuttle Radar Topography Mission data.

    Args:
    bounds (tuple): Input site boundaries.
    site_gdf (geopandas.GeoDataFrame): Land unit GeoDataFrame.
    download_dir (str): Path of download directory.

    Returns:
    xarray.DataArray: A site elevation raster.
    """

    # Returns data granules for given bounds
    strm_granules = earthaccess.search_data(
        # SRTMGL1: NASA Shuttle Radar Topography Mission 
        # Global 1 arc second V003
        short_name="SRTMGL1",
        bounding_box=bounds
    )

    # Download data granules
    earthaccess.download(strm_granules, download_dir)

    # Set SRTM data dir. hgt = height 
    strm_pattern = os.path.join(download_dir, '*.hgt.zip')

    # Build merged elevation DataArray
    strm_da = build_da(glob(strm_pattern), tuple(site_gdf.total_bounds))

    return strm_da

def calculate_aspect(elev_da):
    """
    Create aspect DataArray from site elevation.
    
    Args:
    elev_da (xarray.DataArray): Input raster layer.

    Returns:
    xarray.DataArray: A raster of site aspect. 
    """

    # Calculate aspect (degrees)
    aspect_da = xrspatial.aspect(elev_da)
    aspect_da = aspect_da.where(aspect_da >= 0)

    return aspect_da

def download_topography(site_name, site_gdf, plot_path, plot_title, 
                        elevation_dir, data_dir, plots_dir):
    """
    Retrieve topographic data, build DataArray, plot site, and export raster.

    Args:
    site_name (str): Name of site.
    site_gdf (geopandas.GeoDataFrame): Site GeoDataFrame.
    plot_path (str): Path of topographic plot.
    plot_title (str): Title of topographic plot.
    elevation_dir (str): Path of site elevation directory.
    data_dir (str): Path of data directory.
    plots_dir (str): Path of plots directory.

    Returns:
    xarray.DataArray: An elevation DataArray for a given location. 
    """
    
    # Produce Digital Elevation Model DataArray

    elev_da = select_dem(tuple(site_gdf.total_bounds), site_gdf, 
                        elevation_dir)
    export_raster(elev_da, f"{site_name}_elevation.tif", data_dir)
    plot_site(
        elev_da, site_gdf, plots_dir, f'{plot_path}-Elevation', 
        f'{plot_title} Elevation', 'Meters', 'terrain', 'black',
    )

    # Calculate aspect from elevation 

    aspect_da = calculate_aspect(elev_da)
    export_raster(aspect_da, f"{site_name}_aspect.tif", data_dir)
    plot_site(
        aspect_da, site_gdf, plots_dir, f'{plot_path}-Aspect', 
        f'{plot_title} Aspect', 'Degrees', 'terrain', 'black'
    )

    return elev_da

