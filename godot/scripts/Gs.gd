extends Node
## Game state: the party, the purse, the bag, world flags, and saving.

const SAVE_PATH := "user://rivenbrook_save.json"      ## the journal the player writes
const AUTOSAVE_PATH := "user://rivenbrook_auto.json"  ## the game's own, at milestones
const SAVE_VERSION := 2
const DIRS := ["up", "down", "left", "right"]

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


func _payload() -> Dictionary:
	return {
		"version": SAVE_VERSION, "saved_at": int(Time.get_unix_time_from_system()),
		"party": _slim(party), "bench": _slim(bench),
		"gil": gil, "bag": bag, "gear": gear, "map_id": map_id,
		"px": px, "py": py, "dir": dir, "flags": flags, "playtime": playtime,
	}


func _write(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(_payload()))
	f.close()
	return true


func save_game() -> bool:
	return _write(SAVE_PATH)


## Written by the game at the moments a player would hate to lose: a map
## change, a purchase, someone joining, a chest, a boss. Its own file, so the
## journal the player wrote on purpose is never overwritten by accident;
## Continue takes whichever of the two is newer.
func autosave() -> bool:
	return _write(AUTOSAVE_PATH)


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


func _is_int(v) -> bool:
	return typeof(v) == TYPE_INT or (typeof(v) == TYPE_FLOAT and v == floor(v))


func _is_plain(v) -> bool:
	return typeof(v) == TYPE_DICTIONARY


func _check_hero(p, where: String) -> String:
	if not _is_plain(p):
		return where + " is not a hero"
	if not Dat.classes.has(p.get("id", "")):
		return where + " is nobody we know"
	if not _is_int(p.get("lv")) or int(p["lv"]) < 1 or int(p["lv"]) > 99:
		return where + " has an impossible level"
	if not _is_int(p.get("exp")) or int(p["exp"]) < 0:
		return where + " has impossible experience"
	if not _is_int(p.get("hp")) or not _is_int(p.get("mp")) or int(p["hp"]) < 0 or int(p["mp"]) < 0:
		return where + " has impossible health"
	if p.has("gear"):
		if not _is_plain(p["gear"]):
			return where + " wears nonsense"
		var slot_ids := []
		for g in Dat.gear_slots:
			slot_ids.append(g["id"])
		for slot in p["gear"]:
			if not slot_ids.has(slot):
				return where + " wears something on a limb nobody has"
			var id = p["gear"][slot]
			if id != null and not Dat.gear.has(id):
				return where + " wears something that does not exist"
	return ""


## Nothing is read out of a save until the whole thing has been checked. A
## field that is missing, the wrong type, or names something the game does
## not have is a reason, and a save with a reason is not loaded: the title
## says why instead of the game misbehaving later. Returns the reason, or "".
func check_save(d) -> String:
	if not _is_plain(d):
		return "it is not a journal"
	var version = d.get("version", 1)
	if not _is_int(version) or int(version) < 1:
		return "its version makes no sense"
	if int(version) > SAVE_VERSION:
		return "it was written by a newer game"
	var party_rows = d.get("party")
	if typeof(party_rows) != TYPE_ARRAY or party_rows.size() < 1 or party_rows.size() > PARTY_MAX:
		return "the party is missing"
	for i in party_rows.size():
		var r := _check_hero(party_rows[i], "party member %d" % (i + 1))
		if r != "":
			return r
	if d.has("bench"):
		if typeof(d["bench"]) != TYPE_ARRAY:
			return "the bench is not a bench"
		for i in (d["bench"] as Array).size():
			var r := _check_hero(d["bench"][i], "bench member %d" % (i + 1))
			if r != "":
				return r
	if not _is_int(d.get("gil")) or int(d["gil"]) < 0:
		return "the purse is not a number"
	if d.has("bag") and not _is_plain(d["bag"]):
		return "the bag is not a bag"
	if d.has("gear") and not _is_plain(d["gear"]):
		return "the spare gear is not a list"
	if not Dat.maps.has(d.get("map_id", "")):
		return "it is set on a map we do not have"
	var m: Dictionary = Dat.maps[d["map_id"]]
	if not _is_int(d.get("px")) or not _is_int(d.get("py")) \
			or int(d["px"]) < 0 or int(d["py"]) < 0 \
			or int(d["px"]) >= int(m["w"]) or int(d["py"]) >= int(m["h"]):
		return "the party is standing off the map"
	if d.has("dir") and not DIRS.has(d["dir"]):
		return "the party is facing nowhere"
	if d.has("flags") and not _is_plain(d["flags"]):
		return "its flags are not flags"
	if d.has("playtime") and typeof(d["playtime"]) != TYPE_FLOAT and typeof(d["playtime"]) != TYPE_INT:
		return "its clock is broken"
	return ""


## A sound save from any version, brought up to this one: everything optional
## gets its default, and items or gear the game no longer has fall out of the
## bag rather than sitting there as names nothing can draw.
func migrate_save(d: Dictionary) -> Dictionary:
	var out := {"bench": [], "bag": {}, "gear": {}, "flags": {}, "playtime": 0.0,
		"dir": "down", "saved_at": 0}
	out.merge(d, true)
	var bag_out := {}
	for id in out["bag"]:
		if Dat.items.has(id) and _is_int(out["bag"][id]) and int(out["bag"][id]) > 0:
			bag_out[id] = int(out["bag"][id])
	out["bag"] = bag_out
	var gear_out := {}
	for id in out["gear"]:
		if Dat.gear.has(id) and _is_int(out["gear"][id]) and int(out["gear"][id]) > 0:
			gear_out[id] = int(out["gear"][id])
	out["gear"] = gear_out
	var flags_out := {"chests": {}}
	flags_out.merge(out["flags"], true)
	if typeof(flags_out["chests"]) != TYPE_DICTIONARY:
		flags_out["chests"] = {}
	out["flags"] = flags_out
	out["version"] = SAVE_VERSION
	return out


## One slot, read and checked: {} when empty, {"data": ...} when sound,
## {"problem": ...} when it is there but cannot be trusted.
func read_slot(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	# A JSON instance rather than parse_string, so a file that is not JSON is
	# a reason on the title and not an error in the engine log.
	var json := JSON.new()
	if json.parse(FileAccess.get_file_as_string(path)) != OK:
		return {"problem": "it is not even text we can read"}
	var parsed = json.data
	var problem := check_save(parsed)
	if problem != "":
		return {"problem": problem}
	return {"data": migrate_save(parsed)}


func _slots() -> Array:
	var out := []
	for path in [SAVE_PATH, AUTOSAVE_PATH]:
		var slot := read_slot(path)
		if not slot.is_empty():
			out.append(slot)
	return out


func newest_save() -> Dictionary:
	var best := {}
	for slot in _slots():
		if slot.has("data") and (best.is_empty() or int(slot["data"]["saved_at"]) > int(best["saved_at"])):
			best = slot["data"]
	return best


func has_save() -> bool:
	return not newest_save().is_empty()


## Why Continue is missing when there is something on disk: the first slot's
## reason, or "" when nothing is wrong (or nothing is there).
func save_problem() -> String:
	var slots := _slots()
	if slots.is_empty():
		return ""
	for slot in slots:
		if slot.has("data"):
			return ""
	return slots[0]["problem"]


func load_game() -> bool:
	var d := newest_save()
	if d.is_empty():
		return false
	party = _fat(d["party"])
	bench = _fat(d["bench"])
	gil = int(d["gil"])
	bag = d["bag"]
	gear = d["gear"]
	flags = d["flags"]
	playtime = float(d["playtime"])
	map_id = d["map_id"]
	px = int(d["px"])
	py = int(d["py"])
	dir = d["dir"]
	return true


func format_time(seconds: float) -> String:
	var total := int(seconds)
	return "%02d:%02d:%02d" % [total / 3600, (total / 60) % 60, total % 60]
