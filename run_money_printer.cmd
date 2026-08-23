@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Money Printer — 6-Step One-Click Orchestrator
:: ============================================================================
:: Usage:
::   run_money_printer.cmd                           (default topic)
::   run_money_printer.cmd "Hamburger Hafen"           (custom topic)
::   run_money_printer.cmd --topic "Cafe" --dry-run    (validate only)
:: ============================================================================

set TOPIC=Hamburger Hafen bei Sonnenuntergang, Containerterminals, Krane, Elbe
set DRY_RUN=0
set DRY_FLAG=
set TIMESTAMP=%DATE:~-4%%DATE:~-7,2%%DATE:~-10,2%-%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_DIR=logs\money_printer
set LOG=%LOG_DIR%\%TIMESTAMP%.log

:: ---- Parse args ----
:parse
if "%~1"=="" goto :start
if /i "%~1"=="--dry-run" (set DRY_RUN=1 & shift & goto :parse)
if /i "%~1"=="--topic"   (set "TOPIC=%~2" & shift & shift & goto :parse)
set "TOPIC=%~1"
shift
goto :parse

:start
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if %DRY_RUN%==1 (set DRY_FLAG=--dry-run)

echo ################################################################################
echo # Money Printer — %DATE% %TIME%
echo # Topic: %TOPIC%
if %DRY_RUN%==1 (echo # MODE: dry-run) else (echo # MODE: production)
echo # Log: %LOG%
echo ################################################################################
echo.

set SCRIPT_JSON=data/audio/script.json
set SCRIPT_TXT=data/audio/script.txt
set TTS_JSON=data/audio/tts.json
set VOICE_WAV=data/audio/e2e_voice.wav
set IMG_JSON=data/audio/images.json
set IMG_OUT=C:/OmniRoute/ComfyUI/output/continuum/money_printer
set BROLL_JSON=data/audio/broll.json
set BROLL_OUT=%IMG_OUT%/broll.mp4
set TIKTOK_JSON=data/audio/tiktok.json
set TIKTOK_OUT=data/media/e2e_tiktok.mp4
set ARTIFACT_JSON=data/audio/artifact.json

set PROMPT=Schreibe ein 150-Woerter deutsches faceless TikTok-Skript ueber %TOPIC%: packender Hook am Anfang, 3 kurze Fakten, Call-to-Action am Ende. Keine Einleitung, nur der Sprechertext.
set IMG_PROMPT=%TOPIC%, cinematic, photorealistic, golden hour, dramatic lighting
set VID_PROMPT=%TOPIC%, cinematic slow pan

:: ============================================================================
:: STEP 1/6: ai/generate
:: ============================================================================
echo [%TIME%] Step 1/6: ai/generate ...
python scripts/ai_generate.py --prompt "%PROMPT%" %DRY_FLAG% > "%SCRIPT_JSON%" 2>&1
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: ai/generate failed & type "%SCRIPT_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%SCRIPT_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   words:',d.get('words','?'),'| model:',d.get('model','?'))"
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: script JSON invalid & exit /b 1)
if %DRY_RUN%==0 python -c "import json,pathlib; t=json.load(open('%SCRIPT_JSON%',encoding='utf-8'))['text']; pathlib.Path('%SCRIPT_TXT%').write_text(t,encoding='utf-8')"
echo.

:: ============================================================================
:: STEP 2/6: tts/speak
:: ============================================================================
echo [%TIME%] Step 2/6: tts/speak ...
if %DRY_RUN%==1 (
  python scripts/tts_speak.py --text "dry" --speed 1.5 --output "%VOICE_WAV%" --dry-run > "%TTS_JSON%" 2>&1
) else (
  python -c "import json,subprocess,sys; t=json.load(open('%SCRIPT_JSON%',encoding='utf-8'))['text']; r=subprocess.run([sys.executable,'scripts/tts_speak.py','--text',t,'--speed','1.5','--output','%VOICE_WAV%'],capture_output=True,text=True,cwd=r'%CD%'); print(r.stdout); sys.exit(r.returncode)" > "%TTS_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: tts/speak failed & type "%TTS_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%TTS_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   engine:',d.get('engine','?'),'| duration:',round(d.get('duration',0),1),'s')"
echo.

:: ============================================================================
:: STEP 3/6: image/generate-realistic
:: ============================================================================
echo [%TIME%] Step 3/6: image/generate-realistic (3 images, 576x1024) ...
python scripts/image_generate_realistic.py --prompt "%IMG_PROMPT%" --batch 3 --output "%IMG_OUT%" %DRY_FLAG% > "%IMG_JSON%" 2>&1
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: image/generate-realistic failed & type "%IMG_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%IMG_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   images:',len(d.get('images',[])),'| seed:',d.get('seed','?'))"
echo.

:: ============================================================================
:: STEP 4/6: video/generate --base-images
:: ============================================================================
echo [%TIME%] Step 4/6: video/generate (array path, 3 images x 4 frames) ...
if %DRY_RUN%==1 (
  echo {"success":true,"images":3,"frames":12,"model":"ken-burns","duration":9.25,"dryRun":true} > "%BROLL_JSON%"
) else (
  python -c "import json,subprocess,sys; d=json.load(open('%IMG_JSON%',encoding='utf-8')); imgs=','.join(d['images']); r=subprocess.run([sys.executable,'scripts/video_generate.py','--base-images',imgs,'--prompt','%VID_PROMPT%','--frames','4','--output',r'%BROLL_OUT%'],capture_output=True,text=True,cwd=r'%CD%'); print(r.stdout); sys.exit(r.returncode)" > "%BROLL_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: video/generate failed & type "%BROLL_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%BROLL_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   images:',d.get('images','?'),'| frames:',d.get('frames','?'),'| duration:',round(d.get('duration',0),1),'s')"
echo.

:: ============================================================================
:: STEP 5/6: ffmpeg_tiktok
:: ============================================================================
echo [%TIME%] Step 5/6: ffmpeg_tiktok (1080x1920, subtitles) ...
if %DRY_RUN%==1 (
  echo {"success":true,"videoPath":"%TIKTOK_OUT%","width":1080,"height":1920,"fps":24,"duration":22.0,"codecVideo":"h264","codecAudio":"aac","dryRun":true} > "%TIKTOK_JSON%"
) else (
  python scripts/ffmpeg_tiktok.py --video "%BROLL_OUT%" --audio "%VOICE_WAV%" --subtitles --subtitle-lang de --subtitle-model small --output "%TIKTOK_OUT%" > "%TIKTOK_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: ffmpeg_tiktok failed & type "%TIKTOK_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%TIKTOK_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   ',d.get('width','?'),'x',d.get('height','?'),'|',round(d.get('duration',0),1),'s','|',d.get('codecVideo','?'),'+',d.get('codecAudio','?'))"
echo.

:: ============================================================================
:: STEP 6/6: artifacts/store
:: ============================================================================
echo [%TIME%] Step 6/6: artifacts/store ...
if %DRY_RUN%==1 (
  echo {"success":true,"artifactId":"dry-run-000000000000","path":"%TIKTOK_OUT%","dryRun":true} > "%ARTIFACT_JSON%"
) else (
  python scripts/artifacts_store.py --artifact "%TIKTOK_OUT%" --type video > "%ARTIFACT_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: artifacts/store failed & type "%ARTIFACT_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%ARTIFACT_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   artifact:',d.get('artifactId','?'))"
echo.

:: ============================================================================
:: DONE
:: ============================================================================
echo ################################################################################
echo # Money Printer COMPLETE — %DATE% %TIME%
if %DRY_RUN%==1 (
  echo # MODE: dry-run (no artifacts)
) else (
  echo # Video: %TIKTOK_OUT%
  echo # Voice: %VOICE_WAV%
  echo # B-Roll: %BROLL_OUT%
  echo # Images: %IMG_OUT%\
)
echo ################################################################################

endlocal
exit /b 0