import sys
from openpyxl import load_workbook


def read_values(path):
    workbook = load_workbook(path, data_only=True)
    sheet = workbook["Sheet1"]
    return [sheet["A13"].value, sheet["A14"].value]


if len(sys.argv) != 3:
    raise SystemExit("usage: check_answer_range.py OUTPUT.xlsx GOLDEN.xlsx")

output_values = read_values(sys.argv[1])
golden_values = read_values(sys.argv[2])

print({"output": output_values, "golden": golden_values, "match": output_values == golden_values})
raise SystemExit(0 if output_values == golden_values else 1)
