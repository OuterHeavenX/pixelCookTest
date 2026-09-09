extends Node
## Game state: the party, the purse, the bag, world flags, and saving.

const SAVE_PATH := "user://rivenbrook_save.json"

const PARTY_MAX := 4

var party := []
var bench := []       ## everyone who has joined but is not in the line
var gil := 200
var bag := {}
var gear := {}          ## unequipped pieces in the pack, id -> count
var map_id := "town"
var px := 0
var py := 0
var dir := "down"
var steps := 0
var steps_to_encounter := 999
var playtime := 0.0
var flags := {"chests": {}, "bossDown": false, "visitedWild": false}


func exp_to_next(level: int) -> int:
	return int(22.0 * pow(float(level), 1.75))


func stat_at(cls: Dictionary, key: String, level: int) -> int:
	return int(float(cls["base"][key]) + float(cls["grow"][key]) * (level - 1))


func make_hero(id: String, level := 1) -> Dictionary:
	var cls: Dictionary = Dat.classes[id]
	var worn := {"weapon": null, "armour": null, "trinket": null}
	for slot in Dat.starting_gear.get(id, {}):
		worn[slot] = Dat.starting_gear[id][slot]
	var h := {
		"id": id, "name": cls["name"], "title": cls["title"], "sprite": cls["sprite"],
		"lv": level, "exp": 0, "alive": true, "defending": false,
		"atb": 0.0, "hurt": 0.0, "offset": 0.0, "gear": worn,
	}
	refresh_stats(h)
	h["hp"] = h["maxhp"]
	h["mp"] = h["maxmp"]
	return h


func refresh_stats(h: Dictionary) -> void:
	var cls: Dictionary = Dat.classes[h["id"]]
	h["maxhp"] = stat_at(cls, "hp", h["lv"])
	h["maxmp"] = stat_at(cls, "mp", h["lv"])
	h["atk"] = stat_at(cls, "atk", h["lv"])
	h["def"] = stat_at(cls, "def", h["lv"])
	h["mag"] = stat_at(cls, "mag", h["lv"])
	h["spd"] = stat_at(cls, "spd", h["lv"])
	# Equipment is folded straight into the derived stats, so nothing
	# downstream has to know it exists - a sword just makes atk bigger.
	for g in gear_on(h):
		for k in g["stats"]:
			var v := int(g["stats"][k])
			if k == "hp":
				h["maxhp"] = int(h["maxhp"]) + v
			elif k == "mp":
				h["maxmp"] = int(h["maxmp"]) + v
			else:
				h[k] = maxi(1, int(h[k]) + v)
	var known := []
	for entry in cls["spells"]:
		if int(entry["lv"]) <= int(h["lv"]):
			known.append(entry["id"])
	h["spells"] = known


## ----------------------------------------------------------------- roster --
## `party` is who fights: at most PARTY_MAX of them, and every system already
## reads it, so it stays exactly what it was. `bench` is everyone else who has
## joined. Recruiting and losing people is then moving them between two arrays.

func roster() -> Array:
	return party + bench


func find_hero(id: String) -> Variant:
	for h in roster():
		if h["id"] == id:
			return h
	return null


## Someone joins. They arrive at a level that keeps up with the party rather
## than at 1, because a level-1 friend in a level-12 party is a liability
## dressed as a gift.
func join_party(id: String, level := 0) -> Variant:
	var existing = find_hero(id)
	if existing != null:
		return existing
	var lv := level
	if lv <= 0:
		var total := 0
		for h in party:
			total += int(h["lv"])
		lv = maxi(1, roundi(float(total) / maxi(1, party.size())))
	var h := make_hero(id, lv)
	if party.size() < PARTY_MAX:
		party.append(h)
	else:
		bench.append(h)
	return h


## Someone goes. Their gear goes back in the pack - they are not taking your
## halberd with them.
func leave_party(id: String) -> Variant:
	var h = find_hero(id)
	if h == null:
		return null
	for slot in h["gear"]:
		if h["gear"][slot] != null:
			take_gear(h["gear"][slot])
	party.erase(h)
	bench.erase(h)
	# The line never empties: somebody has to be standing there.
	if party.is_empty() and not bench.is_empty():
		party.append(bench.pop_front())
	return h


## Swap someone between the line and the bench. Aldric cannot be benched - he
## is the one the story is happening to.
func bench_swap(h: Dictionary) -> bool:
	if party.has(h):
		if party.size() <= 1 or h["id"] == "aldric":
			return false
		party.erase(h)
		bench.append(h)
		return true
	if party.size() >= PARTY_MAX:
		return false
	bench.erase(h)
	party.append(h)
	return true


## ------------------------------------------------------------------- gear --

## The pieces a character is actually wearing.
func gear_on(h: Dictionary) -> Array:
	var out := []
	for slot in h.get("gear", {}):
		var id = h["gear"][slot]
		if id != null and Dat.gear.has(id):
			out.append(Dat.gear[id])
	return out


func equipped(h: Dictionary, slot: String) -> Variant:
	var id = h.get("gear", {}).get(slot, null)
	return Dat.gear[id] if id != null and Dat.gear.has(id) else null


func can_wear(h: Dictionary, g: Dictionary) -> bool:
	var users = g.get("users", null)
	return users == null or users.has(h["id"])


## Unequipped pieces in the pack, for one slot, that this character can wear.
func gear_for(h: Dictionary, slot: String) -> Array:
	var out := []
	for id in gear:
		if int(gear[id]) > 0 and Dat.gear.has(id) \
				and Dat.gear[id]["slot"] == slot and can_wear(h, Dat.gear[id]):
			out.append(id)
	out.sort_custom(func(a, b): return int(Dat.gear[a]["price"]) < int(Dat.gear[b]["price"]))
	return out


func take_gear(id: String, n := 1) -> void:
	gear[id] = int(gear.get(id, 0)) + n


## Swap a piece in. The old one goes back in the pack, and current HP/MP move
## with the maximum so a +30 HP charm is felt immediately rather than banked.
func equip_gear(h: Dictionary, slot: String, id) -> bool:
	if id != null:
		if not Dat.gear.has(id):
			return false
		var g: Dictionary = Dat.gear[id]
		if g["slot"] != slot or not can_wear(h, g) or int(gear.get(id, 0)) <= 0:
			return false
	var before_hp := int(h["maxhp"])
	var before_mp := int(h["maxmp"])
	var old = h["gear"][slot]
	if id != null:
		gear[id] = int(gear[id]) - 1
		if int(gear[id]) <= 0:
			gear.erase(id)
	if old != null:
		take_gear(old)
	h["gear"][slot] = id
	refresh_stats(h)
	h["hp"] = clampi(int(h["hp"]) + int(h["maxhp"]) - before_hp, 1, int(h["maxhp"]))
	h["mp"] = clampi(int(h["mp"]) + int(h["maxmp"]) - before_mp, 0, int(h["maxmp"]))
	return true


## "+6 ATK  -1 SPD", the line that actually decides a purchase.
func gear_delta(h: Dictionary, g: Dictionary) -> String:
	var cur = equipped(h, g["slot"])
	var parts := []
	for k in ["atk", "def", "mag", "spd", "hp", "mp"]:
		var now := 0
		if cur != null:
			now = int(cur["stats"].get(k, 0))
		var d := int(g["stats"].get(k, 0)) - now
		if d != 0:
			parts.append("%s%d %s" % ["+" if d > 0 else "", d, k.to_upper()])
	return "  ".join(parts) if not parts.is_empty() else "no change"


## Returns one entry per level gained, each listing the spells it unlocked.
func grant_exp(h: Dictionary, amount: int) -> Array:
	var gained := []
	if not h["alive"]:
		return gained
	h["exp"] = int(h["exp"]) + amount
	while int(h["exp"]) >= exp_to_next(int(h["lv"])):
		h["exp"] = int(h["exp"]) - exp_to_next(int(h["lv"]))
		h["lv"] = int(h["lv"]) + 1
		var before_hp: int = h["maxhp"]
		var before_mp: int = h["maxmp"]
		var before_spells: Array = (h["spells"] as Array).duplicate()
		refresh_stats(h)
		h["hp"] = int(h["hp"]) + int(h["maxhp"]) - before_hp
		h["mp"] = int(h["mp"]) + int(h["maxmp"]) - before_mp
		var learned := []
		for sp in h["spells"]:
			if not before_spells.has(sp):
				learned.append(sp)
		gained.append({"lv": h["lv"], "learned": learned})
	return gained


func living_heroes() -> Array:
	return party.filter(func(h): return h["alive"])


func new_game() -> void:
	party = [make_hero("aldric"), make_hero("lyra"), make_hero("mira")]
	bench = []
	gil = 200
	bag = {"potion": 5, "ether": 1, "phoenix": 1}
	gear = {"leather_vest": 2}   # two spare vests: the mages start bare
	flags = {"chests": {}, "bossDown": false, "visitedWild": false}
	steps = 0
	playtime = 0.0


func bag_list() -> Array:
	var out := []
	for key in bag:
		if int(bag[key]) > 0:
			out.append({"id": key, "n": int(bag[key])})
	out.sort_custom(func(a, b): return a["id"] < b["id"])
	return out


func take_item(id: String, n := 1) -> void:
	bag[id] = int(bag.get(id, 0)) + n


func spend_item(id: String) -> void:
	bag[id] = int(bag.get(id, 0)) - 1
	if int(bag[id]) <= 0:
		bag.erase(id)


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func _slim(who: Array) -> Array:
	var out := []
	for h in who:
		out.append({"id": h["id"], "lv": h["lv"], "exp": h["exp"],
			"hp": h["hp"], "mp": h["mp"], "alive": h["alive"], "gear": h["gear"]})
	return out


func _fat(rows) -> Array:
	var out := []
	for p in rows:
		var h := make_hero(p["id"], int(p["lv"]))
		# Saves from before equipment existed just keep their starting kit.
		if p.has("gear"):
			for slot in p["gear"]:
				h["gear"][slot] = p["gear"][slot]
			refresh_stats(h)
		h["exp"] = int(p["exp"])
		h["hp"] = int(p["hp"])
		h["mp"] = int(p["mp"])
		h["alive"] = bool(p.get("alive", true))
		out.append(h)
	return out


func save_game() -> bool:
	var payload := {
		"party": _slim(party), "bench": _slim(bench),
		"gil": gil, "bag": bag, "gear": gear, "map_id": map_id,
		"px": px, "py": py, "dir": dir, "flags": flags, "playtime": playtime,
	}
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(payload))
	f.close()
	return true


func load_game() -> bool:
	if not has_save():
		return false
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(parsed) != TYPE_DICTIONARY:
		return false
	var d: Dictionary = parsed
	party = _fat(d.get("party", []))
	bench = _fat(d.get("bench", []))
	gil = int(d.get("gil", 200))
	bag = d.get("bag", {})
	gear = d.get("gear", {})
	flags = d.get("flags", {"chests": {}, "bossDown": false, "visitedWild": false})
	playtime = float(d.get("playtime", 0.0))
	map_id = d.get("map_id", "town")
	px = int(d.get("px", 0))
	py = int(d.get("py", 0))
	dir = d.get("dir", "down")
	return true


func format_time(seconds: float) -> String:
	var total := int(seconds)
	return "%02d:%02d:%02d" % [total / 3600, (total / 60) % 60, total % 60]
