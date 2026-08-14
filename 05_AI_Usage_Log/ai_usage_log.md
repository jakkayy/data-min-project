# 🤖 บันทึกการใช้งาน Generative AI (AI Usage Log)

**โครงการ**: ETL & Data Warehouse สำหรับระบบวิเคราะห์รถยนต์มือสอง (Used Car Analytics)  
**กลุ่ม**: GroupXX  

ตามข้อกำหนดของรายวิชา เอกสารฉบับนี้จัดทำขึ้นเพื่อบันทึกประวัติการใช้งาน Generative AI ในการช่วยวิเคราะห์ ออกแบบ และพัฒนาระบบ

---

## 📌 ตารางบันทึกการใช้งาน AI (5 Prompts สำคัญ)

| # | Prompt สำคัญที่ใช้ | สิ่งที่ AI แนะนำ | สิ่งที่กลุ่มนำไปใช้ / แก้ไขปรับปรุง | วิธีตรวจสอบว่าผลลัพธ์จาก AI ถูกต้อง |
|---|---|---|---|---|
| **1** | *"ช่วยวิเคราะห์โจทย์ธุรกิจรถมือสอง และกำหนด Business Questions + Measures ให้ตอบโจทย์ส่วนลด vs ค่าเสื่อมราคา"* | แนะนำคำถาม 5 ข้อ และ Measures 6 ตัว พร้อมสูตรคำนวณ `Discount-to-Depreciation Ratio` | นำกรอบคำถาม 5 ข้อมาเป็นหลักใน [business_requirements.md](file:///home/naeiger/data-min/project-group/business_requirements.md) และใช้กำหนด 5 กราฟบน Dashboard | ตรวจสอบกับโจทย์อุตสาหกรรมรถมือสองจริง และเช็คความสอดคล้องกับ Data Sources ที่มี |
| **2** | *"ออกแบบ Data Warehouse แบบ Star Schema เพื่อวิเคราะห์ยอดขายและราคากลางตลาด ให้ได้ Bonus Points"* | แนะนำการทำ **2 Fact Tables** (`FactSales` และ `FactMarketListings`) ร่วมกับ **5 Dimensions** | นำสถาปัตยกรรม 2 Fact Tables มาสร้างใน [02_ETL/src/integrate.py](file:///home/naeiger/data-min/project-group/02_ETL/src/integrate.py) และ PostgreSQL/SQLite Database | ตรวจสอบ ER Diagram, Grain, PK/FK Uniqueness และรัน SQL Queries ทดสอบการ Join |
| **3** | *"ขอโค้ด Regex ภาษา Python สำหรับสกัด Year, Brand, Model, BodyType, FuelType จาก car_title และ description"* | ให้โค้ด `re.search` และฟังก์ชันแยกหมวดหมู่ `body_type` (Pick-up, SUV, Sedan, Hatchback ฯลฯ) | ปรับปรุงฟังก์ชัน `parse_car_title()` ใน [02_ETL/src/clean.py](file:///home/naeiger/data-min/project-group/02_ETL/src/clean.py) ให้สกัด BodyType & FuelType ได้ 100% | รันสคริปต์ทดสอบกับข้อมูล 4,190 แถว และตรวจสอบสถิติการกระจายตัวใน DimCar |
| **4** | *"ขอวิธีจัดการอ่านไฟล์ Web Scraped Data หลายไฟล์ (Multi-file) และแมปชื่อคอลัมน์ดิบอัตโนมัติ"* | แนะนำการใช้ `glob.glob` อ่าน 3 ไฟล์ Scraped Period และแมปคอลัมน์ `data`, `data2` -> `car_title`, `description` | เขียนสคริปต์ `standardize_scraped_columns()` ใน [02_ETL/src/extract.py](file:///home/naeiger/data-min/project-group/02_ETL/src/extract.py) รันอ่านและ Concat อัตโนมัติ | รัน Data Validation Check และยืนยันจำนวนแถวรวม 4,190 แถว |
| **5** | *"ขอสถาปัตยกรรมโค้ด ETL ที่รันรวดเดียวอัตโนมัติ (Automated Pipeline) แยกโมดูล Extract, Clean, Transform, Load"* | แนะนำโครงสร้างไฟล์ modular ใน `src/` และสคริปต์ orchestrator `run_pipeline.py` | สร้างไฟล์ใน [02_ETL/src/](file:///home/naeiger/data-min/project-group/02_ETL/src) และ [02_ETL/run_pipeline.py](file:///home/naeiger/data-min/project-group/02_ETL/run_pipeline.py) รันลง PostgreSQL & SQLite | สั่งรันคำสั่ง `python 02_ETL/run_pipeline.py` ใน Terminal และตรวจสอบความสมบูรณ์ของ DB |

---

## 🔍 สรุปวิธีการตรวจสอบผลลัพธ์จาก AI (Verification Methodology)

1. **Automated Assertion Checks**: สั่งรันกฎการตรวจสอบความถูกต้อง 4 ข้อใน [02_ETL/src/validate.py](file:///home/naeiger/data-min/project-group/02_ETL/src/validate.py) เพื่อยืนยันว่า PK ไม่ซ้ำ และ FK ไม่เป็น Null
2. **Empirical Execution Verification**: ทดลองรันสคริปต์ทั้งหมดในสภาพแวดล้อมจริง (`python 02_ETL/run_pipeline.py`)
3. **Manual Spot Inspection**: สุ่มส่องตรวจสอบตารางใน PostgreSQL / SQLite `used_car_dw.db` ว่าค่า Financial Measures สอดคล้องกับหลักความเป็นจริง
