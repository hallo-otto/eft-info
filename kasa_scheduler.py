import asyncio
from kasa import Discover
import pandas as pd
import streamlit as st
import subprocess

class Kasa_Scheduler:
  def __init__(self,user, pw):
    self.plug_ip = [
      {"ip": "192.168.2.157", "name": "0Pumpe blau Küche"},
      {"ip": "192.168.2.156", "name": "1Rasen grün Innenstern"},
      {"ip": "192.168.2.160", "name": "2Beet gelb Küche S-Bogen"},
      {"ip": "192.168.2.158", "name": "3Vorgarten orange Außenstern"},
      {"ip": "192.168.2.161", "name": "4Micro Drip" },
      {"ip": "192.168.2.159", "name": "Tropfenlampe grau mini"}
    ]

    self.username = user
    self.password = pw

  async def dev_info(self):
      for ip in self.plug_ip:
          rc = await self.dev_ausgabe(ip["ip"])
      return rc

  async def dev_ausgabe(self,ip):
      if ping(ip) == False: return
      
      try:
        devices = await Discover.discover_single (
          host=ip,
          timeout=5,
          username= self.username,
          password="self.password"
        )
        rc = await devices.update()
        # print(f"devices: {devices}")

      except Exception as e:
        st.error(f"❌ Error bei IP {ip}: {e!r}")
        return "error"

      info   = devices.sys_info  # rohes Dict aus system.get_sysinfo
      status = "an" if info["relay_state"] == 1 else "aus"
      title  = f"Device: {devices.host} {info['alias']} Status: {status}"

      rule_list = devices.modules["schedule"].data["get_rules"]["rule_list"]

      # Sortieren
      rule_list_sorted = sorted(
         rule_list,
         key=lambda item: item.get("smin")
      )
      data = []
      for rule in rule_list_sorted:
        #print(rule)
        h    = rule.get("smin") // 60
        m    = rule.get("smin") % 60
        if m<10: m=f"0{m}"
        zeit   = f"{h}:{m}"
        schalt = "aus" if rule.get('sact') == 0 else "an"
        tage   = ", ".join(str(x) for x in rule.get("wday"))

        data.append({
          "Name": rule.get("name"),
          "Schalter": schalt,
          "Tage": tage,
          "Zeit": zeit
        })
      df = pd.DataFrame(data)
      st.markdown(
       "<style>table th {text-align: left !important;</style>",
        unsafe_allow_html=True
      )
      st.markdown(f"**{title}**")
      st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
      return "ok"

  async def ping(self, ip):
    # Anzahl Ping-Versuche
    count = '4'  if platform.system().lower() != 'windows' else '4'
    param = '-n' if platform.system().lower() == 'windows' else '-c'

    try:
      result = subprocess.run(
        ['ping', param, count, ip],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
      )
      print(result.stdout)
      return result.returncode == 0
    except Exception as e:
      st.error(f"Fehler beim Ping: {ip} {e}")
      return False
# ----------------
# Streamlit Start
# ----------------
async def start():
  user = st.text_input("User")
  pw   = st.text_input("Password")
  if st.button("Anmelden"):
    try:
      s = Kasa_Scheduler(user, pw)
      if await s.dev_info() == "error": return
      st.success("Login erfolgreich!")
      #st.session_state.logged_in = True
      # Neustart nach Anmeldung
      #st.rerun()
    except Exception as e:
      st.error(f"Anmeldefehler: {e}")

  #Test
  #await s.dev_ausgabe("192.168.2.159")

asyncio.run(start())
