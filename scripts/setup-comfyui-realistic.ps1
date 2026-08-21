$ErrorActionPreference = "Stop"

$src = "C:\Users\Sebastian\Downloads\realisticVisionV60B1_v51HyperVAE.safetensors"
$dst = "C:\OmniRoute\ComfyUI\models\checkpoints\realisticVisionV60B1_v51HyperVAE.safetensors"
$ggufDir = "C:\OmniRoute\ComfyUI\custom_nodes\ComfyUI-GGUF"
$ggufRepo = "https://github.com/city96/ComfyUI-GGUF"
$expectedHash = "F47E942AD4C30D863AD7F53CB60145FFCD2118845DFA705CE8BD6B42E90C4A13"
$expectedSize = 2132625894
$minSize = 1900000000

function Write-Info($msg) { Write-Host "[setup-comfyui-realistic] $msg" }

if (!(Test-Path -LiteralPath $src)) {
    Write-Host "[setup-comfyui-realistic] ERROR: source checkpoint not found: $src" -ForegroundColor Red
    exit 1
}

$srcSize = (Get-Item -LiteralPath $src).Length
if ($srcSize -lt $minSize) {
    Write-Host "[setup-comfyui-realistic] ERROR: source too small ($srcSize bytes, expected > $minSize)" -ForegroundColor Red
    exit 1
}

Write-Info "Verifying source SHA256..."
$srcHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $src).Hash
if ($srcHash -ne $expectedHash) {
    Write-Host "[setup-comfyui-realistic] ERROR: source SHA256 mismatch. Expected $expectedHash got $srcHash" -ForegroundColor Red
    exit 1
}
Write-Info "Source OK: $srcSize bytes, SHA256 $srcHash"

$dstDir = Split-Path -Parent $dst
if (!(Test-Path -LiteralPath $dstDir)) {
    Write-Info "Creating directory $dstDir"
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
}

$needCopy = $true
if (Test-Path -LiteralPath $dst) {
    $dstSize = (Get-Item -LiteralPath $dst).Length
    if ($dstSize -eq $srcSize) {
        $dstHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash
        if ($dstHash -eq $expectedHash) {
            Write-Info "Destination already exists and is valid, skipping copy: $dst"
            $needCopy = $false
        } else {
            Write-Info "Destination hash mismatch ($dstHash), recopying..."
        }
    } else {
        Write-Info "Destination size mismatch ($dstSize vs $srcSize), recopying..."
    }
}

if ($needCopy) {
    Write-Info "Copying checkpoint to $dst ..."
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $copiedSize = (Get-Item -LiteralPath $dst).Length
    $copiedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dst).Hash
    if ($copiedSize -ne $expectedSize) {
        Write-Info "Warning: copied size $copiedSize != expected $expectedSize"
    }
    if ($copiedHash -ne $expectedHash) {
        Write-Host "[setup-comfyui-realistic] ERROR: copied file SHA256 mismatch: $copiedHash" -ForegroundColor Red
        exit 1
    }
    Write-Info "Copy done: $copiedSize bytes, SHA256 $copiedHash"
}

if (Test-Path -LiteralPath $ggufDir) {
    Write-Info "ComfyUI-GGUF already exists: $ggufDir"
    Push-Location $ggufDir
    try {
        git rev-parse --is-inside-work-tree 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "ComfyUI-GGUF is a git repo, skipping clone."
        } else {
            Write-Info "ComfyUI-GGUF exists but is not a git repo, skipping."
        }
    } finally {
        Pop-Location
    }
} else {
    $parentDir = Split-Path -Parent $ggufDir
    if (!(Test-Path -LiteralPath $parentDir)) {
        Write-Info "Creating directory $parentDir"
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    }
    Write-Info "Cloning ComfyUI-GGUF from $ggufRepo ..."
    git clone $ggufRepo $ggufDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[setup-comfyui-realistic] ERROR: git clone failed" -ForegroundColor Red
        exit 1
    }
    Write-Info "Clone done: $ggufDir"
}

Write-Info "Done. Checkpoint: $dst, GGUF: $ggufDir"
