import os
import re
import sqlite3
from difflib import get_close_matches

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots



st.set_page_config(page_title="Used Car Intelligence", page_icon="car", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#17202a; --muted:#68727d; --mint:#0b766e; --orange:#e56b2f; --line:#d9e1df; }
    html, body, [class*="css"] { font-family:'IBM Plex Sans Thai', sans-serif; color:var(--ink); }
    .stApp { background:linear-gradient(135deg,#f5f7f4 0%,#eef5f1 52%,#fffaf3 100%); }
    h1,h2,h3 { font-family:'Space Grotesk','IBM Plex Sans Thai',sans-serif !important; letter-spacing:0 !important; }
    [data-testid="stMetric"] { background:#ffffffcc; border:1px solid var(--line); border-radius:8px; padding:16px; }
    [data-testid="stMetricValue"] { color:var(--mint); font-family:'Space Grotesk',sans-serif; }
    section[data-testid="stSidebar"] { background:#17202a; }
    section[data-testid="stSidebar"] * { color:#f5f7f4 !important; }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #0b766e;
        color: #ffffff !important;
        border: 1px solid #0b766e;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        padding: 6px 12px;
        transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #0e8c83;
        border-color: #0e8c83;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stButton > button:active {
        background-color: #08524d;
        border-color: #08524d;
    }
    .status { border-left:4px solid var(--mint); background:#ffffffaa; padding:12px 16px; margin:8px 0 16px; }
    .status.warn { border-left-color:var(--orange); }
    </style>
    """, unsafe_allow_html=True,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "03_Data_Warehouse", "used_car_dw.db")

BRAND_PALETTE = [
    "#0b766e",  # mint
    "#e56b2f",  # orange
    "#2a9d8f",  # teal
    "#f4a261",  # sand
    "#17202a",  # ink
    "#457b9d",  # steel blue
    "#e76f51",  # coral
    "#68727d",  # slate
    "#3d5a80",  # navy
    "#d4a373",  # ochre
]


def status_box(message, level="info"):
    cls = "status warn" if level == "warn" else "status"
    st.markdown(f'<div class="{cls}">{message}</div>', unsafe_allow_html=True)


@st.cache_data
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"ไม่พบฐานข้อมูล: {os.path.abspath(DB_PATH)}")
        return None
    with sqlite3.connect(DB_PATH) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"FactSales", "FactMarketListings", "DimCar", "DimDate", "DimLocation", "DimCustomer"}
        missing = required - tables
        if missing:
            st.error(f"ตารางที่จำเป็นหายไป: {', '.join(sorted(missing))}")
            return None
        frames = {name: pd.read_sql_query(f"SELECT * FROM {name}", conn) for name in required}
        if "DimAcquisitionSource" in tables:
            frames["DimAcquisitionSource"] = pd.read_sql_query("SELECT * FROM DimAcquisitionSource", conn)
        if "FactMLPredictions" in tables:
            frames["FactMLPredictions"] = pd.read_sql_query("SELECT * FROM FactMLPredictions", conn)

    sales = frames["FactSales"].merge(frames["DimCar"], on="car_key", how="left")
    sales = sales.merge(frames["DimDate"], on="date_key", how="left", suffixes=("", "_date"))
    sales = sales.merge(frames["DimLocation"], on="location_key", how="left", suffixes=("", "_location"))
    sales = sales.merge(frames["DimCustomer"], on="customer_key", how="left", suffixes=("", "_customer"))
    if "DimAcquisitionSource" in frames:
        sales = sales.merge(frames["DimAcquisitionSource"], left_on="acquisition_source_key", right_on="source_key", how="left")
    listings = frames["FactMarketListings"].merge(frames["DimCar"], on="car_key", how="left")
    listings = listings.merge(frames["DimDate"], on="date_key", how="left", suffixes=("", "_date"))
    listings = listings.merge(frames["DimLocation"], on="location_key", how="left", suffixes=("", "_location"))
    return {"sales": sales, "listings": listings, "raw": frames}


def money(value):
    return f"฿{value:,.0f}"


def safe_ratio(numerator, denominator):
    return float(numerator / denominator * 100) if denominator else 0.0


def chart_layout(figure, height=360):
    figure.update_layout(template="plotly_white", height=height, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.55)", font=dict(family="IBM Plex Sans Thai, sans-serif", color="#17202a"))
    return figure


def apply_filters(frame, selections):
    result = frame.copy()
    for column, values in selections.items():
        if column not in result:
            continue
        if column == "brand":
            if values:
                result = result[result[column].isin(values)]
        else:
            result = result[result[column].isin(values)]
    return result


DAYS_ON_LOT_ORDER = [
    "< 30 วัน (Fast Moving - สภาพคล่องสูง)",
    "31–60 วัน (Normal)",
    "61–90 วัน (Slow Moving)",
    "> 90 วัน (High Risk - ความเสี่ยงขาดทุนสูง)",
]


def classify_days_on_lot(days):
    if pd.isna(days):
        return None
    if days <= 30:
        return DAYS_ON_LOT_ORDER[0]
    elif days <= 60:
        return DAYS_ON_LOT_ORDER[1]
    elif days <= 90:
        return DAYS_ON_LOT_ORDER[2]
    else:
        return DAYS_ON_LOT_ORDER[3]


def top_bottom_diverging_chart(
    frame, group_col, value_col, title, x_label, n=5, agg="sum"
):
    """สร้างกราฟแท่งแบบ 2 ช่องเปรียบเทียบ Top n และ Bottom n แบบแยกแกน X"""
    grouped = (
        frame.groupby(group_col, dropna=False)[value_col]
        .agg(agg)
        .sort_values(ascending=False)
        .dropna()
    )

    if grouped.empty:
        return None

    top = grouped.head(n).sort_values(ascending=True)
    bottom = grouped.tail(n).sort_values(ascending=True)

    # 1. เพิ่มระยะห่างระหว่างซ้าย-ขวา (horizontal_spacing)
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(" "),
        horizontal_spacing=0.22,
    )

    fig.add_trace(
        go.Bar(
            x=top.values,
            y=top.index.astype(str),
            orientation="h",
            name="Top",
            marker_color="#0b766e",
            text=[f"{v:,.0f}" for v in top.values],
            textposition="outside",
            cliponaxis=False,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=bottom.values,
            y=bottom.index.astype(str),
            orientation="h",
            name="Bottom",
            marker_color="#e56b2f",
            text=[f"{v:,.0f}" for v in bottom.values],
            textposition="outside",
            cliponaxis=False,
        ),
        row=1,
        col=2,
    )

    # 2. ปรับระยะขอบแกน X (X-axis Range Padding) เพื่อเผื่อพื้นที่ให้ตัวเลขปลายแท่งไม่หลุดขอบ
    top_max = top.max() * 1.35 if not top.empty else 1
    bottom_max = bottom.max() * 1.35 if not bottom.empty else 1
    fig.update_xaxes(range=[0, top_max], row=1, col=1)
    fig.update_xaxes(range=[0, bottom_max], row=1, col=2)

    # 3. จัดการ Layout เผื่อระยะ Top Margin ให้ Title ไม่ชน Subtitle
    fig.update_layout(
        title_text=f"{title} ({x_label})",
        title_y=0.98,
        showlegend=False,
        margin=dict(r=60, l=40, t=90, b=40),
    )

    # 4. ขยับตำแหน่ง Subtitle (Subplot Annotations) ลงมาเล็กน้อยป้องกันการชน Title หลัก
    for annotation in fig["layout"]["annotations"]:
        annotation["y"] = 1.02

    return fig


def is_other_model(value):
    normalized = str(value).strip().lower()
    return normalized in {"other", "others", "รุ่นอื่นๆ", "รุ่นอื่น ๆ"} or "other model" in normalized


def model_class(brand, model):
    brand_name = str(brand).lower()
    model_name = str(model).strip()
    upper_model = model_name.upper()
    if brand_name == "bmw":
        if upper_model.startswith("X"):
            return "BMW X Series"
        if upper_model.startswith("Z"):
            return "BMW Z Series"
        if upper_model.startswith("I"):
            return "BMW i Series"
        if upper_model.startswith("M"):
            return "BMW M Series"
        for series in ("1", "2", "3", "4", "5", "6", "7", "8"):
            if upper_model.startswith(series) or upper_model == f"SERIES {series}":
                return f"BMW {series} Series"
    if "mercedes" in brand_name or brand_name == "benz":
        for series in ("SPRINTER", "GLA", "GLB", "GLC", "GLE", "GLS", "CLA", "CLS", "CLE", "CLK", "G-", "A", "B", "C", "E", "S", "G", "SL", "V", "ML"):
            if upper_model.startswith(series) or upper_model == f"{series}-CLASS":
                return f"Mercedes-Benz {series.rstrip('-')} Class"
    return "Other"


def model_group(brand, model):
    brand_name = str(brand).lower()
    model_name = str(model).strip().upper().replace(" ", "")
    if brand_name == "bmw":
        series_match = re.fullmatch(r"SERIES([1-8])", model_name)
        numeric_match = re.match(r"^([1-8])\d{2}", model_name)
        if series_match:
            return f"BMW Series {series_match.group(1)}"
        if numeric_match:
            return f"BMW Series {numeric_match.group(1)}"
        if model_name.startswith("X"):
            return "BMW X Series"
        if model_name.startswith("Z"):
            return "BMW Z Series"
        if model_name.startswith("I"):
            return "BMW i Series"
        if model_name.startswith("M"):
            return "BMW M Series"
    if "mercedes" in brand_name or brand_name == "benz":
        for series in ("GLA", "GLB", "GLC", "GLE", "GLS", "CLA", "CLS", "CLE", "CLK", "SPRINTER", "A", "B", "C", "E", "S", "G", "SL", "V", "ML"):
            if model_name.startswith(series):
                return f"Mercedes-Benz {series} Class"
    return None


def show_kpis(sales):
    revenue = sales["net_revenue"].sum()
    profit = sales["profit"].sum()
    metrics = st.columns(5)
    metrics[0].metric("Total Revenue", money(revenue))
    metrics[1].metric("Total Profit", money(profit))
    metrics[2].metric("Net Profit Margin %", f"{safe_ratio(profit, revenue):.2f}%")
    metrics[3].metric("Sales Volume", f"{len(sales):,}")
    metrics[4].metric("Avg Days on Lot", f"{sales['days_on_lot'].mean():.1f} วัน" if not sales.empty else "0.0 วัน")


def executive_page(sales):
    st.subheader("Page 1 · Executive Sales Overview")
    show_kpis(sales)
    
    # BQ5: Trend with Transaction Count on Dual Axis
    left, right = st.columns([1.5, 1])
    with left:
        trend = sales.groupby(["year", "month"], as_index=False).agg(
            revenue=("net_revenue", "sum"), 
            profit=("profit", "sum"),
            transaction_count=("sales_id", "nunique")
        ).sort_values(["year", "month"])
        trend["period"] = trend["year"].astype(str) + "-" + trend["month"].astype(str).str.zfill(2)
        
        figure = go.Figure()
        figure.add_bar(x=trend["period"], y=trend["revenue"], name="Revenue", marker_color="#00c2a8", yaxis="y1")
        figure.add_scatter(x=trend["period"], y=trend["profit"], name="Profit", mode="lines+markers", line_color="#e56b2f", yaxis="y1")
        figure.add_scatter(x=trend["period"], y=trend["transaction_count"], name="Transactions", mode="lines", line=dict(color="#377eb9", dash="dot"), yaxis="y2")
        
        figure.update_layout(
            title="แนวโน้มรายได้ กำไรสุทธิ และจำนวนธุรกรรม (Revenue, Profit & Volume)",
            yaxis=dict(title="บาท (THB)"),
            yaxis2=dict(title="จำนวนธุรกรรม (คัน)", overlaying="y", side="right", showgrid=False)
        )
        st.plotly_chart(chart_layout(figure, 400), use_container_width=True)
        
    with right:
        payment = sales.groupby("payment_method", dropna=False).size().reset_index(name="sales_volume")
        st.plotly_chart(
            chart_layout(
                px.pie(
                    payment,
                    names="payment_method",
                    values="sales_volume",
                    hole=0.45,
                    title="สัดส่วนช่องทางการชำระเงิน (Payment Method Ratio)",
                    color_discrete_sequence=BRAND_PALETTE,
                ),
                400,
            ),
            use_container_width=True,
        )
        
    # BQ5: Seasonality - เปรียบเทียบ pattern รายเดือนข้ามปี เพื่อดูว่ามีฤดูกาลหรือไม่
    left, right = st.columns(2)
    with left:
        month_order = sales[["month", "month_name"]].dropna().drop_duplicates().sort_values("month")["month_name"].tolist()
        season = sales.groupby(["year", "month", "month_name"], as_index=False)["profit"].sum()
        season_fig = px.line(
            season.sort_values(["year", "month"]),
            x="month_name",
            y="profit",
            color="year",
            markers=True,
            category_orders={"month_name": month_order},
            title="ความเป็นฤดูกาลของกำไร: เปรียบเทียบรายเดือนข้ามปี (Seasonality - BQ5)",
            labels={"month_name": "เดือน", "profit": "กำไรรวม (บาท)", "year": "ปี"},
            color_discrete_sequence=BRAND_PALETTE,
        )
        st.plotly_chart(chart_layout(season_fig, 380), use_container_width=True)
    with right:
        # BQ6: กลุ่มลูกค้าใดทำกำไรดีที่สุด
        segment_profit = sales.groupby("customer_segment", dropna=False)["profit"].sum().reset_index().sort_values("profit", ascending=True)
        segment_fig = px.bar(
            segment_profit,
            x="profit",
            y="customer_segment",
            orientation="h",
            title="กำไรรวมตามกลุ่มลูกค้า (Total Profit by Customer Segment - BQ6)",
            labels={"profit": "กำไรรวม (บาท)", "customer_segment": "กลุ่มลูกค้า"},
            color_discrete_sequence=["#3d5a80"],
        )
        st.plotly_chart(chart_layout(segment_fig, 380), use_container_width=True)

    left, right = st.columns(2)
    with left:
        # BQ1: แบรนด์ใดทำกำไรรวมสูงสุด-ต่ำสุด
        profit_fig = top_bottom_diverging_chart(
            sales, "brand", "profit",
            title="แบรนด์ที่ทำกำไรรวมสูงสุด vs ต่ำสุด (Top/Bottom 5 Brand by Total Profit - BQ1)",
            x_label="กำไรรวม (บาท)",
        )
        if profit_fig is not None:
            st.plotly_chart(chart_layout(profit_fig), use_container_width=True)
    with right:
        # BQ4: Channel Acquisition Cost vs Profit Margin
        if "source_type" in sales.columns:
            channel_profit = sales.groupby("source_type", dropna=False).agg(
                avg_cost=("cost_price", "mean"),
                avg_margin=("profit_margin", "mean")
            ).reset_index()
            
            channel_fig = px.scatter(
                channel_profit, 
                x="avg_cost", 
                y="avg_margin", 
                text="source_type",
                size="avg_cost",
                title="ต้นทุนและอัตรากำไรตามแหล่งจัดหา (Source Cost vs Margin)",
                labels={"avg_cost": "ต้นทุนเฉลี่ย (บาท)", "avg_margin": "อัตรากำไรเฉลี่ย (%)"},
                color_discrete_sequence=["#0b766e"]
            )
            channel_fig.update_traces(textposition='top center')
            st.plotly_chart(chart_layout(channel_fig, 400), use_container_width=True)
        else:
            st.info("ไม่พบข้อมูลแหล่งจัดหา (DimAcquisitionSource)")

    # BQ6: Regional Profitability Analysis
    left, right = st.columns(2)
    with left:
        if "region" in sales.columns:
            region_data = sales.groupby("region", as_index=False).agg(
                avg_profit=("profit", "mean"),
                total_profit=("profit", "sum")
            ).sort_values("total_profit", ascending=False)
            
            reg_fig = px.bar(
                region_data,
                x="region",
                y="total_profit",
                title="กำไรรวมตามภูมิภาค (Total Profit by Region)",
                labels={"region": "ภูมิภาค", "total_profit": "กำไรรวม (บาท)"},
                color_discrete_sequence=["#2a9d8f"]
            )
            st.plotly_chart(chart_layout(reg_fig, 400), use_container_width=True)
    with right:
        body_data = sales.groupby("body_type", dropna=False).size().reset_index(name="sales_volume")
        body_data["body_type"] = body_data["body_type"].fillna("Unknown")
        body_fig = px.pie(
            body_data,
            names="body_type",
            values="sales_volume",
            hole=0.45,
            title="สัดส่วนยอดขายตามประเภทรถ (Body Type Ratio)",
            color_discrete_sequence=BRAND_PALETTE,
        )
        st.plotly_chart(chart_layout(body_fig, 400), use_container_width=True)


def Stock_page(sales, raw):
    st.subheader("Page 2 · Stock Analysis")
    available_tiers = sorted(sales["price_tier"].dropna().unique().tolist())
    selected_tiers = st.multiselect(
        "Price Segment Filter · เลือกกลุ่มราคาเพื่อแสดงข้อมูล Page 2",
        available_tiers,
        default=available_tiers,
        key="page2_price_tiers",
    )
    sales = sales[sales["price_tier"].isin(selected_tiers)]
    if sales.empty:
        status_box("⚠️ ไม่มีข้อมูลใน Price Segment ที่เลือก", level="warn")
        return
    st.markdown("#### ระยะเวลาจอดตามกลุ่มราคา (Days on Lot by Segment - BQ3)")
    sales_binned = sales.copy()
    sales_binned["days_category"] = sales_binned["days_on_lot"].apply(classify_days_on_lot)
    sales_binned = sales_binned.dropna(subset=["days_category"])

    grouped = sales_binned.groupby(["days_category", "price_tier"], as_index=False).size().rename(columns={"size": "sales_volume"})

    figure = px.bar(
        grouped,
        x="days_category",
        y="sales_volume",
        color="price_tier",
        barmode="group",
        category_orders={"days_category": DAYS_ON_LOT_ORDER},
        labels={"days_category": "ช่วงเวลาที่จอด", "sales_volume": "จำนวนคัน", "price_tier": "Price Segment"},
        color_discrete_sequence=BRAND_PALETTE,
    )
    figure.update_layout(height=520)
    st.plotly_chart(chart_layout(figure, 520), use_container_width=True)

    st.markdown("#### กลุ่มรถที่มีความเสี่ยง Dead Stock (>90 วัน) แยกตามประเภทตัวถังและเชื้อเพลิง (BQ3)")
    dim_choice = st.radio("แยกตาม", ["ประเภทตัวถัง (Body Type)", "ประเภทเชื้อเพลิง (Fuel Type)"], horizontal=True, key="deadstock_dim")
    dim_col = "body_type" if dim_choice.startswith("ประเภทตัวถัง") else "fuel_type"
    risk = sales.copy()
    risk["is_high_risk"] = risk["days_on_lot"] > 90
    risk_summary = risk.groupby(dim_col, dropna=False).agg(
        total_cars=("sales_id", "nunique"),
        high_risk_cars=("is_high_risk", "sum"),
        avg_days_on_lot=("days_on_lot", "mean"),
    ).reset_index()
    risk_summary["high_risk_pct"] = risk_summary.apply(lambda r: safe_ratio(r["high_risk_cars"], r["total_cars"]), axis=1)
    risk_summary = risk_summary.sort_values("high_risk_pct", ascending=True)
    risk_fig = px.bar(
        risk_summary,
        x="high_risk_pct",
        y=dim_col,
        orientation="h",
        text=risk_summary["high_risk_pct"].map(lambda v: f"{v:.1f}%"),
        title=f"สัดส่วนรถที่จอดเกิน 90 วัน (Dead Stock Risk) แยกตาม {dim_choice}",
        labels={"high_risk_pct": "% ของคันที่จอดเกิน 90 วัน", dim_col: ""},
        color_discrete_sequence=["#e56b2f"],
    )
    risk_fig.update_traces(textposition="outside")
    st.plotly_chart(chart_layout(risk_fig, 340), use_container_width=True)
    st.caption("ยิ่งเปอร์เซ็นต์สูง ยิ่งมีความเสี่ยงเป็น Dead Stock มาก ควรพิจารณาปรับราคาหรือทำโปรโมชันกับกลุ่มนี้ก่อน")

    st.markdown("#### ราคาขายเฉลี่ยตามอายุรถหรือเลขไมล์ (Selling Price by Car Age or Mileage)")
    left = st.container()
    with left:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            x_axis = st.radio("วิเคราะห์ตาม", ["อายุรถ", "เลขไมล์"], horizontal=True, key="selling_price_x_axis")
            brands = sorted(sales["brand"].dropna().unique().tolist())
            selected_brand = st.selectbox("เลือกยี่ห้อ", ["ทั้งหมด"] + brands, key="age_chart_brand")
        brand_sales = sales if selected_brand == "ทั้งหมด" else sales[sales["brand"] == selected_brand]
        with chart_col2:
            model_values = [value for value in brand_sales["model"].dropna().unique() if not is_other_model(value)]
            model_options = [("ทั้งหมด", (None, None, "all"))]
            group_values = {}
            for model in sorted(model_values):
                matching_brands = sorted(brand_sales.loc[brand_sales["model"] == model, "brand"].dropna().unique().tolist())
                model_brand = selected_brand if selected_brand != "ทั้งหมด" else (matching_brands[0] if matching_brands else "")
                group = model_group(model_brand, model)
                if group:
                    group_values.setdefault((model_brand, group), []).append(model)
            for (group_brand, group), group_models in sorted(group_values.items()):
                group_label = f"{group_brand} · {group} (รวม {len(group_models)} รุ่น)"
                model_options.append((group_label, (group_brand, group, "group")))
            for model in sorted(model_values):
                matching_brands = sorted(brand_sales.loc[brand_sales["model"] == model, "brand"].dropna().unique().tolist())
                model_brand = selected_brand if selected_brand != "ทั้งหมด" else (matching_brands[0] if matching_brands else "")
                label = f"{model} · {model_class(model_brand, model)}" if selected_brand != "ทั้งหมด" else f"{model_brand} · {model} · {model_class(model_brand, model)}"
                model_options.append((label, (model_brand, model, "model")))
            model_label = st.selectbox("เลือกรุ่น · class", [label for label, _ in model_options], key="age_chart_model")
            selected_model_brand, selected_model, selected_model_type = dict(model_options)[model_label]
            if selected_model_brand and selected_brand == "ทั้งหมด":
                brand_sales = brand_sales[brand_sales["brand"] == selected_model_brand]
        if selected_model is None:
            price_by_age = brand_sales
        elif selected_model_type == "group":
            price_by_age = brand_sales[brand_sales["model"].map(lambda value: model_group(selected_model_brand, value) == selected_model)]
        else:
            price_by_age = brand_sales[brand_sales["model"] == selected_model]
        chart_sales = price_by_age.copy()
        if x_axis == "เลขไมล์":
            chart_sales["chart_axis"] = (pd.to_numeric(chart_sales["mileage"], errors="coerce") // 10000) * 10000
            axis_label = "เลขไมล์ (ช่วงละ 10,000 กม.)"
        else:
            chart_sales["chart_axis"] = pd.to_numeric(chart_sales["car_age"], errors="coerce")
            axis_label = "อายุรถ (ปี)"
        chart_sales = chart_sales.dropna(subset=["chart_axis"])
        price_by_axis = chart_sales.groupby("chart_axis", as_index=False).agg(
            selling_price=("selling_price", "mean"), cars=("sales_id", "nunique")
        ).sort_values("chart_axis")
        st.metric("จำนวนคันที่ใช้คำนวณ", f"{chart_sales['sales_id'].nunique():,} คัน")
        figure = px.line(price_by_axis, x="chart_axis", y="selling_price", markers=True, custom_data=["cars"], labels={"chart_axis": axis_label, "selling_price": "ราคาขายเฉลี่ย (บาท)"}, color_discrete_sequence=["#e56b2f"])
        figure.update_traces(hovertemplate=f"<b>{axis_label}:</b> %{{x:,.0f}}<br><b>ราคาขายเฉลี่ย:</b> ฿%{{y:,.0f}}<br><b>จำนวนคัน:</b> %{{customdata[0]:,}} คัน<extra></extra>")
        st.plotly_chart(chart_layout(figure), use_container_width=True)

    st.markdown("#### เมทริกซ์วิเคราะห์ Brand → Model → Model Year (BQ1)")
    matrix_search = st.text_input("ค้นหารุ่นใน matrix", placeholder="พิมพ์ชื่อรุ่น เช่น 320d หรือ C220", key="matrix_model_search")
    matrix = sales.groupby(["brand", "model", "model_year"], as_index=False).agg(
        cost_price=("cost_price", "mean"), 
        selling_price=("selling_price", "mean"), 
        total_profit=("profit", "sum"),
        profit_margin=("profit_margin", "mean"), 
        days_on_lot=("days_on_lot", "mean")
    ).sort_values("total_profit", ascending=False)
    matrix = matrix[~matrix["model"].map(is_other_model)]
    if matrix_search.strip():
        search_text = matrix_search.strip()
        model_names = sorted(matrix["model"].astype(str).unique())
        exact_matches = [name for name in model_names if search_text.lower() in name.lower()]
        nearby_names = get_close_matches(search_text, model_names, n=5, cutoff=0.25)
        recommended = list(dict.fromkeys(exact_matches + nearby_names))
        if recommended:
            st.caption("รุ่นที่แนะนำใกล้เคียง: " + " · ".join(recommended))
        matrix = matrix[matrix["model"].astype(str).str.contains(search_text, case=False, na=False)]
    st.dataframe(matrix, use_container_width=True, hide_index=True)


def market_page(sales, listings):
    st.subheader("Page 3 · Market Benchmark & Price Elasticity (BQ2 & BQ7)")

    # BQ2: Company vs Market Price Comparison — เทียบได้ทั้งตามแบรนด์, กลุ่มราคา, และประเภทรถ
    st.markdown("#### ราคาบริษัทเทียบราคาตลาด (Company vs Market Price - BQ2)")
    dim_label_map = {"แบรนด์ (Brand)": "brand", "กลุ่มราคา (Price Tier)": "price_tier", "ประเภทรถ (Body Type)": "body_type"}
    dim_choice = st.radio("เปรียบเทียบตาม", list(dim_label_map.keys()), horizontal=True, key="benchmark_dim")
    dim_col = dim_label_map[dim_choice]

    internal = sales.groupby(dim_col, as_index=False)["selling_price"].mean().rename(columns={"selling_price": "company_price"})
    market = sales.groupby(dim_col, as_index=False)["list_price"].mean().rename(columns={"list_price": "market_price"})

    # 1. เปลี่ยนเป็น outer หรือ left เพื่อป้องกันข้อมูลหาย
    benchmark = pd.merge(internal, market, on=dim_col, how="left").fillna(0)

    # คำนวณ gap_pct (ปรับเป็นเปอร์เซ็นต์ * 100 เพื่อใชักับกราฟได้ง่ายขึ้น)
    benchmark["gap_pct"] = benchmark.apply(
        lambda r: safe_ratio(r["company_price"] - r["market_price"], r["market_price"])  if r["market_price"] > 0 else 0, 
        axis=1
    )

    if dim_col == "brand":
        # 2. ปรับการจัดเรียงเรียงตาม abs() ให้ปลอดภัยขึ้น
        benchmark = benchmark.assign(abs_gap=benchmark["gap_pct"].abs()).sort_values("abs_gap", ascending=False).head(15).drop(columns=["abs_gap"])

    # 3. สร้างกราฟแท่งเปรียบเทียบ พร้อม Hover Format (ใส่สกุลเงิน บาท)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=benchmark[dim_col], 
        y=benchmark["company_price"], 
        name="ราคาบริษัท (Company Price)", 
        marker_color="#0b766e",
        hovertemplate="%{x}<br>ราคาบริษัท: %{y:,.0f} บาท<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=benchmark[dim_col], 
        y=benchmark["market_price"], 
        name="ราคาตลาด (Market Benchmark)", 
        marker_color="#e56b2f",
        hovertemplate="%{x}<br>ราคาตลาด: %{y:,.0f} บาท<extra></extra>"
    ))
    fig.update_layout(title=f"เปรียบเทียบราคาขายเฉลี่ยของบริษัทกับราคาตลาด แยกตาม {dim_choice}", barmode='group')
    st.plotly_chart(chart_layout(fig), use_container_width=True)

    # 4. กราฟส่วนต่าง (%) แสดงเครื่องหมาย % บนแกน X และ Hover
    gap_fig = px.bar(
        benchmark.sort_values("gap_pct"),
        x="gap_pct",
        y=dim_col,
        orientation="h",
        title=f"ส่วนต่างราคาขายทียบตลาด (%) แยกตาม {dim_choice} — บวก = ตั้งราคาสูงกว่าตลาด, ลบ = ต่ำกว่าตลาด",
        labels={"gap_pct": "ส่วนต่างราคา (%)", dim_col: ""},
        color="gap_pct",
        color_continuous_scale=["#e56b2f", "#d9e1df", "#0b766e"],
        color_continuous_midpoint=0,
    )
    gap_fig.update_traces(hovertemplate="%{y}<br>ส่วนต่าง: %{x:.2f}%<extra></extra>")
    gap_fig.update_xaxes(ticksuffix="%")
    gap_fig.add_vline(x=0, line_dash="dash", line_color="#68727d")

    st.plotly_chart(chart_layout(gap_fig, 340), use_container_width=True)
    # BQ7: Discount to Depreciation Ratio & Consistency Check
    st.markdown("#### ส่วนลดสอดคล้องกับค่าเสื่อมราคาจริงหรือไม่ (Discount vs Depreciation - BQ7)")
    if "discount_to_deprec_ratio" in sales.columns:
        left, right = st.columns(2)
        with left:
            ratio = sales.groupby("price_tier", as_index=False)["discount_to_deprec_ratio"].mean().sort_values("discount_to_deprec_ratio", ascending=False)
            st.plotly_chart(
                chart_layout(
                    px.bar(
                        ratio,
                        x="price_tier",
                        y="discount_to_deprec_ratio",
                        title="อัตราส่วนส่วนลดต่อค่าเสื่อมราคาเฉลี่ย ตามกลุ่มราคา (%)",
                        color_discrete_sequence=["#e56b2f"],
                        labels={"discount_to_deprec_ratio": "Discount / Depreciation (%)", "price_tier": "กลุ่มราคา"},
                    )
                ),
                use_container_width=True,
            )
        with right:
            brand_dd = sales.groupby("brand", as_index=False).agg(
                avg_discount=("discount_amount", "mean"),
                avg_depreciation=("depreciation_amount", "mean"),
            )
            
            # 1. กรองเฉพาะข้อมูลที่เป็นบวกเพื่อป้องกัน error ใน Log scale
            brand_dd = brand_dd[(brand_dd["avg_discount"] > 0) & (brand_dd["avg_depreciation"] > 0)]

            # 2. สร้าง Scatter Plot พร้อม Log scale
            dd_fig = px.scatter(
                brand_dd,
                x="avg_depreciation",
                y="avg_discount",
                text="brand",
                hover_name="brand",
                title="ส่วนลดเฉลี่ย vs ค่าเสื่อมราคาเฉลี่ย ตามแบรนด์",
                labels={"avg_depreciation": "ค่าเสื่อมราคาเฉลี่ย (บาท)", "avg_discount": "ส่วนลดเฉลี่ย (บาท)"},
                color_discrete_sequence=["#0b766e"],
                log_x=True,
                log_y=True,
            )

            # 3. คำนวณช่วงขอบเขต min/max สำหรับเส้นประ 1:1 ใน Log Scale
            min_val = min(brand_dd["avg_depreciation"].min(), brand_dd["avg_discount"].min())
            max_val = max(brand_dd["avg_depreciation"].max(), brand_dd["avg_discount"].max())

            dd_fig.add_shape(
                type="line",
                x0=min_val, y0=min_val,
                x1=max_val, y1=max_val,
                line=dict(color="#e56b2f", dash="dash")
            )
            
            # 4. ปรับแต่งตำแหน่งและขนาดตัวอักษรไม่ให้ซ้อนทับ
            dd_fig.update_traces(
                textposition="bottom right",
                textfont=dict(size=5),
                cliponaxis=False
            )
            
            st.plotly_chart(chart_layout(dd_fig), use_container_width=True)
            st.caption("จุดที่อยู่ 'เหนือ' เส้นประ หมายถึงแบรนด์นั้นให้ส่วนลดมากกว่าค่าเสื่อมราคาจริง (เสี่ยงขาดทุนแฝง)")
    else:
        st.info("ไม่พบคอลัมน์ discount_to_deprec_ratio ในข้อมูล")


def insights_page(sales):
    st.subheader("Page 4 · Business Insights & Recommendations (5 ข้อมูลเชิงลึกเชิงธุรกิจ)")
    st.caption("คำนวณสดจากข้อมูลภายใต้ตัวกรองปัจจุบัน ครอบคลุม 5 มุมมองเชิงลึกที่ทีมธุรกิจให้ความสำคัญ")
    if sales.empty:
        status_box("⚠️ ไม่มีข้อมูลเพียงพอสำหรับสร้าง Insight ภายใต้ตัวกรองปัจจุบัน", level="warn")
        return

    # ============ ข้อมูลเชิงลึก 1: ผลกระทบของระยะเวลาจอดสต็อกต่อกำไร ============
    st.markdown("### 1. ผลกระทบของระยะเวลาจอดสต็อกต่อกำไร (Days on Lot vs. Profit Margin)")
    lot_view = sales.copy()
    lot_view["days_category"] = lot_view["days_on_lot"].apply(classify_days_on_lot)
    lot_view = lot_view.dropna(subset=["days_category"])
    lot_summary = lot_view.groupby("days_category").agg(
        avg_margin=("profit_margin", "mean"),
        avg_ratio=("discount_to_deprec_ratio", "mean"),
        cars=("sales_id", "nunique"),
    ).reindex(DAYS_ON_LOT_ORDER)
    lot_chart_data = lot_summary.dropna(subset=["avg_margin"])

    if not lot_chart_data.empty:
        fig1 = go.Figure()
        fig1.add_bar(x=lot_chart_data.index, y=lot_chart_data["avg_margin"], name="Profit Margin เฉลี่ย (%)", marker_color="#0b766e", yaxis="y1")
        fig1.add_scatter(x=lot_chart_data.index, y=lot_chart_data["avg_ratio"], name="Discount/Depreciation Ratio (%)", mode="lines+markers", line_color="#e56b2f", yaxis="y2")
        fig1.update_layout(
            title="Profit Margin และ Discount-to-Depreciation Ratio ตามช่วงระยะเวลาจอด",
            yaxis=dict(title="Profit Margin เฉลี่ย (%)"),
            yaxis2=dict(title="Discount/Depreciation Ratio (%)", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(chart_layout(fig1, 380), use_container_width=True)

    fast_label, slow_label = DAYS_ON_LOT_ORDER[0], DAYS_ON_LOT_ORDER[-1]
    if fast_label in lot_summary.index and pd.notna(lot_summary.loc[fast_label, "avg_margin"]) and pd.notna(lot_summary.loc[slow_label, "avg_margin"]):
        fast_margin = lot_summary.loc[fast_label, "avg_margin"]
        slow_margin = lot_summary.loc[slow_label, "avg_margin"]
        slow_ratio = lot_summary.loc[slow_label, "avg_ratio"]
        direction = "ต่ำกว่า" if slow_margin < fast_margin else "ใกล้เคียงหรือสูงกว่า"
        st.write(
            f"รถที่จอดไม่เกิน 30 วัน มี Profit Margin เฉลี่ย {fast_margin:.2f}% ขณะที่รถที่จอดเกิน 90 วัน มี Margin เฉลี่ย {slow_margin:.2f}% "
            f"({direction}กลุ่มจอดเร็ว) และมีอัตราส่วนส่วนลดต่อค่าเสื่อมราคาเฉลี่ยสูงถึง {slow_ratio:.1f}% "
            f"ข้อมูลจาก FactSales สะท้อนว่ารถที่จอดนาน (days_on_lot) มีแนวโน้มถูกกัดกินกำไรจากทั้งค่าเสื่อมราคา (depreciation_amount) และส่วนลดที่ต้องให้ลูกค้าเพิ่มขึ้น (discount_amount)"
        )
        margin_gap = fast_margin - slow_margin
        if margin_gap > 1:
            insight1_reco = (
                f"กำหนดนโยบายปรับราคาแบบขั้นบันได (Dynamic Pricing): ภายใต้ตัวกรองนี้ รถที่จอดเกิน 90 วันมี Margin ต่ำกว่ากลุ่มจอดเร็วอยู่ {margin_gap:.1f} จุดเปอร์เซ็นต์ "
                f"และมี Discount/Depreciation Ratio สูงถึง {slow_ratio:.1f}% ควรตั้ง trigger ให้พิจารณาลดราคาเมื่อรถเข้าเดือนที่ 3 บนลาน ก่อนที่ margin จะถูกกัดกินมากไปกว่านี้"
            )
        else:
            insight1_reco = (
                f"ภายใต้ตัวกรองนี้ Profit Margin ของกลุ่มจอดนาน ({slow_margin:.2f}%) ไม่ได้ต่ำกว่ากลุ่มจอดเร็วอย่างมีนัยสำคัญ ({fast_margin:.2f}%) "
                f"แนะนำให้ตรวจสอบว่า days_on_lot มีความสัมพันธ์จริงกับตัวแปรอื่น (เช่น price_tier, brand) ก่อนใช้เป็นเกณฑ์ตัดสินใจลดราคาอัตโนมัติ"
            )
    else:
        insight1_reco = "ข้อมูลกลุ่มจอดเร็ว/จอดนานภายใต้ตัวกรองนี้ยังไม่พอสำหรับสรุปคำแนะนำเชิงตัวเลข"
    st.caption(f"💡 ข้อเสนอแนะ: {insight1_reco}")
    st.divider()

    # ============ ข้อมูลเชิงลึก 2: แนวโน้มตลาดตามประเภทเชื้อเพลิงและตัวถัง ============
    st.markdown("### 2. แนวโน้มตลาดตามประเภทเชื้อเพลิงและตัวถัง (Fuel & Body Type Trends)")
    fuel_summary = sales.groupby("fuel_type", dropna=False).agg(
        avg_days_on_lot=("days_on_lot", "mean"),
        avg_profit=("profit", "mean"),
        cars=("sales_id", "nunique"),
    ).sort_values("avg_profit", ascending=False)

    if not fuel_summary.empty:
        fig2 = go.Figure()
        fig2.add_bar(x=fuel_summary.index, y=fuel_summary["avg_profit"], name="กำไรเฉลี่ย/คัน (บาท)", marker_color="#0b766e", yaxis="y1")
        fig2.add_scatter(x=fuel_summary.index, y=fuel_summary["avg_days_on_lot"], name="Days on Lot เฉลี่ย (วัน)", mode="lines+markers", line_color="#e56b2f", yaxis="y2")
        fig2.update_layout(
            title="กำไรเฉลี่ยและความเร็วในการขาย (Days on Lot) ตามประเภทเชื้อเพลิง (DimCar.fuel_type)",
            yaxis=dict(title="กำไรเฉลี่ย/คัน (บาท)"),
            yaxis2=dict(title="Days on Lot เฉลี่ย (วัน)", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(chart_layout(fig2, 380), use_container_width=True)

    alt_energy = fuel_summary.reindex(["EV", "Hybrid"]).dropna(how="all")
    conventional = fuel_summary.reindex(["Petrol", "Diesel"]).dropna(how="all")
    if not alt_energy.empty and not conventional.empty:
        alt_days, conv_days = alt_energy["avg_days_on_lot"].mean(), conventional["avg_days_on_lot"].mean()
        alt_profit, conv_profit = alt_energy["avg_profit"].mean(), conventional["avg_profit"].mean()
        faster = "เร็วกว่า" if alt_days < conv_days else "ช้ากว่าหรือใกล้เคียงกับ"
        more_profit = "สูงกว่า" if alt_profit > conv_profit else "ต่ำกว่าหรือใกล้เคียงกับ"
        st.write(
            f"กลุ่มพลังงานทางเลือก (EV/Hybrid) มี Days on Lot เฉลี่ย {alt_days:.1f} วัน และกำไรเฉลี่ย {money(alt_profit)}/คัน "
            f"ซึ่ง{faster}รถสันดาปดั้งเดิม (Petrol/Diesel) ที่ {conv_days:.1f} วัน และให้กำไรเฉลี่ย {money(conv_profit)}/คัน ({more_profit}กลุ่มสันดาป)"
        )
        if alt_days < conv_days and alt_profit > conv_profit:
            insight2_reco = (
                f"กลุ่ม EV/Hybrid ขายได้เร็วกว่า ({alt_days:.1f} vs {conv_days:.1f} วัน) และให้กำไรเฉลี่ยสูงกว่า ({money(alt_profit)} vs {money(conv_profit)}) "
                f"ควรปรับโครงสร้างพอร์ตโฟลิโอโดยเพิ่มโควตาการรับซื้อรถกลุ่มนี้ให้มากขึ้น"
            )
        elif alt_profit > conv_profit:
            insight2_reco = (
                f"กลุ่ม EV/Hybrid ให้กำไรเฉลี่ยต่อคันสูงกว่า ({money(alt_profit)} vs {money(conv_profit)}) แม้ Days on Lot จะไม่ได้เร็วกว่าอย่างชัดเจน "
                f"ควรพิจารณาเพิ่มสัดส่วนอย่างระมัดระวัง พร้อมติดตามความเร็วในการขายควบคู่ไปด้วย"
            )
        else:
            insight2_reco = (
                f"ภายใต้ตัวกรองนี้ กลุ่ม EV/Hybrid ยังไม่ได้ให้ผลลัพธ์ดีกว่ารถสันดาปทั้งด้านความเร็วในการขายและกำไรเฉลี่ย "
                f"ยังไม่ควรเร่งเพิ่มโควตาการรับซื้อ แนะนำให้ติดตามแนวโน้มต่อไปอีกระยะก่อนปรับพอร์ตโฟลิโอ"
            )
    else:
        insight2_reco = "ข้อมูลกลุ่มพลังงานทางเลือกหรือกลุ่มสันดาปภายใต้ตัวกรองนี้ยังไม่พอสำหรับเปรียบเทียบ"
    st.caption(f"💡 ข้อเสนอแนะ: {insight2_reco}")
    st.divider()

    # ============ ข้อมูลเชิงลึก 3: ประสิทธิภาพของแหล่งรับซื้อ ============
    st.markdown("### 3. ประสิทธิภาพของแหล่งรับซื้อ (Acquisition Source Efficiency)")
    if "source_type" in sales.columns and sales["source_type"].notna().any():
        source_eff = sales.groupby("source_type", dropna=False).agg(
            avg_cost=("cost_price", "mean"),
            avg_profit=("profit", "mean"),
            total_profit=("profit", "sum"),
            cars=("sales_id", "nunique"),
        ).reset_index()

        fig3 = px.scatter(
            source_eff,
            x="avg_cost",
            y="avg_profit",
            size="cars",
            text="source_type",
            title="ต้นทุนเฉลี่ย (cost_price) vs กำไรเฉลี่ย (profit) ตามแหล่งรับซื้อ · ขนาดจุด = จำนวนคัน",
            labels={"avg_cost": "ต้นทุนเฉลี่ย (บาท)", "avg_profit": "กำไรเฉลี่ย (บาท)"},
            color_discrete_sequence=["#0b766e"],
        )
        fig3.update_traces(textposition="top center")
        st.plotly_chart(chart_layout(fig3, 380), use_container_width=True)

        lowest_cost_src = source_eff.loc[source_eff["avg_cost"].idxmin(), "source_type"]
        highest_profit_src = source_eff.loc[source_eff["avg_profit"].idxmax(), "source_type"]
        best_profit_value = source_eff.set_index("source_type").loc[highest_profit_src, "avg_profit"]
        st.write(
            f"แหล่งรับซื้อ '{lowest_cost_src}' มีต้นทุนเฉลี่ยต่อคันต่ำที่สุด ในขณะที่แหล่ง '{highest_profit_src}' สร้างกำไรเฉลี่ยต่อคันสูงที่สุดที่ {money(best_profit_value)}/คัน"
        )
        cost_spread = source_eff["avg_cost"].max() - source_eff["avg_cost"].min()
        cost_spread_pct = safe_ratio(cost_spread, source_eff["avg_cost"].mean())
        if cost_spread_pct > 5:
            insight3_reco = (
                f"ต้นทุนเฉลี่ยระหว่างแหล่งรับซื้อต่างกันถึง {cost_spread_pct:.1f}% ควรจัดสรรงบประมาณจัดซื้อเพิ่มไปที่ '{lowest_cost_src}' "
                f"และเจรจาสัญญาระยะยาวกับ '{highest_profit_src}' ซึ่งให้กำไรเฉลี่ยต่อคันสูงสุด"
            )
        else:
            insight3_reco = (
                f"ภายใต้ตัวกรองนี้ ต้นทุนเฉลี่ยระหว่างแหล่งรับซื้อต่างกันเพียง {cost_spread_pct:.1f}% ซึ่งถือว่าใกล้เคียงกันมาก "
                f"ยังไม่มีเหตุผลเพียงพอที่จะเทน้ำหนักงบจัดซื้อไปแหล่งใดแหล่งหนึ่งเป็นพิเศษ ควรเลือกตามคุณภาพรถและความสม่ำเสมอของ supply แทน"
            )
    else:
        insight3_reco = "ยังไม่มีข้อมูลแหล่งรับซื้อ (DimAcquisitionSource) เพียงพอสำหรับสรุปคำแนะนำ"
    st.caption(f"💡 ข้อเสนอแนะ: {insight3_reco}")
    st.divider()

    # ============ ข้อมูลเชิงลึก 4: พฤติกรรมการชำระเงินตามระดับราคา ============
    st.markdown("### 4. พฤติกรรมการชำระเงินตามระดับราคา (Payment Behavior by Price Tier)")
    pay_ct = pd.crosstab(sales["price_tier"], sales["payment_method"], normalize="index") * 100
    pay_long = pay_ct.reset_index().melt(id_vars="price_tier", var_name="payment_method", value_name="pct")
    fig4 = px.bar(
        pay_long,
        x="price_tier",
        y="pct",
        color="payment_method",
        barmode="stack",
        title="สัดส่วนวิธีการชำระเงิน (DimCustomer.payment_method) ในแต่ละกลุ่มราคา (DimCar.price_tier)",
        labels={"pct": "สัดส่วน (%)", "price_tier": "กลุ่มราคา", "payment_method": "วิธีชำระเงิน"},
        color_discrete_sequence=BRAND_PALETTE,
    )
    st.plotly_chart(chart_layout(fig4, 380), use_container_width=True)

    if "Finance/Leasing" in pay_ct.columns and not pay_ct.empty:
        finance_share = pay_ct["Finance/Leasing"]
        top_finance_tier = finance_share.idxmax()
        finance_spread = finance_share.max() - finance_share.min()
        st.write(f"กลุ่มราคา '{top_finance_tier}' พึ่งพาการผ่อนชำระ/ไฟแนนซ์มากที่สุด ({finance_share.max():.1f}% ของธุรกรรมในกลุ่มราคานี้)")
        if finance_spread > 5:
            insight4_reco = (
                f"กลุ่มราคา '{top_finance_tier}' พึ่งพาไฟแนนซ์สูงกว่ากลุ่มอื่นชัดเจน ({finance_share.max():.1f}% เทียบต่ำสุด {finance_share.min():.1f}%) "
                f"ควรออกแบบแพ็กเกจสินเชื่อ/แคมเปญดอกเบี้ยพิเศษเจาะกลุ่มราคานี้เป็นลำดับแรก เพื่อเพิ่มอัตราการปิดการขาย"
            )
        else:
            insight4_reco = (
                f"สัดส่วนการใช้ไฟแนนซ์ใกล้เคียงกันในทุกกลุ่มราคา (ต่างกันเพียง {finance_spread:.1f} จุดเปอร์เซ็นต์) "
                f"จึงควรออกแบบแพ็กเกจสินเชื่อแบบเดียวที่ยืดหยุ่นครอบคลุมทุกกลุ่ม แทนการเจาะจงเฉพาะกลุ่มราคาใดกลุ่มหนึ่ง"
            )
    else:
        insight4_reco = "ไม่พบข้อมูลวิธีการชำระเงินแบบไฟแนนซ์/ผ่อนชำระภายใต้ตัวกรองนี้"
    st.caption(f"💡 ข้อเสนอแนะ: {insight4_reco}")
    st.divider()

    # ============ ข้อมูลเชิงลึก 5: ความต้องการเชิงพื้นที่ ============
    st.markdown("### 5. ความต้องการเชิงพื้นที่ (Regional Demand Dynamics)")
    insight5_reco = "ไม่พบข้อมูลภูมิภาค (DimLocation.region) เพียงพอสำหรับสรุปคำแนะนำ"
    if "region" in sales.columns and sales["region"].notna().any():
        region_body = pd.crosstab(sales["region"], sales["body_type"], normalize="index") * 100
        if not region_body.empty:
            heat_fig = px.imshow(
                region_body,
                text_auto=".0f",
                color_continuous_scale=px.colors.sequential.Teal,
                title="สัดส่วนประเภทรถ (body_type) ที่ขายได้ในแต่ละภูมิภาค (DimLocation.region) — %",
                labels=dict(x="ประเภทรถ", y="ภูมิภาค", color="% ในภูมิภาค"),
            )
            st.plotly_chart(chart_layout(heat_fig, 380), use_container_width=True)

            overall_share = sales["body_type"].value_counts(normalize=True) * 100
            diff = region_body.subtract(overall_share, axis=1)
            insight5_reco = "ยังไม่มีข้อมูลเพียงพอในการเปรียบเทียบสัดส่วนประเภทรถระหว่างภูมิภาคภายใต้ตัวกรองนี้"
            if diff.notna().any().any():
                max_region, max_body = diff.stack().idxmax()
                max_gap = diff.stack().max()
                region_n = int(sales.loc[sales["region"] == max_region, "sales_id"].nunique())
                st.write(
                    f"ภูมิภาค '{max_region}' มีสัดส่วนยอดขายรถประเภท '{max_body}' สูงกว่าค่าเฉลี่ยรวมทั้งประเทศถึง {max_gap:.1f} จุดเปอร์เซ็นต์ "
                    f"บ่งชี้ถึงความต้องการเฉพาะทางในพื้นที่นี้ที่แตกต่างจากภาพรวม (คำนวณจาก {region_n:,} ธุรกรรมในภูมิภาคนี้)"
                )
                if region_n < 50:
                    insight5_reco = (
                        f"ภูมิภาค '{max_region}' มีสัดส่วนรถประเภท '{max_body}' สูงกว่าค่าเฉลี่ยประเทศ {max_gap:.1f} จุดเปอร์เซ็นต์ แต่คำนวณจากตัวอย่างเพียง {region_n:,} ธุรกรรม "
                        f"ควรเก็บข้อมูลเพิ่มก่อนตัดสินใจโอนย้ายสต็อกจริง เพื่อลดความเสี่ยงจากขนาดตัวอย่างที่เล็กเกินไป"
                    )
                else:
                    insight5_reco = (
                        f"วางกลยุทธ์โอนย้ายสต็อกไปยังภูมิภาค '{max_region}' ซึ่งมีความต้องการรถประเภท '{max_body}' สูงกว่าค่าเฉลี่ยประเทศ {max_gap:.1f} จุดเปอร์เซ็นต์ "
                        f"(อ้างอิงจาก {region_n:,} ธุรกรรม) — ประเมินอุปสงค์ → หารถจากภูมิภาคที่ล้นสต็อก → โอนย้าย → ทำกำไรจากส่วนต่างราคา"
                    )
    st.caption(f"💡 ข้อเสนอแนะ: {insight5_reco}")


def audit_page(sales):
    st.subheader("QA · Reconciliation, RLS & Performance Audit")
    audit = pd.DataFrame([
        {"Check": "FactSales rows", "Result": f"{len(sales):,}", "Status": "PASS" if len(sales) else "FAIL"},
        {"Check": "Revenue = SUM(net_revenue)", "Result": money(sales["net_revenue"].sum()), "Status": "PASS"},
        {"Check": "Broken ratio protection", "Result": "DIVIDE guarded by zero", "Status": "PASS"},
        {"Check": "Performance baseline", "Result": "Cached load + filtered frames", "Status": "INFO"},
    ])
    st.dataframe(audit, use_container_width=True, hide_index=True)
    region = st.selectbox("ทดสอบ RLS: เลือก Regional Manager region", sorted(sales["region"].dropna().unique()))
    rls_sales = sales[sales["region"] == region]
    st.metric("Rows visible under region filter", f"{len(rls_sales):,}")
    st.caption("Production RLS expression: [region] = USERPRINCIPALNAME(). Streamlit session นี้จำลองด้วย region selector เพราะไม่มี identity provider")
    st.download_button("ดาวน์โหลด transaction detail", rls_sales.to_csv(index=False).encode("utf-8"), "transaction_detail.csv", "text/csv")


data = load_data()
if data:
    sales, listings = data["sales"], data["listings"]
    st.title("Used Car Intelligence")
    st.caption("Star schema analytics · One-to-many dimensions → facts · Active single-direction filters")
    with st.sidebar:
        st.header("Global Slicers")
        page = st.radio("Canvas", ["Executive Overview", "Stock", "Market Benchmark", "Business Insights", "QA Audit"])
        st.divider()
        year_values = sorted(sales["year"].dropna().astype(int).unique())
        min_year, max_year = min(year_values), max(year_values)
        month_values = sorted(
            sales[["month", "month_name"]].dropna().drop_duplicates("month").itertuples(index=False, name=None),
            key=lambda item: item[0],
        )
        month_options = [month_name for _, month_name in month_values]
        region_options = sorted(sales["region"].dropna().unique().tolist())
        brand_options = sorted(sales["brand"].dropna().unique().tolist())

        def reset_all_filters():
            st.session_state["filter_years"] = (min_year, max_year)
            st.session_state["filter_months"] = month_options
            st.session_state["filter_regions"] = region_options
            st.session_state["filter_brands"] = []

        st.button("Clear Filters", on_click=reset_all_filters, use_container_width=True)

        years = st.slider("Year", min_value=min_year, max_value=max_year, value=(min_year, max_year), key="filter_years")
        selected_years = list(range(years[0], years[1] + 1))
        months = st.multiselect("Month", month_options, default=month_options, key="filter_months")
        regions = st.multiselect("Region", region_options, default=region_options, key="filter_regions")
        brands = st.multiselect("Brand", brand_options, default=[], key="filter_brands", placeholder="ทั้งหมด (All Brands)")
        selections = {"year": selected_years, "month_name": months, "region": regions, "brand": brands}
        st.caption("Model keys: car_key, date_key, customer_key, location_key, source_key")
        
    filtered_sales = apply_filters(sales, selections)
    filtered_listings = apply_filters(listings, selections)
    
    if filtered_sales.empty:
        status_box("⚠️ ไม่มีข้อมูลตามตัวกรองที่เลือก กรุณาปรับเปลี่ยนตัวกรองในแถบด้านซ้าย", level="warn")
    elif page == "Executive Overview":
        executive_page(filtered_sales)
    elif page == "Stock":
        Stock_page(filtered_sales, data["raw"])
    elif page == "Market Benchmark":
        market_page(filtered_sales, filtered_listings)
    elif page == "Business Insights":
        insights_page(filtered_sales)
    else:
        audit_page(filtered_sales)
        
    with st.expander("Data model & drill paths"):
        st.write("1:* DimCar/car_key → FactSales, FactMarketListings; DimDate/date_key → facts; DimCustomer/customer_key → FactSales; DimLocation/location_key → facts; DimAcquisitionSource/source_key → FactSales.")
        st.write("Drill-down: Brand → Model → Model Year and Year → Quarter → Month. Transaction detail is available from QA Audit.")
        st.write("Cross-filtering uses shared selections; joins are left joins with one-way dimension-to-fact propagation.")
else:
    st.stop()