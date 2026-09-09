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
	main.open_shop("amber")
	_expect(await _until(func(): return main.mode == "shop"), "the shop opens")
	await _shot("shop_wares")
	main.shop.set_tab(1)
	await _step(6)
	var stock: Array = main.shop.shop_stock()
	# gear_stock is keyed by shelf now, so this has to compare against the
	# shelf this counter sells, not against the number of shelves.
	_expect(stock.size() == Dat.gear_stock["amber"].size(),
		"the armoury lists every piece on its shelf (%d)" % stock.size())
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

	print("barrow")
	main.field.enter_map("barrow1", 20, 27)
	Gs.steps_to_encounter = 9999
	await _step(10)
	_expect(Gs.map_id == "barrow1", "the barrow loads")
	_expect(str(main.field.map.get("encounters", "")) == "barrow",
		"it draws from the barrow's own encounter table")
	_expect(Dat.encounters.has("barrow") and not Dat.encounters["barrow"].is_empty(),
		"that table has entries (%d)" % Dat.encounters.get("barrow", []).size())
	_expect(str(main.field.map.get("music", "")) == "barrow", "the barrow has its own theme")
	await _shot("barrow_upper")

	# The gate is a wall until the key turns up.
	Gs.flags["barrowKey"] = false
	_expect(main.field.solid_at(20, 13), "the gate is shut without the key")
	Gs.px = 20
	Gs.py = 14
	Gs.dir = "up"
	await _step(4)
	main.field.interact()
	await _step(4)
	_expect(not main.field.msg.is_empty(), "the gate says something when you try it")
	await _shot("barrow_gate")
	main.field.msg = {}

	# Take the key, and it opens.
	main.field.open_chest(33, 6)
	await _step(4)
	_expect(bool(Gs.flags.get("barrowKey", false)), "the east chamber holds the key")
	_expect(not main.field.solid_at(20, 13), "the gate opens once you have it")
	main.field.msg = {}

	# The floor below, and the chieftain on it.
	main.field.enter_map("barrow2", 18, 25)
	Gs.steps_to_encounter = 9999
	await _step(10)
	_expect(Gs.map_id == "barrow2", "the lower floor loads")
	var boss_here := false
	for n in main.field.npcs:
		if n["boss"]:
			boss_here = int(n["tx"]) == 18 and int(n["ty"]) == 8
	_expect(boss_here, "the chieftain waits at the bottom, not in a field")
	await _shot("barrow_deep")

	# A barrow encounter draws barrow monsters.
	var group := Dat.roll_encounter("barrow")
	var barrow_only := true
	for id in group:
		if not Dat.enemies.has(id):
			barrow_only = false
	_expect(barrow_only, "its encounters name real monsters (%s)" % ", ".join(group))
	main.start_encounter(["skeleton", "wight"], false)
	_expect(await _until(func(): return main.mode == "battle"), "the barrow's own monsters fight")
	await _until(func(): return main.battle.phase == "command")
	await _shot("barrow_battle")
	main.finish_battle("win", false)
	await _until(func(): return main.mode == "field")

	print("ending")
	# fade_to() is a no-op while a fade is already running, so an encounter
	# started mid-transition never begins. Wait for the screen to settle first.
	await _settle()
	Gs.flags["boss_down"] = false
	Gs.flags["seal_broken"] = false
	main.field.enter_map("barrow2", 18, 12)
	Gs.steps_to_encounter = 9999
	await _step(6)
	Gs.px = 18
	Gs.py = 7
	Gs.dir = "up"
	await _step(4)
	main.field.interact()
	await _step(4)
	_expect(not main.field.msg.is_empty(), "the ward in the floor can be read")
	main.field.msg = {}

	await _settle()
	main.start_encounter(["ogre"], true)
	_expect(await _until(func(): return main.mode == "battle"), "the chieftain fights")
	await _until(func(): return main.battle.phase != "intro")
	for e in main.battle.enemies:
		main.battle.apply_damage(e, 99999, false)
	_expect(await _until(func(): return main.battle.phase == "result"),
		"killing him ends the fight")
	_expect(bool(Gs.flags.get("seal_broken", false)), "his death breaks the ward")
	var pages := 0
	while main.mode == "battle" and main.battle.phase == "result" and pages < 30:
		await _press("confirm", 3)
		pages += 1
	_expect(pages < 30, "the victory window pages through")
	await _settle()
	_expect(await _until(func(): return main.mode == "ending"), "the chapter closes")
	_expect(Gs.map_id == "town", "and leaves the party in Rivenbrook")
	_expect(Gs.has_save(), "with the journal already written")
	await _shot("ending_beat")

	for i in 12:
		if main.ending.phase != "beats":
			break
		await _press("confirm", 3)
	_expect(main.ending.phase == "card", "the beats give way to the card")
	await _shot("ending_card")
	# The card holds for 0.6s before it will accept a confirm, so a player
	# mashing through the beats cannot skip past their own results.
	await _until(func(): return main.ending.t > 0.7)
	await _press("confirm", 6)
	_expect(main.ending.phase == "credits", "then the credits roll")
	await _shot("ending_credits")
	_expect(await _until(func(): return main.ending.phase == "hook", 3000),
		"and the credits reach the hook")
	await _shot("ending_hook")

	print("aftermath")
	main.field.enter_map("town", 20, 24)
	await _step(8)
	var reacted := false
	for n in main.field.npcs:
		if n["name"] == "Elder Halvard" and n.get("after", null) != null:
			reacted = true
	_expect(reacted, "the town has something new to say")
	await _shot("aftermath_town")

	print("chapter two")
	await _settle()
	Gs.flags["boss_down"] = true
	main.field.enter_map("shore", 3, 14)
	Gs.steps_to_encounter = 9999
	await _step(8)
	_expect(Gs.map_id == "shore", "the mere road loads")
	_expect(str(main.field.map.get("encounters", "")) == "shore",
		"with its own encounter table")
	var cold := Dat.roll_encounter("shore")
	var real := true
	for id in cold:
		if not Dat.enemies.has(id):
			real = false
	_expect(real, "that names real cold-country monsters (%s)" % ", ".join(cold))
	await _shot("ch2_road")

	main.field.enter_map("hollow", 21, 31)
	await _step(8)
	_expect(Gs.map_id == "hollow", "Hollowmere loads")
	var found := {"Bram": false, "Sera": false, "Armourer Fenn": false}
	for n in main.field.npcs:
		if found.has(n["name"]):
			found[n["name"]] = true
	_expect(found["Bram"] and found["Sera"], "Bram and Sera are waiting in it")
	await _shot("ch2_hollow")

	main.field.recruit("bram")
	main.field.msg = {}
	main.field.recruit("sera")
	main.field.msg = {}
	await _step(4)
	_expect(Gs.find_hero("bram") != null and Gs.find_hero("sera") != null,
		"both of them join")
	_expect(Gs.bench.size() == 1, "the fifth waits on the bench")
	var still_there := false
	for n in main.field.npcs:
		if n["name"] == "Bram":
			still_there = true
	_expect(not still_there, "and stop standing in the street")

	# The Hollowmere counter sells its own shelf.
	main.open_shop("hollow")
	await _step(6)
	_expect(main.mode == "shop", "the armourer opens")
	main.shop.set_tab(1)
	await _step(4)
	var shelf := main.shop.shop_stock()
	_expect(shelf.size() == Dat.gear_stock["hollow"].size(),
		"stocking cold-country work (%d pieces)" % shelf.size())
	await _shot("ch2_shop")
	main.close_shop()
	await _until(func(): return main.mode == "field")

	# Walking back onto the road with both of them: Bram stays.
	var pack_before := Gs.gear.size()
	main.field.enter_map("shore", 45, 14)
	Gs.steps_to_encounter = 9999
	await _step(8)
	_expect(not main.field.msg.is_empty(), "the road has something to say about it")
	await _shot("ch2_bram")
	var beats_read := 0
	while not main.field.msg.is_empty() and beats_read < 30:
		await _press("confirm", 3)
		beats_read += 1
	_expect(beats_read < 30, "the scene reads to the end")
	_expect(Gs.find_hero("bram") == null, "Bram stays behind")
	_expect(Gs.gear.size() > pack_before, "and leaves his kit with you")
	main.field.enter_map("hollow", 21, 31)
	await _step(6)
	main.field.enter_map("shore", 45, 14)
	await _step(8)
	_expect(main.field.msg.is_empty(), "and the scene does not play twice")

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
