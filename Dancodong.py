import streamlit as st
import pandas as pd
import json
import numpy as np
import easyocr
from PIL import Image

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="Matrix V9.5.4 - Sniper Core Master", layout="wide")
TOTAL_POS = 107 

# Custom CSS khóa chết giao diện tối, ép số trên 1 hàng duy nhất cho Mobile
st.markdown("""
    <style>
    .main { background-color: #0A0D14; padding: 10px; }
    .stButton>button { width: 100%; border-radius: 6px; height: 3.5em; background-color: #161B26; color: #F0F4F8; border: 1px solid #2D3748; font-weight: bold; }
    .stButton>button:hover { border-color: #FFD700; color: #FFD700; }
    .stExpander { border: 1px solid #1E293B; background-color: #0A0D14; border-radius: 8px; }
    
    .mobile-box-3 { background-color: #030508; padding: 12px 5px; border-radius: 12px; text-align: center; border: 3px solid #2563EB; margin-bottom: 12px; overflow: hidden; }
    .mobile-box-4 { background-color: #030508; padding: 12px 5px; border-radius: 12px; text-align: center; border: 3px solid #D97706; margin-bottom: 15px; overflow: hidden; }
    
    .mobile-text-3 { color: #FF1E27 !important; font-size: 10vw !important; font-weight: 900 !important; font-family: monospace; letter-spacing: 1px; margin: 0; line-height: 1.1; white-space: nowrap !important; }
    .mobile-text-4 { color: #FFD700 !important; font-size: 8vw !important; font-weight: 900 !important; font-family: monospace; letter-spacing: 1px; margin: 0; line-height: 1.1; white-space: nowrap !important; }
    </style>
    """, unsafe_allow_html=True)

if 'db' not in st.session_state:
    st.session_state['db'] = {
        "wire_scores": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "break_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "max_reached_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "over_1d_matrix": np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist(),
        "last_digits": "",
        "last_loto": [],
        "history": [],
        "last_predictions": {},
        "core_four": [],
        "gan_tracker": {str(i).zfill(2): 0 for i in range(100)},
        "bet_tracker": {str(i).zfill(2): 0 for i in range(100)},
        "total_hits": {str(i).zfill(2): 0 for i in range(100)}
    }
if 'raw_input' not in st.session_state: st.session_state['raw_input'] = ""

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'])

# --- 2. THUẬT TOÁN MA TRẬN VÀ CƠ CHẾ NỚI LỎG BỘ LỌC THÔNG MINH ---

def check_and_fix_db_structure():
    db = st.session_state['db']
    if "gan_tracker" not in db or not db["gan_tracker"]:
        db["gan_tracker"] = {str(i).zfill(2): 0 for i in range(100)}
    if "bet_tracker" not in db or not db["bet_tracker"]:
        db["bet_tracker"] = {str(i).zfill(2): 0 for i in range(100)}
    if "total_hits" not in db or not db["total_hits"]:
        db["total_hits"] = {str(i).zfill(2): 0 for i in range(100)}
    if "break_matrix" not in db:
        db["break_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()
    if "max_reached_matrix" not in db:
        db["max_reached_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()
    if "over_1d_matrix" not in db:
        db["over_1d_matrix"] = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int).tolist()

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

def get_filtered_power_score_4(new_wire_scores, current_digits):
    check_and_fix_db_structure()
    db = st.session_state['db']
    
    mapping_1d = {str(i).zfill(2): 0 for i in range(100)}
    coords_1 = np.argwhere(new_wire_scores == 1)
    for r, c in coords_1:
        num = current_digits[r] + current_digits[c]
        mapping_1d[num] += 1

    # 1. Bộ lọc đứt gãy nhiều
    break_arr = np.array(db["break_matrix"])
    num_break_counts = {str(i).zfill(2): 0 for i in range(100)}
    for r in range(TOTAL_POS):
        for c in range(TOTAL_POS):
            n = current_digits[r] + current_digits[c]
            num_break_counts[n] += break_arr[r][c]
    sorted_breaks = sorted([item for item in num_break_counts.items() if item[1] > 0], key=lambda x: x[1], reverse=True)
    death_20_breaks = [item[0] for item in sorted_breaks[:20]]

    # 2. Bộ lọc ăn 1 lần rồi gãy vĩnh viễn
    max_reached_arr = np.array(db["max_reached_matrix"])
    one_hit_blacklist = set()
    for r in range(TOTAL_POS):
        for c in range(TOTAL_POS):
            if break_arr[r][c] > 0 and max_reached_arr[r][c] < 2:
                one_hit_blacklist.add(current_digits[r] + current_digits[c])

    # 3. Bộ lọc cầu nghẹn hiệu suất thấp
    over_1d_arr = np.array(db["over_1d_matrix"])
    num_over_counts = {}
    for r in range(TOTAL_POS):
        for c in range(TOTAL_POS):
            n = current_digits[r] + current_digits[c]
            if max_reached_arr[r][c] > 0:
                num_over_counts[n] = num_over_counts.get(n, 0) + over_1d_arr[r][c]
                
    ghost_20_wires = []
    if num_over_counts:
        sorted_overs = sorted(num_over_counts.items(), key=lambda x: x[1])
        ghost_20_wires = [item[0] for item in sorted_overs[:20]]

    # 4. Các bộ lọc cơ bản
    gan_blacklist = [n for n, days in db['gan_tracker'].items() if days > 12]
    bet_blacklist = [n for n, streak in db['bet_tracker'].items() if streak >= 2]
    sorted_hits = sorted(db['total_hits'].items(), key=lambda x: (x[1], int(x[0])))
    bottom_20 = [item[0] for item in sorted_hits[:20]]
    
    # Gom danh sách cấm ban đầu
    final_blacklist = set(gan_blacklist + bet_blacklist + bottom_20 + death_20_breaks + list(one_hit_blacklist) + ghost_20_wires)

    # --- CƠ CHẾ CỨU TRỢ CHỐNG TRỐNG DÀN ---
    # Nếu danh sách cấm nuốt chửng gần hết (hơn 95 số), tự động thả xích bớt bộ lọc hiệu suất thấp và đứt gãy
    if len(final_blacklist) > 95:
        final_blacklist = set(gan_blacklist + bet_blacklist + bottom_20 + list(one_hit_blacklist))

    power_map = {str(i).zfill(2): 0 for i in range(100)}
    max_s = int(new_wire_scores.max())
    for s in range(2, max_s + 1):
        coords = np.argwhere(new_wire_scores == s)
        for r, c in coords:
            num = current_digits[r] + current_digits[c]
            if num in final_blacklist: continue
            
            base_score = s ** 2
            heat_bonus = 15 if 5 <= mapping_1d[num] <= 15 else 0
            heat_penalty = -30 if mapping_1d[num] > 30 else 0
            power_map[num] += (base_score + heat_bonus + heat_penalty)

    sorted_power = sorted(power_map.items(), key=lambda x: x[1], reverse=True)
    final_4 = [item[0] for item in sorted_power[:4] if item[1] > 0]
    
    # --- FALLBACK TOÀN DIỆN: Ép buộc phải bốc đủ quân khỏe nhất kể cả nằm trong blacklist nếu thiếu số ---
    if len(final_4) < 4:
        for s in range(max_s, -1, -1):
            coords = np.argwhere(new_wire_scores == s)
            for r, c in coords:
                num = current_digits[r] + current_digits[c]
                if num not in final_4:
                    # Ưu tiên lấy con nằm ngoài blacklist trước, nếu hết rồi thì lấy cả trong blacklist (trừ lô gan gắt)
                    if num not in final_blacklist or num not in gan_blacklist:
                        final_4.append(num)
                if len(final_4) >= 4: break
            if len(final_4) >= 4: break
            
    return final_4[:4]

def process_matrix(current_digits, current_loto, gdb_val):
    check_and_fix_db_structure()
    db = st.session_state['db']
    update_statistics(current_loto)
    
    old_scores = np.array(db['wire_scores'], dtype=int)
    old_digits = db['last_digits']
    old_preds = db['last_predictions']
    old_core_4 = db.get('core_four', [])
    
    new_wire_scores = np.zeros((TOTAL_POS, TOTAL_POS), dtype=int)
    break_arr = np.array(db["break_matrix"], dtype=int)
    max_reached_arr = np.array(db["max_reached_matrix"], dtype=int)
    over_1d_arr = np.array(db["over_1d_matrix"], dtype=int)
    
    hit_report = {"STT": len(db['history']) + 1, "GĐB": gdb_val}
    if old_core_4:
        old_tam_thu = old_core_4[:3]
        found_3 = [n for n in old_tam_thu if n in current_loto]
        count_3 = sum([current_loto.count(n) for n in found_3])
        hit_report["Dàn 3q"] = f"{count_3} ({','.join(found_3) if found_3 else '0'})"
        
        found_4 = [n for n in old_core_4 if n in current_loto]
        count_4 = sum([current_loto.count(n) for n in found_4])
        hit_report["Dàn 4q"] = f"{count_4} ({','.join(found_4) if found_4 else '0'})"
        
        if count_3 >= 1 or gdb_val in old_tam_thu:
            hit_report["Kết quả"] = "Win 🔥"
        elif count_4 >= 1:
            hit_report["Kết quả"] = "✅"
        else:
            hit_report["Kết quả"] = "❌"

    if len(old_digits) == TOTAL_POS:
        for i in range(TOTAL_POS):
            for j in range(TOTAL_POS):
                num_past = old_digits[i] + old_digits[j]
                if num_past in current_loto:
                    new_wire_scores[i][j] = old_scores[i][j] + 1
                    if new_wire_scores[i][j] > max_reached_arr[i][j]:
                        max_reached_arr[i][j] = new_wire_scores[i][j]
                    if new_wire_scores[i][j] >= 2:
                        over_1d_arr[i][j] += 1
                else:
                    if old_scores[i][j] >= 1:
                        break_arr[i][j] += 1
                    new_wire_scores[i][j] = 0

    new_preds = {}
    max_s = int(new_wire_scores.max())
    if max_s > 0:
        for s in range(1, max_s + 1):
            coords = np.argwhere(new_wire_scores == s)
            if len(coords) == 0: continue
            level_map = {}
            for r, c in coords:
                num = current_digits[r] + current_digits[c]
                level_map[num] = level_map.get(num, 0) + 1
            isolated = [n for n, count in level_map.items() if count == 1]
            new_preds[int(s)] = {"nums": sorted(isolated), "total_wires": int(len(coords))}

    db['wire_scores'] = new_wire_scores.tolist()
    db['break_matrix'] = break_arr.tolist()
    db['max_reached_matrix'] = max_reached_arr.tolist()
    db['over_1d_matrix'] = over_1d_arr.tolist()
    db['last_digits'] = current_digits
    db['last_loto'] = current_loto
    db['last_predictions'] = new_preds
    db['core_four'] = get_filtered_power_score_4(new_wire_scores, current_digits)
    db['history'].insert(0, hit_report)

# --- 3. GIAO DIỆN CHÍNH ---
st.markdown("<h2 style='text-align: center; color: #E2E8F0; font-weight: bold; font-size: 1.5rem;'>⚡ MATRIX MOBILE V9.5.4</h2>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 💾 HỆ THỐNG DATA")
    uploaded_file = st.file_uploader("Nạp JSON", type=['json'])
    if uploaded_file and st.button("📥 PHỤC HỒI MA TRẬN"):
        st.session_state['db'] = json.load(uploaded_file)
        check_and_fix_db_structure()
        st.rerun()
    if st.session_state['db']['last_digits']:
        st.download_button("💾 XUẤT FILE JSON", json.dumps(st.session_state['db']), "matrix_mobile.json")
    
    st.divider()
    st.markdown("### 📸 OCR KQ")
    uploaded_img = st.file_uploader("Quét ảnh", type=['jpg', 'png', 'jpeg'])
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

# --- HIỂN THỊ KẾT QUẢ ---
st.markdown("<h3><font color='#FF1E27'><b>🎯 TỌA ĐỘ PHÁT LỰC</b></font></h3>", unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #FF1E27; margin-top: -5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

c4 = st.session_state['db'].get('core_four', [])
if c4:
    tam_thu_str = ' - '.join(c4[:3])
    st.markdown(f"""
        <div class="mobile-box-3">
            <span style="color: #94A3B8; font-size: 12px; font-weight: bold; font-family: sans-serif;">🔥 TAM THỦ CHỦ LỰC</span><br>
            <p class="mobile-text-3"><b>{tam_thu_str}</b></p>
        </div>
        """, unsafe_allow_html=True)

    tu_thu_str = ' - '.join(c4)
    st.markdown(f"""
        <div class="mobile-box-4">
            <span style="color: #94A3B8; font-size: 12px; font-weight: bold; font-family: sans-serif;">🎯 TỨ THỦ CHIẾN THUẬT</span><br>
            <p class="mobile-text-4"><b>{tu_thu_str}</b></p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Đang chờ tích lũy xung nhịp kỳ kế tiếp.")

check_and_fix_db_structure()
with st.expander("🚫 Hệ thống chặn số tự động"):
    gan_list = [n for n, days in st.session_state['db']['gan_tracker'].items() if days > 12]
    bet_list = [n for n, streak in st.session_state['db']['bet_tracker'].items() if streak >= 2]
    st.write(f"**Lô Gan (>12 ngày):** {', '.join(gan_list) if gan_list else 'Trống'}")
    st.write(f"**Lô Bệt (>=2 ngày):** {', '.join(bet_list) if bet_list else 'Trống'}")

# MỨC ĐIỂM DÂY
st.markdown("<h3><font color='#FF1E27'><b>📊 ĐIỂM SỐ SỢI DÂY</b></font></h3>", unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #FF1E27; margin-top: -5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

preds = st.session_state['db'].get('last_predictions', {})
if preds:
    sorted_keys = sorted([int(k) for k in preds.keys()], reverse=True)
    for lv in sorted_keys:
        data = preds[str(lv)] if str(lv) in preds else preds[lv]
        with st.expander(f"Mức {lv}đ ({len(data['nums'])} quân)"):
            st.code(", ".join(data['nums']))

# BẢNG LỊCH SỬ CHỐNG LỖI 
st.markdown("<h3><font color='#FF1E27'><b>📋 LỊCH SỬ ĐỐI SOÁT KẾT QUẢ</b></font></h3>", unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #FF1E27; margin-top: -5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

if st.session_state['db']['history']:
    df_hist = pd.DataFrame(st.session_state['db']['history']).fillna("0")
    cols = list(df_hist.columns)
    important = ["Kết quả", "Dàn 3q", "Dàn 4q", "GĐB", "STT"]
    for col in reversed(important):
        if col in cols: cols.insert(0, cols.pop(cols.index(col)))
    
    if "Kết quả" in df_hist.columns:
        st.dataframe(
            df_hist[cols].style.map(
                lambda x: 'color: #F59E0B; font-weight: bold' if x == "Win 🔥" else 
                          ('color: #10B981' if x == "✅" else ('color: #EF4444' if x == "❌" else '')),
                subset=["Kết quả"]
            ),
            use_container_width=True,
            height=400
        )
    else:
        st.dataframe(df_hist[cols], use_container_width=True, height=400)
else:
    st.dataframe(pd.DataFrame(columns=["Kết quả", "Dàn 3q", "Dàn 4q", "GĐB", "STT"]), use_container_width=True, height=150)
