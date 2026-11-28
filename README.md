# Radball Regie

Kivy-Anwendung zur Spielleitung im Radball. Spieltage lassen sich lokal verwalten und offline spielen; wenn eine Verbindung besteht, kann die App Spielpläne laden und freigegebene Ergebnisse an die jeweilige API übertragen. Anzeigen werden direkt im lokalen Netzwerk per UDP angesteuert.

## Download

Die fertigen Installationsdateien liegen im [GitHub-Release](https://github.com/radeddi/radball/releases/latest):

- **Android (ARM64):** `Radball-Regie-*-Android-arm64.apk`
- **Linux x86_64:** `Radball-Regie-*-Linux-x86_64.tar.gz`
- **Windows x64:** `Radball-Regie-*-Windows-x64.exe`

APK-Datei auf dem Android-Gerät öffnen und die Installation aus dieser Quelle erlauben. Bei einem Wechsel von einer anders signierten Testversion muss diese vorher entfernt werden; lokale, noch nicht synchronisierte Daten vorher sichern.

## Aus dem Quellcode bauen

Für Android werden Buildozer, Android SDK/NDK und die in `buildozer.spec` festgelegten Abhängigkeiten benötigt. Das offizielle APK ist für ARM64-Geräte gebaut; Emulator-Builds mit `x86_64` sind nur für Tests und nicht für Smartphones gedacht.

Die App verwendet als Portal-Standard `https://radball.groff.ch`. Spielbetrieb und Anzeige im lokalen WLAN funktionieren unabhängig von einer Internetverbindung.

## Entwicklung und Tests

Die Hilfsmodule liegen neben `main.py`, der Android-Hintergrunddienst unter `service/` und die Regressionstests unter `tests/`. Tests aus dem App-Verzeichnis starten mit:

```sh
python3 -m unittest discover -s tests -v
```
