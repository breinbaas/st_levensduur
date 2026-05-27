from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt


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
            # df = df[(df["l"] >= -1 * m_naar_boezem) & (df["l"] <= m_naar_polder)]
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

    combined_df_breedte = combined_df.copy()

    # bereken achtergrondzetting
    combined_df = combined_df[
        (combined_df["l"] >= -1 * m_naar_boezem) & (combined_df["l"] <= m_naar_polder)
    ]
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
        and "z3" in combined_df.columns
        and "z4" in combined_df.columns
        and "z5" in combined_df.columns
    ):
        z3_l0 = combined_df[combined_df["l"] == 0][["c", "z3"]].rename(
            columns={"z3": "z3_l0"}
        )
        z4_l0 = combined_df[combined_df["l"] == 0][["c", "z4"]].rename(
            columns={"z4": "z4_l0"}
        )
        z5_l0 = combined_df[combined_df["l"] == 0][["c", "z5"]].rename(
            columns={"z5": "z5_l0"}
        )
    else:
        z3_l0 = None
        z4_l0 = None
        z5_l0 = None

    # Aggregate all rows based on 'c' to get the average
    if "c" in combined_df.columns:
        combined_df = combined_df.groupby("c").mean(numeric_only=True).reset_index()

        # Override averaged z5 with the values at l == 0
        if z3_l0 is not None:
            combined_df = pd.merge(combined_df, z3_l0, on="c", how="left")
            combined_df["z3"] = combined_df["z3_l0"]
            combined_df = combined_df.drop(columns=["z3_l0"])
        if z4_l0 is not None:
            combined_df = pd.merge(combined_df, z4_l0, on="c", how="left")
            combined_df["z4"] = combined_df["z4_l0"]
            combined_df = combined_df.drop(columns=["z4_l0"])
        if z5_l0 is not None:
            combined_df = pd.merge(combined_df, z5_l0, on="c", how="left")
            combined_df["z5"] = combined_df["z5_l0"]
            combined_df = combined_df.drop(columns=["z5_l0"])

    # Remove column l
    combined_df = combined_df.drop(columns=["l"], errors="ignore")

    return combined_df, combined_df_breedte


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
        combined_df, combined_df_breedte = handle_csv_uploads(
            uploaded_files, m_naar_boezem, m_naar_polder
        )
        if combined_df is not None and combined_df_breedte is not None:
            st.session_state["combined_df"] = combined_df
            st.session_state["combined_df_breedte"] = combined_df_breedte
    else:
        st.warning("Please select at least one CSV file before clicking Upload.")

# Display data if it exists in session state
if "combined_df" and "combined_df_breedte" in st.session_state:
    combined_df = st.session_state["combined_df"]
    combined_df_breedte = st.session_state["combined_df_breedte"]

    st.subheader("Gecombineerde AHN data")
    st.info(
        "Het onderstaande dataframe is als csv te downloaden voor eigen verwerking, gebruik hiervoor de Download als CSV optie in het menu dat naar voren komt als je over de data scrollt."
    )
    st.dataframe(combined_df, use_container_width=True)

    z_cols = [col for col in ["z3", "z4", "z5"] if col in combined_df.columns]
    if z_cols:
        st.subheader("Hoogtes (z3, z4, z5) per meetpunt (c)")
        df_hoogte_melted = combined_df.melt(
            id_vars=["c"],
            value_vars=z_cols,
            var_name="Hoogte",
            value_name="Waarde",
        )
        selection_hoogte = alt.selection_point(fields=["Hoogte"], bind="legend")
        chart_hoogte = (
            alt.Chart(df_hoogte_melted)
            .mark_line()
            .encode(
                x=alt.X("c:Q", title="c"),
                y=alt.Y("Waarde:Q", title="Hoogte (m)", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "Hoogte:N",
                    scale=alt.Scale(
                        domain=["z3", "z4", "z5"],
                        range=["#1f77b4", "#ff7f0e", "black"],
                    ),
                ),
                opacity=alt.condition(selection_hoogte, alt.value(1), alt.value(0.2)),
            )
            .add_params(selection_hoogte)
        )
        st.altair_chart(chart_hoogte, use_container_width=True)

    st.subheader("Zettingen (z54, z43, z53) per meetpunt (c)")
    st.info(
        "Gebruik de onderstaande grafiek om de achtergrondzetting te kiezen die je voor de levensduur analyse wilt gebruiken."
    )
    st.warning(
        "Negatieve zetting (zwel) wordt op 1mm zetting per jaar gezet, zetting > 30mm per jaar wordt op het maximum van 30mm gezet."
    )

    df_melted = combined_df.melt(
        id_vars=["c"],
        value_vars=["z54", "z43", "z53"],
        var_name="Zetting",
        value_name="Waarde",
    )
    selection = alt.selection_point(fields=["Zetting"], bind="legend")
    chart = (
        alt.Chart(df_melted)
        .mark_line()
        .encode(
            x=alt.X("c:Q", title="c"),
            y=alt.Y("Waarde:Q", title="Zetting (m/jaar)"),
            color=alt.Color(
                "Zetting:N",
                scale=alt.Scale(
                    domain=["z54", "z43", "z53"],
                    range=["#1f77b4", "#ff7f0e", "black"],
                ),
            ),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        )
        .add_params(selection)
    )
    st.altair_chart(chart, use_container_width=True)

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
            m_naar_boezem_hoogte = st.number_input(
                "m naar boezem t.o.v. referentielijn", value=4.0, step=0.5
            )
            zettings_factor = st.number_input("Zettingsfactor:", value=1.4, step=0.1)
        with col2:
            c_interval = st.number_input(
                "Interval voor berekening levensduur (m):",
                min_value=10,
                max_value=250,
                value=10,
                step=5,
            )
            m_naar_polder_hoogte = st.number_input(
                "m naar polder t.o.v. referentielijn", value=4.0, step=0.5
            )
            planperiodes = [
                int(s)
                for s in st.multiselect(
                    "Planperiodes:",
                    options=["5", "10", "15", "20", "25", "30"],
                    default=["5", "10", "15", "20", "25", "30"],
                )
            ]

        bereken_submitted = st.form_submit_button("Bereken levensduur")

    if bereken_submitted:
        st.header(planperiodes)

        import numpy as np

        results_z5_breedte = []
        for c_val, group in combined_df_breedte.groupby("c"):
            # Filter on l within boundaries
            mask = (group["l"] >= -m_naar_boezem_hoogte) & (
                group["l"] <= m_naar_polder_hoogte
            )
            filtered = group[mask].sort_values("l").reset_index(drop=True)

            z5_breedte_val = np.nan
            if len(filtered) >= 4:
                # Find the highest 4 consecutive points by their sum
                rolling_sum = filtered["z5"].rolling(window=4).sum()

                # dropna removes windows that contain NaN values
                valid_sums = rolling_sum.dropna()

                if not valid_sums.empty:
                    # Get index of the max sum
                    max_idx = valid_sums.idxmax()
                    # The 4 consecutive points end at max_idx
                    highest_4 = filtered.loc[max_idx - 3 : max_idx, "z5"]
                    # Take the lowest value of z5 from those highest points
                    z5_breedte_val = highest_4.min()

            results_z5_breedte.append({"c": c_val, "z5_breedte": z5_breedte_val})

        df_z5_breedte = pd.DataFrame(results_z5_breedte)

        # Combine with combined_df
        combined_df
        if "z5_breedte" in combined_df.columns:
            combined_df = combined_df.drop(columns=["z5_breedte"])
        combined_df = pd.merge(combined_df, df_z5_breedte, on="c", how="left")

        current_year = datetime.now().year

        # calculate z_huidig_jaar voor de breedte
        setting_map = combined_df.set_index("c")[gekozen_zetting]

        combined_df_breedte = combined_df_breedte[
            (combined_df_breedte["c"] >= start_metrering)
            & (combined_df_breedte["c"] <= end_metrering)
        ]

        combined_df_breedte[f"z_{current_year}"] = combined_df_breedte["z5"] - (
            current_year - AHN5
        ) * combined_df_breedte["c"].map(setting_map)

        st.header(
            "Debug data - ter controle van de hoogte bepaling over de breedte van de  dijk."
        )
        st.dataframe(combined_df_breedte)

        ref_label = f"z_{current_year}_ref"
        ref_label_breedte = f"z_{current_year}_breedte"

        combined_df[ref_label] = (
            combined_df["z5"] - (current_year - AHN5) * combined_df[gekozen_zetting]
        )
        combined_df["z_rest_ref"] = combined_df[ref_label] - afkeur_hoogte
        combined_df[ref_label_breedte] = (
            combined_df["z5_breedte"]
            - (current_year - AHN5) * combined_df[gekozen_zetting]
        )
        combined_df["z_rest_breedte"] = combined_df[ref_label_breedte] - afkeur_hoogte

        for periode in planperiodes:
            # benodigde ophoging over de referentielijn
            title = f"oph_{periode}_ref"
            combined_df[title] = np.where(
                combined_df[gekozen_zetting] > 0,
                (
                    (afkeur_hoogte + periode * combined_df[gekozen_zetting])
                    - combined_df["z_2026_ref"]
                )
                * zettings_factor,
                np.nan,
            )
            combined_df.loc[combined_df[title] < 0, title] = 0

            # benodigde ophoging over de breedte van de dijk
            title = f"oph_{periode}_breedte"
            combined_df[title] = np.where(
                combined_df[gekozen_zetting] > 0,
                (
                    (afkeur_hoogte + periode * combined_df[gekozen_zetting])
                    - combined_df["z_2026_breedte"]
                )
                * zettings_factor,
                np.nan,
            )
            combined_df.loc[combined_df[title] < 0, title] = 0

        # Calculate levensduur safely
        combined_df["levensduur_ref"] = np.where(
            combined_df[gekozen_zetting] > 0,
            combined_df["z_rest_ref"] / combined_df[gekozen_zetting],
            np.nan,
        )
        combined_df.loc[combined_df["levensduur_ref"] < 0, "levensduur_ref"] = 0.0
        combined_df.loc[combined_df["levensduur_ref"] > 30, "levensduur_ref"] = 30.0

        combined_df["levensduur_breedte"] = np.where(
            combined_df[gekozen_zetting] > 0,
            combined_df["z_rest_breedte"] / combined_df[gekozen_zetting],
            np.nan,
        )
        combined_df.loc[combined_df["levensduur_breedte"] < 0, "levensduur_breedte"] = (
            0.0
        )
        combined_df.loc[
            combined_df["levensduur_breedte"] > 30, "levensduur_breedte"
        ] = 30.0

        # Calculate levensduur per interval of c (lowest value, in multiples of 5)
        combined_df["c_bin_ref"] = (combined_df["c"] // c_interval) * c_interval
        bin_min = combined_df.groupby("c_bin_ref")["levensduur_ref"].transform("min")
        combined_df["levensduur_5y_ref"] = (bin_min // 5) * 5

        combined_df["c_bin_breedte"] = (combined_df["c"] // c_interval) * c_interval
        bin_min = combined_df.groupby("c_bin_breedte")["levensduur_breedte"].transform(
            "min"
        )
        combined_df["levensduur_5y_breedte"] = (bin_min // 5) * 5

        # Update the dataframe in session state
        st.session_state["combined_df"] = combined_df

        st.info(
            "Je kunt dit dataframe downloaden in csv formaat voor eventuele eigen berekeningen. Gebruik de Download als CSV knop in het menu dat verschijnt als je over de data scrollt"
        )
        st.dataframe(combined_df, use_container_width=True)

        st.info("De onderstaande grafieken vatten de belangrijkste resultaten samen.")

        # Create chart for Zetting
        df_zetting_melt = combined_df.melt(
            id_vars=["c"],
            value_vars=[ref_label, ref_label_breedte],
            var_name="Type",
            value_name="Hoogte",
        )
        name_ref_zetting = f"Hoogte {current_year} (ref)"
        name_breedte_zetting = f"Hoogte {current_year} (breedte)"
        df_zetting_melt["Type"] = df_zetting_melt["Type"].replace(
            {ref_label: name_ref_zetting, ref_label_breedte: name_breedte_zetting}
        )

        selection_zetting = alt.selection_point(fields=["Type"], bind="legend")

        lines_zetting = (
            alt.Chart(df_zetting_melt)
            .mark_line()
            .encode(
                x=alt.X("c:Q", title="c"),
                y=alt.Y("Hoogte:Q", title="Huidige hoogte (m)"),
                color=alt.Color(
                    "Type:N",
                    title="Legenda",
                    scale=alt.Scale(
                        domain=[name_ref_zetting, name_breedte_zetting],
                        range=["blue", "green"],
                    ),
                ),
                strokeDash=alt.StrokeDash(
                    "Type:N",
                    title="Legenda",
                    scale=alt.Scale(
                        domain=[name_ref_zetting, name_breedte_zetting],
                        range=[[1, 0], [5, 5]],
                    ),
                ),
                opacity=alt.condition(selection_zetting, alt.value(1), alt.value(0.2)),
            )
            .add_params(selection_zetting)
            .properties(title=f"Hoogte in {current_year}")
        )

        hline = (
            alt.Chart(pd.DataFrame({"y": [afkeur_hoogte]}))
            .mark_rule(strokeDash=[5, 5], color="orange")
            .encode(y="y:Q")
        )

        st.altair_chart(lines_zetting + hline, use_container_width=True)

        # Create chart for Zettingssnelheid
        df_snelheid = combined_df[["c", gekozen_zetting]].copy()
        name_snelheid = f"Snelheid ({gekozen_zetting})"
        df_snelheid["Type"] = name_snelheid

        selection_snelheid = alt.selection_point(fields=["Type"], bind="legend")

        chart_snelheid = (
            alt.Chart(df_snelheid)
            .mark_line()
            .encode(
                x=alt.X("c:Q", title="c"),
                y=alt.Y(f"{gekozen_zetting}:Q", title="Snelheid (m/jaar)"),
                color=alt.Color(
                    "Type:N", title="Legenda", scale=alt.Scale(range=["green"])
                ),
                opacity=alt.condition(selection_snelheid, alt.value(1), alt.value(0.2)),
            )
            .add_params(selection_snelheid)
            .properties(title=f"Gebruikte Zettingssnelheid ({gekozen_zetting})")
        )

        st.altair_chart(chart_snelheid, use_container_width=True)

        # Create chart for Levensduur
        df_levensduur_melt = combined_df.melt(
            id_vars=["c"],
            value_vars=["levensduur_5y_ref", "levensduur_5y_breedte"],
            var_name="Type",
            value_name="Levensduur",
        )

        name_ref_levensduur = f"Levensduur (ref)"
        name_breedte_levensduur = f"Levensduur (breedte)"

        df_levensduur_melt["Type"] = df_levensduur_melt["Type"].replace(
            {
                "levensduur_5y_ref": name_ref_levensduur,
                "levensduur_5y_breedte": name_breedte_levensduur,
            }
        )

        selection_levensduur = alt.selection_point(fields=["Type"], bind="legend")

        chart_levensduur = (
            alt.Chart(df_levensduur_melt)
            .mark_line(interpolate="step-after")
            .encode(
                x=alt.X("c:Q", title="c"),
                y=alt.Y(
                    "Levensduur:Q",
                    title="Levensduur (jaren)",
                    scale=alt.Scale(domain=[0, 35]),
                ),
                color=alt.Color(
                    "Type:N",
                    title="Legenda",
                    scale=alt.Scale(
                        domain=[name_ref_levensduur, name_breedte_levensduur],
                        range=["red", "green"],
                    ),
                ),
                strokeDash=alt.StrokeDash(
                    "Type:N",
                    title="Legenda",
                    scale=alt.Scale(
                        domain=[name_ref_levensduur, name_breedte_levensduur],
                        range=[[1, 0], [5, 5]],
                    ),
                ),
                opacity=alt.condition(
                    selection_levensduur, alt.value(1), alt.value(0.2)
                ),
            )
            .add_params(selection_levensduur)
            .properties(title="Berekende Levensduur")
        )

        st.altair_chart(chart_levensduur, use_container_width=True)

        st.info(
            "Hieronder zijn indicatieve grafieken van de benodigde ophoging per planperiode ."
        )
        for periode in planperiodes:
            title_ref = f"oph_{periode}_ref"
            title_breedte = f"oph_{periode}_breedte"

            # Binning logic for ophoging (max value per interval, rounded up to multiples of 0.1)
            combined_df["c_bin"] = (combined_df["c"] // c_interval) * c_interval

            bin_max_ref = combined_df.groupby("c_bin")[title_ref].transform("max")
            title_ref_binned = f"oph_{periode}_ref_binned"
            combined_df[title_ref_binned] = np.ceil(bin_max_ref * 10) / 10

            bin_max_breedte = combined_df.groupby("c_bin")[title_breedte].transform(
                "max"
            )
            title_breedte_binned = f"oph_{periode}_breedte_binned"
            combined_df[title_breedte_binned] = np.ceil(bin_max_breedte * 10) / 10

            df_ophoging_melt = combined_df.melt(
                id_vars=["c"],
                value_vars=[title_ref_binned, title_breedte_binned],
                var_name="Type",
                value_name="Ophoging",
            )
            name_ref_oph = f"Ophoging (ref)"
            name_breedte_oph = f"Ophoging (breedte)"
            df_ophoging_melt["Type"] = df_ophoging_melt["Type"].replace(
                {title_ref_binned: name_ref_oph, title_breedte_binned: name_breedte_oph}
            )

            selection_oph = alt.selection_point(fields=["Type"], bind="legend")

            chart_oph = (
                alt.Chart(df_ophoging_melt)
                .mark_line(interpolate="step-after")
                .encode(
                    x=alt.X("c:Q", title="c"),
                    y=alt.Y("Ophoging:Q", title="Benodigde ophoging (m)"),
                    color=alt.Color(
                        "Type:N",
                        title="Legenda",
                        scale=alt.Scale(
                            domain=[name_ref_oph, name_breedte_oph],
                            range=["blue", "green"],
                        ),
                    ),
                    strokeDash=alt.StrokeDash(
                        "Type:N",
                        title="Legenda",
                        scale=alt.Scale(
                            domain=[name_ref_oph, name_breedte_oph],
                            range=[[1, 0], [5, 5]],
                        ),
                    ),
                    opacity=alt.condition(selection_oph, alt.value(1), alt.value(0.2)),
                )
                .add_params(selection_oph)
                .properties(
                    title=f"Benodigde ophoging voor planperiode van {periode} jaar"
                )
            )

            st.altair_chart(chart_oph, use_container_width=True)
