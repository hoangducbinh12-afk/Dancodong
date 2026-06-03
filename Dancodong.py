import streamlit as st
import json
import os

# 1. Cấu hình giao diện Mobile
st.set_page_config(page_title="Loto Cô Đọng V4.1", page_icon="💎", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0f172a; color: white; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5rem; background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); color: white; border: none; }
    .stTextInput>div>div>input { text-align: center; font-size: 22px; font-weight: bold; border-radius: 12px; background-color: #1e293b; color: #60a5fa; border: 1px solid #334155; }
    .final-card { background: #1e293b; padding: 20px; border-radius: 20px; border: 2px solid #a855f7; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); margin-top: 20px; text-align: center; }
    .final-label { font-size: 14px; font-weight: 800; color: #a855f7; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }
    .final-numbers { font-size: 28px; font-weight: 900; color: #ffffff; letter-spacing: 2px; line-height: 1.6; }
    .history-item { display: flex; align-items: center; justify-content: space-between; background: #1e293b; padding: 12px; border-radius: 12px; margin-bottom: 8px; border: 1px solid #334155; }
    .hist-num { font-size: 22px; font-weight: 900; color: #f8fafc; }
    .hist-status { font-size: 12px; font-weight: 700; color: #94a3b8; }
    </style>
""", unsafe_allow_html=True)

DATA_FILE = "data_master.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                d = json.load(f)
                return d.get("master_data", d), d.get("history", [])
            except: return {}, []
    return {}, []

def save_data(master, history):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"master_data": master, "history": history}, f, ensure_ascii=False)

if 'master_data' not in st.session_state:
    m, h = load_data()
    st.session_state.master_data, st.session_state.history = m, h

def callback_learning():
    actual = st.session_state.get("actual_in", "").strip()
    last_pred = st.session_state.get("last_condensed_list", [])
    if actual and st.session_state.get("last_t1"):
        act_num = actual.zfill(2)
        t1_old = st.session_state.last_t1
        
        # Cập nhật bạc nhớ
        m = st.session_state.master_data
        if t1_old not in m: m[t1_old] = {}
        m[t1_old][act_num] = m[t1_old].get(act_num, 0) + 1
        
        # Kiểm tra xem có nổ trong dàn cô đọng không
        status = "TRÚNG" if act_num in last_pred else "TRẬT"
        st.session_state.history.insert(0, {"num": act_num, "status": status})
        
        save_data(m, st.session_state.history)
        
        # Đảo kỳ (T-1 -> T-2, T-2 -> T-3)
        st.session_state["w_t3"] = st.session_state.get("w_t2", "")
        st.session_state["w_t2"] = t1_old
        st.session_state["w_t1"] = act_num
        st.session_state["actual_in"] = ""
        st.toast(f"Đã học số {act_num}!", icon="✅")

st.title("💎 LOTO CONDENSED V4.1")

with st.sidebar:
    st.header("⚙️ Dữ liệu")
    up = st.file_uploader("Nạp file JSON", type=["json"])
    if up:
        temp = json.load(up)
        st.session_state.master_data = temp.get("master_data", temp)
        st.session_state.history = temp.get("history", [])
        save_data(st.session_state.master_data, st.session_state.history)
        st.success("Đã đồng bộ!")
    st.download_button("📥 Tải dữ liệu", json.dumps({"master_data": st.session_state.master_data, "history": st.session_state.history}, ensure_ascii=False), "loto_condensed.json")

# Nhập liệu
c1, c2, c3 = st.columns(3)
with c3: t3_val = st.text_input("T-3", key="w_t3").zfill(2)
with c2: t2_val = st.text_input("T-2", key="w_t2").zfill(2)
with c1: t1_val = st.text_input("T-1", key="w_t1").zfill(2)

if st.button("🔍 CHIẾT XUẤT DÀN CÔ ĐỌNG"):
    if t1_val and t2_val and t3_val:
        m = st.session_state.master_data
        
        # B1: Lấy các số nổ sau từng thằng
        set1 = set(m.get(t1_val, {}).keys())
        set2 = set(m.get(t2_val, {}).keys())
        set3 = set(m.get(t3_val, {}).keys())
        
        # Dàn 1: Trùng cả 3 thằng
        dan1 = set1.intersection(set2).intersection(set3)
        
        # Dàn 2: Trùng T-1 và T-2
        dan2 = set1.intersection(set2)
        
        # Dàn 50: 50 số về nhiều nhất sau T-1
        t1_data = m.get(t1_val, {})
        dan50 = sorted(t1_data.keys(), key=lambda x: t1_data[x], reverse=True)[:50]
        dan50_set = set(dan50)
        
        # Dàn Sau Loại: Dàn 2 loại bỏ Dàn 1
        dan_sau_loai = dan2.difference(dan1)
        
        # KẾT QUẢ CUỐI CÙNG: Trùng giữa Dàn 50 và Dàn Sau Loại
        final_list = sorted(list(dan50_set.intersection(dan_sau_loai)))
        
        st.session_state.last_condensed_list = final_list
        st.session_state.last_t1 = t1_val
        
        # Hiển thị
        st.markdown(f"""
            <div class="final-card">
                <div class="final-label">💎 DÀN CÔ ĐỌNG (Số lượng: {len(final_list)})</div>
                <div class="final-numbers">{' - '.join(final_list) if final_list else "KHÔNG CÓ SỐ NÀO HỘI TỤ"}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Nhập đủ 3 kỳ để lọc!")

# Phần học số
if st.session_state.get("last_condensed_list") is not None:
    st.write("---")
    st.text_input("Kết quả nổ thực tế?", key="actual_in")
    st.button("💾 GHI NHẬN & TIẾP TỤC", on_click=callback_learning)

# Nhật ký
st.subheader("📋 Nhật ký nổ")
if st.session_state.history:
    for h in st.session_state.history[:15]:
        color = "#22c55e" if h['status'] == "TRÚNG" else "#ef4444"
        st.markdown(f"""
            <div class="history-item">
                <div class="hist-num">{h['num']}</div>
                <div class="hist-status" style="color: {color}">{h['status']}</div>
            </div>
        """, unsafe_allow_html=True)