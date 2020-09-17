import requests
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import os


session = requests.Session()
app_folder = os.path.dirname(os.path.abspath(__file__))


def get_url(url):
    return json.loads(session.get(url).text)


r = session.get('https://bw.cycleball.eu/leagues')
y = json.loads(r.text)
list_of_urls=[]
leagues=[]
for league in y:
    list_of_urls.append("https://bw.cycleball.eu/leagues/"+league['id'])
with ThreadPoolExecutor(max_workers=50) as pool:
    leagues=(list(pool.map(get_url,list_of_urls)))    
matchdays=[]

for league in leagues:
    for day in league['days']:
        list_of_urls.append('https://bw.cycleball.eu/matchdays/'+str(day["id"]))

with ThreadPoolExecutor(max_workers=50) as pool:
    matchdays=(list(pool.map(get_url,list_of_urls)))

for match in matchdays:
    f= open(app_folder+"/spieltage/"+str(match['id'])+".radball","w+",encoding='utf-8')
    print(type(match))
    f.write(json.dumps(match, indent=4, ensure_ascii=False))
    #print(match)
    #time.sleep(10)
    f.close
    
