import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- PAGE CONFIGURATION (Premium Light Theme) ---
st.set_page_config(
    page_title="Used Car DW Analytics Dashboard",
    page_icon="car",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM PREMIUM LIGHT CSS SYSTEM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .main {
        font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif !important;
        background-color: #ffffff;
        color: #1f2937;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif !important;
        font-weight: 700;
        color: #111827 !important;
    }
    
    .stMetric {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
    }
    
    div[data-testid="stMetricValue"] {
        font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif !important;
        font-weight: 700;
        color: #2563eb !important;
        font-size: 28px !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif !important;
        color: #4b5563 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }

    .stSelectbox label, .stMultiSelect label {
        font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif !important;
        color: #374151 !important;
        font-weight: 600 !important;
    }
    
    .insight-card {
        font-family: 'IBM Plex Sans', 'IBM Plex Sans Thai', sans-serif !important;
        background-color: #f8f9fa;
        border-left: 5px solid #0d9488;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-top: 1px solid #e5e7eb;
        border-right: 1px solid #e5e7eb;
        border-bottom: 1px solid #e5e7eb;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    
    .insight-card h4 {
        margin-top: 0;
        color: #0d9488 !important;
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 6px;
    }
    
    .insight-card p {
        color: #4b5563;
        font-size: 14px;
        margin-bottom: 0;
        line-height: 1.5;
    }

    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 16px !important;
        background-color: #f3f4f6 !important;
        border-radius: 6px !important;
        border: 1px solid #e5e7eb !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE CONNECTION & LOADING (Dynamic relative path) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "used_car_dw.db")
if not os.path.exists(db_path):
    db_path = os.path.abspath(os.path.join(BASE_DIR, "..", "03_Data_Warehouse", "used_car_dw.db"))

@st.cache_data
def load_data():
    if not os.path.exists(db_path):
        st.error(f"ไม่พบไฟล์ฐานข้อมูล used_car_dw.db ที่ {db_path} กรุณาตรวจสอบว่ามีไฟล์อยู่ในโฟลเดอร์ 03_Data_Warehouse หรือไม่")
        return None, None, None, None, None

    conn = sqlite3.connect(db_path)
    
    df_sales = pd.read_sql_query("SELECT * FROM FactSales", conn)
    df_car = pd.read_sql_query("SELECT * FROM DimCar", conn)
    df_date = pd.read_sql_query("SELECT * FROM DimDate", conn)
    df_location = pd.read_sql_query("SELECT * FROM DimLocation", conn)
    df_customer = pd.read_sql_query("SELECT * FROM DimCustomer", conn)
    df_listings = pd.read_sql_query("SELECT * FROM FactMarketListings", conn)
    
    conn.close()
    
    m_sales = df_sales.merge(df_car, on='car_key', how='left')
    m_sales = m_sales.merge(df_date, on='date_key', how='left')
    m_sales = m_sales.merge(df_location, on='location_key', how='left')
    m_sales = m_sales.merge(df_customer, on='customer_key', how='left')
    
    m_listings = df_listings.merge(df_car, on='car_key', how='left')
    m_listings = m_listings.merge(df_date, on='date_key', how='left')
    m_listings = m_listings.merge(df_location, on='location_key', how='left')
    
    return m_sales, m_listings, df_car, df_location, df_date

m_sales, m_listings, df_car, df_location, df_date = load_data()

# --- INTERACTIVE RENDER ---
if m_sales is not None:
    # Title Header
    st.title("Used Car DW & Analytics Dashboard")
    st.markdown("ระบบวิเคราะห์ข้อมูลยอดขายและข้อมูลการลงประกาศตลาดรถยนต์มือสองแบบครบวงจร (Star Schema Model)")
    st.markdown("---")

    # ==========================================
    # --- SECTION 1: HIGH-LEVEL KPIS ---
    # ==========================================
    # ดึงตัวเลือกตั้งต้นสำหรับ Filter
    all_brands = sorted(list(m_sales['brand'].unique()))
    all_regions = sorted(list(m_sales['region'].dropna().unique()))
    all_years = sorted(list(m_sales['year'].dropna().unique()))

    # ==========================================
    # --- SECTION 2: INTERACTIVE FILTERS (อยู่บน Key Insights) ---
    # ==========================================
    st.subheader("ตัวกรองข้อมูลและความคุมแอนิเมชัน (Interactive Filters)")
    
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
    
    with ctrl_col1:
        brand_sort_option = st.selectbox(
            "เรียงลำดับแบรนด์รถยนต์ตาม:",
            ["เรียงตามตัวอักษร (A-Z)", "เรียงตามยอดขายสูงสุด", "เรียงตามจำนวนคันที่ขายสูงสุด"]
        )
        
        if brand_sort_option == "เรียงตามยอดขายสูงสุด":
            sorted_brands = m_sales.groupby('brand')['selling_price'].sum().sort_values(ascending=False).index.tolist()
        elif brand_sort_option == "เรียงตามจำนวนคันที่ขายสูงสุด":
            sorted_brands = m_sales.groupby('brand')['quantity'].sum().sort_values(ascending=False).index.tolist()
        else:
            sorted_brands = sorted(list(m_sales['brand'].unique()))

        selected_brands = st.multiselect(
            "เลือกแบรนด์รถยนต์ (Car Brand)", 
            sorted_brands, 
            default=[]
        )
    with ctrl_col2:
        selected_regions = st.multiselect(
            "เลือกภูมิภาค (Region)", 
            all_regions, 
            default=all_regions
        )
    with ctrl_col3:
        selected_years = st.multiselect(
            "เลือกปี (Year)", 
            all_years, 
            default=all_years
        )

    # กรองข้อมูลตามที่ผู้ใช้เลือกในตัวกรองด้านบน (ถ้าไม่เลือกแบรนด์ ให้แสดงทั้งหมด)
    brand_cond = m_sales['brand'].isin(selected_brands) if len(selected_brands) > 0 else True
    region_cond = m_sales['region'].isin(selected_regions) if len(selected_regions) > 0 else True
    year_cond = m_sales['year'].isin(selected_years) if len(selected_years) > 0 else True

    filtered_sales = m_sales[brand_cond & region_cond & year_cond]
    
    list_brand_cond = m_listings['brand'].isin(selected_brands) if len(selected_brands) > 0 else True
    list_region_cond = m_listings['region'].isin(selected_regions) if len(selected_regions) > 0 else True
    list_year_cond = m_listings['year'].isin(selected_years) if len(selected_years) > 0 else True

    filtered_listings = m_listings[list_brand_cond & list_region_cond & list_year_cond]

    st.markdown(" ")

    # คำนวณ KPIs
    total_sales_revenue = filtered_sales['selling_price'].sum()
    total_profit = filtered_sales['profit'].sum()
    avg_days_on_lot = filtered_sales['days_on_lot'].mean() if not filtered_sales['days_on_lot'].empty else 0
    total_quantity = filtered_sales['quantity'].sum()

    st.subheader("ข้อมูลภาพรวมหลัก (High-Level KPIs)")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric("ยอดขายสุทธิ (Sales Amount)", f"฿{total_sales_revenue:,.2f}")
    kpi_col2.metric("กำไรสุทธิ (Total Profit)", f"฿{total_profit:,.2f}")
    kpi_col3.metric("จำนวนวันจอดเฉลี่ย (Avg Days on Lot)", f"{avg_days_on_lot:.1f} วัน")
    kpi_col4.metric("จำนวนคันที่ขายออก (Cars Sold)", f"{total_quantity:,} คัน")
    
    st.markdown(" ")

    # ==========================================
    # --- SECTION 3: KEY INSIGHTS (อยู่ล่าง Interactive Filters) ---
    # ==========================================
    st.subheader("บทวิเคราะห์และข้อเสนอแนะทางธุรกิจหลัก (Key Insights)")
    
    brand_sales_summary = filtered_sales.groupby('brand')['selling_price'].sum().reset_index()
    top_brand = brand_sales_summary.sort_values('selling_price', ascending=False).iloc[0]['brand'] if not brand_sales_summary.empty else "N/A"
    top_brand_rev = brand_sales_summary.sort_values('selling_price', ascending=False).iloc[0]['selling_price'] if not brand_sales_summary.empty else 0
    
    region_sales_summary = filtered_sales.groupby('region')['selling_price'].sum().reset_index()
    top_region = region_sales_summary.sort_values('selling_price', ascending=False).iloc[0]['region'] if not region_sales_summary.empty else "N/A"
    
    avg_discount = filtered_sales['discount_amount'].mean() if not filtered_sales['discount_amount'].empty else 0
    avg_profit_margin = filtered_sales['profit_margin'].mean() if not filtered_sales['profit_margin'].empty else 0

    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        st.markdown(f"""
        <div class="insight-card">
            <h4>1. แบรนด์รถยนต์สร้างรายได้สูงสุด</h4>
            <p>แบรนด์ <b>{top_brand}</b> สร้างส่วนแบ่งยอดขายสูงสุดเป็นเงิน <b>฿{top_brand_rev:,.2f}</b> แนะนำให้มุ่งเพิ่มสต็อกรถยี่ห้อนี้และแบรนด์รองท็อปเพื่อสร้างสภาพคล่องสูงสุด</p>
        </div>
        <div class="insight-card">
            <h4>2. ภูมิภาคยุทธศาสตร์การขาย</h4>
            <p>พื้นที่เขต <b>{top_region}</b> ครองสัดส่วนรายได้หลักของธุรกิจ ควรให้ความสำคัญด้านคลังสินค้าและการวางงบการตลาดเป้าหมายในพื้นที่จังหวัดเหล่านี้</p>
        </div>
        <div class="insight-card">
            <h4>3. กลยุทธ์ราคาและผลกำไร</h4>
            <p>ปัจจุบันมอบส่วนลดเฉลี่ยอยู่ที่ <b>฿{avg_discount:,.2f} ต่อคัน</b> และมีอัตรากำไรเฉลี่ย <b>{avg_profit_margin:.2f}%</b> การเพิ่มกำไรสามารถทำได้โดยลดส่วนลดกลุ่มรุ่นที่เป็นกระแสตลาดลง 1-2%</p>
        </div>
        """, unsafe_allow_html=True)
        
    with insight_col2:
        st.markdown("""
        <div class="insight-card">
            <h4>4. ความสัมพันธ์ของอายุรถกับราคากลาง</h4>
            <p>ราคากลางตลาดจะตกลงมากอย่างรวดเร็วหลังจากการจดทะเบียนใช้งานในระยะ 3-5 ปีแรก ควรคัดสรรรถอายุสั้น (ไม่เกิน 5 ปี) เพื่อหลีกเลี่ยงการขาดทุนจากการจอดจมสต็อกนาน</p>
        </div>
        <div class="insight-card">
            <h4>5. ผลกระทบด้านพฤติกรรมการใช้งานต่อราคาตั้งขาย</h4>
            <p>ระยะทางวิ่ง (Mileage) ร่วมกับเชื้อเพลิงเบนซิน/ดีเซล เป็นปัจจัยหลักที่ส่งผลตรงกับราคาตั้งขาย การจัดโปรแกรมรับประกันเครื่องยนต์และเกียร์ฟรีหลังขายสามารถเพิ่มแรงจูงใจในการขายรถเลขไมล์สูงได้ดี</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ==========================================
    # --- SECTION 4: DETAILED VISUALIZATIONS ---
    # ==========================================
    st.subheader("กราฟวิเคราะห์เจาะลึก (Detailed Visualizations)")

    with st.expander("1) แผนภูมิวิเคราะห์ความเคลื่อนไหวรายเดือนสะสม (Monthly Trends)", expanded=True):
        st.markdown("#### ยอดขายและกำไรสะสมรายเดือน (Time-Series with Explicit Data Labels)")
        
        trend_data = filtered_sales.groupby(['year', 'month', 'month_name']).agg(
            revenue=('selling_price', 'sum'),
            profit=('profit', 'sum')
        ).reset_index()
        
        if not trend_data.empty:
            trend_data['period'] = trend_data['year'].astype(str) + "-" + trend_data['month'].astype(str).str.zfill(2)
            trend_data = trend_data.sort_values('period')
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=trend_data['period'], 
                y=trend_data['revenue'], 
                name='ยอดขาย (Revenue)', 
                line=dict(color='#2563eb', width=3),
                mode='lines+markers',
                hovertemplate="<b>ปี-เดือน:</b> %{x}<br><b>ยอดขาย:</b> ฿%{y:,.0f}<extra></extra>"
            ))
            fig_trend.add_trace(go.Scatter(
                x=trend_data['period'], 
                y=trend_data['profit'], 
                name='กำไร (Profit)', 
                line=dict(color='#0d9488', width=3),
                mode='lines+markers',
                hovertemplate="<b>ปี-เดือน:</b> %{x}<br><b>กำไร:</b> ฿%{y:,.0f}<extra></extra>"
            ))
            
            fig_trend.update_layout(
                template="plotly_white", 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif", color="#1f2937"),
                height=450,
                xaxis_title="ปี-เดือน (Period)",
                yaxis_title="จำนวนเงิน (บาท)",
                margin=dict(l=20, r=20, t=30, b=20),
                hoverlabel=dict(font_size=24, font_family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif")
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("ไม่มีข้อมูลในตัวกรองนี้สำหรับแผนภูมิความเคลื่อนไหวรายเดือนสะสม")

    with st.expander("2) แผนภูมิวิเคราะห์เปรียบเทียบแบรนด์รถและส่วนแบ่งภูมิภาค (Brand & Region Analysis)", expanded=False):
        show_region_share = len(selected_regions) > 1
        
        if show_region_share:
            row1_col1, row1_col2 = st.columns(2)
        else:
            row1_col1 = st.container()
            
        with row1_col1:
            st.markdown("#### ยอดขายแยกตามแบรนด์รถยนต์ (Car Brand Revenue with Data Labels)")
            brand_sales = filtered_sales.groupby('brand')['selling_price'].sum().reset_index()
            brand_sales = brand_sales.sort_values('selling_price', ascending=True)
            
            if not brand_sales.empty:
                fig_brand = px.bar(
                    brand_sales, 
                    y='brand', 
                    x='selling_price', 
                    orientation='h', 
                    labels={'selling_price': 'ยอดขาย (บาท)', 'brand': 'แบรนด์'},
                    color_discrete_sequence=['#8b5cf6'],
                    text_auto='.3s'
                )
                fig_brand.update_layout(
                    template="plotly_white", 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif", color="#1f2937"),
                    height=400,
                    margin=dict(l=20, r=20, t=10, b=20),
                    hoverlabel=dict(font_size=24, font_family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif")
                )
                fig_brand.update_traces(textposition='outside')
                st.plotly_chart(fig_brand, use_container_width=True)
            else:
                st.warning("ไม่มีข้อมูลในตัวกรองนี้สำหรับเปรียบเทียบแบรนด์")
                
        if show_region_share:
            with row1_col2:
                st.markdown("#### สัดส่วนยอดขายรายภูมิภาค (Regional Market Share)")
                region_sales = filtered_sales.groupby('region')['selling_price'].sum().reset_index()
                
                if not region_sales.empty:
                    fig_region = px.pie(
                        region_sales, 
                        names='region', 
                        values='selling_price', 
                        hole=0.4,
                        color_discrete_sequence=['#2563eb', '#0d9488', '#f43f5e', '#8b5cf6', '#f59e0b']
                    )
                    fig_region.update_layout(
                        template="plotly_white", 
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)', 
                        font=dict(family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif", color="#1f2937"),
                        height=400,
                        margin=dict(l=20, r=20, t=10, b=20),
                        showlegend=True,
                        hoverlabel=dict(font_size=24, font_family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif")
                    )
                    fig_region.update_traces(
                        textinfo='none',
                        hovertemplate="<b>ภูมิภาค:</b> %{label}<br><b>ยอดขาย:</b> ฿%{value:,.0f}<br><b>สัดส่วน:</b> %{percent}<extra></extra>"
                    )
                    st.plotly_chart(fig_region, use_container_width=True)
                else:
                    st.warning("ไม่มีข้อมูลในตัวกรองนี้สำหรับแผนภูมิตามภูมิภาค")

    with st.expander("3) แผนภูมิวิเคราะห์ข้อมูลราคาขายตลาดและเชื้อเพลิง (Market & Fuel Analysis)", expanded=False):
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            st.markdown("#### ความสัมพันธ์อายุรถเฉลี่ย vs ราคาตั้งขายเฉลี่ย (Market Trend)")
            age_price = filtered_listings.groupby('car_age')['ask_price'].mean().reset_index()
            
            if not age_price.empty:
                fig_scatter = px.line(
                    age_price, 
                    x='car_age', 
                    y='ask_price', 
                    labels={'car_age': 'อายุรถ (ปี)', 'ask_price': 'ราคาตั้งขายเฉลี่ย (บาท)'},
                    markers=True,
                    color_discrete_sequence=['#f43f5e']
                )
                fig_scatter.update_traces(
                    hovertemplate="<b>อายุรถ:</b> %{x} ปี<br><b>ราคาตั้งขายเฉลี่ย:</b> ฿%{y:,.0f}<extra></extra>"
                )
                fig_scatter.update_layout(
                    template="plotly_white", 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif", color="#1f2937"),
                    height=400,
                    margin=dict(l=20, r=20, t=10, b=20),
                    hoverlabel=dict(font_size=24, font_family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif")
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.warning("ไม่มีข้อมูลในตัวกรองนี้สำหรับวิเคราะห์อายุเทียบราคากลาง")
                
        with row2_col2:
            st.markdown("#### ระยะทางวิ่งเฉลี่ยจำแนกตามประเภทเชื้อเพลิง (Fuel-type Mileage)")
            fuel_mileage = filtered_sales.groupby('fuel_type')['mileage'].mean().reset_index()
            fuel_mileage = fuel_mileage.sort_values('mileage', ascending=False)
            
            if not fuel_mileage.empty:
                fig_fuel = px.bar(
                    fuel_mileage,
                    x='fuel_type',
                    y='mileage',
                    labels={'fuel_type': 'ประเภทเชื้อเพลิง', 'mileage': 'ระยะวิ่งเฉลี่ย (กิโลเมตร)'},
                    color_discrete_sequence=['#0d9488'],
                    text_auto='.3s'
                )
                fig_fuel.update_layout(
                    template="plotly_white", 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif", color="#1f2937"),
                    height=400,
                    margin=dict(l=20, r=20, t=10, b=20),
                    hoverlabel=dict(font_size=24, font_family="IBM Plex Sans, IBM Plex Sans Thai, sans-serif")
                )
                fig_fuel.update_traces(textposition='outside')
                st.plotly_chart(fig_fuel, use_container_width=True)
            else:
                st.warning("ไม่มีข้อมูลในตัวกรองนี้สำหรับประเภทเชื้อเพลิง")
                
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 12px;'>Used Car Data Warehouse Analytics Dashboard • พัฒนาด้วย Streamlit, Plotly & SQLite</p>", unsafe_allow_html=True)