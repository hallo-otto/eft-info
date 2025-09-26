import asyncio
from tplinkcloud import TPLinkDeviceManager
import pandas as pd
import streamlit as st

class Kasa_Devices:
    def __init__(self):
        self.devices = None

    async def logon(self,user, pw):
        # TPLinkCloud-Verbindung
        try:
            device_manager = TPLinkDeviceManager(user, pw)
            self.devices = await device_manager.get_devices()
            if (len(self.devices) == 0): return False
        except Exception as e:
            return False
        return True

    def ausgabe(self):
        data = []
        # Auslesen Devices
        for device in self.devices:
            info = device.device_info
            #print(f"Gerät:  {info.device_model} {info.alias})")
            data.append({
                "Modell": info.device_model,
                "Alias": info.alias,
                "Name": info.device_name,
                "Type": info.device_type
            })

        # Sortieren
        data_sorted = sorted(data, key=lambda item: item.get("Alias"))
        df = pd.DataFrame(data_sorted)
        st.markdown(
            "<style>table th {text-align: left !important;</style>",
            unsafe_allow_html=True
        )
        title = "KASA Devices"
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
        d = Kasa_Devices()
        if not await d.logon(user, pw):
            st.error(f"❌ Anmeldefehler")
            return
        d.ausgabe()
     except Exception as e:
        st.error(f"❌ Anmeldefehler1: {e}")



async def start_test():
    d = Kasa_Devices()
    await d.logon("hallo.otto123.oo@gmail.com", "kasa#196")
    d.ausgabe()

asyncio.run(start())