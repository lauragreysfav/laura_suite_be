$frontend = "D:\LauraSuite\frontend"
$log = "D:\LauraSuite\frontend\vite.log"
Start-Process -WindowStyle Hidden -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory $frontend -RedirectStandardOutput $log
Write-Host "Laura Suite frontend starting on :5173"
