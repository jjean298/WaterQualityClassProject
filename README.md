# 💧 Water Quality Data Explorer

A full-stack data pipeline and visualization tool for analyzing water quality observations.  
This project demonstrates **data cleaning (ETL)**, a **Flask REST API**, and an interactive **Streamlit dashboard** backed by **MongoDB Atlas**.

---

## 🚀 Features

### 🔹 ETL (Extract – Transform – Load)
- Loads multiple CSV datasets from `/data/raw/`
- Cleans timestamps, removes outliers (Z-score filtering)
- Saves cleaned CSVs to `/data/cleaned/`
- Inserts data into MongoDB with automatic indexing

### 🔹 Flask REST API
- `/api/health` → health check  
- `/api/observations` → paginated query with filters for date, salinity, ODO, temperature, etc.  
- `/api/stats` → summary statistics for numeric fields  
- `/api/outliers` → returns outlier records by field and method (IQR or Z-score)

### 🔹 Streamlit Dashboard
- Displays cleaned data in a sortable table  
- Provides dynamic filters (date range, salinity, ODO, etc.)  
- Interactive charts for trends and outlier visualization  
- Connects directly to the Flask API

---

## 🧠 Tech Stack

| Layer | Tools & Libraries |
|-------|-------------------|
| **Backend** | Python, Flask, MongoDB (Atlas), PyMongo |
| **Frontend** | Streamlit |
| **ETL / Data Processing** | Pandas, NumPy |
| **Environment Management** | `python-dotenv`, virtualenv |
| **Version Control** | Git + GitHub |

---

## 🧩 How to Run Locally
Clone → install requirements → run Flask & Streamlit → open `localhost:8501`

