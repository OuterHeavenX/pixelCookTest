class_name EndingMode
extends RefCounted
## The close of chapter one: staged text over a scene, a card with what the
## party walked out with, credits, and the hook.
##
## The journal is already saved by the time this starts, so nothing here can
## cost the player their game.

var main
var which := "one"
var phase := "beats"
var beat := 0
var chars := 0.0
var t := 0.0
var scroll := 0.0


func _init(owner) -> void:
	main = owner


func open(chapter := "one") -> void:
	which = chapter
	phase = "beats"
	beat = 0
	chars = 0.0
	t = 0.0
	scroll = 0.0
	Snd.play("barrow")


## Which chapter is closing. The game has more than one now, so the ending is
## keyed like everything else rather than being the only one there is.
func ending() -> Dictionary:
	return Dat.endings.get(which, Dat.endings.get("one", {}))


## The beats this party earned: a beat with `when` needs those flags, one
## with `absent` needs them unset, so the close can say what you did.
func beats() -> Array:
	var out := []
	for b in ending().get("beats", []):
		var ok := true
		for f in b.get("when", []):
			if not bool(Gs.flags.get(f, false)):
				ok = false
		for f in b.get("absent", []):
			if bool(Gs.flags.get(f, false)):
				ok = false
		if ok:
			out.append(b)
	return out


func current() -> Dictionary:
	var list := beats()
	if list.is_empty():
		return {"scene": "barrow", "lines": []}
	return list[mini(beat, list.size() - 1)]


func _typed_length(lines: Array) -> int:
	var n := 0
	for line in lines:
		n += (line as String).length()
	return n


func update(dt: float) -> void:
	t += dt
	match phase:
		"beats":
			_update_beats(dt)
		"card":
			if t > 0.6 and Inp.tap("confirm"):
				phase = "credits"
				scroll = 0.0
				Snd.sfx("confirm")
		"credits":
			scroll += dt * 16.0
			if Inp.held("confirm"):
				scroll += dt * 70.0
			if scroll > ending().get("credits", []).size() * 14.0 + 40.0:
				phase = "hook"
				t = 0.0
		_:
			if t > 1.0 and (Inp.tap("confirm") or Inp.tap("cancel")):
				Snd.sfx("confirm")
				main.fade_to(func() -> void:
					main.mode = "title"
					main.title.index = 0
					Snd.stop())


func _update_beats(dt: float) -> void:
	var lines: Array = current()["lines"]
	var total := _typed_length(lines)
	if chars < total:
		chars += dt * 46.0
		if Inp.tap("confirm") or Inp.tap("cancel"):
			chars = total
		return
	if Inp.tap("confirm") or Inp.tap("cancel"):
		beat += 1
		chars = 0.0
		Snd.sfx("cursor")
		if beat >= beats().size():
			phase = "card"
			t = 0.0


func draw(c: CanvasItem) -> void:
	var beat_now := current()
	var scene := str(beat_now.get("scene", ""))
	var night: bool = phase != "beats" or scene != "town"
	Art.spr(c, "bg_night" if night else "bg_dusk", Vector2.ZERO)
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH),
		Color(0.03, 0.02, 0.07, 0.55 if night else 0.35))
	c.draw_rect(Rect2(0, 116, Art.VW, Art.VH - 116), Color("#0b0a16"))

	match phase:
		"beats":
			_draw_beats(c, beat_now)
		"card":
			_draw_card(c)
		"credits":
			_draw_credits(c)
		_:
			_draw_hook(c)


func _draw_beats(c: CanvasItem, beat_now: Dictionary) -> void:
	if str(beat_now.get("scene", "")) == "rift":
		# A shaft of light, drawn as stacked bars that narrow and fade. A
		# gradient in a rectangle gave it four hard corners and read as a pane
		# of glass rather than as something coming up out of the ground.
		var pulse := 0.34 + sin(t * 2.2) * 0.10
		var y := 116.0
		while y > 34.0:
			var k := (116.0 - y) / 82.0
			var w := roundf(46.0 * (1.0 - k * 0.72))
			c.draw_rect(Rect2(round(Art.VW / 2.0 - w), y, w * 2.0, 2.0),
				Color(0.50, 0.91, 0.85, pulse * (1.0 - k) * (1.0 - k)))
			y -= 2.0

	# The mere: light coming down through moving water rather than up out of a
	# floor. Thin and sparse - wide bars close together read as a grey pane
	# laid over the sky rather than as water.
	if str(beat_now.get("scene", "")) == "mere":
		var wy := 10.0
		while wy < 112.0:
			var wk := wy / 112.0
			var wob := sin(t * 1.5 + wy * 0.11) * 16.0
			var ww := 40.0 + sin(t * 0.9 + wy * 0.07) * 22.0
			c.draw_rect(Rect2(round(Art.VW / 2.0 - ww + wob), wy, round(ww * 2.0), 1.0),
				Color(0.62, 0.85, 0.91, 0.16 * (1.0 - wk * 0.7)))
			wy += 9.0

	# Hollowmere going out. The lamps darken left to right as the beat types
	# itself, so the event of the chapter happens on screen rather than only
	# in the sentence describing it.
	var scene_now := str(beat_now.get("scene", ""))
	if scene_now == "hollow" or scene_now == "road":
		var road := scene_now == "road"
		var total := float(_typed_length(beat_now["lines"]))
		var done: float = minf(1.0, chars / maxf(1.0, total))
		var n := 9 if road else 11
		for i in n:
			var lx: float = (Art.VW / 2.0 + (i - (n - 1) / 2.0) * (26.0 - i * 1.6)) \
				if road else (18.0 + i * ((Art.VW - 36.0) / (n - 1)))
			var ly: float = (62.0 + round(i * 1.6)) if road else 66.0
			var lit: bool = (i == n - 1) if road else (float(i) / n > done)
			var r: float = 3.0 if lit else 2.0
			var col := Color(1.0, 0.79, 0.42, 0.92) if lit else Color(0.29, 0.23, 0.23, 0.9)
			c.draw_rect(Rect2(round(lx - r), ly - r, r * 2.0, r * 2.0), col)
			if lit:
				c.draw_rect(Rect2(round(lx - r * 3.0), ly - r * 3.0, r * 6.0, r * 6.0),
					Color(1.0, 0.79, 0.42, 0.18))

	var budget := chars
	var lines: Array = beat_now["lines"]
	for i in lines.size():
		var line: String = lines[i]
		var shown: String = line.substr(0, maxi(0, int(budget)))
		budget -= line.length()
		Art.draw_text(c, shown, Vector2(20, 128 + i * 14), Color("#f2ecd8"))
	if chars >= _typed_length(lines) and sin(t * 5.0) > 0.0:
		Art.draw_text(c, ">", Vector2(Art.VW - 20, 166), Color("#9aa4c8"), "right")


func _draw_card(c: CanvasItem) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(0.03, 0.02, 0.07, 0.72))
	Art.draw_text_big(c, str(ending().get("title", "")), Vector2(Art.VW / 2.0, 20),
		Color("#f6e2a8"), 2, "center")
	Art.draw_text(c, str(ending().get("subtitle", "")), Vector2(Art.VW / 2.0, 42),
		Color("#c8b9e8"), "center")
	Art.draw_window(c, Rect2(40, 58, Art.VW - 80, 74), "dark")
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var y := 66 + i * 14
		Art.draw_text(c, h["name"], Vector2(52, y), Color("#f2f4ff"))
		Art.draw_text(c, h["title"], Vector2(116, y), Color("#8f97c0"))
		Art.draw_text(c, "Lv %d" % int(h["lv"]), Vector2(Art.VW - 52, y),
			Color("#ffe9a0"), "right")
	Art.draw_text(c, "Time", Vector2(52, 112), Color("#8f97c0"))
	Art.draw_text(c, Gs.format_time(Gs.playtime), Vector2(150, 112), Color("#f2f4ff"), "right")
	Art.draw_text(c, "Gil", Vector2(168, 112), Color("#8f97c0"))
	Art.draw_text(c, str(Gs.gil), Vector2(Art.VW - 52, 112), Color("#f6e2a8"), "right")
	Art.draw_text(c, "[Z]", Vector2(Art.VW / 2.0, 150), Color("#7a82a8"), "center")


func _draw_credits(c: CanvasItem) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color("#0b0a16"))
	var lines: Array = ending().get("credits", [])
	for i in lines.size():
		var y := roundf(Art.VH + 6 + i * 14 - scroll)
		if y < -14 or y > Art.VH:
			continue
		Art.draw_text(c, lines[i], Vector2(Art.VW / 2.0, y),
			Color("#f6e2a8") if i < 2 else Color("#c2c8e8"), "center")


func _draw_hook(c: CanvasItem) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color("#0b0a16"))
	Art.draw_text_big(c, "TO BE CONTINUED", Vector2(Art.VW / 2.0, 62),
		Color("#f2ecd8"), 2, "center")
	Art.draw_text(c, str(ending().get("hook", "")), Vector2(Art.VW / 2.0, 96),
		Color("#8fd8c8"), "center")
	if t > 1.0 and sin(t * 3.0) > 0.0:
		Art.draw_text(c, "[Z]", Vector2(Art.VW / 2.0, 130), Color("#7a82a8"), "center")
