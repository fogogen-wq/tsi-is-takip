import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import json
from streamlit_gsheets import GSheetsConnection

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="TSI Yönetim Paneli", layout="wide", page_icon="🚀")

# --- MODERN UI CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 5% 10%;
        border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div.stButton > button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 1. VERİTABANI VE BAĞLANTI ---
USER_DB = "kullanicilar.csv"
conn = st.connection("gsheets", type=GSheetsConnection)

if 'form_id' not in st.session_state:
    st.session_state.form_id = 0  # Formu sıfırlamak için versiyon takibi

def veriyi_yukle():
    try:
        df = conn.read(ttl=0)
        if 'BAŞLANGIÇ' in df.columns:
            df['BAŞLANGIÇ'] = pd.to_datetime(df['BAŞLANGIÇ']).dt.strftime('%Y-%m-%d')
        return df
    except:
        columns = ['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BAŞLANGIÇ', 'BİTİŞ', 'DURUM', 'ÖNCELİK', 'NOTLAR', 'AŞAMALAR', 'KAYIT_TARIHI']
        return pd.DataFrame(columns=columns)

def veriyi_kaydet(df):
    # Boşlukları temizle ve doğrudan bağlantı kur
    temiz_df = df.fillna("")
    conn.update(
        spreadsheet="https://docs.google.com/spreadsheets/d/1iF2VPQmygjibDXm3Q93COpMu0r4p4odayQZa_0ej0qM/edit?usp=sharing",
        worksheet="Sayfa1",
        data=temiz_df
    )

# --- 2. SESSION STATE VE SIFIRLAMA ---
if 'data' not in st.session_state:
    st.session_state.data = veriyi_yukle()

if 'temp_stages' not in st.session_state:
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]

def formu_sifirla():
    # Form versiyonunu artırarak tüm widget'ları zorla temizle
    st.session_state.form_id += 1
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]
    # frm_ ile başlayan tüm manuel girdileri sil
    for key in list(st.session_state.keys()):
        if key.startswith("frm_"):
            del st.session_state[key]

# Yardımcı Fonksiyonlar
def asamalari_coz(asama_metni):
    try:
        if pd.isna(asama_metni) or asama_metni == "": return []
        asamalar = json.loads(str(asama_metni))
        return asamalar if isinstance(asamalar, list) else []
    except: return []

def asamalari_paketle(asama_listesi):
    return json.dumps(asama_listesi, ensure_ascii=False)

# --- 3. LOGIN SİSTEMİ ---
if "giris_basarili" not in st.session_state:
    st.session_state.giris_basarili, st.session_state.aktif_kullanici, st.session_state.aktif_rol = False, None, None

kullanicilar = ["Yönetici", "Zilan Demir", "Nilay", "Saim", "Uğur"]

if not st.session_state.giris_basarili:
    st.sidebar.title("🔐 Giriş")
    user = st.sidebar.selectbox("Kullanıcı", ["Seçiniz"] + kullanicilar)
    pwd = st.sidebar.text_input("Şifre", type="password")
    if st.sidebar.button("Giriş Yap"):
        if user != "Seçiniz" and pwd == "1234" or (user == "Yönetici" and pwd == "admin123"):
            st.session_state.giris_basarili, st.session_state.aktif_kullanici = True, user
            st.session_state.aktif_rol = "Admin" if user == "Yönetici" else "User"
            st.rerun()
        else: st.sidebar.error("Hatalı giriş!")
    st.stop()

# --- 4. ANA EKRAN VE FİLTRELER ---
st.sidebar.success(f"Hoş geldin, {st.session_state.aktif_kullanici}!")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.giris_basarili = False
    st.rerun()

firmalar = sorted(st.session_state.data['FİRMA'].dropna().unique().tolist()) if not st.session_state.data.empty else ["TSI"]
sorumlular = [k for k in kullanicilar if k != "Yönetici"]

st.sidebar.divider()
f_firma = st.sidebar.multiselect("Firma Filtresi", firmalar)
f_durum = st.sidebar.multiselect("Durum Filtresi", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"])

display_df = st.session_state.data.copy()
if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_durum: display_df = display_df[display_df['DURUM'].isin(f_durum)]

tab_ekle, tab_liste, tab_rapor = st.tabs(["➕ Yeni Görev", "📋 İş Listesi", "📊 Raporlama"])

# ================= TAB 1: YENİ GÖREV (SIFIRLANABİLİR FORM) =================
with tab_ekle:
    # form_id değiştiğinde tüm bu alanlar sıfırlanır
    fid = st.session_state.form_id
    c1, c2 = st.columns(2)
    v_ad = c1.text_input("Görev Adı *", key=f"frm_ad_{fid}")
    v_firma_sec = c1.selectbox("Firma *", ["➕ YENİ EKLE..."] + firmalar, key=f"frm_f_sec_{fid}")
    v_firma = c1.text_input("Yeni Firma Adı *", key=f"frm_f_yeni_{fid}") if v_firma_sec == "➕ YENİ EKLE..." else v_firma_sec
    v_sorumlu = c2.selectbox("Ana Sorumlu *", sorumlular, key=f"frm_s_sec_{fid}")
    v_bitis = c2.date_input("Hedef Bitiş", datetime.now() + timedelta(days=7), key=f"frm_bit_{fid}")
    v_oncelik = st.selectbox("Öncelik", ["Düşük", "Orta", "Yüksek"], key=f"frm_on_{fid}")
    v_not = st.text_area("📌 Genel Görev Notu", key=f"frm_not_{fid}")

    st.subheader("🛠 Alt Aşamalar")
    yeni_asamalar = []
    for i, stg in enumerate(st.session_state.temp_stages):
        ca1, ca2, ca3, ca4 = st.columns([3, 2, 2, 3])
        s_ad = ca1.text_input("İşlem", value=stg["Aşama Adı"], key=f"frm_st_ad_{fid}_{i}")
        s_ki = ca2.selectbox("Sorumlu", ["Aynı"] + sorumlular, key=f"frm_st_ki_{fid}_{i}")
        s_dr = ca3.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı"], key=f"frm_st_dr_{fid}_{i}")
        s_nt = ca4.text_input("Not", value=stg["Not"], key=f"frm_st_nt_{fid}_{i}")
        yeni_asamalar.append({"Aşama Adı": s_ad, "Sorumlu": v_sorumlu if s_ki=="Aynı" else s_ki, "Durum": s_dr, "Not": s_nt})

    if st.button("➕ Aşama Ekle"):
        st.session_state.temp_stages.append({"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""})
        st.rerun()

    if st.button("✅ GÖREVİ OLUŞTUR", use_container_width=True):
        if v_ad and v_firma:
            yeni_gorev = {
                'GÖREV ADI': v_ad, 'FİRMA': v_firma, 'ANA SORUMLU': v_sorumlu,
                'BAŞLANGIÇ': datetime.now().strftime('%Y-%m-%d'), 'BİTİŞ': v_bitis.strftime('%Y-%m-%d'),
                'DURUM': 'Bekliyor', 'ÖNCELİK': v_oncelik, 'NOTLAR': v_not,
                'AŞAMALAR': asamalari_paketle([a for a in yeni_asamalar if a["Aşama Adı"].strip()]),
                'KAYIT_TARIHI': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([yeni_gorev])], ignore_index=True)
            veriyi_kaydet(st.session_state.data)
            st.success("Görev başarıyla eklendi!")
            formu_sifirla()
            st.rerun()
        else: st.error("Zorunlu alanları doldurun!")

# ================= TAB 2: LİSTE VE TIKLA-DÜZENLE =================
with tab_liste:
    if not display_df.empty:
        gosterilecek_df = display_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'], errors='ignore')
        selection = st.dataframe(gosterilecek_df, use_container_width=True, height=350, selection_mode="single-row", on_select="rerun", key="ana_tablo")
        
        selected_rows = selection.get("selection", {}).get("rows", [])
        if selected_rows:
            st.divider()
            idx = gosterilecek_df.index[selected_rows[0]]
            secili = st.session_state.data.loc[idx]
            
            with st.container(border=True):
                st.markdown(f"### 🎯 Detay: {secili['GÖREV ADI']}")
                c1, c2 = st.columns(2)
                y_durum = c1.selectbox("Genel Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"], index=0, key=f"up_dr_{idx}")
                y_not = c2.text_input("Genel Not", value=str(secili['NOTLAR']), key=f"up_nt_{idx}")
                
                asamalar = asamalari_coz(secili['AŞAMALAR'])
                asama_df = pd.DataFrame(asamalar) if asamalar else pd.DataFrame(columns=["Aşama Adı", "Sorumlu", "Durum", "Not"])
                
                edit_asamalar = st.data_editor(asama_df, num_rows="dynamic", use_container_width=True, key=f"ed_st_{idx}")
                
                if st.button("💾 Değişiklikleri Kaydet", use_container_width=True):
                    st.session_state.data.at[idx, 'DURUM'] = y_durum
                    st.session_state.data.at[idx, 'NOTLAR'] = y_not
                    st.session_state.data.at[idx, 'AŞAMALAR'] = asamalari_paketle(edit_asamalar.to_dict('records'))
                    veriyi_kaydet(st.session_state.data)
                    st.success("Güncellendi!")
                    st.rerun()
    else: st.info("Görev bulunamadı.")

# ================= TAB 3: RAPOR =================
with tab_rapor:
    if not st.session_state.data.empty:
        st.plotly_chart(px.pie(st.session_state.data, names="DURUM", title="İşlerin Durum Dağılımı"), use_container_width=True)
