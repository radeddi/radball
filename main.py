debug=False

__version__ = "1.0.0"

from kivy.config import Config

import kivy


Config.set('kivy', 'exit_on_escape', '0')
Config.set('graphics', 'width', '1200')
Config.set('graphics', 'height', '1000')
Config.set('graphics', 'minimum_width', '1000')
Config.set('graphics', 'minimum_height', '800')

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
# to use buttons:
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.progressbar import ProgressBar
from kivy.network.urlrequest import UrlRequest
from kivy.core.window import Window

from kivy.uix.dropdown import DropDown
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.uix.relativelayout import RelativeLayout

import os
import re
#import certifi as cfi
import requests
import random
import certifi
from matchday_import import FEEDS, import_jobs, save_matchday
from portal_results import ResultQueue
from digital_results import VerifiedMatchday, matchday_url, scored
from matchday_selection import league_order, matchday_order, selection_labels
from portal_import import CATALOG, PORTAL_NAME, PORTAL_REGIONS, PORTAL_URL, SWISS_PORTAL_NAME, cache_portal_plan, portal_jobs

import datetime
from datetime import timedelta
from uuid import uuid4
from display_routes import Displays, MODES, result_page, send_displays
from game_navigation import expired_during_play, may_finalize_on_navigation, quick_game_plan

from collections import deque

if platform == 'android':
    from android.permissions import Permission, check_permission, request_permissions
    perms = [Permission.WRITE_EXTERNAL_STORAGE]
    if not all([check_permission(perm) for perm in perms]):
        request_permissions(perms)


if platform == 'android':
    from android import mActivity
    from jnius import autoclass
    from plyer import orientation

try:
	import simplejson as json
except ImportError:
	import json
import time
from concurrent.futures import ThreadPoolExecutor
import socket 
from kivy.utils import platform

from kivy.core.window import Window


KNOWN_TEAMS = [
    "Prechtal 2",
    "Prechtal 3",
    "Hardt 1",
    "Ailingen 2",
    "Weil im Schönbuch 1",
    "Schwaikheim 1",
    "Schwaikheim 2",
    "Waldrems 4",
    "Gastteam A",
    "Gastteam B"
]




sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock2.setblocking(False)
try:
    sock2.bind(("", 5006))
except OSError:
    sock2.close()
    sock2 = None


kivy.require("1.10.1")




class MySpinnerOption(SpinnerOption):
    font_size = 40  # Angepasste Schriftgröße


def set_orientation(orientation):
    if platform == "android":
        # Überprüfen, ob auf Android, und dann die Orientierung setzen
        import android
        android.orientation = orientation

import re

def build_known_teams():
    """
    Durchsucht alle .radball-Dateien unter 'spieltage/' und sammelt dort gefundene Teams in einem Set.
    Anschließend entfernen wir alles ab dem ersten Vorkommen von:
       - U + Ziffern (z.B. 'U15')
       - oder jeder anderen Ziffer (z.B. '3', '12', '2ZSR')
    So wird aus 'Neetzow U15' => 'Neetzow', 'Burgkunstadt U19ZSR' => 'Burgkunstadt', usw.

    Alle zusammengesammelten Teamnamen speichern wir alphabetisch sortiert in der globalen Liste KNOWN_TEAMS.
    """
    global KNOWN_TEAMS
    found_teams = set()

    root_path = os.path.join(app_folder, "spieltage")
    if not os.path.exists(root_path):
        return  # Keine Spieltage vorhanden

    for land_dir in sorted(os.listdir(root_path)):
        full_land_path = os.path.join(root_path, land_dir)
        if not os.path.isdir(full_land_path):
            continue

        # Jede .radball-Datei im Unterordner
        for datei in sorted(os.listdir(full_land_path)):
            if not datei.endswith(".radball") or (land == SWISS_PORTAL_NAME and not datei.startswith("portal-")):
                continue  # Nur radball-Dateien

            full_file_path = os.path.join(full_land_path, datei)
            try:
                with open(full_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Fehler beim Lesen von {full_file_path}: {e}")
                continue

            # Teams auslesen und verarbeiten
            if "teams" in data:
                for t in data["teams"]:
                    raw_name = t.get("name", "").strip()
                    if not raw_name:
                        continue

                    # Regex: Finde das erste Vorkommen von "Uxx" (groß/klein) ODER jeder anderen Ziffer
                    # (?i) = case-insensitive
                    # (u\d+|\d+) = "U" gefolgt von >=1 Ziffern ODER >=1 Ziffer
                    pattern = r"(?i)(u\d+|\d+)"
                    m = re.search(pattern, raw_name)
                    if m:
                        # Alles vor dem Fund behalten, Rest weg
                        name_cleaned = raw_name[:m.start()].strip()
                    else:
                        # Keine Ziffer / kein "Uxx" gefunden, also komplett lassen
                        name_cleaned = raw_name

                    if name_cleaned:
                        found_teams.add(name_cleaned)

    # Alphabetisch sortieren
    KNOWN_TEAMS = sorted(found_teams)
    print("Aufgebaute KNOWN_TEAMS:", KNOWN_TEAMS)



class SwipeSafeButton(Button):
    """
    Button, der nicht klickt, wenn sich der Finger zu weit bewegt.
    So lassen sich versehentliche Klicks bei Wischgesten vermeiden.
    """
    move_threshold = NumericProperty(20)  # Bewegungstoleranz in Pixeln

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._touch_start = (0, 0)  # Startkoordinaten des Touches
        self._touch_is_valid = False  # Ob der Touch noch als Klick gelten darf

    def on_touch_down(self, touch):
        # Prüfen, ob der Touch in unseren Button fällt
        if self.collide_point(*touch.pos):
            # Merken, dass wir "aktiver" Button sind
            self._touch_start = touch.pos
            self._touch_is_valid = True
            # Wir "grabben" den Touch => alle move/up-Events kommen an uns
            touch.grab(self)
            # Weiter an Kivy.Button, damit der Button z. B. optisch "gedrückt" wird
            super_return = super().on_touch_down(touch)
            return True if super_return else True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        # Nur wenn dieser Button den Touch gegriffen hat, interessieren wir uns
        if touch.grab_current is self and self._touch_is_valid:
            dx = abs(touch.x - self._touch_start[0])
            dy = abs(touch.y - self._touch_start[1])
            # Überschreitet die Bewegung unsere Schwelle => Touch ist kein Klick mehr
            if dx > self.move_threshold or dy > self.move_threshold:
                self._touch_is_valid = False
                # Button aus dem "gedrückt"-Zustand optisch lösen
                self.state = "normal"
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        # Nur wenn wir den Touch wirklich gegrabbt haben
        if touch.grab_current is self:
            touch.ungrab(self)  # wir geben den Touch wieder frei
            if self._touch_is_valid:
                # Wenn der Finger sich nicht zu weit bewegt hat -> normaler Klick
                # => Wir rufen Button's on_touch_up auf, was on_release etc. triggert.
                return super().on_touch_up(touch)
            else:
                # Geste war zu groß => Kein Klick. "Verbrauch" das Event, 
                # damit es nicht nochmal durch andere Buttons läuft
                return True
        return super().on_touch_up(touch)

def get_new_matchday_number(league_short):
    eigene_folder = os.path.join(app_folder, "spieltage", "eigene")
    if not os.path.exists(eigene_folder):
        return 1
    max_number = 0
    for fname in os.listdir(eigene_folder):
        if fname.startswith(f"{league_short}_") and fname.endswith(".radball"):
            try:
                # Entferne das Präfix (league_short + "_") und das Suffix ".radball"
                number_str = fname[len(league_short) + 1: -8]
                number = int(number_str)
                if number > max_number:
                    max_number = number
            except Exception:
                continue
    return max_number + 1

# Simple information/error page
class SelectorPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Just one column
        self.cols = 1        
        
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)



        self.backFurtherButton = GridLayout(cols=2,size_hint = (1, 0.15))
        self.backButton = Button(text="zurück",font_size=40)#size_hint_y=None)
        self.backButton.bind(on_release=self.goBack)
        self.furtherButton = Button(text="Spieltag starten",font_size=40)#size_hint_y=None)
        self.furtherButton.bind(on_release=self.goFurther)
        self.backFurtherButton.add_widget(self.backButton)
        self.furtherButton.disabled=True
        self.backFurtherButton.add_widget(self.furtherButton)
        self.add_widget(self.backFurtherButton)
        
        self.dropdownLand = DropDown()
        self.mainbuttonLand = Button(text='Land auswählen',font_size=40,size_hint = (1, 0.15))#, size_hint_y=None)
		# show the dropdown menu when the main button is released - note: all the bind() calls pass the instance of the caller (here, the mainbutton instance) as the first argument of the callback (here, dropdown.open.).
        self.mainbuttonLand.bind(on_release=self.dropdownLand.open)
        # one last thing, listen for the selection in the dropdown list and assign the data to the button text.
        self.dropdownLand.bind(on_select=lambda instance, x: setattr(self.mainbuttonLand, 'text', x))
        self.add_widget(self.mainbuttonLand)
        
        
        self.dropdownLeague = DropDown()
        self.mainbuttonLeague = Button(text='Liga auswählen',font_size=40,size_hint = (1, 0.15))#, size_hint_y=None)
		# show the dropdown menu when the main button is released - note: all the bind() calls pass the instance of the caller (here, the mainbutton instance) as the first argument of the callback (here, dropdown.open.).
        self.mainbuttonLeague.bind(on_release=self.dropdownLeague.open)
        # one last thing, listen for the selection in the dropdown list and assign the data to the button text.
        self.dropdownLeague.bind(on_select=lambda instance, x: setattr(self.mainbuttonLeague, 'text', x))
        self.add_widget(self.mainbuttonLeague)
        
        self.dropdownDay = DropDown()
        self.mainbuttonDay = Button(text='Spieltag auswählen',font_size=40,size_hint = (1, 0.15))#, size_hint_y=None)
		# show the dropdown menu when the main button is released - note: all the bind() calls pass the instance of the caller (here, the mainbutton instance) as the first argument of the callback (here, dropdown.open.).
        self.mainbuttonDay.bind(on_release=self.dropdownDay.open)
        # one last thing, listen for the selection in the dropdown list and assign the data to the button text.
        self.dropdownDay.bind(on_select=lambda instance, x: setattr(self.mainbuttonDay, 'text', x))
        self.add_widget(self.mainbuttonDay)
        
        self.labelCity = Label(text='',font_size=40,size_hint = (1, 0.4))#, size_hint_y=None)
        self.add_widget(self.labelCity)
        
        self.gameId=""
        self.land=""
    def goBack(self,instance):
        print("going back")
        rad_app.screen_manager.current = 'Start'
    def goFurther(self,instance):
        rad_app.pin_page.load_PinPage(self.land, self.gameId, self.league_short)
        
        # Called with a message, to update message text in widget
    def update_info(self):
        print("*********************************")
        self.dropdownLand.clear_widgets()
        landliste = sorted(os.listdir(app_folder+"/spieltage/"))
        for land in landliste:
          print(land)
          if os.path.isdir(app_folder+"/spieltage/"+land):
            btn = Button(text="Radball-Portal" if land == PORTAL_NAME else land, size_hint_y=None, height=80,font_size=40)
            btn.bind(on_release=lambda btn,land=land: self.update_leagues(btn,land))
            self.dropdownLand.add_widget(btn)
        
    def update_leagues(self, btn, land):
        self.land = land
        self.dropdownLand.select(btn.text)
        dateiliste=sorted(os.listdir(app_folder+"/spieltage/"+land))
        self.spieltage=dict()
        self.leagues=dict()
        for datei in dateiliste:
            if not datei.endswith(".radball"):
                continue
            try:
                path = os.path.join(app_folder, "spieltage", land, datei)
                with open(path, encoding="utf-8") as file:
                    game_json = json.load(file)
                league_name, _, _ = selection_labels(game_json)
                matchday_order(game_json)
            except (AttributeError, KeyError, OSError, TypeError, ValueError) as error:
                print(f"Spieltag übersprungen: {datei}: {error}")
                continue
            self.spieltage[datei] = game_json
            self.leagues.setdefault(league_name, []).append(game_json)
        self.dropdownLeague.clear_widgets()
        self.dropdownLeague.select("Liga auswählen")
        self.createdropdownDay(None)
        for league in sorted(self.leagues, key=league_order):
            item = Button(text=league, size_hint_y=None, height=80, font_size=40)
            item.bind(on_release=lambda button, league=league: self.dropdownLeagueAction(button, league))
            self.dropdownLeague.add_widget(item)

    def dropdownLeagueAction(self, btn, league):
        self.dropdownLeague.select(btn.text)
        self.createdropdownDay(league)

    def createdropdownDay(self, league):
        self.dropdownDay.clear_widgets()
        self.dropdownDay.select("Spieltag auswählen")
        self.labelCity.text = ""
        self.furtherButton.disabled = True
        for day in sorted(self.leagues.get(league, ()), key=matchday_order):
            _, label, city = selection_labels(day)
            start = day["start"][:10]
            displayed_date = ".".join(reversed(start.split("-")))
            item = Button(text=f"{label}\n{displayed_date}", size_hint_y=None, height=106,
                          font_size=30, halign="center", valign="middle")
            item.bind(size=lambda button, size: setattr(button, "text_size", (max(0, size[0] - 16), size[1])))
            item.bind(on_release=lambda button, day=day, city=city:
                      self.dropdownDayAction(button, day["number"], city, day["leagueShortName"]))
            self.dropdownDay.add_widget(item)

    def dropdownDayAction(self, btn,index,city,league_short):
        self.dropdownDay.select(btn.text)
        self.labelCity.text=city
        self.gameId=index
        self.league_short = league_short
        self.furtherButton.disabled=False
        
    # Called on label width update, so we can set text width properly - to 90% of label width
    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)

class PinPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols=1
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)




    def load_PinPage(self,land,game_id,league_short):
        self.land=land
        self.gameId=game_id
        self.league_short = league_short
        self.clear_widgets()
        self.backFurtherButton = GridLayout(cols=2,size_hint = (1, 0.15))
        self.backButton = Button(text="zurück",font_size=40)#size_hint_y=None)
        self.backButton.bind(on_release=self.goBack)
        self.furtherButton = Button(text="Pin übernehmen",font_size=40)#size_hint_y=None)
        self.furtherButton.bind(on_release=self.goFurther)
        self.backFurtherButton.add_widget(self.backButton)
        self.backFurtherButton.add_widget(self.furtherButton)
        self.add_widget(self.backFurtherButton)
        is_portal = land in PORTAL_REGIONS
        self.digital_url = matchday_url(land, league_short, game_id)
        self.pin_request = None
        rad_app.digital_access = None
        self.textinput = TextInput(input_filter=None if is_portal else "int", password=is_portal or bool(self.digital_url),
                                   multiline=False, size_hint=(1, 0.15), font_size=40)
        self.add_widget(self.textinput)
        self.lb = Label(text='Spieltags-PIN',size_hint = (1, 0.15),font_size=40)
        self.add_widget(self.lb)
        self.placeholder = Label(size_hint=(1, 0.55), font_size=34, halign="center", valign="middle")
        self.placeholder.bind(size=lambda label, size: setattr(label, "text_size", size))
        self.add_widget(self.placeholder)
        self.day_url = self.digital_url
        if is_portal:
            self.portal_scope = ResultQueue.scope(game_id, league_short.removeprefix("portal-"))
            self.day_url = f"{PORTAL_URL}/api/v1/matchdays/{game_id}"
        if self.day_url:
            self.show_saved_access()

        rad_app.screen_manager.current = 'Pin'

    def show_saved_access(self):
        saved = rad_app.portal_queue.saved_pin(self.day_url)
        self.textinput.text = saved
        self.furtherButton.text = "Weiter"
        if self.land in PORTAL_REGIONS and rad_app.portal_queue.token(self.portal_scope):
            self.placeholder.text = "Gerätezugang für diese Fläche gespeichert."
        elif saved:
            self.placeholder.text = "PIN gespeichert. Weiter zum Prüfen."
        else:
            self.placeholder.text = "PIN eingeben oder leer lassen, um lokal zu spielen."

    def goBack(self,instance):
        self.pin_request = None
        rad_app.screen_manager.current = 'Selector'
        print("going back")
    def goFurther(self, instance):
        pin = self.textinput.text.strip()
        if self.digital_url:
            rad_app.digital_access = None
            if not pin:
                self.open_portal_day()
                return
            self.textinput.text = ""
            self.furtherButton.disabled = True
            self.placeholder.text = "PIN wird geprüft ..."
            self.pin_request = UrlRequest(
                self.digital_url, method="GET", req_headers={"x-pin": pin, "Accept": "application/json",
                                                            "Cache-Control": "no-cache"},
                on_success=lambda req, data: self.accept_digital_pin(req, data, pin),
                on_failure=lambda req, data: self.digital_pin_failed(req, data, pin if req.resp_status in (401, 403) else None),
                on_error=self.digital_pin_failed,
                on_redirect=self.digital_pin_failed, timeout=5,
            )
            return
        if self.land not in PORTAL_REGIONS:
            rad_app.present_page.load_PresentPage(self.land, self.gameId, self.league_short, pin)
            return
        saved = rad_app.portal_queue.saved_pin(self.day_url)
        if not pin or (pin.upper() == saved and rad_app.portal_queue.token(self.portal_scope)):
            self.open_portal_day()
            return
        self.textinput.text = ""
        self.furtherButton.disabled = True
        self.placeholder.text = "PIN wird geprüft ..."
        scope = self.portal_scope
        self.pin_request = UrlRequest(
            f"{self.day_url}/access/redeem",
            req_body=json.dumps({"pin": pin.upper(), "court": int(scope.split(":")[1])}),
            req_headers={"Content-Type": "application/json"},
            on_success=lambda req, data: self.accept_portal_pin(req, scope, pin.upper(), data),
            on_failure=lambda req, data: self.portal_pin_failed(req, data, pin.upper()), on_error=self.portal_pin_failed,
            on_redirect=self.portal_pin_failed, timeout=5,
        )

    def open_portal_day(self):
        rad_app.present_page.load_PresentPage(self.land, self.gameId, self.league_short, "")

    def accept_digital_pin(self, request, data, pin):
        if request is not self.pin_request or rad_app.screen_manager.current != "Pin":
            return
        access = VerifiedMatchday.from_response(
            self.digital_url, self.league_short, self.gameId, pin, data,
        )
        if access is None:
            same_day = (isinstance(data, dict) and data.get("number") == self.gameId
                        and data.get("leagueShortName") == self.league_short)
            self.digital_pin_failed(request, data, pin if same_day else None)
            return
        self.pin_request = None
        self.furtherButton.disabled = False
        try:
            rad_app.portal_queue.remember_pin(self.day_url, pin)
        except OSError:
            rad_app.textpopup(title="PIN nicht gespeichert", text="Der Zugang gilt für dieses Spiel.")
        rad_app.digital_access = access
        self.open_portal_day()

    def digital_pin_failed(self, request, _, rejected=None):
        if request is not self.pin_request:
            return
        self.pin_request = None
        self.furtherButton.disabled = False
        self.discard_rejected_pin(rejected)
        self.placeholder.text = "PIN nicht bestätigt. PIN prüfen oder leer lassen."

    def discard_rejected_pin(self, rejected):
        try:
            rad_app.portal_queue.forget_pin(self.day_url, rejected)
        except OSError:
            rad_app.textpopup(title="PIN-Speicher prüfen", text="Der alte PIN konnte nicht entfernt werden.")

    def accept_portal_pin(self, request, scope, pin, data):
        if request is not self.pin_request or rad_app.screen_manager.current != "Pin":
            return
        self.pin_request = None
        self.furtherButton.disabled = False
        try:
            token = data["token"]
            if not isinstance(token, str) or not 32 <= len(token) <= 100:
                raise ValueError
            expires = datetime.datetime.fromisoformat(data["expires_at"]).timestamp()
            rad_app.portal_queue.set_token(scope, token, self.day_url, pin, expires)
        except (KeyError, TypeError, ValueError, OSError):
            self.placeholder.text = "Gerätezugang konnte nicht gespeichert werden."
            return
        if rad_app.screen_manager.current == "Pin" and scope == self.portal_scope:
            self.open_portal_day()

    def portal_pin_failed(self, request, result, pin=None):
        if request is not self.pin_request:
            return
        self.pin_request = None
        if request.resp_status == 403:
            self.discard_rejected_pin(pin)
        self.furtherButton.disabled = False
        self.placeholder.text = "PIN oder Verbindung prüfen. Leer: lokal spielen."


class PresentPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols=1
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)

    def load_PresentPage(self,land,game_id,league_short,pin=0):
        self.land=land
        self.gameId=game_id
        self.league_short = league_short
        self.clear_widgets()
        self.backFurtherButton = GridLayout(cols=2,size_hint = (1, 0.15))
        self.backButton = Button(text="zurück",font_size=40)#size_hint_y=None)
        self.backButton.bind(on_release=self.goBack)
        self.furtherButton = Button(text="alle anwesend",font_size=40)#size_hint_y=None)
        self.furtherButton.bind(on_release=self.goFurther)
        self.backFurtherButton.add_widget(self.backButton)
        self.backFurtherButton.add_widget(self.furtherButton)
        self.add_widget(self.backFurtherButton)
        
        
        rad_app.screen_manager.current = 'Present'
        f=open(app_folder+"/spieltage/"+str(land)+"/"+league_short+"_"+str(game_id)+".radball","r",encoding='utf-8')
        self.game_json=(json.loads(f.read()))
        if pin != "":
            self.game_json["pin"]=int(pin)
        self.teamsLayout = GridLayout(cols=2,size_hint = (1, 0.7))
        self.add_widget(Label(text="anwesende Mannschaften",font_size=40,size_hint = (1, 0.15)))
        self.add_widget(self.teamsLayout)
        self.bx=[]
        self.lb=[]
        teams=[]
        self.absent=[]
        i=0
        for team in self.game_json["teams"]:
            teamLayout = GridLayout(cols=1)
            print(team)
            #bx=CheckBox()
            #bx.active=True
            #teamLayout.add_widget(bx)
            lb=ToggleButton(text=team["name"],font_size=40,background_color = (0, 1, 0, 1))
            #teamLayout.bind(on_prese=lambda lb=lb: self.set_box(lb))
            lb.bind(on_press=lambda lb: self.unset_box(self,lb))
            lb.state="down"
            teamLayout.add_widget(lb)
            self.teamsLayout.add_widget(teamLayout)
            i+=1
    def unset_box(self, instance, box):
        print(box.state)
        if box.state=="normal":
            box.background_color = (0.88, 0, 0.73)
            self.absent.append(box.text)
            print(self.absent)
        else:
            box.background_color = (0, 1, 0, 1)
            self.absent.remove(box.text)
            print(self.absent)
        if len(self.absent)==0:
            self.furtherButton.text="alle anwesend"
        elif len(self.absent)==1:
            self.furtherButton.text="1 Mannschaft abwesend"
        else:
            self.furtherButton.text=str(len(self.absent)) +" Mannschaften abwesend"  
    def goBack(self,instance):
        rad_app.pin_page.load_PinPage(self.land, self.gameId, self.league_short)
        print("going back")
    def goFurther(self,instance):
        rad_app.sequence_page.load_SequencePage(self.game_json,self.absent,self.land,self.gameId,self.league_short)
        print("go on")
    

            
    
class SequencePage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols=1
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)

        self.index=0
    def load_SequencePage(self,game_json,absence_list,land,game_id,league_short):
        
        self.land=land
        self.gameId=game_id
        self.league_short = league_short
        rad_app.screen_manager.current = 'Sequence'
        self.game_json=game_json
        self.absence_list=absence_list
        self.clear_widgets()
        self.backFurtherButton = GridLayout(cols=2,size_hint = (1, 0.15))
        self.backButton = Button(text="zurück",font_size=40)#size_hint_y=None)
        self.backButton.bind(on_release=self.goBack)
        self.furtherButton = Button(text="weiter",font_size=40)#size_hint_y=None)
        self.furtherButton.bind(on_release=self.goFurther)
        self.backFurtherButton.add_widget(self.backButton)
        self.backFurtherButton.add_widget(self.furtherButton)
        self.add_widget(self.backFurtherButton)
        self.add_widget(Label(text="Spielreihenfolge (ohne ausfallende Spiele)",size_hint = (1, 0.05), font_size=30))
        self.sv = ScrollView(size_hint=(1, 1.0))
        self.add_widget(self.sv)
        
        self.layout = GridLayout(cols=1, spacing=10, size_hint_y=None,height=self.minimum_size[1])
        self.layout.bind(minimum_height=self.layout.setter('height'))

        self.sv.add_widget(self.layout)
        
        
        self.upDownButton = GridLayout(cols=2,size_hint = (1, 0.1))
        self.downButton = Button(text="nach hinten schieben",font_size=40,disabled = True)#size_hint_y=None)
        self.downButton.bind(on_release=self.down)
        self.upButton = Button(text="nach vorne schieben",font_size=40,disabled = True)#size_hint_y=None)
        self.upButton.bind(on_release=self.up)
        self.upDownButton.add_widget(self.upButton)
        self.upDownButton.add_widget(self.downButton)
        self.add_widget(self.upDownButton)
        self.upButton.disabled=True
        self.downButton.disabled=True


        
        self.update_buttons(range(len(self.game_json["games"])))
        
    def update_buttons(self,seq):
        self.layout.clear_widgets()
        self.sequence=[]
        self.buttonList=[]
        
        for game_nr in seq:
            print(self.game_json["games"][game_nr])
            score = {}

            if self.game_json["games"][game_nr]["teamA"] in self.absence_list and self.game_json["games"][game_nr]["teamB"] in self.absence_list:
                print("beide Teams nicht da")
                score["bothLost"]=True
                self.game_json["games"][game_nr]["score"]=score
            elif self.game_json["games"][game_nr]["teamA"] in self.absence_list:
                score["bothLost"]=False
                score["goalsA"]=0
                score["goalsB"]=5
                print("teamA nicht da")
                self.game_json["games"][game_nr]["score"]=score
            elif self.game_json["games"][game_nr]["teamB"] in self.absence_list:
                score["bothLost"]=False
                score["goalsA"]=5
                score["goalsB"]=0
                print("teamB nicht da")
                self.game_json["games"][game_nr]["score"]=score
            else:
                self.sequence.append(game_nr)
                text=str(self.game_json["games"][game_nr]["number"])
                text+=". Spiel "
                text+=self.game_json["games"][game_nr]["teamA"]
                text+=" : "
                text+=self.game_json["games"][game_nr]["teamB"]
                bt=(ToggleButton(text=text,size_hint_y=None, height=40, font_size=30))
                self.buttonList.append(bt)
                bt.bind(on_press=lambda bt,game_nr=game_nr: self.select_game(self,bt,game_nr))
                self.layout.add_widget(bt)
        #print(absence_list)
        for game_nr in range(len(self.game_json["games"])):
            print( self.game_json["games"][game_nr])
    def select_game(self, instance, button,gamenr):
        for tempbt in self.buttonList:
            tempbt.state="normal"
        button.state="down"
        print(self.buttonList)
        self.index=gamenr
        self.activateButton()
        
    def activateButton(self):
        gamenr=self.index
        if self.sequence.index(gamenr)>0:
            self.upButton.disabled=False
        else:
            self.upButton.disabled=True
        if self.sequence.index(gamenr)<len(self.sequence)-1:
            self.downButton.disabled=False
        else:
            self.downButton.disabled=True
    def goBack(self,instance):
        rad_app.screen_manager.current = 'Present'
        print("going back")
    def goFurther(self,instance):
        rad_app.game_page.load_GamePage(self.game_json,self.sequence,self.land,self.gameId,self.league_short)
       
        print("go on")
        
    def up(self,instance):
        pos=self.sequence.index(self.index)
        print(pos)
        self.sequence[pos],self.sequence[pos-1]=self.sequence[pos-1],self.sequence[pos]
        self.update_buttons(self.sequence)
        self.buttonList[pos-1].state="down"
        self.activateButton()

        print("up")
    def down(self,instance):
        pos=self.sequence.index(self.index)
        print(pos)
        self.sequence[pos],self.sequence[pos+1]=self.sequence[pos+1],self.sequence[pos]
        self.update_buttons(self.sequence)
        self.buttonList[pos+1].state="down"
        self.activateButton()
                
        print("down")    
 
 
class GamePage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols=1
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)

        self.index=0 
        self.firstLine = GridLayout(cols=3,size_hint = (1, 0.2))
        self.LineHidden = GridLayout(cols=1,size_hint = (1, 0.0))
        self.secondLine = GridLayout(cols=3,size_hint = (1, 0.2))
        self.thirdLine = GridLayout(cols=5,size_hint = (1, 0.2))
        self.fourthLine = GridLayout(cols=4,size_hint = (1, 0.2))
        self.fifthLine = GridLayout(cols=3,size_hint = (1, 0.2))
        self.add_widget(self.firstLine)
        self.add_widget(self.secondLine)
        self.add_widget(self.LineHidden)
        self.add_widget(self.thirdLine)
        self.add_widget(self.fourthLine)
        self.add_widget(self.fifthLine)

        
        self.gameNr=0
        self.gameStatus=0
        # 0 = stopped
        # 1 = running
        # 2 = halftime
        self.halfTime = timedelta ( minutes= 2)
        self.timeLeft = timedelta ( minutes = 0, seconds = 15)
        self.playingTime = timedelta ( minutes = 7)
        self.startTime = datetime.datetime.now()
        self.pauseTime = datetime.datetime.now()        
        
        self.teamALabel=Label(size_hint = (0.4, 1),text="Team 1",font_size=60)
        self.teamBLabel=Label(size_hint = (0.4, 1),text="Team 2",font_size=60)
        self.htLabel=Label(size_hint = (0.2, 1),text="1. Halbzeit",font_size=50)
        self.firstLine.add_widget(self.teamALabel)
        self.firstLine.add_widget(self.htLabel)
        self.firstLine.add_widget(self.teamBLabel)
        
        self.goalALabel=Label(size_hint = (0.3, 1),text="0",font_size=60)
        self.goalBLabel=Label(size_hint = (0.3, 1),text="0",font_size=60)
        self.timeLabel=Label(size_hint = (0.4, 1),text="7:00",font_size=60)
        self.secondLine.add_widget(self.goalALabel)
        self.secondLine.add_widget(self.timeLabel)
        self.secondLine.add_widget(self.goalBLabel)
        
        self.teamAp=Button(size_hint = (0.15, 1),text="+",font_size=60)
        self.teamAm=Button(size_hint = (0.15, 1),text="-",font_size=60)
        self.teamBp=Button(size_hint = (0.15, 1),text="+",font_size=60)
        self.teamBm=Button(size_hint = (0.15, 1),text="-",font_size=60)
        self.sideButton=Button(size_hint =(0.4, 1),text="Seitenwechsel",font_size=40)
        self.thirdLine.add_widget(self.teamAp)
        self.thirdLine.add_widget(self.teamAm)
        self.thirdLine.add_widget(self.sideButton)
        self.thirdLine.add_widget(self.teamBp)
        self.thirdLine.add_widget(self.teamBm)
        
        self.sideButton.bind(on_release=self.sideChange)
        self.teamAp.bind(on_release=self.teamApCB)
        self.teamAm.bind(on_release=self.teamAmCB)
        self.teamBp.bind(on_release=self.teamBpCB)
        self.teamBm.bind(on_release=self.teamBmCB)

        
        self.rszButton=Button(size_hint =(0.3, 1),text="Restspielzeit",font_size=40)
        self.rszButton.bind(on_release=self.setRsz)
        self.pauseButton=Button(size_hint =(0.4, 1),text="Halbzeitpause starten",font_size=40)
        self.pauseButton.bind(on_release=self.setPause)
        self.settingsButton=Button(size_hint =(0.3, 1),text="Einstellungen",font_size=40)
        self.settingsButton.bind(on_release=self.create_popup)
        
        self.fourthLine.add_widget(self.rszButton)
        self.fourthLine.add_widget(self.pauseButton)
        self.rszButton.font_size = 30
        self.pauseButton.font_size = 30
        self.settingsButton.font_size = 31
        self.fourthLine.add_widget(self.settingsButton)
        self.display_button = Button(text="Anzeigen", font_size=31, size_hint=(.3, 1))
        self.display_button.bind(on_release=self.choose_displays)
        self.fourthLine.add_widget(self.display_button)
        self.display_popup = None
        
        self.lastButton=Button(size_hint =(0.3, 1),text="vorheriges Spiel",font_size=40)
        self.lastButton.bind(on_release=self.lastGame)
        
        self.startStopButton=Button(size_hint =(0.4, 1),text="Zeit starten",font_size=40)
        self.startStopButton.bind(on_release=self.startGame)

        self.nextButton=Button(size_hint =(0.3, 1),text="nächstes Spiel",font_size=40)
        self.nextButton.bind(on_release=self.nextGame)

        self.fifthLine.add_widget(self.lastButton)
        self.fifthLine.add_widget(self.startStopButton)
        self.fifthLine.add_widget(self.nextButton)
        
        self.popup = []
        
        self.rotation=False
        # Coalesce a side swap or several label changes into one complete scoreboard snapshot.
        self.refresh_display = Clock.create_trigger(self.refreshTime, -1)
        self.goalALabel.bind(text=self.refresh_display)
        self.goalBLabel.bind(text=self.refresh_display)


    def load_GamePage(self,game_json,sequence,land,game_id,league_short):
        if not sequence:
            rad_app.textpopup(title="Kein spielbares Spiel", text="Prüfe den Spielplan und die anwesenden Mannschaften.")
            return
        welcome = game_json.get("welcome") or "Willkommen zur Radballanzeige"
        rad_app.start_page.message.text = welcome
        if rad_app.config.get("halle", "welcome") != welcome:
            rad_app.config.set("halle", "welcome", welcome)
            rad_app.config.write()
        self.match_drafts = {}
        Clock.schedule_interval(self.refreshTime, 0.1)
        rad_app.displays.seen.clear()
        Clock.schedule_interval(self.findClients, .5)
        print(sequence)
        self.sequence = sequence
        self.game_json = game_json
        self.land=land
        self.gameId=game_id
        self.league_short = league_short
        rad_app.screen_manager.current = 'Game'
        if platform == "android":
            orientation.set_sensor(mode="landscape")
            Window.allow_screensaver = False
        self.gameNr = sequence[0]
        self.load_Game()
    def load_Game (self):
        print(self.gameNr)
        game = self.game_json["games"][self.gameNr]
        draft = self.match_drafts.get(self.gameNr, {})
        self.timeLeft = draft.get("time_left", self.playingTime)
        self.regulation_expired = draft.get("expired", False)
        self.gameStatus = 0
        self.pauseButton.text = "Halbzeitpause starten"
        self.pauseButton.disabled = not (self.timeLeft <= timedelta(0) and not draft.get("second_half"))
        self.LineHidden.clear_widgets()
        self.LineHidden.size_hint = (1, 0)
        self.firstLine.size_hint = self.secondLine.size_hint = (1, 0.2)
        self.teamALabel.text=self.game_json["games"][self.gameNr]["teamA"]
        self.teamBLabel.text=self.game_json["games"][self.gameNr]["teamB"]
        
        self.htLabel.text = "2. Halbzeit" if draft.get("second_half") else "1. Halbzeit"
        self.startStopButton.disabled = self.result_is_final()
        self.nextButton.disabled = False
        
        score = draft.get("score", game.get("score", {}))
        if score:
            if {"goalsA", "goalsB"} <= score.keys():
                self.goalALabel.text = str(score["goalsA"])
                self.goalBLabel.text = str(score["goalsB"])
                print("there is a score")
            else:
                self.goalALabel.text= "0"
                self.goalBLabel.text= "0"
        else:
            self.goalALabel.text= "0"
            self.goalBLabel.text= "0"
            
            
        if self.gameNr == self.sequence [0] :
            #game is first game
            self.lastButton.disabled=True
        else:
            self.lastButton.disabled=False
        if self.gameNr == self.sequence[-1]:
            #game is last game
            #self.nextButton.disabled=True
            self.nextButton.unbind(on_release=self.nextGame)
            self.nextButton.text = "Spieltag beenden"
            self.nextButton.bind(on_release=self.quitGames)
        else:
            #self.nextButton.disabled=False
            if self.nextButton.text == "Spieltag beenden":
                self.nextButton.text = "nächstes Spiel"
                self.nextButton.bind(on_release=self.nextGame)
                self.nextButton.unbind(on_release=self.quitGames)
    
        self.refresh_display()

    def nav_score(self):
        game = self.game_json["games"][self.gameNr]
        left, right = int(self.goalALabel.text), int(self.goalBLabel.text)
        if self.teamALabel.text != game["teamA"]:
            left, right = right, left
        return {"bothLost": False, "goalsA": left, "goalsB": right}

    def result_is_final(self):
        game = self.game_json["games"][self.gameNr]
        return game["state"] == "finished" or (
            matchday_url(self.land, self.league_short, self.gameId) is not None and scored(game)
        ) or (
            self.land in PORTAL_REGIONS and rad_app.portal_queue.already_finished(game)
        )

    def leave_current_match(self):
        if may_finalize_on_navigation(self.regulation_expired, self.result_is_final()):
            if not self.save_current_result(self.nav_score()):
                return False
        game = self.game_json["games"][self.gameNr]
        if not self.result_is_final():
            # A draft is presentation state only. Navigation does not change game state.
            self.match_drafts[self.gameNr] = {
                "time_left": self.timeLeft, "expired": self.regulation_expired,
                "second_half": self.htLabel.text == "2. Halbzeit", "score": self.nav_score(),
            }
        return True

    def nextGame(self, instance):
        if self.leave_current_match():
            self.gameNr = self.sequence[self.sequence.index(self.gameNr) + 1]
            self.load_Game()

    def lastGame(self, instance):
        if self.leave_current_match():
            self.gameNr = self.sequence[self.sequence.index(self.gameNr) - 1]
            self.load_Game()

    def quitGames(self, instance):
        if getattr(rad_app, "back_popup", None):
            return
        box = BoxLayout(orientation="vertical", padding=12, spacing=8)
        box.add_widget(Label(text="Spieltag beenden und zum Hauptmenü zurückkehren?", font_size=25))
        buttons = BoxLayout(spacing=8)
        cancel = Button(text="Weiterspielen", font_size=26)
        confirm = Button(text="Spieltag beenden", font_size=26)
        buttons.add_widget(cancel)
        buttons.add_widget(confirm)
        box.add_widget(buttons)
        popup = Popup(title="Spieltag beenden?", content=box, size_hint=(.94, .48), auto_dismiss=False)
        rad_app.back_popup = popup
        popup.bind(on_dismiss=lambda *_: setattr(rad_app, "back_popup", None))
        cancel.bind(on_release=popup.dismiss)
        def finish(*_):
            popup.dismiss()
            if self.leave_current_match():
                self.leave_game_screen()
        confirm.bind(on_release=finish)
        popup.open()

    def leave_game_screen(self):
        if self.gameStatus == 1:
            self.stopGame(self)
        self.refresh_display.cancel()
        Clock.unschedule(self.refreshTime)
        Clock.unschedule(self.findClients)
        if platform == "android" or debug:
            try:
                sock.sendto(b'{"idle":true}', ("127.0.0.1", 5066))
            except OSError:
                pass
        Window.allow_screensaver = True
        if platform == "android":
            orientation.set_sensor(mode="any")
        rad_app.screen_manager.current = "Start"

    def confirm_game_result(self, instance):
        if self.gameStatus == 1 or self.result_is_final():
            return
        self.popup.dismiss()
        game = self.game_json["games"][self.gameNr]
        score = self.nav_score()
        layout = GridLayout(cols=1, padding=12, spacing=12)
        layout.add_widget(Label(
            text=f"{game['teamA']} – {game['teamB']}\n{score['goalsA']}:{score['goalsB']}",
            font_size=30,
        ))
        actions = GridLayout(cols=2, spacing=12)
        cancel = Button(text="Abbrechen", font_size=26)
        confirm = Button(text="Resultat speichern", font_size=26)
        actions.add_widget(cancel)
        actions.add_widget(confirm)
        layout.add_widget(actions)
        popup = Popup(title="Spiel abschliessen?", content=layout, size_hint=(.8, .65))
        cancel.bind(on_release=popup.dismiss)
        confirm.bind(on_release=lambda *_: self.finish_game(popup, score))
        popup.open()

    def finish_game(self, popup, score):
        if self.save_current_result(score):
            popup.dismiss()

    def save_current_result(self, score):
        if self.result_is_final():
            return True
        if self.land in PORTAL_REGIONS and not self.queue_portal_result(score):
            return False
        game = self.game_json["games"][self.gameNr]
        game["score"] = score
        game["state"] = "finished"
        self.startStopButton.disabled = True
        self.pauseButton.disabled = True
        self.match_drafts.pop(self.gameNr, None)
        self.send_digital_result(game)
        return True

    def findClients(self, instance):
        if sock2 is None:
            return
        now = time.monotonic()
        for _ in range(64):
            try:
                data, (address, _) = sock2.recvfrom(2048)
            except BlockingIOError:
                break
            rad_app.displays.discover(data, address, now)
        rad_app.displays.available(now)
        if self.display_popup:
            self.render_displays()

    def choose_displays(self, *_):
        if self.display_popup:
            return
        body = BoxLayout(orientation="vertical", spacing=8)
        scroll = ScrollView()
        self.display_rows = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.display_rows.bind(minimum_height=self.display_rows.setter("height"))
        scroll.add_widget(self.display_rows)
        body.add_widget(scroll)
        maintenance = Button(text="Raspberry Pi warten", size_hint_y=None, height=56)
        maintenance.bind(on_release=lambda *_: self.open_pi_maintenance())
        body.add_widget(maintenance)
        close = Button(text="Fertig", size_hint_y=None, height=56)
        body.add_widget(close)
        self.display_popup = Popup(title="Hallenanzeigen auswählen", content=body, size_hint=(.94, .85))
        close.bind(on_release=self.display_popup.dismiss)
        self.display_popup.bind(on_dismiss=lambda *_: setattr(self, "display_popup", None))
        self.display_state = None
        self.render_displays()
        self.display_popup.open()

    def open_pi_maintenance(self):
        url = "https://connect.raspberrypi.com/"
        if platform == "android":
            intent = autoclass("android.content.Intent")
            uri = autoclass("android.net.Uri").parse(url)
            mActivity.startActivity(intent(intent.ACTION_VIEW, uri))
        else:
            import webbrowser
            webbrowser.open(url)

    def render_displays(self):
        devices = rad_app.displays
        state = [(key, item["name"], item["address"], item["owner"], item["modes"],
                  devices.choices.get(key, "off")) for key, item in sorted(devices.seen.items())]
        if state == self.display_state:
            return
        self.display_state = state
        self.display_rows.clear_widgets()
        if not state:
            self.display_rows.add_widget(Label(text="Suche Hallenanzeigen im WLAN …", size_hint_y=None, height=64))
        for key, name, address, owner, supported, selected in state:
            busy = owner not in ("", devices.controller)
            row = BoxLayout(size_hint_y=None, height=66, spacing=8)
            row.add_widget(Label(text=f"{name} · {address}" + (" · belegt" if busy else ""), font_size=21))
            modes = ("off",) if busy else ("off", *supported)
            choice = Spinner(text=MODES.get(selected if selected in modes or busy else "game", "Aus"), values=[MODES[m] for m in modes],
                             disabled=busy and selected == "off", font_size=23)
            choice.bind(text=lambda _, value, k=key: self.select_display(k, value))
            row.add_widget(choice)
            self.display_rows.add_widget(row)

    def select_display(self, key, label):
        choices = dict(rad_app.displays.choices)
        mode = next(m for m, text in MODES.items() if text == label)
        if mode == "off":
            choices.pop(key, None)
        else:
            choices[key] = mode
        rad_app.config.set("halle", "displays", json.dumps(choices))
        rad_app.config.write()
        rad_app.displays.choices = choices
        self.refresh_display()

    def refreshTime (self,instance):
        
        next_position = self.sequence.index(self.gameNr) + 1
        nextTeams = nextTeamsLocal = ""
        if next_position < len(self.sequence) and (
            self.timeLeft <= timedelta(0)
            or (self.timeLeft == self.playingTime and self.htLabel.text == "2. Halbzeit"
                and self.startStopButton.text == "Zeit starten")
        ):
            upcoming = self.game_json["games"][self.sequence[next_position]]
            home, away = upcoming["teamA"], upcoming["teamB"]
            nextTeams = f"{home} \n {away}"
            nextTeamsLocal = f"nächstes Spiel: {home} gegen {away}"
        if self.gameStatus == 0:
            remTime = self.timeLeft
            if remTime <= timedelta(0):
                self.timeLabel.text = "0:00"
                remTime = timedelta ( seconds = 0)
            elif remTime < timedelta ( seconds = 10):
                total_seconds = (remTime.total_seconds())
                hours, remainder = divmod(total_seconds,60*60)
                minutes, seconds = divmod(remainder,60)
          #      seconds, remainder = divmod(remainder,1)
                self.timeLabel.text = '{}:{}'.format("{:02.0f}".format(minutes),"{:04.1f}".format(seconds))
            else :    
                total_seconds = int(remTime.total_seconds())
                hours, remainder = divmod(total_seconds,60*60)
                minutes, remainder = divmod(remainder,60)
                seconds, remainder = divmod(remainder,1)
                self.timeLabel.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        elif self.gameStatus == 1:
            remTime = -(datetime.datetime.now() - self.startTime) + self.timeLeft
            if remTime <= timedelta(0):
                self.timeLabel.text = "0:00"
                self.stopGame(self)
                self.pauseButton.disabled = self.htLabel.text == "2. Halbzeit"
                remTime = timedelta ( seconds = 0)
            elif remTime < timedelta ( seconds = 10):
                total_seconds = (remTime.total_seconds())
                hours, remainder = divmod(total_seconds,60*60)
                minutes, seconds = divmod(remainder,60)
           #     seconds, remainder = divmod(remainder,1)
                self.timeLabel.text = '{}:{}'.format("{:02.0f}".format(minutes),"{:04.1f}".format(seconds))
            else :    
                total_seconds = int(remTime.total_seconds())
                hours, remainder = divmod(total_seconds,60*60)
                minutes, remainder = divmod(remainder,60)
                seconds, remainder = divmod(remainder,1)
                self.timeLabel.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        elif self.gameStatus == 2:
            remTime = self.timeLeft
            remPause = -(datetime.datetime.now() - self.pauseTime) + self.halfTime
            
            if remPause  > timedelta(0):

                total_seconds = int(remTime.total_seconds())
                hours, remainder = divmod(total_seconds,60*60)
                minutes, remainder = divmod(remainder,60)
                seconds, remainder = divmod(remainder,1)
                
                pause_seconds = int(remPause.total_seconds())
                pause_hours, remainder = divmod(pause_seconds,60*60)
                pause_minutes, remainder = divmod(remainder,60)
                pause_seconds, remainder = divmod(remainder,1)
                
                
                self.timeLabel.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
                self.pauseButton.text = '{}:{}'.format("{:0>2d}".format(pause_minutes),"{:0>2d}".format(pause_seconds))
                self.nextLabel.text = nextTeamsLocal
            else:
                self.gameStatus = 0
                self.pauseButton.text = "Halbzeitpause starten"

            
        routes = rad_app.displays.routes(time.monotonic())
        left, right = (self.teamALabel.text, self.goalALabel.text), (self.teamBLabel.text, self.goalBLabel.text)
        if self.rotation:
            left, right = right, left
        minutes, seconds = self.timeLabel.text.split(":")
        frame = dict(team1=left[0], team2=right[0], tore1=left[1], tore2=right[1],
                     minutes=minutes, seconds=seconds, schnaps=0, next=nextTeams, status=self.gameStatus,
                     rem=str(remTime), routes=routes, controller=rad_app.displays.controller)
        if any(route[2] == "results" for route in routes):
            score = self.nav_score()
            frame["overview"] = result_page(self.game_json["games"], self.sequence, self.gameNr,
                                            score["goalsA"], score["goalsB"], time.monotonic())
            if self.land in PORTAL_REGIONS:
                frame["event_id"] = self.game_json.get("portal_event_id")
        try:
            if platform == "android" or debug:
                sock.sendto(json.dumps(frame, ensure_ascii=False).encode(), ("127.0.0.1", 5066))
            else:
                send_displays(sock, frame)
        except OSError:
            pass

    def setRsz (self,instance):
        self.rszButton.text="Restspielzeit setzen"
        self.rszButton.unbind(on_release=self.setRsz)
        self.rszButton.bind(on_release=self.finishRsz)
        self.sideButton.unbind(on_release=self.sideChange)
        
        total_seconds = int(self.playingTime.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
        self.sideButton.bind(on_release=self.resetTime)
        self.startStopButton.disabled=True
        self.setButtons()
        
    def finishRsz (self,instance):
        
        total_seconds = int(self.playingTime.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        playing_str = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
        if not self.sideButton.text == playing_str:
            t = datetime.datetime.strptime(self.sideButton.text,"%M:%S")
            self.timeLeft = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
            self.regulation_expired = False

        self.rszButton.text="Restspielzeit"
        self.rszButton.unbind(on_release=self.finishRsz)  
        self.rszButton.bind(on_release=self.setRsz)  
        self.sideButton.unbind(on_release=self.resetTime)
        self.sideButton.text="Seitenwechsel"
        self.sideButton.bind(on_release=self.sideChange)
        self.startStopButton.disabled = self.result_is_final()
        self.resetButtons()
     
    def resetTime (self,instance=None):
        t = datetime.datetime.strptime(self.sideButton.text,"%M:%S")
        self.timeLeft = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        self.regulation_expired = False

    def setButtons  (self):
        self.teamAp.text="+10s"
        self.teamAp.font_size=40
        self.teamAm.text="-10s"
        self.teamAm.font_size=40
        self.teamBp.text="+1s"
        self.teamBp.font_size=40
        self.teamBm.text="-1s"
        self.teamBm.font_size=40
        
        self.teamAp.unbind(on_release=self.teamApCB)
        self.teamAm.unbind(on_release=self.teamAmCB)
        self.teamBp.unbind(on_release=self.teamBpCB)
        self.teamBm.unbind(on_release=self.teamBmCB)
        self.teamAp.bind(on_release=self.p10s)
        self.teamAm.bind(on_release=self.m10s)
        self.teamBp.bind(on_release=self.p1s)
        self.teamBm.bind(on_release=self.m1s)
        
    def resetButtons  (self):
        self.teamAp.text="+"
        self.teamAp.font_size=60
        self.teamAm.text="-"
        self.teamAm.font_size=60
        self.teamBp.text="+"
        self.teamBp.font_size=60
        self.teamBm.text="-"
        self.teamBm.font_size=60
        
        self.teamAp.unbind(on_release=self.p10s)
        self.teamAm.unbind(on_release=self.m10s)
        self.teamBp.unbind(on_release=self.p1s)
        self.teamBm.unbind(on_release=self.m1s)
        
        
        
        self.teamAp.bind(on_release=self.teamApCB)
        self.teamAm.bind(on_release=self.teamAmCB)
        self.teamBp.bind(on_release=self.teamBpCB)
        self.teamBm.bind(on_release=self.teamBmCB)
    
    
    def p1s (self,instance):
        total_seconds = int(self.playingTime.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        playing_str = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
        if self.sideButton.text == playing_str:
            total_seconds = int(self.timeLeft.total_seconds())
            hours, remainder = divmod(total_seconds,60*60)
            minutes, remainder = divmod(remainder,60)
            seconds, remainder = divmod(remainder,1)
            self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        t = datetime.datetime.strptime(self.sideButton.text,"%M:%S") + timedelta(seconds=1)
        t = datetime.timedelta(days=t.day, hours=t.hour, minutes=t.minute, seconds=t.second)
        
        total_seconds = int(t.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
    def p10s (self,instance):
        total_seconds = int(self.playingTime.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        playing_str = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
        if self.sideButton.text == playing_str:
            total_seconds = int(self.timeLeft.total_seconds())
            hours, remainder = divmod(total_seconds,60*60)
            minutes, remainder = divmod(remainder,60)
            seconds, remainder = divmod(remainder,1)
            self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
            
        t = datetime.datetime.strptime(self.sideButton.text,"%M:%S") + timedelta(seconds=10)
        t = datetime.timedelta(days=t.day, hours=t.hour, minutes=t.minute, seconds=t.second)
        
        total_seconds = int(t.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
    def m1s (self,instance):
        total_seconds = int(self.playingTime.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        playing_str = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
        if self.sideButton.text == playing_str:
            total_seconds = int(self.timeLeft.total_seconds())
            hours, remainder = divmod(total_seconds,60*60)
            minutes, remainder = divmod(remainder,60)
            seconds, remainder = divmod(remainder,1)
            self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
            
        t = datetime.datetime.strptime(self.sideButton.text,"%M:%S") - timedelta(seconds=1)
        base = datetime.datetime(1900, 1, 1)
        if (t - base) > timedelta(0):


            t = datetime.timedelta(days=t.day, hours=t.hour, minutes=t.minute, seconds=t.second)
            
            
            total_seconds = int(t.total_seconds())
            hours, remainder = divmod(total_seconds,60*60)
            minutes, remainder = divmod(remainder,60)
            seconds, remainder = divmod(remainder,1)
            self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
    def m10s (self,instance):
        total_seconds = int(self.playingTime.total_seconds())
        hours, remainder = divmod(total_seconds,60*60)
        minutes, remainder = divmod(remainder,60)
        seconds, remainder = divmod(remainder,1)
        playing_str = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
        
        if self.sideButton.text == playing_str:
            total_seconds = int(self.timeLeft.total_seconds())
            hours, remainder = divmod(total_seconds,60*60)
            minutes, remainder = divmod(remainder,60)
            seconds, remainder = divmod(remainder,1)
            self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
            
        t = datetime.datetime.strptime(self.sideButton.text,"%M:%S") - timedelta(seconds=10)
        base = datetime.datetime(1900, 1, 1)
        if (t - base) > timedelta(0):
            t = datetime.timedelta(days=t.day, hours=t.hour, minutes=t.minute, seconds=t.second)
            
            
            total_seconds = int(t.total_seconds())
            hours, remainder = divmod(total_seconds,60*60)
            minutes, remainder = divmod(remainder,60)
            seconds, remainder = divmod(remainder,1)
            self.sideButton.text = '{}:{}'.format("{:0>2d}".format(minutes),"{:0>2d}".format(seconds))
        
    def startGame (self,instance):
        if self.timeLeft <= timedelta(0) or self.result_is_final():
            return
        self.regulation_expired = False
        self.LineHidden.clear_widgets()
        self.LineHidden.size_hint = (1, 0.0)
        self.firstLine.size_hint = (1, 0.2)
        self.secondLine.size_hint = (1, 0.2)

        self.startStopButton.text="Zeit stoppen"
        self.startTime = datetime.datetime.now()    
        self.startStopButton.unbind(on_release=self.startGame)
        self.startStopButton.bind(on_release=self.stopGame)
        self.rszButton.disabled = True
        self.pauseButton.disabled = True
        self.settingsButton.disabled = True
        self.lastButton.disabled = True
        self.nextButton.disabled = True
        self.gameStatus=1 
        self.game_json["games"][self.gameNr]["state"]="running"
        self.pauseButton.text = "Halbzeitpause starten"
        self.refresh_display()

    def stopGame (self,instance):
        self.startStopButton.text="Zeit starten"
        remaining = self.timeLeft - (datetime.datetime.now() - self.startTime)
        self.regulation_expired = expired_during_play(remaining, self.htLabel.text == "2. Halbzeit")
        self.timeLeft = max(timedelta(0), remaining)
        self.pauseButton.disabled = self.timeLeft > timedelta(0) or self.htLabel.text == "2. Halbzeit"
        self.startStopButton.unbind(on_release=self.stopGame)         
        self.startStopButton.bind(on_release=self.startGame)
        self.rszButton.disabled = False
        self.settingsButton.disabled = False
        self.nextButton.disabled=False

        if self.gameNr == 0:
            #game is first game
            self.lastButton.disabled=True
        else:
            self.lastButton.disabled=False
        if self.gameNr == len(self.sequence)-1:
            #game is last game
            pass
            #self.nextButton.disabled=True
        else:
            self.nextButton.disabled=False

        self.gameStatus=0
        self.refresh_display()
        
    def sideChange (self,instance=None):    
        teamA = self.teamALabel.text
        goalA = self.goalALabel.text
        self.teamALabel.text = self.teamBLabel.text
        self.teamBLabel.text = teamA
        self.goalALabel.text = self.goalBLabel.text
        self.goalBLabel.text = goalA
        self.refresh_display()

    def setPause (self,instance):
        self.regulation_expired = False
        self.sideChange()
        self.pauseTime = datetime.datetime.now()  
        self.timeLeft = self.playingTime
        self.htLabel.text="2. Halbzeit"
        self.gameStatus = 2
        self.pauseButton.disabled = True
        
        self.nextLabel=Label(size_hint = (0.2, 1),font_size=30)
        self.LineHidden.add_widget(self.nextLabel)
        self.firstLine.size_hint = (1, 0.15)
        self.secondLine.size_hint = (1, 0.15)
        self.LineHidden.size_hint = (1, 0.1)
        
    def teamApCB (self,instance):
        self.goalALabel.text = str(int(self.goalALabel.text) + 1)          
    def teamAmCB (self,instance):
        if int(self.goalALabel.text) > 0 :
            self.goalALabel.text = str(int(self.goalALabel.text) - 1)
    def teamBpCB (self,instance):
        self.goalBLabel.text = str(int(self.goalBLabel.text) + 1)
    def teamBmCB (self,instance):        
        if int(self.goalBLabel.text) > 0 :
            self.goalBLabel.text = str(int(self.goalBLabel.text) - 1)
    
    def queue_portal_result(self, score):
        try:
            scope = ResultQueue.scope(self.gameId, self.game_json["portal_court"])
            game = self.game_json["games"][self.gameNr]
            rad_app.portal_queue.enqueue(scope, game, score["goalsA"], score["goalsB"])
        except KeyError:
            rad_app.textpopup(title="Resultat nicht gespeichert",
                              text="Bitte lade den Spieltag mit dieser App-Version erneut vom Portal.")
            return False
        except (OSError, ValueError):
            rad_app.textpopup(title="Resultat nicht gespeichert", text="Bitte versuche es erneut.")
            return False
        rad_app.show_portal_status()
        return True


    def send_digital_result(self, game):
        access = rad_app.digital_access
        if access is None:
            return
        url = matchday_url(self.land, self.league_short, self.gameId)
        request = access.final_request(url, game, rad_app.digital_attempted)
        if request is None:
            return
        destination, headers, body = request

        def failed(_request, _result):
            rad_app.textpopup(title="Endresultat nicht übertragen",
                              text="Das Ergebnis ist lokal übernommen. Bitte den Online-Eintrag prüfen.")

        UrlRequest(destination, method="PUT", req_headers=headers, req_body=body,
                   on_failure=failed, on_error=failed, on_redirect=failed, timeout=5)

    def create_popup(self,instance):
        layout=GridLayout(cols=1, rows=10)
        self.padding = (50, 50, 50, 50)
        min_5 = Button(text='5 min',font_size=40)
        min_6 = Button(text='6 min',font_size=40)
        min_7 = Button(text='7 min',font_size=40)
        swapBt = Button(text='Halbzeit anpassen',font_size=40)
        swapPos = Button(text='Anzeige drehen',font_size=40)
        dismiss = Button(text='Abbrechen',font_size=40)
        self.popup = Popup(title='Einstellungen',content=layout, auto_dismiss=False)
        layout.add_widget(min_5)
        layout.add_widget(min_6)
        layout.add_widget(min_7)
        layout.add_widget(swapBt)
        layout.add_widget(swapPos)
        manual = Button(text="Resultat manuell übernehmen", font_size=32, disabled=self.result_is_final())
        manual.bind(on_release=self.confirm_game_result)
        layout.add_widget(manual)
        layout.add_widget(dismiss)
        min_5.bind(on_release=(self.set_playtime5))
        min_6.bind(on_release=(self.set_playtime6))
        min_7.bind(on_release=(self.set_playtime7))
        swapBt.bind(on_release=(self.swapHT))
        swapPos.bind(on_release=(self.swapP))
        dismiss.bind(on_release=self.popup.dismiss)
        self.popup.open()        
    
    def set_playtime5(self,instance):
        if self.timeLeft == self.playingTime:
            self.playingTime = timedelta ( minutes = 5)
            self.timeLeft = self.playingTime
        else:
            self.playingTime = timedelta ( minutes = 5)
        self.popup.dismiss()
    def set_playtime6(self,instance):
        if self.timeLeft == self.playingTime:
            self.playingTime = timedelta ( minutes = 6)
            self.timeLeft = self.playingTime
        else:
            self.playingTime = timedelta ( minutes = 6)
        self.popup.dismiss()
    def set_playtime7(self,instance):
        if self.timeLeft == self.playingTime:
            self.playingTime = timedelta ( minutes = 7)
            self.timeLeft = self.playingTime
        else:
            self.playingTime = timedelta ( minutes = 7)
        self.popup.dismiss()
    def swapHT(self,instance):
        self.regulation_expired = False
        if self.htLabel.text=="1. Halbzeit":
            self.htLabel.text="2. Halbzeit"
        else:
            self.htLabel.text="1. Halbzeit"
        self.popup.dismiss()
    def swapP(self,instance):
        self.rotation = not self.rotation
        self.popup.dismiss()
class StartPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)

        self.rows = 10
        self.message = Label(halign="center",font_size=40)


        # Add text widget to the layout
        self.add_widget(self.message)
        self.message.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        self.message.text = App.get_running_app().config.get("halle", "welcome")
        
        #Spieltag wählen
        self.existing_day = Button(text="Spieltag wählen",font_size=40)
        self.add_widget(self.existing_day)
        
        #neuen Spieltag erstellen
        create_row = BoxLayout(spacing=8)
        self.new_day = Button(text="Spieltag erstellen", font_size=29)
        self.quick_day = Button(text="Schnelles Spiel", font_size=29)
        self.quick_day.bind(on_release=self.open_quick_game)
        create_row.add_widget(self.new_day)
        create_row.add_widget(self.quick_day)
        self.add_widget(create_row)

        #spieltage online laden
        self.update_days = Button(text="Spieltage online aktualisieren",font_size=40)#,id="up_da")
        self.add_widget(self.update_days)
        self.portal_days = Button(text="Spieltage vom Portal laden", font_size=40)
        self.add_widget(self.portal_days)
        self.portal_status = Label(text="", size_hint_y=.27, font_size=24)
        self.add_widget(self.portal_status)

        self.bind_buttons()
		
        
	
	
        # By default every widget returns it's side as [100, 100], it gets finally resized,
        # but we have to listen for size change to get a new one
        # more: https://github.com/kivy/kivy/issues/1044
        self.message.bind(width=self.update_text_width)
        self.pb=ProgressBar()
        self.add_widget(self.pb)
        self.requests = {}
    def bind_buttons(self):
        self.existing_day.bind(on_release=self.existing_button)
        self.new_day.bind(on_release=self.new_button)
        self.update_days.bind(on_release=self.update_button)
        self.update_days.unbind(on_release=self.create_popup)
        self.portal_days.unbind(on_release=self.create_popup)
        self.portal_days.bind(on_release=self.update_button)
        self.update_days.disabled = self.portal_days.disabled = False
    def unbind_buttons(self):
        self.existing_day.unbind(on_release=self.existing_button)
        self.new_day.unbind(on_release=self.new_button)
        self.update_days.unbind(on_release=self.update_button)
        self.portal_days.unbind(on_release=self.update_button)
        self.active_import.bind(on_release=self.create_popup)
        inactive = self.portal_days if self.active_import is self.update_days else self.update_days
        inactive.disabled = True
    def existing_button(self, instance):
        rad_app.selector_page.update_info()
        rad_app.screen_manager.current = 'Selector'
    def new_button(self, instance):

        build_known_teams()  # <-- Aufruf
        rad_app.temp_matchday_data = {}
        # Dann auf Seite 1 springen
        rad_app.screen_manager.current = "NewGameStep1"
           
    def open_quick_game(self, instance):
        if self.requests:
            return
        content = BoxLayout(orientation="vertical", padding=14, spacing=8)
        home = TextInput(hint_text="Heimmannschaft", multiline=False, font_size=27)
        away = TextInput(hint_text="Gastmannschaft", multiline=False, font_size=27)
        message = Label(text="", font_size=22)
        actions = BoxLayout(spacing=8)
        cancel = Button(text="Abbrechen", font_size=24)
        play = Button(text="Spielen", font_size=24)
        for widget in (home, away, message, actions):
            content.add_widget(widget)
        actions.add_widget(cancel)
        actions.add_widget(play)
        popup = Popup(title="Schnelles Spiel", content=content, size_hint=(.9, .65))
        cancel.bind(on_release=popup.dismiss)

        def play_local(*_):
            try:
                plan = quick_game_plan(home.text, away.text)
            except ValueError as error:
                message.text = str(error)
                return
            popup.dismiss()
            rad_app.game_page.load_GamePage(plan, [0], "Schnelles Spiel", 0, "quick")

        play.bind(on_release=play_local)
        popup.open()

    def update_button(self, instance):
        self.update_all(instance)

        # Called on label width update, so we can set text width properly - to 90% of label width
    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)
    def create_popup(self,instance):
        
        layout=GridLayout(cols=1, rows=3, padding = (50, 50, 50, 50))
        layout.add_widget(Label(text="Wollen Sie wirklich das Update abbrechen?", halign="center",font_size=40))
        cancel = Button(text='abbrechen',font_size=40)
        go_on = Button(text='nicht abbrechen',font_size=40)
        layout.add_widget(cancel)
        layout.add_widget(go_on)
        popup = Popup(title='cancel',content=layout, auto_dismiss=False)
        go_on.bind(on_release=popup.dismiss)
        cancel.bind(on_release=popup.dismiss)
        cancel.bind(on_release=self.cancel)
        popup.open()
    def cancel(self, instance):
        for request in self.requests:
            request.cancel()
        self.requests.clear()
        self.pending.clear()
        self.finish_update("Update abgebrochen")

    def update_all(self, button):
        self.active_import = button
        if button is self.portal_days:
            self.pending = deque([(PORTAL_NAME, CATALOG)])
        else:
            self.pending = deque((region, "/leagues") for region in FEEDS)
            self.pending.append((PORTAL_NAME, CATALOG))
        self.failed_regions = set()
        self.completed_requests = 0
        self.imported_days = 0
        self.pb.value = 0
        self.unbind_buttons()
        self.next_request()

    def next_request(self):
        while self.pending and len(self.requests) < 4:
            region, route = self.pending.popleft()
            self.active_import.text = f"Lade {region} ..."
            origin = PORTAL_URL if region == PORTAL_NAME else FEEDS[region]
            request = UrlRequest(
                origin + route,
                on_success=self.import_response,
                on_failure=self.import_failure,
                on_error=self.import_failure,
                on_redirect=self.import_failure,
                req_headers={"Accept": "application/json"},
                ca_file=certifi.where(),
                timeout=10,
            )
            self.requests[request] = (region, route)
        if self.requests:
            return
        if self.failed_regions:
            failed = ", ".join(sorted(self.failed_regions))
            status = f"{self.imported_days} geladen, Fehler: {failed}"
        else:
            status = f"{self.imported_days} Spieltage aktualisiert"
        self.finish_update(status)

    def import_response(self, request, result):
        if request not in self.requests:
            return
        region, route = self.requests[request]
        try:
            if region == PORTAL_NAME:
                if route == CATALOG:
                    self.pending.extend((region, job) for job in portal_jobs(result))
                else:
                    self.imported_days += cache_portal_plan(app_folder, route, result)
            elif "/matchdays/" in route:
                save_matchday(app_folder, region, result)
                self.imported_days += 1
            else:
                self.pending.extend((region, job) for job in import_jobs(route, result))
        except (AttributeError, KeyError, OSError, TypeError, ValueError) as error:
            self.import_failure(request, error)
            return
        self.advance_update(request)

    def import_failure(self, request, error):
        if request not in self.requests:
            return
        region, _ = self.requests[request]
        print(f"Spieltag-Import {region}: {request.url}: {error}"[:250])
        self.failed_regions.add(region)
        self.advance_update(request)

    def advance_update(self, request):
        del self.requests[request]
        self.completed_requests += 1
        self.pb.max = self.completed_requests + len(self.pending) + len(self.requests)
        self.pb.value = self.completed_requests
        self.next_request()

    def finish_update(self, status):
        self.active_import.text = status
        self.bind_buttons()


class AutoCompleteTextInput(TextInput):
    """
    Sehr einfaches Autocomplete für Teamnamen:
    - Zeigt ein DropDown mit Vorschlägen aus KNOWN_TEAMS an, 
      die den bisher eingegebenen Text enthalten.
    - Klick auf Vorschlag -> TextInput wird damit gefüllt.
    
    Für ein vollwertiges Autocomplete bräuchte man ggf. mehr Logik
    (z.B. Eingaben wie "schw" -> "Schwaikheim 1" finden).
    """
    # Liste der Vorschläge
    suggestions = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dropdown = DropDown()
        self.bind(text=self.on_text)  # Bei Texteingabe Vorschläge aktualisieren
    
    def on_text(self, instance, value):
        # Dropdown zurücksetzen
        self.dropdown.dismiss()
        self.dropdown.clear_widgets()
        # Neue Vorschläge filtern
        self.suggestions = [team for team in KNOWN_TEAMS if value.lower() in team.lower()]

        # Bei leerer Eingabe nix anzeigen
        if not self.text.strip():
            return

        # Dropdown füllen
        for team_name in self.suggestions[:5]:  # max. 5 Vorschläge
            btn = Button(text=team_name, size_hint_y=None, height=40)
            btn.bind(on_release=lambda btn: self.select_autocomplete(btn.text))
            self.dropdown.add_widget(btn)

        # Dropdown öffnen, wenn Vorschläge vorhanden
        if self.suggestions:
            self.dropdown.open(self)

    def select_autocomplete(self, text):
        # Wenn Vorschlag geklickt -> in TextInput übernehmen und Dropdown schließen
        self.text = text
        self.dropdown.dismiss()



###############################################################################
# SCREEN 1: Allgemeine Spieltags-Infos
###############################################################################
class NewGameStep1Screen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # links, oben, rechts, unten = 50 px Abstand
        
        layout = GridLayout(cols=1, spacing=10, padding=50)

        self.headerLayout = GridLayout(cols=2, size_hint=(1, 0.15))
        self.backButton = Button(text="Zurück", font_size=32)
        self.backButton.bind(on_release=self.go_back)
        self.headerLayout.add_widget(self.backButton)
        self.nextButton = Button(text="Weiter", font_size=32)
        self.nextButton.bind(on_release=self.go_next)
        self.headerLayout.add_widget(self.nextButton)
        layout.add_widget(self.headerLayout, index=0)

        self.add_widget(layout)

        layout.add_widget(Label(text="Neuen Spieltag erstellen (1/3)", font_size=50, size_hint=(1, 0.1)))

        # Grid für Eingaben
        input_grid = GridLayout(cols=2, size_hint=(1, 0.7))
        layout.add_widget(input_grid)

         # leagueLongName
        input_grid.add_widget(Label(text="Turniername:", font_size=40))
        self.leagueLongNameInput = TextInput(font_size=40, multiline=False)
        input_grid.add_widget(self.leagueLongNameInput)

        # HostClub
        input_grid.add_widget(Label(text="Veranstalter:", font_size=40))
        self.hostClubInput = TextInput(font_size=40, multiline=False)
        input_grid.add_widget(self.hostClubInput)

        # Datum-Label + Button für DatePicker
        input_grid.add_widget(Label(text="Datum wählen:", font_size=40))
        self.dateButton = Button(text="Datum wählen...", font_size=40)
        self.dateButton.bind(on_release=self.open_date_picker)
        input_grid.add_widget(self.dateButton)


        self.picked_date = datetime.date.today()

    def on_pre_enter(self, *args):
        # Falls bei "Zurück" und Wiederkehr vorhandene Daten gefüllt werden sollen,
        # könnte man hier 'rad_app.temp_matchday_data' lesen.
        pass

    def open_date_picker(self, instance):
        """
        Sehr einfacher DatePicker (Popup mit 3 Spinners: Jahr, Monat, Tag).
        """
        popup_layout = GridLayout(cols=2, spacing=5, padding=10)
        self.padding = (50, 50, 50, 50)
        # Spinner für Jahr
        years = [str(y) for y in range(2023, 2035)]
        self.yearSpinner = Spinner(text=str(self.picked_date.year), values=years, font_size=30, option_cls=MySpinnerOption)

        # Spinner für Monat
        months = [str(m) for m in range(1, 13)]
        self.monthSpinner = Spinner(text=str(self.picked_date.month), values=months, font_size=30, option_cls=MySpinnerOption)

        # Spinner für Tag
        days = [str(d) for d in range(1, 32)]
        self.daySpinner = Spinner(text=str(self.picked_date.day), values=days, font_size=30, option_cls=MySpinnerOption)

        popup_layout.add_widget(Label(text="Jahr:", font_size=30))
        popup_layout.add_widget(self.yearSpinner)
        popup_layout.add_widget(Label(text="Monat:", font_size=30))
        popup_layout.add_widget(self.monthSpinner)
        popup_layout.add_widget(Label(text="Tag:", font_size=30))
        popup_layout.add_widget(self.daySpinner)

        ok_btn = Button(text="OK", font_size=30)
        cancel_btn = Button(text="Abbrechen", font_size=30)
        popup_layout.add_widget(ok_btn)
        popup_layout.add_widget(cancel_btn)

        popup = Popup(title="Datum wählen",
                      content=popup_layout,
                      size_hint=(None, None),
                      size=(600, 400),
                      auto_dismiss=False)

        def on_ok(btn):
            yy = int(self.yearSpinner.text)
            mm = int(self.monthSpinner.text)
            dd = int(self.daySpinner.text)
            try:
                self.picked_date = datetime.date(yy, mm, dd)
                self.dateButton.text = self.picked_date.strftime("%Y-%m-%d")
            except ValueError:
                self.picked_date = datetime.date.today()
                self.dateButton.text = "Fehlerhaft, neu wählen"
            popup.dismiss()

        def on_cancel(btn):
            popup.dismiss()

        ok_btn.bind(on_release=on_ok)
        cancel_btn.bind(on_release=on_cancel)
        popup.open()

    def go_next(self, instance):
        # Überprüfe, ob der leagueLongName eingegeben wurde
        if not self.leagueLongNameInput.text.strip():
            popup = Popup(
                title="Fehlende Eingabe",
                content=Label(text="Bitte fülle den Turniernamen aus.",font_size=30),
                size_hint=(0.5, 0.5)
            )
            popup.open()
            return

        data = rad_app.temp_matchday_data
        data["leagueShortName"] = "own"
        data["leagueLongName"]  = self.leagueLongNameInput.text.strip()
        data["hostClub"]        = self.hostClubInput.text.strip()

        # Automatisch ermittelte Spieltagsnummer (siehe vorherige Anpassung)
        data["number"] = get_new_matchday_number(data["leagueShortName"])

        # Datum:
        dt_str = self.picked_date.strftime("%Y-%m-%dT00:00:00.000Z")
        data["start"] = dt_str

        # Gym-Daten (können noch leer bleiben)
        data["gym"] = {
            "name":   "",
            "street": "",
            "zip":    "",
            "city":   "",
            "phone":  ""
        }

        rad_app.screen_manager.current = "NewGameStep2"



    def go_back(self, instance):
    # zurück zur Screen "NewGameStep1"
        rad_app.screen_manager.current = "Start"


###############################################################################
# SCREEN 2: Teams eingeben
###############################################################################

class NewGameStep2Screen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)

        layout = GridLayout(cols=1, spacing=10, padding=50)

        self.headerLayout = GridLayout(cols=2, size_hint=(1, 0.15))
        self.backButton = Button(text="Zurück", font_size=32)
        self.backButton.bind(on_release=self.go_back)
        self.headerLayout.add_widget(self.backButton)
        self.nextButton = Button(text="Weiter", font_size=32)
        self.nextButton.bind(on_release=self.go_next)
        self.headerLayout.add_widget(self.nextButton)
        layout.add_widget(self.headerLayout, index=0)


        self.add_widget(layout)

        layout.add_widget(Label(text="Teams anlegen (2/3)", font_size=50, size_hint=(1, 0.1)))

        # ScrollView
        self.scroll = ScrollView(size_hint=(1, 0.7))
        layout.add_widget(self.scroll)

        self.teamsContainer = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.teamsContainer.bind(minimum_height=self.teamsContainer.setter("height"))
        self.scroll.add_widget(self.teamsContainer)

        # "+ Team hinzufügen"
        add_btn = Button(text="+ Team hinzufügen", font_size=40, size_hint=(1, 0.1))
        add_btn.bind(on_release=self.add_team_row)
        layout.add_widget(add_btn)


    def add_team_row(self, *args):
        """
        Zeile: Spinner links, TextInput rechts, "X"-Button zum Entfernen.
        Ausgewähltes Spinner-Item -> ins TextInput.
        """
        row = GridLayout(cols=3, size_hint_y=None, height=60)

        # Spinner mit bekannten Teams:
        spinner = Spinner(
            text="Team auswählen...",
            values=KNOWN_TEAMS,  # jetzt wirklich die globale Liste
            font_size=30,
            size_hint=(0.3, None),
            height=60,
            option_cls=MySpinnerOption
        )
        # TextInput
        txt = TextInput(font_size=30, multiline=False, size_hint_x=0.6)

        # "X"-Button
        remove_btn = Button(text="X", font_size=30, size_hint_x=0.1)

        def on_spinner_text(spin, new_value):
            print("Spinner gewählt:", new_value)
            txt.text = new_value

        spinner.bind(text=on_spinner_text)

        def on_remove(btn):
            self.teamsContainer.remove_widget(row)

        remove_btn.bind(on_release=on_remove)

        row.add_widget(spinner)
        row.add_widget(txt)
        row.add_widget(remove_btn)

        self.teamsContainer.add_widget(row)

    def go_next(self, instance):
        """
        Liest alle Textfelder aus und speichert sie in temp_matchday_data["teams"].
        Danach weiter zu Schritt 3.
        """
        data = rad_app.temp_matchday_data
        data["teams"] = []  # neu anlegen

        # reversed, weil neue rows ganz oben in .children landen
        for row in reversed(self.teamsContainer.children):
            text_input = None
            for child in row.children:
                if isinstance(child, TextInput):
                    text_input = child
                    break

            if text_input:
                tname = text_input.text.strip()
                if tname:
                    # Team eintragen
                    data["teams"].append({
                        "name": tname,
                        "present": True,
                        "players": []
                    })

        names = [team["name"].casefold() for team in data["teams"]]
        if len(names) < 2 or len(names) != len(set(names)):
            rad_app.textpopup(title="Mannschaften prüfen", text="Gib mindestens zwei unterschiedliche Mannschaftsnamen ein.")
            return

        # Weiter zu Schritt 3
        rad_app.screen_manager.current = "NewGameStep3"

    def go_back(self, instance):
    # zurück zur Screen "NewGameStep2"
        rad_app.screen_manager.current = "NewGameStep1"


###############################################################################
# SCREEN 3: Spiele definieren
###############################################################################

class NewGameStep3Screen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # links, oben, rechts, unten = 50 px Abstand
        self.padding = (50, 50, 50, 50)

        layout = GridLayout(cols=1, spacing=10, padding=50)
        self.headerLayout = GridLayout(cols=2, size_hint=(1, 0.15))
        self.backButton = Button(text="Zurück", font_size=32)
        self.backButton.bind(on_release=self.go_back)
        self.headerLayout.add_widget(self.backButton)
        self.saveButton = Button(text="Speichern", font_size=32)
        self.saveButton.bind(on_release=self.save_matchday)
        self.headerLayout.add_widget(self.saveButton)
        layout.add_widget(self.headerLayout, index=0)


        self.add_widget(layout)

        layout.add_widget(Label(text="Spiele anlegen (3/3)", font_size=50, size_hint=(1, 0.1)))

        # ScrollView für Game-Eingaben
        self.scroll = ScrollView(size_hint=(1, 0.7))
        layout.add_widget(self.scroll)

        self.gamesContainer = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.gamesContainer.bind(minimum_height=self.gamesContainer.setter("height"))
        self.scroll.add_widget(self.gamesContainer)

        # "+ Spiel hinzufügen"
        add_game_btn = Button(text="+ Spiel hinzufügen", font_size=40, size_hint=(1, 0.1))
        add_game_btn.bind(on_release=self.add_game_row)
        layout.add_widget(add_game_btn)


        self.available_teams = []

    def on_pre_enter(self, *args):
        """
        Kurz bevor die Seite sichtbar wird: Teams aus temp_matchday_data holen
        und in self.available_teams packen.
        """
        data = rad_app.temp_matchday_data
        if "teams" in data:
            self.available_teams = [t["name"] for t in data["teams"]]
        else:
            self.available_teams = []
        # Optional: self.gamesContainer.clear_widgets() falls man neu aufbaut

    def add_game_row(self, *args):
        """
        Zeile: SpinnerA, SpinnerB, "X"
        """
        row = GridLayout(cols=3, size_hint_y=None, height=60)

        spinnerA = Spinner(text="Team A wählen", values=self.available_teams, font_size=30, option_cls=MySpinnerOption)
        spinnerB = Spinner(text="Team B wählen", values=self.available_teams, font_size=30, option_cls=MySpinnerOption)
        remove_btn = Button(text="X", font_size=30, size_hint_x=None, width=60)

        def on_remove(btn):
            self.gamesContainer.remove_widget(row)

        remove_btn.bind(on_release=on_remove)

        row.add_widget(spinnerA)
        row.add_widget(spinnerB)
        row.add_widget(remove_btn)
        self.gamesContainer.add_widget(row)

    def save_matchday(self, instance):
        """
        Liest alle Games aus, speichert sie in temp_matchday_data, schreibt das JSON.
        """
        data = rad_app.temp_matchday_data

        games = []
        game_counter = 1
        for row in reversed(self.gamesContainer.children):
            spinners = [c for c in row.children if isinstance(c, Spinner)]
            if len(spinners) == 2:
                # spinnerA = spinners[1], spinnerB = spinners[0] in umgekehrter Reihenfolge
                teamA = spinners[1].text
                teamB = spinners[0].text

                # Nur gültige Paarungen übernehmen
                if teamA not in ("Team A wählen", "") and teamB not in ("Team B wählen", "") and teamA != teamB:
                    games.append({
                        "number": game_counter,
                        "teamA": teamA,
                        "teamB": teamB,
                        "goalsA": 0,
                        "goalsB": 0,
                        "state": "Open"
                    })
                    game_counter += 1

        if not games:
            rad_app.textpopup(title="Keine gültige Paarung", text="Lege mindestens ein Spiel mit zwei unterschiedlichen Mannschaften an.")
            return
        data["games"] = games
        data["incidents"] = []

        # Fallbacks
        if "leagueShortName" not in data:
            data["leagueShortName"] = "UNDEF"
        if "number" not in data:
            data["number"] = 1

        # Datei speichern
        eigene_folder = os.path.join(app_folder, "spieltage", "eigene")
        if not os.path.exists(eigene_folder):
            os.makedirs(eigene_folder)

        filename = f"{data['leagueShortName']}_{data['number']}.radball"
        save_path = os.path.join(eigene_folder, filename)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"[INFO] Neuer Spieltag gespeichert unter {save_path}")
        # Zurück zur Start-Seite
        rad_app.screen_manager.current = "Start"
    def go_back(self, instance):
    # zurück zur Screen "NewGameStep2"
        rad_app.screen_manager.current = "NewGameStep2"


class EpicApp(App):
    def get_application_config(self, defaultpath=None):
        if platform == "android":
            return super().get_application_config()
        return os.path.join(self.user_data_dir, "radball.ini")


    def build_config(self, config):
        config.setdefaults("halle", {"welcome": "Willkommen zur Radballanzeige", "controller": "", "displays": "{}"})

    service = ""
    def on_request_close(self, *args):
        if getattr(self, "back_popup", None) is not None:
            return True
        current = self.screen_manager.current
        exiting = current == "Start"
        layout = BoxLayout(orientation="vertical", padding=12, spacing=8)
        layout.add_widget(Label(text="App beenden?" if exiting else "Zum Hauptmenü zurück?", font_size=29))
        buttons = BoxLayout(spacing=8)
        cancel = Button(text="Abbrechen", font_size=26)
        confirm = Button(text="Beenden" if exiting else "Hauptmenü", font_size=26)
        buttons.add_widget(cancel)
        buttons.add_widget(confirm)
        layout.add_widget(buttons)
        popup = Popup(title="Zurück", content=layout, size_hint=(.85, .45), auto_dismiss=False)
        self.back_popup = popup
        popup.bind(on_dismiss=lambda *_: setattr(self, "back_popup", None))
        cancel.bind(on_release=popup.dismiss)

        def accept(*_):
            popup.dismiss()
            if exiting:
                self.close_app()
            elif current == "Game":
                self.game_page.leave_game_screen()
            else:
                self.screen_manager.current = "Start"

        confirm.bind(on_release=accept)
        popup.open()
        return True

    def close_app(self, *args):
        if platform == 'android':
            self.bgservice.stop(mActivity)
        self.stop()
        return True
    def textpopup(self, title='', text=''):
        """Open the pop-up with the name.

        :param title: title of the pop-up to open
        :type title: str
        :param text: main text of the pop-up to open
        :type text: str
        :rtype: None
        """
        box = BoxLayout(orientation='vertical')
        box.add_widget(Label(text=text,font_size=30))
        mybutton = Button(text='OK', size_hint=(1, 0.25), font_size=30)
        box.add_widget(mybutton)
        popup = Popup(title=title, content=box, size_hint=(None, None), size=(600, 300),padding = (50, 50, 50, 50))
        mybutton.bind(on_release=popup.dismiss)
        popup.open()
    
    def on_key(self, window, key, *args):
        if key == 27:  # the esc key
            return self.on_request_close()
    
    def start_service(self, name):    
        context =  mActivity.getApplicationContext()
        service_name = str(context.getPackageName()) + '.Service' + "Radball"
        service = autoclass(service_name)
        service.start(mActivity,'')   # starts or re-initializes a service
        return service


    def show_portal_status(self):
        if self.portal_queue.storage_error:
            self.start_page.portal_status.text = "Ergebnisspeicher prüfen · Lokales Spiel verfügbar"
            return
        pending, sent, conflicts = self.portal_queue.overview()
        if pending or sent or conflicts:
            self.start_page.portal_status.text = (
                f"Portal: {pending} offen · {sent} gesendet · {conflicts} prüfen"
            )

    def upload_portal_results(self, dt):
        if self.portal_upload is not None:
            return
        row = self.portal_queue.next_result()
        if row is None:
            return
        key, entry, token = row
        request_id = entry["body"]["request_id"]
        self.portal_upload = UrlRequest(
            f"{PORTAL_URL}/api/v1/games/{key}/result",
            req_body=json.dumps(entry["body"]),
            req_headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            on_success=lambda req, data: self.portal_uploaded(key, request_id, data),
            on_failure=lambda req, data: self.portal_rejected(req, key, entry["scope"], request_id, token),
            on_error=self.portal_retry, on_redirect=self.portal_retry, timeout=5,
        )

    def portal_uploaded(self, key, request_id, data):
        self.portal_upload = None
        try:
            if isinstance(data, dict) and type(data.get("revision")) is int:
                self.portal_queue.mark(key, "sent", request_id)
        except OSError:
            pass
        self.show_portal_status()

    def portal_rejected(self, request, key, scope, request_id, token):
        self.portal_upload = None
        try:
            if request.resp_status == 403:
                self.portal_queue.fail_authorization(scope, token)
            elif request.resp_status in (400, 404, 409):
                self.portal_queue.mark(key, "conflict", request_id)
        except OSError:
            pass
        self.show_portal_status()

    def portal_retry(self, request, error):
        self.portal_upload = None

    def upload_portal_live_status(self, dt):
        if self.portal_live_request is not None or self.screen_manager.current != "Game":
            return
        page = self.game_page
        if page.land not in PORTAL_REGIONS:
            return
        game = page.game_json["games"][page.gameNr]
        if game["state"] != "running" or "portal_revision" not in game:
            return
        scope = ResultQueue.scope(page.gameId, page.game_json["portal_court"])
        token = self.portal_queue.token(scope)
        if not token:
            return
        score = page.nav_score()
        running = page.gameStatus == 1
        remaining = page.timeLeft
        if running:
            remaining -= datetime.datetime.now() - page.startTime
        self.portal_live_seq = max(time.time_ns(), self.portal_live_seq + 1)
        self.portal_live_request = UrlRequest(
            f"{PORTAL_URL}/api/v1/games/{game['portal_game_id']}/live-status",
            req_body=json.dumps({
                "revision": game["portal_revision"], "seq": self.portal_live_seq,
                "home_goals": score["goalsA"], "away_goals": score["goalsB"],
                "remaining_ms": max(0, min(7_200_000, int(remaining.total_seconds() * 1000))),
                "running": running,
            }),
            req_headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            on_success=self.portal_live_done,
            on_failure=lambda req, data: self.portal_live_rejected(req, data, scope, token),
            on_error=self.portal_live_done, on_redirect=self.portal_live_done, timeout=3,
        )

    def portal_live_rejected(self, request, result, scope, token):
        self.portal_live_done(request, result)
        if request.resp_status == 403:
            try:
                self.portal_queue.fail_authorization(scope, token)
            except OSError:
                pass

    def portal_live_done(self, request, result):
        self.portal_live_request = None

    def build(self):
        controller = self.config.get("halle", "controller")
        if not controller:
            controller = uuid4().hex
            self.config.set("halle", "controller", controller)
            self.config.write()
        try:
            choices = json.loads(self.config.get("halle", "displays"))
        except ValueError:
            choices = {}
        self.displays = Displays(controller, choices if isinstance(choices, dict) else {})
        if platform == 'android':
            self.bgservice = self.start_service('Radball') # starts a service

            
        
        # We are going to use screen manager, so we can add multiple screens
        # and switch between them
        self.screen_manager = ScreenManager()

        # Initial, connection screen (we use passed in name to activate screen)
        # First create a page, then a new screen, add page to screen and screen to screen manager
        self.start_page = StartPage()
        screen = Screen(name='Start')
        screen.add_widget(self.start_page)
        self.screen_manager.add_widget(screen)
        
        # Leage selector page
        self.selector_page = SelectorPage()
        screen = Screen(name='Selector')
        screen.add_widget(self.selector_page)
        self.screen_manager.add_widget(screen)

        self.pin_page = PinPage()
        screen = Screen(name='Pin')
        screen.add_widget(self.pin_page)
        self.screen_manager.add_widget(screen)
        
        
        self.present_page = PresentPage()
        screen = Screen(name='Present')
        screen.add_widget(self.present_page)
        self.screen_manager.add_widget(screen)
        
        self.sequence_page = SequencePage()
        screen = Screen(name='Sequence')
        screen.add_widget(self.sequence_page)
        self.screen_manager.add_widget(screen)
        
        self.game_page = GamePage()
        screen = Screen(name='Game')
        screen.add_widget(self.game_page)
        self.screen_manager.add_widget(screen)
        
        self.temp_matchday_data = {}

        # Schritt-1-Screen
        new_game_step1 = NewGameStep1Screen(name="NewGameStep1")
        self.screen_manager.add_widget(new_game_step1)

        # Schritt-2-Screen
        new_game_step2 = NewGameStep2Screen(name="NewGameStep2")
        self.screen_manager.add_widget(new_game_step2)

        # Schritt-3-Screen
        new_game_step3 = NewGameStep3Screen(name="NewGameStep3")
        self.screen_manager.add_widget(new_game_step3)

        


        Window.bind(on_request_close=self.on_request_close)
        Window.bind(on_keyboard=self.on_key)
        Window.update_viewport()

        if platform == 'android':
            orientation.set_sensor(mode='any')

        
        # 1) In build() oder on_start(), sobald dein ScreenManager fertig ist:

        # 2) Neue Methode in EpicApp (nur das hier ist neu!):
        

        
        self.digital_access = None
        self.digital_attempted = set()
        self.portal_queue = ResultQueue(self.user_data_dir)
        self.portal_upload = None
        self.portal_live_request = None
        self.portal_live_seq = 0
        self.show_portal_status()
        Clock.schedule_interval(self.upload_portal_results, 5)
        Clock.schedule_interval(self.upload_portal_live_status, 2)
        return self.screen_manager
    
		

if __name__ == "__main__":
    rad_app = EpicApp()
    app_folder = (os.path.dirname(os.path.abspath(__file__)) if platform == "android"
                  else rad_app.user_data_dir)
    if not os.path.exists(app_folder+"/spieltage"):
        os.makedirs(app_folder+"/spieltage")
    rad_app.run()
