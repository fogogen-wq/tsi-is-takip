import streamlit as st
import pandas as pd
import plotly.express as px

# Sayfa Yapılandırması
st.set_page_config(page_title="TSI İş Takip Sistemi 2026", layout="wide")

# Veri Yükleme (Excel'den gelen CSV'leri okuyoruz)
@st.cache_data
def load_data():
    # Sizin paylaştığınız CSV formatına göre okuma yapıyoruz
    df = pd.read_csv('TSI IS TAKIP LISTESI 2026.xlsx - 📋 Görev Listesi.csv', skiprows=5)
    df['BAŞLANGIÇ'] = pd.to_datetime(df['BAŞLANGIÇ'])
    return df

df = load_data()

# --- YAN MENÜ (FİLTRELER) ---
st.sidebar.header("Filtreleme Paneli")
sorumlu = st.sidebar.multiselect("Sorumlu Seçin", options=df['SORUMLU'].unique())
durum = st.sidebar.multiselect("Durum Seçin", options=df['DURUM'].unique())

filtered_df = df.copy()
if sorumlu:
    filtered_df = filtered_df[filtered_df['SORUMLU'].isin(sorumlu)]
if durum:
    filtered_df = filtered_df[filtered_df['DURUM'].isin(durum)]

# --- ANA SAYFA (DASHBOARD) ---
st.title("🚀 İş Takip Yönetim Sistemi")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Toplam Görev", len(filtered_df))
col2.metric("Tamamlanan", len(filtered_df[filtered_df['DURUM'] == 'Tamamlandı']))
col3.metric("Devam Eden", len(filtered_df[filtered_df['DURUM'] == 'Devam Ediyor']))
col4.metric("Bekleyen", len(filtered_df[filtered_df['DURUM'] == 'Bekliyor']))

# --- TABLAR (Görünümler) ---
tab1, tab2, tab3 = st.tabs(["📋 Görev Listesi", "📊 Analiz ve Özet", "📅 Zaman Çizelgesi (Gantt)"])

with tab1:
    st.subheader("Aktif Görev Listesi")
    # Veriyi düzenlenebilir tablo olarak sunma
    edited_df = st.data_editor(filtered_df, num_rows="dynamic", use_container_width=True)
    if st.button("Değişiklikleri Kaydet"):
        st.success("Veriler başarıyla güncellendi (Veritabanına yazma işlemi eklenebilir).")

with tab2:
    st.subheader("Kategori Bazlı Dağılım")
    fig_pie = px.pie(filtered_df, names='PROJE / KATEGORİ', title="Projelerin Dağılımı")
    st.plotly_chart(fig_pie)
    
    st.subheader("Durum Özeti")
    fig_bar = px.bar(filtered_df, x='DURUM', color='ÖNCELİK', barmode='group')
    st.plotly_chart(fig_bar)

with tab3:
    st.subheader("Gantt Çizelgesi")
    # Başlangıç tarihi olan işleri göster
    gantt_df = filtered_df.dropna(subset=['BAŞLANGIÇ'])
    if not gantt_df.empty:
        # Örnek bitiş tarihi yoksa başlangıca 7 gün ekleyelim görselleştirmek için
        gantt_df['BİTİŞ'] = gantt_df['BAŞLANGIÇ'] + pd.Timedelta(days=7)
        fig_gantt = px.timeline(gantt_df, start="BAŞLANGIÇ", end="BİTİŞ", x_start="BAŞLANGIÇ", 
                                 y="GÖREV ADI", color="DURUM", hover_data=['SORUMLU'])
        fig_gantt.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.info("Zaman çizelgesi için geçerli tarih girişi bulunamadı.")