import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# 🔄 รีเฟรชทุก 10 วินาที (10000 มิลลิวินาที)
st_autorefresh(interval=500, key="data_refresh")

# 🔗 ข้อมูลจาก Google Sheets
sheet_id = "1ZDYycnq6unLkxelJIrZ_yQjKXadJfnSLZzoJ96KjQKw"
sheet_name = "test%20dashboard"  # ถ้ามี space ให้ใช้ %20 แทน
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

# 📥 โหลดข้อมูล
try:
    df = pd.read_csv(csv_url)
    st.title("อยากให้เก็บใน googlesheet ได้จัง")
    st.success("โหลดข้อมูลสำเร็จ ✅")
    st.dataframe(df)

    # ✅ ตัวอย่างการแสดงกราฟถ้ามีคอลัมน์ชื่อ 'วันที่' และ 'ยอดขาย'
    if 'วันที่' in df.columns and 'ยอดขาย' in df.columns:
        df['วันที่'] = pd.to_datetime(df['วันที่'], errors='coerce')
        df = df.dropna(subset=['วันที่'])
        df = df.sort_values('วันที่')
        st.line_chart(df.set_index("วันที่")["ยอดขาย"])
    else:
        st.info("เพิ่มคอลัมน์ 'วันที่' และ 'ยอดขาย' เพื่อแสดงกราฟ")

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
