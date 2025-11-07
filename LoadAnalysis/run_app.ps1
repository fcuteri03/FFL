# Start Streamlit Dashboard
Write-Host "Starting TMS Lane & Rate Analysis Dashboard..." -ForegroundColor Green
Set-Location $PSScriptRoot
$env:Path = "C:\Python314;C:\Python314\Scripts;$env:Path"
streamlit run app.py

