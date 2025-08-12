import asyncio
from aiolimiter import AsyncLimiter
from aiohttp import ClientSession
from api.api import AnkerSolixApi
import streamlit as st
from datetime import date, datetime, timedelta
from api.apitypes import SolixDeviceType  # pylint: disable=no-name-in-module
import numpy as np
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

  async def energy_analysis_raw(self, siteId, deviceSn, startday, endday, dayTotals, deviceType):
    endpoint = "power_service/v1/site/energy_analysis"
    payload = {
      "site_id": siteId,
      "device_sn": deviceSn,          # Solarbank
      "start_time": startday,         # str: "2025-08-01"
      "end_time": endday,             # str: "2025-08-12"
      "device_type": deviceType,      # "solar_production", "solarbank", "home_usage", "grid"
      "dayTotals":dayTotals,          #  "false" / "true"
      "type": "week",
    }

    resp = await self.api.apisession.request("POST", endpoint, json=payload)
    return resp

  async def ausgabe_graph(self, data):
      # Ausgabe
      werte = []
      for d in data:
        dd = d.get("data")

        arr_dd = []
        arr_ww = []
        for w in dd:
            arr_dd.extend([datetime.strptime(w.get("time"), '%Y-%m-%d')])
            arr_ww.extend([round(float(w.get("value")), 2)])

        werte.extend([[d.get("type"),arr_dd, arr_ww, d.get("color")]])

      # Grafik erstellen
      fig, ax = plt.subplots(figsize=(12, 6))

      for w in werte:
          ax.plot(w[1], w[2], label=w[0], marker="o", linestyle="-", color=w[3])
          for d, v in zip(w[1],w[2]):
              ax.text(d, v + 0.2, f"{v}", ha="center", va="bottom", fontsize=10, color=w[3])

      # Achsenbeschriftung
      ax.set_xlabel("Datum")
      # ax.set_xticks(rotation=45)
      ax.set_ylabel("Strom")

      # Titel
      ax.set_title("Solaranlage")

      # Legende anzeigen
      ax.legend()

      # Raster aktivieren
      ax.grid(True)

      # Grafik anzeigen
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
      startDay  = (dat          - timedelta(days=numDays)).strftime("%Y-%m-%d")
      endDay    = dat.strftime("%Y-%m-%d")
      dayTotals = "false"

      # "device_type": ["solar_production", "solarbank", "home_usage", "grid"]
      data = []
      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "solar_production")
      data.extend([{"type": "solar production", "color": "#84bd00", "data": resp.get("data").get("power")}])

      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "solarbank")
      data.extend([{"type": 'solarbank', "color": "#e1e000", "data": resp.get("data").get("power")}])

      #resp = await self.energy_analysis_raw(siteId, deviceSn2, startDay, endDay, dayTotals, "hes")
      #data.extend([{"type": "hes", "color": "#ffcc99", "data": resp.get("data").get("power")}])

      resp = await self.energy_analysis_raw(siteId, deviceSn1, startDay, endDay, dayTotals, "home_usage")
      data.extend([{"type": "home usage", "color": "#0085ad", "data": resp.get("data").get("power")}])

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

      #limiter = AsyncLimiter(max_rate=10, time_period=60)  # 5 Anfragen pro Sekunde
      #try:
      #  async with limiter:
      #    await self.hist(site_data)
      #except Exception as e:
      #  print(f"Error: {e}")

      await self.hist(site_data)

      self.api.sites.clear()
    else:
       st.warning("Keine Standorte verfügbar.")
       #print("Keine Standorte verfügbar.")

async def create_session_and_update(user, pw, country, numdays):
  async with ClientSession() as session:
    a = AnkerSolixInfo(user, pw, country, numdays, session)
    await a.update_sites()

#asyncio.run(create_session_and_update("hallo.otto123.oo@gmail.com", "Anker3.oo#196", "DE",2))
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
