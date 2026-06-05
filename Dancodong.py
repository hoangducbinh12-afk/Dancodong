import streamlit as st
import pandas as pd
import json
import numpy as np
import easyocr
from PIL import Image

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Matrix V9.8.0 - Pure Wire Sniper", layout="wide")
TOTAL_POS = 107 

st.markdown("""
    <style>
    .main { background-color: #0A0D14; padding: 10px; }
    .stButton>button { width: 100%; border-radius: 6px; height: 3.5em; background-color: #161B26; color: #F0F4F8; border: 1px solid #2D3748; font-weight: bold; }
    .stButton>button:hover { border-color: #FFD700; color: #FFD700; }
    
    .mobile-box-bt { background-color: #05070B; padding: 10px 5px; border-radius: 12px; text-align: center; border: 3px solid #EF4444; margin-bottom: 12px; overflow: hidden; box-shadow: 0px 4px 15px rgba(239,68,68,0.2); }
    .mobile-box-3 { background-color: #030508; padding: 10px 5px; border-radius: 12px; text-align: center; border: 3px solid #2563EB; margin-bottom: 12px; overflow: hidden; }
    .mobile-box-4 { background-color: #030508; padding: 10px 5px; border-radius: 12px; text-align: center; border: 3px solid #D97706; margin-bottom: 15px; overflow: hidden; }
    
    .mobile-text-bt { color: #FF1E27 !important; font-size: 11vw !important; font-weight: 900 !important; font-family: monospace; letter-spacing: 2px; margin: 0; line-height: 1.1; white-space: nowrap !important; }
    .mobile-text-3 { color: #FF1E27 !important; font-size: 8.5vw !important; font-weight: 900 !important; font-family: monospace; letter-spacing: 1px; margin: 0; line-height: 1.1; white-space: nowrap !important; }
    .mobile-text-4 { color: #FFD700 !important; font-size: 6.5vw !important; font-weight: 900 !important; font-family: monospace; letter-spacing: 1px; margin: 0; line-height: 1.1; white-space: nowrap !important; }
    </style>
    """, unsafe_allow_html=True)

if 'db' not in st.session_state:
    st.session_state['db'] = {
        "wire_scores": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "break_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "max_reached_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "over_1d_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "deep_break_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "last_digits": "",
        "last_loto": [],
        "history": [],
        "last_predictions": {},
        "core_four": [],
        "bach_thu": "",
        "gan_tracker": {str(i).zfill(2): 0 for i in range(100)},
        "bet_tracker": {str(i).zfill(2): 0 for i in range(100)},
        "total_hits": {str(i).zfill(2): 0 for i in range(100)}
    }
if 'raw_input' not in st.session_state: st.session_state['raw_input'] = ""

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

def check_and_fix_db_structure():
    db = st.session_state['db']
    for key in ["gan_tracker", "bet_tracker", "total_hits"]:
        if key not in db or not db[key]: db[key] = {str(i).zfill(2): 0 for i in range(100)}
    if "break_matrix" not in db: db["break_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()
    if "max_reached_matrix" not in db: db["max_reached_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()
    if "over_1d_matrix" not in db: db["over_1d_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()
    if "deep_break_matrix" not in db: db["deep_break_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()

def update_statistics(current_loto):
    check_and_fix_db_structure()
    db = st.session_state['db']
    for i in range(100):
        num = str(i).zfill(2)
        db['total_hits'][num] += current_loto.count(num)
        if num in current_loto:
            db['gan_tracker'][num] = 0
            db['bet_tracker'][num] += 1
        else:
            db['gan_tracker'][num] += 1
            db['bet_tracker'][num] = 0

# --- THUẬT TOÁN ĐÃ ĐƯỢC VÁ LỖI CHÍ MẠNG THEO ĐÚNG Ý MÀY ---
def get_filtered_power_score_4(new_wire_scores, current_digits):
    check_and_fix_db_structure()
    db = st.session_state['db']
    
    mapping_1d = {str(i).zfill(2): 0 for i in range(100)}
    coords_1 = np.argwhere(new_wire_scores == 1)
    for r, c in coords_1:
        num = current_digits[r] + current_digits[c]
        mapping_1d[num] += 1

    # BƯỚC 1: CHỈ TRÍCH XUẤT CÁC CON SỐ THUỘC DẢI DÂY 2Đ, 3Đ, 4Đ KỲ NÀY
    max_s = int(new_wire_scores.max())
    valid_wire_numbers = set()
    
    # Giới hạn trần dải điểm chỉ lấy từ 2đ đến 4đ (Chặn đứng >= 5đ từ vòng ngoài)
    target_max_s = min(4, max_s)
    if target_max_s >= 2:
        for s in range(2, target_max_s + 1):
            coords = np.argwhere(new_wire_scores == s)
            for r, c in coords:
                valid_wire_numbers.add(current_digits[r] + current_digits[c])

    # BƯỚC 2: THIẾT LẬP BỘ LỌC CHẶN TRONG PHẠM VI HẸP (CHỈ LỌC NHỮNG SỐ ĐÃ CHỌN)
    break_arr = np.array(db["break_matrix"])
    max_reached_arr = np.array(db["max_reached_matrix"])
    over_1d_arr = np.array(db["over_1d_matrix"])
    deep_break_arr = np.array(db["deep_break_matrix"])
    
    blacklist = set()
    
    # Quét bộ lọc dựa trên lịch sử dây
    for r in range(TOTAL_POS):
        for c in range(TOTAL_POS):
            num = current_digits[r] + current_digits[c]
            if num in valid_wire_numbers:
                # Lọc tỷ lệ đứt gãy %
                total_active = over_1d_arr[r][c] + break_arr[r][c]
                if total_active > 5:
                    if (break_arr[r][c] / total_active) * 100 >= 80.0:
                        blacklist.add(num)
                # Lọc cầu sập hầm
                if deep_break_arr[r][c] >= 2:
                    blacklist.add(num)
                # Lọc cầu ăn 1 lần rồi gãy (One-hit)
                if break_arr[r][c] > 0 and max_reached_arr[r][c] < 2:
                    blacklist.add(num)

    # Lọc các chỉ số cơ bản ngoài đời
    for num in list(valid_wire_numbers):
        if db['gan_tracker'][num] > 12: blacklist.add(num)
        if db['bet_tracker'][num] >= 2: blacklist.add(num)

    # BƯỚC 3: TÍNH ĐIỂM POWER SCORE VÀ XẾP HẠNG ĂN TIỀN
    power_map = {num: 0 for num in valid_wire_numbers if num not in blacklist}
    
    if target_max_s >= 2:
        for s in range(2, target_max_s + 1):
            coords = np.argwhere(new_wire_scores == s)
            for r, c in coords:
                num = current_digits[r] + current_digits[c]
                if num in power_map:
                    base_score = s ** 2
                    heat_bonus = 15 if 5 <= mapping_1d[num] <= 15 else 0
                    heat_penalty = -30 if mapping_1d[num] > 30 else 0
                    power_map[num] += (base_score + heat_bonus + heat_penalty)

    sorted_power = sorted(power_map.items(), key=lambda x: x[1], reverse=True)
    final_4 = [item[0] for item in sorted_power[:4] if item[1] > 0]
    
    # Cơ chế Fallback hồi sinh cứu trợ khẩn cấp nếu dải dây 2,3,4đ bị chém hết quân
    if len(final_4) < 4:
        for s in range(min(4, max_s), -1, -1):
            coords = np.argwhere(new_wire_scores == s)
            for r, c in coords:
                num = current_digits[r] + current_digits[c]
                if num not in final_4 and db['gan_tracker'][num] <= 12:
                    final_4.append(num)
                if len(final_4) >= 4: break
            if len(final_4) >= 4: break
            
    # AI CHỐT BẠCH THỦ TRONG TAM THỦ SẠCH V9.8.0
    tam_thu = final_4[:3]
    if tam_thu:
        bt_scores = {}
        for num in tam_thu:
            score_ai = 100
            for r in range(TOTAL_POS):
                for c in range(TOTAL_POS):
                    if current_digits[r] + current_digits[c] == num:
                        score_ai -= break_arr[r][c] * 2
                        score_ai += over_1d_arr[r][c] * 3
            if 5 <= mapping_1d[num] <= 15: score_ai += 25
            if db['bet_tracker'][num] == 0: score_ai += 15
            bt_scores[num] = score_ai
        db['bach_thu'] = max(bt_scores, key=bt_scores.get)
    else:
        db['bach_thu'] = ""
        
    return final_4[:4]

def process_matrix(current_digits, current_loto, gdb_val):
    check_and_fix_db_structure()
    db = st.session_state['db']
    update_statistics(current_loto)
    
    old_scores = np.array(db['wire_scores'], dtype=int)
    old_digits = db['last_digits']
    old_core_4 = db.get('core_four', [])
    old_bt = db.get('bach_thu', "")
    
    new_wire_scores = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int)
    break_arr = np.array(db["break_matrix"], dtype=int)
    max_reached_arr = np.array(db["max_reached_matrix"], dtype=int)
    over_1d_arr = np.array(db["over_1d_matrix"], dtype=int)
    deep_break_arr = np.array(db["deep_break_matrix"], dtype=int)
    
    hit_report = {"STT": len(db['history']) + 1, "GĐB": gdb_val}
    hit_report["Bạch Thủ"] = old_bt if old_bt else "Trống"
    
    if old_core_4:
        old_tam_thu = old_core_4[:3]
        found_3 = [n for n in old_tam_thu if n in current_loto]
        count_3 = sum([current_loto.count(n) for n in found_3])
        found_4 = [n for n in old_core_4 if n in current_loto]
        count_4 = sum([current_loto.count(n) for n in found_4])
        
        hit_report["Dàn 3q"] = f"{count_3} ({','.join(found_3) if found_3 else '0'})"
        hit_report["Dàn 4q"] = f"{count_4} ({','.join(found_4) if found_4 else '0'})"
        
        if old_bt and old_bt in current_loto: hit_report["Result"] = "🔥 Win BT 🔥"
        elif count_3 >= 1 or gdb_val in old_tam_thu: hit_report["Result"] = "🎯 Win Tam Thủ"
        elif count_4 >= 1: hit_report["Result"] = "✅ Ăn Lót"
        else: hit_report["Result"] = "❌ Loss"
            
    if len(old_digits) == TOTAL_POS:
        for i in range(TOTAL_POS):
            for j in range(TOTAL_POS):
                num_past = old_digits[i] + old_digits[j]
                if num_past in current_loto:
                    new_wire_scores[i][j] = old_scores[i][j] + 1
                    if new_wire_scores[i][j] > max_reached_arr[i][j]: max_reached_arr[i][j] = new_wire_scores[i][j]
                    if new_wire_scores[i][j] >= 2: over_1d_arr[i][j] += 1
                else:
                    if old_scores[i][j] >= 1: 
                        break_arr[i][j] += 1
                        if old_scores[i][j] >= 2: deep_break_arr[i][j] += 1
                    new_wire_scores[i][j] = 0

    db['wire_scores'] = new_wire_scores.tolist()
    break_arr = np.where(break_arr > 50, 50, break_arr) # Khóa chặn chống tràn số thô lịch sử dài ngày
    db['break_matrix'] = break_arr.tolist()
    db['max_reached_matrix'] = max_reached_arr.tolist()
    db['over_1d_matrix'] = over_1d_arr.tolist()
    db['deep_break_matrix'] = deep_break_arr.tolist()
    db['last_digits'] = current_digits
    db['last_loto'] = current_loto
    db['core_four'] = get_filtered_power_score_4(new_wire_scores, current_digits)
    db['history'].insert(0, hit_report)

# --- 3. GIAO DIỆN SIÊU TỐI GIẢN MOBILE V9.8.0 ---
st.markdown("<h2 style='text-align: center; color: #E2E8F0; font-weight: bold; font-size: 1.5rem;'>⚡ MATRIX MASTER V9.8.0</h2>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 💾 DATA SYSTEM")
    uploaded_file = st.file_uploader("Nạp JSON", type=['json'])
    if uploaded_file and st.button("📥 PHỤC HỒI MA TRẬN"):
        st.session_state['db'] = json.load(uploaded_file)
        check_and_fix_db_structure()
        st.rerun()
    if st.session_state['db']['last_digits']:
        st.download_button("💾 XUẤT FILE JSON", json.dumps(st.session_state['db']), "matrix_v980.json")
    
    st.divider()
    st.markdown("### 📸 OCR CAMERA")
    uploaded_img = st.file_uploader("Chọn ảnh kết quả", type=['jpg', 'png', 'jpeg'])
    if uploaded_img and st.button("QUÉT ẢNH"):
        reader = load_ocr()
        res = reader.readtext(np.array(Image.open(uploaded_img)), detail=0)
        nums = [n for n in res if n.isdigit() and 2 <= len(n) <= 5]
        if nums: 
            st.session_state['raw_input'] = ", ".join(nums)
            st.session_state['gdb_ocr'] = nums[0][-2:]
        st.rerun()

    st.session_state['raw_input'] = st.text_area("Bảng kết quả thô:", value=st.session_state.get('raw_input', ""), height=100)
    gdb_val = st.text_input("Đặc biệt (2 số):", value=st.session_state.get('gdb_ocr', ""), max_chars=2)

    if st.button("🔥 CHẠY SNIPER MOBILE", type="primary"):
        raw = [x.strip() for x in st.session_state['raw_input'].replace(",", " ").split() if x]
        if len("".join(raw)) >= TOTAL_POS:
            process_matrix("".join(raw)[:TOTAL_POS], [s[-2:] for s in raw[:27]], gdb_val)
            st.rerun()
    st.button("🚨 XÓA BẢNG TẠM", on_click=lambda: st.session_state.clear())

# --- BẢNG 1: HIỂN THỊ DỰ ĐOÁN ---
st.markdown("<h3><font color='#FF1E27'><b>🎯 TỌA ĐỘ PHÁT LỰC</b></font></h3>", unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #FF1E27; margin-top: -5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

c4 = st.session_state['db'].get('core_four', [])
bt = st.session_state['db'].get('bach_thu', "")

if c4:
    if bt:
        st.markdown(f"""<div class="mobile-box-bt"><span style="color: #FF5555; font-size: 12px; font-weight: bold;">👑 BẠCH THỦ ASSASSIN AI</span><br><p class="mobile-text-bt"><b>{bt}</b></p></div>""", unsafe_allow_html=True)
    tam_thu_str = ' - '.join(c4[:3])
    st.markdown(f"""<div class="mobile-box-3"><span style="color: #94A3B8; font-size: 12px; font-weight: bold;">🔥 TAM THỦ CHỦ LỰC</span><br><p class="mobile-text-3"><b>{tam_thu_str}</b></p></div>""", unsafe_allow_html=True)
    tu_thu_str = ' - '.join(c4)
    st.markdown(f"""<div class="mobile-box-4"><span style="color: #94A3B8; font-size: 12px; font-weight: bold;">🎯 TỨ THỦ CHIẾN THUẬT</span><br><p class="mobile-text-4"><b>{tu_thu_str}</b></p></div>""", unsafe_allow_html=True)
else:
    st.info("Đang chờ tích lũy xung nhịp kỳ kế tiếp.")

# --- BẢNG 2: LỊCH SỬ ĐỐI SOÁT WIN/LOSS ---
st.markdown("<h3><font color='#FF1E27'><b>📋 LỊCH SỬ ĐỐI SOÁT KẾT QUẢ</b></font></h3>", unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #FF1E27; margin-top: -5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

if st.session_state['db']['history']:
    df_hist = pd.DataFrame(st.session_state['db']['history']).fillna("0")
    cols = list(df_hist.columns)
    important = ["Result", "Bạch Thủ", "Dàn 3q", "Dàn 4q", "GĐB", "STT"]
    for col in reversed(important):
        if col in cols: cols.insert(0, cols.pop(cols.index(col)))
    
    if "Result" in df_hist.columns:
        st.dataframe(
            df_hist[cols].style.map(
                lambda x: 'color: #FF1E27; font-weight: 900' if x == "🔥 Win BT 🔥" else 
                          ('color: #F59E0B; font-weight: bold' if x == "🎯 Win Tam Thủ" else 
                          ('color: #10B981; font-weight: bold' if x == "✅ Ăn Lót" else 
                          ('color: #718096' if x == "❌ Loss" else ''))),
                subset=["Result"]
            ),
            use_container_width=True, height=550
        )
    else:
        st.dataframe(df_hist[cols], use_container_width=True, height=550)
else:
    st.dataframe(pd.DataFrame(columns=["Result", "Bạch Thủ", "Dàn 3q", "Dàn 4q", "GĐB", "STT"]), use_container_width=True, height=150)
