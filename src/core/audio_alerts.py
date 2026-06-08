import pygame
import numpy as np
import time
import threading

class AudioAlertSystem:
    def __init__(self):
        # Initialize pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)

        # Per-condition palettes — each condition uses sounds with a distinct
        # character so participants form a clear association between condition
        # and how the system warns them.
        self.sounds = {
            # STANDARD: harsh, urgent classic-car-style beeps
            "STANDARD": {
                "CRITICAL": self._generate_beep(1000, 0.4, 0.55, modulate=True),
                "WARNING":  self._generate_beep(800, 0.2, 0.50),
            },
            # AR_HUD: softer two-tone chirps (more like a phone notification)
            "AR_HUD": {
                "CRITICAL": self._generate_chirp(660, 1320, 0.32, 0.5),
                "WARNING":  self._generate_chirp(520, 880,  0.22, 0.4),
            },
        }
        # Legacy aliases — anything that called .critical_sound / .warning_sound
        # still gets the STANDARD palette so existing code paths keep working.
        self.critical_sound = self.sounds["STANDARD"]["CRITICAL"]
        self.warning_sound = self.sounds["STANDARD"]["WARNING"]

        self.is_playing = False
        self.current_level = "SAFE"
        self.current_condition = "STANDARD"   # active palette
        self.audio_thread = None
        self.running = True

        # Start sound manager thread
        self.audio_thread = threading.Thread(target=self._sound_loop, daemon=True)
        self.audio_thread.start()

    def _generate_chirp(self, f_start, f_end, duration, volume):
        """Linear pitch sweep — softer alternative to the modulated beep."""
        sample_rate = 44100
        n_samples = int(round(duration * sample_rate))
        t = np.linspace(0, duration, n_samples, False)
        freq = np.linspace(f_start, f_end, n_samples)
        phase = 2 * np.pi * np.cumsum(freq) / sample_rate
        wave = np.sin(phase)

        # Soft envelope (longer attack/release than a hard beep)
        attack = int(0.04 * sample_rate)
        release = int(0.08 * sample_rate)
        env = np.ones_like(wave)
        if attack > 0 and len(env) > attack:
            env[:attack] = np.linspace(0, 1, attack)
        if release > 0 and len(env) > release:
            env[-release:] = np.linspace(1, 0, release)
        wave = wave * env

        audio = np.int16(wave * volume * 32767)
        if pygame.mixer.get_init()[2] == 2:
            audio = np.repeat(audio.reshape(n_samples, 1), 2, axis=1)
        return pygame.sndarray.make_sound(audio)

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

    # Minimum on-screen footprint for the threat to count as "really close".
    # A pedestrian/vehicle that's super close fills a noticeable fraction of
    # the frame; far-away ones don't. This sidesteps the per-frame-normalized
    # depth issue (MiDaS reports relative not absolute distance).
    AUDIO_THREAT_AREA_FRAC = 0.025   # ≈ 2.5% of frame area

    def set_alert_level(self, level, min_depth: float = -1.0,
                        threat_area_frac: float = 0.0):
        """
        level: SAFE / CAUTION / WARNING / CRITICAL (drives visual alerts).
        threat_area_frac: 0..1, fraction of the frame occupied by the closest
                          detected object. Audio fires only when this exceeds
                          AUDIO_THREAT_AREA_FRAC — proxy for "object is super
                          close in the real world", not just relatively close.
        min_depth: kept for backwards-compat but no longer used to gate audio.
        """
        self.current_level = level
        self.current_threat_area_frac = float(threat_area_frac)
        self.current_min_depth = float(min_depth)

    def set_condition(self, condition_name: str):
        """Switch the active sound palette to match the experimental condition."""
        if condition_name in self.sounds:
            self.current_condition = condition_name

    def _should_play(self):
        """
        Audio fires only when BOTH:
        1. The alert system rated this CRITICAL
        2. A real threat object was detected on-screen (size > threshold)

        Without #2 we'd fire constantly because MiDaS depth is per-frame
        normalized — there's always something "closest" in the ROI even when
        the road ahead is clear.
        """
        area = getattr(self, "current_threat_area_frac", 0.0)
        if area < self.AUDIO_THREAT_AREA_FRAC:
            return None    # nothing big enough to be a real, close threat
        if self.current_level == "CRITICAL":
            return "CRITICAL"
        # WARNING audio disabled by default — visual cues already cover it
        return None

    def _sound_loop(self):
        """Background loop — fires beeps only when a real, close threat exists."""
        while self.running:
            palette = self.sounds.get(self.current_condition, self.sounds["STANDARD"])
            kind = self._should_play()
            if kind == "CRITICAL" and not pygame.mixer.get_busy():
                palette["CRITICAL"].play()
                time.sleep(0.4)
            else:
                time.sleep(0.1)
                
    def cleanup(self):
        self.running = False
        pygame.mixer.quit()
