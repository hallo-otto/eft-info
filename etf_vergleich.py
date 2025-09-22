import asyncio
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objs as go
import justetf_scraping
import math

class ETFVergleichInteractive:
    def __init__(self):
        # Beispiel ETFs
        self.etfs = {
          "FR0010655712": {"name": "Amundi DAX UCITS ETF DR (V)"    , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BD4TXV59": {"name": "UBS Core MSCI World UCITS (V)"  , "ticker": ""        , "performance": -9999, "df": None},
          "DE0005190003": {"name": "BAY.MOTOREN WERKE AG ST"        , "ticker": ""        , "performance": -9999, "df": None},
          "IE00B43HR379": {"name": "ISHSV-S+P500H.CA.SECT.DLA"      , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BMYDM794": {"name": "LGUE-HYDR.ECO. DLA"             , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BYZK4552": {"name": "ISHS IV-AUTO.+ROBOTIC.ETF"      , "ticker": ""        , "performance": -9999, "df": None},
          "IE00BM67HT60": {"name": "X(IE)-MSCI WO.IN.TE. 1CDL"      , "ticker": ""        , "performance": -9999, "df": None},
          "LU2611732046": {"name": "AIS AMUNDI DAX ETF DIST"        , "ticker": ""        , "performance": -9999, "df": None},
          "LU0171307068": {"name": "BGF-WLD HEALTHSC.NA.A2EO"       , "ticker": ""        , "performance": -9999, "df": None},
          "DE0008486655": {"name": "DWS CONCEPT GS+P FOOD LD"       , "ticker": ""        , "performance": -9999, "df": None},
          "DE0008481763": {"name": "ALL.NEBENW.D A (EUR)"           , "ticker": "ALND.DE" , "performance": -9999, "df": None},
          "FR0010135103": {"name": "CARMIGN.PATRIMOI. AEO ACC"      , "ticker": ""        , "performance": -9999, "df": None},
          "LU0055631609": {"name": "BGF-WORLD GOLD A2DL"            , "ticker": "MI9C.F"  , "performance": -9999, "df": None},
          "LU0323578657": {"name": "FLOSSB.V.STORCH-MUL.OPP.R"      , "ticker": ""        , "performance": -9999, "df": None},
          "DE000SH9VRM6": {"name": "SGIS AKTANL PL 24/26 NVDA"      , "ticker": ""        , "performance": -9999, "df": None},
          "IE0001UQQ933": {"name": "Kommer Fond"                    , "ticker": ""        , "performance": -9999, "df": None},
          "IE00B6R52259": {"name": "iShare MSCI ACWI"               , "ticker": ""        , "performance": -9999, "df": None}
        }
        self.fehler_isin = []
        self.df_comparison = pd.DataFrame()
        self.input_type  = "P"
        self.last_days   = 100
        self.title       = ""

    async def etf_load_data(self, last_days: int):
        self.last_days = last_days
        tasks = [asyncio.to_thread(self._load_single_etf, isin, meta) for isin, meta in self.etfs.items()]
        await asyncio.gather(*tasks)

    def _load_single_etf(self, isin, meta):
        try:
            df = justetf_scraping.load_chart(isin)
            df.index = pd.to_datetime(df.index)
            current_day = df.index.max()
            last_day = current_day - pd.DateOffset(days=self.last_days)
            df_filtered = df[(df.index >= last_day) & (df.index <= current_day)]
            if df_filtered.empty:
                self.fehler_isin.append([isin, meta["name"]])
                return
            meta["df"] = df_filtered.sort_index()
            meta["performance"] = (df_filtered["quote"].iloc[-1] / df_filtered["quote"].iloc[0] - 1) * 100
        except Exception:
            self.fehler_isin.append([isin, meta["name"]])

    async def etf_eingaben(self):
        # Auswahl Kennzahl
        input_type = st.radio(
            "Kennzahl",
            ["Kurs", "Relativert Kurs%", "Performance", "Volatilität", "Fehler Liste"],
            index=2,
            horizontal=True
        )
        mapping = {"Kurs": "K", "Relativert Kurs%": "R", "Performance": "P", "Volatilität": "V", "Fehler Liste": "F"}
        self.title = input_type
        self.input_type = mapping[input_type]

        # Auswahl ETFs
        options = [f"{isin} – {meta['name']}" for isin, meta in self.etfs.items()]
        options.insert(0, "Alle")
        selected = st.multiselect("Wähle ETFs:", options, default="Alle")
        return selected

    async def etf_read(self, selected):
        self.df_comparison = pd.DataFrame()
        for isin, meta in self.etfs.items():
            if meta["df"] is None:
                continue
            if "Alle" not in selected and f"{isin} – {meta['name']}" not in selected:
                continue
            series = self._prepare_series(meta)
            self.df_comparison[isin] = series

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

    async def etf_output(self):
        if self.input_type == "F":
            if self.fehler_isin:
                df_errors = pd.DataFrame(self.fehler_isin, columns=["ISIN", "Name"])
                st.markdown("<div style='font-size:15px;font-weight:bold;text-align:center;'>Nicht in justETF vorhanden</div>", unsafe_allow_html=True)
                st.dataframe(df_errors)
            return

        # Interaktive Plotly Grafik
        fig = go.Figure()
        for isin in self.df_comparison.columns:
            name = self.etfs[isin]["name"]
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
    await etf_app.etf_output()


asyncio.run(start())
