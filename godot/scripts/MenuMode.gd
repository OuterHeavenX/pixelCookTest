class_name MenuMode
extends RefCounted
## The field journal: items, magic, status, saving and the sound toggle.

const ROOT_ENTRIES := [
	{"id": "item", "label": "Item"},
	{"id": "magic", "label": "Magic"},
	{"id": "status", "label": "Status"},
	{"id": "save", "label": "Save"},
	{"id": "sound", "label": "Sound"},
	{"id": "close", "label": "Return"},
]

var main
var state := "root"
var root := 0
var index := 0
var who := 0
var spell := 0
var target := 0
var note := ""
var note_t := 0.0


func _init(owner) -> void:
	main = owner


func open() -> void:
	state = "root"
	root = 0
	index = 0
	who = 0
	Snd.sfx("confirm")


func say(text: String) -> void:
	note = text
	note_t = 2.2


func update(dt: float) -> void:
	Gs.playtime += dt
	note_t = max(0.0, note_t - dt)
	match state:
		"root":
			_update_root(dt)
		"item":
			_update_item(dt)
		"itemTarget":
			_update_item_target(dt)
		"magicWho":
			_update_magic_who(dt)
		"magicList":
			_update_magic_list(dt)
		"magicTarget":
			_update_magic_target(dt)
		"status":
			_update_status(dt)


func _update_root(dt: float) -> void:
	if Inp.nav("up", dt):
		root = (root + ROOT_ENTRIES.size() - 1) % ROOT_ENTRIES.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		root = (root + 1) % ROOT_ENTRIES.size()
		Snd.sfx("cursor")
	if Inp.tap("cancel") or Inp.tap("menu"):
		main.close_menu()
		return
	if not Inp.tap("confirm"):
		return
	var id: String = ROOT_ENTRIES[root]["id"]
	Snd.sfx("confirm")
	match id:
		"close":
			main.close_menu()
		"item":
			state = "item"
			index = 0
		"magic":
			state = "magicWho"
			who = 0
		"status":
			state = "status"
			who = 0
		"sound":
			say("Sound off." if Snd.toggle_mute() else "Sound on.")
		"save":
			say("Journal saved." if Gs.save_game() else "Could not save.")


func _update_item(dt: float) -> void:
	var bag := Gs.bag_list()
	if Inp.tap("cancel"):
		state = "root"
		Snd.sfx("cancel")
		return
	if bag.is_empty():
		return
	if Inp.nav("up", dt):
		index = (index + bag.size() - 1) % bag.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		index = (index + 1) % bag.size()
		Snd.sfx("cursor")
	if Inp.tap("confirm"):
		if Dat.items[bag[index]["id"]]["kind"] == "damage":
			Snd.sfx("cancel")
			say("Only useful in battle.")
			return
		state = "itemTarget"
		who = 0
		Snd.sfx("confirm")


func _update_item_target(dt: float) -> void:
	var bag := Gs.bag_list()
	if Inp.tap("cancel") or bag.is_empty():
		state = "item"
		Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		who = (who + Gs.party.size() - 1) % Gs.party.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		who = (who + 1) % Gs.party.size()
		Snd.sfx("cursor")
	if not Inp.tap("confirm"):
		return
	var entry: Dictionary = bag[mini(index, bag.size() - 1)]
	var it: Dictionary = Dat.items[entry["id"]]
	var h: Dictionary = Gs.party[who]
	var used := false
	if it["kind"] == "heal" and bool(h["alive"]) and int(h["hp"]) < int(h["maxhp"]):
		h["hp"] = mini(int(h["maxhp"]), int(h["hp"]) + int(it["power"]))
		used = true
	elif it["kind"] == "mp" and bool(h["alive"]) and int(h["mp"]) < int(h["maxmp"]):
		h["mp"] = mini(int(h["maxmp"]), int(h["mp"]) + int(it["power"]))
		used = true
	elif it["kind"] == "revive" and not bool(h["alive"]):
		h["alive"] = true
		h["hp"] = int(round(float(h["maxhp"]) * float(it["power"])))
		used = true
	if not used:
		Snd.sfx("cancel")
		say("It had no effect.")
		return
	Gs.spend_item(entry["id"])
	Snd.sfx("heal")
	say("%s used %s." % [h["name"], it["name"]])
	if Gs.bag_list().is_empty():
		state = "root"
	else:
		state = "item"
		index = clampi(index, 0, Gs.bag_list().size() - 1)


func _update_magic_who(dt: float) -> void:
	if Inp.tap("cancel"):
		state = "root"
		Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		who = (who + Gs.party.size() - 1) % Gs.party.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		who = (who + 1) % Gs.party.size()
		Snd.sfx("cursor")
	if Inp.tap("confirm"):
		var h: Dictionary = Gs.party[who]
		if (h["spells"] as Array).is_empty():
			Snd.sfx("cancel")
			say("%s knows no magic." % h["name"])
			return
		state = "magicList"
		spell = 0
		Snd.sfx("confirm")


func _update_magic_list(dt: float) -> void:
	var h: Dictionary = Gs.party[who]
	var known: Array = h["spells"]
	if Inp.tap("cancel"):
		state = "magicWho"
		Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		spell = (spell + known.size() - 1) % known.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		spell = (spell + 1) % known.size()
		Snd.sfx("cursor")
	if not Inp.tap("confirm"):
		return
	var sp: Dictionary = Dat.spells[known[spell]]
	if sp["kind"] == "attack":
		Snd.sfx("cancel")
		say("Save that for a fight.")
		return
	if not bool(h["alive"]):
		Snd.sfx("cancel")
		say("%s cannot act." % h["name"])
		return
	if int(h["mp"]) < int(sp["mp"]):
		Snd.sfx("cancel")
		say("Not enough MP.")
		return
	state = "magicTarget"
	target = 0
	Snd.sfx("confirm")


func _update_magic_target(dt: float) -> void:
	var h: Dictionary = Gs.party[who]
	var sp: Dictionary = Dat.spells[h["spells"][spell]]
	if Inp.tap("cancel"):
		state = "magicList"
		Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		target = (target + Gs.party.size() - 1) % Gs.party.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		target = (target + 1) % Gs.party.size()
		Snd.sfx("cursor")
	if not Inp.tap("confirm"):
		return
	var t: Dictionary = Gs.party[target]
	var ok := false
	if sp["kind"] == "heal" and bool(t["alive"]) and int(t["hp"]) < int(t["maxhp"]):
		t["hp"] = mini(int(t["maxhp"]),
			int(t["hp"]) + int(round(float(sp["power"]) + float(h["mag"]) * 1.2)))
		ok = true
	elif sp["kind"] == "healAll":
		for x in Gs.living_heroes():
			x["hp"] = mini(int(x["maxhp"]),
				int(x["hp"]) + int(round(float(sp["power"]) + float(h["mag"]) * 0.9)))
		ok = true
	elif sp["kind"] == "revive" and not bool(t["alive"]):
		t["alive"] = true
		t["hp"] = maxi(1, int(round(float(t["maxhp"]) * float(sp["power"]))))
		ok = true
	if not ok:
		Snd.sfx("cancel")
		say("Nothing happened.")
		return
	h["mp"] = int(h["mp"]) - int(sp["mp"])
	Snd.sfx("heal")
	say("%s casts %s." % [h["name"], sp["name"]])
	state = "magicList"


func _update_status(dt: float) -> void:
	if Inp.tap("cancel"):
		state = "root"
		Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		who = (who + Gs.party.size() - 1) % Gs.party.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		who = (who + 1) % Gs.party.size()
		Snd.sfx("cursor")


# --- drawing ----------------------------------------------------------------

func hp_color(h: Dictionary) -> Color:
	if not bool(h["alive"]):
		return Color("#c08090")
	var r := float(h["hp"]) / float(h["maxhp"])
	if r < 0.2:
		return Color("#ff6a6a")
	if r < 0.5:
		return Color("#ffd75a")
	return Color("#f2f4ff")


func class_icon(h: Dictionary) -> String:
	return "i_sword" if h["id"] == "aldric" else "i_staff"


func draw(c: CanvasItem, anim: float) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(0.03, 0.02, 0.07, 0.72))

	# Command column: buttons, so an entry can be hit rather than walked to.
	Art.draw_window(c, Rect2(6, 6, 84, 108))
	for i in ROOT_ENTRIES.size():
		var by := 11 + i * 16
		var dim := state != "root" and i != root
		Art.draw_button(c, Rect2(10, by, 76, 14), ROOT_ENTRIES[i]["label"],
			i == root, false, dim)

	Art.draw_window(c, Rect2(6, 118, 84, 56))
	Art.spr(c, "i_gil", Vector2(14, 124))
	Art.draw_text(c, "Gil", Vector2(25, 125), Color("#9aa4c8"))
	Art.draw_text(c, str(Gs.gil), Vector2(82, 136), Color("#f6e2a8"), "right")
	Art.draw_text(c, "Time", Vector2(14, 148), Color("#9aa4c8"))
	Art.draw_text(c, Gs.format_time(Gs.playtime), Vector2(82, 159), Color("#f2f4ff"), "right")

	Art.draw_window(c, Rect2(96, 6, Art.VW - 102, Art.VH - 12))
	if state == "status":
		_draw_status(c, anim)
	elif state == "item" or state == "itemTarget":
		_draw_items(c, anim)
	elif state.begins_with("magic"):
		_draw_magic(c, anim)
	else:
		_draw_party(c)

	if note_t > 0.0:
		var w := Art.text_width(note) + 20
		Art.draw_window(c, Rect2(Art.VW / 2.0 - w / 2.0, Art.VH - 26, w, 18), "dark")
		Art.draw_text(c, note, Vector2(Art.VW / 2.0, Art.VH - 21), Color("#f6e2a8"), "center")


func _draw_party(c: CanvasItem) -> void:
	Art.draw_text(c, "PARTY", Vector2(106, 12), Color("#f6e2a8"))
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var x := 110
		var y := 30 + i * 48
		Art.spr_foot(c, "%s_down0" % h["sprite"], Vector2(x + 12, y + 30),
			Art.scale_for("%s_down0" % h["sprite"], 36.0))
		Art.spr(c, class_icon(h), Vector2(x + 30, y - 1))
		Art.draw_text(c, h["name"], Vector2(x + 40, y),
			Color("#f2f4ff") if bool(h["alive"]) else Color("#c08090"))
		Art.draw_text(c, h["title"], Vector2(x + 40, y + 11), Color("#9aa4c8"))
		Art.draw_text(c, "Lv %d" % int(h["lv"]), Vector2(x + 132, y), Color("#f6e2a8"))
		Art.draw_text(c, "HP", Vector2(x + 30, y + 24), Color("#9aa4c8"))
		Art.draw_text(c, "%d/%d" % [int(h["hp"]), int(h["maxhp"])],
			Vector2(x + 108, y + 24), hp_color(h), "right")
		Art.draw_bar(c, Vector2(x + 30, y + 34), Vector2(78, 4),
			float(h["hp"]) / float(h["maxhp"]), Color("#9fffb0"), Color("#3f9a54"))
		if int(h["maxmp"]) > 0:
			Art.draw_text(c, "MP", Vector2(x + 120, y + 24), Color("#9aa4c8"))
			Art.draw_text(c, "%d/%d" % [int(h["mp"]), int(h["maxmp"])],
				Vector2(x + 196, y + 24), Color("#9fd0ff"), "right")
			Art.draw_bar(c, Vector2(x + 120, y + 34), Vector2(76, 4),
				float(h["mp"]) / float(h["maxmp"]), Color("#bfe4ff"), Color("#3a72c8"))
		else:
			Art.draw_text(c, "No magic", Vector2(x + 120, y + 24), Color("#7a82a8"))


func _draw_items(c: CanvasItem, anim: float) -> void:
	var bag := Gs.bag_list()
	Art.draw_text(c, "ITEMS", Vector2(106, 12), Color("#f6e2a8"))
	if bag.is_empty():
		Art.draw_text(c, "The bag is empty.", Vector2(110, 34), Color("#9aa4c8"))
		return
	var start: int = clampi(index - 3, 0, maxi(0, bag.size() - 5))
	for i in range(start, mini(bag.size(), start + 5)):
		var y := 28 + (i - start) * 16
		var it: Dictionary = Dat.items[bag[i]["id"]]
		Art.spr(c, it["icon"], Vector2(116, y - 1))
		var highlighted := state == "item" and i == index
		Art.draw_text(c, it["name"], Vector2(128, y),
			Color("#ffe9a0") if highlighted else Color("#f2f4ff"))
		Art.draw_text(c, "x%d" % int(bag[i]["n"]), Vector2(300, y), Color("#9fd0ff"), "right")
		if i == index:
			Art.draw_cursor(c, Vector2(106, y - 1), anim)
	var current: Dictionary = Dat.items[bag[mini(index, bag.size() - 1)]["id"]]
	Art.draw_text(c, current["desc"], Vector2(110, 112), Color("#9aa4c8"))

	if state != "itemTarget":
		return
	Art.draw_text(c, "Use on:", Vector2(110, 126), Color("#f6e2a8"))
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var y := 138 + i * 12
		Art.draw_text(c, h["name"], Vector2(128, y),
			Color("#f2f4ff") if bool(h["alive"]) else Color("#c08090"))
		Art.draw_text(c, "%d/%d" % [int(h["hp"]), int(h["maxhp"])],
			Vector2(250, y), hp_color(h), "right")
		if int(h["maxmp"]) > 0:
			Art.draw_text(c, "MP %d" % int(h["mp"]), Vector2(300, y), Color("#9fd0ff"), "right")
		if i == who:
			Art.draw_cursor(c, Vector2(116, y - 1), anim)


func _draw_magic(c: CanvasItem, anim: float) -> void:
	Art.draw_text(c, "MAGIC", Vector2(106, 12), Color("#f6e2a8"))
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var y := 28 + i * 14
		Art.draw_text(c, h["name"], Vector2(128, y),
			Color("#ffe9a0") if i == who else Color("#f2f4ff"))
		var right := "-"
		if not (h["spells"] as Array).is_empty():
			right = "MP %d/%d" % [int(h["mp"]), int(h["maxmp"])]
		Art.draw_text(c, right, Vector2(300, y), Color("#9fd0ff"), "right")
		if i == who and state == "magicWho":
			Art.draw_cursor(c, Vector2(116, y - 1), anim)
	if state == "magicWho":
		Art.draw_text(c, "Choose a caster.", Vector2(110, 84), Color("#9aa4c8"))
		return

	var caster: Dictionary = Gs.party[who]
	var known: Array = caster["spells"]
	for i in known.size():
		var sp: Dictionary = Dat.spells[known[i]]
		var y := 84 + i * 14
		var dim := int(caster["mp"]) < int(sp["mp"])
		var color := Color("#8a8fb0")
		if not dim:
			color = Color("#ffe9a0") if i == spell else Color("#f2f4ff")
		Art.draw_text(c, sp["name"], Vector2(128, y), color)
		Art.draw_text(c, "%d MP" % int(sp["mp"]), Vector2(240, y),
			Color("#8a8fb0") if dim else Color("#9fd0ff"), "right")
		Art.draw_text(c, "battle" if sp["kind"] == "attack" else "field",
			Vector2(306, y), Color("#7a82a8"), "right")
		if i == spell:
			Art.draw_cursor(c, Vector2(116, y - 1), anim)

	if state != "magicTarget":
		return
	c.draw_rect(Rect2(100, 118, Art.VW - 110, 52), Color(0.03, 0.02, 0.07, 0.6))
	Art.draw_text(c, "Cast on:", Vector2(110, 122), Color("#f6e2a8"))
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var y := 136 + i * 11
		Art.draw_text(c, h["name"], Vector2(128, y),
			Color("#f2f4ff") if bool(h["alive"]) else Color("#c08090"))
		Art.draw_text(c, "%d/%d" % [int(h["hp"]), int(h["maxhp"])],
			Vector2(250, y), hp_color(h), "right")
		if i == target:
			Art.draw_cursor(c, Vector2(116, y - 1), anim)


func _draw_status(c: CanvasItem, anim: float) -> void:
	var h: Dictionary = Gs.party[who]
	Art.draw_text(c, "STATUS", Vector2(106, 12), Color("#f6e2a8"))

	# Who-to-inspect column on the left, detail sheet on the right.
	for i in Gs.party.size():
		var x: Dictionary = Gs.party[i]
		var y := 30 + i * 14
		var color := Color("#bfc8ea") if bool(x["alive"]) else Color("#c08090")
		Art.draw_text(c, x["name"], Vector2(118, y),
			Color("#ffe9a0") if i == who else color)
		if i == who:
			Art.draw_cursor(c, Vector2(106, y - 1), anim)
	c.draw_rect(Rect2(154, 24, 1, Art.VH - 46), Color("#4d63b4"))

	Art.spr_foot(c, "%s_ready" % h["sprite"], Vector2(178, 74),
		Art.scale_for("%s_ready" % h["sprite"], 48.0))
	Art.draw_text(c, h["name"], Vector2(200, 30), Color("#f2f4ff"))
	Art.spr(c, class_icon(h), Vector2(200, 41))
	Art.draw_text(c, h["title"], Vector2(212, 42), Color("#9aa4c8"))
	Art.draw_text(c, "Level %d" % int(h["lv"]), Vector2(200, 56), Color("#f6e2a8"))
	var need := Gs.exp_to_next(int(h["lv"])) - int(h["exp"])
	Art.draw_text(c, "Next in %d" % need, Vector2(200, 68), Color("#9aa4c8"))
	Art.draw_bar(c, Vector2(200, 79), Vector2(100, 4),
		float(h["exp"]) / float(Gs.exp_to_next(int(h["lv"]))),
		Color("#ffe9a0"), Color("#c08a2c"))

	var mp_text := "-"
	if int(h["maxmp"]) > 0:
		mp_text = "%d/%d" % [int(h["mp"]), int(h["maxmp"])]
	var stats := [
		["HP", "%d/%d" % [int(h["hp"]), int(h["maxhp"])]], ["MP", mp_text],
		["Attack", str(int(h["atk"]))], ["Defense", str(int(h["def"]))],
		["Magic", str(int(h["mag"]))], ["Speed", str(int(h["spd"]))],
	]
	for i in stats.size():
		var x := 106 + (i % 2) * 104
		var y := 96 + (i / 2) * 14
		Art.draw_text(c, stats[i][0], Vector2(x, y), Color("#9aa4c8"))
		Art.draw_text(c, stats[i][1], Vector2(x + 94, y), Color("#f2f4ff"), "right")

	Art.draw_text(c, "Spells", Vector2(106, 140), Color("#9aa4c8"))
	var names := []
	for sp in h["spells"]:
		names.append(Dat.spells[sp]["name"])
	var known := "none" if names.is_empty() else ", ".join(PackedStringArray(names))
	var wrapped := Art.wrap_text(known, 30)
	for i in mini(2, wrapped.size()):
		Art.draw_text(c, wrapped[i], Vector2(106, 152 + i * 11), Color("#bfc8ea"))
