extends Node
## Game state: the party, the purse, the bag, world flags, and saving.

const SAVE_PATH := "user://rivenbrook_save.json"

var party := []
var gil := 200
var bag := {}
var map_id := "town"
var px := 0
var py := 0
var dir := "down"
var steps := 0
var steps_to_encounter := 999
var playtime := 0.0
var flags := {"chests": {}, "boss_down": false, "visited_wild": false}


func exp_to_next(level: int) -> int:
	return int(22.0 * pow(float(level), 1.75))


func stat_at(cls: Dictionary, key: String, level: int) -> int:
	return int(float(cls["base"][key]) + float(cls["grow"][key]) * (level - 1))


func make_hero(id: String, level := 1) -> Dictionary:
	var cls: Dictionary = Dat.classes[id]
	var h := {
		"id": id, "name": cls["name"], "title": cls["title"], "sprite": cls["sprite"],
		"lv": level, "exp": 0, "alive": true, "defending": false,
		"atb": 0.0, "hurt": 0.0, "offset": 0.0,
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
	var known := []
	for entry in cls["spells"]:
		if int(entry["lv"]) <= int(h["lv"]):
			known.append(entry["id"])
	h["spells"] = known


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
	gil = 200
	bag = {"potion": 5, "ether": 1, "phoenix": 1}
	flags = {"chests": {}, "boss_down": false, "visited_wild": false}
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


func save_game() -> bool:
	var slim := []
	for h in party:
		slim.append({"id": h["id"], "lv": h["lv"], "exp": h["exp"],
			"hp": h["hp"], "mp": h["mp"], "alive": h["alive"]})
	var payload := {
		"party": slim, "gil": gil, "bag": bag, "map_id": map_id,
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
	party = []
	for p in d.get("party", []):
		var h := make_hero(p["id"], int(p["lv"]))
		h["exp"] = int(p["exp"])
		h["hp"] = int(p["hp"])
		h["mp"] = int(p["mp"])
		h["alive"] = bool(p.get("alive", true))
		party.append(h)
	gil = int(d.get("gil", 200))
	bag = d.get("bag", {})
	flags = d.get("flags", {"chests": {}, "boss_down": false, "visited_wild": false})
	playtime = float(d.get("playtime", 0.0))
	map_id = d.get("map_id", "town")
	px = int(d.get("px", 0))
	py = int(d.get("py", 0))
	dir = d.get("dir", "down")
	return true


func format_time(seconds: float) -> String:
	var total := int(seconds)
	return "%02d:%02d:%02d" % [total / 3600, (total / 60) % 60, total % 60]
