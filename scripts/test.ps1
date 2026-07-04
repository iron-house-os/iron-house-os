Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location backend
try {
    ruff check .
    pytest
}
finally {
    Pop-Location
}

Push-Location frontend
try {
    npm run lint
    npm run build
}
finally {
    Pop-Location
}
