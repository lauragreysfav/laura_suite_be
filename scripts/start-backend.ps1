$python = "C:\Users\Grey Area\AppData\Local\Programs\Python\Python312\python.exe"
$backend = "D:\LauraSuite\backend"
$log = "D:\LauraSuite\backend\server.log"
Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info" -WorkingDirectory $backend -RedirectStandardOutput $log
Write-Host "Laura Suite backend started on :8000"
