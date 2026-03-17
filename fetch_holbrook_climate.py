#!/usr/bin/env python3
"""
Fetch daily climate data for Holbrook, AZ from NOAA/ACIS API.
Source: https://www.weather.gov/wrh/Climate?wfo=fgz

Primary Station: HOLBROOK (USC00024089) - COOP station, ceased ~2010
Backup Station:  WINSLOW AIRPORT (USW00023194/KINW) - ~30 mi west, continuous data

Period: 2001-01-01 to 2026-03-17
"""

import csv
import json
import urllib.request
import sys

API_URL = "https://data.rcc-acis.org/StnData"
START_DATE = "2001-01-01"
END_DATE = "2026-03-17"
OUTPUT_FILE = "Holbrook_AZ_Daily_Climate_2001_2026.csv"

STATIONS = [
    {"sid": "024089", "label": "Holbrook COOP (USC00024089)"},
    {"sid": "USW00023194", "label": "Winslow Airport (KINW)"},
]


def fetch_station(sid):
    payload = json.dumps({
        "sid": sid,
        "sdate": START_DATE,
        "edate": END_DATE,
        "elems": [
            {"name": "maxt"},
            {"name": "mint"},
            {"name": "avgt"},
            {"name": "pcpn"},
        ],
        "meta": "name,state,sids,ll",
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def row_has_data(row):
    """Check if at least max and min temp are non-missing."""
    _, maxt, mint, avgt, pcpn = row
    return maxt != "M" and mint != "M"


def main():
    # Fetch both stations
    datasets = {}
    for stn in STATIONS:
        print(f"Fetching {stn['label']}...")
        result = fetch_station(stn["sid"])
        meta = result["meta"]
        print(f"  Station: {meta['name']}, {meta['state']} | Coords: {meta['ll']}")
        data_by_date = {}
        for row in result["data"]:
            data_by_date[row[0]] = row
        datasets[stn["sid"]] = {"meta": meta, "data": data_by_date, "label": stn["label"]}
        print(f"  Days retrieved: {len(result['data'])}")

    # Merge: prefer Holbrook, fallback to Winslow
    primary = datasets["024089"]
    backup = datasets["USW00023194"]

    all_dates = sorted(set(list(primary["data"].keys()) + list(backup["data"].keys())))

    stats = {"primary": 0, "backup": 0, "missing": 0}

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date",
            "Max Temperature (F)",
            "Min Temperature (F)",
            "Avg Temperature (F)",
            "Precipitation (in)",
            "Station Source",
        ])

        for date in all_dates:
            p_row = primary["data"].get(date)
            b_row = backup["data"].get(date)

            if p_row and row_has_data(p_row):
                writer.writerow(p_row + [primary["label"]])
                stats["primary"] += 1
            elif b_row and row_has_data(b_row):
                writer.writerow(b_row + [backup["label"]])
                stats["backup"] += 1
            elif p_row:
                writer.writerow(p_row + [primary["label"] + " (partial)"])
                stats["missing"] += 1
            elif b_row:
                writer.writerow(b_row + [backup["label"] + " (partial)"])
                stats["missing"] += 1
            else:
                writer.writerow([date, "M", "M", "M", "M", "No data"])
                stats["missing"] += 1

    total = stats["primary"] + stats["backup"] + stats["missing"]
    print(f"\n--- Summary ---")
    print(f"Total days: {total}")
    print(f"Holbrook COOP data: {stats['primary']} days ({stats['primary']/total*100:.1f}%)")
    print(f"Winslow Airport fill: {stats['backup']} days ({stats['backup']/total*100:.1f}%)")
    print(f"Still missing/partial: {stats['missing']} days ({stats['missing']/total*100:.1f}%)")
    print(f"\nSpreadsheet saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
