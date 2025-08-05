import asyncio
from aiohttp import ClientSession
from api.api import AnkerSolixApi
import streamlit as st
from aiolimiter import AsyncLimiter
from datetime import date, timedelta, datetime

# @st.cache_resource
class AnkerSolixInfo:
  def __init__(self, user, pw, country, session):
    self.user = user
    self.pw = pw
    self.country = country
    self.session = session
    self.api = AnkerSolixApi(user, pw, country, session)  # einmalig speichern
  def Anker_Info(self,site_data):
    ausgabe = []
    solarbank_info = site_data.get("solarbank_info")
    ausgabe.extend([["updated_time",               solarbank_info.get("updated_time")]])
    ausgabe.extend([["to_home_load",               solarbank_info.get("to_home_load")]])
    ausgabe.extend([["total_battery_power",        solarbank_info.get("total_battery_power")]])
    ausgabe.extend([["solar_power_1",              solarbank_info.get("solar_power_1")]])
    ausgabe.extend([["solar_power_2",              solarbank_info.get("solar_power_2")]])
    ausgabe.extend([["solar_power_3",              solarbank_info.get("solar_power_3")]])
    ausgabe.extend([["solar_power_4",              solarbank_info.get("solar_power_4")]])
    ausgabe.extend([["total_photovoltaic_power",   solarbank_info.get("total_photovoltaic_power")]])
    ausgabe.extend([["total_output_power",         solarbank_info.get("total_output_power")]])
    # plot
    st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>Solarbank Info</div>", unsafe_allow_html=True)
    st.dataframe(ausgabe)

  def Anker_Forecast(self,site_data):
    ausgabe = []
    energy_details = site_data.get("energy_details")
    energy_forecast = energy_details.get("pv_forecast_details")
    ausgabe.extend([["time_this_hour",  energy_forecast.get("time_this_hour")]])
    ausgabe.extend([["trend_this_hour", energy_forecast.get("trend_this_hour")]])
    ausgabe.extend([["time_next_hour",  energy_forecast.get("time_next_hour")]])
    ausgabe.extend([["trend_next_hour", energy_forecast.get("trend_next_hour")]])
    # plot
    st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>Energy Forecast</div>", unsafe_allow_html=True)
    st.dataframe(ausgabe)

  # Summieren Power je Datum un Device Type
  async def sum_power(self, solix, site_id, device_sn, devdate, devtype):
    try:
      hist_data = await solix.energy_analysis(
        siteId=site_id,
        deviceSn=device_sn,
        rangeType="day",
        startDay=devdate,
        endDay=devdate,
        devType=devtype
      )
      power = hist_data.get("power")
      # Summieren Power
      s = 0
      for p in power:
        s += float(p.get("value"))

    except Exception as e:
      st.write(f"Fehler am {devdate}: {e}")
      #daten.append((tag.strftime("%Y-%m-%d"), 0.0))
      return 0

    return s

  async def Anker_Hist(self, site_data):
    # Historische Daten
    # Datumsbereich
    solix = self.api
    site_id = site_data.get("site_id")
    devices = list(solix.devices)
    device_sn = devices[0]

    # "solar_production"	Stromerzeugung durch PV
    # "solarbank"	Batteriespeicher (Anker Solix)
    # "home_usage"	Stromverbrauch im Haus
    # "grid"	Einspeisung ins öffentliche Netz
    end = date.today()
    start = end - timedelta(days=5)
    current = start

    # es funktioniert nur day
    # Summe über der Zeitraum für die einzelnen Devices
    sum_solar         = 0
    sum_home          = 0
    sum_solarbank     = 0
    sum_grid          = 0
    ausgabe_date      = []
    ausgabe_solar     = []
    ausgabe_home      = []
    ausgabe_solarbank = []
    ausgabe_grid      = []
    ausgabe_summe     = []

    #limiter = AsyncLimiter(10, 60)
    while current <= end:
      ausgabe_date.append(current)
      #async with limiter:
      power_solar     = await self.sum_power(solix, site_id, device_sn, current, "solar_production")
      power_home      = await self.sum_power(solix, site_id, device_sn, current, "home_usage")
      power_solarbank = await self.sum_power(solix, site_id, device_sn, current, "power_solarbank")
      power_grid      = await self.sum_power(solix, site_id, device_sn, current, "grid")

      ausgabe_date.append(current)
      ausgabe_solar.append(power_solar)
      ausgabe_home.append(power_home)
      ausgabe_solarbank.append(power_solarbank)
      ausgabe_grid.append(power_grid)

    sum_solar     += power_solar
    sum_home      += power_home
    sum_solarbank += power_solarbank
    sum_grid      += power_grid

    arr = [[current, power_solar,power_home,sum_solarbank,sum_grid]]
    ausgabe_summe.extend(arr)

    #plot
    # Liste Summe
    dfl = pd.DataFrame(ausgabe_summe, columns=["Stromerzeugung", "Stromverbrauch","Solarbank","Netz"])
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>Summe {start_str} - {end_str} </div>", unsafe_allow_html=True)
    st.dataframe(dfl)

    # Diagramm
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(ausgabe_date, ausgabe_solar, label="Stromerzeugung")
    ax.plot(ausgabe_date, ausgabe_home,  label="Stromverbrauch")
    ax.plot(ausgabe_date, ausgabe_solarbank, label="Solarbank")
    ax.plot(ausgabe_date, ausgabe_grid,  label="Netz")

    # Title
    ax.set_title(f"Stromerzeugng und -verbrauch  Zeitraum: {start_str} - {end_str}")
    ax.set_xlabel("Datum")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    st.pyplot(fig)

  async def update_sites(self):
    # Beispiel: await irgendwas mit self.session
    # Du hast zu viele Anfragen in kurzer Zeit gesendet. Die API hat dich mit HTTP-Status 429 blockiert.
    #await asyncio.sleep(2)  # Dummy async call
    #limiter = AsyncLimiter(10, 60)
    #async with limiter:
    await self.api.update_sites()
    await self.api.update_device_details()
    await self.api.update_device_energy()
    xitem = self.api.sites.items()
    items = list(xitem)

    if items:
        site, site_data = items[0]
        await self.update_sites()
        if graph:
          await self.Anker_Hist(self.site_data)
        else:
          self.Anker_Info(self.site_data)
          self.Anker_Forecast(self.site_data)

        self.api.sites.clear()
    else:
        st.warning("Keine Standorte verfügbar.")

async def create_session_and_update(user, pw, country):
  async with ClientSession() as session:
    a = AnkerSolixInfo(user, pw, country, session)
    await a.update_sites()

user = st.text_input("User")
pw = st.text_input("Passwort", type="password")
country = "DE"
graph = st.checkbox("Grafik?")

if st.button("Anmelden"):
  try:
    asyncio.run(create_session_and_update(user, pw, country))
    st.success("Login erfolgreich!")
  except Exception as e:
    st.error(f"Anmeldefehler: {e}")

