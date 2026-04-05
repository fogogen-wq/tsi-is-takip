import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
from streamlit_gsheets import GSheetsConnection

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Zilan Takipte", layout="wide", page_icon="🚀")

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

# --- VERİ YÜKLEME VE KORUMA FONKSİYONU ---
def tablo_yukle(sheet_name, fallback_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=fallback_cols)
        for col in fallback_cols:
            if col not in df.columns: df[col] = ""
        df = df.fillna("")
        for col in df.columns:
            df[col] = df[col].astype(str).replace({"nan": "", "NaN": "", "None": ""})
        return df
    except:
        return pd.DataFrame(columns=fallback_cols)

def tablo_kaydet(df, sheet_name):
    try:
        conn.update(spreadsheet=URL, worksheet=sheet_name, data=df.fillna(""))
    except Exception as e:
        st.error(f"⚠️ Kayıt Hatası: Google Sheets'te '{sheet_name}' adında bir sekme bulunamadı!")

# --- 2. SESSION STATE (BELLEK) ---
if 'kullanicilar' not in st.session_state: st.session_state.kullanicilar = tablo_yukle("Kullanıcılar", ["KULLANICI_ADI", "SIFRE", "ROL", "EMAIL"])
if 'firmalar_db' not in st.session_state: st.session_state.firmalar_db = tablo_yukle("Firmalar", ["FİRMA_ADI", "YETKİLİ_KİŞİ", "EMAIL", "TITLE", "NOTLAR"])
if 'data' not in st.session_state: st.session_state.data = tablo_yukle("Sayfa1", ['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BAŞLANGIÇ', 'BİTİŞ', 'DURUM', 'ÖNCELİK', 'NOTLAR', 'AŞAMALAR', 'KAYIT_TARIHI'])
if 'toplanti_db' not in st.session_state: st.session_state.toplanti_db = tablo_yukle("Toplantı_Notları", ["TARİH", "KONU", "İLGİLİ_FİRMA", "KATILIMCILAR", "NOTLAR"])
if 'todo_db' not in st.session_state: st.session_state.todo_db = tablo_yukle("Yapilacaklar", ["YAPILACAK_IS", "TAMAMLANDI", "KULLANICI", "ÖNCELİK", "BİTİŞ_TARİHİ"])

if 'temp_stages' not in st.session_state: st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Bitiş Tarihi": "", "Durum": "Bekliyor", "Not": ""}]

def formu_sifirla():
    st.session_state.form_id += 1
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Bitiş Tarihi": "", "Durum": "Bekliyor", "Not": ""}]
    for key in list(st.session_state.keys()):
        if key.startswith("frm_") or key.startswith("st_") or key.startswith("top_"): del st.session_state[key]

# --- 3. LOGIN SİSTEMİ ---
if "giris_basarili" not in st.session_state:
    st.session_state.giris_basarili, st.session_state.aktif_kullanici, st.session_state.aktif_rol = False, None, None

kullanici_listesi = sorted(st.session_state.kullanicilar['KULLANICI_ADI'].dropna().unique().tolist()) if not st.session_state.kullanicilar.empty else ["Yönetici"]

if not st.session_state.giris_basarili:
    st.sidebar.title("🔐 Giriş")
    user = st.sidebar.selectbox("Kullanıcı", ["Seçiniz"] + kullanici_listesi)
    pwd = st.sidebar.text_input("Şifre", type="password")
    if st.sidebar.button("Giriş Yap"):
        user_row = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == user]
        if not user_row.empty and str(user_row.iloc[0]['SIFRE']) == pwd:
            st.session_state.giris_basarili, st.session_state.aktif_kullanici = True, user
            st.session_state.aktif_rol = user_row.iloc[0]['ROL']
            st.rerun()
        else: st.sidebar.error("Hatalı Giriş!")
    st.stop()

# --- 4. SIDEBAR VE GELİŞMİŞ FİLTRELER ---
st.sidebar.success(f"Hoş geldin, {st.session_state.aktif_kullanici}!")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.giris_basarili = False; st.rerun()

firmalar_crm = [str(f).strip() for f in st.session_state.firmalar_db['FİRMA_ADI'].dropna().tolist() if str(f).strip() != ""] if not st.session_state.firmalar_db.empty else []
firmalar_gorev = [str(f).strip() for f in st.session_state.data['FİRMA'].dropna().tolist() if str(f).strip() != ""] if not st.session_state.data.empty else []
liste_firmalar = sorted(list(set(firmalar_crm + firmalar_gorev)))

gorev_sorumlulari = [str(s).strip() for s in st.session_state.data['ANA SORUMLU'].dropna().tolist() if str(s).strip() != ""] if not st.session_state.data.empty else []
liste_sorumlular = sorted(list(set(kullanici_listesi + gorev_sorumlulari)))

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Detaylı Filtreler")
display_df = st.session_state.data.copy()

f_firma = st.sidebar.multiselect("🏢 Firma", liste_firmalar)
f_sorumlu = st.sidebar.multiselect("👤 Sorumlu", liste_sorumlular)
f_oncelik = st.sidebar.multiselect("⚡ Öncelik", ["Yüksek", "Orta", "Düşük"])

st.sidebar.markdown("**📅 Bitiş Tarihine Göre**")
tarih_aktif = st.sidebar.checkbox("Tarih Aralığı Belirle")
if tarih_aktif:
    t1, t2 = st.sidebar.columns(2)
    bas_tar = t1.date_input("Başlangıç", datetime.now() - timedelta(days=7))
    bit_tar = t2.date_input("Bitiş", datetime.now() + timedelta(days=30))

if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_sorumlu: display_df = display_df[display_df['ANA SORUMLU'].isin(f_sorumlu)]
if f_oncelik: display_df = display_df[display_df['ÖNCELİK'].isin(f_oncelik)]
if tarih_aktif:
    temp_dates = pd.to_datetime(display_df['BİTİŞ'], errors='coerce').dt.date
    display_df = display_df[temp_dates.between(bas_tar, bit_tar)]

# --- 5. SEKMELER ---
tabs_list = ["➕ Yeni Görev", "📋 İş Listesi ve Detaylar", "📊 Raporlama"]
if st.session_state.aktif_rol in ["Admin", "User"]:
    tabs_list.append("🏢 Firma Yönetimi")
    tabs_list.append("📝 Toplantı & Notlar")
    tabs_list.append("✅ Yapılacaklar")
    tabs_list.append("⚙️ Veri Yönetimi")
tabs_list.append("👤 Profil Ayarları")
if st.session_state.aktif_rol == "Admin": tabs_list.append("👥 Kullanıcı Yönetimi")

sekmeler = st.tabs(tabs_list)
sekme_sozlugu = dict(zip(tabs_list, sekmeler))

# ================= TAB: YENİ GÖREV =================
if "➕ Yeni Görev" in sekme_sozlugu:
    with sekme_sozlugu["➕ Yeni Görev"]:
        fid = st.session_state.form_id
        c1, c2 = st.columns(2)
        v_ad = c1.text_input("Görev Adı *", key=f"frm_ad_{fid}")
        v_f_sec = c1.selectbox("Firma *", ["Seçiniz", "➕ YENİ EKLE..."] + liste_firmalar, key=f"frm_f_sec_{fid}")
        v_firma = c1.text_input("Yeni Firma Adı *", key=f"frm_f_yeni_{fid}") if v_f_sec == "➕ YENİ EKLE..." else v_f_sec
        v_s_sec = c2.selectbox("Ana Sorumlu *", ["➕ YENİ EKLE..."] + liste_sorumlular, key=f"frm_s_sec_{fid}")
        v_sorumlu = c2.text_input("Yeni Sorumlu Adı", key=f"frm_s_yeni_{fid}") if v_s_sec == "➕ YENİ EKLE..." else v_s_sec
        v_basla = c1.date_input("Başlangıç", datetime.now(), key=f"frm_basla_{fid}")
        v_bitis = c2.date_input("Bitiş", datetime.now() + timedelta(days=7), key=f"frm_bit_{fid}")
        v_oncelik = c1.selectbox("Öncelik", ["Düşük", "Orta", "Yüksek"], key=f"frm_on_{fid}")
        v_durum = c2.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"], key=f"frm_dr_{fid}")
        v_not = st.text_area("📌 Notlar", key=f"frm_not_{fid}")

        st.subheader("🛠 Alt Aşamalar")
        yeni_asamalar = []
        for i, stg in enumerate(st.session_state.temp_stages):
            ca1, ca2, ca3, ca4, ca5 = st.columns([3, 2, 2, 2, 3])
            s_ad = ca1.text_input(f"{i+1}. İşlem", value=stg.get("Aşama Adı", ""), key=f"st_ad_{fid}_{i}")
            s_ki_sec = ca2.selectbox("Sorumlu", ["Aynı", "➕ YENİ EKLE..."] + liste_sorumlular, key=f"st_ki_sec_{fid}_{i}")
            s_final_ki = (v_sorumlu if s_ki_sec == "Aynı" else (ca2.text_input("Yeni Sorumlu", key=f"st_ki_y_{fid}_{i}") if s_ki_sec == "➕ YENİ EKLE..." else s_ki_sec))
            s_bit = ca3.date_input("Bitiş", datetime.now() + timedelta(days=7), key=f"st_bit_{fid}_{i}")
            s_dr = ca4.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"], key=f"st_dr_{fid}_{i}")
            s_nt = ca5.text_input("Aşama Notu", value=stg.get("Not", ""), key=f"st_nt_{fid}_{i}")
            yeni_asamalar.append({"Aşama Adı": s_ad, "Sorumlu": s_final_ki, "Bitiş Tarihi": s_bit.strftime('%Y-%m-%d'), "Durum": s_dr, "Not": s_nt})

        if st.button("➕ Aşama Ekle"):
            st.session_state.temp_stages.append({"Aşama Adı": "", "Sorumlu": "Aynı", "Bitiş Tarihi": "", "Durum": "Bekliyor", "Not": ""})
            st.rerun()

        if st.button("✅ KAYDET", use_container_width=True):
            if v_ad and v_firma and v_firma != "Seçiniz":
                if v_firma not in firmalar_crm:
                    yeni_f = pd.DataFrame([{"FİRMA_ADI": v_firma, "YETKİLİ_KİŞİ": "", "EMAIL": "", "TITLE": "", "NOTLAR": ""}])
                    st.session_state.firmalar_db = pd.concat([st.session_state.firmalar_db, yeni_f], ignore_index=True)
                    tablo_kaydet(st.session_state.firmalar_db, "Firmalar")

                yeni = {
                    'GÖREV ADI': v_ad, 'FİRMA': v_firma, 'ANA SORUMLU': v_sorumlu,
                    'BAŞLANGIÇ': v_basla.strftime('%Y-%m-%d'), 'BİTİŞ': v_bitis.strftime('%Y-%m-%d'),
                    'DURUM': v_durum, 'ÖNCELİK': v_oncelik, 'NOTLAR': v_not,
                    'AŞAMALAR': json.dumps([a for a in yeni_asamalar if a["Aşama Adı"].strip()], ensure_ascii=False),
                    'KAYIT_TARIHI': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([yeni])], ignore_index=True)
                tablo_kaydet(st.session_state.data, "Sayfa1")
                st.success("Görev başarıyla kaydedildi!"); formu_sifirla(); st.rerun()
            else: st.error("Lütfen Görev Adı yazın ve Firma seçin.")

# ================= TAB: İŞ LİSTESİ VE DETAYLAR =================
with sekme_sozlugu["📋 İş Listesi ve Detaylar"]:
    if not display_df.empty:
        gorunum = st.radio("Görünüm Seçimi", ["🚀 Aktif Görevler", "🗄️ Arşiv (Tamamlandı & İptal)"], horizontal=True)
        st.divider()
        
        if gorunum == "🚀 Aktif Görevler":
            tablo_df = display_df[~display_df['DURUM'].isin(['Tamamlandı', 'İptal'])]
        else:
            tablo_df = display_df[display_df['DURUM'].isin(['Tamamlandı', 'İptal'])]

        if not tablo_df.empty:
            gosterilecek = tablo_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'], errors='ignore')
            sel = st.dataframe(gosterilecek, use_container_width=True, height=350, selection_mode="single-row", on_select="rerun", key="tablo")
            rows = sel.get("selection", {}).get("rows", [])
            
            if rows and len(rows) > 0 and rows[0] < len(gosterilecek):
                idx = gosterilecek.index[rows[0]]
                secili = st.session_state.data.loc[idx]
                
                with st.container(border=True):
                    st.markdown(f"### 🎯 {secili['GÖREV ADI']}")
                    firma_info = st.session_state.firmalar_db[st.session_state.firmalar_db['FİRMA_ADI'] == secili['FİRMA']]
                    if not firma_info.empty and str(firma_info.iloc[0]['YETKİLİ_KİŞİ']).strip() != "":
                        st.caption(f"📞 Yetkili: {firma_info.iloc[0]['YETKİLİ_KİŞİ']} | 📧 {firma_info.iloc[0]['EMAIL']}")
                    
                    c1, c2 = st.columns(2)
                    durumlar = ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"]
                    
                    y_dr = c1.selectbox("Durum", durumlar, index=durumlar.index(secili['DURUM']) if secili['DURUM'] in durumlar else 0, key=f"up_dr_{idx}")
                    y_nt = c2.text_input("Not", value=str(secili['NOTLAR']) if pd.notna(secili['NOTLAR']) else "", key=f"up_nt_{idx}")
                    
                    as_list = json.loads(secili['AŞAMALAR']) if pd.notna(secili['AŞAMALAR']) and secili['AŞAMALAR'] else []
                    df_as = pd.DataFrame(as_list)
                    
                    # --- HATA ÇÖZÜMÜ: VERİ TİPİ KONTROLÜ ---
                    if df_as.empty:
                        df_as = pd.DataFrame(columns=["Aşama Adı", "Sorumlu", "Bitiş Tarihi", "Durum", "Not"])
                    else:
                        if "Bitiş Tarihi" not in df_as.columns: df_as["Bitiş Tarihi"] = ""
                        # Boş tarihleri NaT yaparak DateColumn hatasını engelliyoruz
                        df_as['Bitiş Tarihi'] = pd.to_datetime(df_as['Bitiş Tarihi'], errors='coerce')
                    
                    ed_as = st.data_editor(
                        df_as, num_rows="dynamic", use_container_width=True, key=f"ed_as_{idx}", 
                        column_config={
                            "Sorumlu": st.column_config.SelectboxColumn("Sorumlu", options=liste_sorumlular),
                            "Bitiş Tarihi": st.column_config.DateColumn("Bitiş Tarihi", format="YYYY-MM-DD"),
                            "Durum": st.column_config.SelectboxColumn("Durum", options=durumlar)
                        }
                    )
                    
                    st.divider()
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("💾 Değişiklikleri Kaydet", use_container_width=True):
                            # Tarihleri JSON'a yazmadan önce tekrar metne çeviriyoruz
                            ed_as['Bitiş Tarihi'] = pd.to_datetime(ed_as['Bitiş Tarihi'], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")
                            st.session_state.data.at[idx, 'DURUM'] = y_dr
                            st.session_state.data.at[idx, 'NOTLAR'] = y_nt
                            st.session_state.data.at[idx, 'AŞAMALAR'] = json.dumps(ed_as.to_dict('records'), ensure_ascii=False)
                            tablo_kaydet(st.session_state.data, "Sayfa1")
                            st.success("Görev güncellendi!"); st.rerun()
                            
                    with bc2:
                        if st.button("🚫 Görevi Listeden Kaldır", type="primary", use_container_width=True):
                            st.session_state.data = st.session_state.data.drop(idx).reset_index(drop=True)
                            tablo_kaydet(st.session_state.data, "Sayfa1")
                            st.success("Görev kaldırıldı!"); st.rerun()
        else:
            st.info("Bu görünümde listelenecek görev bulunmuyor.")

# ================= TAB: DİĞER SEKMELER =================
with sekme_sozlugu["📊 Raporlama"]:
    st.subheader("📊 Gelişmiş Raporlar")
    if not display_df.empty:
        df_rapor = display_df.copy()
        m1, m2, m3, m4 = st.columns(4); m1.metric("Toplam Görev", len(df_rapor)); m2.metric("Tamamlanan ✅", len(df_rapor[df_rapor['DURUM'] == 'Tamamlandı'])); m3.metric("Devam Eden ⏳", len(df_rapor[df_rapor['DURUM'] == 'Devam Ediyor'])); m4.metric("Kritik ⚠️", len(df_rapor[df_rapor['DURUM'].isin(['Gecikti', 'İptal'])]))
        st.divider(); c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.histogram(df_rapor, y="FİRMA", color="DURUM", barmode="group", title="Firma İş Yükü", orientation='h'), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_rapor, names="DURUM", title="İş Durumu"), use_container_width=True)

if "🏢 Firma Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["🏢 Firma Yönetimi"]:
        st.subheader("🏢 Firma ve Rehber")
        st.session_state.firmalar_db = st.session_state.firmalar_db.fillna("").astype(str)
        ed_f = st.data_editor(st.session_state.firmalar_db, num_rows="dynamic", use_container_width=True, key="crm_ed", column_config={"FİRMA_ADI": st.column_config.TextColumn("Firma Adı", required=True)})
        if st.button("💾 Rehberi Kaydet"):
            st.session_state.firmalar_db = ed_f.fillna("").astype(str); tablo_kaydet(ed_f, "Firmalar"); st.success("Rehber güncellendi!"); st.rerun()

if "📝 Toplantı & Notlar" in sekme_sozlugu:
    with sekme_sozlugu["📝 Toplantı & Notlar"]:
        st.subheader("📝 Toplantı Notları")
        with st.container(border=True):
            fid = st.session_state.form_id; col1, col2 = st.columns(2)
            t_konu = col1.text_input("Konu *", key=f"top_k_{fid}"); t_firma = col2.selectbox("Firma", ["Seçiniz"] + liste_firmalar, key=f"top_f_{fid}")
            t_notlar = st.text_area("Notlar", key=f"top_n_{fid}")
            if st.button("💾 Notu Kaydet", use_container_width=True):
                if t_konu:
                    y_not = {"TARİH": datetime.now().strftime('%Y-%m-%d'), "KONU": t_konu, "İLGİLİ_FİRMA": t_firma, "NOTLAR": t_notlar}
                    st.session_state.toplanti_db = pd.concat([st.session_state.toplanti_db, pd.DataFrame([y_not])], ignore_index=True)
                    tablo_kaydet(st.session_state.toplanti_db, "Toplantı_Notları"); st.success("Not kaydedildi!"); formu_sifirla(); st.rerun()

if "✅ Yapılacaklar" in sekme_sozlugu:
    with sekme_sozlugu["✅ Yapılacaklar"]:
        st.subheader("✅ Ajanda (To-Do)")
        kt = st.session_state.todo_db[st.session_state.todo_db['KULLANICI'] == st.session_state.aktif_kullanici].copy()
        kt['TAMAMLANDI'] = kt['TAMAMLANDI'].astype(str).str.upper().isin(['TRUE', '1', 'TRUE.0'])
        kt['BİTİŞ_TARİHİ'] = pd.to_datetime(kt['BİTİŞ_TARİHİ'], errors='coerce')
        ed_t = st.data_editor(kt, num_rows="dynamic", use_container_width=True, hide_index=True, key="todo_ed", column_config={"TAMAMLANDI": st.column_config.CheckboxColumn("Bitti"), "BİTİŞ_TARİHİ": st.column_config.DateColumn("Tarih"), "KULLANICI": None})
        if st.button("💾 Listeyi Güncelle"):
            ed_t['KULLANICI'] = st.session_state.aktif_kullanici; ed_t['BİTİŞ_TARİHİ'] = ed_t['BİTİŞ_TARİHİ'].dt.strftime('%Y-%m-%d').fillna("")
            st.session_state.todo_db = pd.concat([st.session_state.todo_db[st.session_state.todo_db['KULLANICI'] != st.session_state.aktif_kullanici], ed_t], ignore_index=True)
            tablo_kaydet(st.session_state.todo_db, "Yapilacaklar"); st.success("Liste güncellendi!"); st.rerun()

if "⚙️ Veri Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["⚙️ Veri Yönetimi"]: st.download_button("📥 Excel İndir", display_df.to_csv(index=False).encode('utf-8-sig'), "is_listesi.csv", "text/csv")

with sekme_sozlugu["👤 Profil Ayarları"]:
    st.subheader("👤 Şifre Güncelle")
    e_p = st.text_input("Eski Şifre", type="password"); n_p = st.text_input("Yeni Şifre", type="password")
    if st.button("💾 Şifreyi Değiştir"):
        idx = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == st.session_state.aktif_kullanici].index[0]
        if str(st.session_state.kullanicilar.at[idx, 'SIFRE']) == e_p:
            st.session_state.kullanicilar.at[idx, 'SIFRE'] = n_p; tablo_kaydet(st.session_state.kullanicilar, "Kullanıcılar"); st.success("Şifre güncellendi!"); st.rerun()

if "👥 Kullanıcı Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["👥 Kullanıcı Yönetimi"]:
        st.subheader("👥 Kullanıcı Yetki")
        ed_u = st.data_editor(st.session_state.kullanicilar, num_rows="dynamic", use_container_width=True, column_config={"SIFRE": None})
        if st.button("💾 Kullanıcıları Kaydet"):
            ed_u['SIFRE'] = ed_u['SIFRE'].fillna("1234").replace("", "1234"); tablo_kaydet(ed_u, "Kullanıcılar"); st.success("Kaydedildi!"); st.rerun()
