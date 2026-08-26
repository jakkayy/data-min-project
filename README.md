# 🚗 Used Car Analytics: ETL Pipeline & Data Warehouse Project

โครงการพัฒนากระบวนการ **ETL (Extract -> Clean -> Transform -> Integrate -> Validate -> Load)** แบบอัตโนมัติ และ **Data Warehouse (Star Schema)** สำหรับระบบวิเคราะห์ข้อมูลรถยนต์มือสอง 

---

## 📁 โครงสร้างโฟลเดอร์โครงการ (Project Directory Structure)

```text
project-group/
├── 01_Raw_Data/                   # ข้อมูลดิบจาก 3 แหล่งข้อมูลหลัก
│   ├── kaidee/                    # ข้อมูลประกาศขาย Kaidee Auto (kaidee_cars_detail.json)
│   ├── one2car/                   # ข้อมูลประกาศขาย One2car (one2car-11-2.csv, 11-3.csv, 11-4.csv)
│   └── us-usecar/                 # ข้อมูลธุรกรรมการขายจริง (used_car_sales.csv)
├── 02_ETL/                        # กระบวนการและสคริปต์ ETL แบบอัตโนมัติ
│   ├── notebooks/                 # Jupyter Notebooks สำหรับทดลองและ Audit ข้อมูล
│   │   ├── 01_data_exploration.ipynb
│   │   ├── 02_data_cleaning.ipynb
│   │   ├── 03_data_transform.ipynb
│   │   ├── 04_data_validation.ipynb
│   │   └── archive/               # คลังจัดเก็บ Notebooks ร่าง/ทดลอง (new_etl_*.ipynb)
│   ├── src/                       # โมดูลสคริปต์ ETL แยกตามหน้าที่
│   │   ├── extract.py             # อ่านข้อมูลดิบทั้ง 3 แหล่ง (JSON, Multi-CSV, CSV)
│   │   ├── clean.py               # ล้างข้อมูล สกัด Regex สเปกรถ และจัดมาตรฐานจังหวัด
│   │   ├── transform.py           # คำนวณ KPI ทางการเงิน (Profit, Margin, Discount Ratio)
│   │   ├── integrate.py           # สร้าง Surrogate Keys และประกอบ 2 Fact + 5 Dim Tables
│   │   ├── validate.py            # ตรวจสอบ Data Quality Assertions (PK Unique, FK Non-Null)
│   │   └── load.py                # โหลดเข้า SQLite, Docker PostgreSQL, Supabase และ CSV Backups
│   └── run_pipeline.py            # สคริปต์หลักรัน ETL Pipeline ทั้งหมดรวดเดียวอัตโนมัติ
├── 03_Data_Warehouse/             # ฐานข้อมูล Data Warehouse (SQLite DB + CSV Backups)
│   ├── used_car_dw.db             # SQLite Data Warehouse Main Database
│   ├── FactSales.csv              # Fact Table 1: ยอดขาย กำไร ส่วนลด และระยะเวลาจอดขาย
│   ├── FactMarketListings.csv     # Fact Table 2: ประกาศขายและราคากลาง One2car Market Benchmark
│   ├── DimCar.csv                 # Dimension: ข้อมูลสเปกรถยนต์ (ยี่ห้อ, รุ่น, ปี, เกียร์, รูปทรง, เชื้อเพลิง)
│   ├── DimDate.csv                # Dimension: มิติด้านเวลา (วัน, เดือน, ไตรมาส, ปี, วันหยุด)
│   ├── DimLocation.csv            # Dimension: ทำเลจังหวัด จัดกลุ่ม 6 ภูมิภาคมาตรฐานประเทศไทย
│   ├── DimCustomer.csv            # Dimension: ข้อมูลกลุ่มลูกค้าและช่องทางการชำระเงิน
│   └── DimAcquisitionSource.csv   # Dimension: ช่องทางการจัดซื้อรถยนต์เข้าสต็อก
├── 04_Dashboard/                  # ระบบ Dashboard สำหรับแสดงผลวิเคราะห์
│   └── dashboard.py               # Interactive Web Dashboard พัฒนาด้วย Streamlit & Plotly
├── 05_AI_Usage_Log/               # เอกสารบันทึกการใช้งาน Generative AI
│   └── ai_usage_log.md            # รายละเอียด Prompt และวิธีการตรวจสอบผลลัพธ์จาก AI
├── docker-compose.yml             # Docker Compose สำหรับ PostgreSQL 15 Data Warehouse Container
├── requirements.txt               # รายการ Python Library Dependencies ที่จำเป็น
└── README.md                      # คำอธิบายโครงการและการใช้งาน
```

---

## 🏛️ สถาปัตยกรรมคลังข้อมูล (Data Warehouse Star Schema Architecture)

ระบบออกแบบคลังข้อมูลเป็น **Star Schema แบบ 2 Fact Tables + 5 Dimension Tables**:

* **Fact Table 1 (`FactSales`):** ธุรกรรมการขายรถยนต์จริง (Selling Price, Cost, Profit, Margin, Discount Amount, Depreciation Ratio, Days on Lot)
* **Fact Table 2 (`FactMarketListings`):** ประกาศขายราคากลางในตลาด One2car Benchmark (Ask Price, Mileage, Car Age)
* **Dimension Tables:** `DimCar`, `DimDate`, `DimLocation` (6 ภาคประเทศไทย), `DimCustomer`, `DimAcquisitionSource`

---

## 🚀 ขั้นตอนการติดตั้งและรันโครงการ (How to Run Project)

### 1. เตรียมสภาพแวดล้อม Python (Environment Setup)
```bash
# 1.1 สร้างและเปิดใช้งาน Virtual Environment
python -m venv venv
source venv/bin/activate       # สำหรับ Linux/macOS
# venv\Scripts\activate        # สำหรับ Windows Command Prompt

# 1.2 ติดตั้ง Packages ที่จำเป็น
pip install -r requirements.txt
```

### 2. รันฐานข้อมูล Local PostgreSQL Container (Optional)
```bash
# สั่งเปิดใช้งาน PostgreSQL Container (Port 5433)
docker compose up -d
```

### 3. รันกระบวนการ ETL Pipeline อัตโนมัติ (Automated ETL Execution)
```bash
# รัน ETL รวดเดียว (Extract -> Clean -> Transform -> Integrate -> Validate -> Load)
python 02_ETL/run_pipeline.py

# (ทางเลือก) สั่งรันพร้อมยิงข้อมูลขึ้น Supabase Cloud PostgreSQL
python 02_ETL/run_pipeline.py --supabase-url "postgresql://postgres:YOUR_PASSWORD@db.sveahtsaglbgrsnoiwjv.supabase.co:5432/postgres"
```

เมื่อสคริปต์รันสำเร็จ ข้อมูลจะถูกทดสอบ Data Quality Assertions 4 กฎ และโหลดเข้าทั้ง **SQLite Database (`03_Data_Warehouse/used_car_dw.db`)**, **Local Docker PostgreSQL**, **Supabase Cloud PostgreSQL** (ถ้ามี URI), และ **CSV Backup Files** โดยอัตโนมัติ

### 4. รันระบบ Dashboard วิเคราะห์ข้อมูล (Streamlit Web Dashboard)
```bash
streamlit run 04_Dashboard/dashboard.py
```
เบราว์เซอร์จะเปิดหน้าต่างขึ้นมาที่ `http://localhost:8501` เพื่อแสดง Interactive Dashboard วิเคราะห์ยอดขาย อัตรากำไร ค่าเสื่อมราคา และสต็อกรถยนต์มือสองครับ

