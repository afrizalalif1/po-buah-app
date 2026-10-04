from datetime import datetime
import sqlite3
import urllib.parse
import pandas as pd
import streamlit as st


# --- INISIALISASI DATABASE SQLITE ---
def init_db():
  conn = sqlite3.connect("po_buah.db")
  cursor = conn.cursor()
  # Tabel Sesi PO
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS po_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            keterangan TEXT
        )
    """)
  # Tabel Pesanan Pelanggan
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            nama_pelanggan TEXT,
            no_wa TEXT,
            nama_buah TEXT,
            jumlah_kg REAL,
            harga_modal REAL,
            harga_jual REAL,
            status_bayar TEXT,
            status_kirim TEXT,
            FOREIGN KEY (session_id) REFERENCES po_sessions (id)
        )
    """)
  conn.commit()
  conn.close()


init_db()

# --- KONFIGURASI HALAMAN STREAMLIT ---
st.set_page_config(
    page_title="Pencatatan PO Buah Rumahan", page_icon="🍎", layout="centered"
)

st.title("🍎 Aplikasi PO Buah Rumahan")
st.write("Kelola pesanan, pembayaran, pengiriman, dan rekap profit dengan mudah.")

# --- SIDEBAR MENU ---
menu = st.sidebar.selectbox(
    "Pilih Menu",
    [
        "📦 Kelola Pesanan Harian",
        "➕ Buat Sesi PO Baru",
        "📊 Rekapitulasi & Profit",
    ],
)


# --- FUNGSI AMBIL KONEKSI ---
def get_connection():
  return sqlite3.connect("po_buah.db")


# ==========================================
# MENU 1: KELOLA PESANAN HARIAN
# ==========================================
if menu == "📦 Kelola Pesanan Harian":
  st.header("📦 Data Pesanan & Kontrol Pembayaran")

  conn = get_connection()
  sessions = pd.read_sql("SELECT * FROM po_sessions ORDER BY id DESC", conn)

  if sessions.empty:
    st.warning(
        "Belum ada Sesi PO. Silakan buat sesi PO baru di menu sebelah!"
    )
    conn.close()
  else:
    # Pilih Sesi PO aktif
    session_options = {
        f"PO {row['tanggal']} - {row['keterangan']}": row["id"]
        for index, row in sessions.iterrows()
    }
    selected_session_label = st.selectbox(
        "Pilih Jadwal Sesi PO", list(session_options.keys())
    )
    selected_session_id = session_options[selected_session_label]

    with st.expander("➕ Tambah Pesanan Baru untuk Sesi Ini"):
      with st.form("form_tambah_pesanan", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
          nama = st.text_input("Nama Pelanggan")
          no_wa = st.text_input("No. WhatsApp (contoh: 628123456789)")
          buah = st.text_input("Nama Buah (misal: Mangga Harum Manis)")
        with col2:
          jumlah = st.number_input("Jumlah (Kg / Porsi)", min_value=0.1, value=1.0)
          h_modal = st.number_input(
              "Harga Modal per Unit (Rp)", min_value=0, value=15000, step=1000
          )
          h_jual = st.number_input(
              "Harga Jual per Unit (Rp)", min_value=0, value=25000, step=1000
          )

        status_b = st.selectbox(
            "Status Pembayaran", ["Belum Bayar", "Lunas", "DP"]
        )
        status_k = st.selectbox(
            "Status Pengiriman", ["Belum Diantar", "Sudah Diantar"]
        )

        submit_order = st.form_submit_button("Simpan Pesanan")
        if submit_order:
          if nama and buah:
            cursor = conn.cursor()
            cursor.execute(
                """
                            INSERT INTO orders (session_id, nama_pelanggan, no_wa, nama_buah, jumlah_kg, harga_modal, harga_jual, status_bayar, status_kirim)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    selected_session_id,
                    nama,
                    no_wa,
                    buah,
                    jumlah,
                    h_modal,
                    h_jual,
                    status_b,
                    status_k,
                ),
            )
            conn.commit()
            st.success(f"Pesanan untuk {nama} berhasil ditambahkan!")
            st.rerun()
          else:
            st.error("Nama Pelanggan dan Nama Buah wajib diisi.")

    # Tampilkan Daftar Pesanan pada Sesi Terpilih
    st.subheader("Daftar Pesanan di Sesi Ini")
    orders_df = pd.read_sql(
        f"SELECT * FROM orders WHERE session_id = {selected_session_id}", conn
    )

    if orders_df.empty:
      st.info("Belum ada pesanan yang tercatat pada sesi ini.")
    else:
      # Hitung ringkasan cepat
      total_omzet = (orders_df["jumlah_kg"] * orders_df["harga_jual"]).sum()
      total_modal = (orders_df["jumlah_kg"] * orders_df["harga_modal"]).sum()
      total_profit = total_omzet - total_modal

      m1, m2, m3 = st.columns(3)
      m1.metric("Total Omzet Sesi Ini", f"Rp {total_omzet:,.0f}")
      m2.metric("Total Modal", f"Rp {total_modal:,.0f}")
      m3.metric("Estimasi Profit", f"Rp {total_profit:,.0f}")

      st.divider()

      # Tampilkan per baris dengan kontrol aksi
      for index, row in orders_df.iterrows():
        st.markdown(
            f"**👤 {row['nama_pelanggan']}** ({row['nama_buah']} -"
            f" {row['jumlah_kg']} kg)"
        )

        c1, c2, c3, c4 = st.columns(4)

        # Badge Status Bayar
        status_bayar_color = (
            "🔴" if row["status_bayar"] == "Belum Bayar" else "🟢"
        )
        c1.write(f"Bayar: {status_bayar_color} **{row['status_bayar']}**")

        # Badge Status Kirim
        status_kirim_color = (
            "📦" if row["status_kirim"] == "Belum Diantar" else "🛵"
        )
        c2.write(f"Kirim: {status_kirim_color} {row['status_kirim']}")

        subtotal = row["jumlah_kg"] * row["harga_jual"]
        c3.write(f"Total: Rp {subtotal:,.0f}")

        # Tombol Aksi (Ubah Status & Kirim WA)
        with c4:
          if row["status_bayar"] == "Belum Bayar" and row["no_wa"]:
            pesan_teks = (
                f"Halo Kak {row['nama_pelanggan']}, terima kasih sudah ikut PO"
                f" buah kami. Total tagihan untuk {row['jumlah_kg']} kg"
                f" {row['nama_buah']} adalah Rp {subtotal:,.0f}. Silakan"
                " melakukan pembayaran ya. Terima kasih!"
            )
            encoded_pesan = urllib.parse.quote(pesan_teks)
            st.markdown(
                f"[💬 Tagih"
                f" WA](https://wa.me/{row['no_wa']}?text={encoded_pesan})"
            )

        # Tombol Update Cepat Status
        col_up1, col_up2, col_up3 = st.columns(3)
        if col_up1.button(f"Tandai Lunas ID:{row['id']}", key=f"lunas_{row['id']}"):
          cursor = conn.cursor()
          cursor.execute(
              "UPDATE orders SET status_bayar = 'Lunas' WHERE id = ?",
              (row["id"],),
          )
          conn.commit()
          st.rerun()

        if col_up2.button(
            f"Tandai Diantar ID:{row['id']}", key=f"kirim_{row['id']}"
        ):
          cursor = conn.cursor()
          cursor.execute(
              "UPDATE orders SET status_kirim = 'Sudah Diantar' WHERE id = ?",
              (row["id"],),
          )
          conn.commit()
          st.rerun()

        if col_up3.button(f"🗑️ Hapus ID:{row['id']}", key=f"del_{row['id']}"):
          cursor = conn.cursor()
          cursor.execute("DELETE FROM orders WHERE id = ?", (row["id"],))
          conn.commit()
          st.rerun()

        st.markdown("---")

    conn.close()

# ==========================================
# MENU 2: BUAT SESI PO BARU
# ==========================================
elif menu == "➕ Buat Sesi PO Baru":
  st.header("➕ Buka Sesi PO Baru")
  st.write("Catat jadwal hari buka PO (misal: PO Pengiriman Hari Kamis).")

  with st.form("form_po"):
    tgl_po = st.date_input("Tanggal PO / Pengiriman", value=datetime.today())
    ket_po = st.text_input(
        "Keterangan (contoh: PO Mangga & Alpukat Pasar Induk)"
    )

    submitted = st.form_submit_button("Buat Sesi PO")
    if submitted:
      conn = get_connection()
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO po_sessions (tanggal, keterangan) VALUES (?, ?)",
          (str(tgl_po), ket_po),
      )
      conn.commit()
      conn.close()
      st.success("Sesi PO berhasil dibuat! Silakan masuk ke menu Kelola Pesanan.")

# ==========================================
# MENU 3: REKAPITULASI & PROFIT
# ==========================================
elif menu == "📊 Rekapitulasi & Profit":
  st.header("📊 Rekapitulasi Penjualan & Keuntungan")

  conn = get_connection()
  # Ambil semua data pesanan digabung dengan tanggal sesi
  df_full = pd.read_sql(
      """
        SELECT s.tanggal, s.keterangan, o.nama_pelanggan, o.nama_buah, 
               o.jumlah_kg, o.harga_modal, o.harga_jual, o.status_bayar, o.status_kirim
        FROM orders o
        JOIN po_sessions s ON o.session_id = s.id
    """,
      conn,
  )
  conn.close()

  if df_full.empty:
    st.info("Belum ada data transaksi untuk direkap.")
  else:
    df_full["Omzet"] = df_full["jumlah_kg"] * df_full["harga_jual"]
    df_full["Modal"] = df_full["jumlah_kg"] * df_full["harga_modal"]
    df_full["Profit"] = df_full["Omzet"] - df_full["Modal"]

    tot_omzet = df_full["Omzet"].sum()
    tot_profit = df_full["Profit"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Akumulasi Total Omzet", f"Rp {tot_omzet:,.0f}")
    col2.metric("Akumulasi Total Profit Bersih", f"Rp {tot_profit:,.0f}")

    st.subheader("Detail Seluruh Transaksi")
    st.dataframe(df_full, use_container_width=True)