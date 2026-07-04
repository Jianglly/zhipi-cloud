Write-Output "Running ZhiPi Cloud API Tests ..."
Write-Output "=================================================="

$python = "C:\Users\HP\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
$pytest = "C:\Users\HP\.workbuddy\binaries\python\envs\default\Scripts\pytest.exe"

# 验证虚拟环境存在
if (-not (Test-Path $pytest)) {
    Write-Error "ERROR: pytest not found in virtual environment."
    Write-Output "Path checked: $pytest"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Output "Using Python: $python"
Write-Output "Using pytest: $pytest"
Write-Output ""

# 运行测试套件
& $pytest tests/ -v --tb=short

$exitCode = $LASTEXITCODE
Write-Output ""
Write-Output "=================================================="
if ($exitCode -eq 0) {
    Write-Output "All tests passed!"
} else {
    Write-Output "Some tests failed (exit code: $exitCode)"
}

Read-Host "Press Enter to exit"
