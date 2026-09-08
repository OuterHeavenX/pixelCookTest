class_name ShopMode
extends RefCounted
## The quartermaster's counter in the Amber Lantern.

var main
var index := 0
var note := ""
var note_t := 0.0


func _init(owner) -> void:
	main = owner


func open() -> void:
	index = 0
	note = ""
	note_t = 0.0
	Snd.sfx("confirm")


func update(dt: float) -> void:
	Gs.playtime += dt
	note_t = max(0.0, note_t - dt)
	var stock: Array = Dat.shop_stock
	if Inp.tap("cancel") or Inp.tap("menu"):
		main.close_shop()
		Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		index = (index + stock.size() - 1) % stock.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		index = (index + 1) % stock.size()
		Snd.sfx("cursor")
	if not Inp.tap("confirm"):
		return
	var id: String = stock[index]
	var it: Dictionary = Dat.items[id]
	if Gs.gil < int(it["price"]):
		note = "Not enough gil."
		note_t = 1.6
		Snd.sfx("cancel")
		return
	Gs.gil -= int(it["price"])
	Gs.take_item(id)
	note = "Bought %s." % it["name"]
	note_t = 1.6
	Snd.sfx("item")


func draw(c: CanvasItem, anim: float) -> void:
	c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(0.03, 0.02, 0.07, 0.7))
	Art.draw_window(c, Rect2(20, 14, 180, 150))
	Art.draw_text(c, "QUARTERMASTER", Vector2(30, 22), Color("#f6e2a8"))
	var stock: Array = Dat.shop_stock
	for i in stock.size():
		var it: Dictionary = Dat.items[stock[i]]
		var y := 40 + i * 18
		Art.spr(c, it["icon"], Vector2(38, y - 1))
		Art.draw_text(c, it["name"], Vector2(52, y),
			Color("#ffe9a0") if i == index else Color("#f2f4ff"))
		Art.draw_text(c, "%dg" % int(it["price"]), Vector2(192, y),
			Color("#9fd0ff") if Gs.gil >= int(it["price"]) else Color("#8a8fb0"), "right")
		if i == index:
			Art.draw_cursor(c, Vector2(28, y - 1), anim)
	Art.draw_text(c, Dat.items[stock[index]]["desc"], Vector2(30, 136), Color("#9aa4c8"))
	Art.draw_text(c, "[Z] buy   [X] leave", Vector2(30, 150), Color("#7a82a8"))

	Art.draw_window(c, Rect2(206, 14, 96, 44))
	Art.spr(c, "i_gil", Vector2(214, 21))
	Art.draw_text(c, "Gil", Vector2(225, 22), Color("#9aa4c8"))
	Art.draw_text(c, str(Gs.gil), Vector2(294, 36), Color("#f6e2a8"), "right")

	Art.draw_window(c, Rect2(206, 64, 96, 100))
	Art.draw_text(c, "BAG", Vector2(214, 72), Color("#9aa4c8"))
	var bag := Gs.bag_list()
	for i in mini(6, bag.size()):
		Art.draw_text(c, (Dat.items[bag[i]["id"]]["name"] as String).substr(0, 10),
			Vector2(214, 88 + i * 12), Color("#f2f4ff"))
		Art.draw_text(c, "x%d" % int(bag[i]["n"]), Vector2(294, 88 + i * 12),
			Color("#9fd0ff"), "right")

	if note_t > 0.0:
		var w := Art.text_width(note) + 20
		Art.draw_window(c, Rect2(Art.VW / 2.0 - w / 2.0, Art.VH - 24, w, 18), "dark")
		Art.draw_text(c, note, Vector2(Art.VW / 2.0, Art.VH - 19), Color("#f6e2a8"), "center")
