from datetime import datetime
import streamlit as st
import pandas as pd


AHN3 = 2015
AHN4 = 2020
AHN5 = 2023

st.set_page_config(page_title="CSV Uploader", page_icon="📁", layout="wide")


def handle_csv_uploads(uploaded_files, m_naar_boezem, m_naar_polder):
    import re

    combined_df = None

    # Iterate through the uploaded files and combine them
    for file in uploaded_files:
        try:
            # Read the CSV file
            df = pd.read_csv(file)
            df = df[(df["l"] >= -1 * m_naar_boezem) & (df["l"] <= m_naar_polder)]
            df = df.reset_index(drop=True)

            # Determine the new column name for z based on the filename
            match = re.search(r"ahn(\d+)", file.name.lower())
            z_col_name = (
                f"z{match.group(1)}" if match else f'z_{file.name.split(".")[0]}'
            )

            if combined_df is None:
                combined_df = df
                if "z" in combined_df.columns:
                    combined_df = combined_df.rename(columns={"z": z_col_name})
            else:
                if "z" in df.columns:
                    combined_df[z_col_name] = df["z"]

        except Exception as e:
            st.error(f"Error processing {file.name}: {e}")

    # bereken achtergrondzetting
    combined_df = combined_df[
        (combined_df["c"] >= start_metrering) & (combined_df["c"] <= end_metrering)
    ]
    combined_df["z54"] = (combined_df["z4"] - combined_df["z5"]) / (AHN5 - AHN4)
    combined_df["z43"] = (combined_df["z3"] - combined_df["z4"]) / (AHN4 - AHN3)
    combined_df["z53"] = (combined_df["z3"] - combined_df["z5"]) / (AHN5 - AHN3)
    combined_df.loc[combined_df["z54"] < 0, "z54"] = 0.001
    combined_df.loc[combined_df["z43"] < 0, "z43"] = 0.001
    combined_df.loc[combined_df["z53"] < 0, "z53"] = 0.001
    combined_df.loc[combined_df["z54"] > 0.03, "z54"] = 0.03
    combined_df.loc[combined_df["z43"] > 0.03, "z43"] = 0.03
    combined_df.loc[combined_df["z53"] > 0.03, "z53"] = 0.03

    # Extract z5 values where l == 0
    if (
        "c" in combined_df.columns
        and "l" in combined_df.columns
        and "z5" in combined_df.columns
    ):
        z5_l0 = combined_df[combined_df["l"] == 0][["c", "z5"]].rename(
            columns={"z5": "z5_l0"}
        )
    else:
        z5_l0 = None

    # Aggregate all rows based on 'c' to get the average
    if "c" in combined_df.columns:
        combined_df = combined_df.groupby("c").mean(numeric_only=True).reset_index()

        # Override averaged z5 with the values at l == 0
        if z5_l0 is not None:
            combined_df = pd.merge(combined_df, z5_l0, on="c", how="left")
            combined_df["z5"] = combined_df["z5_l0"]
            combined_df = combined_df.drop(columns=["z5_l0"])

    # Remove columns z4, z3, l
    combined_df = combined_df.drop(columns=["z4", "z3", "l"], errors="ignore")

    return combined_df


st.title("Levensduur bepaling")

st.markdown(
    """
    Bepaal de achtergrondzetting o.b.v. AHN gegevens over een gewenste breedte van de dijk en gebruik deze achtergrondzetting
    om een indruk te krijgen van de levensduur van de dijk wat de hoogte betreft.
    """
)

# Create a form to upload files
with st.form("upload_form"):
    st.info("Kies de breedte om de achtergrondzetting over de dijk te berekenen.")

    st.warning(
        "Zet de invoer op 0 m naar boezem en 0 m naar de polder om de zetting op de referentielijn te krijgen."
    )
    col1, col2 = st.columns(2)
    with col1:
        m_naar_boezem = st.number_input(
            "m naar boezem t.o.v. referentielijn", value=1.0, step=0.5
        )
    with col2:
        m_naar_polder = st.number_input(
            "m naar polder t.o.v. referentielijn", value=2.0, step=0.5
        )

    st.info(
        "Kies de start en eind metrering en de afkeurhoogte om het gewenste dijkdeel te bekijken."
    )
    col3, col4, col5 = st.columns(3)
    with col3:
        start_metrering = st.number_input("start metrering", value=0)
    with col4:
        end_metrering = st.number_input("eind metrering", value=9999)
    with col5:
        afkeur_hoogte = st.number_input("afkeurhoogte", value=0.1)

    st.info("Kies de csv bestanden met AHN data.")
    uploaded_files = st.file_uploader(
        "Choose CSV files", type="csv", accept_multiple_files=True
    )

    # Form submit button
    submitted = st.form_submit_button("Analyseer")


# Handle the form submission
if submitted:
    if uploaded_files:
        st.success(f"Successfully uploaded {len(uploaded_files)} file(s)!")
        combined_df = handle_csv_uploads(uploaded_files, m_naar_boezem, m_naar_polder)
        if combined_df is not None:
            st.session_state["combined_df"] = combined_df
    else:
        st.warning("Please select at least one CSV file before clicking Upload.")

# Display data if it exists in session state
if "combined_df" in st.session_state:
    combined_df = st.session_state["combined_df"]

    st.subheader("Gecombineerde AHN data")
    st.info(
        "Het onderstaande dataframe is als csv te downloaden voor eigen verwerking, gebruik hiervoor de Download als CSV optie in het menu dat naar voren komt als je over de data scrollt."
    )
    st.dataframe(combined_df, use_container_width=True)

    st.subheader("Zettingen (z54, z43, z53) per meetpunt (c)")
    st.info(
        "Gebruik de onderstaande grafiek om de achtergrondzetting te kiezen die je voor de levensduur analyse wilt gebruiken."
    )
    st.warning(
        "Negatieve zetting (zwel) wordt op 1mm zetting per jaar gezet, zetting > 30mm per jaar wordt op het maximum van 30mm gezet."
    )

    st.line_chart(combined_df, x="c", y=["z54", "z43", "z53"])

    with st.form("levensduur_form"):
        st.info(
            "Kies hier de te gebruiken achtergrondzetting en het interval voor de metrering waarover de levensduur berekend moet worden (de levensduur wordt in stukjes dijklengte bepaald om te voorkomen dat er teveel lokale verschillen komen)."
        )

        col1, col2 = st.columns(2)

        with col1:
            gekozen_zetting = st.radio(
                "Kies de zettingswaarde voor verdere berekeningen:",
                options=["z54", "z43", "z53"],
                index=2,
                horizontal=True,
            )
        with col2:
            c_interval = st.number_input(
                "Interval voor berekening levensduur (m):",
                min_value=10,
                max_value=250,
                value=50,
                step=5,
            )
        bereken_submitted = st.form_submit_button("Bereken levensduur")

    if bereken_submitted:
        import numpy as np
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        current_year = datetime.now().year
        combined_df[f"z_{current_year}"] = (
            combined_df["z5"] - (current_year - AHN5) * combined_df[gekozen_zetting]
        )
        combined_df["z_rest"] = combined_df[f"z_{current_year}"] - afkeur_hoogte

        # Calculate levensduur safely
        combined_df["levensduur"] = np.where(
            combined_df[gekozen_zetting] > 0,
            combined_df["z_rest"] / combined_df[gekozen_zetting],
            np.nan,
        )
        combined_df.loc[combined_df["levensduur"] < 0, "levensduur"] = 0.0
        combined_df.loc[combined_df["levensduur"] > 30, "levensduur"] = 30.0

        # Calculate levensduur per interval of c (lowest value, in multiples of 5)
        combined_df["c_bin"] = (combined_df["c"] // c_interval) * c_interval
        bin_min = combined_df.groupby("c_bin")["levensduur"].transform("min")
        combined_df["levensduur_5y"] = (bin_min // 5) * 5

        # Update the dataframe in session state
        st.session_state["combined_df"] = combined_df

        st.info(
            "Je kunt dit dataframe downloaden in csv formaat voor eventuele eigen berekeningen. Gebruik de Download als CSV knop in het menu dat verschijnt als je over de data scrollt"
        )
        st.dataframe(combined_df, use_container_width=True)

        st.info("De onderstaande grafieken vatten de belangrijkste resultaten samen.")
        # Create chart for Zetting
        fig_zetting = go.Figure()
        fig_zetting.add_trace(
            go.Scatter(
                x=combined_df["c"],
                y=combined_df[f"z_{current_year}"],
                name=f"Zetting {current_year}",
                mode="lines",
                line=dict(color="blue"),
            )
        )
        # Add dotted line for afkeur_hoogte
        fig_zetting.add_hline(
            y=afkeur_hoogte,
            line_dash="dot",
            line_color="orange",
            annotation_text="Afkeurhoogte",
        )
        fig_zetting.update_layout(title=f"Hoogte in {current_year}")
        fig_zetting.update_yaxes(title_text="Huidige hoogte (m)")

        st.plotly_chart(fig_zetting, use_container_width=True)

        # Create chart for Zettingssnelheid
        fig_snelheid = go.Figure()
        fig_snelheid.add_trace(
            go.Scatter(
                x=combined_df["c"],
                y=combined_df[gekozen_zetting],
                name=f"Snelheid ({gekozen_zetting})",
                mode="lines",
                line=dict(color="green"),
            )
        )
        fig_snelheid.update_layout(
            title=f"Gebruikte Zettingssnelheid ({gekozen_zetting})"
        )
        fig_snelheid.update_yaxes(title_text="Snelheid (m/jaar)")

        st.plotly_chart(fig_snelheid, use_container_width=True)

        # Create chart for Levensduur
        fig_levensduur = go.Figure()
        fig_levensduur.add_trace(
            go.Scatter(
                x=combined_df["c"],
                y=combined_df["levensduur_5y"],
                name=f"Levensduur (min per {c_interval}m)",
                mode="lines",
                line=dict(color="red", shape="hv"),
            )
        )
        fig_levensduur.update_layout(title="Berekende Levensduur")
        fig_levensduur.update_yaxes(title_text="Levensduur (jaren)", range=[0, 35])

        st.plotly_chart(fig_levensduur, use_container_width=True)

        # Combine the three plots for download
        fig_combined = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            subplot_titles=(
                f"Hoogte in {current_year}",
                f"Gebruikte Zettingssnelheid ({gekozen_zetting})",
                "Berekende Levensduur",
            ),
            vertical_spacing=0.1,
        )

        # 1. Zetting
        fig_combined.add_trace(
            go.Scatter(
                x=combined_df["c"],
                y=combined_df[f"z_{current_year}"],
                name=f"Hoogte {current_year}",
                line=dict(color="blue"),
            ),
            row=1,
            col=1,
        )
        fig_combined.add_hline(
            y=afkeur_hoogte, line_dash="dot", line_color="orange", row=1, col=1
        )

        # 2. Snelheid
        fig_combined.add_trace(
            go.Scatter(
                x=combined_df["c"],
                y=combined_df[gekozen_zetting],
                name=f"Achtergrondzetting ({gekozen_zetting})",
                line=dict(color="green"),
            ),
            row=2,
            col=1,
        )

        # 3. Levensduur
        fig_combined.add_trace(
            go.Scatter(
                x=combined_df["c"],
                y=combined_df["levensduur_5y"],
                name=f"Levensduur (min per {c_interval}m)",
                line=dict(color="red", shape="hv"),
            ),
            row=3,
            col=1,
        )

        fig_combined.update_yaxes(title_text="Hoogte (m)", row=1, col=1)
        fig_combined.update_yaxes(title_text="Snelheid (m/jr)", row=2, col=1)
        fig_combined.update_yaxes(
            title_text="Levensduur (jr)", range=[0, 35], row=3, col=1
        )

        fig_combined.update_layout(
            height=800, title_text="Rapportage Levensduurberekening"
        )

        # Convert to PNG for download
        png_bytes = fig_combined.to_image(format="png", width=1200, height=800)

        st.info(
            "Optioneel kun je met de onderstaande knop de grafieken als 1 plaatje downloaden."
        )
        st.download_button(
            label="Download Rapportage Grafieken (PNG)",
            data=png_bytes,
            file_name="levensduur_rapportage.png",
            mime="image/png",
        )
