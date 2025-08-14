import asyncio

import api.apitypes
from aiohttp import ClientSession
from api.api import AnkerSolixApi
from api.apitypes import SolixDeviceType
import streamlit as st
from datetime import date, datetime, timedelta
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# @st.cache_resource
class AnkerSolixInfo:
  def __init__(self, user, pw, country, numdays, session):
    self.user = user
    self.pw = pw
    self.country = country
    self.numdays = numdays
    self.session = session
    self.api = AnkerSolixApi(user, pw, country, session)  # einmalig speichern
    self.API_ENDPOINTS = api.apitypes.API_ENDPOINTS

  async def energy_analysis_raw(self, siteId, deviceSn, startday, endday, dayTotals, deviceType):
    #endpoint = "power_service/v1/site/energy_analysis"
    endpoint = self.API_ENDPOINTS["energy_analysis"]
    payload = {
      "site_id": siteId,
      "device_sn": deviceSn,          # Solarbank
      "start_time": startday,         # str: "2025-08-01"
      "end_time": endday,             # str: "2025-08-12"
      "device_type": deviceType,      # "solar_production", "solarbank", "home_usage", "grid"
      #"dayTotals":dayTotals,          # "false" / "true"
      "type": "week",
    }

    resp = await self.api.apisession.request("POST", endpoint, json=payload)
    return resp

  async def ausgabe_graph(self, data):
      # Ausgabe
      werte     = []
      arr_type  = []
      arr_avg   = []
      arr_color = []
      for d in data:
        dd = d.get("data")

        arr_dd  = []
        arr_ww  = []
        arr_th  = []
        d_sum   = 0
        n       = 0
        # Überstromgrenze
        anz_th  = 0
        th      = -1.8
        for w in dd:
            val = float(w.get("value"))
            arr_dd.extend([datetime.strptime(w.get("time"), '%Y-%m-%d')])
            arr_ww.extend([round(val, 2)])
            arr_th.extend([th])
            # wie oft wird 2.7kWh Einspeisung überschtritten
            if d.get("type") == "grid export" and val <= th:
                anz_th += 1

            d_sum += val
            n = n + 1

        werte.extend([[d.get("type"),arr_dd, arr_ww, d.get("color")]])
        arr_type.extend([d.get("type")])
        arr_color.extend([d.get("color")])
        arr_avg.extend([d_sum/n])

      # Grafik erstellen
      fig, ax = plt.subplots(figsize=(15, 7))

      for w in werte:
          ax.plot(w[1], w[2], label=w[0], marker="o", linestyle="-", color=w[3])
          for dd, v in zip(w[1],w[2]):
              color = w[3]
              # Markiering, wenn der Schwellwert unterschritten wurde
              if d.get("type") == "grid export" and v <= th:
                  color="#84bd00"
              ax.text(dd, v + 0.2, f"{v}", ha="center", va="bottom", fontsize=12, color=color)
      plt.plot(w[1], arr_th, label=str(th) + "kWh", linestyle="-", color="#ffcc99", linewidth=3)

      if n <= 25:
         rot=0
      else:
         rot=15
      ax.tick_params(axis='x', labelsize=14, rotation=rot)  # Schriftgröße x-Achsenwerte
      ax.tick_params(axis='y', labelsize=14)                # Schriftgröße y-Achsenwerte
      # Achsenbeschriftung
      ax.set_xlabel("Datum",fontsize=14)
      ax.set_ylabel("kWh",fontsize=14)
      # Titel
      ax.set_title("Solaranlage",fontsize=16)
      # Legende anzeigen
      #ax.legend()
      ax.legend(loc='upper left', bbox_to_anchor=(0, -0.10), ncol=5,fontsize=14)
      # Raster aktivieren
      ax.grid(True)
      # X-Achse enger beschriften: z. B. alle 3 Tage
      ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))

      # Grafik anzeigen
      fig.tight_layout()
      st.pyplot(fig)
      # Überschreitung 2.7kWk
      prz = round(100 * anz_th / n,2)
      st.markdown(f"<p style='font-size:13px;padding-left:20px'>🔹Überschreitung Einspeisung {th} kWh Tage: {anz_th} ({prz}%)</p>", unsafe_allow_html=True)

      # Durchscnitt
      fig, ax = plt.subplots(figsize=(12, 6))
      bars = ax.bar(arr_type, arr_avg, color=arr_color)
      # Beschriftungen über den Balken
      for bar in bars:
          y = round(bar.get_height(),2)
          plt.text(bar.get_x() + bar.get_width() / 2, y + 0.1, f'{y}', ha='center', va='bottom',fontsize=12)

      ax.set_title(f"Solaranlage Durchscnitt ({n})",fontsize=13)
      ax.legend()
      ax.grid(True)
      ax.tick_params(axis='x',   labelsize=12)  # Schriftgröße x-Achsenwerte
      ax.tick_params(axis='y',   labelsize=12)  # Schriftgröße y-Achsenwerte
      ax.set_xlabel("Type",fontsize=12)
      ax.set_ylabel("kWh", fontsize=12)
      fig.tight_layout()
      st.pyplot(fig)

  async def hist(self, site_data):
      # Historische Daten
      siteId    = site_data.get("site_id")
      devices   = list(self.api.devices)
      deviceSn1 = devices[0]
      deviceSn2 = devices[1]
      numDays   = self.numdays

      # Datumsbereich
      dat       = (date.today() - timedelta(days=1))
      startDay  = (dat          - timedelta(days=numDays-1)).strftime("%Y-%m-%d")
      if startDay < "2025-07-11":
        startDay = "2025-07-11"
      endDay    = dat.strftime("%Y-%m-%d")
      dayTotals = "false"

      # "device_type": ["solar_production", "solarbank", "home_usage", "grid"]
      data = []
      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "solar_production")
      data.extend([{"type": "solar production", "color": "#84bd00", "data": resp.get("data").get("power")}])

      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "home_usage")
      data.extend([{"type": "home usage", "color": "#0085ad", "data": resp.get("data").get("power")}])

      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "solarbank")
      data.extend([{"type": 'solarbank', "color": "#e1e000", "data": resp.get("data").get("power")}])

      #resp = await self.energy_analysis_raw(siteId, deviceSn2, startDay, endDay, dayTotals, "hes")
      #data.extend([{"type": "hes", "color": "#ffcc99", "data": resp.get("data").get("power")}])

      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "grid")
      data.extend([{"type": "grid export", "color": "#e4002b", "data": resp.get("data").get("power")}])

      await self.ausgabe_graph(data)

  async def update_sites(self):
    # Beispiel: await irgendwas mit self.session
    # Du hast zu viele Anfragen in kurzer Zeit gesendet. Die API hat dich mit HTTP-Status 429 blockiert.
    await asyncio.sleep(1)  # Dummy async call
    await self.api.update_sites()
    await self.api.update_device_details()
    await self.api.update_device_energy()

    xitem = self.api.sites.items()
    items = list(xitem)
    if items:
      site, site_data = items[0]
      await self.hist(site_data)
      self.api.sites.clear()
    else:
       st.warning("Keine Standorte verfügbar.")
       #print("Keine Standorte verfügbar.")

async def create_session_and_update(user, pw, country, numdays):
  async with ClientSession() as session:
    a = AnkerSolixInfo(user, pw, country, numdays, session)
    await a.update_sites()

#asyncio.run(create_session_and_update("hallo.otto123.oo@gmail.com", "Anker3.oo#196", "DE",10))

user     = st.text_input("User")
pw       = st.text_input("Passwort", type="password")
country  = "DE"
numdaysx = st.text_input("Anzahl Tage", value="20")

if numdaysx.isdigit():
    numdays = int(numdaysx)
else:
    numdays = 10

if st.button("Anmelden"):
  try:
    asyncio.run(create_session_and_update(user, pw, country, numdays))
    st.success("Login erfolgreich!")
  except Exception as e:
    st.error(f"Anmeldefehler: {e}")
