import asyncio
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objs as go
import justetf_scraping
import math

import time

from selenium.common.exceptions import NoSuchElementException
import requests
from bs4 import BeautifulSoup

class ETFVergleichInteractive:
    def __init__(self):
        # Beispiel ETFs
        self.etfs = {
          "FR0010655712": {"name": "Amundi DAX UCITS ETF DR (V)"    , "url": "https://www.ariva.de/etf/amundi-etf-dax-ucits-etf-dr?utp=1"                              , "performance": -9999, "df": None},
          "DE0005190003": {"name": "BAY.MOTOREN WERKE AG ST"        , "url": "https://www.ariva.de/aktien/bmw-ag-st-aktie?utp=1"                                       , "performance": -9999, "df": None},
          "IE00B43HR379": {"name": "ISHSV-S+P500H.CA.SECT.DLA"      , "url": "https://www.ariva.de/etf/ishares-s-p-500-health-care-sector-ucits-etf-usd-acc?utp=1"     , "performance": -9999, "df": None},
          "IE00BMYDM794": {"name": "LGUE-HYDR.ECO. DLA"             , "url": "https://www.ariva.de/etf/l-g-hydrogen-economy-ucits-etf-usd-acc-etf?utp=1"               , "performance": -9999, "df": None},
          "IE00BYZK4552": {"name": "ISHS IV-AUTO.+ROBOTIC.ETF"      , "url": "https://www.ariva.de/etf/ishares-automation-robotics-ucits-etf-usd-acc?utp=1"            , "performance": -9999, "df": None},
          "IE00BM67HT60": {"name": "X(IE)-MSCI WO.IN.TE. 1CDL"      , "url": "https://www.ariva.de/etf/xtrackers-msci-world-information-technology-ucits-etf-1c?utp=1" , "performance": -9999, "df": None},
          "LU2611732046": {"name": "AIS AMUNDI DAX ETF DIST"        , "url": "https://www.ariva.de/etf/amundi-core-dax-ucits-etf-dist?utp=1"                           , "performance": -9999, "df": None},
          "LU0171307068": {"name": "BGF-WLD HEALTHSC.NA.A2EO"       , "url": "https://www.ariva.de/fonds/blackrock-global-funds-world-healthscience-fund-a2-eur/chart/chartanalyse"  , "performance": -9999, "df": None},
          "DE0008486655": {"name": "DWS CONCEPT GS+P FOOD LD"       , "url": "https://www.ariva.de/fonds/dws-concept-gs-p-food-ld?utp=1"                               , "performance": -9999, "df": None},
          "DE0008481763": {"name": "ALL.NEBENW.D A (EUR)"           , "url": "https://www.ariva.de/fonds/allianz-nebenwerte-deutschland-a-eur?utp=1"                   , "performance": -9999, "df": None},
          "FR0010135103": {"name": "CARMIGN.PATRIMOI. AEO ACC"      , "url": "https://www.ariva.de/fonds/carmignac-patrimoine-a-eur-acc?utp=1"                         , "performance": -9999, "df": None},
          "LU0055631609": {"name": "BGF-WORLD GOLD A2DL"            , "url": "https://www.ariva.de/fonds/blackrock-global-funds-world-gold-fund-a2-usd?utp=1"          , "performance": -9999, "df": None},
          "LU0323578657": {"name": "FLOSSB.V.STORCH-MUL.OPP.R"      , "url": "https://www.ariva.de/fonds/flossbach-von-storch-sicav-multiple-opportunities-r?utp=1"    , "performance": -9999, "df": None},
          "DE000SH9VRM6": {"name": "SGIS AKTANL PL 24/26 NVDA"      , "url": "https://www.ariva.de/zertifikate/SH9VRM?utp=1"                                           , "performance": -9999, "df": None},
          "IE0001UQQ933": {"name": "Kommer Fond"                    , "url": "https://www.ariva.de/etf/l-g-gerd-kommer-multifactor-equity-ucits-etf-usd-acc-etf?utp=1" , "performance": -9999, "df": None},
          "IE00B6R52259": {"name": "iShare MSCI ACWI"               , "url": "https://www.ariva.de/etf/ishares-msci-acwi-ucits-etf?utp=1"                              , "performance": -9999, "df": None}
        }
        self.fehler_isin = []
        self.df_comparison = pd.DataFrame()
        self.df_error      = pd.DataFrame()
        self.input_type    = "P"
        self.last_days     = 100
        self.title         = ""

    # -----------------------------
    # Funktion: Daten Laden
    # -----------------------------
    async def etf_load_data(self, last_days: int):
        self.last_days = last_days
        tasks = [asyncio.to_thread(self._load_single_etf, isin, meta) for isin, meta in self.etfs.items()]
        await asyncio.gather(*tasks)
        # Sortieren
        self.etfs_sorted = sorted(
          self.etfs.items(),
          key=lambda item: (-item[1]["performance"], item[1]["name"])
        )

    # -----------------------------
    # Funktion: ETF Laden
    # -----------------------------
    def _load_single_etf(self, isin, meta):
        try:
            df = justetf_scraping.load_chart(isin)
            df.index = pd.to_datetime(df.index)
            current_day = df.index.max()
            last_day = current_day - pd.DateOffset(days=self.last_days)
            df_filtered = df[(df.index >= last_day) & (df.index <= current_day)]
            if df_filtered.empty:
                self.fehler_isin.append([isin, meta["name"], meta["url"]])
                return
            meta["df"] = df_filtered.sort_index()
            meta["performance"] = (df_filtered["quote"].iloc[-1] / df_filtered["quote"].iloc[0] - 1) * 100
            meta["ETF"] = "OK"
            self.fehler_isin.append([isin, meta["name"], meta["url"], meta["ETF"]])
        except Exception:
            meta["ETF"] = ""
            self.fehler_isin.append([isin, meta["name"], meta["url"],meta["ETF"]])

    # -----------------------------
    # Funktion: Eingaben
    # -----------------------------
    async def etf_eingaben(self):
        # Auswahl Kennzahl
        input_type = st.radio(
            "Kennzahl",
            ["Kurs", "Relativert Kurs%", "Performance", "Volatilität", "Liste"],
            index=2,
            horizontal=True
        )
        mapping = {"Kurs": "K", "Relativert Kurs%": "R", "Performance": "P", "Volatilität": "V", "Liste": "F"}
        self.title = input_type
        self.input_type = mapping[input_type]

        # Auswahl ETFs
        options = [f"{isin} – {meta['name']}" for isin, meta in self.etfs_sorted]
        options.insert(0, "Alle")
        selected = st.multiselect("Wähle ETFs:", options, default="Alle")

        #self.title = "F"
        #self.input_type = "F"
        return selected

    # -----------------------------
    # Funktion: auslesen der Fond Daten
    # -----------------------------
    async def etf_read(self, selected):
        self.df_comparison = pd.DataFrame()
        for isin, meta in self.etfs_sorted:
            if meta["df"] is None:
                continue
            if "Alle" not in selected and f"{isin} – {meta['name']}" not in selected:
                continue
            series = self._prepare_series(meta)
            self.df_comparison[isin] = series

    # -----------------------------
    # Funktion: Berechnen der Diagramm Daten
    # -----------------------------
    def _prepare_series(self, meta):
        df = meta["df"]
        if self.input_type == "K":
            return df["quote"].astype(float)
        elif self.input_type == "R":
            return (df["quote"].pct_change() * 100).astype(float)
        elif self.input_type == "P":
            return (df["quote"] / df["quote"].iloc[0] * 100).astype(float)
        elif self.input_type == "V":
            return np.log(df["quote_with_reinvested_dividends"] / df["quote_with_reinvested_dividends"].shift(1)).dropna().astype(float)
        else:
            return pd.Series(dtype=float)

    # -----------------------------
    # Funktion: Selenium-Fonds-Infos auslesen
    # -----------------------------
    def _getKurs(self, soup, tag1, elem1, elem_name1, nr1, tag2, elem2, elem_name2, nr2, tag3, elem3, elem_name3, nr3, url):
      try:
        text = soup.find(tag1, {elem1: elem_name1}).text.replace("\t","").split("\n")[nr1]
        kurs = float(text.replace("%", "").replace("&nbsp;", "").replace("€", "").replace(",", ".").strip())
      except Exception as e:
        try:
          text = soup.find(tag2, {elem2: elem_name2}).text.replace("\t","").split("\n")[nr2]
          kurs = float(text.replace("%", "").replace("&nbsp;", "").replace("€", "").replace(",", ".").strip())
        except Exception as e:
          try:
            text = soup.find(tag3, {elem3: elem_name3}).text.replace("\t", "").split("\n")[nr3]
            kurs = float(text.replace("%", "").replace("&nbsp;", "").replace("€", "").replace(",", ".").strip())
          except Exception as e:
            kurs = None

      return kurs

    # -----------------------------
    # Funktion: Ermitteln Kurse
    # -----------------------------
    async def scrape_ariva_fund(self, url):
      headers = {"User-Agent": "Mozilla/5.0"}
      r = requests.get(url, headers=headers, timeout=10)
      r.raise_for_status()
      soup = BeautifulSoup(r.text, "html.parser")

      time.sleep(0.2)  # warten, bis JS geladen ist

      try:
        kurs       = self._getKurs(soup,"div","class","instrument-header-quote",  1,"table","class","line",4, "div","class","instrument-header-numbers",1,url)
        abs_change = self._getKurs(soup,"div","class","instrument-header-abs-change",  1,"table","class","line",6, "div","class","instrument-header-numbers",2,url)
        rel_change = self._getKurs(soup,"div","class","instrument-header-rel-change",  1,"table","class","line",8, "div","class","instrument-header-numbers",3,url)
      except Exception as e:
        kurs = abs_change = rel_change = None

      return kurs, abs_change, rel_change

    # -----------------------------
    # Funktion: Fehler Daten
    # -----------------------------
    async def data_error(self, selected):
      data = []
      for f in self.fehler_isin:
        isin = f[0]
        name = f[1]
        url  = f[2]
        etf  = f[3]
        if "Alle" not in selected and f"{isin} – {name}" not in selected:
            continue

        isin_color = "green" if etf == "OK" else "red"
        isin = f"<span style='color:{isin_color}'>{isin}</span>"
        # Test, ob eine URL vorhanden ist
        if len(url) > 10:
           kurs, abs_change, rel_change = await self.scrape_ariva_fund(url)
           isin = f'<a href="{url}" target="_blank">{isin}</a>'
        else:
           kurs, abs_change, rel_change, url = None, None, None, ""

        kurs_color = "#f1cd00"
        if isinstance(rel_change, (int, float)):
           kurs_color = "green" if rel_change > 0 else ("red" if rel_change < 0 else "#f1cd00")

        data.append({
            "ISIN": isin,
            "Name": name,
            "Kurs (EUR)": kurs,
            "Absoluter Tageswechsel (EUR)": f"<span style='color:{kurs_color}'>{abs_change}</span>",
            "Relativer Tageswechsel (%)":   f"<span style='color:{kurs_color}'>{rel_change}</span>",
        })

      # DataFrame erstellen
      data_sort = sorted(data, key=lambda x: x.get("Name", ""))
      self.df_error = pd.DataFrame(data_sort)

    # -----------------------------
    # Funktion: Ausgabe
    # -----------------------------
    async def etf_output(self,selected):
        if self.input_type == "F" or len(self.df_comparison.columns) == 0:
            await self.data_error(selected)
            # -----------------------------
            # Streamlit Anzeige
            # -----------------------------
            st.title("Fonds Übersicht")
            st.markdown("Aktuelle Kurse und Tageswechsel aus Ariva")
            st.markdown(self.df_error.to_html(escape=False, index=False), unsafe_allow_html=True)
            return

        # Interaktive Plotly Grafik
        fig = go.Figure()

        for isin in self.df_comparison.columns:
            name = self.etfs[isin]["name"]
            self.df_comparison[isin] = self.df_comparison[isin].round(2)
            fig.add_trace(go.Scatter(
              x=self.df_comparison.index,
              y=self.df_comparison[isin],
              #mode="lines+markers",
              mode="lines",
              name=f"{isin} – {name}",
              line=dict(width=1)  # dünnere Linie
            ))

        rot = 0 if self.last_days <= 25 else 15
        #Ein Tag = 86400000 Millisekunden.
        #Also Tage = 3 * 86400000 = 259200000.
        tage = math.ceil(self.last_days/15) * 86400000
        font = dict(size=12, color="black")
        font2 = dict(size=15, color="black")
        fig.update_xaxes(
          #dtick="D1",  # tägliche Ticks
          dtick=tage,  # alle 3 Tage
          tickformat="%d.%m.%Y",  # deutsches Datumsformat
          tickangle=rot,  # leichte Schrägstellung für bessere Lesbarkeit
          tickfont =font,
          #title_standoff=1,  # Abstand Achsentitel
          domain=[0, 1],  # Standard 0-1, nur sicherstellen
          automargin=True,
          showline = True
        )

        fig.update_yaxes(
          tickfont = font,
          title_standoff=0,  # Abstand Achsentitel
          #automargin=True,
          showline =True
        )

        fig.update_layout(
          margin=dict(l=2, r=2, t=30, b=2),  # l=left, r=right, t=top, b=bottom
          title=f"ETF-{self.title} – der letzten {self.last_days} Tage",
          #xaxis_title="Datum",
          yaxis_title=self.title,
          title_font=font2,   # Schriftgröße des Titels
          xaxis_title_font=font,  # X-Achsen-Label kleiner
          yaxis_title_font=font,  # Y-Achsen-Label kleiner
          height=600,
          hovermode="x unified",
          legend=dict(
            title=dict(
              text="ETFs",  # Titel der Legende
              font=font # Schriftart, Größe, Farbe
            ),
            font=font,   # Legende
            orientation="h",  # horizontal
            yanchor="top",  # Ausrichtung oben
            y=-0.12,  # Position etwas unterhalb der Grafik
            xanchor="center",
            x=0.45
          )
        )
        st.plotly_chart(fig, use_container_width=True)


# ----------------
# Streamlit Start
# ----------------
async def start():
    input_days = st.text_input("Anzahl Tage", value="100")
    last_days = int(input_days)
    etf_app = ETFVergleichInteractive()
    await etf_app.etf_load_data(last_days)
    selected = await etf_app.etf_eingaben()
    await etf_app.etf_read(selected)
    await etf_app.etf_output(selected)


asyncio.run(start())
