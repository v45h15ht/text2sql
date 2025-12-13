import os
from neo4j import GraphDatabase

# --- CONFIGURATION ---
# Ensure these match your Docker settings
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

def test_connection():
    print(f"Connecting to Neo4j at {URI}...")
    
    try:
        # 1. Initialize Driver
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            
            # 2. Verify Connectivity
            driver.verify_connectivity()
            print("Connection established successfully!")

            # 3. Run a Simple Query (Count Nodes)
            print("Checking database content...")
            
            # Get total node count
            count_query = "MATCH (n) RETURN count(n) AS total"
            records, summary, keys = driver.execute_query(count_query)
            total_nodes = records[0]["total"]
            print(f"   -> Total Nodes found: {total_nodes}")

            # Get breakdown of Labels (what tables you have)
            if total_nodes > 0:
                print("\nTable/Label Breakdown:")
                label_query = """
                MATCH (n) 
                RETURN distinct labels(n)[0] AS TableName, count(n) AS Rows 
                ORDER BY Rows DESC 
                LIMIT 10
                """
                records, _, _ = driver.execute_query(label_query)
                for record in records:
                    print(f"   - {record['TableName']}: {record['Rows']} rows")
            else:
                print("\nDatabase is empty! Did you run setup_graph.py?")

    except Exception as e:
        print("\nCONNECTION FAILED")
        print(f"Error details: {e}")
        print("-" * 30)
        print("Troubleshooting Tips:")
        print("1. Is Docker running? (Run 'docker ps')")
        print("2. Did you change the password? (Default in docker-compose was 'password123')")
        print("3. Is the port 7687 correct?")

if __name__ == "__main__":
    test_connection()