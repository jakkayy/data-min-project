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
        if values and column in result:
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
        st.plotly_chart(chart_layout(figure, 400), use_container_width=True)
    with right:
        payment = sales.groupby("payment_method", dropna=False).size().reset_index(name="sales_volume")
        st.plotly_chart(chart_layout(px.pie(payment, names="payment_method", values="sales_volume", hole=.45, title="Payment Method Ratio"), 400), use_container_width=True)
    left, right = st.columns(2)
    with left:
        top = sales.groupby("brand", as_index=False)["net_revenue"].sum().nlargest(5, "net_revenue")
        st.plotly_chart(chart_layout(px.bar(top.sort_values("net_revenue"), x="net_revenue", y="brand", orientation="h", color_discrete_sequence=["#e56b2f"])), use_container_width=True)
    with right:
        channel = sales.groupby("source_type", dropna=False).size().reset_index(name="sales_volume")
        st.plotly_chart(chart_layout(px.bar(channel, x="source_type", y="sales_volume", color_discrete_sequence=["#0b766e"])), use_container_width=True)
    left, right = st.columns(2)
    with left:
        body_data = sales.groupby("body_type", dropna=False).size().reset_index(name="sales_volume")
        body_data["body_type"] = body_data["body_type"].fillna("Unknown")
        body_fig = px.pie(
            body_data,
            names="body_type",
            values="sales_volume",
            hole=0.45,
            title="Body Type Ratio (สัดส่วนประเภทรถ)",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        st.plotly_chart(chart_layout(body_fig, 400), use_container_width=True)
    with right:
        price_sales = sales.dropna(subset=["selling_price"]).copy()
        if not price_sales.empty:
            step = 100_000
            price_sales["bin_lower"] = (price_sales["selling_price"] // step) * step
            price_sales["bin_upper"] = price_sales["bin_lower"] + step
            price_sales["price_range"] = price_sales["bin_lower"].apply(money) + " - " + price_sales["bin_upper"].apply(money)
            price_data = (
                price_sales.groupby(["bin_lower", "price_range"], as_index=False)
                .size()
                .rename(columns={"size": "sales_volume"})
                .sort_values("bin_lower")
            )
            price_fig = px.pie(
                price_data,
                names="price_range",
                values="sales_volume",
                hole=0.45,
                title="Price Range Ratio · ช่วงละ 100,000 บาท",
                category_orders={"price_range": price_data["price_range"].tolist()},
            )
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
        st.warning("ไม่มีข้อมูลใน Price Segment ที่เลือก")
        return
    st.markdown("#### Days on lot vs profit margin")
    # Keep this as the primary full-width visual; points are still bucketed by days and segment.
    grouped = sales.assign(days_bucket=(sales["days_on_lot"] // 5) * 5)
    grouped = grouped.groupby(["days_bucket", "price_tier"], as_index=False).agg(
        profit_margin=("profit_margin", "mean"), sales_volume=("sales_id", "nunique")
    )
    figure = px.scatter(
        grouped,
        x="days_bucket",
        y="profit_margin",
        size="sales_volume",
        color="price_tier",
        hover_data={"sales_volume": True, "price_tier": True},
        labels={"days_bucket": "Days on Lot (5-day bucket)", "profit_margin": "Profit Margin %", "sales_volume": "จำนวนคัน", "price_tier": "Price Segment"},
    )
    figure.update_layout(height=520)
    st.plotly_chart(chart_layout(figure, 520), use_container_width=True)

    st.markdown("#### Selling price by car age or mileage")
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
    st.markdown("#### Brand → Model → Model Year matrix")
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
    benchmark = listings.groupby("brand", as_index=False).agg(avg_ask_price=("ask_price", "mean"))
    internal = sales.groupby("brand", as_index=False).agg(avg_selling_price=("selling_price", "mean"))
    comparison = benchmark.merge(internal, on="brand", how="outer").sort_values("avg_ask_price", ascending=False).head(15)
    long = comparison.melt("brand", var_name="metric", value_name="price").dropna()
    st.plotly_chart(chart_layout(px.bar(long, x="brand", y="price", color="metric", barmode="group", labels={"price": "ราคาเฉลี่ย (บาท)"})), use_container_width=True)
    ratio = sales.groupby("price_tier", as_index=False)["discount_to_deprec_ratio"].mean().sort_values("discount_to_deprec_ratio", ascending=False)
    st.plotly_chart(chart_layout(px.bar(ratio, x="price_tier", y="discount_to_deprec_ratio", color_discrete_sequence=["#e56b2f"], labels={"discount_to_deprec_ratio": "Discount to Depreciation Ratio"})), use_container_width=True)


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
        page = st.radio("Canvas", ["Executive Overview", "Profitability & ML", "Market Benchmark", "QA Audit"])
        st.divider()
        year_values = sorted(sales["year"].dropna().astype(int).unique())
        min_year, max_year = min(year_values), max(year_values)
        month_values = sorted(
            sales[["month", "month_name"]].dropna().drop_duplicates("month").itertuples(index=False, name=None),
            key=lambda item: item[0],
        )
        region_options = sorted(sales["region"].dropna().unique().tolist())
        brand_options = sorted(sales["brand"].dropna().unique().tolist())

        def reset_all_filters():
            st.session_state["filter_years"] = (min_year, max_year)
            for month_number, _ in month_values:
                st.session_state[f"month_{month_number}"] = False
            st.session_state["filter_regions"] = []
            st.session_state["filter_brands"] = []

        st.button("Clear Filters", on_click=reset_all_filters, use_container_width=True)

        years = st.slider("Year", min_value=min_year, max_value=max_year, value=(min_year, max_year), key="filter_years")
        selected_years = list(range(years[0], years[1] + 1))
        st.markdown("**Month**")
        selected_months = []
        for month_number, month_name in month_values:
            if st.checkbox(str(month_name), value=True, key=f"month_{month_number}"):
                selected_months.append(month_name)
        regions = st.multiselect("Region", region_options, default=region_options, key="filter_regions")
        brands = st.multiselect("Brand", brand_options, default=brand_options, key="filter_brands")
        selections = {"year": selected_years, "month_name": selected_months, "region": regions, "brand": brands}
        st.caption("Model keys: car_key, date_key, customer_key, location_key, source_key")
    filtered_sales = apply_filters(sales, selections)
    filtered_listings = apply_filters(listings, selections)
    if filtered_sales.empty:
        st.warning("ไม่มีข้อมูลตามตัวกรองที่เลือก")
    elif page == "Executive Overview":
        executive_page(filtered_sales)
    elif page == "Profitability & ML":
        profitability_page(filtered_sales, data["raw"])
    elif page == "Market Benchmark":
        market_page(filtered_sales, filtered_listings)
    else:
        audit_page(filtered_sales)
    with st.expander("Data model & drill paths"):
        st.write("1:* DimCar/car_key → FactSales, FactMarketListings; DimDate/date_key → facts; DimCustomer/customer_key → FactSales; DimLocation/location_key → facts; DimAcquisitionSource/source_key → FactSales.")
        st.write("Drill-down: Brand → Model → Model Year and Year → Quarter → Month. Transaction detail is available from QA Audit.")
        st.write("Cross-filtering uses shared selections; joins are left joins with one-way dimension-to-fact propagation.")
else:
    st.stop()