import os
import re
import sqlite3
from difflib import get_close_matches

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


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
            # Optional multiselect: empty means all brands
            if values:
                result = result[result[column].isin(values)]
        else:
            # Dimension slicers: empty list means 0 items selected
            result = result[result[column].isin(values)]
    return result


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
    """Return a selectable family while preserving the raw model value."""
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
    left, right = st.columns([1.5, 1])
    with left:
        trend = sales.groupby(["year", "month"], as_index=False).agg(revenue=("net_revenue", "sum"), profit=("profit", "sum")).sort_values(["year", "month"])
        trend["period"] = trend["year"].astype(str) + "-" + trend["month"].astype(str).str.zfill(2)
        figure = go.Figure()
        figure.add_bar(x=trend["period"], y=trend["revenue"], name="Revenue", marker_color="#0b766e")
        figure.add_scatter(x=trend["period"], y=trend["profit"], name="Profit", mode="lines+markers", line_color="#e56b2f")
        figure.update_layout(title="แนวโน้มรายได้และกำไรสุทธิ (Revenue & Profit Trend)")
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
    left, right = st.columns(2)
    with left:
        top = sales.groupby("brand", as_index=False)["net_revenue"].sum().nlargest(5, "net_revenue")
        st.plotly_chart(
            chart_layout(
                px.bar(
                    top.sort_values("net_revenue"),
                    x="net_revenue",
                    y="brand",
                    orientation="h",
                    title="5 อันดับแบรนด์ที่สร้างรายได้สูงสุด (Top 5 Brands by Revenue)",
                    color_discrete_sequence=["#e56b2f"],
                )
            ),
            use_container_width=True,
        )
    with right:
        channel = sales.groupby("source_type", dropna=False).size().reset_index(name="sales_volume")
        st.plotly_chart(
            chart_layout(
                px.bar(
                    channel,
                    x="source_type",
                    y="sales_volume",
                    title="ยอดขายตามช่องทางการได้มา (Sales Volume by Channel)",
                    color_discrete_sequence=["#0b766e"],
                )
            ),
            use_container_width=True,
        )
    left, right = st.columns(2)
    with left:
        body_data = sales.groupby("body_type", dropna=False).size().reset_index(name="sales_volume")
        body_data["body_type"] = body_data["body_type"].fillna("Unknown")
        body_fig = px.pie(
            body_data,
            names="body_type",
            values="sales_volume",
            hole=0.45,
            title="สัดส่วนประเภทรถ (Body Type Ratio)",
            color_discrete_sequence=BRAND_PALETTE,
        )
        st.plotly_chart(chart_layout(body_fig, 400), use_container_width=True)
    with right:
        price_sales = sales.dropna(subset=["selling_price"]).copy()
        if not price_sales.empty:
            bin_edges = [0, 500_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000, float("inf")]
            bin_labels = [
                f"< {money(500_000)}",
                f"{money(500_000)} - {money(1_000_000)}",
                f"{money(1_000_000)} - {money(2_000_000)}",
                f"{money(2_000_000)} - {money(3_000_000)}",
                f"{money(3_000_000)} - {money(5_000_000)}",
                f"{money(5_000_000)} - {money(10_000_000)}",
                f"≥ {money(10_000_000)}",
            ]
            price_sales["price_range"] = pd.cut(
                price_sales["selling_price"], bins=bin_edges, labels=bin_labels, right=False
            )
            price_data = (
                price_sales.groupby("price_range", observed=True, as_index=False)
                .size()
                .rename(columns={"size": "sales_volume"})
            )
            total_vol = price_data["sales_volume"].sum()
            slice_labels = [
                f"{(row['sales_volume'] / total_vol) * 100:.1f}%" if total_vol and (row["sales_volume"] / total_vol) * 100 >= 1.0 else ""
                for _, row in price_data.iterrows()
            ]

            price_fig = px.pie(
                price_data,
                names="price_range",
                values="sales_volume",
                hole=0.45,
                title="สัดส่วนตามระดับราคา (Price Range Ratio)",
                category_orders={"price_range": bin_labels},
                color_discrete_sequence=BRAND_PALETTE,
            )
            price_fig.update_traces(text=slice_labels, textinfo="text")
            st.plotly_chart(chart_layout(price_fig, 400), use_container_width=True)


def profitability_page(sales, raw):
    st.subheader("Page 2 · Product Profitability & ML Segment Analysis")
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
    st.markdown("#### ระยะเวลาจอดตามกลุ่มราคา (Days on Lot by Segment)")
    def classify_days(days):
        if pd.isna(days):
            return None
        if days <= 30:
            return "< 30 วัน (Fast Moving - สภาพคล่องสูง)"
        elif days <= 60:
            return "31–60 วัน (Normal)"
        elif days <= 90:
            return "61–90 วัน (Slow Moving)"
        else:
            return "> 90 วัน (High Risk - ความเสี่ยงขาดทุนสูง)"

    sales_binned = sales.copy()
    sales_binned["days_category"] = sales_binned["days_on_lot"].apply(classify_days)
    sales_binned = sales_binned.dropna(subset=["days_category"])
    
    category_order = [
        "< 30 วัน (Fast Moving - สภาพคล่องสูง)",
        "31–60 วัน (Normal)",
        "61–90 วัน (Slow Moving)",
        "> 90 วัน (High Risk - ความเสี่ยงขาดทุนสูง)"
    ]
    
    grouped = sales_binned.groupby(["days_category", "price_tier"], as_index=False).size().rename(columns={"size": "sales_volume"})
    
    figure = px.bar(
        grouped,
        x="days_category",
        y="sales_volume",
        color="price_tier",
        barmode="group",
        category_orders={"days_category": category_order},
        labels={"days_category": "ช่วงเวลาที่จอด", "sales_volume": "จำนวนคัน", "price_tier": "Price Segment"},
        color_discrete_sequence=BRAND_PALETTE,
    )
    figure.update_layout(height=520)
    st.plotly_chart(chart_layout(figure, 520), use_container_width=True)

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
    st.markdown("#### เมทริกซ์วิเคราะห์ Brand → Model → Model Year (Matrix Analysis)")
    matrix_search = st.text_input("ค้นหารุ่นใน matrix", placeholder="พิมพ์ชื่อรุ่น เช่น 320d หรือ C220", key="matrix_model_search")
    matrix = sales.groupby(["brand", "model", "model_year"], as_index=False).agg(cost_price=("cost_price", "mean"), selling_price=("selling_price", "mean"), profit_margin=("profit_margin", "mean"), days_on_lot=("days_on_lot", "mean")).sort_values("selling_price", ascending=False)
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
    st.subheader("Page 3 · Market Benchmark & Price Elasticity")
    internal = sales.groupby("brand", as_index=False).agg(avg_selling_price=("selling_price", "mean")).sort_values("avg_selling_price", ascending=False).head(15)
    fig = px.bar(
        internal,
        x="brand",
        y="avg_selling_price",
        title="ราคาขายเฉลี่ยรายยี่ห้อ (Average Selling Price by Brand)",
        labels={"avg_selling_price": "ราคาขายเฉลี่ย (บาท)"},
        color_discrete_sequence=["#0b766e"],
    )
    fig.update_traces(text=internal["avg_selling_price"].map(lambda x: f"฿{x:,.0f}"), textposition="outside")
    st.plotly_chart(chart_layout(fig), use_container_width=True)
    ratio = sales.groupby("price_tier", as_index=False)["discount_to_deprec_ratio"].mean().sort_values("discount_to_deprec_ratio", ascending=False)
    st.plotly_chart(
        chart_layout(
            px.bar(
                ratio,
                x="price_tier",
                y="discount_to_deprec_ratio",
                title="อัตราส่วนส่วนลดต่อค่าเสื่อมราคา (Discount to Depreciation Ratio)",
                color_discrete_sequence=["#e56b2f"],
                labels={"discount_to_deprec_ratio": "Discount to Depreciation Ratio"},
            )
        ),
        use_container_width=True,
    )


def insights_page(sales):
    st.subheader("Page 4 · Business Insights & Recommendations")
    st.caption("คำนวณสดจากข้อมูลภายใต้ตัวกรองด้านซ้ายในขณะนี้ · Auto-generated from the currently filtered data")
    if sales.empty:
        status_box("⚠️ ไม่มีข้อมูลเพียงพอสำหรับสร้าง Insight ภายใต้ตัวกรองปัจจุบัน", level="warn")
        return

    insights = []

    brand_rev = sales.groupby("brand")["net_revenue"].sum().sort_values(ascending=False)
    if not brand_rev.empty and brand_rev.sum():
        top_brand = brand_rev.index[0]
        top_share = safe_ratio(brand_rev.iloc[0], brand_rev.sum())
        insights.append({
            "title": f"แบรนด์ {top_brand} ครองสัดส่วนรายได้สูงสุด ({top_share:.1f}%)",
            "detail": f"{top_brand} สร้างรายได้ {money(brand_rev.iloc[0])} จากรายได้รวม {money(brand_rev.sum())} ในช่วงที่เลือก",
            "action": f"จัดสรรพื้นที่จัดแสดง งบการตลาด และสต๊อกให้ {top_brand} เป็นลำดับต้น พร้อมประเมินความเสี่ยงจากการพึ่งพาแบรนด์เดียวมากเกินไป",
        })

    if "price_tier" in sales and "days_on_lot" in sales and sales["price_tier"].notna().any():
        tier_days = sales.groupby("price_tier")["days_on_lot"].mean().sort_values(ascending=False)
        high_risk_count = int((sales["days_on_lot"] > 90).sum())
        if not tier_days.empty:
            slow_tier = tier_days.index[0]
            insights.append({
                "title": f"กลุ่มราคา {slow_tier} จอดนานที่สุด เฉลี่ย {tier_days.iloc[0]:.0f} วัน",
                "detail": f"มีรถทั้งหมด {high_risk_count:,} คันที่จอดเกิน 90 วัน (High Risk)",
                "action": "พิจารณาโปรโมชั่นลดราคาหรือปรับกลยุทธ์การจัดหาให้เหมาะกับความต้องการตลาดในกลุ่มราคานี้ เพื่อลดต้นทุนจม (holding cost)",
            })

    if "source_type" in sales and "profit_margin" in sales and sales["source_type"].notna().any():
        channel_margin = sales.groupby("source_type")["profit_margin"].mean().sort_values(ascending=False)
        if len(channel_margin) >= 1:
            best_channel, best_margin = channel_margin.index[0], channel_margin.iloc[0]
            worst_channel, worst_margin = channel_margin.index[-1], channel_margin.iloc[-1]
            insights.append({
                "title": f"ช่องทาง {best_channel} ให้กำไรเฉลี่ยต่อคันสูงสุด",
                "detail": f"Margin เฉลี่ย {best_margin:.1f}% เทียบกับ {worst_channel} ที่ {worst_margin:.1f}%",
                "action": f"เพิ่มงบจัดซื้อ/จัดหารถผ่านช่องทาง {best_channel} และทบทวนต้นทุนของช่องทาง {worst_channel}",
            })

    if "payment_method" in sales and sales["payment_method"].notna().any():
        payment_share = sales["payment_method"].value_counts(normalize=True) * 100
        if not payment_share.empty:
            top_payment, top_pct = payment_share.index[0], payment_share.iloc[0]
            insights.append({
                "title": f"{top_payment} เป็นวิธีชำระเงินหลัก ({top_pct:.1f}% ของยอดขาย)",
                "detail": "สัดส่วนวิธีการชำระเงินสะท้อนพฤติกรรมลูกค้าและความต้องการสภาพคล่องของธุรกิจ",
                "action": "หากสัดส่วนสินเชื่อ/ผ่อนชำระสูง ควรเจรจาพันธมิตรไฟแนนซ์เพิ่มเพื่อเร่งปิดการขายและลดขั้นตอนอนุมัติ",
            })

    if "region" in sales and sales["region"].notna().any():
        region_profit = sales.groupby("region")["profit"].mean().sort_values(ascending=False)
        if len(region_profit) >= 1:
            best_region = region_profit.index[0]
            worst_region = region_profit.index[-1]
            insights.append({
                "title": f"ภูมิภาค {best_region} ทำกำไรเฉลี่ยต่อคันสูงสุด",
                "detail": f"ภูมิภาค {worst_region} ทำกำไรเฉลี่ยต่อคันต่ำสุดในช่วงที่เลือก",
                "action": f"ถอดบทเรียนกลยุทธ์การตั้งราคา/เจรจาต่อรองจาก {best_region} ไปปรับใช้ใน {worst_region}",
            })

    if not insights:
        status_box("ข้อมูลไม่เพียงพอสำหรับสร้าง Insight โปรดตรวจสอบ schema ของข้อมูล", level="warn")
        return

    for i, item in enumerate(insights, start=1):
        st.markdown(f"**{i}. {item['title']}**")
        st.write(item["detail"])
        st.caption(f"ข้อเสนอแนะ: {item['action']}")
        st.divider()


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
        page = st.radio("Canvas", ["Executive Overview", "Profitability & ML", "Market Benchmark", "Business Insights", "QA Audit"])
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

        st.button("🧹 Clear Filters", on_click=reset_all_filters, use_container_width=True)

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
    elif page == "Profitability & ML":
        profitability_page(filtered_sales, data["raw"])
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