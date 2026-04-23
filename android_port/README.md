# Aethrune Android Port

This folder contains an Android-friendly wrapper for the Aethrune Python text adventure.

The desktop game is being retconned into the original Aethrune setting. This Android port mirrors the desktop implementation and should be updated after each stable desktop retcon pass rather than treated as separate canon.

## What Is Here

- `main.py`: Kivy app entry point for touch devices.
- `dnd_game/`: copied game engine and story content.
- `requirements.txt`: desktop / Pydroid dependency hint.
- `buildozer.spec`: starter config if you want to package an APK later.

## Fastest Way To Run On Android: Pydroid 3

1. Copy the entire `android_port` folder onto your Android device.
2. Install **Pydroid 3** from the Play Store.
3. Open Pydroid 3 and use its file browser to open `android_port/main.py`.
4. In Pydroid 3, install Kivy if it is not already available.
5. Press Run.

The app stores saves inside the app's own data folder, not in the original desktop `saves/` directory.

## Desktop Preview Before Moving To Android

From inside this folder:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Packaging An APK Later

The included `buildozer.spec` is a starter config for packaging.

Important note:

- Buildozer is usually run from Linux, WSL, or a Linux VM.
- It is not a smooth native Windows workflow.

Typical packaging flow from Linux or WSL:

```bash
cd android_port
pip install buildozer
buildozer android debug
```

The generated APK usually ends up under:

```text
android_port/bin/
```

## Current UI Behavior

- Story text appears in a scrollable log.
- Numbered choices become touch buttons.
- You can still type commands like `save`, `journal`, `inventory`, and `camp`.
- Text-entry prompts like character names and quantity prompts use the text box at the bottom.

## Retcon Note

The Android copy currently follows the desktop source. During the Aethrune retcon, update desktop first, verify it, then mirror stable public-text changes into `android_port/dnd_game`.
