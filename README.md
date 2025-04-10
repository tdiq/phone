# Microwave Phone


## Key Features

* Detects phone pickup/hangup via GPIO.
* Plays audio prompts and records user input.
* Basic speech/silence detection after prompts.
* Sends/Receives OSC messages for status and control.
* Activates physical phone ringer via GPIO.

## Requirements

* **Hardware:** Raspberry Pi, Phone Handset (Mic/Speaker), Hook Switch, Ringer mechanism, Audio Interface (USB/HAT recommended). (GPIO pins defined in `modules/Phone.py`).
* **Software:** Python 3.5.3, `portaudio19-dev`
* **Python Libs:** See `requirements.txt` (includes `gpiozero`, `pygame`, `pyaudio`, `python-osc`).

## Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1.  **OSC IP:** Edit `CTRL_PC_ADDRESS` in `app.py`.
3.  **Audio Files:** Ensure `.wav` files exist in paths used by `app.py` (e.g., `assets/dialogue/`). Wav only for now.
4.  **Speech Threshold:** Tune `silence_threshold` in the `play_and_listen` call within `app.py` based on testing.

## Running

```bash
source venv/bin/activate
python app.py
```
