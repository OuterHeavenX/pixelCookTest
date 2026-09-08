extends Node
## Loads the cooked rules and maps.
##
## gamedata.json comes from tools/datacook.py and maps.json from
## tools/mapcook.py, so the Godot build and the browser build agree on every
## number without either one restating it.

var spells := {}
var items := {}
var classes := {}
var enemies := {}
var encounters := []
var npcs := {}
var shop_stock := []
var legend := {}
var underlay := {}
var sign_text := {}
var chest_loot := {}
var inn_cost := 50
var maps := {}


func _ready() -> void:
	var data: Dictionary = _read_json("res://assets/gamedata.json")
	spells = data.get("spells", {})
	items = data.get("items", {})
	classes = data.get("classes", {})
	enemies = data.get("enemies", {})
	encounters = data.get("encounters", [])
	npcs = data.get("npcs", {})
	shop_stock = data.get("shop_stock", [])
	legend = data.get("legend", {})
	underlay = data.get("underlay", {})
	sign_text = data.get("sign_text", {})
	chest_loot = data.get("chest_loot", {})
	inn_cost = int(data.get("inn_cost", 50))
	maps = _read_json("res://assets/maps.json")


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		push_error("missing cooked asset: %s (run python3 tools/godotcook.py)" % path)
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("could not parse %s" % path)
		return {}
	return parsed


## Weighted pick from the Thornwilds encounter table.
func roll_encounter() -> Array:
	var total := 0.0
	for e in encounters:
		total += float(e["w"])
	var r := randf() * total
	for e in encounters:
		r -= float(e["w"])
		if r <= 0.0:
			return (e["group"] as Array).duplicate()
	return ["slime"]
