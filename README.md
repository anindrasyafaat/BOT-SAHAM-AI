# =============================================
# AUTO UPLOAD TO GITHUB - TINGGAL KLIK!
# =============================================

Write-Host "🚀 STOCK-GOD v11 - Auto GitHub Upload" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Initialize Git
Write-Host "📦 Step 1: Initializing Git..." -ForegroundColor Yellow
git init
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Git not installed! Download from: https://git-scm.com/download/win" -ForegroundColor Red
    Write-Host "After install, run this script again." -ForegroundColor Yellow
    pause
    exit
}

# Step 2: Add all files
Write-Host "✅ Git initialized!" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Step 2: Adding all files..." -ForegroundColor Yellow
git add .
Write-Host "✅ Files added!" -ForegroundColor Green
Write-Host ""

# Step 3: Commit
Write-Host "💾 Step 3: Creating commit..." -ForegroundColor Yellow
git commit -m "Initial commit - STOCK-GOD v11 AI Stock Analysis Platform"
Write-Host "✅ Commit created!" -ForegroundColor Green
Write-Host ""

# Step 4: Rename branch to main
Write-Host "🔀 Step 4: Setting main branch..." -ForegroundColor Yellow
git branch -M main
Write-Host "✅ Branch set to main!" -ForegroundColor Green
Write-Host ""

# Step 5: Instructions for GitHub
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🌐 NEXT STEPS - SUPER SIMPLE!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. KLIK LINK INI untuk create GitHub repo:" -ForegroundColor Yellow
Write-Host "   👉 https://github.com/new" -ForegroundColor Green
Write-Host ""
Write-Host "2. Di halaman GitHub:" -ForegroundColor Yellow
Write-Host "   - Repository name: stock-god-v11" -ForegroundColor White
Write-Host "   - Description: AI Stock Analysis Platform" -ForegroundColor White
Write-Host "   - Public ✅" -ForegroundColor White
Write-Host "   - JANGAN centang 'Add README' ❌" -ForegroundColor Red
Write-Host "   - Click 'Create repository' ✅" -ForegroundColor Green
Write-Host ""
Write-Host "3. COPY URL yang muncul (format: https://github.com/USERNAME/stock-god-v11.git)" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. PASTE URL ke sini dan tekan Enter:" -ForegroundColor Yellow

# Get GitHub URL from user
$githubUrl = Read-Host "GitHub URL"

if ($githubUrl -eq "") {
    Write-Host "❌ URL kosong! Jalankan ulang script ini." -ForegroundColor Red
    pause
    exit
}

# Step 6: Add remote
Write-Host ""
Write-Host "🔗 Step 5: Connecting to GitHub..." -ForegroundColor Yellow
git remote add origin $githubUrl
Write-Host "✅ Connected!" -ForegroundColor Green
Write-Host ""

# Step 7: Push to GitHub
Write-Host "📤 Step 6: Uploading to GitHub..." -ForegroundColor Yellow
Write-Host "⏳ Please wait..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ SUCCESS! APP UPLOADED TO GITHUB!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Your GitHub repo:" -ForegroundColor Cyan
    Write-Host "   $githubUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 NEXT: Deploy to Vercel (FREE Hosting)" -ForegroundColor Cyan
    Write-Host "   1. Go to: https://vercel.com/new" -ForegroundColor Yellow
    Write-Host "   2. Sign in with GitHub" -ForegroundColor Yellow
    Write-Host "   3. Import 'stock-god-v11' repository" -ForegroundColor Yellow
    Write-Host "   4. Click 'Deploy'" -ForegroundColor Yellow
    Write-Host "   5. DONE! App will be live in 30 seconds" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your app URL will be: https://stock-god-v11.vercel.app" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Push failed!" -ForegroundColor Red
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "1. Wrong GitHub URL" -ForegroundColor White
    Write-Host "2. Need to login to GitHub first" -ForegroundColor White
    Write-Host "3. Repository already exists" -ForegroundColor White
    Write-Host ""
    Write-Host "Run this command manually:" -ForegroundColor Yellow
    Write-Host "git push -u origin main" -ForegroundColor White
    Write-Host ""
}

Write-Host "Press any key to exit..." -ForegroundColor Gray
pause
