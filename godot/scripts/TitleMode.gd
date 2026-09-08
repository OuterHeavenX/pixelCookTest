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

	# Skyline of the town, silhouetted.
	c.draw_rect(Rect2(0, 128, Art.VW, Art.VH - 128), Color("#171a38"))
	for i in 9:
		var x := i * 38 - 10
		var h := 20 + (i % 4) * 12
		c.draw_rect(Rect2(x, 128 - h, 30, h), Color("#171a38"))
		# Gable roof, drawn as vertical slices so it stays on the pixel grid.
		for dx in 38:
			var px := x - 4 + dx
			if px < 0 or px >= Art.VW:
				continue
			var k := 1.0 - abs(float(dx) - 19.0) / 19.0
			c.draw_rect(Rect2(px, 128 - h - 12.0 * k, 1, 12.0 * k + 1), Color("#171a38"))
	for i in 14:
		c.draw_rect(Rect2(10 + i * 22, 118 + (i % 3) * 6, 2, 3), Color(0.96, 0.89, 0.66, 0.9))

	Art.draw_text_big(c, "RIVENBROOK", Vector2(Art.VW / 2.0, 26), Color("#f6e2a8"), 3, "center")
	Art.draw_text(c, "a tale of the thornwilds", Vector2(Art.VW / 2.0, 60),
		Color("#c8cdf0"), "center")

	Art.spr(c, "aldric_right0", Vector2(128, 96), 2.0)
	Art.spr(c, "lyra_right0", Vector2(152, 96), 2.0)
	Art.spr(c, "mira_right0", Vector2(176, 96), 2.0)

	var opts := options()
	Art.draw_window(c, Rect2(Art.VW / 2.0 - 52, 138, 104, 16 + opts.size() * 14))
	for i in opts.size():
		var y := 145 + i * 14
		Art.draw_text(c, opts[i], Vector2(Art.VW / 2.0 - 22, y),
			Color("#ffe9a0") if i == index else Color("#f2f4ff"))
		if i == index:
			Art.draw_cursor(c, Vector2(Art.VW / 2.0 - 36, y - 1), t)
	Art.draw_text(c, "Arrows move   Z confirm   X cancel   C menu",
		Vector2(Art.VW / 2.0, Art.VH - 10), Color("#8f97c0"), "center")


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
