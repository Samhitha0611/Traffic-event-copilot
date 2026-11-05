import pandas as pd
from load_data import load_data


def process_diversions():

    # Step 1: Load Excel workbook
    data = load_data()

    # Step 2: Get diversion sheet
    diversions = data["Diversions"].copy()

    # Step 3: Clean column values
    text_columns = [
        "Event_Name",
        "Movement",
        "Vehicle_Class",
        "Diversion_Point",
        "Diverted_Route",
        "Source_URL"
    ]

    for column in text_columns:
        diversions[column] = (
            diversions[column].fillna("").astype(str).str.strip()
        )

    # Step 4: Convert date column
    diversions["Date"] = pd.to_datetime(
        diversions["Date"], errors="coerce"
    )

    # Step 5: Remove records missing essential information
    diversions = diversions.dropna(
        subset=["Date"]
    )

    diversions = diversions[
        (diversions["Movement"] != "") &
        (diversions["Diversion_Point"] != "") &
        (diversions["Diverted_Route"] != "")
    ]

    # Step 6: Display summary
    print("\n========== DIVERSION PROCESSING ==========")

    print("\nTotal Diversion Records:", len(diversions))

    print("\nVehicle Categories:")
    print(diversions["Vehicle_Class"].value_counts())

    print("\nUnique Traffic Movements:",
          diversions["Movement"].nunique())

    # Step 7: Display processed records
    print("\n========== PROCESSED DIVERSION DETAILS ==========")

    for index, row in diversions.iterrows():

        print(f"\nRecord {index + 1}")

        print("Date:", row["Date"].date())
        print("Event:", row["Event_Name"])
        print("Movement:", row["Movement"])
        print("Vehicle Class:", row["Vehicle_Class"])
        print("Diversion Point:", row["Diversion_Point"])
        print("Alternative Route:", row["Diverted_Route"])
        print("Restriction Start:", row["Window_Start"])
        print("Restriction End:", row["Window_End"])

    return diversions

# Main execution block
if __name__ == "__main__":

    processed_data = process_diversions()

    print("\n========================================")
    print("DIVERSION PROCESSING COMPLETED!")
    print("========================================")
