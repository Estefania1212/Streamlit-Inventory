
import streamlit as st
import sqlite3
import pandas as pd

DB_NAME = "business_inventory.db"

# --- Inicializar base de datos ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        size TEXT,
        unit TEXT,
        quantity INTEGER NOT NULL,
        unit_price REAL,
        color TEXT,
        previous_price REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        items_supplied TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        item_id INTEGER,
        quantity INTEGER,
        sale_price REAL,
        FOREIGN KEY (item_id) REFERENCES stock(id)
    )
    """)

    conn.commit()
    conn.close()

def get_stock():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM stock", conn)
    conn.close()
    return df

def add_item(name, type_, size, unit, quantity, unit_price, color, previous_price):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO stock (name, type, size, unit, quantity, unit_price, color, previous_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (name, type_, size, unit, quantity, unit_price, color, previous_price))
    conn.commit()
    conn.close()

# --- Interfaz con Streamlit ---
st.set_page_config(page_title="Inventory App", layout="wide")
st.title("📦 Inventory Management")

init_db()

menu = st.sidebar.selectbox("Opciones", ["Ver inventario", "Agregar producto"])

if menu == "Ver inventario":
    st.subheader("📋 Inventario actual")
    df = get_stock()
    st.dataframe(df)

elif menu == "Agregar producto":
    st.subheader("➕ Agregar nuevo producto")
    with st.form("Agregar"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Nombre")
        type_ = col2.text_input("Tipo")
        size = col1.text_input("Tamaño")
        unit = col2.text_input("Unidad")
        quantity = col1.number_input("Cantidad", min_value=0)
        unit_price = col2.number_input("Precio Unitario", min_value=0.0, format="%.2f")
        color = col1.text_input("Color")
        previous_price = col2.number_input("Precio Anterior", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Agregar")

        if submitted:
            add_item(name, type_, size, unit, quantity, unit_price, color, previous_price)
            st.success("✅ Producto agregado correctamente.")
