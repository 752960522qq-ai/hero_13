extends Node2D

var status_label: Label

func _ready() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)

	var background := ColorRect.new()
	background.color = Color("#101827")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ui.add_child(background)

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ui.add_child(center)

	var column := VBoxContainer.new()
	column.custom_minimum_size = Vector2(560, 300)
	column.add_theme_constant_override("separation", 28)
	center.add_child(column)

	var title := Label.new()
	title.text = "HERO 13"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 64)
	column.add_child(title)

	status_label = Label.new()
	status_label.text = "Godot 手机游戏项目已启动"
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.add_theme_font_size_override("font_size", 28)
	column.add_child(status_label)

	var start_button := Button.new()
	start_button.text = "开始"
	start_button.custom_minimum_size = Vector2(0, 112)
	start_button.add_theme_font_size_override("font_size", 36)
	start_button.pressed.connect(_on_start_pressed)
	column.add_child(start_button)

	print("GODOT_MOBILE_STARTER_OK engine=", Engine.get_version_info().string)

func _on_start_pressed() -> void:
	status_label.text = "触控输入正常，可以开始搭建游戏内容。"
	print("GODOT_TOUCH_BUTTON_OK")
