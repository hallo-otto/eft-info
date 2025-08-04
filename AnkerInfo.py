import asyncio
from aiohttp import ClientSession
from api.api import AnkerSolixApi
import streamlit as st

# @st.cache_resource
class AnkerSolixInfo:
  def __init__(self, user, pw, country, session):
    self.user = user
    self.pw = pw
    self.country = country
    self.session = session
    self.api = AnkerSolixApi(user, pw, country, session)  # einmalig speichern

  async def update_sites(self):
    # Beispiel: await irgendwas mit self.session
    await asyncio.sleep(1)  # Dummy async call
    await self.api.update_device_details()
    await self.api.update_device_energy()

    items = list(self.api.sites.items())
    if items:
      site, site_data = items[0]

      # site, site_data = next(iter(self.api.sites.items()))
      ausgabe1 = []
      solarbank_info = site_data.get("solarbank_info")
      updated_time = solarbank_info.get("updated_time")
      to_home_load = solarbank_info.get("to_home_load")
      total_battery_power = solarbank_info.get("total_battery_power")
      solar_power_1 = solarbank_info.get("solar_power_1")
      solar_power_2 = solarbank_info.get("solar_power_2")
      solar_power_3 = solarbank_info.get("solar_power_3")
      solar_power_4 = solarbank_info.get("solar_power_4")
      total_photovoltaic_power = solarbank_info.get("total_photovoltaic_power")
      total_output_power = solarbank_info.get("total_output_power")

      ausgabe1.extend([["updated_time", updated_time]])
      ausgabe1.extend([["to_home_load", to_home_load]])
      ausgabe1.extend([["total_battery_power", total_battery_power]])
      ausgabe1.extend([["solar_power_1", solar_power_1]])
      ausgabe1.extend([["solar_power_2", solar_power_2]])
      ausgabe1.extend([["solar_power_3", solar_power_3]])
      ausgabe1.extend([["solar_power_4", solar_power_4]])
      ausgabe1.extend([["total_photovoltaic_power", total_photovoltaic_power]])
      ausgabe1.extend([["total_output_power", total_output_power]])

      energy_details = site_data.get("energy_details")
      energy_forecast = energy_details.get("pv_forecast_details")
      time_this_hour = energy_forecast.get("time_this_hour")
      trend_this_hour = energy_forecast.get("trend_this_hour")
      time_next_hour = energy_forecast.get("time_next_hour")
      trend_next_hour = energy_forecast.get("trend_next_hour")

      ausgabe2 = []
      ausgabe2.extend([["time_this_hour", time_this_hour]])
      ausgabe2.extend([["trend_this_hour", trend_this_hour]])
      ausgabe2.extend([["time_next_hour", time_next_hour]])
      ausgabe2.extend([["trend_next_hour", trend_next_hour]])

      # plot
      st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>Solarbank Info</div>",  unsafe_allow_html=True)
      st.dataframe(ausgabe1)

      st.markdown("<div style='font-size:15px;font-weight: bold;text-align: center;'>Energy Forecast</div>",  unsafe_allow_html=True)
      st.dataframe(ausgabe2)

      solix.sites.clear()
    else:
      st.warning("Keine Standorte verfügbar.")

async def create_session_and_update(user, pw, country):
  async with ClientSession() as session:
    a = AnkerSolixInfo(user, pw, country, session)
    await a.update_sites()

user = st.text_input("User")
pw = st.text_input("Passwort", type="password")
country = "DE"

if st.button("Anmelden"):
  try:
    asyncio.run(create_session_and_update(user, pw, country))
    st.success("Login erfolgreich!")
  except Exception as e:
    st.error(f"Anmeldefehler: {e}")
