import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# ---------- CONFIG ---------- #
SHEET_NAME = "StockPortfolioApp"
WORKSHEET_NAME = "Sheet1"
JSON_KEYFILE = "gsheets_key.json"

# ---------- AUTH & LOAD GOOGLE SHEET ---------- #
@st.cache_resource
def load_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, scope)
    client = gspread.authorize(creds)
    worksheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    return worksheet

worksheet = load_sheet()

# ---------- FUNCTIONS ---------- #
def load_data():
    try:
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except:
        return pd.DataFrame(columns=["วันที่", "ชื่อหุ้น", "ประเภท", "จำนวนหุ้น", "ราคาต่อหุ้น", "มูลค่ารวม"])

def save_data(df):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def summarize_portfolio(df):
    df_buy = df[df["ประเภท"] == "ซื้อ"]
    summary = df_buy.groupby("ชื่อหุ้น").agg(
        จำนวนหุ้นรวม=("จำนวนหุ้น", "sum"),
        ต้นทุนรวม=("มูลค่ารวม", "sum"),
    )
    summary["ต้นทุนเฉลี่ย"] = summary["ต้นทุนรวม"] / summary["จำนวนหุ้นรวม"]
    summary["สัดส่วน %"] = (summary["ต้นทุนรวม"] / summary["ต้นทุนรวม"].sum()) * 100
    return summary.reset_index()

# ---------- INITIALIZE SESSION ---------- #
if "data" not in st.session_state:
    st.session_state["data"] = load_data()

# ---------- UI ---------- #
st.set_page_config(page_title="จัดการพอร์ตหุ้น", layout="wide")
tab = st.sidebar.radio("เมนู", ["📊 ภาพรวมพอร์ต", "📝 บันทึกรายการ", "🔍 ค้นหาหุ้น"])

# ---------- PAGE: ภาพรวมพอร์ต ---------- #
if tab == "📊 ภาพรวมพอร์ต":
    st.header("ภาพรวมพอร์ตหุ้น")
    df = st.session_state["data"]

    if df.empty:
        st.info("ยังไม่มีข้อมูลในพอร์ต")
    else:
        summary = summarize_portfolio(df)
        total = summary["ต้นทุนรวม"].sum()

        col1, col2 = st.columns(2)
        with col1:
            fig, ax = plt.subplots()
            ax.pie(summary["ต้นทุนรวม"], labels=summary["ชื่อหุ้น"], autopct='%1.1f%%')
            st.pyplot(fig)

        with col2:
            st.metric("จำนวนหุ้น", summary.shape[0])
            st.metric("มูลค่าพอร์ต", f"${total:,.2f}")

        st.dataframe(summary, use_container_width=True)

# ---------- PAGE: บันทึกรายการ ---------- #
elif tab == "📝 บันทึกรายการ":
    st.header("บันทึกการซื้อขายหุ้น")

    with st.form("form_add"):
        col1, col2, col3 = st.columns(3)
        with col1:
            stock = st.text_input("ชื่อหุ้น (เช่น AAPL)").upper()
        with col2:
            qty = st.number_input("จำนวน", min_value=1)
        with col3:
            price = st.number_input("ราคาต่อหุ้น", min_value=0.01)

        col4, col5 = st.columns(2)
        with col4:
            ttype = st.selectbox("ประเภท", ["ซื้อ", "ขาย"])
        with col5:
            tdate = st.date_input("วันที่", value=date.today())

        submitted = st.form_submit_button("บันทึก")
        if submitted and stock:
            total = qty * price
            new_row = {"วันที่": str(tdate), "ชื่อหุ้น": stock, "ประเภท": ttype,
                       "จำนวนหุ้น": qty, "ราคาต่อหุ้น": price, "มูลค่ารวม": total}
            df = st.session_state["data"].append(new_row, ignore_index=True)
            st.session_state["data"] = df
            save_data(df)
            st.success("✅ บันทึกเรียบร้อยแล้ว!")

    st.subheader("รายการทั้งหมด")
    st.dataframe(st.session_state["data"], use_container_width=True)

# ---------- PAGE: ค้นหาหุ้น ---------- #
elif tab == "🔍 ค้นหาหุ้น":
    st.header("ค้นหาข้อมูลหุ้นรายตัว")
    search = st.text_input("กรอกชื่อหุ้น (เช่น AAPL)").upper()
    df = st.session_state["data"]

    if search:
        filtered = df[df["ชื่อหุ้น"] == search]
        if filtered.empty:
            st.warning("ไม่พบข้อมูลหุ้นนี้")
        else:
            summary = summarize_portfolio(filtered)
            st.metric("จำนวนหุ้นคงเหลือ", int(summary['จำนวนหุ้นรวม'].iloc[0]))
            st.metric("ราคาต้นทุนเฉลี่ย", f"${summary['ต้นทุนเฉลี่ย'].iloc[0]:.2f}")
            st.metric("ต้นทุนรวม", f"${summary['ต้นทุนรวม'].iloc[0]:.2f}")
            st.metric("สัดส่วนในพอร์ต", f"{summary['สัดส่วน %'].iloc[0]:.2f}%")

            st.subheader("ประวัติการทำรายการ")
            st.dataframe(filtered, use_container_width=True)
