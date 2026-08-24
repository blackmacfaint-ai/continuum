@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Money Printer — 7-Step One-Click Orchestrator
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
set YT_JSON=data/audio/youtube.json
set YT_PRIVACY=unlisted
set YT_VOICE=martin
set YT_ENGINE=voicebox
set YT_VOICEBOX_PROFILE=Overlay DE
set TTS_SPEED=1.15
rem YT_PRIVACY: unlisted (Default) | public | private  — fuer echte Veroeffentlichung auf "public" stellen
rem YT_ENGINE: voicebox (Default, Overlay DE) | kokoro
rem YT_VOICE: nur bei YT_ENGINE=kokoro (martin|emma|dmdf|tf_mlenia|...) — Hoerproben in data/voice_samples/
rem YT_VOICEBOX_PROFILE: Voicebox-Profilname (Default "Overlay DE")
rem TTS_SPEED: nur bei YT_ENGINE=kokoro (1.15 natuerlich, 1.0 ruhig, 1.4 hektisch)

set PROMPT_FILE=scripts\prompts\script_short.txt
set IMG_PROMPT=%TOPIC%, cinematic, photorealistic, golden hour, dramatic lighting
set VID_PROMPT=%TOPIC%, cinematic slow pan

:: ============================================================================
:: STEP 1/7: ai/generate
:: ============================================================================
echo [%TIME%] Step 1/7: ai/generate ...
python scripts/ai_generate.py --prompt-file "%PROMPT_FILE%" --topic "%TOPIC%" %DRY_FLAG% > "%SCRIPT_JSON%" 2>&1
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: ai/generate failed & type "%SCRIPT_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%SCRIPT_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   words:',d.get('words','?'),'| model:',d.get('model','?'))"
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: script JSON invalid & exit /b 1)
if %DRY_RUN%==0 (
  python -c "import json,pathlib; t=json.load(open('%SCRIPT_JSON%',encoding='utf-8'))['text']; pathlib.Path('%SCRIPT_TXT%').write_text(t,encoding='utf-8')"
  python scripts/clean_script.py "%SCRIPT_TXT%" "%SCRIPT_TXT%"
)
echo.

:: ============================================================================
:: STEP 2/7: tts/speak
:: ============================================================================
echo [%TIME%] Step 2/7: tts/speak ...
if %DRY_RUN%==1 (
  python scripts/tts_speak.py --text "dry" --speed 1.5 --output "%VOICE_WAV%" --dry-run > "%TTS_JSON%" 2>&1
) else if "%YT_ENGINE%"=="voicebox" (
  python -c "import json,subprocess,sys; t=json.load(open('%SCRIPT_JSON%',encoding='utf-8'))['text']; r=subprocess.run([sys.executable,'scripts/tts_speak.py','--text',t,'--engine','voicebox','--profile','%YT_VOICEBOX_PROFILE%','--fallback-engine','kokoro','--output','%VOICE_WAV%'],capture_output=True,text=True,cwd=r'%CD%'); print(r.stdout); sys.exit(r.returncode)" > "%TTS_JSON%" 2>&1
) else (
  python -c "import json,subprocess,sys; t=json.load(open('%SCRIPT_JSON%',encoding='utf-8'))['text']; r=subprocess.run([sys.executable,'scripts/tts_speak.py','--text',t,'--voice','%YT_VOICE%','--speed','%TTS_SPEED%','--output','%VOICE_WAV%'],capture_output=True,text=True,cwd=r'%CD%'); print(r.stdout); sys.exit(r.returncode)" > "%TTS_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: tts/speak failed & type "%TTS_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%TTS_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   engine:',d.get('engine','?'),'| duration:',round(d.get('duration',0),1),'s')"
echo.

:: ============================================================================
:: STEP 3/7: image/generate-realistic
:: ============================================================================
echo [%TIME%] Step 3/7: image/generate-realistic (3 images, 576x1024) ...
python scripts/image_generate_realistic.py --prompt "%IMG_PROMPT%" --batch 3 --output "%IMG_OUT%" %DRY_FLAG% > "%IMG_JSON%" 2>&1
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: image/generate-realistic failed & type "%IMG_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%IMG_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   images:',len(d.get('images',[])),'| seed:',d.get('seed','?'))"
echo.

:: ============================================================================
:: STEP 4/7: video/generate --base-images
:: ============================================================================
echo [%TIME%] Step 4/7: video/generate (array path, 3 images x 4 frames) ...
if %DRY_RUN%==1 (
  echo {"success":true,"images":3,"frames":12,"model":"ken-burns","duration":9.25,"dryRun":true} > "%BROLL_JSON%"
) else (
  python -c "import json,subprocess,sys; d=json.load(open('%IMG_JSON%',encoding='utf-8')); imgs=','.join(d['images']); r=subprocess.run([sys.executable,'scripts/video_generate.py','--base-images',imgs,'--prompt','%VID_PROMPT%','--frames','4','--output',r'%BROLL_OUT%'],capture_output=True,text=True,cwd=r'%CD%'); print(r.stdout); sys.exit(r.returncode)" > "%BROLL_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: video/generate failed & type "%BROLL_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%BROLL_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   images:',d.get('images','?'),'| frames:',d.get('frames','?'),'| duration:',round(d.get('duration',0),1),'s')"
echo.

:: ============================================================================
:: STEP 5/7: ffmpeg_tiktok
:: ============================================================================
echo [%TIME%] Step 5/7: ffmpeg_tiktok (1080x1920, subtitles) ...
if %DRY_RUN%==1 (
  echo {"success":true,"videoPath":"%TIKTOK_OUT%","width":1080,"height":1920,"fps":24,"duration":22.0,"codecVideo":"h264","codecAudio":"aac","dryRun":true} > "%TIKTOK_JSON%"
) else (
  python scripts/ffmpeg_tiktok.py --video "%BROLL_OUT%" --audio "%VOICE_WAV%" --subtitles --subtitle-lang de --subtitle-model small --output "%TIKTOK_OUT%" > "%TIKTOK_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: ffmpeg_tiktok failed & type "%TIKTOK_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%TIKTOK_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   ',d.get('width','?'),'x',d.get('height','?'),'|',round(d.get('duration',0),1),'s','|',d.get('codecVideo','?'),'+',d.get('codecAudio','?'))"
echo.

:: ============================================================================
:: STEP 6/7: artifacts/store
:: ============================================================================
echo [%TIME%] Step 6/7: artifacts/store ...
if %DRY_RUN%==1 (
  echo {"success":true,"artifactId":"dry-run-000000000000","path":"%TIKTOK_OUT%","dryRun":true} > "%ARTIFACT_JSON%"
) else (
  python scripts/artifacts_store.py --artifact "%TIKTOK_OUT%" --type video > "%ARTIFACT_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: artifacts/store failed & type "%ARTIFACT_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%ARTIFACT_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   artifact:',d.get('artifactId','?'))"
echo.

:: ============================================================================
:: STEP 7/7: youtube/upload
:: ============================================================================
echo [%TIME%] Step 7/7: youtube/upload (privacy=%YT_PRIVACY%) ...
if %DRY_RUN%==1 (
  echo {"success":true,"videoId":"dry-run-000000000000","url":"https://youtu.be/dry-run","dryRun":true} > "%YT_JSON%"
) else (
  python scripts/youtube_upload_pipeline.py --video "%TIKTOK_OUT%" --topic "%TOPIC%" --privacy %YT_PRIVACY% > "%YT_JSON%" 2>&1
)
if %ERRORLEVEL% neq 0 (echo [%TIME%] FATAL: youtube/upload failed & type "%YT_JSON%" & exit /b 1)
python -c "import json; d=json.load(open('%YT_JSON%',encoding='utf-8')); print('OK' if d.get('success') else 'FAIL: '+d.get('error','?')+'\n   url:',d.get('url','?'))"
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
  if exist "%YT_JSON%" python -c "import json; d=json.load(open('%YT_JSON%',encoding='utf-8')); print('  YouTube:', d.get('url','-') if d.get('success') else 'Upload fehlgeschlagen')"
)
echo ################################################################################

endlocal
exit /b 0