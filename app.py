import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import altair as alt

st.set_page_config(layout="wide")
st_autorefresh(interval=5000, key="auto_refresh")

# ----------------- ดึงข้อมูลจาก Google Sheet -----------------
sheet_id = "1bCpfnaNO2ofLVqFysHW0vHQy78pYMuFCfb4EjIWznEw"
sheet_name = "modbus%20data"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

try:
    df = pd.read_csv(csv_url)

    # ตรวจสอบและเปลี่ยนชื่อคอลัมน์ Time -> Timestamp
    if "Time" in df.columns:
        df.rename(columns={"Time": "Timestamp"}, inplace=True)

    # ตรวจสอบว่ามีคอลัมน์ Timestamp หรือไม่
    if "Timestamp" not in df.columns:
        st.error("ไม่พบคอลัมน์ Timestamp ในข้อมูล")
        st.stop()

    df['Timestamp'] = pd.to_datetime(df['Timestamp'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Timestamp'])

    df["DateOnly"] = df["Timestamp"].dt.date
    available_dates = sorted(df["DateOnly"].unique(), reverse=True)

    if not available_dates:
        st.error("ไม่พบข้อมูลวันใน Google Sheet")
        st.stop()

    selected_date = st.sidebar.date_input(
        "📅 เลือกวันที่",
        value=available_dates[0],
        min_value=min(available_dates),
        max_value=max(available_dates),
    )

    df_filtered = df[df["DateOnly"] == selected_date]

    # ----------------- กำหนดจำนวน Node -----------------
    with st.sidebar.expander("🔢 กำหนดจำนวน Node", expanded=True):
        if "node_count" not in st.session_state:
            st.session_state.node_count = 2

        node_count = st.number_input(
            "จำนวน Node ทั้งหมด",
            min_value=1,
            max_value=60,
            value=st.session_state.node_count,
            step=1,
        )
        st.session_state.node_count = node_count

    # ----------------- สร้าง Node -----------------
    if "nodes" not in st.session_state:
        st.session_state.nodes = {}

    existing_nodes = list(st.session_state.nodes.keys())
    for node in existing_nodes:
        node_num = int(node.split()[1])
        if node_num > st.session_state.node_count:
            st.session_state.nodes.pop(node)
            if "temp_settings" in st.session_state:
                st.session_state.temp_settings.pop(node, None)
            if "selected_nodes" in st.session_state:
                st.session_state.selected_nodes = [
                    n for n in st.session_state.selected_nodes if n != node
                ]

    for i in range(1, st.session_state.node_count + 1):
        node_name = f"Node {i:02d}"
        if node_name not in st.session_state.nodes:
            st.session_state.nodes[node_name] = [f"Node{i}A", f"Node{i}B", f"Node{i}C"]

    # ----------------- เลือก Node -----------------
    with st.sidebar.expander("🔘 เลือก Node ที่จะแสดง", expanded=True):
        if "selected_nodes" not in st.session_state:
            st.session_state.selected_nodes = list(st.session_state.nodes.keys())

        selected_nodes = st.multiselect(
            "เลือก Node ที่จะแสดง",
            options=list(st.session_state.nodes.keys()),
            default=st.session_state.selected_nodes,
            key="multiselect_nodes",
        )
        st.session_state.selected_nodes = selected_nodes

        if st.button("🗑️ ลบ Node ที่เลือก"):
            for node in selected_nodes:
                st.session_state.nodes.pop(node, None)
                st.session_state.temp_settings.pop(node, None)
                if node in st.session_state.selected_nodes:
                    st.session_state.selected_nodes.remove(node)
            st.experimental_rerun()

    # ----------------- ตั้งค่าอุณหภูมิ -----------------
    with st.sidebar.expander("⚙️ ตั้งค่าอุณหภูมิ Node", expanded=True):
        if "temp_settings" not in st.session_state:
            st.session_state.temp_settings = {
                node: {"high": 60, "over": 80} for node in st.session_state.nodes
            }

        for node in st.session_state.nodes:
            if node not in st.session_state.temp_settings:
                st.session_state.temp_settings[node] = {"high": 60, "over": 80}

        setting_node = st.selectbox("เลือก Node ที่ต้องการตั้งค่า", list(st.session_state.nodes.keys()))
        high_temp = st.number_input(
            "High Temp (°C)",
            value=st.session_state.temp_settings[setting_node]["high"],
            key=f"high_{setting_node}",
        )
        over_temp = st.number_input(
            "Over Temp (°C)",
            value=st.session_state.temp_settings[setting_node]["over"],
            key=f"over_{setting_node}",
        )
        st.session_state.temp_settings[setting_node]["high"] = high_temp
        st.session_state.temp_settings[setting_node]["over"] = over_temp

    # ----------------- Main Title -----------------
    st.title("📊 Temperature Monitor Dashboard")

    def render_temp_bar(temp, max_temp=125):
        percent = min(100, int(temp / max_temp * 100))
        st.progress(percent)
        st.write(f"{temp}°C")

    if "graph_state" not in st.session_state:
        st.session_state.graph_state = {}

    # ----------------- Style -----------------
    st.markdown(
        """
        <style>
            .node-box { background-color: #dcd6f7; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
            .alert-high { color: white; background-color: orange; padding: 3px 8px; border-radius: 5px; }
            .alert-over { color: white; background-color: red; padding: 3px 8px; border-radius: 5px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for node_name, columns in st.session_state.nodes.items():
        if node_name not in st.session_state.selected_nodes:
            continue

        if not all(col in df.columns for col in columns):
            st.warning(f"{node_name}: ไม่มีข้อมูลคอลัมน์ {columns}")
            continue

        if df_filtered.empty:
            st.info(f"{node_name}: ไม่มีข้อมูลในวันที่ {selected_date}")
            continue

        latest = df_filtered.sort_values("Timestamp", ascending=False).iloc[0]
        temps = [latest[col] for col in columns]

        high = st.session_state.temp_settings[node_name]["high"]
        over = st.session_state.temp_settings[node_name]["over"]

        alert_style = ""
        if any(t >= over for t in temps):
            alert_style = "alert-over"
        elif any(t >= high for t in temps):
            alert_style = "alert-high"

        with st.container():
            st.markdown("<div class='node-box'>", unsafe_allow_html=True)
            if alert_style:
                st.markdown(
                    f"<strong>{node_name}:</strong> <span class='{alert_style}'>! {'OVER' if alert_style == 'alert-over' else 'HIGH'} TEMP !</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**{node_name}:**")

            cols = st.columns([1, 1, 1, 0.5])
            for i, temp in enumerate(temps):
                with cols[i]:
                    st.write(f"{chr(65+i)}")
                    render_temp_bar(temp)

            with cols[3]:
                if st.button("📈", key=f"btn_{node_name}"):
                    st.session_state.graph_state[node_name] = not st.session_state.graph_state.get(node_name, False)

            if st.session_state.graph_state.get(node_name, False):
                chart_data = df_filtered[["Timestamp"] + columns].dropna().sort_values("Timestamp")
                melted_df = chart_data.melt(
                    id_vars=["Timestamp"], value_vars=columns, var_name="Phase", value_name="Temperature"
                )

                min_temp = melted_df["Temperature"].min() - 5
                max_temp = melted_df["Temperature"].max() + 5

                chart = (
                    alt.Chart(melted_df)
                    .mark_line()
                    .encode(
                        x=alt.X("Timestamp:T", title="เวลา", axis=alt.Axis(format="%H:%M")),
                        y=alt.Y("Temperature:Q", title="อุณหภูมิ (°C)", scale=alt.Scale(domain=[min_temp, max_temp])),
                        color="Phase:N",
                    )
                    .properties(width="container", height=300, title=f"กราฟแสดงอุณหภูมิ: {node_name}")
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
