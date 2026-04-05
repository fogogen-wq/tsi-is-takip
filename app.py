import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="TSI Yönetim Paneli", layout="wide", page_icon="🚀")

# --- MODERN UI CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 5% 10%;
        border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div > div { border-radius: 10px; }
    div.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
</style>
""", unsafe_allow_html=True)

# --- 1. VERİTABANI YÖNETİMİ ---
DB_FILE = "tsi_is_takip_veritabani.csv"
USER_DB = "kullanicilar.csv"

# Kullanıcı Veritabanı
def kullanici_yukle():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    else:
        df = pd.DataFrame([
            {"KULLANICI_ADI": "Yönetici", "SIFRE": "admin123", "ROL": "Admin"},
            {"KULLANICI_ADI": "Zilan Demir", "SIFRE": "1234", "ROL": "User"},
            {"KULLANICI_ADI": "Nilay", "SIFRE": "1234", "ROL": "User"},
            {"KULLANICI_ADI": "Saim", "SIFRE": "1234", "ROL": "User"},
            {"KULLANICI_ADI": "Uğur", "SIFRE": "1234", "ROL": "User"}
        ])
        df.to_csv(USER_DB, index=False)
        return df

def kullanici_kaydet(df):
    df.to_csv(USER_DB, index=False)

# Görev Veritabanı
def veriyi_yukle():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        columns = ['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BAŞLANGIÇ', 'BİTİŞ', 'DURUM', 'ÖNCELİK', 'NOTLAR', 'AŞAMALAR', 'KAYIT_TARIHI']
        df = pd.DataFrame(columns=columns)
        df.to_csv(DB_FILE, index=False)
        return df

def veriyi_kaydet(df):
    df.to_csv(DB_FILE, index=False)

# Session State Atamaları
if 'kullanicilar' not in st.session_state: st.session_state.kullanicilar = kullanici_yukle()
if 'data' not in st.session_state: st.session_state.data = veriyi_yukle()

def asamalari_coz(asama_metni):
    try:
        asamalar = json.loads(str(asama_metni))
        if isinstance(asamalar, list): return asamalar
    except:
        return []
    return []

def asamalari_paketle(asama_listesi):
    return json.dumps(asama_listesi, ensure_ascii=False)

if 'temp_stages' not in st.session_state: st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Ana Sorumlu ile Aynı", "Durum": "Bekliyor", "Not": ""}]

def formu_sifirla():
    for key in list(st.session_state.keys()):
        if key.startswith("frm_"): del st.session_state[key]
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Ana Sorumlu ile Aynı", "Durum": "Bekliyor", "Not": ""}]

# --- 2. ŞİFRELİ GİRİŞ (LOGIN) SİSTEMİ ---
if "giris_basarili" not in st.session_state:
    st.session_state.giris_basarili = False
    st.session_state.aktif_kullanici = None
    st.session_state.aktif_rol = None

kullanici_listesi = st.session_state.kullanicilar['KULLANICI_ADI'].tolist()

if not st.session_state.giris_basarili:
    st.sidebar.title("🔐 Sisteme Giriş")
    secilen_kullanici = st.sidebar.selectbox("Kullanıcı Seçin", ["Seçiniz"] + kullanici_listesi)
    girilen_sifre = st.sidebar.text_input("Şifreniz", type="password")
    
    if st.sidebar.button("Giriş Yap", use_container_width=True):
        if secilen_kullanici != "Seçiniz":
            user_row = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == secilen_kullanici].iloc[0]
            if str(user_row['SIFRE']) == girilen_sifre:
                st.session_state.giris_basarili = True
                st.session_state.aktif_kullanici = secilen_kullanici
                st.session_state.aktif_rol = user_row['ROL']
                st.rerun()
            else:
                st.sidebar.error("❌ Şifre hatalı!")
        else:
            st.sidebar.warning("Lütfen kullanıcı seçin.")
            
    st.title("TSI Yönetim Paneline Hoş Geldiniz")
    st.info("👈 Lütfen işlem yapabilmek için sol taraftaki menüden şifrenizle giriş yapınız.")
    st.stop()

# --- GİRİŞ YAPILDIKTAN SONRAKİ EKRAN ---
kullanici = st.session_state.aktif_kullanici
rol = st.session_state.aktif_rol

st.sidebar.success(f"Hoş geldin, {kullanici}!")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state.giris_basarili = False
    st.session_state.aktif_kullanici = None
    st.session_state.aktif_rol = None
    st.rerun()

firmalar = sorted(st.session_state.data['FİRMA'].dropna().unique().tolist()) if not st.session_state.data.empty else ["Akgıda", "Tegep"]
sorumlular = [k for k in kullanici_listesi if k != "Yönetici"] 

st.sidebar.divider()
st.sidebar.subheader("🔍 Hızlı Filtre")
f_firma = st.sidebar.multiselect("Firmaya Göre", firmalar)
f_durum = st.sidebar.multiselect("Duruma Göre", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"])

display_df = st.session_state.data.copy()
if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_durum: display_df = display_df[display_df['DURUM'].isin(f_durum)]


# --- 3. ANA SEKMELER ---
if rol == "Admin":
    tab_ekle, tab_liste, tab_rapor, tab_ayarlar, tab_kullanici = st.tabs(["➕ Yeni Görev", "📋 İş Listesi ve Detaylar", "📊 Raporlama", "⚙️ Veri Yönetimi", "👥 Kullanıcı Yönetimi"])
else:
    tab_ekle, tab_liste, tab_rapor, tab_ayarlar = st.tabs(["➕ Yeni Görev", "📋 İş Listesi ve Detaylar", "📊 Raporlama", "⚙️ Veri Yönetimi"])

# ================= TAB 1: YENİ GÖREV =================
with tab_ekle:
    c1, c2 = st.columns(2)
    with c1:
        v_ad = st.text_input("Görev Adı *", key="frm_ad")
        v_firma_sec = st.selectbox("Firma *", ["➕ YENİ EKLE..."] + firmalar, key="frm_f_sec")
        v_firma = st.text_input("Yeni Firma Adı *", key="frm_f_yeni") if v_firma_sec == "➕ YENİ EKLE..." else v_firma_sec
        v_sorumlu = st.selectbox("Ana Sorumlu *", ["Seçiniz"] + sorumlular, key="frm_s_sec")

    with c2:
        v_basla = st.date_input("Başlangıç", datetime.now(), key="frm_b_t")
        v_bitis = st.date_input("Bitiş", datetime.now() + timedelta(days=7), key="frm_bit_t")
        v_oncelik = st.selectbox("Öncelik *", ["Seçiniz", "Düşük", "Orta", "Yüksek"], key="frm_on")
        v_durum = st.selectbox("Genel Durum *", ["Seçiniz", "Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"], key="frm_dur")

    v_not = st.text_area("📌 Genel Görev Notu", key="frm_not")

    st.write("---")
    st.subheader("🛠 Alt Aşamalar (Detaylı)")
    
    asamalar_listesi = []
    for i, stg in enumerate(st.session_state.temp_stages):
        ca1, ca2, ca3, ca4 = st.columns([3, 2, 2, 3])
        s_ad = ca1.text_input("Ne Yapılacak?", value=stg["Aşama Adı"], key=f"frm_st_ad_{i}")
        s_ki = ca2.selectbox("Sorumlu", ["Aynı"] + sorumlular, key=f"frm_st_ki_{i}")
        s_durum = ca3.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"], key=f"frm_st_dur_{i}")
        s_not = ca4.text_input("Aşama Notu", value=stg["Not"], key=f"frm_st_not_{i}")
        asamalar_listesi.append({"Aşama Adı": s_ad, "Sorumlu": s_ki, "Durum": s_durum, "Not": s_not})

    if st.button("➕ Aşama Ekle"):
        st.session_state.temp_stages.append({"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""})
        st.rerun()

    if st.button("✅ YENİ GÖREVİ SİSTEME EKLE", use_container_width=True):
        if v_ad and v_firma and v_sorumlu != "Seçiniz" and v_durum != "Seçiniz" and v_oncelik != "Seçiniz":
            temiz_asamalar = []
            for a in asamalar_listesi:
                if a["Aşama Adı"].strip():
                    a["Sorumlu"] = v_sorumlu if a["Sorumlu"] == "Aynı" else a["Sorumlu"]
                    temiz_asamalar.append(a)

            yeni = {
                'GÖREV ADI': v_ad, 'FİRMA': v_firma, 'ANA SORUMLU': v_sorumlu,
                'BAŞLANGIÇ': v_basla.strftime('%Y-%m-%d'), 'BİTİŞ': v_bitis.strftime('%Y-%m-%d'),
                'DURUM': v_durum, 'ÖNCELİK': v_oncelik, 'NOTLAR': v_not,
                'AŞAMALAR': asamalari_paketle(temiz_asamalar), 
                'KAYIT_TARIHI': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([yeni])], ignore_index=True)
            veriyi_kaydet(st.session_state.data)
            formu_sifirla()
            st.success("Görev başarıyla eklendi!")
            st.rerun()
        else:
            st.error("Lütfen yıldızlı (*) tüm zorunlu alanları doldurduğunuzdan emin olun!")


# ================= TAB 2: LİSTE VE DETAY PANELİ (GÜNCELLENDİ) =================
with tab_liste:
    st.subheader("📋 Ana Görevler Tablosu")
    st.caption("Detaylarını görmek veya düzenlemek istediğiniz görevin üzerine tıklayın.")
    
    if not display_df.empty:
        gosterilecek_df = display_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'])
        
        # Checkbox yerine Tıklanabilir Seçim (on_select="rerun") eklendi
        selection = st.dataframe(
            gosterilecek_df,
            use_container_width=True,
            height=350,
            selection_mode="single_row", # <-- HATA BURADA
            on_select="rerun",
            key="ana_tablo_secim"
        )
        
        selected_rows = selection.get("selection", {}).get("rows", [])
        
        if len(selected_rows) > 0:
            st.divider()
            idx_label = gosterilecek_df.index[selected_rows[0]]
            secili_satir = st.session_state.data.loc[idx_label]
            
            with st.container(border=True):
                st.write(f"## 🎯 Seçili Görev: {secili_satir['GÖREV ADI']}")
                durumlar = ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"]
                c_durum, c_not = st.columns(2)
                yeni_ana_durum = c_durum.selectbox("Genel Durum", durumlar, index=durumlar.index(secili_satir['DURUM']) if secili_satir['DURUM'] in durumlar else 0, key=f"d_dur_{idx_label}")
                yeni_ana_not = c_not.text_input("Genel Not", value=str(secili_satir['NOTLAR']) if pd.notna(secili_satir['NOTLAR']) else "", key=f"d_not_{idx_label}")
                
                st.write("---")
                st.write("### 🛠 Alt Aşamalar")
                asamalar = asamalari_coz(secili_satir['AŞAMALAR'])
                asama_df = pd.DataFrame(asamalar) if len(asamalar) > 0 else pd.DataFrame(columns=["Aşama Adı", "Sorumlu", "Durum", "Not"])
                
                duz_asama_df = st.data_editor(
                    asama_df, num_rows="dynamic", use_container_width=True, key=f"d_asama_{idx_label}",
                    column_config={
                        "Aşama Adı": st.column_config.TextColumn("📝 Aşama Adı"),
                        "Sorumlu": st.column_config.SelectboxColumn("👤 Sorumlu", options=sorumlular),
                        "Durum": st.column_config.SelectboxColumn("📌 Durum", options=["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"]),
                        "Not": st.column_config.TextColumn("💬 Aşama Notu")
                    }
                )
                
                # Değişiklikleri Kaydet Butonu (Kontrollü kayıt)
                if st.button("💾 Seçili Görevin Değişikliklerini Kaydet", use_container_width=True):
                    st.session_state.data.at[idx_label, 'DURUM'] = yeni_ana_durum
                    st.session_state.data.at[idx_label, 'NOTLAR'] = yeni_ana_not
                    st.session_state.data.at[idx_label, 'AŞAMALAR'] = asamalari_paketle(duz_asama_df.to_dict('records'))
                    
                    veriyi_kaydet(st.session_state.data)
                    st.success("Detaylar başarıyla güncellendi! 💾")
                    st.rerun() 
        else:
            st.info("💡 Alt aşamaları görüntülemek ve düzenlemek için yukarıdaki listeden bir satıra tıklayın.")
    else:
        st.info("Gösterilecek görev bulunamadı.")

# ================= TAB 3: RAPORLAMA =================
with tab_rapor:
    if not st.session_state.data.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(st.session_state.data, x="FİRMA", color="DURUM", title="Firma İş Yükü"), use_container_width=True)
        c2.plotly_chart(px.pie(st.session_state.data, names="ANA SORUMLU", hole=0.4, title="Sorumlu Dağılımı"), use_container_width=True)

# ================= TAB 4: VERİ YÖNETİMİ =================
with tab_ayarlar:
    csv = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Görev Verilerini Yedekle", data=csv, file_name='tsi_yedek.csv', mime='text/csv')

# ================= TAB 5: KULLANICI YÖNETİMİ (SADECE ADMİN) =================
if rol == "Admin":
    with tab_kullanici:
        st.subheader("👥 Sisteme Kayıtlı Kullanıcılar")
        duzenlenen_kullanicilar = st.data_editor(st.session_state.kullanicilar, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Kullanıcı Değişikliklerini Kaydet"):
            st.session_state.kullanicilar = duzenlenen_kullanicilar
            kullanici_kaydet(duzenlenen_kullanicilar)
            st.success("Kullanıcılar başarıyla güncellendi!")
            st.rerun()
