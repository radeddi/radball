import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
# to use buttons:
from kivy.uix.button import Button
from kivy.uix.popup import Popup

from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.progressbar import ProgressBar
from kivy.network.urlrequest import UrlRequest

from kivy.uix.dropdown import DropDown

import os
#import certifi as cfi
import requests
import random

import datetime
from functools import partial

from collections import deque

try:
	import simplejson as json
except ImportError:
	import json
import time
from concurrent.futures import ThreadPoolExecutor
import socket 
from kivy.utils import platform

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 5556))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

kivy.require("1.10.1")


class ConnectPage(GridLayout):
    # runs on initialization
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 2  # used for our grid

        
        self.add_widget(Label(text='IP:'))  # widget #1, top left
        self.ip = TextInput(multiline=False)  # defining self.ip...
        self.add_widget(self.ip) # widget #2, top right

        self.add_widget(Label(text='Port:'))
        self.port = TextInput(multiline=False)
        self.add_widget(self.port)

        self.add_widget(Label(text='Username:'))
        self.username = TextInput(multiline=False)
        self.add_widget(self.username)

        # add our button.
        self.join = Button(text="Join")
        self.join.bind(on_press=self.join_button)
        self.add_widget(Label())  # just take up the spot.
        self.add_widget(self.join)

    def join_button(self, instance):
        port = self.port.text
        ip = self.ip.text
        username = self.username.text
        
        #print(f"Joining {ip}:{port} as {username}")
        # Create info string, update InfoPage with a message and show it
        info = f"Joining {ip}:{port} as {username}"
        chat_app.info_page.update_info(info)
        chat_app.screen_manager.current = 'Info'

# Simple information/error page
class InfoPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Just one column
        self.cols = 3
        
        self.dropdownLeague = DropDown()
        
        self.mainbuttonLeague = Button(text='Liga auswählen', size_hint_y=None)

        # show the dropdown menu when the main button is released
        # note: all the bind() calls pass the instance of the caller (here, the
        # mainbutton instance) as the first argument of the callback (here,
        # dropdown.open.).
        self.mainbuttonLeague.bind(on_release=self.dropdownLeague.open)

        # one last thing, listen for the selection in the dropdown list and
        # assign the data to the button text.
        self.dropdownLeague.bind(on_select=lambda instance, x: setattr(self.mainbuttonLeague, 'text', x))
        self.add_widget(self.mainbuttonLeague)
        
        
    # Called with a message, to update message text in widget
    def update_info(self):
        dateiliste=os.listdir(app_folder+"/spieltage/")
        self.spieltage=dict()
        self.leagues=dict()
        for datei in dateiliste:
            f=open(app_folder+"/spieltage/"+datei,"r",encoding='utf-8')
            game_json=(json.loads(f.read()))
            self.spieltage[datei]=game_json
            print(game_json)
            print(type(game_json))
            if game_json['league'] in self.leagues.keys():
               self.leagues[game_json['league']].append(game_json)
            else:
                self.leagues[game_json['league']]=[game_json]
        for key in self.leagues.keys():
            print(key)
        self.dropdownLeague.clear_widgets()

        for index in sorted(self.leagues.keys()):
            # When adding widgets, we need to specify the height manually
            # (disabling the size_hint_y) so the dropdown can calculate
            # the area it needs.

            btn = Button(text=self.leagues[index][0]["leagueName"], size_hint_y=None, height=44)

            # for each button, attach a callback that will call the select() method
            # on the dropdown. We'll pass the text of the button as the data of the
            # selection.
            btn.bind(on_release=lambda btn: self.dropdownLeague.select(btn.text))

            # then add the button inside the dropdown
            self.dropdownLeague.add_widget(btn)
        
        
        
    # Called on label width update, so we can set text width properly - to 90% of label width
    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)

class StartPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 10
        self.message = Label(halign="center",font_size=30)


        # Add text widget to the layout
        self.add_widget(self.message)
        self.message.text = "Willkommen zur Radballanzeige"    
        
        #Spieltag wählen
        self.existing_day = Button(text="Spieltag wählen",font_size=20)
        self.add_widget(self.existing_day)
        
        #neuen Spieltag erstellen
        self.new_day = Button(text="neuen Spieltag erstellen",font_size=20)
        self.add_widget(self.new_day)

        #spieltage online laden
        self.update_days = Button(text="Spieltage online aktualisieren",font_size=20,id="up_da")
        self.add_widget(self.update_days)

        self.bind_buttons()
		
        
	
	
        # By default every widget returns it's side as [100, 100], it gets finally resized,
        # but we have to listen for size change to get a new one
        # more: https://github.com/kivy/kivy/issues/1044
        self.message.bind(width=self.update_text_width)
        self.pb=ProgressBar()
        self.add_widget(self.pb)
    def bind_buttons(self):
        self.existing_day.bind(on_press=self.existing_button)
        self.new_day.bind(on_press=self.new_button)
        self.update_days.bind(on_press=self.update_button)
        self.update_days.unbind(on_press=self.create_popup) 
    def unbind_buttons(self):
        self.existing_day.unbind(on_press=self.existing_button)
        self.new_day.unbind(on_press=self.new_button)
        self.update_days.unbind(on_press=self.update_button)
        self.update_days.bind(on_press=self.create_popup)    
    def existing_button(self, instance):
        chat_app.info_page.update_info()
        chat_app.screen_manager.current = 'Info'
    def new_button(self, instance):
        pass   
    def update_button(self, instance):
        Clock.schedule_once(self.update_all,1)
        
    def update_button_text(self,instance,text,*largs):
        #pass
        
        self.update_days.text=text
    def update_process(self,dt):
        if self.update_thread.isAlive():
            print("running")
            Clock.schedule_once(self.update_process,1)
            sock.sendto(b'This is a test', ("255.255.255.255", 6666))
        else:    
            self.update_days.text="done"
     
        # Called on label width update, so we can set text width properly - to 90% of label width
    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)
    def create_popup(self,instance):
        layout=GridLayout(cols=1, rows=3)
        layout.add_widget(Label(text="Wollen Sie wirklich das Update abbrechen?", halign="center",font_size=30))
        cancel = Button(text='abbrechen',font_size=20)
        go_on = Button(text='nicht abbrechen',font_size=20)
        layout.add_widget(cancel)
        layout.add_widget(go_on)
        popup = Popup(title='cancel',content=layout, auto_dismiss=False)
        go_on.bind(on_press=popup.dismiss)
        cancel.bind(on_press=popup.dismiss)
        cancel.bind(on_press=self.reset_deque)
        popup.open()
    def reset_deque(self,instance):
        self.run=False
    def update_all(self,instance):
        #try:
        self.reqList=[]
        self.waitlist=[]
        self.unbind_buttons()
        Clock.schedule_once(partial(self.update_button_text,self,"Verbinden"), -1)
        req = UrlRequest('https://bw.cycleball.eu/leagues', on_success=self.extract_leagues,ca_file=None, verify=False, timeout=10)#, on_failure=
        self.reqList.append(req)
        Clock.schedule_once(self.check_all_req,0.5)
    def extract_leagues(self,req,result):
        #print(req)
        Clock.schedule_once(partial(self.update_button_text,self,"Suche nach Ligen"), -1)
        
        self.list_of_urls = []
        self.leaguesList = []
        for league in result:
            self.leaguesList.append(league['league'])
            self.list_of_urls.append("https://bw.cycleball.eu/leagues/"+league['id'])
            req = UrlRequest("https://bw.cycleball.eu/leagues/"+league['id'], on_success=self.add_spieltag,ca_file=None, verify=False, timeout=10)#, on_failure=
            self.reqList.append(req)
        print(self.list_of_urls)
        
        
    def add_spieltag(self,req,result):
        Clock.schedule_once(partial(self.update_button_text,self,"Suche nach Spieltagen"), -1)
        for day in result['days']:
            req = UrlRequest('https://bw.cycleball.eu/matchdays/'+str(day["id"]), on_success=self.export_spieltag,ca_file=None, verify=False, timeout=10)
            self.reqList.append(req)
        
    def check_all_req(self,instance): 
        i=0
        
        #try:
        for req in self.reqList:
            if not req.is_finished:
                i+=1
            elif req.error != None:
                #print(req.error)
                i+=1
                self.reqList.remove(req)
                self.waitlist.append(req)
                Clock.schedule_once(partial(self.update_button_text,self,"Verbindung instabil, wird langsam fortgesetzt"), -1)
                Clock.schedule_once(partial(self.remove_restart_req,self,req),3)
                
                        
        if i==0 and len(self.waitlist)==0:
            self.pb.max=len(self.reqList)+len(self.waitlist)
            self.pb.value=len(self.reqList)-i
            Clock.schedule_once(partial(self.update_button_text,self,"alles aktuell"), -1)
            self.bind_buttons()
            print(os.listdir(app_folder+"/spieltage/"))
            
        else:
            Clock.schedule_once(self.check_all_req,1)
            self.pb.max=len(self.reqList)+len(self.waitlist)
            self.pb.value=len(self.reqList)-i
#        except:
 #           print("an error occured")
  #          Clock.schedule_once(self.check_all_req,1)
        

    def remove_restart_req(self,instace,req_old,*largs):
        
        #maximale Requests, falls es Verbindungsprobleme gibt
        max_req=1
        count=0
        for req in self.reqList:
            if not req.is_finished:
                count+=1
                
        if count <= max_req:
            self.waitlist.remove(req_old)
            #print(req_old.url)
            if "https://bw.cycleball.eu/leagues/" in req_old.url:
                req = UrlRequest(req_old.url, on_success=self.add_spieltag,ca_file=None, verify=False, timeout=10)
            elif "https://bw.cycleball.eu/leagues" in req_old.url:
                req = UrlRequest(req_old.url, on_success=self.extract_leagues,ca_file=None, verify=False, timeout=10)
            elif 'https://bw.cycleball.eu/matchdays/' in req_old.url:
                req = UrlRequest(req_old.url, on_success=self.export_spieltag,ca_file=None, verify=False, timeout=310)
            else:
                print("something is wrong with url")
            self.reqList.append(req)
        else:
            Clock.schedule_once(partial(self.remove_restart_req,self,req_old),1)
            #print("too many Tasks, wait")
        
    def export_spieltag(self,req,result):         
        print(result)
        f= open(app_folder+"/spieltage/"+str(result['id'])+".radball","w+",encoding='utf-8')
        #print(type(day))
        f.write(json.dumps(result, indent=4, ensure_ascii=False))
        #print(day)
        f.close

  

class EpicApp(App):
    def build(self):
        if platform == 'android':
            import android
            service = android.AndroidService('Notification Name', 'Notification Message')
            service.start('Service args')

        
        
        # We are going to use screen manager, so we can add multiple screens
        # and switch between them
        self.screen_manager = ScreenManager()

        # Initial, connection screen (we use passed in name to activate screen)
        # First create a page, then a new screen, add page to screen and screen to screen manager
        self.start_page = StartPage()
        screen = Screen(name='Start')
        screen.add_widget(self.start_page)
        self.screen_manager.add_widget(screen)
        
        
        self.connect_page = ConnectPage()
        screen = Screen(name='Connect')
        screen.add_widget(self.connect_page)
        self.screen_manager.add_widget(screen)

        # Info page
        self.info_page = InfoPage()
        screen = Screen(name='Info')
        screen.add_widget(self.info_page)
        self.screen_manager.add_widget(screen)

        return self.screen_manager


if __name__ == "__main__":
    app_folder = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(app_folder+"/spieltage"):
        os.makedirs(app_folder+"/spieltage")
    chat_app = EpicApp()
    chat_app.run()
