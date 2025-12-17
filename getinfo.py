from pathlib import Path
import re
import csv
import requests
import json
# This code cant run by itself it:
# - execute run.sh to make this code work properly
# Accepts a txt file
# -> convert it to a csv containing:
#   - all the cellular towers which the phone is connected right now
#


def extract_cell_towers(text):
    """Extract cellular tower information using keyword patterns"""
    towers = []

    # Pattern to match CellIdentity blocks (LTE, GSM, WCDMA, NR, etc.)
    cell_identity_pattern = r"CellIdentity\w+:\s*\{([^}]+)\}"

    matches = re.finditer(cell_identity_pattern, text)

    for match in matches:
        cell_block = match.group(1)
        tower = {}

        # Extract common cellular identifiers using keywords
        # Cell ID (mCi, CID, cellId, etc.)
        ci_match = re.search(r"m?[Cc](?:ell)?[Ii]d?=(\d+)", cell_block)
        if ci_match and ci_match.group(1) != "2147483647":  # Ignore invalid values
            tower["CellID"] = ci_match.group(1)

        # Tracking Area Code / Location Area Code (mTac, TAC, LAC)
        tac_match = re.search(r"m?(?:Tac|Lac)=(\d+)", cell_block)
        if tac_match and tac_match.group(1) != "2147483647":
            tower["TAC_LAC"] = tac_match.group(1)

        # Mobile Country Code (mMcc, MCC)
        mcc_match = re.search(r"m?Mcc=(\d+)", cell_block)
        if mcc_match:
            tower["MCC"] = mcc_match.group(1)

        # Mobile Network Code (mMnc, MNC)
        mnc_match = re.search(r"m?Mnc=(\d+)", cell_block)
        if mnc_match:
            tower["MNC"] = mnc_match.group(1)

        # Physical Cell ID (mPci, PCI, PSC)
        pci_match = re.search(r"m?(?:Pci|Psc)=(\d+)", cell_block)
        if pci_match and pci_match.group(1) != "2147483647":
            tower["PCI_PSC"] = pci_match.group(1)

        # Frequency (mEarfcn, ARFCN, UARFCN)
        earfcn_match = re.search(r"m?(?:Earfcn|Arfcn|Uarfcn)=(\d+)", cell_block)
        if earfcn_match and earfcn_match.group(1) != "2147483647":
            tower["EARFCN"] = earfcn_match.group(1)

        # Only add if we have at least Cell ID or (MCC and MNC)
        if "CellID" in tower or ("MCC" in tower and "MNC" in tower):
            # Avoid duplicates
            if tower not in towers:
                towers.append(tower)

    return towers


information = Path.cwd() / "data" / "output.txt"
output_csv = Path.cwd() / "data" / "cell_towers.csv"
api_key_file = Path.cwd() / "data" / "api_key.txt"
url = "https://us1.unwiredlabs.com/v2/process"

if information.exists():
    all_text = information.read_text(encoding="utf-8")

    towers = extract_cell_towers(all_text)

    if towers:
        # Write to CSV
        fieldnames = ["CellID", "TAC_LAC", "MCC", "MNC", "PCI_PSC", "EARFCN"]

        with output_csv.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(towers)

        print(f"Extracted {len(towers)} unique cellular towers to {output_csv}")
        for i, tower in enumerate(towers, 1):
            print(f"{i}. {tower}")
        
        # Read API key
        api_key = api_key_file.read_text(encoding="utf-8").strip()
        
        # Send request to server
        if towers:
            # Prepare request payload based on template.json structure
            # Group towers by MCC/MNC to send separate requests if needed
            # For simplicity, using first tower's MCC/MNC and sending all towers
            first_tower = towers[0]
            
            payload = {
                "token": api_key,
                "radio": "gsm",  # Default to gsm, could be determined from cell type
                "mcc": int(first_tower.get("MCC", 0)),
                "mnc": int(first_tower.get("MNC", 0)),
                "cells": [],
                "address": 1
            }
            
            # Add all towers to cells array
            for tower in towers:
                cell_data = {}
                if "TAC_LAC" in tower:
                    cell_data["lac"] = int(tower["TAC_LAC"])
                if "CellID" in tower:
                    cell_data["cid"] = int(tower["CellID"])
                
                # Only add cell if it has required fields
                if cell_data:
                    payload["cells"].append(cell_data)
            
            # Send request
            try:
                print(f"\nSending request to {url}...")
                response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                response.raise_for_status()
                
                result = response.json()
                print(f"\nResponse received:")
                print(f"Status: {result.get('status')}")
                print(f"Balance: {result.get('balance')}")
                print(f"Latitude: {result.get('lat')}")
                print(f"Longitude: {result.get('lon')}")
                print(f"Accuracy: {result.get('accuracy')} meters")
                print(f"Address: {result.get('address')}")
                
            except requests.exceptions.RequestException as e:
                print(f"\nError sending request: {e}")
            except json.JSONDecodeError as e:
                print(f"\nError parsing response: {e}")
    else:
        print("No cellular tower information found in the output file")

else:
    print("file path not found, you might run this outside the script")
