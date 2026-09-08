extends Node
## Sprite atlas, bitmap font, and the menu chrome.
##
## Everything the game draws comes from assets/atlas.png (cooked by
## tools/spritecook.py). The 5x7 font is rebuilt into a white glyph sheet at
## startup and tinted per draw, so text can be any colour without extra art.

const VW := 320
const VH := 180
const TILE := 16
const GLYPH_W := 6
const GLYPH_H := 8
const FONT_W := 5
const FONT_ROWS := 7

var atlas: Texture2D
var frames := {}

var _glyph_sheet: ImageTexture
var _glyph_index := {}

const INK := Color("#12101c")
const PAPER := Color("#f4f4ec")


func _ready() -> void:
	atlas = load("res://assets/atlas.png")
	if atlas == null:
		push_error("assets/atlas.png did not load (run python3 tools/godotcook.py)")
	var meta = JSON.parse_string(FileAccess.get_file_as_string("res://assets/atlas.json"))
	if typeof(meta) == TYPE_DICTIONARY:
		frames = meta.get("frames", {})
	_build_font()


func _build_font() -> void:
	var font = JSON.parse_string(FileAccess.get_file_as_string("res://assets/font.json"))
	if typeof(font) != TYPE_DICTIONARY:
		push_error("assets/font.json did not load")
		return
	var keys := (font as Dictionary).keys()
	keys.sort()
	var img := Image.create(GLYPH_W * keys.size(), GLYPH_H, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for i in keys.size():
		var ch: String = keys[i]
		_glyph_index[ch] = i
		var rows: Array = font[ch]
		for y in FONT_ROWS:
			var row: String = rows[y]
			for x in FONT_W:
				if row[x] == "1":
					img.set_pixel(i * GLYPH_W + x, y, Color(1, 1, 1, 1))
	_glyph_sheet = ImageTexture.create_from_image(img)


# --- sprites ----------------------------------------------------------------

func frame_size(sprite_name: String) -> Vector2:
	if not frames.has(sprite_name):
		return Vector2.ZERO
	var f: Array = frames[sprite_name]
	return Vector2(f[2], f[3])


func spr(c: CanvasItem, sprite_name: String, pos: Vector2, scale := 1.0,
		modulate := Color.WHITE) -> void:
	if not frames.has(sprite_name):
		return
	var f: Array = frames[sprite_name]
	var src := Rect2(f[0], f[1], f[2], f[3])
	var dst := Rect2(round(pos.x), round(pos.y), f[2] * scale, f[3] * scale)
	c.draw_texture_rect_region(atlas, dst, src, modulate)


## Sprites are not all one size any more - procedural characters are 16x24 and
## generated ones 24x32 - so everything anchors on the feet rather than on a
## hardcoded top-left offset.
func spr_foot(c: CanvasItem, sprite_name: String, foot: Vector2, scale := 1.0,
		modulate := Color.WHITE) -> void:
	var size := frame_size(sprite_name)
	if size == Vector2.ZERO:
		return
	spr(c, sprite_name, Vector2(foot.x - size.x * scale / 2.0, foot.y - size.y * scale),
		scale, modulate)


## Pick the crispest whole-ish zoom that lands near a target height.
func scale_for(sprite_name: String, target_h: float) -> float:
	var size := frame_size(sprite_name)
	if size.y <= 0.0:
		return 1.0
	var best := 1.0
	var best_err := INF
	for s in [1.0, 1.5, 2.0, 3.0]:
		var err: float = abs(size.y * s - target_h)
		if err < best_err:
			best_err = err
			best = s
	return best


# --- text -------------------------------------------------------------------

func text_width(s: String) -> int:
	return s.length() * GLYPH_W


func draw_text(c: CanvasItem, s: String, pos: Vector2, color := PAPER,
		align := "left", shadow := true) -> void:
	var x := round(pos.x)
	var y := round(pos.y)
	var w := text_width(s)
	if align == "center":
		x -= round(w / 2.0)
	elif align == "right":
		x -= w
	if shadow:
		_blit_text(c, s, x + 1, y + 1, INK)
	_blit_text(c, s, x, y, color)


func _blit_text(c: CanvasItem, s: String, x: float, y: float, color: Color) -> void:
	for i in s.length():
		var ch := s[i]
		if not _glyph_index.has(ch):
			continue
		var idx: int = _glyph_index[ch]
		c.draw_texture_rect_region(_glyph_sheet,
			Rect2(x + i * GLYPH_W, y, GLYPH_W, GLYPH_H),
			Rect2(idx * GLYPH_W, 0, GLYPH_W, GLYPH_H), color)


func draw_text_big(c: CanvasItem, s: String, pos: Vector2, color: Color,
		scale: int, align := "left") -> void:
	var x := pos.x
	if align == "center":
		x -= text_width(s) * scale / 2.0
	for pass_i in 2:
		var col := INK if pass_i == 0 else color
		var off := float(scale) if pass_i == 0 else 0.0
		for i in s.length():
			var ch := s[i]
			if not _glyph_index.has(ch):
				continue
			var idx: int = _glyph_index[ch]
			c.draw_texture_rect_region(_glyph_sheet,
				Rect2(round(x + i * GLYPH_W * scale + off), round(pos.y + off),
					GLYPH_W * scale, GLYPH_H * scale),
				Rect2(idx * GLYPH_W, 0, GLYPH_W, GLYPH_H), col)


func wrap_text(s: String, max_chars: int) -> Array:
	var lines := []
	var line := ""
	for word in s.split(" "):
		if line != "" and (line + " " + word).length() > max_chars:
			lines.append(line)
			line = word
		else:
			line = word if line == "" else line + " " + word
	if line != "":
		lines.append(line)
	return lines


# --- windows ----------------------------------------------------------------

## Beveled navy panel with a bright inner rule: the 16-bit menu look. The
## gradient is painted as one-pixel bands because draw_rect takes a flat colour.
func draw_window(c: CanvasItem, rect: Rect2, tone := "blue") -> void:
	var x := round(rect.position.x)
	var y := round(rect.position.y)
	var w := round(rect.size.x)
	var h := round(rect.size.y)
	var top := Color("#2c47a8")
	var bottom := Color("#111a4e")
	if tone == "dark":
		top = Color("#241f38")
		bottom = Color("#12101f")
	elif tone == "red":
		top = Color("#7a2b3c")
		bottom = Color("#3a1120")

	c.draw_rect(Rect2(x + 1, y, w - 2, h), Color("#0b0a16"))
	c.draw_rect(Rect2(x, y + 1, w, h - 2), Color("#0b0a16"))
	for i in int(h) - 2:
		var t := float(i) / max(1.0, h - 3.0)
		var band := top.lerp(bottom, t)
		c.draw_rect(Rect2(x + 2, y + 1 + i, w - 4, 1), band)
		if i >= 1 and i <= h - 4:
			c.draw_rect(Rect2(x + 1, y + 1 + i, 1, 1), band)
			c.draw_rect(Rect2(x + w - 2, y + 1 + i, 1, 1), band)

	var frame := Color("#9db4ea")
	c.draw_rect(Rect2(x + 2, y + 1, w - 4, 1), frame)
	c.draw_rect(Rect2(x + 2, y + h - 2, w - 4, 1), frame)
	c.draw_rect(Rect2(x + 1, y + 2, 1, h - 4), frame)
	c.draw_rect(Rect2(x + w - 2, y + 2, 1, h - 4), frame)
	var corner := Color("#e8eeff")
	c.draw_rect(Rect2(x + 2, y + 1, 2, 1), corner)
	c.draw_rect(Rect2(x + w - 4, y + 1, 2, 1), corner)
	c.draw_rect(Rect2(x + 1, y + 2, 1, 2), corner)
	c.draw_rect(Rect2(x + w - 2, y + 2, 1, 2), corner)
	c.draw_rect(Rect2(x + 3, y + 3, w - 6, 1), Color("#4d63b4"))


func draw_cursor(c: CanvasItem, pos: Vector2, t: float) -> void:
	var bob := 1.0 if sin(t * 8.0) > 0.0 else 0.0
	var x := round(pos.x + bob)
	var y := round(pos.y)
	_triangle(c, x - 1, y - 1, 11, Color("#241b26"))
	_triangle(c, x, y, 9, Color("#e0a83c"))
	c.draw_rect(Rect2(x, y + 1, 3, 1), Color("#ffeda8"))
	c.draw_rect(Rect2(x, y + 2, 2, 1), Color("#ffeda8"))
	c.draw_rect(Rect2(x, y + 3, 4, 1), Color("#ffeda8"))


func _triangle(c: CanvasItem, x: float, y: float, h: int, color: Color) -> void:
	var half := (h - 1) / 2.0
	for i in h:
		var w := round(half + 1.0 - abs(i - half))
		c.draw_rect(Rect2(x, y + i, w, 1), color)


func draw_bar(c: CanvasItem, pos: Vector2, size: Vector2, pct: float,
		top_color: Color, body: Color) -> void:
	pct = clamp(pct, 0.0, 1.0)
	c.draw_rect(Rect2(pos.x - 1, pos.y - 1, size.x + 2, size.y + 2), Color("#0b0a16"))
	c.draw_rect(Rect2(pos, size), Color("#2a2a44"))
	var fill := round(size.x * pct)
	if fill > 0:
		c.draw_rect(Rect2(pos.x, pos.y, fill, size.y), body)
		c.draw_rect(Rect2(pos.x, pos.y, fill, 1), top_color)


## A squashed ellipse, drawn as scanlines so it stays on the pixel grid.
func draw_shadow(c: CanvasItem, center: Vector2, r: float) -> void:
	var ry := max(1.0, round(r * 0.45))
	var color := Color(0.04, 0.03, 0.08, 0.32)
	for i in range(-int(ry), int(ry) + 1):
		var k := 1.0 - pow(float(i) / ry, 2.0)
		if k <= 0.0:
			continue
		var w := round(r * sqrt(k))
		c.draw_rect(Rect2(round(center.x) - w, round(center.y) + i, w * 2.0, 1), color)
