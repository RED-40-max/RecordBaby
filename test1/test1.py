#testing out the ytmusic API
import numpy as np
import sounddevice as sd
from ytmusicapi import YTMusic
import yt_dlp
import scipy.io.wavfile as wav
import sys
import threading
import time

class ScratchEngine:
    def __init__(self):
        self.sample_rate = 44100
        self.audio_data = None
        self.playhead = 0.0
        self.speed = 1.0  # 1.0 = Normal forward, -1.0 = Reverse, 0.0 = Paused
        self.is_playing = False
        self.stream = None

    def load_audio_from_yt(self, song_url):
        """Extracts direct audio stream from YouTube URL and loads into memory."""
        import os

        # Remove previous temporary file if it exists
        if os.path.exists('temp_track.wav'):
            os.remove('temp_track.wav')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'temp_track.%(ext)s',  # Let yt-dlp manage extension
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': False  # Set to False so you can see FFmpeg progress in terminal
        }

        print("\nFetching audio stream...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([song_url])

        if not os.path.exists('temp_track.wav'):
            raise FileNotFoundError(
                "FFmpeg failed to convert the audio to 'temp_track.wav'. "
                "Ensure ffmpeg is installed via 'brew install ffmpeg'."
            )

        # Read WAV data into numpy array
        sr, data = wav.read('temp_track.wav')

        # Convert to float32 normalized [-1, 1]
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0

        self.sample_rate = sr
        self.audio_data = data
        self.playhead = 0.0
        print(f"Track Loaded. Duration: {len(data)/sr:.2f}s")

    def _audio_callback(self, outdata, frames, time_info, status):
        """Dynamic resampling playback callback for real-time scratch simulation."""
        if not self.is_playing or self.audio_data is None:
            outdata.fill(0)
            return

        step = self.speed
        indices = self.playhead + np.arange(frames) * step

        valid_mask = (indices >= 0) & (indices < len(self.audio_data))
        valid_indices = indices[valid_mask].astype(int)

        outdata.fill(0)
        if len(valid_indices) > 0:
            if len(self.audio_data.shape) > 1:  # Stereo
                outdata[valid_mask] = self.audio_data[valid_indices]
            else:  # Mono
                outdata[valid_mask, 0] = self.audio_data[valid_indices]
                outdata[valid_mask, 1] = self.audio_data[valid_indices]

        self.playhead += frames * step

        # Boundary checks
        if self.playhead >= len(self.audio_data):
            self.playhead = float(len(self.audio_data) - 1)
            self.is_playing = False
        elif self.playhead < 0:
            self.playhead = 0.0

    def trigger_quick_scratch(self):
        """Brief scratch effect: reverses quickly then snaps forward back to 1.0."""
        def _scratch_sequence():
            orig_speed = self.speed
            self.speed = -2.5  # Fast backward scratch
            time.sleep(0.15)
            self.speed = 2.0   # Fast forward catch-up
            time.sleep(0.15)
            self.speed = 1.0 if orig_speed != 0 else 0.0  # Resume normal

        threading.Thread(target=_scratch_sequence, daemon=True).start()

    def start(self):
        self.is_playing = True
        channels = 2 if len(self.audio_data.shape) > 1 else 1
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=channels,
            callback=self._audio_callback,
            blocksize=1024
        )
        self.stream.start()

    def stop(self):
        self.is_playing = False
        if self.stream:
            self.stream.stop()
            self.stream.close()

if __name__ == "__main__":
    yt = YTMusic()
    player = ScratchEngine()

    yt_URL = ""
    while True:
        print("\n--- SELECT A SONG ---")
        print(" [1] - Die For You")
        print(" [2] - RATATA")
        print(" [3] - Zip Bomb")
        print(" [4] - Quit")

        try:
            choice = int(input("Song (1/2/3/4): ").strip())
        except ValueError:
            print("Invalid input, please enter a number.")
            continue

        if choice == 1:
            yt_URL = "https://www.youtube.com/watch?v=uPD0QOGTmMI"
            break
        elif choice == 2:
            yt_URL = "https://www.youtube.com/watch?v=xkejbXejA-0"
            break
        elif choice == 3:
            yt_URL = "https://www.youtube.com/watch?v=tRsGByepK9E"
            break
        elif choice == 4:
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice, try again.")

    player.load_audio_from_yt(yt_URL)
    player.start()

    print("\n--- CONTROLS ---")
    print("\n [p] Play/Pause | [f] Fast Forward | [b] Reverse | [s] Trigger Scratch | [n] Normal Speed | [q] Quit")

    try:
        while True:
            cmd = input("Command > ").strip().lower()
            if cmd == 'p':
                player.speed = 1.0 if player.speed == 0 else 0.0
            elif cmd == 'f':
                player.speed = 1.8  # Fast forward
            elif cmd == 'b':
                player.speed = -1.2 # Reverse playback
            elif cmd == 's':
                player.trigger_quick_scratch() # Brief scratch burst
            elif cmd == 'n':
                player.speed = 1.0  # Normal forward playback
            elif cmd == 'q':
                break
    finally:
        player.stop()