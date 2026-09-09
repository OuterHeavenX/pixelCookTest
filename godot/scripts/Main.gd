extends Node2D
## Root node. Owns the mode machine, the screen fade, and all drawing.
##
## The whole game renders through this one _draw(), the same way the browser
## build renders to one canvas. Modes are plain objects, not scene nodes, so
## the scene tree stays a single node and nothing depends on hand-written
## .tscn wiring.

var mode := "title"

var field: FieldMode
var battle: BattleMode
var menu: MenuMode
var shop: ShopMode
var title: TitleMode
var ending: EndingMode

var fade := 0.0
var fade_dir := 0
var _fade_then: Callable = Callable()


func _ready() -> void:
	# Nearest-neighbour keeps the pixel art crisp at every zoom level.
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	field = FieldMode.new(self)
	battle = BattleMode.new(self)
	menu = MenuMode.new(self)
	shop = ShopMode.new(self)
	title = TitleMode.new(self)
	ending = EndingMode.new(self)
	Snd.play("town")


func _process(dt: float) -> void:
	dt = min(dt, 0.05)
	if Inp.tap("mute") and mode != "menu":
		Snd.toggle_mute()

	var blocked := _update_fade(dt) and fade_dir > 0
	if not blocked:
		match mode:
			"title":
				title.update(dt)
			"field":
				field.update(dt)
			"battle":
				battle.update(dt)
			"menu":
				menu.update(dt)
			"shop":
				shop.update(dt)
			"gameover":
				title.update_over(dt)
			"ending":
				ending.update(dt)

	Inp.end_frame()
	queue_redraw()


func _draw() -> void:
	match mode:
		"title":
			title.draw(self)
		"ending":
			ending.draw(self)
		"field":
			field.draw(self)
		"battle":
			battle.draw(self)
		"menu":
			field.draw(self)
			menu.draw(self, field.anim)
		"shop":
			field.draw(self)
			shop.draw(self, field.anim)
		"gameover":
			title.draw_over(self)
	if fade > 0.0:
		draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(0.02, 0.016, 0.05, fade))


# --- fade -------------------------------------------------------------------

func fade_to(action: Callable) -> void:
	if fade_dir != 0:
		return
	fade_dir = 1
	_fade_then = action


func _update_fade(dt: float) -> bool:
	if fade_dir == 0:
		return false
	fade += fade_dir * dt * 3.4
	if fade >= 1.0:
		fade = 1.0
		if _fade_then.is_valid():
			var run := _fade_then
			_fade_then = Callable()
			run.call()
		fade_dir = -1
	elif fade <= 0.0:
		fade = 0.0
		fade_dir = 0
	return true


# --- mode transitions -------------------------------------------------------

func begin_game(continue_save: bool) -> void:
	var start := func() -> void:
		if continue_save and Gs.load_game():
			field.enter_map(Gs.map_id, Gs.px, Gs.py, Gs.dir)
		else:
			Gs.new_game()
			var town: Dictionary = Dat.maps["town"]
			field.enter_map("town", int(town["spawn"][0]), int(town["spawn"][1]), "down")
		mode = "field"
	fade_to(start)


func start_encounter(group: Array, boss: bool) -> void:
	Snd.sfx("encounter")
	var begin := func() -> void:
		battle.start(group, boss)
		mode = "battle"
	fade_to(begin)


func finish_battle(how: String, was_boss: bool) -> void:
	var wrap_up := func() -> void:
		if how == "lose":
			mode = "gameover"
			title.over_index = 0
			Snd.stop()
			return
		mode = "field"
		for h in Gs.party:
			h["defending"] = false
			h["atb"] = 0.0
		if was_boss and how == "win":
			# The chapter closes here. The party is put back in Rivenbrook and
			# the journal written before the credits, so Continue picks up in a
			# town that knows what happened rather than in the room where it
			# happened.
			for h in Gs.party:
				h["hp"] = h["maxhp"]
				h["mp"] = h["maxmp"]
				h["alive"] = true
			var spawn: Array = Dat.maps["town"]["spawn"]
			field.enter_map("town", int(spawn[0]), int(spawn[1]), "up")
			Gs.save_game()
			mode = "ending"
			ending.open()
			return
		Snd.play(field.map.get("music", "field"))
	fade_to(wrap_up)


func resolve_game_over(load_save: bool) -> void:
	var restart := func() -> void:
		if load_save and Gs.load_game():
			field.enter_map(Gs.map_id, Gs.px, Gs.py, Gs.dir)
			mode = "field"
		else:
			mode = "title"
			title.index = 0
			Snd.stop()
	fade_to(restart)


func open_menu() -> void:
	mode = "menu"
	menu.open()


func close_menu() -> void:
	mode = "field"
	Snd.sfx("cancel")


func open_shop() -> void:
	mode = "shop"
	shop.open()


func close_shop() -> void:
	mode = "field"
