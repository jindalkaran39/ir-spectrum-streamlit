import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from io import BytesIO
import json

st.title("IR Spectrum Generator")
st.write("Upload a CSV or Excel file with Wavenumber (cm⁻¹) and Transmittance (%T) data")

uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])

st.sidebar.header("Peak Labeling Options")
show_labels = st.sidebar.checkbox("Enable Peak Labels", value=True)
label_offset_default = st.sidebar.slider("Default Vertical Offset", 1.0, 20.0, 5.0)
manual_peaks_enabled = st.sidebar.checkbox("Manually Adjust Label Positions", value=False)
max_peaks = st.sidebar.slider("Maximum Number of Labels", 1, 100, 25)


def parse_file(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    elif file.name.endswith(".xlsx"):
        df = pd.read_excel(file)
    else:
        raise ValueError("Unsupported file type")

    df = df.apply(pd.to_numeric, errors='coerce')
    df.dropna(inplace=True)

    if df.shape[1] >= 2:
        df.columns = ["Wavenumber", "Transmittance"] + list(df.columns[2:])
    else:
        raise ValueError("File must have at least two columns of numeric data.")

    return df


def plot_ir(df, label_positions):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["Wavenumber"], df["Transmittance"], color="darkblue")
    ax.invert_xaxis()
    ax.set_xlabel("Wavenumber (cm⁻¹)")
    ax.set_ylabel("% Transmittance")
    ax.set_title("IR Spectrum")
    ax.grid(True)

    if show_labels and label_positions:
        for i, (wn, offset) in enumerate(label_positions):
            tr = df.loc[df["Wavenumber"].sub(wn).abs().idxmin(), "Transmittance"]
            ax.annotate(f"{wn:.2f}", xy=(wn, tr), xytext=(wn, tr - offset),
                        ha="center", fontsize=8, color="red",
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="red", lw=0.5))

    st.pyplot(fig)

    buf = BytesIO()
    fig.savefig(buf, format="pdf")
    st.download_button(
        label="Download PDF",
        data=buf,
        file_name="ir_spectrum_labeled.pdf",
        mime="application/pdf"
    )

    return label_positions

if uploaded_file:
    try:
        df = parse_file(uploaded_file)
        label_positions = []

        if show_labels:
            peaks, _ = find_peaks(-df["Transmittance"], distance=30, prominence=1.0)
            selected_peaks = df.iloc[peaks].copy()
            selected_peaks = selected_peaks.sort_values("Wavenumber", ascending=False).head(max_peaks)

            st.subheader("Detected Peaks")
            st.write(selected_peaks[["Wavenumber", "Transmittance"]])

            if manual_peaks_enabled:
                st.subheader("Adjust Label Positions")
                for index, row in selected_peaks.iterrows():
                    wn = float(row["Wavenumber"])
                    offset = st.sidebar.slider(f"Offset for {wn:.2f} cm⁻¹", 1.0, 20.0, label_offset_default, key=f"offset_{wn}")
                    label_positions.append((wn, offset))
            else:
                label_positions = [(float(row["Wavenumber"]), label_offset_default) for _, row in selected_peaks.iterrows()]

        plotted_labels = plot_ir(df, label_positions)

        if st.button("Generate Spectra with Peak Labels"):
            json_data = [
                {"x": wn, "y": float(df.loc[df["Wavenumber"].sub(wn).abs().idxmin(), "Transmittance"]), "label": f"{wn:.2f}"}
                for wn, _ in plotted_labels
            ]
            st.download_button(
                label="Download Peak Labels JSON",
                data=json.dumps(json_data, indent=2),
                file_name="peaks.json",
                mime="application/json"
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")