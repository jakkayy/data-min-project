# 🤖 บันทึกการใช้งาน Generative AI (AI Usage Log)

**โครงการ**: ETL & Data Warehouse สำหรับระบบวิเคราะห์รถยนต์มือสอง (Used Car Analytics)  
**กลุ่ม**: GroupXX

ตามข้อกำหนดของรายวิชา เอกสารฉบับนี้จัดทำขึ้นเพื่อบันทึกประวัติการใช้งาน Generative AI ในการช่วยวิเคราะห์ ออกแบบ และพัฒนาระบบ

---

## 📌 ตารางบันทึกการใช้งาน AI (5 Prompts สำคัญ)

| #     | Prompt สำคัญที่ใช้                                                                                              | สิ่งที่ AI แนะนำ                                                                             | สิ่งที่กลุ่มนำไปใช้ / แก้ไขปรับปรุง                                                                                                                                                                        | วิธีตรวจสอบว่าผลลัพธ์จาก AI ถูกต้อง                                                     |
| ----- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **1** | _"ช่วยวิเคราะห์โจทย์ธุรกิจรถมือสอง และกำหนด Business Questions + Measures ให้ตอบโจทย์ส่วนลด vs ค่าเสื่อมราคา"_  | แนะนำคำถาม 5 ข้อ และ Measures 6 ตัว พร้อมสูตรคำนวณ `Discount-to-Depreciation Ratio`          | นำกรอบคำถาม 5 ข้อมาเป็นหลักใน [business_requirements.md](file:///home/naeiger/data-min/project-group/business_requirements.md) และใช้กำหนด 5 กราฟบน Dashboard                                              | ตรวจสอบกับโจทย์อุตสาหกรรมรถมือสองจริง และเช็คความสอดคล้องกับ Data Sources ที่มี         |
| **2** | _"ออกแบบ Data Warehouse แบบ Star Schema เพื่อวิเคราะห์ยอดขายและราคากลางตลาด ให้ได้ Bonus Points"_               | แนะนำการทำ **2 Fact Tables** (`FactSales` และ `FactMarketListings`) ร่วมกับ **5 Dimensions** | นำสถาปัตยกรรม 2 Fact Tables มาสร้างใน [02_ETL/src/integrate.py](file:///home/naeiger/data-min/project-group/02_ETL/src/integrate.py) และ SQLite Database                                                   | ตรวจสอบ ER Diagram, Grain, PK/FK Uniqueness และรัน SQL Queries ทดสอบการ Join            |
| **3** | _"ขอโค้ด Regex ภาษา Python สำหรับสกัด Year, Brand, Model ออกจากข้อความ car_title ใน One2car"_                   | ให้โค้ด `re.search(r'^(20\d{2}\|19\d{2})', title)` และฟังก์ชันแยกคำ                          | ปรับปรุงฟังก์ชัน `parse_car_title()` ใน [02_ETL/src/clean.py](file:///home/naeiger/data-min/project-group/02_ETL/src/clean.py) ให้รองรับค่าว่างและข้อความไทย                                               | รันสคริปต์ทดสอบกับข้อมูล 4,190 แถว และสุ่มตรวจเช็คผลลัพธ์ 100 รายการ                    |
| **4** | _"ช่วยเขียนสคริปต์ทำความสะอาดราคาและไมล์ที่ติดสัญลักษณ์ บาท, $, ₹, กม., km และช่วง 170-175K"_                   | ให้ฟังก์ชัน `clean_price` และ `clean_mileage` ด้วย `re.sub` และ `re.search`                  | ปรับฟังก์ชันให้รองรับ edge cases ค่าตัวเลขว่าง `''` และกรอง Outliers ที่ราคา/ไมล์เป็น 0                                                                                                                    | รัน Data Validation Check ด้วย `assert` และ `.isnull().sum()` เพื่อยืนยันว่าไม่มี Error |
| **5** | _"ขอสถาปัตยกรรมโค้ด ETL ที่รันรวดเดียวอัตโนมัติ (Automated Pipeline) แยกโมดูล Extract, Clean, Transform, Load"_ | แนะนำโครงสร้างไฟล์ modular ใน `src/` และสคริปต์ orchestrator `run_pipeline.py`               | สร้างไฟล์ใน [02_ETL/src/](file:///home/naeiger/data-min/project-group/02_ETL/src) และ [02_ETL/run_pipeline.py](file:///home/naeiger/data-min/project-group/02_ETL/run_pipeline.py) รันลง SQLite DB และ CSV | สั่งรันคำสั่ง `python 02_ETL/run_pipeline.py` ใน Terminal และตรวจสอบความสมบูรณ์ของ DB   |

---

## 🔍 สรุปวิธีการตรวจสอบผลลัพธ์จาก AI (Verification Methodology)

1. **Automated Assertion Checks**: สั่งรันกฎการตรวจสอบความถูกต้อง 4 ข้อใน [02_ETL/src/validate.py](file:///home/naeiger/data-min/project-group/02_ETL/src/validate.py) เพื่อยืนยันว่า PK ไม่ซ้ำ และ FK ไม่เป็น Null
2. **Empirical Execution Verification**: ทดลองรันสคริปต์ทั้งหมดในสภาพแวดล้อมจริง (`python 02_ETL/run_pipeline.py`)
3. **Manual Spot Inspection**: สุ่มส่องตรวจสอบตารางใน SQLite `used_car_dw.db` ว่าค่า Financial Measures สอดคล้องกับหลักความเป็นจริง
