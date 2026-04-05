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

# --- VERİ YÜKLEME VE KURŞUN GEÇİRMEZ KORUMA FONKSİYONU ---
def tablo_yukle(sheet_name, fallback_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df.empty:
            return pd.DataFrame(columns=fallback_cols)
            
        # KORUMA: Google Sheets'te kolon adı yanlış yazılmışsa veya eksikse, çökmesini engellemek için otomatik ekle
        for col in fallback_cols:
            if col not in df.columns:
                df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=fallback_cols)

def tablo_kaydet(df, sheet_name):
    conn.update(spreadsheet=URL, worksheet=sheet_name, data=df.fillna(""))

# --- 2. SESSION STATE (BELLEK) ---
if 'kullanicilar' not in st.session_state: 
    st.session_state.kullanicilar = tablo_yukle("Kullanıcılar", ["KULLANICI_ADI", "SIFRE", "ROL"])
if 'firmalar_db' not in st.session_state: 
    st.session_state.firmalar_db = tablo_yukle("Firmalar", ["FİRMA_ADI", "YETKİLİ_KİŞİ", "EMAIL", "TITLE", "NOTLAR"])
if 'data' not in st.session_state: 
    st.session_state.data = tablo_yukle("Sayfa1", ['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BAŞLANGIÇ', 'BİTİŞ', 'DURUM', 'ÖNCELİK', 'NOTLAR', 'AŞAMALAR', 'KAYIT_TARIHI'])

if 'temp_stages' not in st.session_state:
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]

def formu_sifirla():
    st.session_state.form_id += 1
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]
    for key in list(st.session_state.keys()):
        if key.startswith("frm_") or key.startswith("st_"): del st.session_state[key]

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
        else: st.sidebar.error("Hatalı Giriş veya Şifre!")
    st.stop()

# --- 4. SIDEBAR VE FİLTRELER (ALFABETİK LİSTELER) ---
st.sidebar.success(f"Hoş geldin, {st.session_state.aktif_kullanici}!")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.giris_basarili = False
    st.rerun()

firmalar_crm = [str(f).strip() for f in st.session_state.firmalar_db['FİRMA_ADI'].dropna().tolist() if str(f).strip() != ""] if not st.session_state.firmalar_db.empty else []
firmalar_gorev = [str(f).strip() for f in st.session_state.data['FİRMA'].dropna().tolist() if str(f).strip() != ""] if not st.session_state.data.empty else []
liste_firmalar = sorted(list(set(firmalar_crm + firmalar_gorev)))

gorev_sorumlulari = [str(s).strip() for s in st.session_state.data['ANA SORUMLU'].dropna().tolist() if str(s).strip() != ""] if not st.session_state.data.empty else []
liste_sorumlular = sorted(list(set(kullanici_listesi + gorev_sorumlulari)))

st.sidebar.divider()
st.sidebar.markdown("### 🔍 Filtreler")
display_df = st.session_state.data.copy()
f_firma = st.sidebar.multiselect("🏢 Firma", liste_firmalar)
f_sorumlu = st.sidebar.multiselect("👤 Sorumlu", liste_sorumlular)
f_durum = st.sidebar.multiselect("📌 Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"])

if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_sorumlu: display_df = display_df[display_df['ANA SORUMLU'].isin(f_sorumlu)]
if f_durum: display_df = display_df[display_df['DURUM'].isin(f_durum)]

# --- 5. SEKMELER (DİNAMİK YETKİ KONTROLÜ) ---
tabs_list = ["➕ Yeni Görev", "📋 İş Listesi ve Detaylar", "📊 Raporlama"]
if st.session_state.aktif_rol in ["Admin", "User"]:
    tabs_list.append("🏢 Firma Yönetimi")
    tabs_list.append("⚙️ Veri Yönetimi")
tabs_list.append("👤 Profil Ayarları")
if st.session_state.aktif_rol == "Admin":
    tabs_list.append("👥 Kullanıcı Yönetimi")

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
        v_durum = c2.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı"], key=f"frm_dr_{fid}")
        
        v_not = st.text_area("📌 Notlar", key=f"frm_not_{fid}")

        st.subheader("🛠 Alt Aşamalar")
        yeni_asamalar = []
        for i, stg in enumerate(st.session_state.temp_stages):
            ca1, ca2, ca3, ca4 = st.columns([3, 3, 2, 3])
            s_ad = ca1.text_input(f"{i+1}. İşlem", value=stg["Aşama Adı"], key=f"st_ad_{fid}_{i}")
            s_ki_sec = ca2.selectbox("Sorumlu", ["Aynı", "➕ YENİ EKLE..."] + liste_sorumlular, key=f"st_ki_sec_{fid}_{i}")
            s_final_ki = (v_sorumlu if s_ki_sec == "Aynı" else (ca2.text_input("Yeni Sorumlu", key=f"st_ki_y_{fid}_{i}") if s_ki_sec == "➕ YENİ EKLE..." else s_ki_sec))
            s_dr = ca3.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı"], key=f"st_dr_{fid}_{i}")
            s_nt = ca4.text_input("Aşama Notu", value=stg["Not"], key=f"st_nt_{fid}_{i}")
            yeni_asamalar.append({"Aşama Adı": s_ad, "Sorumlu": s_final_ki, "Durum": s_dr, "Not": s_nt})

        if st.button("➕ Aşama Ekle"):
            st.session_state.temp_stages.append({"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""})
            st.rerun()

        if st.button("✅ KAYDET", use_container_width=True):
            if v_ad and v_firma and v_firma != "Seçiniz":
                # Yeni firma girildiyse CRM'e otomatik aktar
                if v_firma not in firmalar_crm:
                    yeni_firma_satir = pd.DataFrame([{"FİRMA_ADI": v_firma, "YETKİLİ_KİŞİ": "", "EMAIL": "", "TITLE": "", "NOTLAR": ""}])
                    st.session_state.firmalar_db = pd.concat([st.session_state.firmalar_db, yeni_firma_satir], ignore_index=True)
                    tablo_kaydet(st.session_state.firmalar_db, "Firmalar")

                yeni = {
                    'GÖREV ADI': v_ad, 'FİRMA': v_firma, 'ANA SORUMLU': v_sorumlu,
                    'BAŞLANGIÇ': v_basla.strftime('%Y-%m-%d'), 
                    'BİTİŞ': v_bitis.strftime('%Y-%m-%d'),
                    'DURUM': v_durum, 'ÖNCELİK': v_oncelik, 'NOTLAR': v_not,
                    'AŞAMALAR': json.dumps([a for a in yeni_asamalar if a["Aşama Adı"].strip()], ensure_ascii=False),
                    'KAYIT_TARIHI': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([yeni])], ignore_index=True)
                tablo_kaydet(st.session_state.data, "Sayfa1")
                st.success("Görev başarıyla kaydedildi!")
                formu_sifirla()
                st.rerun()
            else: 
                st.error("Lütfen Görev Adı yazın ve Firma seçin.")

# ================= TAB: İŞ LİSTESİ VE DETAYLAR =================
with sekme_sozlugu["📋 İş Listesi ve Detaylar"]:
    if not display_df.empty:
        gosterilecek = display_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'], errors='ignore')
        sel = st.dataframe(gosterilecek, use_container_width=True, height=350, selection_mode="single-row", on_select="rerun", key="tablo")
        rows = sel.get("selection", {}).get("rows", [])
        if rows:
            idx = gosterilecek.index[rows[0]]
            secili = st.session_state.data.loc[idx]
            with st.container(border=True):
                st.markdown(f"### 🎯 {secili['GÖREV ADI']}")
                # İlgili firmanın CRM bilgisi gösterimi
                firma_info = st.session_state.firmalar_db[st.session_state.firmalar_db['FİRMA_ADI'] == secili['FİRMA']]
                if not firma_info.empty and str(firma_info.iloc[0]['YETKİLİ_KİŞİ']).strip() != "":
                    st.caption(f"📞 Yetkili: {firma_info.iloc[0]['YETKİLİ_KİŞİ']} | 📧 {firma_info.iloc[0]['EMAIL']}")
                
                c1, c2 = st.columns(2)
                durumlar = ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"]
                mevcut_durum_index = durumlar.index(secili['DURUM']) if secili['DURUM'] in durumlar else 0
                
                if st.session_state.aktif_rol == "Guest":
                    st.info(f"**Durum:** {secili['DURUM']} | **Not:** {secili['NOTLAR']}")
                    as_list = json.loads(secili['AŞAMALAR']) if pd.notna(secili['AŞAMALAR']) and secili['AŞAMALAR'] else []
                    st.dataframe(pd.DataFrame(as_list), use_container_width=True, hide_index=True)
                else:
                    y_dr = c1.selectbox("Durum", durumlar, index=mevcut_durum_index, key=f"up_dr_{idx}")
                    y_nt = c2.text_input("Not", value=str(secili['NOTLAR']) if pd.notna(secili['NOTLAR']) else "", key=f"up_nt_{idx}")
                    
                    as_list = json.loads(secili['AŞAMALAR']) if pd.notna(secili['AŞAMALAR']) and secili['AŞAMALAR'] else []
                    ed_as = st.data_editor(pd.DataFrame(as_list) if as_list else pd.DataFrame(columns=["Aşama Adı", "Sorumlu", "Durum", "Not"]), num_rows="dynamic", use_container_width=True, key=f"ed_as_{idx}",
                                          column_config={"Sorumlu": st.column_config.SelectboxColumn("Sorumlu", options=liste_sorumlular)})
                    
                    if st.button("💾 Güncelle", use_container_width=True):
                        st.session_state.data.at[idx, 'DURUM'] = y_dr
                        st.session_state.data.at[idx, 'NOTLAR'] = y_nt
                        st.session_state.data.at[idx, 'AŞAMALAR'] = json.dumps(ed_as.to_dict('records'), ensure_ascii=False)
                        tablo_kaydet(st.session_state.data, "Sayfa1")
                        st.success("Güncellendi!"); st.rerun()

# ================= TAB: RAPORLAMA =================
with sekme_sozlugu["📊 Raporlama"]:
    if not display_df.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(display_df, names="DURUM", title="Durum Dağılımı"), use_container_width=True)
        c2.plotly_chart(px.bar(display_df, x="FİRMA", color="DURUM", title="Firma İş Yükü"), use_container_width=True)

# ================= TAB: FİRMA YÖNETİMİ =================
if "🏢 Firma Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["🏢 Firma Yönetimi"]:
        st.subheader("🏢 Firma ve Rehber Yönetimi")
        ed_firmalar = st.data_editor(
            st.session_state.firmalar_db,
            num_rows="dynamic",
            use_container_width=True,
            key="crm_editor",
            column_config={
                "FİRMA_ADI": st.column_config.TextColumn("Firma Adı *", required=True),
                "YETKİLİ_KİŞİ": st.column_config.TextColumn("Yetkili Kişi"),
                "EMAIL": st.column_config.TextColumn("E-Posta"),
                "TITLE": st.column_config.TextColumn("Unvan"),
                "NOTLAR": st.column_config.TextColumn("Notlar")
            }
        )
        if st.button("💾 Firma Bilgilerini Kaydet"):
            st.session_state.firmalar_db = ed_firmalar
            tablo_kaydet(ed_firmalar, "Firmalar")
            st.success("Firma rehberi güncellendi!"); st.rerun()

# ================= TAB: VERİ YÖNETİMİ =================
if "⚙️ Veri Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["⚙️ Veri Yönetimi"]:
        st.download_button("📥 İş Listesini İndir", display_df.to_csv(index=False).encode('utf-8'), "tsi_is_takibi.csv", "text/csv")

# ================= TAB: PROFİL AYARLARI =================
with sekme_sozlugu["👤 Profil Ayarları"]:
    st.subheader("👤 Profil ve Şifre Yönetimi")
    st.info(f"Kullanıcı: **{st.session_state.aktif_kullanici}** | Yetki: **{st.session_state.aktif_rol}**")
    
    with st.container(border=True):
        st.markdown("#### 🔑 Şifremi Değiştir")
        e_pwd = st.text_input("Mevcut Şifre", type="password", key="p_old")
        n_pwd = st.text_input("Yeni Şifre", type="password", key="p_new")
        n_pwd_c = st.text_input("Yeni Şifre (Tekrar)", type="password", key="p_conf")
        
        if st.button("💾 Şifreyi Güncelle"):
            u_idx = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == st.session_state.aktif_kullanici].index[0]
            gercek_sifre = str(st.session_state.kullanicilar.at[u_idx, 'SIFRE'])
            
            if e_pwd != gercek_sifre:
                st.error("❌ Mevcut şifreniz yanlış.")
            elif n_pwd != n_pwd_c:
                st.error("❌ Yeni şifreler birbiriyle uyuşmuyor.")
            elif len(n_pwd) < 4:
                st.warning("⚠️ Şifre en az 4 karakter olmalıdır.")
            else:
                st.session_state.kullanicilar.at[u_idx, 'SIFRE'] = n_pwd
                tablo_kaydet(st.session_state.kullanicilar, "Kullanıcılar")
                st.success("✅ Şifreniz başarıyla güncellendi!"); st.rerun()

# ================= TAB: KULLANICI YÖNETİMİ =================
if "👥 Kullanıcı Yönetimi" in sekme_sozlugu:
    with sekme_sozlugu["👥 Kullanıcı Yönetimi"]:
        ed_u = st.data_editor(st.session_state.kullanicilar, num_rows="dynamic", use_container_width=True,
                             column_config={"ROL": st.column_config.SelectboxColumn("ROL", options=["Admin", "User", "Guest"])})
        if st.button("💾 Kullanıcıları Kaydet"):
            st.session_state.kullanicilar = ed_u
            tablo_kaydet(ed_u, "Kullanıcılar"); st.success("Kaydedildi!"); st.rerun()
