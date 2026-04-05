import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
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
URL = "https://docs.google.com/spreadsheets/d/1iF2VPQmygjibDXm3Q93COpMu0r4p4odayQZa_0ej0qM/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

if 'form_id' not in st.session_state:
    st.session_state.form_id = 0  

def kullanici_yukle():
    try:
        df = conn.read(worksheet="Kullanıcılar", ttl=0)
        return df
    except:
        return pd.DataFrame([{"KULLANICI_ADI": "Yönetici", "SIFRE": "admin123", "ROL": "Admin"}])

def kullanici_kaydet(df):
    conn.update(spreadsheet=URL, worksheet="Kullanıcılar", data=df.fillna(""))

def veriyi_yukle():
    try:
        df = conn.read(worksheet="Sayfa1", ttl=0)
        if 'BAŞLANGIÇ' in df.columns:
            df['BAŞLANGIÇ'] = pd.to_datetime(df['BAŞLANGIÇ']).dt.strftime('%Y-%m-%d')
        return df
    except:
        columns = ['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BAŞLANGIÇ', 'BİTİŞ', 'DURUM', 'ÖNCELİK', 'NOTLAR', 'AŞAMALAR', 'KAYIT_TARIHI']
        return pd.DataFrame(columns=columns)

def veriyi_kaydet(df):
    conn.update(spreadsheet=URL, worksheet="Sayfa1", data=df.fillna(""))

# --- 2. SESSION STATE ---
if 'kullanicilar' not in st.session_state: st.session_state.kullanicilar = kullanici_yukle()
if 'data' not in st.session_state: st.session_state.data = veriyi_yukle()
if 'temp_stages' not in st.session_state: st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]

def formu_sifirla():
    st.session_state.form_id += 1
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]
    for key in list(st.session_state.keys()):
        if key.startswith("frm_") or key.startswith("st_"): del st.session_state[key]

def asamalari_coz(asama_metni):
    try:
        if pd.isna(asama_metni) or asama_metni == "": return []
        return json.loads(str(asama_metni))
    except: return []

def asamalari_paketle(asama_listesi):
    return json.dumps(asama_listesi, ensure_ascii=False)

# --- 3. LOGIN SİSTEMİ ---
if "giris_basarili" not in st.session_state:
    st.session_state.giris_basarili, st.session_state.aktif_kullanici, st.session_state.aktif_rol = False, None, None

# Kullanıcı listesini alfabetik sırala
kullanici_listesi = sorted(st.session_state.kullanicilar['KULLANICI_ADI'].unique().tolist())

if not st.session_state.giris_basarili:
    st.sidebar.title("🔐 Giriş")
    user = st.sidebar.selectbox("Kullanıcı", ["Seçiniz"] + kullanici_listesi)
    pwd = st.sidebar.text_input("Şifre", type="password")
    if st.sidebar.button("Giriş Yap"):
        if user != "Seçiniz":
            user_row = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == user].iloc[0]
            if str(user_row['SIFRE']) == pwd:
                st.session_state.giris_basarili, st.session_state.aktif_kullanici = True, user
                st.session_state.aktif_rol = user_row['ROL']
                st.rerun()
            else: st.sidebar.error("Hatalı şifre!")
    st.stop()

# --- 4. SIDEBAR VE FİLTRELER ---
st.sidebar.success(f"Hoş geldin, {st.session_state.aktif_kullanici}!")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.giris_basarili = False
    st.rerun()

# Listeleri her zaman alfabetik hazırla
mevcut_firmalar = sorted(st.session_state.data['FİRMA'].dropna().unique().tolist()) if not st.session_state.data.empty else []
gorev_sorumlulari = st.session_state.data['ANA SORUMLU'].dropna().unique().tolist() if not st.session_state.data.empty else []
tum_sorumlular = sorted(list(set(kullanici_listesi + gorev_sorumlulari)))

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Filtreler")
display_df = st.session_state.data.copy()
f_firma = st.sidebar.multiselect("🏢 Firma", mevcut_firmalar)
f_sorumlu = st.sidebar.multiselect("👤 Sorumlu", tum_sorumlular)
f_durum = st.sidebar.multiselect("📌 Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"])

if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_sorumlu: display_df = display_df[display_df['ANA SORUMLU'].isin(f_sorumlu)]
if f_durum: display_df = display_df[display_df['DURUM'].isin(f_durum)]

# --- 5. SEKMELER ---
tab_isimleri = []
if st.session_state.aktif_rol in ["Admin", "User"]: tab_isimleri.append("➕ Yeni Görev")
tab_isimleri.append("📋 İş Listesi ve Detaylar")
tab_isimleri.append("📊 Raporlama")
if st.session_state.aktif_rol in ["Admin", "User"]: tab_isimleri.append("⚙️ Veri Yönetimi")
tab_isimleri.append("👤 Profil Ayarları")
if st.session_state.aktif_rol == "Admin": tab_isimleri.append("👥 Kullanıcı Yönetimi")

sekmeler = st.tabs(tab_isimleri)
sekme_sozlugu = dict(zip(tab_isimleri, sekmeler))

# ================= TAB 1: YENİ GÖREV =================
if "➕ Yeni Görev" in sekme_sozlugu:
    with sekme_sozlugu["➕ Yeni Görev"]:
        fid = st.session_state.form_id
        c1, c2 = st.columns(2)
        v_ad = c1.text_input("Görev Adı *", key=f"frm_ad_{fid}")
        
        # Alfabetik Firma Seçimi
        v_f_sec = c1.selectbox("Firma *", ["➕ YENİ EKLE..."] + mevcut_firmalar, key=f"frm_f_sec_{fid}")
        v_firma = c1.text_input("Yeni Firma Adı", key=f"frm_f_yeni_{fid}") if v_f_sec == "➕ YENİ EKLE..." else v_f_sec
        
        # Alfabetik Sorumlu Seçimi
        v_s_sec = c2.selectbox("Ana Sorumlu *", ["➕ YENİ EKLE..."] + tum_sorumlular, key=f"frm_s_sec_{fid}")
        v_sorumlu = c2.text_input("Yeni Sorumlu Adı", key=f"frm_s_yeni_{fid}") if v_s_sec == "➕ YENİ EKLE..." else v_s_sec
        
        v_bitis = c2.date_input("Bitiş", datetime.now() + timedelta(days=7), key=f"frm_bit_{fid}")
        v_oncelik = st.selectbox("Öncelik", ["Düşük", "Orta", "Yüksek"], key=f"frm_on_{fid}")
        v_durum = st.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı"], key=f"frm_dr_{fid}")
        v_not = st.text_area("📌 Notlar", key=f"frm_not_{fid}")

        st.subheader("🛠 Alt Aşamalar")
        yeni_asamalar = []
        for i, stg in enumerate(st.session_state.temp_stages):
            ca1, ca2, ca3, ca4 = st.columns([3, 3, 2, 3])
            s_ad = ca1.text_input(f"{i+1}. İşlem", value=stg["Aşama Adı"], key=f"st_ad_{fid}_{i}")
            
            # Alfabetik Alt Sorumlu Seçimi
            s_ki_sec = ca2.selectbox("Sorumlu", ["Aynı", "➕ YENİ EKLE..."] + tum_sorumlular, key=f"st_ki_sec_{fid}_{i}")
            if s_ki_sec == "Aynı": s_final_ki = v_sorumlu
            elif s_ki_sec == "➕ YENİ EKLE...": s_final_ki = ca2.text_input("Yeni Sorumlu", key=f"st_ki_y_{fid}_{i}")
            else: s_final_ki = s_ki_sec
            
            s_dr = ca3.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı"], key=f"st_dr_{fid}_{i}")
            s_nt = ca4.text_input("Not", value=stg["Not"], key=f"st_nt_{fid}_{i}")
            yeni_asamalar.append({"Aşama Adı": s_ad, "Sorumlu": s_final_ki, "Durum": s_dr, "Not": s_nt})

        if st.button("➕ Aşama Ekle"):
            st.session_state.temp_stages.append({"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""})
            st.rerun()

        if st.button("✅ KAYDET", use_container_width=True):
            if v_ad and v_firma and v_sorumlu:
                yeni = {
                    'GÖREV ADI': v_ad, 'FİRMA': v_firma, 'ANA SORUMLU': v_sorumlu,
                    'BAŞLANGIÇ': datetime.now().strftime('%Y-%m-%d'), 'BİTİŞ': v_bitis.strftime('%Y-%m-%d'),
                    'DURUM': v_durum, 'ÖNCELİK': v_oncelik, 'NOTLAR': v_not,
                    'AŞAMALAR': asamalari_paketle([a for a in yeni_asamalar if a["Aşama Adı"].strip()]),
                    'KAYIT_TARIHI': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([yeni])], ignore_index=True)
                veriyi_kaydet(st.session_state.data)
                st.success("Kaydedildi!")
                formu_sifirla()
                st.rerun()

# ================= TAB 2: LİSTE VE DETAY =================
with sekme_sozlugu["📋 İş Listesi ve Detaylar"]:
    if not display_df.empty:
        gosterilecek = display_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'], errors='ignore')
        sel = st.dataframe(gosterilecek, use_container_width=True, height=350, selection_mode="single-row", on_select="rerun", key="tablo")
        rows = sel.get("selection", {}).get("rows", [])
        if rows:
            st.divider()
            idx = gosterilecek.index[rows[0]]
            secili = st.session_state.data.loc[idx]
            with st.container(border=True):
                st.markdown(f"### 🎯 {secili['GÖREV ADI']}")
                as_df = pd.DataFrame(asamalari_coz(secili['AŞAMALAR']))
                
                if st.session_state.aktif_rol == "Guest":
                    st.info(f"**Durum:** {secili['DURUM']} | **Not:** {secili['NOTLAR']}")
                    st.dataframe(as_df, use_container_width=True, hide_index=True)
                else:
                    c1, c2 = st.columns(2)
                    y_dr = c1.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"], index=["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"].index(secili['DURUM']) if secili['DURUM'] in ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"] else 0, key=f"up_dr_{idx}")
                    y_nt = c2.text_input("Genel Not", value=str(secili['NOTLAR']), key=f"up_nt_{idx}")
                    
                    # Düzenleme modunda da sorumlular alfabetik
                    ed_as = st.data_editor(as_df, num_rows="dynamic", use_container_width=True, key=f"ed_as_{idx}",
                                          column_config={"Sorumlu": st.column_config.SelectboxColumn("Sorumlu", options=tum_sorumlular)})
                    if st.button("💾 Güncelle", use_container_width=True):
                        st.session_state.data.at[idx, 'DURUM'] = y_dr
                        st.session_state.data.at[idx, 'NOTLAR'] = y_nt
                        st.session_state.data.at[idx, 'AŞAMALAR'] = asamalari_paketle(ed_as.to_dict('records'))
                        veriyi_kaydet(st.session_state.data)
                        st.success("Güncellendi!"); st.rerun()

# ================= TAB: PROFİL VE DİĞERLERİ =================
with sekme_sozlugu["👤 Profil Ayarları"]:
    st.subheader("👤 Profil Bilgileri")
    with st.container(border=True):
        e_pwd = st.text_input("Mevcut Şifre", type="password", key="p_old")
        n_pwd = st.text_input("Yeni Şifre", type="password", key="p_new")
        n_pwd_c = st.text_input("Yeni Şifre (Tekrar)", type="password", key="p_conf")
        if st.button("💾 Şifreyi Güncelle"):
            user_idx = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == st.session_state.aktif_kullanici].index[0]
            if str(st.session_state.kullanicilar.at[user_idx, 'SIFRE']) == e_pwd and n_pwd == n_pwd_c and len(n_pwd) >= 4:
                st.session_state.kullanicilar.at[user_idx, 'SIFRE'] = n_pwd
                kullanici_kaydet(st.session_state.kullanicilar)
                st.success("✅ Şifre güncellendi!"); st.rerun()
            else: st.error("❌ Hatalı bilgi veya şifre uyuşmuyor.")

with sekme_sozlugu["📊 Raporlama"]:
    if not display_df.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(display_df, names="DURUM", title="İşlerin Durum Dağılımı"), use_container_width=True)
        c2.plotly_chart(px.bar(display_df, x="FİRMA", color="DURUM", title="Firma Bazlı İş Yükü"), use_container_width=True)

if "⚙️ Veri Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["⚙️ Veri Yönetimi"]:
        st.download_button("📥 Verileri İndir", display_df.to_csv(index=False).encode('utf-8'), "yedek.csv", "text/csv")

if "👥 Kullanıcı Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["👥 Kullanıcı Yönetimi"]:
        ed_u = st.data_editor(st.session_state.kullanicilar, num_rows="dynamic", use_container_width=True,
                             column_config={"ROL": st.column_config.SelectboxColumn("ROL", options=["Admin", "User", "Guest"])})
        if st.button("💾 Kullanıcıları Kaydet"):
            st.session_state.kullanicilar = ed_u
            kullanici_kaydet(ed_u); st.success("Kaydedildi!")
