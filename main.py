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
        self.cols = 1

        # And one label with bigger font and centered text
        self.message = Label(halign="center", valign="middle", font_size=30)

        # By default every widget returns it's side as [100, 100], it gets finally resized,
        # but we have to listen for size change to get a new one
        # more: https://github.com/kivy/kivy/issues/1044e
        self.message.bind(width=self.update_text_width)

        # Add text widget to the layout
        self.add_widget(self.message)

    # Called with a message, to update message text in widget
    def update_info(self, message):
        self.message.text = message

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
        pass
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
        req = UrlRequest('https://bw.cycleball.eu/leagues', on_success=self.extract_leagues,ca_file=None, verify=False, timeout=30)#, on_failure=
        self.reqList.append(req)
        Clock.schedule_once(self.check_all_req,3)
    def extract_leagues(self,req,result):
        #print(req)
        Clock.schedule_once(partial(self.update_button_text,self,"Suche nach Ligen"), -1)
        
        self.list_of_urls = []
        
        for league in result:
            self.list_of_urls.append("https://bw.cycleball.eu/leagues/"+league['id'])
            req = UrlRequest("https://bw.cycleball.eu/leagues/"+league['id'], on_success=self.add_spieltag,ca_file=None, verify=False, timeout=30)#, on_failure=
            self.reqList.append(req)
        print(self.list_of_urls)
        
        
    def add_spieltag(self,req,result):
        Clock.schedule_once(partial(self.update_button_text,self,"Suche nach Spieltagen"), -1)
        for day in result['days']:
            req = UrlRequest('https://bw.cycleball.eu/matchdays/'+str(day["id"]), on_success=self.export_spieltag,ca_file=None, verify=False, timeout=30)
            self.reqList.append(req)
        
    def check_all_req(self,instance): 
        i=0
        
        try:
            for req in self.reqList:
                if not req.is_finished:
                    i+=1
                elif req.error != None:
                    print(req.error)
                    i+=1
                    self.reqList.remove(req)
                    self.waitlist.append(req)
                    Clock.schedule_once(partial(self.update_button_text,self,"Verbindung instabil, Wiederholung"), -1)
                    Clock.schedule_once(partial(self.remove_restart_req,self,req), 10)
                    
                            
            if i==0 and len(self.waitlist)==0:
                self.pb.max=len(self.reqList)+len(self.waitlist)
                self.pb.value=len(self.reqList)-i
                Clock.schedule_once(partial(self.update_button_text,self,"alles aktuell"), -1)
                
            else:
                Clock.schedule_once(self.check_all_req,1)
                self.pb.max=len(self.reqList)+len(self.waitlist)
                self.pb.value=len(self.reqList)-i
        except:
            print("an error occured")
            Clock.schedule_once(self.check_all_req,1)
        

    def remove_restart_req(self,instace,req_old,*largs):
        
        self.waitlist.remove(req_old)
        print(req_old.url)
        if "https://bw.cycleball.eu/leagues/" in req_old.url:
            req = UrlRequest(req_old.url, on_success=self.add_spieltag,ca_file=None, verify=False, timeout=30)
        elif "https://bw.cycleball.eu/leagues" in req_old.url:
            req = UrlRequest(req_old.url, on_success=self.extract_leagues,ca_file=None, verify=False, timeout=30)
        elif 'https://bw.cycleball.eu/matchdays/' in req_old.url:
            req = UrlRequest(req_old.url, on_success=self.export_spieltag,ca_file=None, verify=False, timeout=30)
        else:
            print("something is wrong with url")
        self.reqList.append(req)
        
    def export_spieltag(self,req,result):         
        print(result)
        f= open(app_folder+"/spieltage/"+str(result['id'])+".radball","w+",encoding='utf-8')
        #print(type(day))
        f.write(json.dumps(result, indent=4, ensure_ascii=False))
        #print(day)
        f.close
        
        '''  
        def get_url(url):
            return json.loads(session.get(url).text)
        session = requests.Session()
        r = session.get('https://bw.cycleball.eu/leagues')
        y = json.loads(r.text)
        list_of_urls=[]
        leagues = []
        for league in y:
            list_of_urls.append("https://bw.cycleball.eu/leagues/"+league['id'])
            
            leagues.append(get_url("https://bw.cycleball.eu/leagues/"+league['id']))
        #print(leagues)    
              
        max_workers=1
        if platform == 'android':
            max_workers=50
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            leagues=(list(pool.map(get_url,list_of_urls)))
        

        
        list_of_urls = deque ([])
        i=0
        for league in leagues:
            for day in league['days']:
                i+=1
                list_of_urls.append('https://bw.cycleball.eu/matchdays/'+str(day["id"]))
        self.pb.max = len(list_of_urls)
        self.pb.value=0   
        self.run=True
        Clock.schedule_once(partial(self.get_spieltage,self,list_of_urls,session), 0)
        #print("scheduled")
        '''
    def get_spieltage(self,dt,urls,session,*largs):           
        if len(urls)>0 and self.run:
            matchday=urls.popleft()
            day=json.loads(session.get(matchday).text)
            #print(day)
            f= open(app_folder+"/spieltage/"+str(day['id'])+".radball","w+",encoding='utf-8')
            #print(type(day))
            f.write(json.dumps(day, indent=4, ensure_ascii=False))
            #print(day)
            f.close
            #print(day['leagueName'])
            #print("Spieltag Nr. " + str (day['number']))
            #for game in day['games']:
            #    print (game['teamA'] + ' - ' + game['teamB'])
            #print()
            #print() 
            Clock.schedule_once(partial(self.update_button_text,self,(day['leagueName']+" _ Spieltag: "+str(day['number']))), -1)
            Clock.schedule_once(partial(self.get_spieltage,self,urls,session), 0)
        elif not self.run:
            Clock.schedule_once(partial(self.update_button_text,self,"Update abgebrochen"), -1)
            self.bind_buttons()
        else:
            Clock.schedule_once(partial(self.update_button_text,self,"Spieltage aktuell"), -1)
            self.bind_buttons()

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
