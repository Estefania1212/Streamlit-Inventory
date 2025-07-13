import streamlit as st
import sqlite3
import pandas as pd
import datetime
from reportlab.pdfgen import canvas
import os

DB_NAME = "business_inventory.db"

# ---------------------- INICIALIZAR BD ----------------------
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
        quantity REAL NOT NULL,
        unit_price REAL,
        color TEXT,
        previous_price REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas_cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        total REAL,
        estado TEXT DEFAULT 'activa'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalle_ventas_cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto TEXT,
        cantidad REAL,
        precio_unitario REAL,
        subtotal REAL,
        FOREIGN KEY (venta_id) REFERENCES ventas_cliente(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        contacto TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reabastecimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        proveedor_id INTEGER,
        tipo TEXT,
        cantidad REAL,
        precio_total REAL,
        iva REAL,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    )
    """)

    conn.commit()
    conn.close()


# ---------------------- INTERFAZ ----------------------
init_db()
st.set_page_config(page_title="Sistema de Inventario", layout="wide")
st.title("📦 Sistema de Inventario - Gestión de Materiales")

menu = st.sidebar.selectbox("Menú", [
    "📋 Ver Inventario",
    "➕ Agregar Producto",
    "🛒 Registrar Venta",
    "📑 Historial de Ventas",
    "📥 Registrar Reabastecimiento",
    "🧾 Comprobante Manual"
])

if menu == "📋 Ver Inventario":
    st.subheader("📦 Inventario Actual")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM stock", conn)
    st.dataframe(df, use_container_width=True)
    conn.close()

elif menu == "➕ Agregar Producto":
    st.subheader("➕ Nuevo Producto")
    with st.form("form_nuevo"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre")
        tipo = col2.text_input("Tipo")
        tamaño = col1.text_input("Tamaño")
        unidad = col2.text_input("Unidad (ej: m, m2, pieza)")
        cantidad = col1.number_input("Cantidad", min_value=0.0, step=0.1)
        precio_unitario = col2.number_input("Precio Unitario", min_value=0.0)
        color = col1.text_input("Color")
        precio_anterior = col2.number_input("Precio Anterior", min_value=0.0)
        enviar = st.form_submit_button("Guardar")

        if enviar:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO stock (name, type, size, unit, quantity, unit_price, color, previous_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre, tipo, tamaño, unidad, cantidad, precio_unitario, color, precio_anterior))
            conn.commit()
            conn.close()
            st.success("✅ Producto agregado con éxito.")

elif menu == "🛒 Registrar Venta":
    st.subheader("🛒 Registrar Venta")
    conn = sqlite3.connect(DB_NAME)
    df_stock = pd.read_sql("SELECT * FROM stock", conn)

    productos = []
    total = 0
    with st.form("form_venta"):
        col1, col2 = st.columns(2)
        producto = col1.selectbox("Producto", df_stock['name'].unique())
        cantidad = col2.number_input("Cantidad vendida", min_value=0.0, step=0.1)
        boton_agregar = st.form_submit_button("Agregar a la venta")

        if boton_agregar and producto:
            datos = df_stock[df_stock['name'] == producto].iloc[0]
            subtotal = round(cantidad * datos['unit_price'], 2)
            productos.append((producto, cantidad, datos['unit_price'], subtotal))
            total += subtotal
            st.session_state['venta_actual'] = productos
            st.session_state['total'] = total

    if 'venta_actual' in st.session_state:
        st.write("### Productos en venta:")
        st.table(pd.DataFrame(st.session_state['venta_actual'], columns=["Producto", "Cantidad", "Precio Unitario", "Subtotal"]))
        st.write(f"**Total: ${st.session_state['total']:.2f}**")

        if st.button("Confirmar y Guardar Venta"):
            fecha = datetime.date.today().strftime("%d/%m/%Y")
            cur = conn.cursor()
            cur.execute("INSERT INTO ventas_cliente (fecha, total) VALUES (?, ?)", (fecha, st.session_state['total']))
            venta_id = cur.lastrowid
            for p in st.session_state['venta_actual']:
                cur.execute("""
                    INSERT INTO detalle_ventas_cliente (venta_id, producto, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (venta_id, *p))
            conn.commit()
            st.success("✅ Venta registrada exitosamente.")
            st.session_state.pop('venta_actual')
            st.session_state.pop('total')
    conn.close()

elif menu == "📑 Historial de Ventas":
    st.subheader("📑 Historial de Ventas")
    conn = sqlite3.connect(DB_NAME)
    ventas = pd.read_sql("SELECT * FROM ventas_cliente", conn)
    detalles = pd.read_sql("SELECT * FROM detalle_ventas_cliente", conn)
    st.dataframe(ventas)

    venta_id = st.number_input("ID de venta a anular", step=1, min_value=1)
    if st.button("Anular venta"):
        cur = conn.cursor()
        cur.execute("UPDATE ventas_cliente SET estado='anulada' WHERE id=?", (venta_id,))
        conn.commit()
        st.success("✅ Venta anulada.")
    conn.close()

elif menu == "📥 Registrar Reabastecimiento":
    st.subheader("📥 Reabastecimiento de Stock")
    with st.form("form_reabastecimiento"):
        col1, col2 = st.columns(2)
        proveedor = col1.text_input("Proveedor")
        tipo = col2.text_input("Tipo de producto")
        cantidad = col1.number_input("Cantidad", min_value=0.0)
        precio_total = col2.number_input("Precio Total", min_value=0.0)
        iva = col1.number_input("IVA (%)", min_value=0.0, max_value=100.0)
        enviar = st.form_submit_button("Guardar")

        if enviar:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("INSERT INTO proveedores (nombre) VALUES (?)", (proveedor,))
            proveedor_id = cur.lastrowid
            fecha = datetime.date.today().strftime("%d/%m/%Y")
            cur.execute("""
                INSERT INTO reabastecimientos (fecha, proveedor_id, tipo, cantidad, precio_total, iva)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fecha, proveedor_id, tipo, cantidad, precio_total, iva))
            conn.commit()
            conn.close()
            st.success("✅ Reabastecimiento registrado.")

elif menu == "🧾 Comprobante Manual":
    st.subheader("🧾 Generar Comprobante de Venta (Manual)")
    nombre_cliente = st.text_input("Nombre del cliente")
    monto_total = st.number_input("Monto total de la venta", min_value=0.0)
    if st.button("Generar PDF"):
        archivo = f"comprobante_{nombre_cliente.replace(' ', '_')}.pdf"
        c = canvas.Canvas(archivo)
        c.drawString(100, 800, f"Comprobante de venta para: {nombre_cliente}")
        c.drawString(100, 780, f"Monto total: ${monto_total:.2f}")
        c.drawString(100, 760, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}")
        c.save()
        with open(archivo, "rb") as f:
            st.download_button("Descargar comprobante", f, file_name=archivo)
        os.remove(archivo)

