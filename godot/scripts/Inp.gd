extends Node
## Keyboard and edge-triggered input, mirroring the browser build's scheme.
##
## Actions are read straight off physical keycodes so the project needs no
## input map, which keeps project.godot free of hand-written resources.

const BINDINGS := {
	"up": [KEY_UP, KEY_W],
	"down": [KEY_DOWN, KEY_S],
	"left": [KEY_LEFT, KEY_A],
	"right": [KEY_RIGHT, KEY_D],
	"confirm": [KEY_Z, KEY_ENTER, KEY_SPACE],
	"cancel": [KEY_X, KEY_BACKSPACE],
	"menu": [KEY_C, KEY_ESCAPE, KEY_SHIFT],
	"mute": [KEY_M],
}

var _down := {}
var _tapped := {}
var _repeat := {}


func _ready() -> void:
	for action in BINDINGS:
		_down[action] = false
		_repeat[action] = 0.0


func _input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key == null or key.echo:
		return
	for action in BINDINGS:
		if not BINDINGS[action].has(key.physical_keycode):
			continue
		if key.pressed:
			if not _down[action]:
				_tapped[action] = true
			_down[action] = true
		else:
			_down[action] = false


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		for action in BINDINGS:
			_down[action] = false


func held(action: String) -> bool:
	return _down.get(action, false)


func tap(action: String) -> bool:
	return _tapped.get(action, false)


## Menus want one immediate step, then a repeat after a short hold.
func nav(action: String, dt: float) -> bool:
	if tap(action):
		_repeat[action] = -0.28
		return true
	if not held(action):
		_repeat[action] = 0.0
		return false
	_repeat[action] = _repeat.get(action, 0.0) + dt
	if _repeat[action] >= 0.08:
		_repeat[action] = 0.0
		return true
	return false


func end_frame() -> void:
	_tapped.clear()
