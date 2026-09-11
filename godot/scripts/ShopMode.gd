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


## Each counter names its own shelf: the forge sells steel and nothing to
## drink, the inn the other way round. A shop only shows the tabs its shelf
## has something on, so a smith is not a smith with an empty pantry beside.
func shelf_stock(tab_id: String) -> Array:
	var out := []
	if tab_id == "armoury":
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


func shop_tabs() -> Array:
	var tabs := []
	for tb in TABS:
		if not shelf_stock(tb["id"]).is_empty():
			tabs.append(tb)
	return tabs if not tabs.is_empty() else [TABS[0]]


## What is on the shelf under the open tab, flattened into one shape.
func shop_stock() -> Array:
	var tabs := shop_tabs()
	return shelf_stock(tabs[mini(tab, tabs.size() - 1)]["id"])


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
		set_tab((tab + shop_tabs().size() - 1) % shop_tabs().size())
	if Inp.nav("right", dt):
		set_tab((tab + 1) % shop_tabs().size())
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
	Gs.autosave()


## The counter fills the view: the shelf down the left, the purse and the
## bag stacked on the right. Composed from VW and VH rather than centred at
## 320x180, so a wide phone gets a wide shelf instead of a margin.
func layout() -> Dictionary:
	var m := 8
	var gap := 6
	var right: int = clampi(roundi(Art.VW * 0.29), 100, 124)
	var left := Rect2(m, m, Art.VW - m * 2 - right - gap, Art.VH - m * 2)
	var gil := Rect2(left.position.x + left.size.x + gap, m, right, 40)
	var bag := Rect2(gil.position.x, gil.position.y + gil.size.y + gap, right,
		Art.VH - m - (gil.position.y + gil.size.y + gap))
	return {"left": left, "gil": gil, "bag": bag}


func draw(c: CanvasItem, _anim: float) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(0.03, 0.02, 0.07, 0.7))
	var lay := layout()
	var left: Rect2 = lay["left"]
	var gil: Rect2 = lay["gil"]
	var bag: Rect2 = lay["bag"]
	var lx := left.position.x
	var ly := left.position.y
	var inner := left.size.x - 20
	Art.draw_window(c, left)
	Art.draw_text(c, "QUARTERMASTER", Vector2(lx + 10, ly + 6), Color("#f6e2a8"))

	# The shelves the counter has anything on: wares, gear, or both.
	var tabs := shop_tabs()
	for i in tabs.size():
		Art.draw_button(c, Rect2(lx + 10 + i * 60, ly + 18, 56, 13), tabs[i]["label"], i == tab)

	# Description and the wearer's line sit at the bottom; the list gets the
	# room between, however many rows that is on this screen.
	var list_top := ly + 36
	var foot_h := 40
	var rows: int = maxi(1, int((left.size.y - 36 - foot_h - 2) / 15))
	var row_w := inner - 6
	var stock := shop_stock()
	if stock.is_empty():
		Art.draw_text(c, "Nothing on this shelf today.", Vector2(lx + 10, list_top + 6), Color("#9aa4c8"))
		return
	var start: int = clampi(index - rows + 1, 0, maxi(0, stock.size() - rows))
	for i in range(start, mini(stock.size(), start + rows)):
		var it: Dictionary = stock[i]
		var by := list_top + (i - start) * 15
		var bx := lx + 10
		var afford := Gs.gil >= int(it["price"])
		Art.draw_button(c, Rect2(bx, by, row_w, 13), "", i == index)
		Art.spr(c, it["icon"], Vector2(bx + 3, by + 2))
		var price := "%dg" % int(it["price"])
		Art.draw_text(c, price, Vector2(bx + row_w - 4, by + 3),
			Color("#9fd0ff") if afford else Color("#8a8fb0"), "right")
		Art.draw_text(c, Art.fit_text(it["name"], row_w - 19 - Art.text_width(price) - 6),
			Vector2(bx + 15, by + 3), Color("#f2f4ff") if afford else Color("#8a8fb0"))
	if stock.size() > rows:
		var track := rows * 15 - 2
		var tx := lx + 10 + row_w + 2
		var thumb: int = maxi(6, roundi(track * float(rows) / stock.size()))
		var ty: int = roundi(list_top) + roundi((track - thumb) * float(start) / (stock.size() - rows))
		c.draw_rect(Rect2(tx, list_top, 2, track), Color("#1a2148"))
		c.draw_rect(Rect2(tx, ty, 2, thumb), Color("#7c88b8"))

	var sel: Dictionary = stock[mini(index, stock.size() - 1)]
	var foot_y := ly + left.size.y - foot_h
	var wrapped := Art.wrap_width(sel["desc"], inner)
	for i in mini(2, wrapped.size()):
		Art.draw_text(c, wrapped[i], Vector2(lx + 10, foot_y + i * 11), Color("#9aa4c8"))
	if bool(sel["gear"]):
		# For gear, what it would do for whoever can actually wear it.
		var g: Dictionary = Dat.gear[sel["id"]]
		var wearer = null
		for h in Gs.party:
			if Gs.can_wear(h, g):
				wearer = h
				break
		if wearer == null:
			Art.draw_text(c, "Nobody here can use it.", Vector2(lx + 10, foot_y + 24), Color("#e08a90"))
		else:
			Art.draw_text(c, Art.fit_text("%s: %s" % [wearer["name"], Gs.gear_delta(wearer, g)], inner),
				Vector2(lx + 10, foot_y + 24), Color("#8fd8a0"))
	else:
		Art.draw_text(c, "[Z] buy   [X] leave", Vector2(lx + 10, foot_y + 24), Color("#7a82a8"))

	Art.draw_window(c, gil)
	Art.spr(c, "i_gil", gil.position + Vector2(8, 7))
	Art.draw_text(c, "Gil", gil.position + Vector2(19, 8), Color("#9aa4c8"))
	Art.draw_text(c, str(Gs.gil), gil.position + Vector2(gil.size.x - 8, 22), Color("#f6e2a8"), "right")

	Art.draw_window(c, bag)
	Art.draw_text(c, "BAG", bag.position + Vector2(8, 8), Color("#9aa4c8"))
	var carried := []
	for b in Gs.bag_list():
		carried.append([Dat.items[b["id"]]["name"], int(b["n"])])
	for id in Gs.gear:
		if Dat.gear.has(id):
			carried.append([Dat.gear[id]["name"], int(Gs.gear[id])])
	var fit: int = maxi(1, int((bag.size.y - 22 - 4) / 11))
	var shown: int = fit - 1 if carried.size() > fit else carried.size()
	for i in shown:
		var count := "x%d" % int(carried[i][1])
		var ry := bag.position.y + 22 + i * 11
		Art.draw_text(c, count, Vector2(bag.position.x + bag.size.x - 8, ry), Color("#9fd0ff"), "right")
		Art.draw_text(c, Art.fit_text(carried[i][0], bag.size.x - 16 - Art.text_width(count) - 4),
			Vector2(bag.position.x + 8, ry), Color("#f2f4ff"))
	if carried.size() > shown:
		Art.draw_text(c, "+%d more" % (carried.size() - shown),
			Vector2(bag.position.x + bag.size.x - 8, bag.position.y + 22 + shown * 11),
			Color("#7a82a8"), "right")

	if note_t > 0.0:
		var w := Art.text_width(note) + 20
		Art.draw_window(c, Rect2(Art.VW / 2.0 - w / 2.0, Art.VH - 24, w, 18), "dark")
		Art.draw_text(c, note, Vector2(Art.VW / 2.0, Art.VH - 19), Color("#f6e2a8"), "center")
