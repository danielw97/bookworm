# coding: utf-8

import threading
import queue
import string
import weakref
import winsound
from pathlib import Path

from bookworm.paths import data_path
from bookworm.i18n import LocaleInfo
from bookworm.logger import logger
from bookworm.speechdriver.engine import BaseSpeechEngine, VoiceInfo
from bookworm.speechdriver.enumerations import (SynthState, EngineEvent, SpeechElementKind, RateSpec, VolumeSpec, PauseSpec)
from bookworm.platforms.win32.nvwave import WavePlayer

from ..utils import audio_uri_to_filepath
from .tts_system import PiperTextToSpeechSystem, AudioTask, BookmarkTask, DEFAULT_RATE, DEFAULT_VOLUME


log = logger.getChild(__name__)


PAUSE_VALUE_MAP = {
    PauseSpec.null: 10,
    PauseSpec.extra_small: 100,
    PauseSpec.small: 250,
    PauseSpec.medium: 500,
    PauseSpec.large: 750,
    PauseSpec.extra_large: 1000,
}
RATE_VALUE_MAP = {
    RateSpec.not_set: None,
    RateSpec.extra_slow: 20,
    RateSpec.slow: 40,
    RateSpec.medium: 60,
    RateSpec.fast: 80,
    RateSpec.extra_fast: 100,
}
VOLUME_VALUE_MAP = {
    VolumeSpec.not_set: None,
    VolumeSpec.silent: 1,
    VolumeSpec.extra_soft: 10,
    VolumeSpec.soft: 25,
    VolumeSpec.medium: 50,
    VolumeSpec.loud: 75,
    VolumeSpec.extra_loud: 100,
    VolumeSpec.default: DEFAULT_VOLUME
}



class AudioFileTask:
    __slots__ = ["filename", "event_sink"]

    def __init__(self, filename, event_sink):
        self.filename = filename
        self.event_sink = event_sink

    def __call__(self):
        if self.event_sink._silence_event.is_set():
            return
        winsound.PlaySound(self.filename, winsound.SND_FILENAME)


class ProcessPiperTask:
    __slots__ = ["task", "player", "event_sink"]

    def __init__(self, task, player, event_sink):
        self.task = task
        self.player = player
        self.event_sink = event_sink

    def __call__(self):
        if self.event_sink._silence_event.is_set():
            return
        self.event_sink.on_state_changed(SynthState.busy)
        if isinstance(self.task, AudioTask):
            self.player.feed(self.task.generate_audio())
        elif isinstance(self.task, BookmarkTask):
            self.event_sink.on_bookmark_reached(self.task.name)


class DoneSpeaking:
    __slots__ = ["player", "event_sink"]

    def __init__(self, player, event_sink):
        self.player = player
        self.event_sink = event_sink

    def __call__(self):
        if self.event_sink._silence_event.is_set():
            self.player.stop()
            self.player.close()
        self.player.idle()
        self.event_sink.on_state_changed(SynthState.ready)


class BgThread(threading.Thread):

    def __init__(self, bgQueue):
        super().__init__()
        self._bgQueue = bgQueue
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            task = self._bgQueue.get()
            if task is None:
                break
            try:
                task()
            except Exception:
                log.error("Error running task from queue", exc_info=True)
            self._bgQueue.task_done()


class EventSink:
    def __init__(self, synthref):
        self.synthref = synthref
        self._state = SynthState.ready
        self._silence_event = threading.Event()
        self._silence_event.set()

    def on_state_changed(self, state):
        if state is self._state:
            return
        if (synth := self.synthref()) is None:
            log.warning(
                "Called on_state_changed method on OneCoreSynth while the synthesizer is dead"
            )
            self._state = SynthState.ready
            return
        self._state = state
        handlers = synth.event_handlers.get(EngineEvent.state_changed, ())
        for handler in handlers:
            handler(self, state)

    def on_bookmark_reached(self, bookmark):
        if (synth := self.synthref()) is None:
            log.warning(
                "Called on_bookmark_reached method on synth while the synthesizer is dead"
            )
            return
        for handler in synth.event_handlers.get(EngineEvent.bookmark_reached, ()):
            handler(self, bookmark)


class PiperSpeechEngine(BaseSpeechEngine):
    name = "piper"
    display_name = _("Piper Neural TTS")
    default_rate = 50

    def __init__(self):
        super().__init__()
        self.event_sink = EventSink(weakref.ref(self))
        self.event_handlers = {}
        voices = PiperTextToSpeechSystem.load_voices_from_directory(get_piper_voices_directory())
        self.tts = PiperTextToSpeechSystem(voices)
        self._bgQueue = queue.Queue()
        self._bgThread = BgThread(self._bgQueue)
        self._players = {}
        self._player = self._get_or_create_player(self.tts.speech_options.voice.config.sample_rate)

    @classmethod
    def check(self):
        return any(PiperTextToSpeechSystem.load_voices_from_directory(get_piper_voices_directory()))

    def close(self):
        super().close()
        self.event_handlers.clear()
        self.event_sink = None
        self.tts.shutdown()
        for player in self._players.values():
            self._bgQueue.put(player.close)
        self._bgQueue.put(self._players.clear)
        self._bgQueue.put(None)
        self._bgThread.join()

    def get_voices(self):
        rv = []
        for voice in self.tts.get_voices():
            voice_locale = LocaleInfo(voice.language)
            voice_quality = voice.properties["quality"]
            rv.append(
                VoiceInfo(
                    id=voice.key,
                    name=voice.name,
                    desc=f"{voice.name}, {voice_locale.english_name} ({voice_quality})",
                    language=voice_locale,
                )
            )
        return rv

    @property
    def state(self):
        return self.event_sink._state

    @property
    def voice(self):
        for voice in self.get_voices():
            if voice.id == self.tts.voice:
                return voice

    @voice.setter
    def voice(self, value):
        self.tts.voice = value.id
        sample_rate = self.tts.speech_options.voice.config.sample_rate
        self._player = self._get_or_create_player(sample_rate)

    @property
    def rate(self):
        return self.tts.rate

    @rate.setter
    def rate(self, value):
        self.tts.rate = value

    @property
    def pitch(self):
        return self.tts.pitch

    @pitch.setter
    def pitch(self, value):
        self.tts.pitch = value

    @property
    def volume(self):
        return self.tts.volume

    @volume.setter
    def volume(self, value):
        self.tts.volume = value

    def speak_utterance(self, utterance):
        self.event_sink._silence_event.clear()
        old_speech_options = self.tts.speech_options.copy()
        old_voice = None
        old_prosody = (None, None, None)
        for element in utterance:
            kind, content = element.kind, element.content
            task = None
            if kind in {SpeechElementKind.text, SpeechElementKind.sentence}:
                if not content.strip(string.punctuation + string.whitespace):
                    continue
                task = self.tts.create_speech_task(content)
            elif kind is SpeechElementKind.bookmark:
                task = self.tts.create_bookmark_task(content)
            elif kind is SpeechElementKind.pause:
                if (pause_value := PAUSE_VALUE_MAP.get(content, content)):
                    task = self.tts.create_break_task(pause_value)
            elif kind is SpeechElementKind.start_voice:
                old_voice = self.tts.voice
                self.tts.voice = content.id
            elif kind is SpeechElementKind.end_voice:
                if old_voice:
                    self.tts.voice = old_voice
            elif kind is SpeechElementKind.start_prosody:
                old_prosody = (self.tts.pitch, self.tts.rate, self.tts.volume)
                pitch, rate, volume = content
                if pitch is not None:
                    self.tts.pitch = pitch
                if (rate_value := RATE_VALUE_MAP.get(rate, rate)) is not None:
                    self.tts.rate = rate_value
                if (volume_value := VOLUME_VALUE_MAP.get(volume, volume)) is not None:
                    self.tts.volume = volume_value
            elif kind is SpeechElementKind.end_prosody:
                pitch, rate, volume = old_prosody
                if pitch is not None:
                    self.tts.pitch = pitch
                if rate is not None:
                    self.tts.rate = rate
                if volume is not None:
                    self.tts.volume = volume
            elif kind is SpeechElementKind.audio:
                self._bgQueue.put(AudioFileTask(audio_uri_to_filepath(content), self.event_sink))
                continue
            self._bgQueue.put(
                ProcessPiperTask(
                    task,
                    self._player,
                    self.event_sink
                )
            )
        self._bgQueue.put(
            DoneSpeaking(
                self._player,
                self.event_sink
            )
        )
        self.tts.speech_options = old_speech_options


    def stop(self):
        self.event_sink._silence_event.set()
        self._player.stop()
        try:
            while True:
                task = self._bgQueue.get_nowait()
                self._bgQueue.task_done()
        except queue.Empty:
            pass
        self._bgQueue.put(DoneSpeaking(self._player, self.event_sink))
        self._bgQueue.join()

    def pause(self):
        self._player.pause(True)
        self.event_sink.on_state_changed(SynthState.paused)

    def resume(self):
        self._player.pause(False)
        self.event_sink.on_state_changed(SynthState.busy)

    def bind(self, event, handler):
        if event not in (EngineEvent.bookmark_reached, EngineEvent.state_changed):
            raise NotImplementedError
        self.event_handlers.setdefault(event, []).append(handler)

    def _get_or_create_player(self, sample_rate):
        if sample_rate not in self._players:
            self._players[sample_rate] = WavePlayer(
                channels=1,
                samplesPerSec=sample_rate,
                bitsPerSample=16,
                buffered=True
            )
        return self._players[sample_rate]


def get_piper_voices_directory():
    piper_voices_path = data_path("piper", "voices")
    piper_voices_path.mkdir(parents=True, exist_ok=True)
    return piper_voices_path