# 33157 C3 formula calculation wrong after import

This package reproduces a wrong calculated value for `Sheet1!C3` after importing
`1_33157_init.xlsx` with `univer import`.

## Commands

```bash
univer daemon stop
univer import 1_33157_init.xlsx 33157-init.univer --json
univer run 33157-init.univer --code '() => {
  const wb = univerAPI.getActiveWorkbook();
  const s = wb.getSheetByName("Sheet1");
  return {
    success: true,
    values: s.getRange("C3").getValues(),
    display: s.getRange("C3").getDisplayValues(),
    formulas: s.getRange("C3").getFormulas(),
    cellDatas: s.getRange("C3").getCellDatas()
  };
}'
```

## Expected

`Sheet1!C3` should calculate to the same non-empty value as the original Excel file.
When opened in Excel and WPS, the original `.xlsx` displays `16/01/2009` in
`Sheet1!C3`.

## Actual

After import, `Sheet1!C3` keeps the formula but its calculated value is empty:

```text
formula = =IFERROR(VALUE(REPLACE(B3,11,500,"")),"")
value = ""
```
