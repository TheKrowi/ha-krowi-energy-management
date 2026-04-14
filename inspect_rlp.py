import urllib.request, io, pyxlsb
from datetime import date, timedelta
from collections import defaultdict

url = "https://www.synergrid.be/images/downloads/SLP-RLP-SPP/2026/RLP0N%202026%20Electricity%20all%20DSOs.xlsb"
data = urllib.request.urlopen(url).read()

with pyxlsb.open_workbook(io.BytesIO(data)) as wb:
    with wb.get_sheet("RLP96UbyDGO") as sheet:
        rows = list(sheet.rows())

# Row 0: RLP labels (internal model names) starting at col 7
# Row 1: DGO names starting at col 7
# Row 2: EAN codes starting at col 7
# Row 3+: data

dgo_row = rows[1]
all_cols = [c.v if c else None for c in dgo_row]
print("All DGO columns:")
for i, v in enumerate(all_cols):
    if v:
        print(f"  col {i}: {v!r}")

print()
# Check if values are all identical (i.e. single model used for all)
print("Comparing Jan 1 QH1 weights across all DSO columns:")
row3 = rows[3]
vals = [c.v if c else None for c in row3]
for i, v in enumerate(vals[7:], start=7):
    if v is not None:
        print(f"  col {i}: {v}")
