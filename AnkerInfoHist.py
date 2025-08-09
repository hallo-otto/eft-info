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

  async def hist(self, site_data):
      # Historische Daten

      """
      Bedeutung der Werte:
      ACCOUNT: Das Nutzerkonto, über das die API-Session läuft.
      SYSTEM: Das „Power System“ (bzw. „Site“) wie es in der Anker-App definiert ist.
      VIRTUAL: Wird für virtuelle Systeme verwendet — z. B. bei Einzelgeräten wie Solaranlagen oder Wechselrichtern, die keinem realen System zugeordnet sind.
      SOLARBANK: Ein Solarbank-Gerät (z. B. Solarbank E1600, Pro, Plus, 2 AC, 3 E2700 etc.)
      INVERTER: Wechselrichter (Standalone oder im System) wie MI60 oder MI80
      SMARTMETER: Smart Meter (z. B. Anker 3-Phase WiFi, Shelly 3EM) für Verbrauchsmessung
      SMARTPLUG: Anker Smart Plug (z. B. 2500 W) – einfache Steuerung möglich
      POWERPANEL: Power Panels (z. B. für SOLIX F3800; derzeit nur Basisüberwachung)
      HES: Home Energy Systems (HES) wie SOLIX X1 Energy-Module oder Batteriesysteme
      """

      siteId   = site_data.get("site_id")
      site_id  = siteId
      devices  = list(self.api.devices)
      deviceSn = devices[0]

      # Datumsbereich
      #startday = datetime.strptime("2025-07-01", "%Y-%m-%d")  # String → datetime
      #numdays = 20
      dat     = date.today() - timedelta(days=self.numdays)
      startday = datetime.strptime(str(dat), "%Y-%m-%d")  # String → datetime
      daytotals=False
      use_file=False

      data = await self.api.energy_daily(
          siteId=site_id,
          deviceSn=deviceSn,
          startDay=startday,
          numDays=self.numdays,
          dayTotals=daytotals,
          devTypes={
            SolixDeviceType.INVERTER.value,
            SolixDeviceType.SOLARBANK.value,
            SolixDeviceType.SMARTMETER.value,
            SolixDeviceType.POWERPANEL.value,
            SolixDeviceType.HES.value,
          },
          showProgress=True,
          fromFile=use_file,
      )

      # Ausgabe
      werte = []
      for l in data:
          d   = data[l]
          dl  = datetime.strptime(l, '%Y-%m-%d')
          arr = [[dl,
                  round(float(d.get("battery_discharge")),0),
                  round(float(d.get("home_usage")),0),
                  round(float(d.get("solar_production")),0)
                ]]
          werte.extend(arr)
      # Transponierte
      ausgabe = np.array(werte).T

      # Grafik erstellen
      fig, ax = plt.subplots(figsize=(12, 6))

      ax.plot(ausgabe[0], ausgabe[1], label="battery_discharge")
      ax.plot(ausgabe[0], ausgabe[2], label="home_usage")
      ax.plot(ausgabe[0], ausgabe[3], label="solar_production")

      # Achsenbeschriftung
      ax.set_xlabel("Datum")
      #ax.set_xticks(rotation=45)
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

#asyncio.run(create_session_and_update("hallo.otto123.oo@gmail.com", "Anker3.oo#196", "DE"))

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

