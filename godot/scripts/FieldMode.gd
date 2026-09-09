class_name FieldMode
extends RefCounted
## Overworld exploration: tile rendering, grid movement, townsfolk, dialogue,
## chests, warps and random encounters.

const TILE := 16
const DIRV := {
	"up": Vector2i(0, -1), "down": Vector2i(0, 1),
	"left": Vector2i(-1, 0), "right": Vector2i(1, 0),
}
const OPPOSITE := {"up": "down", "down": "up", "left": "right", "right": "left"}
const GRASS_VARIANTS := ["t_grass", "t_grass3", "t_grass2"]

var main                     # Main, set on construction
var map := {}
var npcs := []
var anim := 0.0
var walk_phase := 0.0
var moving := {}
var msg := {}
var banner_name := ""
var banner_timer := 0.0


func _init(owner) -> void:
	main = owner


# --- map handling -----------------------------------------------------------

func enter_map(id: String, tx: int, ty: int, facing := "") -> void:
	map = Dat.maps[id]
	Gs.map_id = id
	Gs.px = tx
	Gs.py = ty
	if facing != "":
		Gs.dir = facing
	moving = {}
	msg = {}
	walk_phase = 0.0
	npcs = []
	for n in Dat.npcs.get(id, []):
		var spot := nearest_free(int(n["x"]), int(n["y"]))
		var npc := {
			"tx": spot.x, "ty": spot.y, "ox": 0.0, "oy": 0.0, "phase": 0.0,
			"cool": randf_range(1.0, 4.0), "move": {}, "boss": false,
			"sprite": n["sprite"], "dir": n["dir"], "name": n["name"],
			"wander": bool(n.get("wander", false)), "lines": n["lines"],
			"service": n.get("service", ""),
		}
		npcs.append(npc)
	if id == "wild" and not bool(Gs.flags.get("boss_down", false)) and map.has("boss"):
		npcs.append({
			"tx": int(map["boss"]["x"]), "ty": int(map["boss"]["y"]),
			"ox": 0.0, "oy": 0.0, "phase": 0.0, "cool": 999.0, "move": {},
			"boss": true, "sprite": "e_ogre", "dir": "down",
			"name": "Ogre Chieftain", "wander": false, "lines": [], "service": "",
		})
	Gs.steps_to_encounter = roll_encounter_countdown()
	Snd.play(map.get("music", "field"))


func roll_encounter_countdown() -> int:
	var e := int(map.get("encounter", 0))
	if e <= 0:
		return 1 << 30
	return randi_range(int(e * 0.5), int(e * 1.6))


func tile_at(x: int, y: int) -> String:
	if x < 0 or y < 0 or y >= int(map["h"]) or x >= int(map["w"]):
		return ""
	return (map["rows"][y] as String)[x]


func solid_at(x: int, y: int) -> bool:
	var ch := tile_at(x, y)
	if ch == "" or not Dat.legend.has(ch):
		return true
	return int(Dat.legend[ch][1]) != 0


func npc_at(x: int, y: int):
	for n in npcs:
		if n["tx"] == x and n["ty"] == y:
			return n
	return null


func warp_at(x: int, y: int):
	for w in map.get("warps", []):
		if int(w["x"]) == x and int(w["y"]) == y:
			return w
	return null


## Scenery is scattered procedurally, so an authored NPC tile can end up under
## a tree. Walk outwards until we find somewhere it can actually stand.
func nearest_free(x: int, y: int) -> Vector2i:
	if not solid_at(x, y):
		return Vector2i(x, y)
	for r in range(1, 6):
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				if abs(dx) != r and abs(dy) != r:
					continue
				if not solid_at(x + dx, y + dy):
					return Vector2i(x + dx, y + dy)
	return Vector2i(x, y)


# --- movement ---------------------------------------------------------------

## Diagonals face along the horizontal, which reads better than up/down.
func facing_for(dx: int, dy: int) -> String:
	if dx < 0:
		return "left"
	if dx > 0:
		return "right"
	return "up" if dy < 0 else "down"


func blocked(x: int, y: int) -> bool:
	return solid_at(x, y) or npc_at(x, y) != null


func try_step(dx: int, dy: int) -> bool:
	var nx := Gs.px + dx
	var ny := Gs.py + dy
	Gs.dir = facing_for(dx, dy)
	if blocked(nx, ny):
		return false
	# A diagonal may not cut a corner: both orthogonal neighbours must be clear,
	# otherwise the sprite visibly clips the corner of a wall.
	if dx != 0 and dy != 0:
		if blocked(Gs.px + dx, Gs.py) or blocked(Gs.px, Gs.py + dy):
			return false
	# Scale the step so a diagonal is not a free speed boost.
	var span := sqrt(2.0) if dx != 0 and dy != 0 else 1.0
	moving = {"fx": Gs.px, "fy": Gs.py, "tx": nx, "ty": ny, "t": 0.0, "dur": 0.155 * span}
	return true


func on_step_complete() -> void:
	Gs.steps += 1
	var w = warp_at(Gs.px, Gs.py)
	if w != null:
		do_warp(w)
		return
	for n in npcs:
		if n["boss"] and abs(n["tx"] - Gs.px) + abs(n["ty"] - Gs.py) <= 1:
			challenge_boss()
			return
	if int(map.get("encounter", 0)) > 0:
		Gs.steps_to_encounter -= 1
		if Gs.steps_to_encounter <= 0:
			Gs.steps_to_encounter = roll_encounter_countdown()
			main.start_encounter(Dat.roll_encounter(), false)


func do_warp(w: Dictionary) -> void:
	var to: String = w["to"]
	var tx := int(w["tx"])
	var ty := int(w["ty"])
	var facing: String = w.get("dir", Gs.dir)
	var arrive := func() -> void:
		enter_map(to, tx, ty, facing)
		if to == "wild" and not bool(Gs.flags.get("visited_wild", false)):
			Gs.flags["visited_wild"] = true
			msg = make_message(["THE THORNWILDS",
				"Monsters roam the grass. Press [C] for your journal."])
	main.fade_to(arrive)


# --- talking ----------------------------------------------------------------

func make_message(lines: Array, speaker := "", choice := {}) -> Dictionary:
	return {"lines": lines.duplicate(), "page": 0, "chars": 0.0,
		"speaker": speaker, "choice": choice, "on_close": null}


func fill_tokens(line: String) -> String:
	return line.replace("{name}", Gs.party[0]["name"]) \
		.replace("{menu}", "[C]").replace("{cancel}", "[X]").replace("{confirm}", "[Z]")


func interact() -> void:
	var d: Vector2i = DIRV[Gs.dir]
	var tx := Gs.px + d.x
	var ty := Gs.py + d.y
	var npc = npc_at(tx, ty)
	if npc != null:
		if npc["boss"]:
			challenge_boss()
			return
		npc["dir"] = OPPOSITE[Gs.dir]
		npc["cool"] = 3.0
		if npc["service"] == "inn":
			open_inn(npc)
			return
		if npc["service"] == "shop":
			main.open_shop()
			return
		var lines := []
		for l in npc["lines"]:
			lines.append(fill_tokens(l))
		msg = make_message(lines, npc["name"])
		Snd.sfx("confirm")
		return

	var ch := tile_at(tx, ty)
	if not Dat.legend.has(ch):
		return
	var entry: Array = Dat.legend[ch]
	var tag: String = str(entry[2]) if entry.size() > 2 else ""
	match tag:
		"sign":
			msg = make_message([Dat.sign_text.get(Gs.map_id, "The paint has weathered away.")])
		"chest":
			open_chest(tx, ty)
		"well":
			msg = make_message(["The well is cold and deep. Coins glint at the bottom."])
		"bed":
			msg = make_message(["A made bed with a wool blanket. Speak to the innkeeper to rest."])
		"lamp":
			msg = make_message(["A lantern burns low against the dark."])
		"water":
			msg = make_message(["Clear water. Too deep to wade."])
	if not msg.is_empty():
		Snd.sfx("confirm")


func open_chest(tx: int, ty: int) -> void:
	var key := "%s:%d,%d" % [Gs.map_id, tx, ty]
	var opened: Dictionary = Gs.flags["chests"]
	if opened.has(key):
		msg = make_message(["The chest is empty."])
		return
	opened[key] = true
	var loot: Dictionary = Dat.chest_loot.get(key, {"gil": 50})
	var line := ""
	if loot.has("gil"):
		Gs.gil += int(loot["gil"])
		line = "Found %d gil!" % int(loot["gil"])
	else:
		Gs.take_item(loot["item"], int(loot["n"]))
		line = "Found %s x%d!" % [Dat.items[loot["item"]]["name"], int(loot["n"])]
	Snd.sfx("item")
	msg = make_message([line])


func challenge_boss() -> void:
	Snd.sfx("cancel")
	var on_pick := func(idx: int) -> void:
		if idx == 0:
			Snd.sfx("encounter")
			main.start_encounter(["ogre"], true)
		else:
			Gs.py = clampi(Gs.py - 2, 0, int(map["h"]) - 1)
			Gs.dir = "up"
	var choice := {"options": ["Fight", "Back away"], "index": 0, "on_pick": on_pick}
	msg = make_message([
		"The Ogre Chieftain hauls itself off the shrine stones.",
		"There will be no fleeing from this one. Stand and fight?",
	], "Ogre Chieftain", choice)


func open_inn(npc: Dictionary) -> void:
	var dead := Gs.party.size() != Gs.living_heroes().size()
	var extra := " Your fallen will wake, too." if dead else ""
	var keeper: String = npc["name"]
	var on_pick := func(idx: int) -> void:
		if idx != 0:
			msg = make_message(["Mind how you go, then."], keeper)
			return
		if Gs.gil < Dat.inn_cost:
			Snd.sfx("cancel")
			msg = make_message(["You are short on coin. Come back richer."], keeper)
			return
		Gs.gil -= Dat.inn_cost
		for h in Gs.party:
			h["alive"] = true
			h["hp"] = h["maxhp"]
			h["mp"] = h["maxmp"]
		Snd.sfx("heal")
		msg = make_message(["You sleep until the lanterns burn low.",
			"The party is fully restored!"])
	var choice := {"options": ["Yes", "No"], "index": 0, "on_pick": on_pick}
	msg = make_message([
		"Welcome to the Amber Lantern.",
		"A bed and a hot meal, %d gil.%s Rest here?" % [Dat.inn_cost, extra],
	], keeper, choice)
	Snd.sfx("confirm")


# --- update -----------------------------------------------------------------

func update(dt: float) -> void:
	anim += dt
	Gs.playtime += dt
	banner_timer = max(0.0, banner_timer - dt)

	if not msg.is_empty():
		update_message(dt)
		return
	if Inp.tap("menu"):
		main.open_menu()
		return
	if Inp.tap("confirm"):
		interact()
		return

	if not moving.is_empty():
		moving["t"] = float(moving["t"]) + dt
		walk_phase += dt * (11.0 if Inp.held("cancel") else 7.0)
		if float(moving["t"]) >= float(moving["dur"]):
			Gs.px = int(moving["tx"])
			Gs.py = int(moving["ty"])
			moving = {}
			on_step_complete()
			return
	else:
		var dx := 0
		var dy := 0
		if Inp.held("left"):
			dx -= 1
		if Inp.held("right"):
			dx += 1
		if Inp.held("up"):
			dy -= 1
		if Inp.held("down"):
			dy += 1
		if dx != 0 or dy != 0:
			var moved := try_step(dx, dy)
			# A blocked diagonal slides along whichever axis is still open, so
			# running into a wall at an angle does not stop the player dead.
			if not moved and dx != 0 and dy != 0:
				moved = try_step(dx, 0)
				if not moved:
					moved = try_step(0, dy)
			if moved:
				# Holding cancel dashes.
				moving["dur"] = float(moving["dur"]) * (0.62 if Inp.held("cancel") else 1.0)
			else:
				walk_phase += dt * 5.0
		else:
			walk_phase = 0.0
	update_npcs(dt)


func update_npcs(dt: float) -> void:
	for n in npcs:
		if not n["move"].is_empty():
			var mv: Dictionary = n["move"]
			mv["t"] = float(mv["t"]) + dt
			var k: float = min(1.0, float(mv["t"]) / float(mv["dur"]))
			n["ox"] = lerp(float(mv["fx"]) - n["tx"], 0.0, k)
			n["oy"] = lerp(float(mv["fy"]) - n["ty"], 0.0, k)
			n["phase"] = float(n["phase"]) + dt * 6.0
			if k >= 1.0:
				n["move"] = {}
				n["ox"] = 0.0
				n["oy"] = 0.0
				n["phase"] = 0.0
			continue
		if not n["wander"]:
			continue
		n["cool"] = float(n["cool"]) - dt
		if float(n["cool"]) > 0.0:
			continue
		n["cool"] = randf_range(1.4, 4.5)
		var facing: String = ["up", "down", "left", "right"][randi() % 4]
		var d: Vector2i = DIRV[facing]
		var nx: int = n["tx"] + d.x
		var ny: int = n["ty"] + d.y
		n["dir"] = facing
		if solid_at(nx, ny) or npc_at(nx, ny) != null or (nx == Gs.px and ny == Gs.py):
			continue
		n["move"] = {"fx": n["tx"], "fy": n["ty"], "t": 0.0, "dur": 0.28}
		n["tx"] = nx
		n["ty"] = ny


func update_message(dt: float) -> void:
	var line: String = msg["lines"][int(msg["page"])]
	if float(msg["chars"]) < line.length():
		msg["chars"] = float(msg["chars"]) + dt * 90.0
		if Inp.tap("confirm"):
			msg["chars"] = float(line.length())
		return

	var choice: Dictionary = msg["choice"]
	if not choice.is_empty() and int(msg["page"]) == msg["lines"].size() - 1:
		var options: Array = choice["options"]
		if Inp.nav("up", dt):
			choice["index"] = (int(choice["index"]) + options.size() - 1) % options.size()
			Snd.sfx("cursor")
		if Inp.nav("down", dt):
			choice["index"] = (int(choice["index"]) + 1) % options.size()
			Snd.sfx("cursor")
		if Inp.tap("cancel"):
			Snd.sfx("cancel")
			msg = {}
			choice["on_pick"].call(options.size() - 1)
			return
		if Inp.tap("confirm"):
			Snd.sfx("confirm")
			var picked := int(choice["index"])
			msg = {}
			choice["on_pick"].call(picked)
		return

	if Inp.tap("confirm") or Inp.tap("cancel"):
		msg["page"] = int(msg["page"]) + 1
		msg["chars"] = 0.0
		if int(msg["page"]) >= msg["lines"].size():
			msg = {}
		else:
			Snd.sfx("cursor")


# --- drawing ----------------------------------------------------------------

func player_offset() -> Vector2:
	if moving.is_empty():
		return Vector2.ZERO
	var k: float = min(1.0, float(moving["t"]) / float(moving["dur"]))
	return Vector2(
		lerp(float(moving["fx"]) - int(moving["tx"]), 0.0, k) + (int(moving["tx"]) - Gs.px),
		lerp(float(moving["fy"]) - int(moving["ty"]), 0.0, k) + (int(moving["ty"]) - Gs.py))


func camera_for(offset: Vector2) -> Vector2:
	var mw := int(map["w"]) * TILE
	var mh := int(map["h"]) * TILE
	var cx: float = (Gs.px + offset.x) * TILE + TILE / 2.0 - Art.VW / 2.0
	var cy: float = (Gs.py + offset.y) * TILE + TILE / 2.0 - Art.VH / 2.0
	cx = clamp(cx, 0.0, max(0.0, mw - Art.VW))
	cy = clamp(cy, 0.0, max(0.0, mh - Art.VH))
	return Vector2(round(cx), round(cy))


## Frame 0 is a legs-together idle; 1 and 2 are opposite strides. Walking plays
## 1,0,2,0 so the legs pass through the idle pose on every step, and standing
## still rests on it instead of freezing mid-stride.
const WALK_CYCLE := [1, 0, 2, 0]

func walk_frame(phase: float) -> int:
	if phase <= 0.0:
		return 0
	return WALK_CYCLE[int(phase) % WALK_CYCLE.size()]


func draw(c: CanvasItem) -> void:
	var offset := player_offset()
	var cam := camera_for(offset)
	var water_frame := int(anim * 3.0) % 2
	var ground: String = map.get("ground", "t_grass")

	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color("#12101c"))

	var x0 := int(cam.x / TILE)
	var y0 := int(cam.y / TILE)
	var x1 := int(ceil((cam.x + Art.VW) / TILE))
	var y1 := int(ceil((cam.y + Art.VH) / TILE))
	for y in range(y0, y1 + 1):
		for x in range(x0, x1 + 1):
			var ch := tile_at(x, y)
			if ch == "" or not Dat.legend.has(ch):
				continue
			var pos := Vector2(x * TILE - cam.x, y * TILE - cam.y)
			var under: String = Dat.underlay.get(ch, "")
			if under == "ground":
				under = ground
			if under != "":
				if under == "t_water0":
					under = "t_water%d" % water_frame
				Art.spr(c, under, pos)
			var name: String = Dat.legend[ch][0]
			if name == "t_water0":
				name = "t_water%d" % water_frame
			elif name == "t_grass":
				# Rotate through grass variants so open fields do not visibly tile.
				name = GRASS_VARIANTS[(x * 7 + y * 13) % 3]
			Art.spr(c, name, pos)

	# Entities, sorted so southern sprites overlap northern ones.
	var ents := []
	for n in npcs:
		ents.append({"y": n["ty"] + float(n["oy"]), "npc": n})
	ents.append({"y": Gs.py + offset.y, "npc": null})
	ents.sort_custom(func(a, b): return float(a["y"]) < float(b["y"]))

	for e in ents:
		var n = e["npc"]
		if n == null:
			var pos := Vector2((Gs.px + offset.x) * TILE - cam.x, (Gs.py + offset.y) * TILE - cam.y)
			Art.draw_shadow(c, pos + Vector2(8, 15), 6.0)
			Art.spr_foot(c, "aldric_%s%d" % [Gs.dir, walk_frame(walk_phase)],
				pos + Vector2(8, 16))
			continue
		var npos := Vector2((n["tx"] + float(n["ox"])) * TILE - cam.x,
			(n["ty"] + float(n["oy"])) * TILE - cam.y)
		if n["boss"]:
			Art.draw_shadow(c, npos + Vector2(8, 16), 11.0)
			var size := Art.frame_size("e_ogre")
			Art.spr(c, "e_ogre", npos + Vector2(8 - size.x / 2.0, 16 - size.y))
		else:
			Art.draw_shadow(c, npos + Vector2(8, 15), 6.0)
			Art.spr_foot(c, "%s_%s%d" % [n["sprite"], n["dir"], walk_frame(float(n["phase"]))],
				npos + Vector2(8, 16))

	draw_location_banner(c)
	if not msg.is_empty():
		draw_message_box(c)


func draw_location_banner(c: CanvasItem) -> void:
	var name: String = map.get("name", "")
	if banner_name != name:
		banner_name = name
		banner_timer = 2.6
	if banner_timer <= 0.0:
		return
	var w := Art.text_width(name) + 20
	Art.draw_window(c, Rect2(Art.VW - w - 6, 6, w, 18), "dark")
	Art.draw_text(c, name, Vector2(Art.VW - w / 2.0 - 6, 11), Color("#f6e2a8"), "center")


func draw_message_box(c: CanvasItem) -> void:
	var box_h := 42
	var y := Art.VH - box_h - 6
	Art.draw_window(c, Rect2(6, y, Art.VW - 12, box_h))
	var speaker: String = msg["speaker"]
	if speaker != "":
		var nw := Art.text_width(speaker) + 12
		Art.draw_window(c, Rect2(10, y - 9, nw, 15), "dark")
		Art.draw_text(c, speaker, Vector2(16, y - 5), Color("#f6e2a8"))

	var full: String = msg["lines"][int(msg["page"])]
	var shown := full.substr(0, int(msg["chars"]))
	var lines := Art.wrap_text(shown, 47)
	for i in mini(2, lines.size()):
		Art.draw_text(c, lines[i], Vector2(16, y + 11 + i * 12), Color("#f2f4ff"))

	var choice: Dictionary = msg["choice"]
	if not choice.is_empty() and int(msg["page"]) == msg["lines"].size() - 1 \
			and float(msg["chars"]) >= full.length():
		var options: Array = choice["options"]
		var w := 0
		for o in options:
			w = maxi(w, Art.text_width(o))
		w += 26
		var h := 8 + options.size() * 13
		var cx := Art.VW - w - 12
		var cy := y - h - 4
		Art.draw_window(c, Rect2(cx, cy, w, h), "dark")
		for i in options.size():
			var oy := cy + 5 + i * 13
			var picked := i == int(choice["index"])
			Art.draw_text(c, options[i], Vector2(cx + 18, oy),
				Color("#ffe9a0") if picked else Color("#f2f4ff"))
			if picked:
				Art.draw_cursor(c, Vector2(cx + 6, oy - 1), anim)
		return

	if float(msg["chars"]) >= full.length():
		var bob := 0 if sin(anim * 7.0) > 0.0 else 1
		for i in 4:
			c.draw_rect(Rect2(Art.VW - 26 + i, y + box_h - 12 + bob + i, 8 - i * 2, 1),
				Color("#f4e08a"))
