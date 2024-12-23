import os
import json
import sys
import pandas as pd
from neo4j import GraphDatabase


class Constants:
    """
    A class to hold constant values such as Neo4j connection details and folder paths.
    Constants can be loaded from a JSON file for easy configuration management.
    """
    NEO4J_URI = None
    NEO4J_USERNAME = None
    NEO4J_PASSWORD = None
    FOLDER_PATH = None

    @classmethod
    def load_from_json(cls, json_file_path):
        """Load constants from a JSON file."""
        with open(json_file_path, "r") as file:
            data = json.load(file)
        
        # Load Neo4j constants
        neo4j_constants = data["NEO4J_CONSTANTS"][0]
        cls.NEO4J_URI = neo4j_constants["NEO4J_URI"]
        cls.NEO4J_USERNAME = neo4j_constants["NEO4J_USERNAME"]
        cls.NEO4J_PASSWORD = neo4j_constants["NEO4J_PASSWORD"]
        
        # Load folder path
        cls.FOLDER_PATH = data["FOLDER_PATH"]

class DataProcessor:
    """
    A class to handle data loading and preprocessing from a folder of files.
    Supports reading data from CSV and Excel files and organizing them into dictionaries.
    """
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.data_dict = {}
        self.sector_dict = {}

    def load_data(self):
        """
        Load data from CSV or Excel files in the specified folder path into a dictionary.
        """
        for item in os.listdir(self.folder_path):
            item_path = os.path.join(self.folder_path, item)
            if os.path.isfile(item_path):
                file_extension = item.split('.')[-1]
                if file_extension == 'csv':
                    print(f"Loading CSV: {item}")
                    self.data_dict[item.split('.')[0]] = pd.read_csv(item_path)
                elif file_extension in ['xls', 'xlsx']:
                    print(f"Loading Excel: {item}")
                    excel_sheets = pd.read_excel(item_path, sheet_name=None, engine="openpyxl")
                    for sheet_name, df in excel_sheets.items():
                        print(f"Loading Sheet: {sheet_name}")
                        self.data_dict[sheet_name] = df
            else:
                print(f"Skipping non-file item: {item}")

    def generate_sector_dict(self):
        """
        Generate a sector dictionary mapping keys from data_dict based on naming conventions.
        """
        for key in self.data_dict.keys():
            parts = key.split('_')
            self.sector_dict[parts[0]] = parts[1] if len(parts) > 1 else None

    def display_summary(self):
        """
        Print summaries of loaded data and sector mappings.
        """
        print("\nData Dictionary Keys:")
        for key in self.data_dict.keys():
            print(f"- {key}")
        print("\nSector Dictionary:")
        for sector, sub_sector in self.sector_dict.items():
            print(f"{sector}: {sub_sector}")

class Neo4jLoader:
    """
    A class to manage Neo4j database interactions, including loading data into the graph database.
    """
    def __init__(self, uri, user, password):
        """
        Initialize the Neo4jLoader with connection details.

        Args:
            uri (str): URI of the Neo4j database.
            user (str): Username for the Neo4j database.
            password (str): Password for the Neo4j database.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """
        Close the connection to the Neo4j database.
        """
        self.driver.close()

    def load_dataframe(self, df, sub_sector_name, sector_name):
        """
        Load a DataFrame into the Neo4j graph database, creating nodes and relationships.

        Args:
            df (pd.DataFrame): The DataFrame to load into the database.
            sub_sector_name (str): Name of the subsector.
            sector_name (str): Name of the sector.
        """
        
        # Safeguard dynamic parameters by escaping or validating
        sub_sector_name = str(sub_sector_name).replace("'", "\\'")
        sector_name = str(sector_name).replace("'", "\\'")

        query = f"""
        UNWIND $rows AS row
        MERGE (state:State {{name: row.State}})
        MERGE (region:EDD {{name: row.Region}})
        MERGE (state)-[:HAS_EDD]->(region)
        MERGE (county:County {{name: row.County, fips_id: row.county_id}})
        MERGE (region)-[:HAS_COUNTY]->(county)
        MERGE (sector:Sector {{name: '{sector_name}'}})
        MERGE (county)-[:HAS_SECTOR]->(sector)
        // Check if subsector_name is provided and create subsector
        WITH row, sector
        {f"MERGE (subsector:Sub_Sector {{name: '{sub_sector_name}'}}) MERGE (sector)-[:HAS_SUB_SECTOR]->(subsector)" if sub_sector_name else ""}
        WITH row, sector, {f"subsector" if sub_sector_name else "NULL"} AS subsector
        UNWIND keys(row) AS columnName
        WITH row, subsector, columnName
        WHERE NOT columnName IN ['State', 'Region', 'County', 'Year']  // Exclude non-metric columns
        MERGE (metric:Metrics {{metric_name: columnName, year: toInteger(row.Year), county:row.County}})
        ON CREATE SET metric.value = toFloat(row[columnName])  // Set metric value if created
        MERGE (subsector)-[:REPORTS]->(metric);
        """
        
        rows = df.to_dict('records')
        with self.driver.session() as session:
            session.run(query, rows=rows)


if __name__ == "__main__":
    
    # Check for sys arguments
    if len(sys.argv) < 2:
        print("Usage: python data_ingestion.py <path_to_config.json>")
        sys.exit(1)
    
    # Load JSON file
    json_file_path = sys.argv[1]
    Constants.load_from_json(json_file_path)
    
    # Load Data
    folder_path = Constants.FOLDER_PATH
    processor = DataProcessor(folder_path)
    processor.load_data()
    processor.generate_sector_dict()
    processor.display_summary()

    # Connect to Neo4j and Load Data
    uri = Constants.NEO4J_URI
    user = Constants.NEO4J_USERNAME
    password = Constants.NEO4J_PASSWORD

    # Initialize loader
    loader = Neo4jLoader(uri, user, password)

    try:
        # Ingest the DataFrame
        print("Ingesting DataFrame...")
        for i in processor.sector_dict.keys():
            if processor.sector_dict[i]:
                print(f"Creating nodes for {i} subsector")
                loader.load_dataframe(processor.data_dict[i+'_'+processor.sector_dict[i]], sub_sector_name=i, sector_name=processor.sector_dict[i])
            else:
                print(f"Creating nodes for {i} sector")
                loader.load_dataframe(processor.data_dict[i], sub_sector_name=None, sector_name=i)
        print("DataFrame ingested successfully!")

    finally:
        loader.close()