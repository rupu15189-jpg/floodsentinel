# 一键把本地仓库推送到 GitHub
#
# 用法（在项目根目录）：
#   powershell -ExecutionPolicy Bypass -File .\scripts\push-to-github.ps1 -RepoUrl "https://github.com/你的用户名/floodsentinel.git"
#
# 前提：已经在 GitHub 上建好一个**空仓库**（不要勾选 README / .gitignore / license）

param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

# 切到项目根目录（脚本在 scripts/ 下）
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "项目目录：$root" -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    Write-Host "这里不是 git 仓库，先执行 git init" -ForegroundColor Red
    exit 1
}

if ($RepoUrl -notmatch '^https://') {
    Write-Host "建议使用 https 地址（SSH 需要额外配密钥）：$RepoUrl" -ForegroundColor Yellow
}

# 已有 origin 就先移除，避免 "remote origin already exists"
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
    Write-Host "已存在 origin：$existing，覆盖为 $RepoUrl" -ForegroundColor Yellow
    git remote remove origin
}

git remote add origin $RepoUrl
git branch -M $Branch

$dirty = git status --porcelain
if ($dirty) {
    Write-Host "注意：有未提交的改动，本次不会推送它们：" -ForegroundColor Yellow
    $dirty | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
}

Write-Host "开始推送 $Branch ..." -ForegroundColor Cyan
git push -u origin $Branch

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "推送成功。仓库地址：$RepoUrl" -ForegroundColor Green
    Write-Host "把这条地址发到群里，队友就能 git clone 了。" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "推送失败。常见原因：" -ForegroundColor Red
    Write-Host "  1. 仓库不是空的 —— 建仓库时勾了 README，先去网页删掉或改用 --force" -ForegroundColor Gray
    Write-Host "  2. 没登录 —— 应该会弹浏览器登录窗口，登录后重试" -ForegroundColor Gray
    Write-Host "  3. 网络问题 —— 试试手机热点或 Gitee" -ForegroundColor Gray
    exit 1
}
