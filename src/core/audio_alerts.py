import pygame
import numpy as np
import time
import threading

class AudioAlertSystem:
    def __init__(self):
        # Initialize pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
        
        # Generate generic beep sounds in memory (no files needed)
        self.critical_sound = self._generate_beep(1000, 0.4, 0.5, modulate=True)
        self.warning_sound = self._generate_beep(800, 0.2, 0.5)
        
        self.is_playing = False
        self.current_level = "SAFE"
        self.audio_thread = None
        self.running = True
        
        # Start sound manager thread
        self.audio_thread = threading.Thread(target=self._sound_loop, daemon=True)
        self.audio_thread.start()

    def _generate_beep(self, frequency, duration, volume, modulate=False):
        """Generate a raw audio buffer for a beep"""
        sample_rate = 44100
        n_samples = int(round(duration * sample_rate))
        t = np.linspace(0, duration, n_samples, False)
        
        # Base sine wave
        wave = np.sin(frequency * t * 2 * np.pi)
        
        if modulate:
            # Add an urgent modulation effect
            mod = 0.5 * (1 + np.sin(10 * 2 * np.pi * t))
            wave = wave * mod
            
        # Envelope to avoid clicking
        attack = int(0.01 * sample_rate)
        release = int(0.05 * sample_rate)
        
        env = np.ones_like(wave)
        if attack > 0 and len(env) > attack:
            env[:attack] = np.linspace(0, 1, attack)
        if release > 0 and len(env) > release:
            env[-release:] = np.linspace(1, 0, release)
            
        wave = wave * env
        
        # Convert to 16-bit integer array
        audio = np.int16(wave * volume * 32767)
        # Stereo format requirement for pygame mixer sometimes
        if pygame.mixer.get_init()[2] == 2:
            audio = np.repeat(audio.reshape(n_samples, 1), 2, axis=1)
            
        return pygame.sndarray.make_sound(audio)

    def set_alert_level(self, level):
        self.current_level = level

    def _sound_loop(self):
        """Background loop to play sounds based on current alert level"""
        while self.running:
            if self.current_level == "CRITICAL" and not pygame.mixer.get_busy():
                self.critical_sound.play()
                time.sleep(0.4) # Wait for sound to finish
            elif self.current_level == "WARNING" and not pygame.mixer.get_busy():
                self.warning_sound.play()
                time.sleep(1.0) # Play less frequently than critical
            else:
                time.sleep(0.1)
                
    def cleanup(self):
        self.running = False
        pygame.mixer.quit()
