# Hero 13

A mobile-first Godot 4 starter project. The project currently contains a portrait touch-friendly start screen; game systems and content can be added on this base.

## Engine

- Godot 4.4.1 stable
- GDScript
- 2D renderer set to Compatibility for broad mobile-device support
- Portrait viewport: 720 × 1280, scaled with `canvas_items`

## Run

Open this repository folder in Godot 4.4.1 and press Play. The GitHub Actions workflow also imports the project and launches its main scene in headless mode on every push to `main`.

## Android export

Install the matching Godot export templates, OpenJDK 17, Android SDK command-line tools, Android platform/build-tools, and the Android export template. In Godot, configure the Java SDK and Android SDK paths, add an Android export preset, then export a debug APK. The official setup steps are in the [Godot Android export guide](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_android.html).

Godot Engine is MIT licensed. This project does not yet include game assets or third-party add-ons.
