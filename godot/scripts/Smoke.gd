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
var log_path := ""


func _ready() -> void:
	out_dir = OS.get_environment("SMOKE_OUT")
	if out_dir != "":
		# Godot block-buffers its own stdout when that is a pipe, so print()
		# tells a watching process nothing until the run exits - which is
		# exactly no use when the run is the thing that hangs. Every line goes
		# to a file as well, opened and closed per write so it is on disk
		# immediately.
		log_path = out_dir + "/progress.log"
		var f := FileAccess.open(log_path, FileAccess.WRITE)
		if f != null:
			f.store_line("smoke start")
			f.close()
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


## Press through whatever is on screen, the way a player reads it. Returns how
## many presses it took; the cap is the assertion that it ended.
func _read_msg(limit := 30) -> int:
	var pressed := 0
	while not main.field.msg.is_empty() and pressed < limit:
		await _press("confirm", 3)
		pressed += 1
	return pressed


## Talk to somebody: stand next to them, face them, press through what they
## say. Calling recruit() directly is not the same test - it passed for a
## while against a build where the conversation ended without ever running
## what it was for, so nobody actually joined.
func _talk_to(who: String) -> bool:
	for n in main.field.npcs:
		if n["name"] != who:
			continue
		# Hold them still for a moment. They wander, and a wanderer who takes
		# a step between being found and being spoken to is not there any more.
		n["cool"] = 999.0
		for step in [[0, 1, "up"], [0, -1, "down"], [1, 0, "left"], [-1, 0, "right"]]:
			var x: int = int(n["tx"]) + int(step[0])
			var y: int = int(n["ty"]) + int(step[1])
			if main.field.solid_at(x, y):
				continue
			Gs.px = x
			Gs.py = y
			Gs.dir = str(step[2])
			await _step(2)
			main.field.interact()
			await _step(2)
			# Standing next to somebody is not the same as reaching them: if
			# nothing opened, that side was no good and the next one gets a go.
			if main.field.msg.is_empty():
				continue
			await _read_msg()
			return true
		_say("    .. could not reach " + who)
		return false
	_say("    .. nobody called " + who + " is here")
	return false


## Press through a message until it is waiting on its choice - the last page,
## fully typed out, with the options up.
func _wait_for_choice(limit := 20) -> bool:
	var pressed := 0
	while pressed < limit:
		var m: Dictionary = main.field.msg
		if m.is_empty():
			return false
		var ch: Dictionary = m.get("choice", {})
		var lines: Array = m["lines"]
		var page := int(m["page"])
		if not ch.is_empty() and page == lines.size() - 1 \
				and float(m["chars"]) >= float((lines[page] as String).length()):
			return true
		await _press("confirm", 3)
		pressed += 1
	return false


## Roll the credits the way somebody who has seen them does: leaning on the
## confirm key. The hold-to-hurry does not register from a synthesised key
## event, so this takes the credits at their own pace and just gives them
## enough frames to get there - roughly eleven seconds of them.
func _roll_credits(limit := 400) -> bool:
	var pressed := 0
	while main.ending.phase == "credits" and pressed < limit:
		await _press("confirm", 2)
		pressed += 1
	return main.ending.phase == "hook"


func _shot(name: String) -> void:
	_say("    .. shot " + name)
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


func _say(line: String) -> void:
	print(line)
	if log_path == "":
		return
	var f := FileAccess.open(log_path, FileAccess.READ_WRITE)
	if f == null:
		return
	f.seek_end()
	f.store_line(line)
	f.close()


func _expect(ok: bool, what: String) -> void:
	_say(("  ok   " if ok else "  FAIL ") + what)
	if not ok:
		failures.append(what)


func _run() -> void:
	await _step(8)

	_say("title")
	_expect(main.mode == "title", "boots to the title screen")
	await _shot("title")

	_say("field")
	await _press("confirm", 2)           # New Game
	_expect(await _until(func(): return main.mode == "field"),
		"New Game reaches the field")
	_expect(Gs.party.size() == 3, "three characters in the party")
	_expect(Gs.map_id == "town", "starts in town")
	var pics: Dictionary = Art.pictures_for("town")
	_expect(pics.has("base") and pics.has("over"), "the town draws from its Blender picture and overlay")
	_expect(pics.has("water") and (pics["water"] as Array).size() == 4, "with four frames of water")
	_expect(not Art.pictures_for("barrow1").has("water"), "and the barrow has no water to animate")
	await _shot("field")

	_say("equipment")
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

	_say("menu")
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

	_say("shop")
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

	_say("battle")
	main.start_encounter(["goblin", "goblin", "slime"])
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

	_say("barrow")
	# The field has to be in charge for a beat to play out: finish the fight
	# first, the way a player would, rather than poking the field from inside
	# the battle.
	main.finish_battle("win", "")
	await _settle()
	_expect(await _until(func(): return main.mode == "field"), "the fight ends")
	main.field.enter_map("barrow1", 20, 27)
	Gs.steps_to_encounter = 9999
	await _step(10)
	_expect(Gs.map_id == "barrow1", "the barrow loads")
	# Aldric's moment: the re-cut sign, and whether the town gets word.
	_expect(await _wait_for_choice(), "the barrow mouth asks whether to send word")
	await _read_msg()
	_expect(bool(Gs.flags.get("aldricWarned", false)), "and the runner goes back to Rivenbrook")
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
	# Lyra's moment: a minute with the letters before anyone breaks them.
	_expect(str(main.field.msg.get("speaker", "")) == "Lyra" and await _wait_for_choice(),
		"Lyra asks for a minute with the letters")
	await _read_msg()
	_expect(bool(Gs.flags.get("lyraRead", false)), "and reads the name cut into them")
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
	main.start_encounter(["skeleton", "wight"])
	_expect(await _until(func(): return main.mode == "battle"), "the barrow's own monsters fight")
	await _until(func(): return main.battle.phase == "command")
	await _shot("barrow_battle")
	# The lantern: lit to begin with; a cold thing in the dark is shrouded;
	# any hero can spend a turn to light it again.
	_expect(main.battle.lantern, "the lantern is lit when a fight starts")
	var guard: Dictionary = main.battle.enemies[0]
	_expect(bool(guard.get("cold", false)), "the barrow's dead are of the cold")
	guard["hp"] = 1000
	guard["maxhp"] = 1000
	main.battle.lantern = false
	main.battle.apply_damage(guard, 100, false)
	_expect(int(guard["hp"]) == 950, "a cold thing in the dark takes half")
	var can_light := false
	for cmd in main.battle.commands_for(Gs.party[0]):
		if cmd["id"] == "light":
			can_light = true
	_expect(can_light, "and Light is on the menu while it is out")
	main.battle.resolve_hero_action(Gs.party[0], {"kind": "light"})
	_expect(main.battle.lantern, "and lighting it works")
	main.finish_battle("win", "")
	await _until(func(): return main.mode == "field")

	_say("ending")
	# fade_to() is a no-op while a fade is already running, so an encounter
	# started mid-transition never begins. Wait for the screen to settle first.
	await _settle()
	Gs.flags["bossDown"] = false
	Gs.flags["sealBroken"] = false
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
	main.start_encounter(["ogre"], "chieftain")
	_expect(await _until(func(): return main.mode == "battle"), "the chieftain fights")
	await _until(func(): return main.battle.phase != "intro")
	_expect(not main.battle.lantern, "in the dark: the barrow starts with the lantern out")
	var exp_total := 0
	for e in main.battle.enemies:
		exp_total += int(e["exp"])
	var before := []
	for h in Gs.party:
		before.append([int(h["exp"]), int(h["lv"]), bool(h["alive"])])
	for e in main.battle.enemies:
		main.battle.apply_damage(e, 99999, false)
	_expect(await _until(func(): return main.battle.phase == "result"),
		"killing him ends the fight")
	var banked := true
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		if not before[i][2]:
			continue
		if int(h["lv"]) <= before[i][1] and int(h["exp"]) != before[i][0] + exp_total:
			banked = false
	_expect(banked, "every survivor banks the EXP the card shows")
	_expect(bool(Gs.flags.get("sealBroken", false)), "his death breaks the ward")
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
	var remembers := false
	var wall_lit := false
	for b in main.ending.beats():
		var text := " ".join(b["lines"])
		if text.find("VAIL") >= 0:
			remembers = true
		if text.find("Every lamp on the wall") >= 0:
			wall_lit = true
	_expect(remembers, "and the ending remembers what Lyra read")
	_expect(wall_lit, "and that the wall was lit for your return")
	await _shot("ending_card")
	# The card holds for 0.6s before it will accept a confirm, so a player
	# mashing through the beats cannot skip past their own results.
	await _until(func(): return main.ending.t > 0.7)
	await _press("confirm", 6)
	_expect(main.ending.phase == "credits", "then the credits roll")
	await _shot("ending_credits")
	_expect(await _roll_credits(), "and the credits reach the hook")
	await _shot("ending_hook")

	_say("aftermath")
	# The credits leave the game sitting in the ending, and the player comes
	# back through Continue. Skipping that and poking the field directly is
	# not the same thing: another mode still owns the screen and the input,
	# so the field never updates and nothing a player does actually happens.
	main.begin_game(true)
	await _until(func(): return main.mode == "field")
	_expect(main.mode == "field", "Continue picks the game back up in the field")
	# Mira's moment fires the moment you are back in charge in town: Tam,
	# shivering, and whether the party stays the night.
	await _step(8)
	_expect(str(main.field.msg.get("speaker", "")) == "Mira" and await _wait_for_choice(),
		"Mira asks to sit with the boy")
	await _read_msg()
	_expect(bool(Gs.flags.get("miraTended", false)), "and stays the night")
	main.field.enter_map("town", 20, 24)
	await _step(8)
	var reacted := false
	var tam_still := false
	for n in main.field.npcs:
		if n["name"] == "Elder Halvard" and not main.field.npc_stage(n).is_empty():
			reacted = true
		if n["name"] == "Tam" and not bool(n["wander"]):
			tam_still = true
	_expect(reacted, "the town has something new to say")
	_expect(tam_still, "and Tam has stopped wandering")
	_expect(Art.picture_variant("town") == "cold", "and the town wears its frost")
	await _shot("aftermath_town")

	_say("chapter two")
	await _settle()
	_expect(main.mode == "field", "and the field is the one taking input")
	Gs.flags["bossDown"] = true
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

	var spoke_to_bram := await _talk_to("Bram")
	var spoke_to_sera := await _talk_to("Sera")
	_expect(spoke_to_bram and spoke_to_sera, "you can walk up to both of them")
	await _step(4)
	_expect(Gs.find_hero("bram") != null and Gs.find_hero("sera") != null,
		"and asking is what makes them join")
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
	var shelf: Array = main.shop.shop_stock()
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
	var beats_read := await _read_msg()
	_expect(beats_read < 30, "the scene reads to the end")
	_expect(Gs.find_hero("bram") == null, "Bram stays behind")
	_expect(Gs.gear.size() > pack_before, "and leaves his kit with you")
	main.field.enter_map("hollow", 21, 31)
	await _step(6)
	main.field.enter_map("shore", 45, 14)
	await _step(8)
	# Coming back the same way does not play his goodbye again. The road is
	# not silent, though - she has the next word, and that is the next test.
	_expect(str(main.field.msg.get("speaker", "")) != "Bram",
		"and the scene does not play twice")

	# Sera, in four movements. Worth running in the engine rather than trusting
	# the browser for it: it is all message plumbing - a gift that has to land
	# in the pack, a question whose answer has to stick - and message plumbing
	# is exactly where this build was thin.
	_expect(not main.field.msg.is_empty(), "the road gives her the first word")
	await _read_msg()
	_expect(bool(Gs.flags.get("seraDusk", false)), "and it stays said")

	main.field.enter_map("hollow", 21, 31)
	await _step(8)
	_expect(not main.field.msg.is_empty(), "she gives you something in town")
	await _read_msg()
	_expect(int(Gs.gear.get("lamp_key", 0)) > 0, "and the lamp key lands in the pack")
	_expect(Gs.can_wear(Gs.find_hero("aldric"), Dat.gear["lamp_key"])
		and not Gs.can_wear(Gs.find_hero("sera"), Dat.gear["lamp_key"]),
		"and it is his to wear, nobody else's")

	main.field.enter_map("shore", 45, 14)
	await _step(8)
	_expect(await _wait_for_choice(), "the road asks you something")
	await _shot("ch2_sera")
	await _press("confirm")
	await _read_msg()
	_expect(bool(Gs.flags.get("seraClose", false)), "sitting with her is an answer")

	main.field.enter_map("hollow", 21, 31)
	await _step(8)
	await _read_msg()
	_expect(bool(Gs.flags.get("seraKeptTwice", false)),
		"and she answers the question she would not answer")
	_expect(not bool(Gs.flags.get("seraKeptQuiet", false)),
		"and the other answer stays unsaid")

	_say("the mere")
	# The way down, and the two floors under it. Everything from here is the
	# chapter closing itself, which is the part that used to be hardwired to
	# exactly one boss and exactly one ending.
	main.field.enter_map("hollow", 21, 31)
	await _step(8)
	await _read_msg()
	_expect(bool(Gs.flags.get("mereOpened", false)), "she opens the keepers' hatch")
	_expect(not main.field.solid_at(20, 8), "and it is a way through now, not a wall")

	main.field.enter_map("mere1", 20, 25)
	Gs.steps_to_encounter = 9999
	await _step(8)
	_expect(Gs.map_id == "mere1", "the keepers' road loads")
	_expect(not main.field.msg.is_empty(), "and she counts the lamps on it")
	await _read_msg()
	await _shot("mere_road")
	var deep := []
	for id in Dat.roll_encounter("mere"):
		deep.append(str(Dat.enemies[id]["name"]))
	_expect(not deep.is_empty(), "with monsters of its own (%s)" % ", ".join(deep))

	main.field.enter_map("mere2", 18, 22)
	Gs.steps_to_encounter = 9999
	await _step(8)
	_expect(Gs.map_id == "mere2", "the cutting floor loads")
	await _read_msg()
	var kestrel := false
	var warden := false
	for n in main.field.npcs:
		if str(n["name"]) == "Kestrel Vail":
			kestrel = true
		if str(n["boss"]) == "drowned":
			warden = true
	_expect(kestrel, "Kestrel is at the ward")
	_expect(warden, "and the Warden is standing on it")
	await _shot("mere_floor")

	Gs.px = 18
	Gs.py = 7
	Gs.dir = "up"
	await _step(2)
	main.field.on_step_complete()
	await _step(6)
	_expect(str(main.field.msg.get("speaker", "")) == "Drowned Warden",
		"stepping onto the letters stands it up")
	await _shot("mere_challenge")
	_expect(await _wait_for_choice(), "and it asks whether you are staying")
	await _press("confirm")
	_expect(await _until(func(): return main.mode == "battle"), "the Warden fights")
	await _until(func(): return main.battle.phase != "intro")
	await _shot("mere_battle")
	for e in main.battle.enemies:
		main.battle.apply_damage(e, 99999, false)
	_expect(await _until(func(): return main.battle.phase == "result"),
		"killing it ends the fight")
	_expect(bool(Gs.flags.get("wardenDown", false)), "and the ward goes quiet")
	var mere_pages := 0
	while main.mode == "battle" and main.battle.phase == "result" and mere_pages < 30:
		await _press("confirm", 3)
		mere_pages += 1
	_expect(mere_pages < 30, "the victory window pages through")
	await _settle()
	_expect(await _until(func(): return main.mode == "ending"), "the chapter closes")
	_expect(main.ending.which == "two", "on chapter two's ending, not chapter one's")
	_expect(Gs.map_id == "hollow", "and leaves you up in Hollowmere")
	await _shot("end2_beat")
	for i in 30:
		if main.ending.phase != "beats":
			break
		main.ending.chars = 9999.0
		await _press("confirm", 3)
	_expect(main.ending.phase != "beats", "the beats give way to the card")
	await _shot("end2_card")
	await _until(func(): return main.ending.t > 0.7)
	await _press("confirm", 6)
	_expect(main.ending.phase == "credits", "and chapter two's credits roll")
	_expect(await _roll_credits(), "all the way to the next hook")
	_expect(str(main.ending.ending().get("hook", "")).find("Mere Road") >= 0,
		"which is the road south, and what is on it")
	await _shot("end2_hook")

	_say("save")
	_expect(Gs.save_game(), "the journal saves")
	var gear_before := (Gs.party[1]["gear"] as Dictionary).duplicate()
	Gs.party = []
	Gs.bench = []
	_expect(Gs.load_game(), "the journal loads")
	_expect(Gs.party.size() == 3, "the party comes back")
	# The bench is the half of the roster a save could quietly drop: nothing
	# on screen would look wrong until you opened the menu and found her gone.
	_expect(Gs.bench.size() == 1, "and so does the bench")
	_expect(Gs.find_hero("sera") != null, "with Sera still on it")
	_expect(Gs.find_hero("bram") == null, "and Bram still up on the road")
	_expect((Gs.party[1]["gear"] as Dictionary) == gear_before, "equipment survives the round trip")
	# The game writes its own save at the milestones, in a file of its own.
	_expect(FileAccess.file_exists(Gs.AUTOSAVE_PATH), "the game has been autosaving")
	var written = JSON.parse_string(FileAccess.get_file_as_string(Gs.SAVE_PATH))
	_expect(typeof(written) == TYPE_DICTIONARY and int(written.get("version", 0)) == 2,
		"the journal carries a version")
	# A save that cannot be trusted is refused with a reason, not loaded and
	# left to misbehave later. Both files are broken so nothing sound is left.
	var kept_save := FileAccess.get_file_as_string(Gs.SAVE_PATH)
	var kept_auto := FileAccess.get_file_as_string(Gs.AUTOSAVE_PATH)
	var jf := FileAccess.open(Gs.SAVE_PATH, FileAccess.WRITE)
	jf.store_string(JSON.stringify({"version": 2, "party": [{"id": "nobody", "lv": 1, "exp": 0, "hp": 1, "mp": 0}],
		"gil": 0, "map_id": "town", "px": 1, "py": 1}))
	jf.close()
	jf = FileAccess.open(Gs.AUTOSAVE_PATH, FileAccess.WRITE)
	jf.store_string("not json at all")
	jf.close()
	_expect(not Gs.has_save(), "a broken journal is not offered")
	var why := Gs.save_problem()
	_expect(why.contains("nobody we know"), "and the title says why")
	_expect(not Gs.load_game(), "and cannot be loaded")
	jf = FileAccess.open(Gs.SAVE_PATH, FileAccess.WRITE)
	jf.store_string(JSON.stringify({"party": [{"id": "aldric", "lv": 3, "exp": 10, "hp": 20, "mp": 5}],
		"gil": 5, "map_id": "town", "px": 2, "py": 2, "bag": {"potion": 2, "gone_item": 1}}))
	jf.close()
	DirAccess.remove_absolute(Gs.AUTOSAVE_PATH)
	_expect(Gs.has_save() and Gs.load_game() and Gs.party.size() == 1 \
		and int(Gs.bag.get("potion", 0)) == 2 and not Gs.bag.has("gone_item"),
		"an old journal without a version still loads, minus what the game no longer has")
	jf = FileAccess.open(Gs.SAVE_PATH, FileAccess.WRITE)
	jf.store_string(kept_save)
	jf.close()
	jf = FileAccess.open(Gs.AUTOSAVE_PATH, FileAccess.WRITE)
	jf.store_string(kept_auto)
	jf.close()
	Gs.load_game()

	if failures.is_empty():
		_say("SMOKE OK  (%d screenshots)" % shots)
	else:
		_say("SMOKE FAILED (%d)" % failures.size())
		for f in failures:
			_say("  - " + f)
	await _step(2)
	get_tree().quit(0 if failures.is_empty() else 1)
