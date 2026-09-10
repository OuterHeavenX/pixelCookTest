class_name BattleMode
extends RefCounted
## Wait-mode ATB combat, the way Final Fantasy IV plays on the patient side:
## gauges fill in real time and freeze while a command window is open.

const ATB_RATE := 5.2
var main

var phase := "intro"
var t := 0.0
var intro := 0.0
var enemies := []
var is_boss := ""   ## which boss, by id; empty for an ordinary fight
var backdrop := "dusk"
var escapable := true

var actor = null
var pending := []
var acting := {}
var pending_action := {}

var cmd := 0
var sub := ""
var sub_index := 0
var target_side := "enemy"
var target := 0

var banner := ""
var banner_t := 0.0
var popups := []
var fx := []
var shake := 0.0
var flash := 0.0

var result := ""
var result_lines := []
var result_page := 0


func _init(owner) -> void:
	main = owner


func start(group: Array, boss: String) -> void:
	phase = "intro"
	intro = 0.6
	t = 0.0
	is_boss = boss
	# The backdrop follows the place you were standing, so a fight in the
	# barrow is not lit by a sunset that is four floors above you.
	backdrop = "night" if boss != "" else str(main.field.map.get("battle_bg", "dusk"))
	escapable = boss == ""
	popups = []
	fx = []
	shake = 0.0
	flash = 1.0
	actor = null
	acting = {}
	pending = []
	cmd = 0
	sub = ""
	sub_index = 0
	banner = str(Dat.bosses[boss]["banner"]) if boss != "" else "Monsters appear!"
	banner_t = 2.2

	enemies = []
	var counts := {}
	for i in group.size():
		var id: String = group[i]
		counts[id] = int(counts.get(id, 0)) + 1
		var e: Dictionary = (Dat.enemies[id] as Dictionary).duplicate(true)
		e["id"] = id
		e["maxhp"] = int(e["hp"])
		e["hp"] = int(e["hp"])
		e["alive"] = true
		e["atb"] = randf_range(0.0, 30.0)
		e["hurt"] = 0.0
		e["dying"] = 0.0
		e["offset"] = 0.0
		e["index"] = i
		var repeats := 0
		for g in group:
			if g == id:
				repeats += 1
		e["label"] = e["name"]
		if repeats > 1:
			e["label"] = "%s %s" % [e["name"], String.chr(64 + int(counts[id]))]
		enemies.append(e)

	for i in Gs.party.size():
		Gs.party[i]["slot"] = i
	for h in Gs.party:
		h["atb"] = randf_range(0.0, 45.0) if h["alive"] else 0.0
		h["defending"] = false
		h["hurt"] = 0.0
		h["offset"] = 0.0
	Snd.play("battle")


func living_enemies() -> Array:
	return enemies.filter(func(e): return e["alive"])


## The backdrop's meadow starts about 6px below the geometric horizon, so the
## front of the line stands on grass rather than in the treeline.
## The fight is composed as a 320-wide stage on top of a HUD glued to the
## bottom edge. On a wider view the stage is centred and the backdrop shows
## more world either side; on a taller one the sky above it gets deeper.
const HUD_H := 64


func stage_x() -> float:
	return roundf((Art.VW - 320.0) / 2.0)


func stage_floor() -> float:
	return float(Art.VH - HUD_H)


func hero_slot(i: int) -> Vector2:
	return Vector2(stage_x() + 266 - i * 16, stage_floor() - 66 + i * 12)


## Humanoid monsters are drawn at hero scale; beasts and the boss stay chunky.
## How big a monster stands, from the height its data asks for rather than from
## a blanket multiplier. Whole steps only: a monster at 1.5x lands half its
## pixels on double size and half on single, and the sprite crawls.
func enemy_scale(e: Dictionary) -> float:
	return Art.scale_for(e["sprite"], float(e.get("height", 32)), [1.0, 2.0, 3.0])


## Enemies are baseline-anchored so tall and short monsters share a ground line
## and none of them dips behind the HUD.
func enemy_slot(e: Dictionary, i: int, n: int) -> Dictionary:
	var size := Art.frame_size(e["sprite"])
	var z := enemy_scale(e)
	var w := size.x * z
	var h := size.y * z
	var cols: int = mini(3, n)
	var col := i % cols
	var row: int = i / cols
	# Pack the line from the monsters' own widths. A fixed 48px column was
	# spaced for sprites drawn at double size; once they were sized honestly it
	# left them scattered across the field with holes between them.
	var x := stage_x() + 30.0 + row * 20.0
	for k in col:
		var idx := row * cols + k
		if idx < enemies.size():
			var prev: Dictionary = enemies[idx]
			x += Art.frame_size(prev["sprite"]).x * enemy_scale(prev) + 16.0
		else:
			x += 48.0
	var base_y := stage_floor() - 24.0 + col * 8.0 - row * 20.0
	return {"x": x, "y": base_y - h, "w": w, "h": h, "base_y": base_y}


func enemy_center(e: Dictionary) -> Vector2:
	var i := int(e["index"])
	var s := enemy_slot(e, i, enemies.size())
	return Vector2(float(s["x"]) + float(s["w"]) / 2.0, float(s["y"]))


# --- mechanics --------------------------------------------------------------

func phys_damage(attacker: Dictionary, victim: Dictionary, mult := 1.0) -> Dictionary:
	var atk := float(attacker["atk"]) * mult
	var dfn := float(victim["def"]) * (1.9 if bool(victim.get("defending", false)) else 1.0)
	var dmg := int(round((atk * 2.2 - dfn * 1.1) * randf_range(0.9, 1.12)))
	dmg = maxi(1, dmg)
	var crit := randf() < 0.07
	if crit:
		dmg = int(round(dmg * 1.9))
	# An elemental weapon carries its element into the swing, so the Flame
	# Brand is worth the walk if the thing in front of you hates fire.
	var weak := false
	if attacker.has("gear"):
		var w = Gs.equipped(attacker, "weapon")
		if w != null and w.get("element", null) != null \
				and victim.get("weak", null) == w["element"]:
			weak = true
			dmg = int(round(dmg * 1.5))
	return {"dmg": dmg, "crit": crit, "weak": weak}


func magic_damage(caster: Dictionary, victim: Dictionary, spell: Dictionary) -> Dictionary:
	var dmg := int(round((float(caster["mag"]) * 1.6 + float(spell["power"])) * randf_range(0.92, 1.1)))
	var weak: bool = victim.get("weak", null) != null and spell.get("element", null) == victim.get("weak")
	if weak:
		dmg = int(round(dmg * 1.6))
	dmg = maxi(1, dmg - int(round(float(victim["def"]) * 0.35)))
	return {"dmg": dmg, "weak": weak}


func popup(text: String, pos: Vector2, color := Color.WHITE) -> void:
	popups.append({"text": text, "x": pos.x, "y": pos.y, "color": color, "t": 0.0, "life": 1.05})


func add_fx(kind: String, pos: Vector2, life := 0.55) -> void:
	fx.append({"kind": kind, "x": pos.x, "y": pos.y, "t": 0.0, "life": life})


func _target_anchor(victim: Dictionary, is_hero: bool) -> Vector2:
	if is_hero:
		return hero_slot(int(victim["slot"])) + Vector2(8, 0)
	return enemy_center(victim)


func apply_damage(victim: Dictionary, dmg: int, is_hero: bool, crit := false, weak := false) -> void:
	victim["hp"] = maxi(0, int(victim["hp"]) - dmg)
	victim["hurt"] = 0.28
	var pos := _target_anchor(victim, is_hero)
	var color := Color.WHITE
	if crit:
		color = Color("#ffd75a")
	elif weak:
		color = Color("#8fe8ff")
	popup(str(dmg), pos + Vector2(0, -6), color)
	if crit:
		popup("CRITICAL", pos + Vector2(0, -18), Color("#ffd75a"))
	elif weak:
		popup("WEAK", pos + Vector2(0, -18), Color("#8fe8ff"))
	shake = max(shake, 5.0 if crit else 3.0)
	if int(victim["hp"]) <= 0:
		victim["alive"] = false
		if is_hero:
			victim["atb"] = 0.0
		else:
			victim["dying"] = 0.6
		Snd.sfx("ko")


func heal_target(victim: Dictionary, amount: int, is_hero: bool) -> void:
	var before := int(victim["hp"])
	victim["hp"] = mini(int(victim["maxhp"]), before + amount)
	popup("+%d" % (int(victim["hp"]) - before),
		_target_anchor(victim, is_hero) + Vector2(0, -6), Color("#8fffa8"))


func commands_for(h: Dictionary) -> Array:
	var list := [{"id": "fight", "label": "Fight"}]
	if (h["spells"] as Array).size() > 0:
		list.append({"id": "magic", "label": "Magic"})
	list.append({"id": "item", "label": "Item"})
	list.append({"id": "guard", "label": "Guard"})
	list.append({"id": "run", "label": "Run"})
	return list


func flash_banner(text: String) -> void:
	banner = text
	banner_t = 1.4


# --- update -----------------------------------------------------------------

func update(dt: float) -> void:
	t += dt
	Gs.playtime += dt
	banner_t = max(0.0, banner_t - dt)
	shake = max(0.0, shake - dt * 22.0)
	flash = max(0.0, flash - dt * 2.2)

	var live_popups := []
	for p in popups:
		p["t"] = float(p["t"]) + dt
		if float(p["t"]) < float(p["life"]):
			live_popups.append(p)
	popups = live_popups

	var live_fx := []
	for f in fx:
		f["t"] = float(f["t"]) + dt
		if float(f["t"]) < float(f["life"]):
			live_fx.append(f)
	fx = live_fx

	for e in enemies:
		e["hurt"] = max(0.0, float(e["hurt"]) - dt)
		if float(e["dying"]) > 0.0:
			e["dying"] = max(0.0, float(e["dying"]) - dt)
		e["offset"] = lerp(float(e["offset"]), 0.0, min(1.0, dt * 8.0))
	for h in Gs.party:
		h["hurt"] = max(0.0, float(h["hurt"]) - dt)
		h["offset"] = lerp(float(h["offset"]), 0.0, min(1.0, dt * 8.0))

	# The side that has run out ends the fight, whichever settled phase we are
	# in. This used to be checked only while gauges were filling, so killing the
	# last enemy with a command window open left a battle that could never end -
	# nothing does that today, but nothing should be able to.
	if phase == "active" or phase == "command" or phase == "target":
		if living_enemies().is_empty():
			begin_victory()
			return
		if Gs.living_heroes().is_empty():
			begin_defeat()
			return

	match phase:
		"intro":
			intro -= dt
			if intro <= 0.0:
				phase = "active"
		"active":
			update_atb(dt)
		"command":
			update_command(dt)
		"target":
			update_targeting(dt)
		"action":
			update_action(dt)
		"result":
			update_result(dt)


func _queued(h: Dictionary) -> bool:
	for x in pending:
		if is_same(x, h):
			return true
	return false


func update_atb(dt: float) -> void:
	if living_enemies().is_empty():
		begin_victory()
		return
	if Gs.living_heroes().is_empty():
		begin_defeat()
		return

	for h in Gs.party:
		if not h["alive"]:
			continue
		h["atb"] = min(100.0, float(h["atb"]) + float(h["spd"]) * ATB_RATE * dt)
		if float(h["atb"]) >= 100.0 and not _queued(h):
			pending.append(h)
	for e in living_enemies():
		e["atb"] = min(100.0, float(e["atb"]) + float(e["spd"]) * ATB_RATE * dt)
		if float(e["atb"]) >= 100.0:
			e["atb"] = 0.0
			begin_enemy_action(e)
			return

	# A hero knocked out while queued loses the turn.
	pending = pending.filter(func(h): return h["alive"])
	if not pending.is_empty():
		actor = pending[0]
		actor["defending"] = false
		cmd = 0
		sub = ""
		sub_index = 0
		phase = "command"


func update_command(dt: float) -> void:
	var h: Dictionary = actor
	if sub == "":
		var cmds := commands_for(h)
		if Inp.nav("up", dt):
			cmd = (cmd + cmds.size() - 1) % cmds.size()
			Snd.sfx("cursor")
		if Inp.nav("down", dt):
			cmd = (cmd + 1) % cmds.size()
			Snd.sfx("cursor")
		if Inp.tap("confirm"):
			var id: String = cmds[cmd]["id"]
			Snd.sfx("confirm")
			if id == "fight":
				begin_targeting("enemy", {"kind": "fight"})
			elif id == "guard":
				choose_action({"kind": "guard"})
			elif id == "run":
				choose_action({"kind": "run"})
			else:
				sub = id
				sub_index = 0
		return

	var entries := sub_entries(h)
	if Inp.tap("cancel"):
		sub = ""
		Snd.sfx("cancel")
		return
	if entries.is_empty():
		if Inp.tap("confirm"):
			sub = ""
			Snd.sfx("cancel")
		return
	if Inp.nav("up", dt):
		sub_index = (sub_index + entries.size() - 1) % entries.size()
		Snd.sfx("cursor")
	if Inp.nav("down", dt):
		sub_index = (sub_index + 1) % entries.size()
		Snd.sfx("cursor")
	if not Inp.tap("confirm"):
		return

	if sub == "magic":
		var spell_id: String = entries[sub_index]["id"]
		var sp: Dictionary = Dat.spells[spell_id]
		if int(h["mp"]) < int(sp["mp"]):
			Snd.sfx("cancel")
			flash_banner("Not enough MP!")
			return
		Snd.sfx("confirm")
		var act := {"kind": "magic", "spell_id": spell_id}
		var scope: String = sp["target"]
		if scope == "enemy":
			begin_targeting("enemy", act)
		elif scope == "ally":
			begin_targeting("ally", act)
		else:
			choose_action(act)
	else:
		var item_id: String = entries[sub_index]["id"]
		Snd.sfx("confirm")
		var side := "enemy" if Dat.items[item_id]["kind"] == "damage" else "ally"
		begin_targeting(side, {"kind": "item", "item_id": item_id})


func sub_entries(h: Dictionary) -> Array:
	if sub == "magic":
		var out := []
		for id in h["spells"]:
			out.append({"id": id})
		return out
	return Gs.bag_list()


func begin_targeting(side: String, action: Dictionary) -> void:
	target_side = side
	pending_action = action
	if side == "enemy":
		var alive := living_enemies()
		target = int(alive[0]["index"]) if not alive.is_empty() else 0
	else:
		target = int(actor["slot"])
	phase = "target"


func _target_valid(i: int) -> bool:
	if target_side == "enemy":
		return bool(enemies[i]["alive"])
	# Revival is the one thing that may be aimed at a fallen ally.
	if pending_action.get("kind", "") == "item":
		if Dat.items[pending_action["item_id"]]["kind"] == "revive":
			return true
	elif pending_action.get("kind", "") == "magic":
		if Dat.spells[pending_action["spell_id"]]["kind"] == "revive":
			return true
	return bool(Gs.party[i]["alive"])


func update_targeting(dt: float) -> void:
	if Inp.tap("cancel"):
		phase = "command"
		Snd.sfx("cancel")
		return
	var count := enemies.size() if target_side == "enemy" else Gs.party.size()
	var step := 0
	if Inp.nav("up", dt) or Inp.nav("left", dt):
		step = -1
	elif Inp.nav("down", dt) or Inp.nav("right", dt):
		step = 1
	if step != 0:
		for k in range(1, count + 1):
			var i := ((target + step * k) % count + count) % count
			if _target_valid(i):
				target = i
				Snd.sfx("cursor")
				break
	if Inp.tap("confirm"):
		Snd.sfx("confirm")
		var act := pending_action.duplicate()
		act["target"] = enemies[target] if target_side == "enemy" else Gs.party[target]
		choose_action(act)


func choose_action(action: Dictionary) -> void:
	var h: Dictionary = actor
	pending = pending.filter(func(x): return not is_same(x, h))
	h["atb"] = 0.0
	acting = {"who": h, "is_hero": true, "action": action, "t": 0.0, "stage": 0,
		"hold": 0.5, "fled": false}
	phase = "action"
	actor = null
	sub = ""


func begin_enemy_action(e: Dictionary) -> void:
	var ai: Array = e["ai"]
	var total := 0.0
	for o in ai:
		total += float(o["w"])
	var r := randf() * total
	var choice: Dictionary = ai[0]
	for o in ai:
		r -= float(o["w"])
		if r <= 0.0:
			choice = o
			break
	var action := {"kind": choice["act"]}
	if choice.has("spell"):
		action["spell_id"] = choice["spell"]
	acting = {"who": e, "is_hero": false, "action": action, "t": 0.0, "stage": 0,
		"hold": 0.5, "fled": false}
	phase = "action"


## Actions play out in three beats: step in, resolve, step back.
func update_action(dt: float) -> void:
	acting["t"] = float(acting["t"]) + dt
	var who: Dictionary = acting["who"]
	var dir_sign := -1.0 if bool(acting["is_hero"]) else 1.0
	var elapsed := float(acting["t"])
	var stage := int(acting["stage"])

	if stage == 0:
		who["offset"] = lerp(0.0, 14.0 * dir_sign, min(1.0, elapsed / 0.18))
		if elapsed >= 0.18:
			acting["stage"] = 1
			acting["t"] = 0.0
			resolve_action()
	elif stage == 1:
		if elapsed >= float(acting["hold"]):
			acting["stage"] = 2
			acting["t"] = 0.0
	else:
		who["offset"] = lerp(14.0 * dir_sign, 0.0, min(1.0, elapsed / 0.16))
		if elapsed >= 0.16:
			who["offset"] = 0.0
			var fled := bool(acting["fled"])
			acting = {}
			if fled:
				end_battle("fled")
				return
			if living_enemies().is_empty():
				begin_victory()
				return
			if Gs.living_heroes().is_empty():
				begin_defeat()
				return
			phase = "active"


func resolve_action() -> void:
	if bool(acting["is_hero"]):
		resolve_hero_action(acting["who"], acting["action"])
	else:
		resolve_enemy_action(acting["who"], acting["action"])


func resolve_hero_action(h: Dictionary, act: Dictionary) -> void:
	var kind: String = act["kind"]

	if kind == "guard":
		h["defending"] = true
		flash_banner("%s takes a guarded stance." % h["name"])
		Snd.sfx("cursor")
		acting["hold"] = 0.35
		return

	if kind == "run":
		if not escapable:
			flash_banner("There is no escape!")
			Snd.sfx("cancel")
			acting["hold"] = 0.7
			return
		var heroes := Gs.living_heroes()
		var foes := living_enemies()
		var party_spd := 0.0
		for x in heroes:
			party_spd += float(x["spd"])
		party_spd /= max(1, heroes.size())
		var foe_spd := 0.0
		for x in foes:
			foe_spd += float(x["spd"])
		foe_spd /= max(1, foes.size())
		if randf() < clamp(0.35 + (party_spd - foe_spd) * 0.06, 0.2, 0.9):
			flash_banner("Got away safely!")
			acting["fled"] = true
			acting["hold"] = 0.5
		else:
			flash_banner("Couldn't escape!")
			acting["hold"] = 0.6
		return

	if kind == "fight":
		var foe: Dictionary = act["target"]
		if not bool(foe["alive"]):
			var alive := living_enemies()
			if alive.is_empty():
				return
			foe = alive[0]
		add_fx("slash", enemy_center(foe))
		Snd.sfx("hit")
		var roll := phys_damage(h, foe)
		apply_damage(foe, int(roll["dmg"]), false, bool(roll["crit"]), bool(roll["weak"]))
		foe["offset"] = 6.0
		flash_banner("%s attacks!" % h["name"])
		acting["hold"] = 0.45
		return

	if kind == "magic":
		var sp: Dictionary = Dat.spells[act["spell_id"]]
		h["mp"] = maxi(0, int(h["mp"]) - int(sp["mp"]))
		flash_banner("%s casts %s!" % [h["name"], sp["name"]])
		var spell_kind: String = sp["kind"]
		var restorative := spell_kind in ["heal", "healAll", "revive"]
		Snd.sfx("heal" if restorative else "magic")
		acting["hold"] = 0.75

		if spell_kind == "attack":
			var targets := []
			if sp["target"] == "enemies":
				targets = living_enemies()
			else:
				var foe: Dictionary = act["target"]
				if not bool(foe["alive"]):
					var alive := living_enemies()
					if alive.is_empty():
						return
					foe = alive[0]
				targets = [foe]
			for foe in targets:
				add_fx(sp["fx"], enemy_center(foe), 0.7)
				var roll := magic_damage(h, foe, sp)
				apply_damage(foe, int(roll["dmg"]), false, false, bool(roll["weak"]))
		elif spell_kind == "heal":
			var ally: Dictionary = act["target"]
			if not bool(ally["alive"]):
				ally = h
			add_fx("heal", hero_slot(int(ally["slot"])) + Vector2(8, -4), 0.7)
			heal_target(ally, int(round(float(sp["power"]) + float(h["mag"]) * 1.2)), true)
		elif spell_kind == "healAll":
			for ally in Gs.living_heroes():
				add_fx("heal", hero_slot(int(ally["slot"])) + Vector2(8, -4), 0.7)
				heal_target(ally, int(round(float(sp["power"]) + float(h["mag"]) * 0.9)), true)
		elif spell_kind == "guardAll":
			# Sera's Ward: the thing her family has been doing for four hundred
			# years, scaled down to one fight. Everyone guards without spending
			# their turn on it.
			for ally in Gs.living_heroes():
				ally["defending"] = true
				add_fx("holy", hero_slot(int(ally["slot"])) + Vector2(8, -4), 0.6)
			flash_banner("A ward closes over the party!")
		elif spell_kind == "revive":
			var ally: Dictionary = act["target"]
			if not bool(ally["alive"]):
				ally["alive"] = true
				ally["hp"] = maxi(1, int(round(float(ally["maxhp"]) * float(sp["power"]))))
				ally["atb"] = 0.0
				var at := hero_slot(int(ally["slot"]))
				add_fx("holy", at + Vector2(8, -4), 0.9)
				popup("REVIVED", at + Vector2(8, -18), Color("#ffe9a0"))
			else:
				flash_banner("Nothing happened.")
		return

	if kind == "item":
		var item_id: String = act["item_id"]
		var it: Dictionary = Dat.items[item_id]
		Gs.spend_item(item_id)
		flash_banner("%s uses %s." % [h["name"], it["name"]])
		Snd.sfx("item")
		acting["hold"] = 0.55
		var item_kind: String = it["kind"]
		var subject: Dictionary = act.get("target", h)
		if item_kind == "heal":
			add_fx("heal", hero_slot(int(subject["slot"])) + Vector2(8, -4))
			heal_target(subject, int(it["power"]), true)
		elif item_kind == "mp":
			subject["mp"] = mini(int(subject["maxmp"]), int(subject["mp"]) + int(it["power"]))
			popup("+%d MP" % int(it["power"]),
				hero_slot(int(subject["slot"])) + Vector2(8, -6), Color("#9fd0ff"))
		elif item_kind == "revive":
			if not bool(subject["alive"]):
				subject["alive"] = true
				subject["hp"] = int(round(float(subject["maxhp"]) * float(it["power"])))
				subject["atb"] = 0.0
				popup("REVIVED", hero_slot(int(subject["slot"])) + Vector2(8, -18),
					Color("#ffe9a0"))
			else:
				flash_banner("Nothing happened.")
		elif item_kind == "damage":
			var foe: Dictionary = subject
			if not bool(foe.get("alive", false)) or not foe.has("ai"):
				var alive := living_enemies()
				if alive.is_empty():
					return
				foe = alive[0]
			add_fx("fire", enemy_center(foe), 0.7)
			apply_damage(foe, int(it["power"]) + randi_range(0, 20), false)


func resolve_enemy_action(e: Dictionary, act: Dictionary) -> void:
	var targets := Gs.living_heroes()
	if targets.is_empty():
		return
	var victim: Dictionary = targets[randi() % targets.size()]
	acting["hold"] = 0.5
	var kind: String = act["kind"]

	if kind == "spell":
		var sp: Dictionary = Dat.spells[act["spell_id"]]
		flash_banner("%s casts %s!" % [e["label"], sp["name"]])
		Snd.sfx("magic")
		var hit := targets if sp["target"] == "enemies" else [victim]
		for x in hit:
			add_fx(sp["fx"], hero_slot(int(x["slot"])) + Vector2(8, -2), 0.7)
			var roll := magic_damage(e, x, sp)
			apply_damage(x, int(roll["dmg"]), true)
		acting["hold"] = 0.75
		return

	if kind == "drain":
		flash_banner("%s drains life!" % e["label"])
		Snd.sfx("magic")
		var roll := phys_damage(e, victim, 0.8)
		apply_damage(victim, int(roll["dmg"]), true)
		var back := int(round(float(roll["dmg"]) * 0.6))
		e["hp"] = mini(int(e["maxhp"]), int(e["hp"]) + back)
		popup("+%d" % back, enemy_center(e) + Vector2(0, -6), Color("#8fffa8"))
		return

	if kind == "rally":
		flash_banner("%s howls for reinforcements!" % e["label"])
		for x in living_enemies():
			x["atk"] = int(round(float(x["atk"]) * 1.08))
			x["offset"] = -4.0
		Snd.sfx("cursor")
		return

	if kind == "steal":
		var stolen := mini(Gs.gil, randi_range(10, 40))
		Gs.gil -= stolen
		flash_banner("%s snatches %d gil!" % [e["label"], stolen])
		Snd.sfx("cancel")
		return

	var mult := 1.0
	var verb := " attacks!"
	if kind == "pounce":
		mult = 1.35
		verb = " pounces!"
	elif kind == "smash":
		mult = 1.6
		verb = " swings its club!"
	flash_banner(e["label"] + verb)
	add_fx("slash", hero_slot(int(victim["slot"])) + Vector2(8, -2))
	Snd.sfx("crit" if mult > 1.0 else "hit")
	var roll := phys_damage(e, victim, mult)
	apply_damage(victim, int(roll["dmg"]), true, bool(roll["crit"]))
	victim["offset"] = -6.0


# --- outcome ----------------------------------------------------------------

func begin_victory() -> void:
	var exp_total := 0
	var gil_total := 0
	for e in enemies:
		exp_total += int(e["exp"])
		gil_total += int(e["gil"])
	Gs.gil += gil_total
	var lines := ["Victory!", "Gained %d EXP and %d gil." % [exp_total, gil_total]]
	# Everyone standing at the end gets the whole amount on the card, the way
	# the classics do it. Split three ways, the card said 17 and each hero's
	# "next in" moved by 6, which reads as a bug at the grind.
	var alive := Gs.living_heroes()
	for h in alive:
		for up in Gs.grant_exp(h, exp_total):
			lines.append("%s reached level %d!" % [h["name"], int(up["lv"])])
			for sp in up["learned"]:
				lines.append("%s learned %s!" % [h["name"], Dat.spells[sp]["name"]])
	if is_boss != "":
		var won: Dictionary = Dat.bosses[is_boss]
		Gs.flags[str(won["flag"])] = true
		for f in won.get("sets", []):
			Gs.flags[str(f)] = true
		for line in won["victory"]:
			lines.append(line)
	result_lines = lines
	result_page = 0
	result = "win"
	phase = "result"
	Snd.stop()
	Snd.sfx("levelup" if lines.size() > 2 else "victory")


func begin_defeat() -> void:
	result_lines = ["The party has fallen..."]
	result_page = 0
	result = "lose"
	phase = "result"
	Snd.stop()
	Snd.sfx("ko")


func update_result(_dt: float) -> void:
	if not Inp.tap("confirm") and not Inp.tap("cancel"):
		return
	result_page += 1
	Snd.sfx("cursor")
	if result_page < result_lines.size():
		return
	end_battle("win" if result == "win" else "lose")


func end_battle(how: String) -> void:
	main.finish_battle(how, is_boss)


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


func draw_backdrop(c: CanvasItem) -> void:
	# Rendered in Blender (tools/blender/backdrop.py) and quantised to the game
	# palette (tools/pixelate.py), so it arrives on the atlas as one sprite.
	var name := "bg_" + backdrop
	var size := Art.frame_size(name)
	var bx := roundf((Art.VW - size.x) / 2.0)
	var by := stage_floor() - size.y
	# A view taller than the render leaves sky above it. One pixel of the
	# backdrop's own sky, stretched over the gap; stretching the whole top row
	# put its horizontal variation on screen as a hard band across the top.
	if by > 0.0:
		Art.spr_stretched(c, name, Rect2(0, 0, Art.VW, by + 1.0), Rect2(0, 0, 1, 1))
	Art.spr(c, name, Vector2(bx, by))


func draw(c: CanvasItem) -> void:
	var sh: float = round(randf_range(-shake, shake)) if shake > 0.0 else 0.0
	c.draw_set_transform(Vector2(sh, 0))
	draw_backdrop(c)

	for i in enemies.size():
		var e: Dictionary = enemies[i]
		if not bool(e["alive"]) and float(e["dying"]) <= 0.0:
			continue
		var s := enemy_slot(e, i, enemies.size())
		var pos := Vector2(float(s["x"]) + float(e["offset"]), float(s["y"]))
		var alpha := 1.0
		if float(e["dying"]) > 0.0:
			alpha = float(e["dying"]) / 0.6
		if float(e["hurt"]) > 0.0 and int(float(e["hurt"]) * 30.0) % 2 == 0:
			alpha *= 0.65
		Art.draw_shadow(c, Vector2(pos.x + float(s["w"]) / 2.0,
			float(s["base_y"]) - 2.0), float(s["w"]) * 0.4)
		Art.spr(c, e["sprite"], pos, enemy_scale(e), Color(1, 1, 1, alpha))

	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var slot := hero_slot(i)
		var pos := Vector2(slot.x + float(h["offset"]), slot.y)
		var bs := Art.scale_for("%s_ready" % h["sprite"], 36.0)
		if not bool(h["alive"]):
			# Fallen party members lie on their back: the 16-bit shorthand for KO.
			var ko := Art.frame_size("%s_hurt" % h["sprite"])
			c.draw_set_transform(Vector2(pos.x + 12 + sh, pos.y + 26), -PI / 2.0)
			Art.spr(c, "%s_hurt" % h["sprite"],
				Vector2(-ko.x * bs / 2.0, -ko.y * bs / 2.0), bs, Color(1, 1, 1, 0.5))
			c.draw_set_transform(Vector2(sh, 0))
			continue
		var is_acting := not acting.is_empty() and is_same(acting["who"], h) \
			and int(acting["stage"]) >= 1
		var is_ready := actor != null and is_same(actor, h)
		Art.draw_shadow(c, Vector2(pos.x + 12, pos.y + 35), 9.0)
		var alpha := 1.0
		if float(h["hurt"]) > 0.0 and int(float(h["hurt"]) * 30.0) % 2 == 0:
			alpha = 0.55
		var bob := sin(t * 6.0) if is_ready else 0.0
		var pose := "_attack" if is_acting else "_ready"
		Art.spr_foot(c, h["sprite"] + pose, Vector2(pos.x + 12, pos.y + 36 + bob), bs,
			Color(1, 1, 1, alpha))

	draw_fx(c)

	for p in popups:
		var k := float(p["t"]) / float(p["life"])
		var y := float(p["y"]) - 16.0 * sin(min(1.0, k * 1.6) * PI * 0.5)
		var col: Color = p["color"]
		if k > 0.75:
			col.a = (1.0 - k) * 4.0
		Art.draw_text(c, p["text"], Vector2(float(p["x"]), y), col, "center")

	c.draw_set_transform(Vector2.ZERO)
	draw_ui(c)

	if flash > 0.0:
		c.draw_rect(Rect2(0, 0, Art.VW, Art.VH), Color(1, 1, 1, min(0.9, flash)))


func draw_fx(c: CanvasItem) -> void:
	for f in fx:
		var k := float(f["t"]) / float(f["life"])
		var a := 1.0 - k * k
		var x := float(f["x"])
		var y := float(f["y"])
		match f["kind"]:
			"slash":
				for i in 3:
					var off := i * 6 - 6
					c.draw_line(Vector2(x - 14 + off, y - 14 + k * 18),
						Vector2(x + 14 + off, y + 14 + k * 18), Color(1, 0.96, 0.85, a), 2.0)
			"fire":
				for i in 10:
					var ang := float(i) / 10.0 * TAU + k * 3.0
					var r := 6.0 + k * 24.0
					c.draw_rect(Rect2(x + cos(ang) * r - 2, y + sin(ang) * r * 0.7 - 2, 4, 4),
						Color("#ffb03c") if i % 2 == 1 else Color("#ff5a2c"), true)
				c.draw_rect(Rect2(x - 12, y - 12, 24, 24), Color(1.0, 0.86, 0.55, a * 0.5))
			"ice":
				for i in 7:
					var ang := float(i) / 7.0 * TAU
					var r := 22.0 * (1.0 - k)
					c.draw_rect(Rect2(x + cos(ang) * r - 1, y + sin(ang) * r - 5, 3, 10),
						(Color("#bff0ff") if i % 2 == 1 else Color("#5ac8f0")) * Color(1, 1, 1, a))
			"bolt":
				var bx := x
				var by := y - 60.0
				for i in 6:
					var nx := bx + randf_range(-7, 7)
					var ny := by + 12.0
					c.draw_line(Vector2(bx, by), Vector2(nx, ny), Color(1, 0.94, 0.35, a), 2.0)
					bx = nx
					by = ny
				c.draw_rect(Rect2(x - 16, y - 10, 32, 20), Color(1, 1, 0.7, a * 0.4))
			"quake":
				for i in 14:
					c.draw_rect(Rect2(x + randf_range(-26, 26),
						y + 16.0 - k * 30.0 + randf_range(-6, 6), 4, 4),
						Color("#a07a48") * Color(1, 1, 1, a))
			"heal":
				for i in 8:
					var ang := float(i) / 8.0 * TAU + k * 2.0
					var r := 14.0 * (1.0 - k * 0.4)
					c.draw_rect(Rect2(x + cos(ang) * r - 1, y + sin(ang) * r - 12.0 - k * 14.0, 3, 3),
						(Color("#c8ffd8") if i % 2 == 1 else Color("#7ce8a0")) * Color(1, 1, 1, a))
			"holy", "flare":
				var col := Color(1, 0.96, 0.78, a) if f["kind"] == "holy" else Color(1, 0.7, 1, a)
				var r := 4.0 + k * 30.0
				c.draw_rect(Rect2(x - r, y - 1, r * 2.0, 3), col)
				c.draw_rect(Rect2(x - 1, y - r, 3, r * 2.0), col)
				c.draw_circle(Vector2(x, y), r * 0.8, Color(col.r, col.g, col.b, a * 0.4))


func draw_ui(c: CanvasItem) -> void:
	if banner_t > 0.0:
		var w: int = mini(Art.VW - 16, Art.text_width(banner) + 20)
		Art.draw_window(c, Rect2(Art.VW / 2.0 - w / 2.0, 6, w, 18), "dark")
		Art.draw_text(c, banner, Vector2(Art.VW / 2.0, 11), Color("#f6f0d8"), "center")

	# The band the HUD sits in. Two windows used to cover it exactly; on a
	# wider view they do not, and the gap has to be painted.
	c.draw_rect(Rect2(0, stage_floor(), Art.VW, HUD_H), Color("#0b0a16"))

	var panel_y := stage_floor()
	var panel_h := float(HUD_H - 4)

	var pr := Art.VW - 200.0
	Art.draw_window(c, Rect2(pr, panel_y, 196, panel_h))
	for i in Gs.party.size():
		var h: Dictionary = Gs.party[i]
		var y := panel_y + 6 + i * 14
		var active := actor != null and is_same(actor, h)
		var name_color := Color("#9a8090")
		if bool(h["alive"]):
			name_color = Color("#ffe9a0") if active else Color("#f2f4ff")
		Art.draw_text(c, h["name"], Vector2(pr + 12, y), name_color)
		if bool(h["defending"]) and bool(h["alive"]):
			Art.spr(c, "i_shield", Vector2(pr + 4, y - 1))
		elif bool(h["alive"]) and float(h["hp"]) / float(h["maxhp"]) < 0.25:
			Art.spr(c, "i_heart", Vector2(pr + 4, y - 1))
		var hp_text := "K.O."
		if bool(h["alive"]):
			hp_text = "%d/%d" % [int(h["hp"]), int(h["maxhp"])]
		# Columns sized for four digits each: a late-game 394/394 and 118/118
		# ran into each other at the old spacing.
		Art.draw_text(c, hp_text, Vector2(pr + 94, y), hp_color(h), "right")
		var mp_text := "-"
		if int(h["maxmp"]) > 0:
			mp_text = "%d/%d" % [int(h["mp"]), int(h["maxmp"])]
		Art.draw_text(c, mp_text, Vector2(pr + 140, y), Color("#9fd0ff"), "right")
		var full := float(h["atb"]) >= 100.0
		Art.draw_bar(c, Vector2(pr + 144, y + 1), Vector2(46, 5),
			float(h["atb"]) / 100.0 if bool(h["alive"]) else 0.0,
			Color("#fff0a8") if full else Color("#8fd8ff"),
			Color("#e0a83c") if full else Color("#3a72c8"))
		if active:
			Art.draw_cursor(c, Vector2(pr + 4, y - 1), t)

	Art.draw_window(c, Rect2(4, panel_y, 112, panel_h))
	if phase == "command" and actor != null:
		draw_command_panel(c, panel_y)
	elif phase == "target":
		Art.draw_text(c, "Choose a", Vector2(14, panel_y + 8), Color("#f6e2a8"))
		Art.draw_text(c, "target", Vector2(14, panel_y + 20), Color("#f6e2a8"))
		Art.draw_button(c, Rect2(8, panel_y + 38, 104, 15), "Back")
	elif phase == "result":
		var line: String = result_lines[mini(result_page, result_lines.size() - 1)]
		var wrapped := Art.wrap_text(line, 17)
		for i in mini(4, wrapped.size()):
			Art.draw_text(c, wrapped[i], Vector2(10, panel_y + 7 + i * 12), Color("#f6f0d8"))
	else:
		Art.draw_text(c, "Gil", Vector2(14, panel_y + 9), Color("#9aa4c8"))
		Art.draw_text(c, str(Gs.gil), Vector2(108, panel_y + 9), Color("#f6e2a8"), "right")
		var alive := living_enemies()
		if not alive.is_empty():
			var foe: Dictionary = alive[0]
			Art.draw_text(c, (foe["label"] as String).substr(0, 15),
				Vector2(14, panel_y + 26), Color("#f2f4ff"))
			Art.draw_bar(c, Vector2(14, panel_y + 40), Vector2(94, 5),
				float(foe["hp"]) / float(foe["maxhp"]), Color("#ff9a9a"), Color("#c0384c"))

	if phase == "target":
		draw_target_cursor(c)


func draw_command_panel(c: CanvasItem, panel_y: int) -> void:
	var h: Dictionary = actor
	if sub == "":
		var cmds := commands_for(h)
		for i in cmds.size():
			var bx := 8 + (i % 2) * 53
			var by := panel_y + 5 + (i / 2) * 17
			Art.draw_button(c, Rect2(bx, by, 51, 15), cmds[i]["label"], i == cmd)
		return

	var entries := sub_entries(h)
	if entries.is_empty():
		Art.draw_text(c, "(nothing)", Vector2(20, panel_y + 8), Color("#9aa4c8"))
		return
	var start: int = clampi(sub_index - 3, 0, maxi(0, entries.size() - 4))
	var wide := entries.size() > 4
	var bw := 100 if wide else 104
	for i in range(start, mini(entries.size(), start + 4)):
		var by := panel_y + 4 + (i - start) * 13
		var label := ""
		var cost := ""
		var dim := false
		if sub == "magic":
			var sp: Dictionary = Dat.spells[entries[i]["id"]]
			label = sp["name"]
			cost = str(int(sp["mp"]))
			dim = int(h["mp"]) < int(sp["mp"])
		else:
			label = Dat.items[entries[i]["id"]]["name"]
			cost = str(int(entries[i]["n"]))
		Art.draw_button(c, Rect2(8, by, bw, 12), label, i == sub_index, false, dim, "left")
		Art.draw_text(c, cost, Vector2(3 + bw, by + 3),
			Color("#8a8fb0") if dim else Color("#9fd0ff"), "right")
	# A scrollbar, so a list longer than the window says so.
	if wide:
		var track := 50
		var thumb: int = maxi(6, roundi(track * 4.0 / entries.size()))
		var ty: int = panel_y + 4 + roundi((track - thumb) * float(start) / (entries.size() - 4))
		c.draw_rect(Rect2(110, panel_y + 4, 2, track), Color("#1a2148"))
		c.draw_rect(Rect2(110, ty, 2, thumb), Color("#7c88b8"))


func draw_target_cursor(c: CanvasItem) -> void:
	if target_side == "enemy":
		if target < 0 or target >= enemies.size():
			return
		var e: Dictionary = enemies[target]
		var s := enemy_slot(e, target, enemies.size())
		var cx := float(s["x"]) + float(s["w"]) / 2.0
		Art.draw_cursor(c, Vector2(cx - 3, float(s["y"]) - 14), t)
		var w := Art.text_width(e["label"]) + 12
		var bx: float = clamp(cx - w / 2.0, 2.0, Art.VW - w - 2.0)
		Art.draw_window(c, Rect2(bx, float(s["y"]) - 30, w, 15), "dark")
		Art.draw_text(c, e["label"], Vector2(bx + w / 2.0, float(s["y"]) - 26),
			Color("#ffd0d0"), "center")
	else:
		var slot := hero_slot(target)
		Art.draw_cursor(c, slot + Vector2(-12, 12), t)
