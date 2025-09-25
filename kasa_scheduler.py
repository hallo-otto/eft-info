import asyncio
from kasa import Discover
import pandas as pd
import streamlit as st

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
          await self.dev_ausgabe(ip["ip"])

  async def dev_ausgabe(self,ip):
      try:
        devices = await Discover.discover_single (
          host=ip,
          timeout=2,
          username= self.username,
          password="self.password"
        )
        await devices.update()
       # print(f"devices: {devices}")

      except Exception as e:
        print(f"❌ Error bei IP {ip}: {e!r}")
        return

      #print(f"Info: {info}")
      info = devices.sys_info  # rohes Dict aus system.get_sysinfo
      #print("Info")
      #print("Gerät:", info["alias"])
      #print("Modell:", info["model"])
      #print("Name:", info["dev_name"])
      #print("Firmware:", info["sw_ver"])
      #print("Status:", "an" if info["relay_state"] == 1 else "aus")
      ##print("Betriebszeit:", info["on_time"], "Sekunden")
      ##print("Signalstärke:", info["rssi"], "dBm")
      #print("Aktiver Modus:", info["active_mode"])
      #print("Nächste Aktion:", info["next_action"])

      status = "an" if info["relay_state"] == 1 else "aus"
      title  = f"Device: {devices.host} {info['alias']} Status: {status}"
      #print(f"Device: {devices.host} {info['alias']} Status: {status}")
      #print("rule_list")
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
        #print(f"Name: {rule.get('name')} Schalter: {schalt} Tage: {tage}, stime: {rule.get('stime_opt')} Zeit:{zeit}")
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
# ----------------
# Streamlit Start
# ----------------
async def start():
  user = st.text_input("User")
  pw   = st.text_input("Password")
  if st.button("Anmelden"):
    try:
      s = Kasa_Scheduler(user, pw)
      await s.dev_info()
      st.success("Login erfolgreich!")
      #st.session_state.logged_in = True
      # Neustart nach Anmeldung
      #st.rerun()
    except Exception as e:
      st.error(f"Anmeldefehler: {e}")

  #Test
  #await s.dev_ausgabe("192.168.2.159")

asyncio.run(start())
