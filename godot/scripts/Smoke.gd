extends Node
## A smoke test for the Godot build: boots the real game scene, walks it
## through every mode with real key events, screenshots each one, and reports
## what it saw.
##
## The Godot build had been checked only by gdlint and a syntax pass, which
## cannot catch a parse error the engine treats as fatal or a method that does
## not exist on a real object. This runs the game.
##
##     python3 tools/godotsmoke.py
##
## SMOKE_OUT names a directory for the screenshots; without it none are saved.

const STEP_FRAMES := 4

var main: Node2D
var out_dir := ""
var failures: Array[String] = []
var shots := 0


func _ready() -> void:
	out_dir = OS.get_environment("SMOKE_OUT")
	var packed: PackedScene = load("res://scenes/Main.tscn")
	main = packed.instantiate()
	add_child(main)
	_run.call_deferred()


func _step(frames := STEP_FRAMES) -> void:
	for i in frames:
		await get_tree().process_frame


## Wait for the game to actually be in a state, rather than guessing at a
## frame count - the first version of this screenshotted a half-finished fade.
func _until(cond: Callable, limit := 900) -> bool:
	var waited := 0
	while not cond.call() and waited < limit:
		await get_tree().process_frame
		waited += 1
	return cond.call()


## Fades cover the screen; a shot taken during one shows nothing.
func _settle(limit := 900) -> void:
	await _until(func(): return main.fade <= 0.0 and main.fade_dir == 0, limit)
	await _step(2)


## Press and release an action, the way a player would.
func _press(action: String, frames := STEP_FRAMES) -> void:
	var code: int = Inp.BINDINGS[action][0]
	var down := InputEventKey.new()
	down.physical_keycode = code
	down.pressed = true
	Input.parse_input_event(down)
	await _step(2)
	var up := InputEventKey.new()
	up.physical_keycode = code
	up.pressed = false
	Input.parse_input_event(up)
	await _step(frames)


func _shot(name: String) -> void:
	await _settle()
	await RenderingServer.frame_post_draw
	if out_dir == "":
		return
	var img := get_viewport().get_texture().get_image()
	var err := img.save_png("%s/godot_%s.png" % [out_dir, name])
	if err != OK:
		failures.append("could not save screenshot %s (error %d)" % [name, err])
	else:
		shots += 1


func _expect(ok: bool, what: String) -> void:
	print(("  ok   " if ok else "  FAIL ") + what)
	if not ok:
		failures.append(what)


func _run() -> void:
	await _step(8)

	print("title")
	_expect(main.mode == "title", "boots to the title screen")
	await _shot("title")

	print("field")
	await _press("confirm", 2)           # New Game
	_expect(await _until(func(): return main.mode == "field"),
		"New Game reaches the field")
	_expect(Gs.party.size() == 3, "three characters in the party")
	_expect(Gs.map_id == "town", "starts in town")
	await _shot("field")

	print("equipment")
	_expect(int(Gs.party[0]["atk"]) == 22,
		"Aldric's bronze sword is counted (atk 22, got %d)" % int(Gs.party[0]["atk"]))
	_expect(Gs.equipped(Gs.party[0], "weapon") != null, "Aldric starts armed")
	var lyra: Dictionary = Gs.party[1]
	var def_before := int(lyra["def"])
	var worn: bool = Gs.equip_gear(lyra, "armour", "leather_vest")
	_expect(worn, "a leather vest goes on")
	_expect(int(lyra["def"]) > def_before,
		"the vest raises DEF (%d -> %d)" % [def_before, int(lyra["def"])])
	var hp_before := int(lyra["hp"])
	Gs.take_gear("copper_ring")
	Gs.equip_gear(lyra, "trinket", "copper_ring")
	_expect(int(lyra["hp"]) == hp_before + 24,
		"a +24 HP charm moves current HP too (%d -> %d)" % [hp_before, int(lyra["hp"])])

	print("menu")
	await _press("menu", 2)
	_expect(await _until(func(): return main.mode == "menu"), "the menu opens")
	await _shot("menu")
	main.menu.state = "equipWho"
	main.menu.who = 1
	await _step(6)
	await _shot("menu_equip_who")
	main.menu.state = "equipSlot"
	main.menu.slot = 1
	await _step(6)
	await _shot("menu_equip_slot")
	main.menu.state = "equipPick"
	main.menu.pick = 0
	await _step(6)
	_expect(main.menu.equip_choices().size() > 0, "the pack offers something for that slot")
	await _shot("menu_equip_pick")
	main.menu.state = "status"
	await _step(6)
	await _shot("menu_status")
	main.close_menu()
	_expect(await _until(func(): return main.mode == "field"),
		"the menu closes back to the field")

	print("shop")
	Gs.gil = 5000
	main.open_shop()
	_expect(await _until(func(): return main.mode == "shop"), "the shop opens")
	await _shot("shop_wares")
	main.shop.set_tab(1)
	await _step(6)
	var stock: Array = main.shop.shop_stock()
	_expect(stock.size() == Dat.gear_stock.size(),
		"the armoury lists every piece (%d)" % stock.size())
	await _shot("shop_armoury")
	var gil_before := Gs.gil
	await _press("confirm", 8)
	_expect(Gs.gil < gil_before, "buying costs gil (%d -> %d)" % [gil_before, Gs.gil])
	_expect(not Gs.gear.is_empty(), "the piece lands in the pack")
	await _shot("shop_bought")
	await _press("cancel", 2)
	_expect(await _until(func(): return main.mode == "field"), "the shop closes")

	print("battle")
	main.start_encounter(["goblin", "goblin", "slime"], false)
	_expect(await _until(func(): return main.mode == "battle"), "an encounter starts")
	await _shot("battle_intro")
	# Wait for someone's gauge to fill, then walk the command window.
	_expect(await _until(func(): return main.battle.phase == "command"),
		"a character's turn comes up")
	await _shot("battle_command")
	var cmds: Array = main.battle.commands_for(main.battle.actor)
	_expect(cmds.size() >= 4, "the command window has its buttons (%d)" % cmds.size())
	if main.battle.actor != null and not (main.battle.actor["spells"] as Array).is_empty():
		for i in cmds.size():
			if cmds[i]["id"] == "magic":
				main.battle.cmd = i
		main.battle.sub = "magic"
		await _step(6)
		_expect(main.battle.sub_entries(main.battle.actor).size() > 0, "the spell list fills")
		await _shot("battle_magic")
		main.battle.sub = ""
	main.battle.cmd = 0
	await _press("confirm", 2)
	_expect(await _until(func(): return main.battle.phase == "target"),
		"Fight asks for a target")
	await _shot("battle_target")
	await _press("confirm", 2)
	_expect(await _until(func(): return main.battle.phase != "target"),
		"the attack resolves")
	await _shot("battle_action")

	print("save")
	_expect(Gs.save_game(), "the journal saves")
	var gear_before := (Gs.party[1]["gear"] as Dictionary).duplicate()
	Gs.party = []
	_expect(Gs.load_game(), "the journal loads")
	_expect(Gs.party.size() == 3, "the party comes back")
	_expect((Gs.party[1]["gear"] as Dictionary) == gear_before, "equipment survives the round trip")

	print("")
	if failures.is_empty():
		print("SMOKE OK  (%d screenshots)" % shots)
	else:
		print("SMOKE FAILED (%d)" % failures.size())
		for f in failures:
			print("  - " + f)
	await _step(2)
	get_tree().quit(0 if failures.is_empty() else 1)
