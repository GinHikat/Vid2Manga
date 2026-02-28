
Write-Host "=== Running Unit Tests ==="
pytest tests/unit -v
if ($LASTEXITCODE -ne 0) { Write-Host "Unit Tests Failed"; exit 1 }

Write-Host "`n=== Running Ablation Tests ==="
pytest tests/ablation -v
if ($LASTEXITCODE -ne 0) { Write-Host "Ablation Tests Failed"; exit 1 }

Write-Host "`n=== Running System Tests ==="
pytest tests/system -v
if ($LASTEXITCODE -ne 0) { Write-Host "System Tests Failed"; exit 1 }

Write-Host "`nAll tests passed successfully!"
