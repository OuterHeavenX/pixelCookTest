class_name ShopMode
extends RefCounted
## The quartermaster's counter in the Amber Lantern.

const TABS := [
	{"id": "wares", "label": "Wares"},
	{"id": "armoury", "label": "Armoury"},
]

var main
var index := 0
var tab := 0
var shelf := "amber"
var note := ""
var note_t := 0.0


func _init(owner) -> void:
	main = owner


func open(from_shelf := "amber") -> void:
	index = 0
	tab = 0
	shelf = from_shelf
	note = ""
	note_t = 0.0
	Snd.sfx("confirm")


## What is on the shelf under the open tab, flattened into one shape.
func shop_stock() -> Array:
	var out := []
	# Each counter names its own shelf, so Hollowmere sells cold-country work
	# and the Amber Lantern goes on selling what it always did.
	if TABS[tab]["id"] == "armoury":
		for id in Dat.gear_stock.get(shelf, []):
			var g: Dictionary = Dat.gear[id]
			out.append({"id": id, "gear": true, "name": g["name"], "icon": g["icon"],
				"price": int(g["price"]), "desc": g["desc"]})
	else:
		for id in Dat.shop_stock.get(shelf, []):
			var it: Dictionary = Dat.items[id]
			out.append({"id": id, "gear": false, "name": it["name"], "icon": it["icon"],
				"price": int(it["price"]), "desc": it["desc"]})
	return out


func set_tab(i: int) -> void:
	if i == tab:
		return
	tab = i
	index = 0
	Snd.sfx("cursor")


func update(dt: float) -> void:
	Gs.playtime += dt
	note_t = max(0.0, note_t - dt)
	if Inp.tap("cancel") or Inp.tap("menu"):
		main.close_shop()
		Snd.sfx("cancel")
		return
	if Inp.nav("left", dt):
		set_tab((tab + TABS.size() - 1) % TABS.size())
	if Inp.nav("right", dt):
		set_tab((tab + 1) % TABS.size())
	var stock := shop_stock()
	if Inp.nav("up", dt):
		index = (index + stock.size() - 1) % stock.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		index = (index + 1) % stock.size()
		Snd.sfx("cursor")
	if not Inp.tap("confirm"):
		return
	var it: Dictionary = stock[index]
	if Gs.gil < int(it["price"]):
		note = "Not enough gil."
		note_t = 1.6
		Snd.sfx("cancel")
		return
	Gs.gil -= int(it["price"])
	if bool(it["gear"]):
		Gs.take_gear(it["id"])
	else:
		Gs.take_item(it["id"])
	note = "Bought %s." % it["name"]
	note_t = 1.6
	Snd.sfx("item")


func draw(c: CanvasItem, anim: float) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(0.03, 0.02, 0.07, 0.7))
	Art.draw_window(c, Rect2(20, 14, 180, 150))
	Art.draw_text(c, "QUARTERMASTER", Vector2(30, 20), Color("#f6e2a8"))

	# Two shelves: consumables and gear. The armoury is where gil finally goes.
	for i in TABS.size():
		Art.draw_button(c, Rect2(30 + i * 60, 32, 56, 13), TABS[i]["label"], i == tab)

	var stock := shop_stock()
	var rows := 5
	var start: int = clampi(index - rows + 1, 0, maxi(0, stock.size() - rows))
	for i in range(start, mini(stock.size(), start + rows)):
		var it: Dictionary = stock[i]
		var by := 50 + (i - start) * 15
		var afford := Gs.gil >= int(it["price"])
		Art.draw_button(c, Rect2(30, by, 160, 13), "", i == index)
		Art.spr(c, it["icon"], Vector2(33, by + 2))
		Art.draw_text(c, it["name"], Vector2(45, by + 3),
			Color("#f2f4ff") if afford else Color("#8a8fb0"))
		Art.draw_text(c, "%dg" % int(it["price"]), Vector2(186, by + 3),
			Color("#9fd0ff") if afford else Color("#8a8fb0"), "right")
	if stock.size() > rows:
		var track := rows * 15 - 2
		var thumb: int = maxi(6, roundi(track * float(rows) / stock.size()))
		var ty: int = 50 + roundi((track - thumb) * float(start) / (stock.size() - rows))
		c.draw_rect(Rect2(192, 50, 2, track), Color("#1a2148"))
		c.draw_rect(Rect2(192, ty, 2, thumb), Color("#7c88b8"))

	var sel: Dictionary = stock[mini(index, stock.size() - 1)]
	var wrapped := Art.wrap_text(sel["desc"], 27)
	for i in mini(2, wrapped.size()):
		Art.draw_text(c, wrapped[i], Vector2(30, 130 + i * 11), Color("#9aa4c8"))
	if bool(sel["gear"]):
		# For gear, what it would do for whoever can actually wear it.
		var g: Dictionary = Dat.gear[sel["id"]]
		var wearer = null
		for h in Gs.party:
			if Gs.can_wear(h, g):
				wearer = h
				break
		if wearer == null:
			Art.draw_text(c, "Nobody here can use it.", Vector2(30, 152), Color("#e08a90"))
		else:
			Art.draw_text(c, "%s: %s" % [wearer["name"], Gs.gear_delta(wearer, g)],
				Vector2(30, 152), Color("#8fd8a0"))
	else:
		Art.draw_text(c, "[Z] buy   [X] leave", Vector2(30, 152), Color("#7a82a8"))

	Art.draw_window(c, Rect2(206, 14, 96, 44))
	Art.spr(c, "i_gil", Vector2(214, 21))
	Art.draw_text(c, "Gil", Vector2(225, 22), Color("#9aa4c8"))
	Art.draw_text(c, str(Gs.gil), Vector2(294, 36), Color("#f6e2a8"), "right")

	Art.draw_window(c, Rect2(206, 64, 96, 100))
	Art.draw_text(c, "BAG", Vector2(214, 72), Color("#9aa4c8"))
	var carried := []
	for b in Gs.bag_list():
		carried.append([Dat.items[b["id"]]["name"], int(b["n"])])
	for id in Gs.gear:
		if Dat.gear.has(id):
			carried.append([Dat.gear[id]["name"], int(Gs.gear[id])])
	for i in mini(7, carried.size()):
		Art.draw_text(c, (carried[i][0] as String).substr(0, 10),
			Vector2(214, 86 + i * 11), Color("#f2f4ff"))
		Art.draw_text(c, "x%d" % int(carried[i][1]), Vector2(294, 86 + i * 11),
			Color("#9fd0ff"), "right")

	if note_t > 0.0:
		var w := Art.text_width(note) + 20
		Art.draw_window(c, Rect2(Art.VW / 2.0 - w / 2.0, Art.VH - 24, w, 18), "dark")
		Art.draw_text(c, note, Vector2(Art.VW / 2.0, Art.VH - 19), Color("#f6e2a8"), "center")
