import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

DB_FILE = "jkh_database.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "apartments": [{"id": i, "owner": f"Владелец {i}", "phone": "—", "visible": True} for i in range(1, 19)],
            "tariffs": [{"date": "2026-01-01", "rate": 50.0}],
            "readings": [],
            "payments": [],
            "pumping": []
        }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="Учет ЖКХ и Откачек", layout="wide")

# БОКОВАЯ ПАНЕЛЬ ДЛЯ АВТОРИЗАЦИИ
st.sidebar.title("🔐 Доступ")
password = st.sidebar.text_input("Введите пароль для редактирования:", type="password")
# Задайте свой пароль вместо "admin123"
is_admin = (password == "admin123")

if is_admin:
    st.sidebar.success("Режим редактирования включен!")
else:
    st.sidebar.info("Режим чтения. Формы ввода скрыты.")

data = load_data()

# Динамически скрываем вкладку управления апартами от обычных пользователей
tab_titles = ["📊 Дашборд баланса", "💧 База показаний", "🚚 База откачек", "💰 База оплат"]
if is_admin:
    tab_titles.insert(1, "🏠 База апартов")

tabs = st.tabs(tab_titles)

# Назначаем переменные для вкладок в зависимости от прав
tab_dash = tabs[0]
if is_admin:
    tab_aparts = tabs[1]
    tab_readings = tabs[2]
    tab_pumping = tabs[3]
    tab_payments = tabs[4]
else:
    tab_readings = tabs[1]
    tab_pumping = tabs[2]
    tab_payments = tabs[3]

current_month = datetime.now().strftime("%Y-%m")

# ==========================================
# 1. ДАШБОРД БАЛАНСА (Доступен всем)
# ==========================================
with tab_dash:
    st.title("📊 Текущий статус и баланс квартир")
    
    df_readings = pd.DataFrame(data["readings"])
    df_payments = pd.DataFrame(data["payments"])
    current_rate = data["tariffs"][-1]["rate"] if data["tariffs"] else 50.0
    
    dash_rows = []
    for ap in data["apartments"]:
        if not ap["visible"]:
            continue
        ap_id = ap["id"]
        
        total_cubes = 0
        if not df_readings.empty:
            ap_readings = df_readings[df_readings["apartment"] == ap_id].sort_values("date")
            if len(ap_readings) > 1:
                total_cubes = ap_readings["counter_1"].max() - ap_readings["counter_1"].min()
                if "counter_2" in ap_readings.columns:
                    total_cubes += ap_readings["counter_2"].max() - ap_readings["counter_2"].min()
        
        total_billed = total_cubes * current_rate
        total_paid = df_payments[df_payments["apartment"] == ap_id]["amount"].sum() if not df_payments.empty else 0
        
        has_payment_this_month = False
        if not df_payments.empty:
            ap_payments = df_payments[df_payments["apartment"] == ap_id]
            has_payment_this_month = any(pd.to_datetime(ap_payments["date"]).dt.strftime("%Y-%m") == current_month)
            
        has_reading_this_month = False
        if not df_readings.empty:
            ap_month_readings = df_readings[df_readings["apartment"] == ap_id]
            has_reading_this_month = any(pd.to_datetime(ap_month_readings["date"]).dt.strftime("%Y-%m") == current_month)
            
        balance = total_paid - total_billed
        color_status = "🔴 Нет показаний" if not has_reading_this_month else ("🟢 Оплачено" if has_payment_this_month else "Обычный")
        
        dash_rows.append({
            "Квартира": f"Кв. {ap_id}",
            "Владелец": ap["owner"],
            "Потрачено кубов (всего)": round(total_cubes, 2),
            "Текущий баланс": round(balance, 2),
            "Статус месяца": color_status
        })
        
    df_dash = pd.DataFrame(dash_rows)
    if not df_dash.empty:
        def style_rows(row):
            if "🔴" in str(row["Статус месяца"]): return ["background-color: #ffe6e6"] * len(row)
            if "🟢" in str(row["Статус месяца"]): return ["background-color: #e6f9e6"] * len(row)
            return ["background-color: white"] * len(row)
        st.dataframe(df_dash.style.apply(style_rows, axis=1), use_container_width=True, height=600)

# ==========================================
# 2. БАЗА АПАРТОВ (Только для Админа)
# ==========================================
if is_admin:
    with tab_aparts:
        st.title("🏠 Управление базой квартир")
        edited_df = st.data_editor(
            pd.DataFrame(data["apartments"]), 
            column_config={"visible": st.column_config.CheckboxColumn("Показывать на дашборде", default=True)},
            disabled=["id"], use_container_width=True
        )
        if st.button("Сохранить изменения"):
            data["apartments"] = edited_df.to_dict(orient="records")
            save_data(data)
            st.success("База обновлена!")

# ==========================================
# 3. БАЗА ПОКАЗАНИЙ (Просмотр всем, ввод — Админу)
# ==========================================
with tab_readings:
    st.title("💧 Журнал показаний")
    col1, col2 = st.columns([1, 2] if is_admin else [0.1, 1])
    if is_admin:
        with col1:
            st.subheader("Добавить показания")
            with st.form("r_form", clear_on_submit=True):
                r_date = st.date_input("Дата", datetime.now())
                r_ap = st.number_input("Квартира", 1, 18, 1)
                r_c1 = st.number_input("Счетчик 1", min_value=0.0)
                r_c2 = st.number_input("Счетчик 2", min_value=0.0)
                if st.form_submit_button("Записать"):
                    data["readings"].append({"date": str(r_date), "apartment": int(r_ap), "counter_1": r_c1, "counter_2": r_c2})
                    save_data(data); st.rerun()
    with col2:
        if data["readings"]: st.dataframe(pd.DataFrame(data["readings"]).sort_values("date", ascending=False), use_container_width=True)

# ==========================================
# 4. БАЗА ОТКАЧЕК (Просмотр всем, ввод — Админу)
# ==========================================
with tab_pumping:
    st.title("🚚 Учет откачек")
    col1, col2 = st.columns([1, 2] if is_admin else [0.1, 1])
    if is_admin:
        with col1:
            st.subheader("Добавить откачку")
            with st.form("p_form", clear_on_submit=True):
                p_date = st.date_input("Дата откачки", datetime.now())
                p_cubes = st.number_input("Кубы", min_value=0.0)
                p_cost = st.number_input("Стоимость", min_value=0.0)
                if st.form_submit_button("Записать"):
                    data["pumping"].append({"date": str(p_date), "cubes": p_cubes, "cost": p_cost})
                    save_data(data); st.rerun()
    with col2:
        if data["pumping"]: st.dataframe(pd.DataFrame(data["pumping"]).sort_values("date", ascending=False), use_container_width=True)

# ==========================================
# 5. БАЗА ОПЛАТ (Просмотр всем, ввод — Админу)
# ==========================================
with tab_payments:
    st.title("💰 Журнал поступления денег")
    col1, col2 = st.columns([1, 2] if is_admin else [0.1, 1])
    if is_admin:
        with col1:
            st.subheader("Внести платеж")
            with st.form("pay_form", clear_on_submit=True):
                pay_date = st.date_input("Дата оплаты", datetime.now())
                pay_ap = st.number_input("Квартира ", 1, 18, 1)
                pay_amount = st.number_input("Сумма", min_value=0.0)
                if st.form_submit_button("Внести"):
                    data["payments"].append({"date": str(pay_date), "apartment": int(pay_ap), "amount": pay_amount})
                    save_data(data); st.rerun()
    with col2:
        if data["payments"]: st.dataframe(pd.DataFrame(data["payments"]).sort_values("date", ascending=False), use_container_width=True)
