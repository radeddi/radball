debug=False

__version__ = "0.0.3"

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
import urllib.parse

import datetime
from datetime import timedelta
from functools import partial

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




broadcast = False
client_ip = []


if broadcast:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
else:
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    
    UDP_IP = ""
    UDP_PORT = 5006
    sock2 = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock2.settimeout(0.05)
    sock2.bind((UDP_IP, UDP_PORT))
#sock.bind(("", 5556))
#sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)



kivy.require("1.10.1")




server_urls = {
"Baden Württemberg": "https://bw.cycleball.eu/api",
"Bayern": "https://by.cycleball.eu/api",
"Deutschland": "https://de.cycleball.eu/api",
"Brandenburg": "https://bb.cycleball.eu/api",
"Schweiz": "https://rmva.groff.de/api"
}

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
            if not datei.endswith(".radball"):
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
        rad_app.pin_page.load_PinPage(self.land,self.gameId,self.league_short)
        
        # Called with a message, to update message text in widget
    def update_info(self):
        print("*********************************")
        self.dropdownLand.clear_widgets()
        landliste = sorted(os.listdir(app_folder+"/spieltage/"))
        for land in landliste:
          print(land)
          if os.path.isdir(app_folder+"/spieltage/"+land):
            btn = Button(text=land, size_hint_y=None, height=80,font_size=40)
            btn.bind(on_release=lambda btn,land=land: self.update_leagues(btn,land))
            self.dropdownLand.add_widget(btn)
        
    def update_leagues(self, btn, land):
        self.land = land
        self.dropdownLand.select(btn.text)
        dateiliste=sorted(os.listdir(app_folder+"/spieltage/"+land))
        self.spieltage=dict()
        self.leagues=dict()
        for datei in dateiliste:
            f=open(app_folder+"/spieltage/"+land+"/"+datei,"r",encoding='utf-8')
            game_json=(json.loads(f.read()))
            self.spieltage[datei]=game_json
            print(game_json)
            print(type(game_json))
            if game_json['leagueLongName'] in self.leagues.keys():
               self.leagues[game_json['leagueLongName']].append(game_json)
            else:
                self.leagues[game_json['leagueLongName']]=[game_json]
        for key in self.leagues.keys():
            print(key)
        self.dropdownLeague.clear_widgets()

        for index in sorted(self.leagues.keys()):
            # When adding widgets, we need to specify the height manually
            # (disabling the size_hint_y) so the dropdown can calculate
            # the area it needs.

            btn = Button(text=self.leagues[index][0]["leagueLongName"], size_hint_y=None, height=80,font_size=40)

            # for each button, attach a callback that will call the select() method
            # on the dropdown. We'll pass the text of the button as the data of the
            # selection.
            #btn.bind(on_release=lambda btn: self.dropdownLeague.select(btn.text))
            btn.bind(on_release=lambda btn,index=index: self.dropdownLeagueAction(btn,index))

            # then add the button inside the dropdown
            self.dropdownLeague.add_widget(btn)
    def dropdownLeagueAction(self, btn,index):
        self.dropdownLeague.select(btn.text)
        self.createdropdownDay(index)
    def createdropdownDay(self,index):
        self.dropdownDay.clear_widgets()
        self.dropdownDay.select("Spieltag auswählen")
        self.labelCity.text=""
        self.furtherButton.disabled=True
        print(index)
        for liga in self.leagues.keys():
            if liga == index:
                print(type(self.leagues[liga]))
                btnList=[]
                
                for spieltag in self.leagues[liga]:
                    date = spieltag["start"][8:10]+"."+spieltag["start"][5:7]+"."+spieltag["start"][0:4]
                    city = spieltag["gym"]["city"]
                     
                    btnList.append([Button(text="Spieltag "+str(spieltag["number"])+"\n"+date, size_hint_y=None, height=100,font_size=40),spieltag["number"],spieltag["number"],city])
                    
                for btnL in sorted(btnList, key=lambda tup: tup[1]):  
                    btn=btnL[0]
                    #btn.bind(on_release=lambda btn: self.dropdownDay.select(btn.text))
                    btn.bind(on_release=lambda btn,btnL=btnL: self.dropdownDayAction(btn,btnL[2],btnL[3],spieltag["leagueShortName"]))
                    self.dropdownDay.add_widget(btn)    
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
        self.textinput = TextInput(input_filter="int",size_hint = (1, 0.15),font_size=40)
        self.add_widget(self.textinput)
        self.lb = Label(text='Spieltags Pin',size_hint = (1, 0.15),font_size=40)
        self.add_widget(self.lb)
        self.placeholder = Label(size_hint = (1, 0.55),font_size=40)
        self.add_widget(self.placeholder)
        rad_app.screen_manager.current = 'Pin'
    def goBack(self,instance):
        rad_app.screen_manager.current = 'Selector'
        print("going back")
    def goFurther(self,instance):
        rad_app.present_page.load_PresentPage(self.land,self.gameId,self.league_short,(self.textinput.text))
        print("go on")   

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
        rad_app.screen_manager.current = 'Pin'
        print("going back")
    def goFurther(self,instance):
        print(self.game_json)
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
        self.fourthLine = GridLayout(cols=3,size_hint = (1, 0.2))
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
        self.fourthLine.add_widget(self.settingsButton)
        
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


    def load_GamePage(self,game_json,sequence,land,game_id,league_short):
        Clock.schedule_interval(self.refreshTime, 0.1)
        Clock.schedule_interval(self.findClients, 1)
        print(sequence)
        self.sequence = sequence
        self.game_json = game_json
        self.land=land
        self.gameId=game_id
        self.league_short = league_short
        rad_app.screen_manager.current = 'Game'
        if sequence == []:
            rad_app.screen_manager.current = 'Present'
        else:
            if platform == "android":
                orientation.set_sensor(mode='landscape')
                Window.allow_screensaver = False
            self.gameNr=self.sequence[0]
            self.load_Game()
    def load_Game (self):
        print(self.gameNr)
        self.timeLeft = self.playingTime
        self.teamALabel.text=self.game_json["games"][self.gameNr]["teamA"]
        self.teamBLabel.text=self.game_json["games"][self.gameNr]["teamB"]
        
        self.htLabel.text="1. Halbzeit"
        
        if "score" in self.game_json["games"][self.gameNr]:
            if "goalsA" and "goalsB" in self.game_json["games"][self.gameNr]["score"]:
                self.goalALabel.text= str(self.game_json["games"][self.gameNr]["score"]["goalsA"])
                self.goalBLabel.text= str(self.game_json["games"][self.gameNr]["score"]["goalsB"])
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
    
    def nextGame (self,instance):
        score = {}
        if self.game_json["games"][self.gameNr]["teamA"] == self.teamALabel.text:
            score["bothLost"]=False
            score["goalsA"]=int(self.goalALabel.text)
            score["goalsB"]=int(self.goalBLabel.text)
            self.game_json["games"][self.gameNr]["score"]=score
        elif self.teamBLabel.text == self.game_json["games"][self.gameNr]["teamA"]:
            score["bothLost"]=False
            score["goalsA"]=int(self.goalBLabel.text)
            score["goalsB"]=int(self.goalALabel.text)
            self.game_json["games"][self.gameNr]["score"]=score
            
        else: 
            print("there is a big error")
        if self.game_json["games"][self.gameNr]["state"]=="running":
            self.game_json["games"][self.gameNr]["state"]="finished"
        Clock.schedule_once(self.sendUpdate,1)
        self.gameNr = self.sequence [self.sequence.index(self.gameNr) +1]
        self.load_Game()
    def lastGame (self,instance):        
        score = {}
        if self.game_json["games"][self.gameNr]["teamA"] == self.teamALabel.text:
            score["bothLost"]=False
            score["goalsA"]=int(self.goalALabel.text)
            score["goalsB"]=int(self.goalBLabel.text)
            self.game_json["games"][self.gameNr]["score"]=score
        elif self.teamBLabel.text == self.game_json["games"][self.gameNr]["teamA"]:
            score["bothLost"]=False
            score["goalsA"]=int(self.goalBLabel.text)
            score["goalsB"]=int(self.goalALabel.text)
            self.game_json["games"][self.gameNr]["score"]=score
            
        else: 
            print("there is a big error")
        self.gameNr = self.sequence [self.sequence.index(self.gameNr) - 1]
        self.load_Game()     
    def quitGames(self,instance):
        score = {}
        if self.game_json["games"][self.gameNr]["teamA"] == self.teamALabel.text:
            score["bothLost"]=False
            score["goalsA"]=int(self.goalALabel.text)
            score["goalsB"]=int(self.goalBLabel.text)
            self.game_json["games"][self.gameNr]["score"]=score
        elif self.teamBLabel.text == self.game_json["games"][self.gameNr]["teamA"]:
            score["bothLost"]=False
            score["goalsA"]=int(self.goalBLabel.text)
            score["goalsB"]=int(self.goalALabel.text)
            self.game_json["games"][self.gameNr]["score"]=score
            
        else: 
            print("there is a big error")
        if self.game_json["games"][self.gameNr]["state"]=="running":
            self.game_json["games"][self.gameNr]["state"]="finished"
        Clock.schedule_once(self.sendUpdate,1)
        time.sleep(3)
        Window.allow_screensaver = True
        rad_app.screen_manager.current = 'Start'
        #exit()
    def findClients (self,instance):
        try:
            print("finding")
            data, addr = sock2.recvfrom(1024) # buffer size is 1024 bytes
            print("found")
            print(addr)
            if addr[0] not in client_ip:
                client_ip.append(addr[0])
                print(client_ip)
            for i in range(len(client_ip)):
               if  client_ip[i].split(":")[2]  != addr[0].split(":")[2]:
                   client_ip.remove(i)
        except Exception as e: print(e)
        
    def refreshTime (self,instance):
        
        if self.gameNr == len(self.sequence)-1 or not ((self.timeLabel.text.split(":")[0] == "0" and self.timeLabel.text.split(":")[1] == "00") or (self.timeLeft == self.playingTime and self.htLabel.text=="2. Halbzeit" and self.startStopButton.text=="Zeit starten")) :
            nextTeams = ""
            nextTeamsLocal=''
        else:
            nextTeams = f'{(self.game_json["games"][self.gameNr+1]["teamA"])} \n {(self.game_json["games"][self.gameNr+1]["teamB"])}'
            nextTeamsLocal=f'nächstes Spiel: {(self.game_json["games"][self.gameNr+1]["teamA"])} gegen {(self.game_json["games"][self.gameNr+1]["teamB"])}'
        if self.gameStatus == 0:
            remTime = self.timeLeft
            if remTime < timedelta ( minutes = 0):
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
            if remTime < timedelta ( minutes = 0):
                self.timeLabel.text = "0:00"
                self.stopGame(self)
                self.pauseButton.disabled = False
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

            
        if self.rotation:
            send_str = {
                "team1": self.teamBLabel.text,
                "team2": self.teamALabel.text,
                "tore1": self.goalBLabel.text,
                "tore2": self.goalALabel.text,
                "minutes": self.timeLabel.text.split(":")[0],
                "seconds": self.timeLabel.text.split(":")[1],
                "schnaps": 0,
                "next": nextTeams,
                "status": self.gameStatus,
                "rem": str(remTime),
                "client_ip": client_ip
                }
        else:
            send_str = {
                "team1": self.teamALabel.text,
                "team2": self.teamBLabel.text,
                "tore1": self.goalALabel.text,
                "tore2": self.goalBLabel.text,
                "minutes": self.timeLabel.text.split(":")[0],
                "seconds": self.timeLabel.text.split(":")[1],
                "schnaps": 0,
                "next": nextTeams,
                "status": self.gameStatus,
                "rem": str(remTime),
                "client_ip": client_ip
                }
        try:
            if platform == 'android' or debug:
                #add Android here
                sock.sendto((json.dumps(send_str)+"\n").encode(), ("127.0.0.1", 5066))
            else:
                if broadcast:
                    sock.sendto((json.dumps(send_str)+"\n").encode(), ("255.255.255.255", 5005))
                else:
                    #sock.sendto((json.dumps(send_str)+"\n").encode(), ("127.0.0.1", 5066))
                    for client in client_ip:
                        sock.sendto((json.dumps(send_str)+"\n").encode(), (client, 5005))
            
        except:
            pass
        #print("hello")
    
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
            
        self.rszButton.text="Restspielzeit"
        self.rszButton.unbind(on_release=self.finishRsz)  
        self.rszButton.bind(on_release=self.setRsz)  
        self.sideButton.unbind(on_release=self.resetTime)
        self.sideButton.text="Seitenwechsel"
        self.sideButton.bind(on_release=self.sideChange)
        self.startStopButton.disabled=False
        self.resetButtons()
     
    def resetTime (self,instance=None):
        t = datetime.datetime.strptime(self.sideButton.text,"%M:%S")
        self.timeLeft = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        
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
        Clock.schedule_once(self.sendUpdate,1)
    def stopGame (self,instance):
        self.startStopButton.text="Zeit starten"
        self.timeLeft= -(datetime.datetime.now() - self.startTime) + self.timeLeft
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
        
    def sideChange (self,instance=None):    
        teamA = self.teamALabel.text
        goalA = self.goalALabel.text
        self.teamALabel.text = self.teamBLabel.text
        self.teamBLabel.text = teamA
        self.goalALabel.text = self.goalBLabel.text
        self.goalBLabel.text = goalA

    def setPause (self,instance):
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
        Clock.schedule_once(self.sendUpdate,1)
    def teamAmCB (self,instance):
        if int(self.goalALabel.text) > 0 :
            self.goalALabel.text = str(int(self.goalALabel.text) - 1)
        Clock.schedule_once(self.sendUpdate,1)
    def teamBpCB (self,instance):
        self.goalBLabel.text = str(int(self.goalBLabel.text) + 1)
        Clock.schedule_once(self.sendUpdate,1)
    def teamBmCB (self,instance):        
        if int(self.goalBLabel.text) > 0 :
            self.goalBLabel.text = str(int(self.goalBLabel.text) - 1)
        Clock.schedule_once(self.sendUpdate,1)
    
    def sendUpdate (self, instance=None):
        
        if self.land in server_urls:
            url=f"{server_urls[self.land]}/leagues/{self.league_short}/matchdays/{self.gameId}"
            print (url)
            print(self.game_json)
            try:
                #r = requests.post(url, json=self.game_json, timeout=2)
                params = json.dumps(self.game_json, indent=2)

                # changed Content-type from application/x-www-form-urlencoded to application/json
                headers = {'Content-type': 'application/json','Accept': 'text/plain'}
                UrlRequest(url, req_headers=headers,req_body=params, verify=False, timeout=10)
            except:
                pass
    

    
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
        self.message.text = "Willkommen zur Radballanzeige"    
        
        #Spieltag wählen
        self.existing_day = Button(text="Spieltag wählen",font_size=40)
        self.add_widget(self.existing_day)
        
        #neuen Spieltag erstellen
        self.new_day = Button(text="neuen Spieltag erstellen",font_size=40)
        self.add_widget(self.new_day)

        #spieltage online laden
        self.update_days = Button(text="Spieltage online aktualisieren",font_size=40)#,id="up_da")
        self.add_widget(self.update_days)

        self.bind_buttons()
		
        
	
	
        # By default every widget returns it's side as [100, 100], it gets finally resized,
        # but we have to listen for size change to get a new one
        # more: https://github.com/kivy/kivy/issues/1044
        self.message.bind(width=self.update_text_width)
        self.pb=ProgressBar()
        self.add_widget(self.pb)
    def bind_buttons(self):
        self.existing_day.bind(on_release=self.existing_button)
        self.new_day.bind(on_release=self.new_button)
        self.update_days.bind(on_release=self.update_button)
        self.update_days.unbind(on_release=self.create_popup) 
    def unbind_buttons(self):
        self.existing_day.unbind(on_release=self.existing_button)
        self.new_day.unbind(on_release=self.new_button)
        self.update_days.unbind(on_release=self.update_button)
        self.update_days.bind(on_release=self.create_popup)    
    def existing_button(self, instance):
        rad_app.selector_page.update_info()
        rad_app.screen_manager.current = 'Selector'
    def new_button(self, instance):

        build_known_teams()  # <-- Aufruf
        rad_app.temp_matchday_data = {}
        # Dann auf Seite 1 springen
        rad_app.screen_manager.current = "NewGameStep1"
           
    def update_button(self, instance):
        Clock.schedule_once(self.update_all,0)
        
    def update_button_text(self,instance,text,*largs):
        
        #pass
        
        self.update_days.text=text
    def update_process(self,dt):
        if self.update_thread.isAlive():
            #print("running")
            Clock.schedule_once(self.update_process,1)
            #sock.sendto(b'This is a test', ("255.255.255.255", 6666))
        else:    
            self.update_days.text="done"
     
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
    def cancel(self,instance):
        self.run=False
    def update_all(self,instance):
        #try:
        self.clear_folder(app_folder+"/spieltage/")
        self.run=True
        self.reqList=[]
        self.waitlist=[]
        self.unbind_buttons()
        Clock.schedule_once(partial(self.update_button_text,self,"Verbinden"), -1)
        for server_url in list(server_urls.values()):
          req = UrlRequest(server_url+'/leagues', on_success=self.extract_leagues,ca_file=None, verify=False, timeout=10)#, on_failure=
        self.reqList.append(req)
        Clock.schedule_once(self.check_all_req,0.5)
    def extract_leagues(self,req,result):
        #print(req)
        Clock.schedule_once(partial(self.update_button_text,self,"Suche nach Ligen"), -1)
        
        self.list_of_urls = []
        self.leaguesList = []
        #print(result)
        for league in result:
            print(league)
            print("#############")
            self.leaguesList.append(league['longName'])
            for server_url in list(server_urls.values()):
              self.list_of_urls.append(self.escape_url(server_url+"/"+league['shortName']))
              req = UrlRequest(self.escape_url(server_url + "/leagues/"+league['shortName']+"/matchdays"), on_success=self.add_spieltag,ca_file=None, verify=False, timeout=10)#, on_failure=
              self.reqList.append(req)
        print(self.list_of_urls)
        
        
    def add_spieltag(self,req,result):
        Clock.schedule_once(partial(self.update_button_text,self,"Suche nach Spieltagen"), -1)
        if result:
          if type(result) is dict:
            leagueName = result['leagueShortName'].replace(" ","%20")
          else:  
            leagueName = result[0]['leagueShortName'].replace(" ","%20")
          print("#######")
          #print(req.get_full_url)
          print("#######")
          for day in result:
              for server_url in list(server_urls.values()):
                print(server_url)
                if server_url in req.url:
                  req = UrlRequest(self.escape_url(server_url+'/leagues/'+leagueName +'/matchdays/'+str(day["number"])), on_success=self.export_spieltag,ca_file=None, verify=False, timeout=10)
                  self.reqList.append(req)
        
    def check_all_req(self,instance): 
        i=0
        
        #try:
        if self.run:
            for req in self.reqList:
                if not req.is_finished:
                    i+=1
                elif req.error != None:
                    print(req.error)
                    i+=1
                    self.reqList.remove(req)
                    self.waitlist.append(req)
                    Clock.schedule_once(partial(self.update_button_text,self,"Verbindung instabil, wird langsam fortgesetzt"), -1)
                    Clock.schedule_once(partial(self.remove_restart_req,self,req),3)
                    
                        
        if i==0 and len(self.waitlist)==0:
            if self.run:
                self.pb.max=len(self.reqList)+len(self.waitlist)
                self.pb.value=len(self.reqList)-i
                Clock.schedule_once(partial(self.update_button_text,self,"alles aktuell"), -1)
                self.bind_buttons()
                print(os.listdir(app_folder+"/spieltage/"))
            else:
                Clock.schedule_once(partial(self.update_button_text,self,"Update abgebrochen"), -1)
                self.bind_buttons()
        else:
            Clock.schedule_once(self.check_all_req,1)
            self.pb.max=len(self.reqList)+len(self.waitlist)
            self.pb.value=len(self.reqList)-i
    #        except:
 #           print("an error occured")
  #          Clock.schedule_once(self.check_all_req,1)
        

    def remove_restart_req(self,instace,req_old,*largs):
        if self.run:
            #maximale Requests, falls es Verbindungsprobleme gibt
            max_req=1
            count=0
            for req in self.reqList:
                if not req.is_finished:
                    count+=1
                    
            if count <= max_req:
                self.waitlist.remove(req_old)
                #print(req_old.url)
                if "/leagues/" in req_old.url:
                    req = UrlRequest(req_old.url, on_success=self.add_spieltag,ca_file=None, verify=False, timeout=10)
                elif "/leagues" in req_old.url:
                    req = UrlRequest(req_old.url, on_success=self.extract_leagues,ca_file=None, verify=False, timeout=10)
                elif '/matchdays/' in req_old.url:
                    req = UrlRequest(req_old.url, on_success=self.export_spieltag,ca_file=None, verify=False, timeout=310)
                else:
                    print("something is wrong with url")
                self.reqList.append(req)
            else:
                Clock.schedule_once(partial(self.remove_restart_req,self,req_old),1)
                #print("too many Tasks, wait")
        ##Cancel if cancel button pressed
        else:
            self.waitlist=[]
            self.reqList=[]
    def export_spieltag(self,req,result):         
        if self.run:
            for server_url in server_urls:
                if server_urls[server_url] in req.url:
                    if not os.path.isdir(app_folder+"/spieltage/"+server_url):
                      os.mkdir(app_folder+"/spieltage/"+server_url)
                    
                    f= open(app_folder+"/spieltage/"+server_url+"/"+str(result['leagueShortName'])+"_"+str(result['number'])+".radball","w+",encoding='utf-8')
            #print(type(day))
            f.write(json.dumps(result, indent=4, ensure_ascii=False))
            #print(day)
            f.close

    def escape_url(self, url):
        #Python 3 has libraries to handle this situation. Use urllib.parse.urlsplit to split the URL into its components, and urllib.parse.quote to properly quote/escape the unicode characters and urllib.parse.urlunsplit to join it back together.
        url = urllib.parse.urlsplit(url)
        url = list(url)
        url[2] = urllib.parse.quote(url[2])
        url = urllib.parse.urlunsplit(url)
        return url
    def clear_folder(self, dir):
        if os.path.exists(dir):
            for the_file in os.listdir(dir):
                file_path = os.path.join(dir, the_file)
                print(file_path)
                print(dir)
                
                if dir == app_folder + "/spieltage/eigene":
                    pass
                else:
                    
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        else:
                            self.clear_folder(file_path)
                            os.rmdir(file_path)
                    except Exception as e:
                        print(e)



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

        data["games"] = list((games))
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
    service = ""
    def on_request_close(self, *args):
        self.textpopup(title='', text='Programm beenden?')
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
        mybutton.bind(on_release=self.close_app)
        popup.open()
    
    def on_key(self, window, key, *args):
        if key == 27:  # the esc key
            Clock.schedule_once(partial(self.on_request_close,self, -1))
            return True
    
    def start_service(self, name):    
        context =  mActivity.getApplicationContext()
        service_name = str(context.getPackageName()) + '.Service' + "Radball"
        service = autoclass(service_name)
        service.start(mActivity,'')   # starts or re-initializes a service
        return service


    def on_android_back(self, window, key, scancode, codepoint, modifiers):
            # key==27 bedeutet "Escape"/"Back" in Kivy
            if key == 27:
                current_screen = self.screen_manager.current
                if current_screen == "Start":
                    # Wenn wir im Start-Screen sind, dürfen wir die App schließen:
                    return False  # Kivy bzw. Android darf das Event normal behandeln -> App schließen
                else:
                    # In jedem anderen Screen gehen wir zurück zum jeweiligen vorherigen Screen
                    if current_screen == "NewGameStep1":
                        self.screen_manager.current = "Start"
                    elif current_screen == "NewGameStep2":
                        self.screen_manager.current = "NewGameStep1"
                    elif current_screen == "NewGameStep3":
                        self.screen_manager.current = "NewGameStep2"
                    elif current_screen == "Game":
                        return False
                    else:
                        # Fallback, falls andere Screens: zurück zu "Start"
                        self.screen_manager.current = "Start"

                    return True  # Wir haben das Event verarbeitet, App bleibt offen
            return False


    def build(self):
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
        Window.bind(on_keyboard=self.on_android_back)

        # 2) Neue Methode in EpicApp (nur das hier ist neu!):
        

        
        return self.screen_manager
    
		

if __name__ == "__main__":
    app_folder = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(app_folder+"/spieltage"):
        os.makedirs(app_folder+"/spieltage")
    rad_app = EpicApp()
    rad_app.run()
