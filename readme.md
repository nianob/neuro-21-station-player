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

## Detailed breakdown of settings:
All of the settings are saved in `[Your User Directory]/neuro_21_station_player/settings_v2.json`. When you delete any setting from your settings file it will be reset automatically.

 Setting | Default | Description
 -----:  | :-----: | :----------
`size` | `[600, 600]` | The Size of the window, when it starts.
`data_url` | `"https://radio.twinskaraoke.com/api/ nowplaying_static/neuro_21.json"` | The url to fetch the data from
`darken_factor` | `0.75` | How much to brighten/darken the blurred area, 0 is completely black and 1 is not darkened at all
`main_container_width` | `0.7` | How wide the blurred area is relatively to the window
`blur_scale` | `20` | How much the blurred area should be blurred
`border_radius` | `0.1` | How rounded the edges of the blurred are
`author_scale` | `0.65` | How big the name of the author is relatively to the title of the song
`font_color` | `[255, 255, 255]` | The color of most text
`content_padding` | `0.03` | How big the padding of the the elements is
`controls_size` | `0.075` | How big the buttons are
`button_padding` | `0.01` | The distance between the buttons
`autoplay` | `false` | If the player should start playing
`button_color` | `[134, 215, 247, 170]` | The color of the the buttons
`progress_bar_color` | `[255, 255, 255, 100]` | The background color of the progress bar
`stream_type` | `"mp3"` | The default stream type. Possible options: `"mp3"`, `"hls"`
`button_text_color` | `[0, 0, 0]` | The color of the text on the buttons
`open_link` | `"https://neurokaraoke.com/song/%s` | The link to use to open the songs, `%s` is replaced by the song-id
`referal_url` | `"https://twinskaraoke.com/"` | The url to use as the referal url and origin for all requests to api.neurokaraoke.com
`volume` | `0.15` | The volume of the audio when the player starts
`reduce_fps` | `"hidden"` | When to reduce the fps. Possible options: `"never"`, `"hidden"`, `"unfocused"`
`fps` | `60` | The maximum framerate of the app
`reduced_fps` | `2` | The maximum framerate when the fps are reduced
