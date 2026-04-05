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
    st.session_state.form_id = 0  

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
    temiz_df = df.fillna("")
    conn.update(
        spreadsheet="https://docs.google.com/spreadsheets/d/1iF2VPQmygjibDXm3Q93COpMu0r4p4odayQZa_0ej0qM/edit?usp=sharing",
        worksheet="Sayfa1",
        data=temiz_df
    )

# --- 2. SESSION STATE VE SIFIRLAMA ---
if 'kullanicilar' not in st.session_state:
    st.session_state.kullanicilar = kullanici_yukle()
if 'data' not in st.session_state:
    st.session_state.data = veriyi_yukle()

if 'temp_stages' not in st.session_state:
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]

def formu_sifirla():
    st.session_state.form_id += 1
    st.session_state.temp_stages = [{"Aşama Adı": "", "Sorumlu": "Aynı", "Durum": "Bekliyor", "Not": ""}]
    for key in list(st.session_state.keys()):
        if key.startswith("frm_"):
            del st.session_state[key]

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

kullanicilar = st.session_state.kullanicilar['KULLANICI_ADI'].tolist()

if not st.session_state.giris_basarili:
    st.sidebar.title("🔐 Giriş")
    user = st.sidebar.selectbox("Kullanıcı", ["Seçiniz"] + kullanicilar)
    pwd = st.sidebar.text_input("Şifre", type="password")
    if st.sidebar.button("Giriş Yap"):
        if user != "Seçiniz":
            user_row = st.session_state.kullanicilar[st.session_state.kullanicilar['KULLANICI_ADI'] == user].iloc[0]
            if str(user_row['SIFRE']) == pwd:
                st.session_state.giris_basarili, st.session_state.aktif_kullanici = True, user
                st.session_state.aktif_rol = user_row['ROL']
                st.rerun()
            else: st.sidebar.error("Hatalı giriş!")
        else: st.sidebar.warning("Lütfen kullanıcı seçin.")
    st.stop()

# --- 4. ANA EKRAN VE FİLTRELER ---
st.sidebar.success(f"Hoş geldin, {st.session_state.aktif_kullanici}!")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.giris_basarili = False
    st.session_state.aktif_kullanici = None
    st.session_state.aktif_rol = None
    st.rerun()

firmalar = sorted(st.session_state.data['FİRMA'].dropna().unique().tolist()) if not st.session_state.data.empty else ["Akgıda", "Tegep"]
sorumlular = [k for k in kullanicilar if k != "Yönetici"]

st.sidebar.divider()
st.sidebar.caption(f"🔑 Yetki Seviyesi: **{st.session_state.aktif_rol}**")

display_df = st.session_state.data.copy()

# Sol menü filtrelerini tanımla
st.sidebar.markdown("### 🔍 Filtreler")
f_firma = st.sidebar.multiselect("🏢 Firma", firmalar)
f_sorumlu = st.sidebar.multiselect("👤 Sorumlu", sorumlular)
f_durum = st.sidebar.multiselect("📌 Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal", "Gecikti"])
f_oncelik = st.sidebar.multiselect("⚡ Öncelik", ["Düşük", "Orta", "Yüksek"])

# Filtreleri tabloya uygula
if f_firma: display_df = display_df[display_df['FİRMA'].isin(f_firma)]
if f_sorumlu: display_df = display_df[display_df['ANA SORUMLU'].isin(f_sorumlu)]
if f_durum: display_df = display_df[display_df['DURUM'].isin(f_durum)]
if f_oncelik: display_df = display_df[display_df['ÖNCELİK'].isin(f_oncelik)]

# --- SOL MENÜ İSTATİSTİKLERİ (Filtrelenmiş Veriye Göre Çalışır) ---
if not display_df.empty:
    st.sidebar.divider()
    st.sidebar.markdown("### 📊 Filtre Özeti")
    toplam_is = len(display_df)
    tamamlanan = len(display_df[display_df['DURUM'] == 'Tamamlandı'])
    bekleyen = len(display_df[display_df['DURUM'].isin(['Bekliyor', 'Devam Ediyor'])])
    
    c1, c2 = st.sidebar.columns(2)
    c1.metric("Listelenen", toplam_is)
    c2.metric("Biten", tamamlanan)
    st.sidebar.metric("⏳ Bekleyen/Devam", bekleyen)

# --- 5. SEKMELER ---
if st.session_state.aktif_rol == "Admin":
    tab_ekle, tab_liste, tab_rapor, tab_ayarlar, tab_kullanici = st.tabs(["➕ Yeni Görev", "📋 İş Listesi ve Detaylar", "📊 Raporlama", "⚙️ Veri Yönetimi", "👥 Kullanıcı Yönetimi"])
else:
    tab_ekle, tab_liste, tab_rapor, tab_ayarlar = st.tabs(["➕ Yeni Görev", "📋 İş Listesi ve Detaylar", "📊 Raporlama", "⚙️ Veri Yönetimi"])

# ================= TAB 1: YENİ GÖREV =================
with tab_ekle:
    fid = st.session_state.form_id
    c1, c2 = st.columns(2)
    with c1:
        v_ad = st.text_input("Görev Adı *", key=f"frm_ad_{fid}")
        v_firma_sec = st.selectbox("Firma *", ["➕ YENİ EKLE..."] + firmalar, key=f"frm_f_sec_{fid}")
        v_firma = st.text_input("Yeni Firma Adı *", key=f"frm_f_yeni_{fid}") if v_firma_sec == "➕ YENİ EKLE..." else v_firma_sec
        v_sorumlu = st.selectbox("Ana Sorumlu *", ["Seçiniz"] + sorumlular, key=f"frm_s_sec_{fid}")

    with c2:
        v_basla = st.date_input("Başlangıç", datetime.now(), key=f"frm_b_t_{fid}")
        v_bitis = st.date_input("Bitiş", datetime.now() + timedelta(days=7), key=f"frm_bit_t_{fid}")
        v_oncelik = st.selectbox("Öncelik *", ["Seçiniz", "Düşük", "Orta", "Yüksek"], key=f"frm_on_{fid}")
        v_durum = st.selectbox("Genel Durum *", ["Seçiniz", "Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"], key=f"frm_dur_{fid}")

    v_not = st.text_area("📌 Genel Görev Notu", key=f"frm_not_{fid}")

    st.write("---")
    st.subheader("🛠 Alt Aşamalar (Detaylı)")
    
    asamalar_listesi = []
    for i, stg in enumerate(st.session_state.temp_stages):
        ca1, ca2, ca3, ca4 = st.columns([3, 2, 2, 3])
        s_ad = ca1.text_input("Ne Yapılacak?", value=stg["Aşama Adı"], key=f"frm_st_ad_{fid}_{i}")
        s_ki = ca2.selectbox("Sorumlu", ["Aynı"] + sorumlular, key=f"frm_st_ki_{fid}_{i}")
        s_durum = ca3.selectbox("Durum", ["Bekliyor", "Devam Ediyor", "Tamamlandı", "İptal"], key=f"frm_st_dur_{fid}_{i}")
        s_not = ca4.text_input("Aşama Notu", value=stg["Not"], key=f"frm_st_not_{fid}_{i}")
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
            st.success("Görev Google Sheets'e başarıyla eklendi!")
            st.rerun()
        else:
            st.error("Lütfen yıldızlı (*) tüm zorunlu alanları doldurduğunuzdan emin olun!")

# ================= TAB 2: LİSTE VE DETAY PANELİ =================
with tab_liste:
    st.subheader("📋 Ana Görevler Tablosu")
    st.caption("Detaylarını görmek veya düzenlemek istediğiniz görevin üzerine tıklayın.")
    
    if not display_df.empty:
        gosterilecek_df = display_df.drop(columns=['AŞAMALAR', 'KAYIT_TARIHI'], errors='ignore')
        
        selection = st.dataframe(
            gosterilecek_df,
            use_container_width=True,
            height=350,
            selection_mode="single-row",
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
                
                if st.button("💾 Seçili Görevin Değişikliklerini Kaydet", use_container_width=True):
                    st.session_state.data.at[idx_label, 'DURUM'] = yeni_ana_durum
                    st.session_state.data.at[idx_label, 'NOTLAR'] = yeni_ana_not
                    st.session_state.data.at[idx_label, 'AŞAMALAR'] = asamalari_paketle(duz_asama_df.to_dict('records'))
                    
                    veriyi_kaydet(st.session_state.data)
                    st.success("Detaylar Google Sheets'e başarıyla kaydedildi! 💾")
                    st.rerun() 
        else:
            st.info("💡 Alt aşamaları görüntülemek ve düzenlemek için yukarıdaki listeden bir satıra tıklayın.")
    else:
        st.info("Gösterilecek görev bulunamadı veya filtrelere uyan sonuç yok.")

# ================= TAB 3: GELİŞMİŞ RAPORLAMA =================
with tab_rapor:
    st.subheader("📊 Gelişmiş İş ve Performans Raporları")
    
    # ÇÖZÜM: st.session_state.data yerine süzülmüş olan display_df kullanılıyor!
    if not display_df.empty:
        df_rapor = display_df.copy()
        
        # 1. SATIR: KPI KARTLARI
        st.markdown("#### 🎯 Seçili Filtrelere Göre Özet")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Gösterilen Görev", len(df_rapor))
        m2.metric("Tamamlanan ✅", len(df_rapor[df_rapor['DURUM'] == 'Tamamlandı']))
        m3.metric("Devam Eden ⏳", len(df_rapor[df_rapor['DURUM'] == 'Devam Ediyor']))
        m4.metric("Geciken/İptal ⚠️", len(df_rapor[df_rapor['DURUM'].isin(['Gecikti', 'İptal'])]))
        
        st.divider()
        
        # 2. SATIR: GRAFİKLER
        c1, c2 = st.columns(2)
        with c1:
            fig_firma = px.histogram(df_rapor, y="FİRMA", color="DURUM", barmode="group", 
                                     title="🏢 Firmalara Göre İş Yükü Dağılımı", orientation='h')
            st.plotly_chart(fig_firma, use_container_width=True)
            
            renk_haritasi = {"Yüksek": "#EF553B", "Orta": "#FECB52", "Düşük": "#00CC96"}
            fig_oncelik = px.pie(df_rapor, names="ÖNCELİK", title="⚡ Aciliyet / Öncelik Dağılımı", 
                                 hole=0.3, color="ÖNCELİK", color_discrete_map=renk_haritasi)
            st.plotly_chart(fig_oncelik, use_container_width=True)

        with c2:
            fig_sorumlu = px.pie(df_rapor, names="ANA SORUMLU", hole=0.4, title="👤 Personel Sorumluluk Dağılımı")
            fig_sorumlu.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_sorumlu, use_container_width=True)
            
            fig_durum = px.pie(df_rapor, names="DURUM", title="📌 Genel İş Durumu")
            st.plotly_chart(fig_durum, use_container_width=True)
            
        st.divider()
        
        # 3. SATIR: YAKLAŞAN / ACİL İŞLER TABLOSU
        st.markdown("#### ⏳ Yaklaşan ve Acil Görevler (Filtrelenmiş İşler İçinden)")
        try:
            df_rapor['BİTİŞ'] = pd.to_datetime(df_rapor['BİTİŞ'])
            df_yaklasan = df_rapor[df_rapor['DURUM'].isin(['Bekliyor', 'Devam Ediyor'])].sort_values(by='BİTİŞ')
            
            if not df_yaklasan.empty:
                df_yaklasan['BİTİŞ'] = df_yaklasan['BİTİŞ'].dt.strftime('%Y-%m-%d')
                st.dataframe(
                    df_yaklasan[['GÖREV ADI', 'FİRMA', 'ANA SORUMLU', 'BİTİŞ', 'ÖNCELİK']], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.success("Seçili filtrelere göre beklemede olan görev bulunmuyor!")
        except Exception as e:
            st.info("Görevler tarih sırasına dizilirken bir hata oluştu.")
            
    else:
        st.warning("Seçtiğiniz filtrelere uyan herhangi bir görev bulunmuyor.")

# ================= TAB 4: VERİ YÖNETİMİ =================
with tab_ayarlar:
    csv = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Tüm Görev Verilerini İndir (Yedek)", data=csv, file_name='tsi_is_takip_yedek.csv', mime='text/csv')

# ================= TAB 5: KULLANICI YÖNETİMİ (SADECE ADMİN) =================
if st.session_state.aktif_rol == "Admin":
    with tab_kullanici:
        st.subheader("👥 Sisteme Kayıtlı Kullanıcılar")
        duzenlenen_kullanicilar = st.data_editor(st.session_state.kullanicilar, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Kullanıcı Değişikliklerini Kaydet"):
            st.session_state.kullanicilar = duzenlenen_kullanicilar
            kullanici_kaydet(duzenlenen_kullanicilar)
            st.success("Kullanıcılar başarıyla güncellendi!")
            st.rerun()
