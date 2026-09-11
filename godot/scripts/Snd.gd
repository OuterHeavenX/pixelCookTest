extends Node
## A tiny chip synth: square-wave sound effects and six looping themes,
## all generated into AudioStreamWAV buffers at runtime so the project ships
## no audio files.

const RATE := 22050
const SFX_VOICES := 6

var muted := false

var _sfx_players: Array = []
var _next_voice := 0
var _music_player: AudioStreamPlayer
var _music_cache := {}
var _track := ""

## The note tables live in the data (datacook THEMES), so both engines play
## the same tunes. Three voices: the tune on a triangle wave, a bass under it,
## and a quiet harmony in the middle, all soft enough to sit under an hour of
## play.
func _themes() -> Dictionary:
	return Dat.themes


func _ready() -> void:
	for i in SFX_VOICES:
		var p := AudioStreamPlayer.new()
		p.volume_db = -8.0
		add_child(p)
		_sfx_players.append(p)
	_music_player = AudioStreamPlayer.new()
	_music_player.volume_db = -16.0
	add_child(_music_player)


# --- synthesis --------------------------------------------------------------

func _wave(kind: String, phase: float) -> float:
	match kind:
		"square":
			return 1.0 if phase < 0.5 else -1.0
		"triangle":
			return 4.0 * abs(phase - 0.5) - 1.0
		"saw":
			return phase * 2.0 - 1.0
		_:
			return sin(phase * TAU)


## One note rendered into an existing 16-bit buffer, mixed additively.
func _render_note(data: PackedByteArray, start: int, count: int, freq: float,
		kind: String, volume: float, decay := true) -> void:
	if freq <= 0.0:
		return
	for i in count:
		var idx := start + i
		if idx * 2 + 1 >= data.size():
			return
		var t := float(i) / RATE
		var env := 1.0
		if decay:
			env = clamp(1.0 - float(i) / float(count), 0.0, 1.0)
			env = env * env
		var attack: float = min(1.0, float(i) / 80.0)
		var phase: float = fmod(t * freq, 1.0)
		var sample: float = _wave(kind, phase) * env * attack * volume
		var mixed: float = clamp(float(data.decode_s16(idx * 2)) / 32767.0 + sample, -1.0, 1.0)
		data.encode_s16(idx * 2, int(mixed * 32767.0))


func _make_stream(samples: int, loop: bool) -> AudioStreamWAV:
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = RATE
	w.stereo = false
	if loop:
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_begin = 0
		w.loop_end = samples
	return w


func _tone(freq: float, dur: float, kind := "square", volume := 0.5) -> AudioStreamWAV:
	var count := int(dur * RATE)
	var data := PackedByteArray()
	data.resize(count * 2)
	data.fill(0)
	_render_note(data, 0, count, freq, kind, volume)
	var w := _make_stream(count, false)
	w.data = data
	return w


## A short arpeggio or sweep built from a list of [freq, duration, kind] steps.
func _sequence(steps: Array, volume := 0.45) -> AudioStreamWAV:
	var total := 0
	for s in steps:
		total += int(float(s[1]) * RATE)
	var data := PackedByteArray()
	data.resize(max(2, total * 2))
	data.fill(0)
	var cursor := 0
	for s in steps:
		var count := int(float(s[1]) * RATE)
		_render_note(data, cursor, count, float(s[0]), s[2], volume)
		cursor += count
	var w := _make_stream(total, false)
	w.data = data
	return w


# --- effects ----------------------------------------------------------------

var _sfx_cache := {}

func _sfx_stream(name: String) -> AudioStreamWAV:
	if _sfx_cache.has(name):
		return _sfx_cache[name]
	var s: AudioStreamWAV
	match name:
		"cursor": s = _tone(660, 0.05, "square", 0.35)
		"confirm": s = _sequence([[880, 0.05, "square"], [1320, 0.07, "square"]])
		"cancel": s = _tone(300, 0.08, "square", 0.4)
		"hit": s = _sequence([[420, 0.05, "square"], [220, 0.05, "square"], [110, 0.05, "square"]], 0.6)
		"crit": s = _sequence([[700, 0.06, "saw"], [400, 0.06, "saw"], [150, 0.08, "saw"]], 0.6)
		"magic": s = _sequence([[300, 0.06, "triangle"], [600, 0.06, "triangle"],
			[900, 0.06, "triangle"], [1400, 0.08, "triangle"]], 0.5)
		"heal": s = _sequence([[660, 0.07, "triangle"], [880, 0.07, "triangle"],
			[1100, 0.07, "triangle"], [1320, 0.1, "triangle"]], 0.5)
		"ko": s = _sequence([[400, 0.1, "saw"], [260, 0.12, "saw"], [120, 0.2, "saw"]], 0.55)
		"item": s = _sequence([[990, 0.05, "triangle"], [1480, 0.09, "triangle"]], 0.5)
		"encounter": s = _sequence([[880, 0.06, "square"], [0, 0.03, "square"],
			[880, 0.06, "square"], [0, 0.03, "square"], [1200, 0.12, "square"]], 0.55)
		"victory": s = _sequence([[523, 0.14, "square"], [659, 0.14, "square"],
			[784, 0.14, "square"], [1047, 0.3, "square"]], 0.5)
		"levelup": s = _sequence([[784, 0.1, "triangle"], [988, 0.1, "triangle"],
			[1175, 0.1, "triangle"], [1568, 0.26, "triangle"]], 0.5)
		_: s = _tone(440, 0.05)
	_sfx_cache[name] = s
	return s


func sfx(name: String) -> void:
	if muted:
		return
	var p: AudioStreamPlayer = _sfx_players[_next_voice]
	_next_voice = (_next_voice + 1) % _sfx_players.size()
	p.stream = _sfx_stream(name)
	p.play()


# --- music ------------------------------------------------------------------

func _build_theme(name: String) -> AudioStreamWAV:
	var theme: Dictionary = _themes()[name]
	var step_samples := int(60.0 / float(theme["bpm"]) * RATE)
	var lead: Array = theme["lead"]
	var bass: Array = theme.get("bass", [])
	var harm: Array = theme.get("harm", [])
	var total := step_samples * lead.size()
	var data := PackedByteArray()
	data.resize(total * 2)
	data.fill(0)
	for i in lead.size():
		var at := i * step_samples
		_render_note(data, at, mini(step_samples * 2, total - at), float(lead[i]), "triangle", 0.26)
		if not bass.is_empty():
			_render_note(data, at, mini(step_samples * 3, total - at), float(bass[i % bass.size()]), "triangle", 0.24)
		if not harm.is_empty():
			_render_note(data, at, mini(step_samples * 4, total - at), float(harm[i % harm.size()]), "sine", 0.14)
	var w := _make_stream(total, true)
	w.data = data
	return w


func play(name: String) -> void:
	if _track == name:
		return
	_track = name
	if not _themes().has(name):
		_music_player.stop()
		return
	if not _music_cache.has(name):
		_music_cache[name] = _build_theme(name)
	_music_player.stream = _music_cache[name]
	if not muted:
		_music_player.play()


func stop() -> void:
	_track = ""
	_music_player.stop()


func toggle_mute() -> bool:
	muted = not muted
	if muted:
		_music_player.stop()
	elif _music_player.stream != null:
		_music_player.play()
	return muted
