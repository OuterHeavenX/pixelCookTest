class_name TitleMode
extends RefCounted
## Title screen and the game over screen.

var main
var index := 0
var t := 0.0
var over_index := 0


func _init(owner) -> void:
	main = owner


func options() -> Array:
	return ["New Game", "Continue"] if Gs.has_save() else ["New Game"]


func update(dt: float) -> void:
	t += dt
	var count := options().size()
	if Inp.nav("up", dt):
		index = (index + count - 1) % count
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		index = (index + 1) % count
		Snd.sfx("cursor")
	if Inp.tap("confirm"):
		Snd.sfx("confirm")
		main.begin_game(index == 1 and Gs.has_save())


func draw(c: CanvasItem) -> void:
	for y in Art.VH:
		var k := float(y) / Art.VH
		var col := Color("#0d1030").lerp(Color("#24244e"), min(1.0, k / 0.55))
		if k > 0.55:
			col = Color("#24244e").lerp(Color("#5a3a54"), (k - 0.55) / 0.45)
		c.draw_rect(Rect2(0, y, Art.VW, 1), col)
	for i in 60:
		var x := (i * 71) % Art.VW
		var y := (i * 37) % 90
		var tw := 0.5 + 0.5 * sin(t * 2.0 + i)
		c.draw_rect(Rect2(x, y, 1, 1), Color(1, 1, 1, 0.15 + tw * 0.5))

	# Skyline of the town, silhouetted, sitting on the bottom edge - and as
	# many roofs as the view is wide, rather than the nine that happened to
	# reach the edge of a 320-pixel one.
	# Laid out from the bottom up: the key hint on the last line, the menu
	# above it, the skyline behind that. Anchoring the menu to a fixed row
	# instead put its bottom two pixels off the end of a 180-tall screen, and
	# under the hint on anything taller.
	var opts := options()
	var box_h := float(16 + opts.size() * 14)
	var box_y := Art.VH - 16.0 - box_h
	var horizon := box_y - 10.0
	c.draw_rect(Rect2(0, horizon, Art.VW, Art.VH - horizon), Color("#171a38"))
	for i in int(ceil(Art.VW / 38.0)) + 1:
		var x := i * 38 - 10
		var h := 20 + (i % 4) * 12
		c.draw_rect(Rect2(x, horizon - h, 30, h), Color("#171a38"))
		# Gable roof, drawn as vertical slices so it stays on the pixel grid.
		for dx in 38:
			var px := x - 4 + dx
			if px < 0 or px >= Art.VW:
				continue
			var k := 1.0 - absf(float(dx) - 19.0) / 19.0
			c.draw_rect(Rect2(px, horizon - h - 12.0 * k, 1, 12.0 * k + 1),
				Color("#171a38"))
	for i in int(ceil(Art.VW / 22.0)):
		c.draw_rect(Rect2(10 + i * 22, horizon - 10 + (i % 3) * 6, 2, 3),
			Color(0.96, 0.89, 0.66, 0.9))

	Art.draw_text_big(c, "RIVENBROOK", Vector2(Art.VW / 2.0, 26), Color("#f6e2a8"), 3, "center")
	Art.draw_text(c, "a tale of the thornwilds", Vector2(Art.VW / 2.0, 60),
		Color("#c8cdf0"), "center")

	var lineup := ["aldric_right0", "lyra_right0", "mira_right0"]
	for i in lineup.size():
		Art.spr_foot(c, lineup[i], Vector2(Art.VW / 2.0 - 20 + i * 24, horizon + 16),
			Art.scale_for(lineup[i], 48.0))

	Art.draw_window(c, Rect2(Art.VW / 2.0 - 52, box_y, 104, box_h))
	for i in opts.size():
		var y := box_y + 7 + i * 14
		Art.draw_text(c, opts[i], Vector2(Art.VW / 2.0 - 22, y),
			Color("#ffe9a0") if i == index else Color("#f2f4ff"))
		if i == index:
			Art.draw_cursor(c, Vector2(Art.VW / 2.0 - 36, y - 1), t)
	Art.draw_text(c, "Arrows move   Z confirm   X cancel   C menu",
		Vector2(Art.VW / 2.0, Art.VH - 8), Color("#8f97c0"), "center")


# --- game over --------------------------------------------------------------

func over_options() -> Array:
	return ["Load Journal", "Title Screen"] if Gs.has_save() else ["Title Screen"]


func update_over(dt: float) -> void:
	t += dt
	var count := over_options().size()
	if Inp.nav("up", dt):
		over_index = (over_index + count - 1) % count
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		over_index = (over_index + 1) % count
		Snd.sfx("cursor")
	if Inp.tap("confirm"):
		Snd.sfx("confirm")
		main.resolve_game_over(over_index == 0 and Gs.has_save())


func draw_over(c: CanvasItem) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color("#140810"))
	c.draw_rect(Rect2(0, 60, Art.VW, 60), Color(0.47, 0.08, 0.16, 0.25))
	Art.draw_text_big(c, "GAME OVER", Vector2(Art.VW / 2.0, 44), Color("#e07a8a"), 3, "center")
	Art.draw_text(c, "The Thornwilds claim another party.",
		Vector2(Art.VW / 2.0, 84), Color("#a8899a"), "center")
	var opts := over_options()
	Art.draw_window(c, Rect2(Art.VW / 2.0 - 56, 108, 112, 16 + opts.size() * 14), "red")
	for i in opts.size():
		var y := 115 + i * 14
		Art.draw_text(c, opts[i], Vector2(Art.VW / 2.0 - 26, y),
			Color("#ffe9a0") if i == over_index else Color("#f2f4ff"))
		if i == over_index:
			Art.draw_cursor(c, Vector2(Art.VW / 2.0 - 40, y - 1), t)
