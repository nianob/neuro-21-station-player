A small and resource-friendly player for the [Neuro 21 Station](https://radio.twinskaraoke.com/public/neuro_21).

## Features

- choosing between the mp3 and hls stream type
- muting/unmuting the stream
- changing the volume
- seeing, if the song is liked on https://neurokaraoke.com
- opening the song directly on https://neurokaraoke.com
- hitting F1 hides the menu

## Features for advanced users

- the settings are saved at `[Your User Directory]/neuro_21_station_player/settings_v2.json`
- the images in `[Your User Directory]/neuro_21_station_player` can be replaced and used instead of the default ones (deleting them will cause them to reset)
- logs from the current session are saved to `[Your User Directory]/neuro_21_station_player/latest.log`
- when the player crashes the logs will be saved to  `[Your User Directory]/neuro_21_station_player/crash_[Current Date and Time].log`
- show all hitboxes using the `--hitboxes` flag when starting the player

## Comming Soon™

- A proper settings menu
- Discord Integration
- Liking/Unliking songs directly in the app

## How to run it directly

- Install Python >= 3.12
- Install Dependencies: `python -m pip install -r requirements.txt`
- Run `player_v2.py` using python >= 3.12

## How to build yourself

- Install Python >= 3.12
- Install Dependencies: `python -m pip install -r requirements.txt`
- Run `build.bat` on Windows or `build.sh` on linux
