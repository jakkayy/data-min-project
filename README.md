# 🚗 Used Car Analytics: ETL Pipeline & Data Warehouse Project

โครงการพัฒนากระบวนการ **ETL (Extract -> Clean -> Transform -> Integrate -> Validate -> Load)** และ **Data Warehouse (Star Schema)** สำหรับระบบวิเคราะห์รถยนต์มือสอง 

---

## 📁 โครงสร้างโฟลเดอร์โครงการ (Project Directory Structure)

```text
project-group/
├── 01_Raw_Data/                   # ข้อมูลดิบทั้ง 3 แหล่งข้อมูล
│   ├── one2car/                   # ข้อมูลตลาดประกาศขายในไทย (one2car_data.csv)
│   ├── us-usecar/                 # ข้อมูลธุรกรรมการขายจริง (used_car_sales.csv)
│   └── usecar-dataset/            # ข้อมูลสเปกและคุณลักษณะเพิ่มเติม
├── 02_ETL/                        # กระบวนการและสคริปต์ ETL
│   ├── notebooks/                 # Notebooks สำหรับทดลองและ Audit Data
│   │   ├── 01_data_exploration.ipynb
│   │   ├── 02_data_cleaning.ipynb
│   │   ├── 03_data_transform.ipynb
│   │   └── 04_data_validation.ipynb
│   ├── src/                       # โมดูลสคริปต์ ETL แบบรันอัตโนมัติ
│   │   ├── extract.py
│   │   ├── clean.py
│   │   ├── transform.py
│   │   ├── integrate.py
│   │   ├── validate.py
│   │   └── load.py
│   └── run_pipeline.py            # สคริปต์หลักรัน ETL Pipeline ทั้งหมดอัตโนมัติ
├── 03_Data_Warehouse/             # ฐานข้อมูล Data Warehouse (SQLite DB + CSV Backups)
│   ├── used_car_dw.db             # SQLite Data Warehouse
│   ├── FactSales.csv              # Fact Table 1 (ยอดขายและกำไร)
│   ├── FactMarketListings.csv     # Fact Table 2 (ราคากลางประกาศขาย One2car)
│   ├── DimCar.csv                 # Dimension รถยนต์
│   ├── DimDate.csv                # Dimension วันที่
│   ├── DimCustomer.csv            # Dimension ลูกค้า
│   ├── DimLocation.csv            # Dimension ทำเล/จังหวัด
│   └── DimAcquisitionSource.csv   # Dimension แหล่งที่มาการซื้อ
├── 04_Dashboard/                  # ชิ้นงานและไฟล์ Dashboard
├── 05_AI_Usage_Log/               # เอกสารบันทึกการใช้งาน Generative AI
│   └── ai_usage_log.md
├── docker-compose.yml             # Docker Compose สำหรับ PostgreSQL Data Warehouse Container
├── business_requirements.md       # เอกสารกำหนดความต้องการทางธุรกิจ (Business Requirement Document)
└── README.md                      # คำอธิบายโครงการและการใช้งาน
```

---

## 🐳 การใช้งาน PostgreSQL ร่วมกับ Docker (Optional & Recommended)

หากต้องการเปิดใช้งาน **PostgreSQL Data Warehouse** ผ่าน Docker:

```bash
# 1. เปิดใช้งาน PostgreSQL Container
docker compose up -d

# 2. ตรวจสอบสถานะการทำงานของ Container
docker compose ps
```

---

## 🚀 วิธีการรันกระบวนการ ETL (How to Run ETL Pipeline)

คุณสามารถสั่งรันกระบวนการ ETL ทั้งหมด (Extract -> Clean -> Transform -> Integrate -> Validate -> Load) ได้อัตโนมัติผ่าน Terminal เพียงใช้คำสั่งเดียว:

```bash
# 1. เข้าสู่โฟลเดอร์โครงการ
cd /path/to/project-group

# 2. เปิดใช้งาน Virtual Environment
source venv/bin/activate

# 3. รันสคริปต์ ETL อัตโนมัติ
python 02_ETL/run_pipeline.py
```

เมื่อสคริปต์รันเสร็จสิ้น ข้อมูลจะถูกโหลดเข้าทั้ง **PostgreSQL Container**, **SQLite Database (`03_Data_Warehouse/used_car_dw.db`)**, และไฟล์ **CSV Backups** ใน [03_Data_Warehouse](file:///home/naeiger/data-min/project-group/03_Data_Warehouse) โดยอัตโนมัติพร้อมกันครับ!
