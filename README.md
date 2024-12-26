# Graph Data Generator and Loader

We have developed a graph database system to automate the creation of summary backgrounds for Comprehensive Economic Development Strategy (CEDS) documents. This system includes a utility for generating and loading graph data into a Neo4j database by extracting information from various sources, including API calls, CSV, and Excel files. The data is preprocessed and structured into nodes and relationships within the Neo4j graph, which can then be integrated into a Retrieval-Augmented Generation (RAG) architecture. This integration enables automated querying and the generation of key economic indicators, significantly streamlining the process of creating and updating CEDS, making them more accessible and actionable for Economic Development Districts (EDDs).

## Prerequisites

- Python 3.8 or above
- Neo4j database instance
- Required Python libraries (install via `pip install -r requirements.txt`):
  - `pandas`
  - `neo4j`
  - `openpyxl`

## How to Run the Code

1. Clone this repository and navigate to the project directory.

2. Set up your `config.json` file with the following structure:

```json
{
  "NEO4J_CONSTANTS": [
    {
      "NEO4J_URI": "neo4j+ssc://your_instance.databases.neo4j.io",
      "NEO4J_USERNAME": "your_username",
      "NEO4J_PASSWORD": "your_password"
    }
  ],
  "FOLDER_PATH": "input_data_folder_path"
}
```
   - Replace `your_instance.databases.neo4j.io`, `your_username`, and `your_password` with your Neo4j instance details.
   - Replace `input_data_folder_path` with the path to the folder containing your input data files (CSV or Excel).

3. Run the script using the following command:

   ```bash
   python graph_generator.py <config_file_path>
   

   Replace `<config_file_path>` with the path to your `config.json` file.

## Input Data Format

- The input folder should contain `.csv` or `.xlsx` files.
- Each file's name should follow the convention `<sector>_<sub_sector>.csv` or similar, where `sector` and `sub_sector` represent the graph hierarchy.
- The files should include columns like `State`, `Region`, `County`, `Year`, and metric columns.

## Output

The script creates a graph in Neo4j with the following structure:
- Nodes: `State`, `EDD` (Economic Development District), `County`, `Sector`, `Sub_Sector`, and `Metrics`.
- Relationships:
  - `State` -> `HAS_EDD` -> `EDD`
  - `EDD` -> `HAS_COUNTY` -> `County`
  - `County` -> `HAS_SECTOR` -> `Sector`
  - `Sector` -> `HAS_SUB_SECTOR` -> `Sub_Sector` (if applicable)
  - `Sub_Sector` -> `REPORTS` -> `Metrics`
