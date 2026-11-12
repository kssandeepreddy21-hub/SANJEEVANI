import geopandas as gpd
from pathlib import Path


def extract_bengaluru_roads():

    print("Reading Bengaluru geographical data...")

    file_path = Path(
        "data/planet_77.46_12.907_d3d9fd17-geopackage/"
        "planet_77.46_12.907_d3d9fd17.gpkg"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"GeoPackage not found: {file_path}"
        )

    print("Loading road features...")

    roads = gpd.read_file(
        file_path,
        layer="lines"
    )

    print("Total geographical features:", len(roads))

    # Keep only road classifications suitable
    # for ordinary motor vehicle routing.
    drivable_types = [
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "residential",
        "living_street",
        "unclassified",
        "road",
        "service"
    ]

    roads = roads[
        roads["highway"].isin(drivable_types)
    ].copy()

    roads = roads[
        roads.geometry.notna()
        & ~roads.geometry.is_empty
    ].copy()

    print("\nRoad extraction completed!")

    print("Drivable road features:", len(roads))

    print("\nRoad classification summary:")
    print(roads["highway"].value_counts())

    # Save extracted road features.
    output_folder = Path("data/processed")
    output_folder.mkdir(parents=True, exist_ok=True)

    output_path = output_folder / "bengaluru_roads.gpkg"

    roads.to_file(
        output_path,
        layer="roads",
        driver="GPKG"
    )

    print("\nExtracted roads saved at:")
    print(output_path)

    return roads


if __name__ == "__main__":
    extract_bengaluru_roads()
